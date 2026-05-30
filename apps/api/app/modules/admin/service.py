import json
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import func as sqlfunc
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.admin.models import (
    AuditLog,
    PushSubscription,
    SourceTemplate,
    UserGroup,
    UserGroupMember,
)
from app.modules.admin.schemas import (
    AuditLogPage,
    AuditLogRead,
    GroupCreate,
    GroupDetailRead,
    GroupMemberAdd,
    GroupMemberRead,
    GroupRead,
    PushAction,
    PushSubscriptionRead,
    TemplateCreate,
    TemplatePush,
    TemplateRead,
    UserCreate,
    UserListPage,
    UserRead,
    UserRoleUpdate,
    UserStatusUpdate,
)
from app.modules.auth.schemas import CurrentUser
from app.modules.auth.service import hash_password
from app.modules.sources.models import Source, Subscription
from app.modules.users.models import User


def _require_admin(current_user: CurrentUser) -> None:
    if "admin" not in (current_user.roles or []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )


class AdminService:
    # ── User Management ──

    def list_users(
        self, db: Session, current_user: CurrentUser, q: str | None = None
    ) -> UserListPage:
        _require_admin(current_user)
        stmt = select(User).where(User.deleted_at.is_(None))
        if q:
            like = f"%{q}%"
            stmt = stmt.where(
                (User.username.ilike(like)) | (User.display_name.ilike(like))
            )
        stmt = stmt.order_by(User.created_at.desc())
        users = db.scalars(stmt).all()
        return UserListPage(
            items=[self._user_to_read(u) for u in users],
            total=len(users),
        )

    def update_user_role(
        self,
        db: Session,
        current_user: CurrentUser,
        user_id: str,
        payload: UserRoleUpdate,
    ) -> UserRead:
        _require_admin(current_user)
        user = self._get_user(db, user_id)
        user.role = payload.role
        self._log(db, current_user.id, "update_role", "user", user_id, {"role": payload.role})
        db.commit()
        db.refresh(user)
        return self._user_to_read(user)

    def update_user_status(
        self,
        db: Session,
        current_user: CurrentUser,
        user_id: str,
        payload: UserStatusUpdate,
    ) -> UserRead:
        _require_admin(current_user)
        user = self._get_user(db, user_id)
        user.status = payload.status
        self._log(db, current_user.id, "update_status", "user", user_id, {"status": payload.status})
        db.commit()
        db.refresh(user)
        return self._user_to_read(user)

    def create_user(
        self, db: Session, current_user: CurrentUser, payload: UserCreate
    ) -> UserRead:
        _require_admin(current_user)
        existing = db.scalar(
            select(User).where(User.username == payload.username)
        )
        if existing:
            raise HTTPException(status_code=409, detail="用户名已存在")
        if payload.email:
            existing_email = db.scalar(
                select(User).where(User.email == payload.email)
            )
            if existing_email:
                raise HTTPException(status_code=409, detail="邮箱已被使用")
        user = User(
            id=f"user_{uuid4().hex}",
            username=payload.username,
            password_hash=hash_password(payload.password),
            display_name=payload.display_name,
            email=payload.email,
            role=payload.role,
            status="active",
        )
        db.add(user)
        self._log(
            db, current_user.id, "create", "user", user.id,
            {"username": payload.username, "role": payload.role},
        )
        db.commit()
        db.refresh(user)
        return self._user_to_read(user)

    # ── Group Management ──

    def list_groups(self, db: Session, current_user: CurrentUser) -> list[GroupRead]:
        _require_admin(current_user)
        groups = db.scalars(
            select(UserGroup).order_by(UserGroup.created_at.desc())
        ).all()
        result = []
        for g in groups:
            count = db.scalar(
                select(sqlfunc.count())
                .select_from(UserGroupMember)
                .where(UserGroupMember.group_id == g.id)
            ) or 0
            result.append(
                GroupRead(
                    id=g.id,
                    name=g.name,
                    description=g.description,
                    member_count=count,
                    created_by=g.created_by,
                    created_at=g.created_at,
                )
            )
        return result

    def get_group(
        self, db: Session, current_user: CurrentUser, group_id: str
    ) -> GroupDetailRead:
        _require_admin(current_user)
        group = db.get(UserGroup, group_id)
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")
        members = db.scalars(
            select(UserGroupMember).where(UserGroupMember.group_id == group_id)
        ).all()
        member_reads = []
        for m in members:
            user = db.get(User, m.user_id)
            member_reads.append(
                GroupMemberRead(
                    user_id=m.user_id,
                    username=user.username if user else m.user_id,
                    display_name=user.display_name if user else "Unknown",
                    joined_at=m.created_at,
                )
            )
        return GroupDetailRead(
            id=group.id,
            name=group.name,
            description=group.description,
            members=member_reads,
            created_by=group.created_by,
            created_at=group.created_at,
        )

    def create_group(
        self, db: Session, current_user: CurrentUser, payload: GroupCreate
    ) -> GroupRead:
        _require_admin(current_user)
        existing = db.scalar(
            select(UserGroup).where(UserGroup.name == payload.name)
        )
        if existing:
            raise HTTPException(status_code=409, detail="Group name already exists")
        group = UserGroup(
            id=f"group_{uuid4().hex}",
            name=payload.name,
            description=payload.description,
            created_by=current_user.id,
        )
        db.add(group)
        self._log(db, current_user.id, "create", "group", group.id, {"name": payload.name})
        db.commit()
        db.refresh(group)
        return GroupRead(
            id=group.id,
            name=group.name,
            description=group.description,
            member_count=0,
            created_by=group.created_by,
            created_at=group.created_at,
        )

    def delete_group(
        self, db: Session, current_user: CurrentUser, group_id: str
    ) -> None:
        _require_admin(current_user)
        group = db.get(UserGroup, group_id)
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")
        # Delete members first
        members = db.scalars(
            select(UserGroupMember).where(UserGroupMember.group_id == group_id)
        ).all()
        for m in members:
            db.delete(m)
        self._log(db, current_user.id, "delete", "group", group_id, {"name": group.name})
        db.delete(group)
        db.commit()

    def add_group_members(
        self,
        db: Session,
        current_user: CurrentUser,
        group_id: str,
        payload: GroupMemberAdd,
    ) -> GroupDetailRead:
        _require_admin(current_user)
        group = db.get(UserGroup, group_id)
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")
        added = 0
        for uid in payload.user_ids:
            existing = db.scalar(
                select(UserGroupMember)
                .where(UserGroupMember.group_id == group_id)
                .where(UserGroupMember.user_id == uid)
            )
            if existing:
                continue
            db.add(
                UserGroupMember(
                    id=f"gm_{uuid4().hex}",
                    group_id=group_id,
                    user_id=uid,
                )
            )
            added += 1
        if added:
            self._log(
                db, current_user.id, "add_members", "group", group_id,
                {"added": added, "user_ids": payload.user_ids},
            )
            db.commit()
        return self.get_group(db, current_user, group_id)

    def remove_group_member(
        self,
        db: Session,
        current_user: CurrentUser,
        group_id: str,
        user_id: str,
    ) -> None:
        _require_admin(current_user)
        member = db.scalar(
            select(UserGroupMember)
            .where(UserGroupMember.group_id == group_id)
            .where(UserGroupMember.user_id == user_id)
        )
        if not member:
            raise HTTPException(status_code=404, detail="Member not found")
        db.delete(member)
        self._log(
            db, current_user.id, "remove_member", "group", group_id,
            {"user_id": user_id},
        )
        db.commit()

    # ── Source Templates ──

    def list_templates(
        self, db: Session, current_user: CurrentUser
    ) -> list[TemplateRead]:
        _require_admin(current_user)
        templates = db.scalars(
            select(SourceTemplate)
            .where(SourceTemplate.deleted_at.is_(None))
            .order_by(SourceTemplate.created_at.desc())
        ).all()
        return [self._template_to_read(t) for t in templates]

    def create_template(
        self, db: Session, current_user: CurrentUser, payload: TemplateCreate
    ) -> TemplateRead:
        _require_admin(current_user)
        template = SourceTemplate(
            id=f"tpl_{uuid4().hex}",
            name=payload.name,
            type=payload.type,
            endpoint=payload.endpoint,
            config_json=json.dumps(payload.config, ensure_ascii=False),
            description=payload.description,
            created_by=current_user.id,
        )
        db.add(template)
        self._log(db, current_user.id, "create", "template", template.id, {"name": payload.name})
        db.commit()
        db.refresh(template)
        return self._template_to_read(template)

    def delete_template(
        self, db: Session, current_user: CurrentUser, template_id: str
    ) -> None:
        _require_admin(current_user)
        template = db.get(SourceTemplate, template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        template.deleted_at = datetime.now(timezone.utc)
        self._log(db, current_user.id, "delete", "template", template_id, {})
        db.commit()

    def push_template(
        self,
        db: Session,
        current_user: CurrentUser,
        template_id: str,
        payload: TemplatePush,
    ) -> list[PushSubscriptionRead]:
        _require_admin(current_user)
        template = db.get(SourceTemplate, template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        target_user_ids: list[str] = []
        if payload.target_type == "user":
            target_user_ids = payload.target_ids
        elif payload.target_type == "group":
            for gid in payload.target_ids:
                members = db.scalars(
                    select(UserGroupMember).where(UserGroupMember.group_id == gid)
                ).all()
                for m in members:
                    if m.user_id not in target_user_ids:
                        target_user_ids.append(m.user_id)

        results: list[PushSubscriptionRead] = []
        for uid in target_user_ids:
            existing = db.scalar(
                select(PushSubscription)
                .where(PushSubscription.user_id == uid)
                .where(PushSubscription.template_id == template_id)
            )
            if existing:
                continue
            ps = PushSubscription(
                id=f"push_{uuid4().hex}",
                user_id=uid,
                template_id=template_id,
                status="pending",
                pushed_by=current_user.id,
            )
            db.add(ps)
            results.append(
                PushSubscriptionRead(
                    id=ps.id,
                    user_id=uid,
                    template_id=template_id,
                    template_name=template.name,
                    source_id=None,
                    status="pending",
                    pushed_by=current_user.id,
                    created_at=None,
                )
            )

        self._log(
            db, current_user.id, "push_template", "template", template_id,
            {
                "target_type": payload.target_type,
                "target_ids": payload.target_ids,
                "pushed_to": len(results),
            },
        )
        db.commit()
        return results

    # ── Push Subscriptions (user side) ──

    def list_my_pushes(
        self, db: Session, current_user: CurrentUser
    ) -> list[PushSubscriptionRead]:
        pushes = db.scalars(
            select(PushSubscription)
            .where(PushSubscription.user_id == current_user.id)
            .where(PushSubscription.status == "pending")
            .order_by(PushSubscription.created_at.desc())
        ).all()
        result = []
        for p in pushes:
            template = db.get(SourceTemplate, p.template_id)
            result.append(
                PushSubscriptionRead(
                    id=p.id,
                    user_id=p.user_id,
                    template_id=p.template_id,
                    template_name=template.name if template else "Unknown",
                    source_id=p.source_id,
                    status=p.status,
                    pushed_by=p.pushed_by,
                    created_at=p.created_at,
                )
            )
        return result

    def act_on_push(
        self,
        db: Session,
        current_user: CurrentUser,
        push_id: str,
        payload: PushAction,
    ) -> PushSubscriptionRead:
        ps = db.get(PushSubscription, push_id)
        if not ps:
            raise HTTPException(status_code=404, detail="Push subscription not found")
        if ps.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not your push subscription")
        if ps.status != "pending":
            raise HTTPException(status_code=400, detail="Already processed")

        template = db.get(SourceTemplate, ps.template_id)

        if payload.action == "accept":
            # Create a real source from the template
            source = Source(
                id=f"source_{uuid4().hex}",
                name=template.name if template else "Pushed Source",
                type=template.type if template else "rss",
                endpoint=template.endpoint if template else "",
                config_json=template.config_json if template else "{}",
                created_by=current_user.id,
            )
            db.add(source)
            db.flush()
            # Create subscription
            sub = Subscription(
                id=f"sub_{uuid4().hex}",
                user_id=current_user.id,
                source_id=source.id,
            )
            db.add(sub)
            ps.source_id = source.id
            ps.status = "accepted"
        else:
            ps.status = "ignored"

        self._log(
            db, current_user.id, payload.action, "push_subscription", push_id,
            {"template_id": ps.template_id},
        )
        db.commit()
        db.refresh(ps)
        return PushSubscriptionRead(
            id=ps.id,
            user_id=ps.user_id,
            template_id=ps.template_id,
            template_name=template.name if template else "Unknown",
            source_id=ps.source_id,
            status=ps.status,
            pushed_by=ps.pushed_by,
            created_at=ps.created_at,
        )

    # ── Audit Logs ──

    def list_audit_logs(
        self,
        db: Session,
        current_user: CurrentUser,
        action: str | None = None,
        resource_type: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> AuditLogPage:
        _require_admin(current_user)
        stmt = select(AuditLog)
        if action:
            stmt = stmt.where(AuditLog.action == action)
        if resource_type:
            stmt = stmt.where(AuditLog.resource_type == resource_type)

        count_stmt = select(sqlfunc.count()).select_from(stmt.subquery())
        total = db.scalar(count_stmt) or 0

        stmt = stmt.order_by(AuditLog.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        logs = db.scalars(stmt).all()

        return AuditLogPage(
            items=[self._audit_to_read(log) for log in logs],
            total=total,
            page=page,
            page_size=page_size,
        )

    # ── Helpers ──

    def _get_user(self, db: Session, user_id: str) -> User:
        user = db.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user

    def _user_to_read(self, u: User) -> UserRead:
        return UserRead(
            id=u.id,
            username=u.username,
            email=u.email,
            display_name=u.display_name,
            role=getattr(u, "role", "user"),
            status=u.status,
            last_login_at=u.last_login_at,
            created_at=u.created_at,
        )

    def _template_to_read(self, t: SourceTemplate) -> TemplateRead:
        config = {}
        try:
            config = json.loads(t.config_json or "{}")
        except (json.JSONDecodeError, TypeError):
            pass
        return TemplateRead(
            id=t.id,
            name=t.name,
            type=t.type,
            endpoint=t.endpoint,
            config=config,
            description=t.description,
            created_by=t.created_by,
            created_at=t.created_at,
        )

    def _audit_to_read(self, log: AuditLog) -> AuditLogRead:
        details = {}
        try:
            details = json.loads(log.details_json or "{}")
        except (json.JSONDecodeError, TypeError):
            pass
        return AuditLogRead(
            id=log.id,
            actor_id=log.actor_id,
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            details=details,
            created_at=log.created_at,
        )

    def _log(
        self,
        db: Session,
        actor_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        details: dict,
    ) -> None:
        db.add(
            AuditLog(
                id=f"audit_{uuid4().hex}",
                actor_id=actor_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details_json=json.dumps(details, ensure_ascii=False),
            )
        )


admin_service = AdminService()
