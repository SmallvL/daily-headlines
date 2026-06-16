import {
  ClockCircleOutlined,
  FilterOutlined,
  ReloadOutlined,
  SearchOutlined
} from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import { Button, Card, Select, Space, Table, Tag, Typography } from "antd";
import { useState } from "react";

import { useTranslation } from "react-i18next";

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

export function FetchLogsPage({ session }: FetchLogsPageProps) {
  const { t } = useTranslation();

  const STATUS_LABELS: Record<string, string> = {
    success: t("taskLogs.success"),
    failed: t("taskLogs.failed"),
    running: t("taskLogs.running"),
    retrying: t("taskLogs.retrying"),
  };

  const TRIGGER_LABELS: Record<string, string> = {
    manual: t("taskLogs.manual"),
    schedule: t("taskLogs.scheduled"),
    retry: t("taskLogs.retry"),
  };

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
              {t("taskLogs.title")}
            </Space>
          </Typography.Title>
          <Typography.Text type="secondary">
            {t("taskLogs.subtitle")}
          </Typography.Text>
        </div>
        <Button
          icon={<ReloadOutlined />}
          onClick={() => logsQuery.refetch()}
        >
          {t("taskLogs.refresh")}
        </Button>
      </div>

      <Card
        styles={{ body: { padding: "16px 20px" } }}
        style={{ borderRadius: "var(--radius-md)" }}
      >
        <Space style={{ marginBottom: 16 }} wrap>
          <Select
            allowClear
            placeholder={t("taskLogs.allSources")}
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
            placeholder={t("taskLogs.allStatus")}
            style={{ width: 120 }}
            value={statusFilter}
            onChange={(v) => {
              setStatusFilter(v);
              setPage(1);
            }}
            options={[
              { label: STATUS_LABELS["success"], value: "success" },
              { label: STATUS_LABELS["failed"], value: "failed" },
              { label: STATUS_LABELS["running"], value: "running" },
              { label: STATUS_LABELS["retrying"], value: "retrying" },
            ]}
            suffixIcon={<FilterOutlined />}
          />
          <Select
            allowClear
            placeholder="Filter by trigger"
            style={{ width: 120 }}
            value={triggerFilter}
            onChange={(v) => {
              setTriggerFilter(v);
              setPage(1);
            }}
            options={[
              { label: TRIGGER_LABELS["manual"], value: "manual" },
              { label: TRIGGER_LABELS["schedule"], value: "schedule" },
              { label: TRIGGER_LABELS["retry"], value: "retry" },
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
            showTotal: (total) => t("taskLogs.totalRecords", { total }),
            showSizeChanger: false,
          }}
        />
      </Card>
    </div>
  );
}
