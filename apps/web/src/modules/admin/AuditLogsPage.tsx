import { ReloadOutlined } from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import { Button, Select, Space, Table, Tag, Typography } from "antd";
import { useState } from "react";

import { AuthSession } from "../../shared/api/auth";
import { listAuditLogs } from "../../shared/api/admin";

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

const ACTION_LABELS: Record<string, string> = {
  create: "创建",
  delete: "删除",
  update_role: "修改角色",
  update_status: "修改状态",
  add_members: "添加成员",
  remove_member: "移除成员",
  push_template: "推送模板",
  accept: "接受",
  ignore: "忽略",
};

const RESOURCE_LABELS: Record<string, string> = {
  user: "用户",
  group: "组",
  template: "模板",
  push_subscription: "推送订阅",
};

export function AuditLogsPage({ session }: AuditLogsPageProps) {
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
      title: "操作",
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
      title: "资源类型",
      dataIndex: "resource_type",
      key: "resource_type",
      width: 120,
      render: (rt: string) => RESOURCE_LABELS[rt] ?? rt,
    },
    {
      title: "资源 ID",
      dataIndex: "resource_id",
      key: "resource_id",
      ellipsis: true,
      render: (v: string | null) => v ?? "—",
    },
    {
      title: "操作人",
      dataIndex: "actor_id",
      key: "actor_id",
      width: 140,
    },
    {
      title: "详情",
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
      title: "时间",
      dataIndex: "created_at",
      key: "created_at",
      width: 180,
      render: (v: string | null) =>
        v ? new Date(v).toLocaleString("zh-CN") : "—",
    },
  ];

  return (
    <div>
      <Typography.Title level={4}>审计日志</Typography.Title>
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
          options={[
            { label: "创建", value: "create" },
            { label: "删除", value: "delete" },
            { label: "修改角色", value: "update_role" },
            { label: "修改状态", value: "update_status" },
            { label: "添加成员", value: "add_members" },
            { label: "移除成员", value: "remove_member" },
            { label: "推送模板", value: "push_template" },
          ]}
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
          options={[
            { label: "用户", value: "user" },
            { label: "组", value: "group" },
            { label: "模板", value: "template" },
            { label: "推送订阅", value: "push_subscription" },
          ]}
        />
        <Button
          icon={<ReloadOutlined />}
          onClick={() => logsQuery.refetch()}
        >
          刷新
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
          showTotal: (total) => `共 ${total} 条`,
        }}
      />
    </div>
  );
}
