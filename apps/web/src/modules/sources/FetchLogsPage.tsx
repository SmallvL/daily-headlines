import {
  ClockCircleOutlined,
  FilterOutlined,
  ReloadOutlined,
  SearchOutlined
} from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import { Button, Card, Select, Space, Table, Tag, Typography } from "antd";
import { useState } from "react";

import { AuthSession } from "../../shared/api/auth";
import { Source, SourceFetchLog, listAllFetchLogs, listSources } from "../../shared/api/sources";

type FetchLogsPageProps = {
  session: AuthSession;
};

const STATUS_COLORS: Record<string, string> = {
  success: "green",
  failed: "red",
  running: "blue",
  retrying: "orange",
};

const STATUS_LABELS: Record<string, string> = {
  success: "成功",
  failed: "失败",
  running: "运行中",
  retrying: "重试中",
};

const TRIGGER_LABELS: Record<string, string> = {
  manual: "手动",
  schedule: "定时",
  retry: "重试",
};

export function FetchLogsPage({ session }: FetchLogsPageProps) {
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);
  const [triggerFilter, setTriggerFilter] = useState<string | undefined>(undefined);
  const [sourceFilter, setSourceFilter] = useState<string | undefined>(undefined);
  const [page, setPage] = useState(1);
  const pageSize = 20;

  const sourcesQuery = useQuery({
    queryKey: ["sources"],
    queryFn: () => listSources(session),
  });

  const logsQuery = useQuery({
    queryKey: ["all-fetch-logs", sourceFilter, statusFilter, triggerFilter, page],
    queryFn: () =>
      listAllFetchLogs(session, {
        source_id: sourceFilter,
        status: statusFilter,
        trigger: triggerFilter,
        page,
        page_size: pageSize,
      }),
  });

  const sourceNameMap = new Map<string, string>(
    (sourcesQuery.data ?? []).map((s: Source) => [s.id, s.name])
  );

  const columns = [
    {
      title: "信息源",
      dataIndex: "source_id",
      key: "source_id",
      render: (sourceId: string) => (
        <Typography.Text strong>{sourceNameMap.get(sourceId) ?? sourceId}</Typography.Text>
      ),
    },
    {
      title: "触发方式",
      dataIndex: "trigger",
      key: "trigger",
      width: 100,
      render: (trigger: string) => (
        <Tag>{TRIGGER_LABELS[trigger] ?? trigger}</Tag>
      ),
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      width: 100,
      render: (status: string) => (
        <Tag color={STATUS_COLORS[status] ?? "default"}>
          {STATUS_LABELS[status] ?? status}
        </Tag>
      ),
    },
    {
      title: "尝试",
      key: "attempt",
      width: 80,
      render: (_: unknown, record: SourceFetchLog) => (
        <Typography.Text type="secondary">
          {record.attempt}/{record.max_attempts}
        </Typography.Text>
      ),
    },
    {
      title: "新增",
      dataIndex: "inserted_count",
      key: "inserted_count",
      width: 80,
      render: (v: number) => (
        <Typography.Text type="success">{v}</Typography.Text>
      ),
    },
    {
      title: "跳过",
      dataIndex: "skipped_count",
      key: "skipped_count",
      width: 80,
      render: (v: number) => (
        <Typography.Text type="secondary">{v}</Typography.Text>
      ),
    },
    {
      title: "错误信息",
      dataIndex: "error_message",
      key: "error_message",
      ellipsis: true,
      render: (msg: string | null) =>
        msg ? (
          <Typography.Text type="danger" ellipsis={{ tooltip: msg }}>
            {msg}
          </Typography.Text>
        ) : (
          <Typography.Text type="secondary">—</Typography.Text>
        ),
    },
    {
      title: "开始时间",
      dataIndex: "started_at",
      key: "started_at",
      width: 180,
      render: (v: string) => (
        <Space size={4}>
          <ClockCircleOutlined style={{ fontSize: 12, color: "var(--ant-color-text-tertiary)" }} />
          <Typography.Text>{v ? new Date(v).toLocaleString("zh-CN") : "—"}</Typography.Text>
        </Space>
      ),
    },
  ];

  return (
    <div className="fetch-logs-page">
      <div className="source-section-header">
        <div>
          <Typography.Title level={4} style={{ marginBottom: 4 }}>
            <Space>
              <ClockCircleOutlined />
              任务日志
            </Space>
          </Typography.Title>
          <Typography.Text type="secondary">
            查看所有信息源的抓取记录和状态
          </Typography.Text>
        </div>
        <Button
          icon={<ReloadOutlined />}
          onClick={() => logsQuery.refetch()}
        >
          刷新
        </Button>
      </div>

      <Card
        styles={{ body: { padding: "16px 20px" } }}
        style={{ borderRadius: "var(--radius-md)" }}
      >
        <Space style={{ marginBottom: 16 }} wrap>
          <Select
            allowClear
            placeholder="按信息源筛选"
            style={{ minWidth: 180 }}
            value={sourceFilter}
            onChange={(v) => {
              setSourceFilter(v);
              setPage(1);
            }}
            options={(sourcesQuery.data ?? []).map((s: Source) => ({
              label: s.name,
              value: s.id,
            }))}
            suffixIcon={<SearchOutlined />}
          />
          <Select
            allowClear
            placeholder="按状态筛选"
            style={{ width: 120 }}
            value={statusFilter}
            onChange={(v) => {
              setStatusFilter(v);
              setPage(1);
            }}
            options={[
              { label: "成功", value: "success" },
              { label: "失败", value: "failed" },
              { label: "运行中", value: "running" },
              { label: "重试中", value: "retrying" },
            ]}
            suffixIcon={<FilterOutlined />}
          />
          <Select
            allowClear
            placeholder="按触发方式"
            style={{ width: 120 }}
            value={triggerFilter}
            onChange={(v) => {
              setTriggerFilter(v);
              setPage(1);
            }}
            options={[
              { label: "手动", value: "manual" },
              { label: "定时", value: "schedule" },
              { label: "重试", value: "retry" },
            ]}
            suffixIcon={<FilterOutlined />}
          />
        </Space>

        <Table
          dataSource={logsQuery.data?.items ?? []}
          columns={columns}
          rowKey="id"
          loading={logsQuery.isLoading}
          size="small"
          pagination={{
            current: page,
            pageSize,
            total: logsQuery.data?.total ?? 0,
            onChange: setPage,
            showTotal: (total) => `共 ${total} 条记录`,
            showSizeChanger: false,
          }}
        />
      </Card>
    </div>
  );
}
