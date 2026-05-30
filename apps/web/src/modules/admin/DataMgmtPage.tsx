import { useMutation, useQuery } from "@tanstack/react-query";
import {
  Alert,
  Button,
  Card,
  Col,
  Descriptions,
  InputNumber,
  message,
  Modal,
  Progress,
  Row,
  Space,
  Statistic,
  Switch,
  Table,
  Tag,
  Typography,
} from "antd";
import { useState } from "react";

import type { AuthSession } from "../../shared/api/auth";
import {
  executePurge,
  getStorageStats,
  listRetentionConfigs,
  previewPurge,
  runVacuum,
  updateRetentionConfig,
  type PurgeAllResult,
  type PurgePreview,
  type RetentionConfig,
} from "../../shared/api/dataMgmt";

type Props = {
  session: AuthSession;
};

const TABLE_LABELS: Record<string, string> = {
  feed_items: "📰 信息条目",
  user_item_states: "👤 用户状态",
  source_fetch_logs: "📋 抓取日志",
  audit_logs: "🔒 审计日志",
  agent_drafts: "🤖 Agent 草稿",
  users: "用户",
  sources: "信源",
  subscriptions: "订阅",
  saved_searches: "保存搜索",
  user_groups: "用户组",
  user_group_members: "组成员",
  source_templates: "信源模板",
  push_subscriptions: "推送订阅",
  llm_providers: "LLM 提供商",
  user_preferences: "用户偏好",
  agent_tokens: "Agent 令牌",
  data_retention_configs: "保留策略",
};

function fmtNum(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
  if (n >= 1_000) return (n / 1_000).toFixed(1) + "K";
  return String(n);
}

function fmtDate(s: string | null): string {
  if (!s) return "—";
  try {
    return new Date(s).toLocaleDateString("zh-CN");
  } catch {
    return "—";
  }
}

export default function DataMgmtPage({ session }: Props) {
  const [messageApi, contextHolder] = message.useMessage();
  const [purgePreviews, setPurgePreviews] = useState<PurgePreview[]>([]);
  const [purgeModalOpen, setPurgeModalOpen] = useState(false);
  const [purgeResult, setPurgeResult] = useState<PurgeAllResult | null>(null);

  /* ── Queries ── */
  const statsQuery = useQuery({
    queryKey: ["data-mgmt-stats"],
    queryFn: () => getStorageStats(session),
    refetchInterval: 30_000,
  });

  const configsQuery = useQuery({
    queryKey: ["data-mgmt-configs"],
    queryFn: () => listRetentionConfigs(session),
  });

  /* ── Mutations ── */
  const updateConfigMut = useMutation({
    mutationFn: (args: { tableName: string; updates: Partial<RetentionConfig> }) =>
      updateRetentionConfig(session, args.tableName, args.updates),
    onSuccess: () => {
      configsQuery.refetch();
      messageApi.success("策略已更新");
    },
    onError: (e) => messageApi.error(e instanceof Error ? e.message : "更新失败"),
  });

  const previewMut = useMutation({
    mutationFn: () => previewPurge(session),
    onSuccess: (data) => {
      setPurgePreviews(data);
      setPurgeModalOpen(true);
    },
    onError: (e) => messageApi.error(e instanceof Error ? e.message : "预览失败"),
  });

  const purgeMut = useMutation({
    mutationFn: () => executePurge(session),
    onSuccess: (data) => {
      setPurgeResult(data);
      setPurgeModalOpen(false);
      statsQuery.refetch();
      configsQuery.refetch();
      if (data.total_deleted === 0) {
        messageApi.info("没有需要清理的数据");
      } else {
        messageApi.success(`已清理 ${fmtNum(data.total_deleted)} 条记录`);
      }
    },
    onError: (e) => messageApi.error(e instanceof Error ? e.message : "清理失败"),
  });

  const vacuumMut = useMutation({
    mutationFn: () => runVacuum(session),
    onSuccess: (data) => {
      if (data.success) {
        const d = data.details as Record<string, number>;
        messageApi.success(
          `VACUUM 完成：${d.size_before_mb}MB → ${d.size_after_mb}MB，回收 ${(d.reclaimed_mb || 0).toFixed(3)}MB`,
        );
        statsQuery.refetch();
      } else {
        messageApi.error("VACUUM 失败");
      }
    },
    onError: (e) => messageApi.error(e instanceof Error ? e.message : "VACUUM 失败"),
  });

  const stats = statsQuery.data;
  const configs = configsQuery.data ?? [];

  /* ── Growth tables (the ones with retention configs) ── */
  const growthTables = stats?.tables.filter((t) =>
    configs.some((c) => c.table_name === t.table_name),
  ) ?? [];

  const maxRecords = Math.max(...growthTables.map((t) => t.record_count), 1);

  return (
    <div style={{ maxWidth: 960, margin: "0 auto" }}>
      {contextHolder}

      <Typography.Title level={4} style={{ marginBottom: 24 }}>
        📦 数据管理
      </Typography.Title>

      {/* ── Overview Cards ── */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic
              title="数据库大小"
              value={stats?.db_size_mb ?? "—"}
              suffix="MB"
              precision={3}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic
              title="总记录数"
              value={stats?.total_records ?? "—"}
              formatter={(v) => fmtNum(v as number)}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic
              title="可增长表"
              value={growthTables.length}
              suffix={`/ ${stats?.tables.length ?? "—"}`}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card>
            <Space direction="vertical" size={4} style={{ width: "100%" }}>
              <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                操作
              </Typography.Text>
              <Button
                type="primary"
                size="small"
                block
                loading={previewMut.isPending}
                onClick={() => previewMut.mutate()}
              >
                预览清理
              </Button>
              <Button
                size="small"
                block
                loading={vacuumMut.isPending}
                onClick={() => vacuumMut.mutate()}
              >
                VACUUM
              </Button>
            </Space>
          </Card>
        </Col>
      </Row>

      {/* ── Purge result ── */}
      {purgeResult && (
        <Alert
          type="success"
          showIcon
          closable
          onClose={() => setPurgeResult(null)}
          style={{ marginBottom: 16 }}
          message={
            <>
              清理完成：删除 {fmtNum(purgeResult.total_deleted)} 条记录，
              数据库 {purgeResult.db_size_before_mb}MB → {purgeResult.db_size_after_mb}MB
              {purgeResult.vacuum_performed && "（已 VACUUM）"}
            </>
          }
        />
      )}

      {/* ── Table Size Visualization ── */}
      <Card title="📊 各表数据量" style={{ marginBottom: 24 }}>
        <Space direction="vertical" style={{ width: "100%" }} size={8}>
          {growthTables.map((t) => (
            <div key={t.table_name} style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <Typography.Text style={{ width: 160, fontSize: 13, flexShrink: 0 }}>
                {TABLE_LABELS[t.table_name] ?? t.table_name}
              </Typography.Text>
              <Progress
                percent={Math.round((t.record_count / maxRecords) * 100)}
                size="small"
                style={{ flex: 1 }}
                format={() => fmtNum(t.record_count)}
              />
              <Typography.Text type="secondary" style={{ fontSize: 11, width: 60, textAlign: "right" }}>
                {fmtDate(t.oldest_record)}
              </Typography.Text>
            </div>
          ))}
        </Space>
      </Card>

      {/* ── Retention Configs ── */}
      <Card title="⚙️ 数据保留策略" style={{ marginBottom: 24 }}>
        <Table
          dataSource={configs}
          rowKey="id"
          size="small"
          pagination={false}
          columns={[
            {
              title: "数据表",
              dataIndex: "table_name",
              render: (v: string) => TABLE_LABELS[v] ?? v,
            },
            {
              title: "保留天数",
              dataIndex: "max_age_days",
              width: 120,
              render: (v: number | null, record: RetentionConfig) => (
                <InputNumber
                  size="small"
                  min={1}
                  max={3650}
                  value={v ?? undefined}
                  disabled={!record.enabled}
                  style={{ width: 80 }}
                  onChange={(val) =>
                    updateConfigMut.mutate({
                      tableName: record.table_name,
                      updates: { max_age_days: val },
                    })
                  }
                />
              ),
            },
            {
              title: "每源上限",
              dataIndex: "max_records",
              width: 120,
              render: (v: number | null, record: RetentionConfig) => (
                <InputNumber
                  size="small"
                  min={10}
                  max={100000}
                  value={v ?? undefined}
                  disabled={!record.enabled || record.table_name !== "feed_items"}
                  style={{ width: 80 }}
                  placeholder="—"
                  onChange={(val) =>
                    updateConfigMut.mutate({
                      tableName: record.table_name,
                      updates: { max_records: val },
                    })
                  }
                />
              ),
            },
            {
              title: "保留收藏",
              dataIndex: "keep_saved",
              width: 80,
              render: (v: boolean, record: RetentionConfig) => (
                <Switch
                  size="small"
                  checked={v}
                  disabled={!record.enabled || record.table_name !== "feed_items"}
                  onChange={(checked) =>
                    updateConfigMut.mutate({
                      tableName: record.table_name,
                      updates: { keep_saved: checked },
                    })
                  }
                />
              ),
            },
            {
              title: "启用",
              dataIndex: "enabled",
              width: 60,
              render: (v: boolean, record: RetentionConfig) => (
                <Switch
                  size="small"
                  checked={v}
                  onChange={(checked) =>
                    updateConfigMut.mutate({
                      tableName: record.table_name,
                      updates: { enabled: checked },
                    })
                  }
                />
              ),
            },
            {
              title: "上次清理",
              dataIndex: "last_purge_at",
              width: 120,
              render: (v: string | null, record: RetentionConfig) =>
                v ? (
                  <Space size={4}>
                    <span>{fmtDate(v)}</span>
                    {record.last_purge_count != null && (
                      <Tag>{fmtNum(record.last_purge_count)}条</Tag>
                    )}
                  </Space>
                ) : (
                  <Typography.Text type="secondary">从未</Typography.Text>
                ),
            },
          ]}
        />
      </Card>

      {/* ── Export ── */}
      <Card title="📤 数据导出">
        <Space>
          <Button
            onClick={() => {
              const token = session.accessToken;
              window.open(
                `/api/data-mgmt/export?fmt=json&token=${encodeURIComponent(token)}`,
                "_blank",
              );
            }}
          >
            导出 JSON
          </Button>
          <Button
            onClick={() => {
              const token = session.accessToken;
              window.open(
                `/api/data-mgmt/export?fmt=csv&token=${encodeURIComponent(token)}`,
                "_blank",
              );
            }}
          >
            导出 CSV
          </Button>
        </Space>
      </Card>

      {/* ── Purge Preview Modal ── */}
      <Modal
        title="清理预览"
        open={purgeModalOpen}
        onCancel={() => setPurgeModalOpen(false)}
        footer={
          <Space>
            <Button onClick={() => setPurgeModalOpen(false)}>取消</Button>
            <Button
              type="primary"
              danger
              loading={purgeMut.isPending}
              onClick={() => purgeMut.mutate()}
              disabled={purgePreviews.length === 0}
            >
              {purgePreviews.length === 0 ? "无需清理" : "确认清理"}
            </Button>
          </Space>
        }
      >
        {purgePreviews.length === 0 ? (
          <Alert type="info" showIcon message="所有数据都在保留期内，无需清理。" />
        ) : (
          <Space direction="vertical" style={{ width: "100%" }}>
            {purgePreviews.map((p) => (
              <Card key={p.table_name} size="small">
                <Descriptions column={1} size="small">
                  <Descriptions.Item label="数据表">
                    {TABLE_LABELS[p.table_name] ?? p.table_name}
                  </Descriptions.Item>
                  <Descriptions.Item label="待删除">{fmtNum(p.records_to_delete)} 条</Descriptions.Item>
                  <Descriptions.Item label="条件">{p.criteria}</Descriptions.Item>
                </Descriptions>
              </Card>
            ))}
          </Space>
        )}
      </Modal>
    </div>
  );
}
