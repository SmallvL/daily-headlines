import { PlusOutlined, ReloadOutlined, SearchOutlined } from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import {
  Button,
  Form,
  Input,
  Modal,
  Select,
  Space,
  Switch,
  Table,
  Tag,
  Typography,
  message,
} from "antd";
import { useState } from "react";

import { AuthSession } from "../../shared/api/auth";
import {
  AdminUser,
  createUser,
  listAdminUsers,
  updateUserRole,
  updateUserStatus,
} from "../../shared/api/admin";

import { useTranslation } from "react-i18next";

type UsersPageProps = { session: AuthSession };

const STATUS_COLORS: Record<string, string> = {
  active: "green",
  disabled: "default",
};

export function UsersPage({ session }: UsersPageProps) {
  const { t } = useTranslation();
  const [search, setSearch] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [messageApi, contextHolder] = message.useMessage();
  const [form] = Form.useForm();

  const usersQuery = useQuery({
    queryKey: ["admin-users", search],
    queryFn: () => listAdminUsers(session, search || undefined),
  });

  async function handleRoleChange(userId: string, isAdmin: boolean) {
    try {
      await updateUserRole(session, userId, isAdmin ? "admin" : "user");
      messageApi.success("角色已更新");
      usersQuery.refetch();
    } catch {
      messageApi.error("更新失败");
    }
  }

  async function handleStatusChange(userId: string, disabled: boolean) {
    try {
      await updateUserStatus(
        session,
        userId,
        disabled ? "disabled" : "active"
      );
      messageApi.success("状态已更新");
      usersQuery.refetch();
    } catch {
      messageApi.error("更新失败");
    }
  }

  async function handleCreate() {
    try {
      const values = await form.validateFields();
      await createUser(session, values);
      messageApi.success("用户已创建");
      setCreateOpen(false);
      form.resetFields();
      usersQuery.refetch();
    } catch (e) {
      if (typeof e === "object" && e !== null && "errorFields" in e) return; // validation
      messageApi.error(e instanceof Error ? e.message : "创建失败");
    }
  }

  const columns = [
    {
      title: t("admin.username"),
      dataIndex: "username",
      key: "username",
      width: 140,
    },
    {
      title: t("admin.displayName"),
      dataIndex: "display_name",
      key: "display_name",
      width: 140,
    },
    {
      title: t("admin.email"),
      dataIndex: "email",
      key: "email",
      render: (v: string | null) => v ?? "—",
    },
    {
      title: t("admin.role"),
      dataIndex: "role",
      key: "role",
      width: 120,
      render: (role: string, record: AdminUser) => (
        <Switch
          checked={role === "admin"}
          checkedChildren={t("admin.admin")}
          unCheckedChildren={t("admin.normalUser")}
          onChange={(checked) => handleRoleChange(record.id, checked)}
        />
      ),
    },
    {
      title: t("admin.status"),
      key: "status",
      width: 120,
      render: (_: unknown, record: AdminUser) => (
        <Space>
          <Tag color={STATUS_COLORS[record.status] ?? "default"}>
            {record.status === "active" ? t("admin.active") : t("admin.disabled")}
          </Tag>
          <Switch
            size="small"
            checked={record.status === "active"}
            onChange={(checked) => handleStatusChange(record.id, !checked)}
          />
        </Space>
      ),
    },
    {
      title: t("admin.lastLogin"),
      dataIndex: "last_login_at",
      key: "last_login_at",
      width: 180,
      render: (v: string | null) =>
        v ? new Date(v).toLocaleString("zh-CN") : "—",
    },
    {
      title: t("admin.createdAt"),
      dataIndex: "created_at",
      key: "created_at",
      width: 180,
      render: (v: string | null) =>
        v ? new Date(v).toLocaleString("zh-CN") : "—",
    },
  ];

  return (
    <div className="users-page">
      {contextHolder}
      <Typography.Title level={4}>{t("admin.userManagement")}</Typography.Title>
      <Space style={{ marginBottom: 16 }}>
        <Input
          placeholder={t("admin.searchPlaceholder")}
          prefix={<SearchOutlined />}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onPressEnter={() => usersQuery.refetch()}
          style={{ width: 240 }}
          allowClear
        />
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => setCreateOpen(true)}
        >
          {t("admin.createUser")}
        </Button>
        <Button
          icon={<ReloadOutlined />}
          onClick={() => usersQuery.refetch()}
        >
          {t("admin.refresh")}
        </Button>
      </Space>
      <Table
        dataSource={usersQuery.data?.items ?? []}
        columns={columns}
        rowKey="id"
        loading={usersQuery.isLoading}
        size="small"
        pagination={false}
      />

      {/* Create User Modal */}
      <Modal
        title={t("admin.createUser")}
        open={createOpen}
        onOk={handleCreate}
        onCancel={() => {
          setCreateOpen(false);
          form.resetFields();
        }}
      >
        <Form form={form} layout="vertical" initialValues={{ role: "user" }}>
          <Form.Item
            name="username"
            label="用户名"
            rules={[
              { required: true, message: "请输入用户名" },
              { min: 2, message: "至少2个字符" },
            ]}
          >
            <Input placeholder="用于登录的用户名" />
          </Form.Item>
          <Form.Item
            name="password"
            label="密码"
            rules={[
              { required: true, message: "请输入密码" },
              { min: 6, message: "至少6个字符" },
            ]}
          >
            <Input.Password placeholder="登录密码" />
          </Form.Item>
          <Form.Item
            name="display_name"
            label="显示名"
            rules={[{ required: true, message: "请输入显示名" }]}
          >
            <Input placeholder="用户昵称或姓名" />
          </Form.Item>
          <Form.Item name="email" label="邮箱">
            <Input placeholder="可选邮箱" />
          </Form.Item>
          <Form.Item name="role" label="角色">
            <Select
              options={[
                { label: "普通用户", value: "user" },
                { label: "管理员", value: "admin" },
              ]}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
