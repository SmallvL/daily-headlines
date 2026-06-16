import { ReloadOutlined } from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import { Button, Select, Space, Table, Tag, Typography } from "antd";
import { useState } from "react";

import { AuthSession } from "../../shared/api/auth";
import { listAuditLogs } from "../../shared/api/admin";

import { useTranslation } from "react-i18next";

type AuditLogsPageProps = { session: AuthSession };

const ACTION_COLORS: Record<string, string> = {
  create: "green",
  delete: "red",
  update_role: "blue",
  update_status: "orange",
  add_members: "cyan",
  remove_member: "magenta",
  push_template: "purple",
  accept: "green",
  ignore: "default",
};



export function AuditLogsPage({ session }: AuditLogsPageProps) {
  const { t } = useTranslation();
  const ACTION_LABELS: Record<string, string> = {
    create: t("admin.actionCreate"),
    delete: t("admin.actionDelete"),
    update_role: t("admin.actionUpdateRole"),
    update_status: t("admin.actionUpdateStatus"),
    add_members: t("admin.actionAddMembers"),
    remove_member: t("admin.actionRemoveMember"),
    push_template: t("admin.actionPushTemplate"),
    accept: t("admin.actionAccept"),
    ignore: t("admin.actionIgnore"),
  };
  const RESOURCE_LABELS: Record<string, string> = {
    user: t("admin.resourceUser"),
    group: t("admin.resourceGroup"),
    template: t("admin.resourceTemplate"),
    push_subscription: t("admin.resourcePushSubscription"),
  };
  const [actionFilter, setActionFilter] = useState<string | undefined>(undefined);
  const [resourceFilter, setResourceFilter] = useState<string | undefined>(undefined);
  const [page, setPage] = useState(1);
  const pageSize = 20;

  const logsQuery = useQuery({
    queryKey: ["admin-audit-logs", actionFilter, resourceFilter, page],
    queryFn: () =>
      listAuditLogs(session, {
        action: actionFilter,
        resource_type: resourceFilter,
        page,
        page_size: pageSize,
      }),
  });

  const columns = [
    {
      title: t("admin.auditAction"),
      dataIndex: "action",
      key: "action",
      width: 120,
      render: (action: string) => (
        <Tag color={ACTION_COLORS[action] ?? "default"}>
          {ACTION_LABELS[action] ?? action}
        </Tag>
      ),
    },
    {
      title: t("admin.resourceType"),
      dataIndex: "resource_type",
      key: "resource_type",
      width: 120,
      render: (rt: string) => RESOURCE_LABELS[rt] ?? rt,
    },
    {
      title: t("admin.resourceId"),
      dataIndex: "resource_id",
      key: "resource_id",
      ellipsis: true,
      render: (v: string | null) => v ?? "—",
    },
    {
      title: t("admin.operator"),
      dataIndex: "actor_id",
      key: "actor_id",
      width: 140,
    },
    {
      title: t("admin.details"),
      dataIndex: "details",
      key: "details",
      ellipsis: true,
      render: (details: Record<string, unknown>) => (
        <Typography.Text
          type="secondary"
          ellipsis={{ tooltip: JSON.stringify(details) }}
        >
          {Object.keys(details).length > 0
            ? JSON.stringify(details)
            : "—"}
        </Typography.Text>
      ),
    },
    {
      title: t("admin.time"),
      dataIndex: "created_at",
      key: "created_at",
      width: 180,
      render: (v: string | null) =>
        v ? new Date(v).toLocaleString("zh-CN") : "—",
    },
  ];

  return (
    <div className="audit-logs-page">
      <Typography.Title level={4}>{t("admin.auditLogs")}</Typography.Title>
      <Space style={{ marginBottom: 16 }} wrap>
        <Select
          allowClear
          placeholder="按操作筛选"
          style={{ width: 140 }}
          value={actionFilter}
          onChange={(v) => {
            setActionFilter(v);
            setPage(1);
          }}
          options={Object.entries(ACTION_LABELS).map(([value, label]) => ({ value, label }))}
        />
        <Select
          allowClear
          placeholder="按资源类型筛选"
          style={{ width: 140 }}
          value={resourceFilter}
          onChange={(v) => {
            setResourceFilter(v);
            setPage(1);
          }}
          options={Object.entries(RESOURCE_LABELS).map(([value, label]) => ({ value, label }))}
        />
        <Button
          icon={<ReloadOutlined />}
          onClick={() => logsQuery.refetch()}
        >
          {t("admin.refresh")}
        </Button>
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
        }}
      />
    </div>
  );
}
