import csv
import io
import json
import os
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.modules.data_mgmt.models import DataRetentionConfig
from app.modules.data_mgmt.schemas import (
    ExportInfo,
    PurgeAllResult,
    PurgePreview,
    PurgeResult,
    StorageStats,
    TableStats,
)
from app.modules.feed.models import FeedItem, UserItemState

# ── Retentionable tables and their timestamp columns ──
RETENTION_TABLES: dict[str, dict] = {
    "feed_items": {
        "model": FeedItem,
        "timestamp_col": "fetched_at",
        "cascades": ["user_item_states"],
    },
    "user_item_states": {
        "model": UserItemState,
        "timestamp_col": "updated_at",
    },
    "source_fetch_logs": {
        "table": "source_fetch_logs",
        "timestamp_col": "finished_at",
    },
    "audit_logs": {
        "table": "audit_logs",
        "timestamp_col": "created_at",
    },
    "agent_drafts": {
        "table": "agent_drafts",
        "timestamp_col": "created_at",
    },
}

# All tables we track for stats
TRACKED_TABLES = [
    "users", "sources", "subscriptions", "feed_items", "user_item_states",
    "source_fetch_logs", "saved_searches", "user_groups", "user_group_members",
    "source_templates", "push_subscriptions", "audit_logs", "llm_providers",
    "agent_drafts", "user_preferences", "agent_tokens", "data_retention_configs",
]


class DataMgmtService:

    # ── Storage Stats ──

    def get_storage_stats(self, db: Session, db_path: str) -> StorageStats:
        """Return storage statistics for all tracked tables."""
        db_size = os.path.getsize(db_path) if os.path.exists(db_path) else 0
        tables: list[TableStats] = []
        total_records = 0

        for table_name in TRACKED_TABLES:
            try:
                count = db.scalar(text(f"SELECT COUNT(*) FROM {table_name}")) or 0
            except Exception:
                continue

            total_records += count

            # Estimate size: avg row size * count
            try:
                page_count = db.scalar(text(f"SELECT COUNT(*) FROM {table_name}"))
                # Rough estimate: use db page info if available
                avg_row = db_size / max(total_records, 1) if total_records > 0 else 0
                est_kb = (count * avg_row) / 1024 if avg_row > 0 else 0
            except Exception:
                est_kb = 0

            # Get oldest/newest timestamps
            oldest = None
            newest = None
            ts_col = None
            if table_name in RETENTION_TABLES:
                ts_col = RETENTION_TABLES[table_name].get("timestamp_col")
            elif table_name == "feed_items":
                ts_col = "fetched_at"

            if ts_col:
                try:
                    oldest = db.scalar(text(f"SELECT MIN({ts_col}) FROM {table_name}"))
                    newest = db.scalar(text(f"SELECT MAX({ts_col}) FROM {table_name}"))
                except Exception:
                    pass

            tables.append(TableStats(
                table_name=table_name,
                record_count=count,
                estimated_size_kb=round(est_kb, 2),
                oldest_record=oldest,
                newest_record=newest,
            ))

        return StorageStats(
            db_path=db_path,
            db_size_mb=round(db_size / (1024 * 1024), 3),
            tables=tables,
            total_records=total_records,
        )

    # ── Retention Configs ──

    def list_configs(self, db: Session) -> list[DataRetentionConfig]:
        configs = list(db.scalars(
            select(DataRetentionConfig).order_by(DataRetentionConfig.table_name)
        ).all())
        if not configs:
            configs = self._seed_defaults(db)
        return configs

    def _seed_defaults(self, db: Session) -> list[DataRetentionConfig]:
        """Seed default retention configs if none exist."""
        defaults = [
            ("feed_items", 90, 500, True, True),
            ("source_fetch_logs", 30, None, False, True),
            ("audit_logs", 180, None, False, True),
            ("agent_drafts", 30, None, False, True),
            ("user_item_states", 90, None, False, True),
        ]
        configs = []
        for table_name, max_age, max_rec, keep_saved, enabled in defaults:
            cfg = DataRetentionConfig(
                table_name=table_name,
                max_age_days=max_age,
                max_records=max_rec,
                keep_saved=keep_saved,
                enabled=enabled,
            )
            db.add(cfg)
            configs.append(cfg)
        db.commit()
        return configs

    def update_config(
        self, db: Session, table_name: str, updates: dict
    ) -> DataRetentionConfig | None:
        # Ensure defaults are seeded
        self.list_configs(db)
        cfg = db.scalar(
            select(DataRetentionConfig).where(DataRetentionConfig.table_name == table_name)
        )
        if not cfg:
            return None
        for key, val in updates.items():
            if val is not None and hasattr(cfg, key):
                setattr(cfg, key, val)
        cfg.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(cfg)
        return cfg

    # ── Purge ──

    def preview_purge(self, db: Session, table_name: str | None = None) -> list[PurgePreview]:
        """Preview what would be deleted without actually deleting."""
        configs = self.list_configs(db)
        previews = []

        for cfg in configs:
            if table_name and cfg.table_name != table_name:
                continue
            if not cfg.enabled:
                continue

            preview = self._preview_one(db, cfg)
            if preview:
                previews.append(preview)

        return previews

    def _preview_one(self, db: Session, cfg: DataRetentionConfig) -> PurgePreview | None:
        table = cfg.table_name
        if table not in RETENTION_TABLES:
            return None

        ts_col = RETENTION_TABLES[table].get("timestamp_col", "created_at")
        criteria_parts = []
        count = 0
        oldest_to_keep = None

        # Age-based cleanup
        if cfg.max_age_days:
            cutoff = datetime.now(timezone.utc) - timedelta(days=cfg.max_age_days)
            try:
                age_count = db.scalar(
                    text(f"SELECT COUNT(*) FROM {table} WHERE {ts_col} < :cutoff"),
                    {"cutoff": cutoff},
                ) or 0
                count += age_count
                criteria_parts.append(f"超过 {cfg.max_age_days} 天的记录")
                oldest_to_keep = cutoff
            except Exception:
                pass

        # Count-based cleanup (per source for feed_items)
        if cfg.max_records and table == "feed_items":
            try:
                # Get sources that have more than max_records items
                overflow = db.execute(text(f"""
                    SELECT source_id, COUNT(*) as cnt
                    FROM feed_items
                    GROUP BY source_id
                    HAVING cnt > :max_rec
                """), {"max_rec": cfg.max_records}).fetchall()

                excess = 0
                for row in overflow:
                    src_id, cnt = row
                    excess += cnt - cfg.max_records

                if excess > 0:
                    count += excess
                    criteria_parts.append(f"每个信源超过 {cfg.max_records} 条的记录")
            except Exception:
                pass

        if count == 0:
            return None

        return PurgePreview(
            table_name=table,
            records_to_delete=count,
            oldest_to_keep=oldest_to_keep,
            criteria=" + ".join(criteria_parts) if criteria_parts else "保留策略",
        )

    def execute_purge(
        self, db: Session, table_name: str | None = None, vacuum: bool = True
    ) -> PurgeAllResult:
        """Execute purge based on retention configs."""
        db_size_before = self._get_db_size(db)
        configs = self.list_configs(db)
        results: list[PurgeResult] = []
        total_deleted = 0

        for cfg in configs:
            if table_name and cfg.table_name != table_name:
                continue
            if not cfg.enabled:
                continue

            result = self._purge_one(db, cfg)
            if result and result.deleted_count > 0:
                results.append(result)
                total_deleted += result.deleted_count

                # Update last purge info
                cfg.last_purge_at = datetime.now(timezone.utc)
                cfg.last_purge_count = result.deleted_count

        db.commit()

        # VACUUM if requested and we deleted something
        vacuum_performed = False
        if vacuum and total_deleted > 0:
            try:
                db.execute(text("VACUUM"))
                vacuum_performed = True
            except Exception:
                pass

        db_size_after = self._get_db_size(db)

        return PurgeAllResult(
            results=results,
            total_deleted=total_deleted,
            db_size_before_mb=round(db_size_before / (1024 * 1024), 3),
            db_size_after_mb=round(db_size_after / (1024 * 1024), 3),
            vacuum_performed=vacuum_performed,
        )

    def _purge_one(self, db: Session, cfg: DataRetentionConfig) -> PurgeResult | None:
        table = cfg.table_name
        if table not in RETENTION_TABLES:
            return None

        ts_col = RETENTION_TABLES[table].get("timestamp_col", "created_at")
        start = time.monotonic()
        deleted = 0

        # Age-based purge
        if cfg.max_age_days:
            cutoff = datetime.now(timezone.utc) - timedelta(days=cfg.max_age_days)
            try:
                if table == "feed_items" and cfg.keep_saved:
                    # Don't delete saved items
                    result = db.execute(text(f"""
                        DELETE FROM {table}
                        WHERE {ts_col} < :cutoff
                        AND id NOT IN (
                            SELECT item_id FROM user_item_states
                            WHERE saved_at IS NOT NULL
                        )
                    """), {"cutoff": cutoff})
                else:
                    result = db.execute(
                        text(f"DELETE FROM {table} WHERE {ts_col} < :cutoff"),
                        {"cutoff": cutoff},
                    )
                deleted += result.rowcount

                # Cascade: clean orphaned user_item_states
                if table == "feed_items" and deleted > 0:
                    db.execute(text("""
                        DELETE FROM user_item_states
                        WHERE item_id NOT IN (SELECT id FROM feed_items)
                    """))
            except Exception:
                pass

        # Count-based purge for feed_items
        if cfg.max_records and table == "feed_items":
            try:
                # Delete oldest items beyond max_records per source
                db.execute(text(f"""
                    DELETE FROM {table}
                    WHERE id IN (
                        SELECT id FROM (
                            SELECT id, ROW_NUMBER() OVER (
                                PARTITION BY source_id ORDER BY {ts_col} DESC
                            ) as rn
                            FROM {table}
                        ) ranked
                        WHERE rn > :max_rec
                    )
                """), {"max_rec": cfg.max_records})
                deleted_after = db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar() or 0
                # The rowcount from the DELETE above isn't reliable in SQLite subqueries
                # so we just track the main age-based deletion count
            except Exception:
                pass

        duration_ms = int((time.monotonic() - start) * 1000)

        if deleted == 0:
            return None

        return PurgeResult(
            table_name=table,
            deleted_count=deleted,
            duration_ms=duration_ms,
        )

    # ── Export ──

    def export_data(
        self,
        db: Session,
        tables: list[str] | None = None,
        fmt: str = "json",
        source_id: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> tuple[bytes, ExportInfo]:
        """Export data from specified tables."""
        export_tables = tables or ["feed_items", "sources", "saved_searches"]
        exported: dict[str, list[dict]] = {}
        total_records = 0

        for table_name in export_tables:
            if table_name not in TRACKED_TABLES:
                continue

            rows = self._fetch_table(
                db, table_name, source_id=source_id,
                date_from=date_from, date_to=date_to,
            )
            exported[table_name] = rows
            total_records += len(rows)

        # Serialize
        if fmt == "csv":
            content = self._to_csv(exported)
        else:
            content = json.dumps(exported, ensure_ascii=False, indent=2, default=str).encode("utf-8")

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"daily_headlines_export_{timestamp}.{fmt}"

        info = ExportInfo(
            filename=filename,
            format=fmt,
            tables_exported=list(exported.keys()),
            total_records=total_records,
            file_size_kb=round(len(content) / 1024, 2),
            created_at=datetime.now(timezone.utc),
        )

        return content, info

    def _fetch_table(
        self,
        db: Session,
        table_name: str,
        source_id: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> list[dict]:
        """Fetch all rows from a table with optional filters."""
        where_clauses = []
        params: dict = {}

        if source_id and table_name == "feed_items":
            where_clauses.append("source_id = :source_id")
            params["source_id"] = source_id

        ts_col = RETENTION_TABLES.get(table_name, {}).get("timestamp_col", "created_at")

        if date_from:
            where_clauses.append(f"{ts_col} >= :date_from")
            params["date_from"] = date_from
        if date_to:
            where_clauses.append(f"{ts_col} <= :date_to")
            params["date_to"] = date_to

        where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        try:
            result = db.execute(text(f"SELECT * FROM {table_name}{where_sql}"), params)
            columns = result.keys()
            return [dict(zip(columns, row)) for row in result.fetchall()]
        except Exception:
            return []

    def _to_csv(self, data: dict[str, list[dict]]) -> bytes:
        """Convert multi-table export to CSV (one section per table)."""
        output = io.StringIO()
        for table_name, rows in data.items():
            if not rows:
                continue
            output.write(f"# {table_name}\n")
            writer = csv.DictWriter(output, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
            output.write("\n")
        return output.getvalue().encode("utf-8")

    # ── Maintenance ──

    def run_vacuum(self, db: Session) -> dict:
        """Run VACUUM to reclaim space."""
        db_size_before = self._get_db_size(db)
        try:
            db.execute(text("VACUUM"))
            db_size_after = self._get_db_size(db)
            return {
                "success": True,
                "size_before_mb": round(db_size_before / (1024 * 1024), 3),
                "size_after_mb": round(db_size_after / (1024 * 1024), 3),
                "reclaimed_mb": round((db_size_before - db_size_after) / (1024 * 1024), 3),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _get_db_size(self, db: Session) -> int:
        """Get database file size in bytes."""
        try:
            db_path = db.bind.url.database
            if db_path and os.path.exists(db_path):
                return os.path.getsize(db_path)
        except Exception:
            pass
        return 0


data_mgmt_service = DataMgmtService()
