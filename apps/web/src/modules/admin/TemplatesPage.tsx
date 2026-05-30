import {
  DeleteOutlined,
  PlusOutlined,
  PushpinOutlined,
  ReloadOutlined,
} from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import {
  Button,
  Form,
  Input,
  List,
  Modal,
  Popconfirm,
  Select,
  Space,
  Tag,
  Typography,
  message,
} from "antd";
import { useState } from "react";

import { AuthSession } from "../../shared/api/auth";
import {
  SourceTemplate,
  createTemplate,
  deleteTemplate,
  listGroups,
  listTemplates,
  listAdminUsers,
  pushTemplate,
} from "../../shared/api/admin";

type TemplatesPageProps = { session: AuthSession };

export function TemplatesPage({ session }: TemplatesPageProps) {
  const [createOpen, setCreateOpen] = useState(false);
  const [pushOpen, setPushOpen] = useState<string | null>(null);
  const [pushTargetType, setPushTargetType] = useState("user");
  const [messageApi, contextHolder] = message.useMessage();
  const [form] = Form.useForm();
  const [pushForm] = Form.useForm();

  const templatesQuery = useQuery({
    queryKey: ["admin-templates"],
    queryFn: () => listTemplates(session),
  });

  const usersQuery = useQuery({
    queryKey: ["admin-users-for-push"],
    queryFn: () => listAdminUsers(session),
    enabled: pushOpen !== null && pushTargetType === "user",
  });

  const groupsQuery = useQuery({
    queryKey: ["admin-groups-for-push"],
    queryFn: () => listGroups(session),
    enabled: pushOpen !== null && pushTargetType === "group",
  });

  async function handleCreate() {
    try {
      const values = await form.validateFields();
      await createTemplate(session, {
        name: values.name,
        type: values.type,
        endpoint: values.endpoint,
        description: values.description,
      });
      messageApi.success("模板已创建");
      setCreateOpen(false);
      form.resetFields();
      templatesQuery.refetch();
    } catch (e) {
      if (typeof e === "object" && e !== null && "errorFields" in e) return; // validation
      messageApi.error(e instanceof Error ? e.message : "创建失败");
    }
  }

  async function handleDelete(templateId: string) {
    try {
      await deleteTemplate(session, templateId);
      messageApi.success("模板已删除");
      templatesQuery.refetch();
    } catch {
      messageApi.error("删除失败");
    }
  }

  async function handlePush() {
    try {
      const values = await pushForm.validateFields();
      await pushTemplate(
        session,
        pushOpen!,
        pushTargetType,
        values.target_ids
      );
      messageApi.success("推送成功");
      setPushOpen(null);
      pushForm.resetFields();
    } catch (e) {
      if (typeof e === "object" && e !== null && "errorFields" in e) return; // validation
      messageApi.error(e instanceof Error ? e.message : "推送失败");
    }
  }

  return (
    <div>
      {contextHolder}
      <Typography.Title level={4}>公共信息源模板</Typography.Title>
      <Space style={{ marginBottom: 16 }}>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => setCreateOpen(true)}
        >
          创建模板
        </Button>
        <Button
          icon={<ReloadOutlined />}
          onClick={() => templatesQuery.refetch()}
        >
          刷新
        </Button>
      </Space>

      <List
        loading={templatesQuery.isLoading}
        dataSource={templatesQuery.data ?? []}
        renderItem={(tpl: SourceTemplate) => (
          <List.Item
            actions={[
              <Button
                key="push"
                size="small"
                icon={<PushpinOutlined />}
                onClick={() => setPushOpen(tpl.id)}
              >
                推送
              </Button>,
              <Popconfirm
                key="delete"
                title="确定删除此模板？"
                onConfirm={() => handleDelete(tpl.id)}
              >
                <Button size="small" danger icon={<DeleteOutlined />} />
              </Popconfirm>,
            ]}
          >
            <List.Item.Meta
              title={
                <Space>
                  {tpl.name}
                  <Tag color={tpl.type === "rss" ? "blue" : "green"}>
                    {tpl.type.toUpperCase()}
                  </Tag>
                </Space>
              }
              description={
                <div>
                  <div>{tpl.endpoint}</div>
                  {tpl.description && (
                    <Typography.Text type="secondary">
                      {tpl.description}
                    </Typography.Text>
                  )}
                </div>
              }
            />
          </List.Item>
        )}
      />

      {/* Create Template Modal */}
      <Modal
        title="创建公共模板"
        open={createOpen}
        onOk={handleCreate}
        onCancel={() => {
          setCreateOpen(false);
          form.resetFields();
        }}
      >
        <Form form={form} layout="vertical" initialValues={{ type: "rss" }}>
          <Form.Item
            name="name"
            label="名称"
            rules={[{ required: true, message: "请输入名称" }]}
          >
            <Input placeholder="模板名称" />
          </Form.Item>
          <Form.Item
            name="type"
            label="类型"
            rules={[{ required: true }]}
          >
            <Select
              options={[
                { label: "RSS", value: "rss" },
                { label: "API", value: "api" },
              ]}
            />
          </Form.Item>
          <Form.Item
            name="endpoint"
            label="端点 URL"
            rules={[{ required: true, message: "请输入 URL" }]}
          >
            <Input placeholder="https://example.com/feed.xml" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} placeholder="可选描述" />
          </Form.Item>
        </Form>
      </Modal>

      {/* Push Modal */}
      <Modal
        title="推送给用户/组"
        open={!!pushOpen}
        onOk={handlePush}
        onCancel={() => {
          setPushOpen(null);
          pushForm.resetFields();
        }}
      >
        <Form form={pushForm} layout="vertical">
          <Form.Item label="推送目标">
            <Select
              value={pushTargetType}
              onChange={(v) => {
                setPushTargetType(v);
                pushForm.resetFields(["target_ids"]);
              }}
              options={[
                { label: "用户", value: "user" },
                { label: "组", value: "group" },
              ]}
            />
          </Form.Item>
          <Form.Item
            name="target_ids"
            label={pushTargetType === "user" ? "选择用户" : "选择组"}
            rules={[{ required: true, message: "请选择至少一个目标" }]}
          >
            <Select
              mode="multiple"
              placeholder={
                pushTargetType === "user" ? "选择用户" : "选择组"
              }
              options={
                pushTargetType === "user"
                  ? (usersQuery.data?.items ?? []).map((u) => ({
                      label: `${u.display_name} (@${u.username})`,
                      value: u.id,
                    }))
                  : (groupsQuery.data ?? []).map((g) => ({
                      label: `${g.name} (${g.member_count}人)`,
                      value: g.id,
                    }))
              }
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
