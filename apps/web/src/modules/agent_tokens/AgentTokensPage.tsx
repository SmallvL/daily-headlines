import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  CloseCircleOutlined,
  CopyOutlined,
  DeleteOutlined,
  KeyOutlined,
  PlusOutlined,
  WarningOutlined,
} from "@ant-design/icons";
import {
  Alert,
  Button,
  Card,
  Checkbox,
  Col,
  Form,
  Input,
  Modal,
  Popconfirm,
  Row,
  Select,
  Space,
  Table,
  Tag,
  Tooltip,
  Typography,
  message,
} from "antd";
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { AuthSession } from "../../shared/api/auth";
import {
  AgentToken,
  AgentTokenCreate,
  AgentTokenCreated,
  createToken,
  listTokens,
  revokeToken,
} from "../../shared/api/agentTokens";

const { Title, Text, Paragraph } = Typography;

type Props = { session: AuthSession };

const SCOPE_OPTIONS = [
  { label: "Read Feed", value: "read:feed" },
  { label: "Read Sources", value: "read:sources" },
  { label: "Export Data", value: "export:data" },
  { label: "Read Profile", value: "read:profile" },
];

export function AgentTokensPage({ session }: Props) {
  const { t } = useTranslation();
  const [tokens, setTokens] = useState<AgentToken[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm<AgentTokenCreate>();
  const [createdToken, setCreatedToken] = useState<AgentTokenCreated | null>(null);
  const [creating, setCreating] = useState(false);

  const loadTokens = useCallback(async () => {
    try {
      const items = await listTokens(session);
      setTokens(items);
    } catch (e) {
      message.error(`加载 Token 失败: ${e}`);
    } finally {
      setLoading(false);
    }
  }, [session]);

  useEffect(() => {
    void loadTokens();
  }, [loadTokens]);

  const handleCreate = async () => {
    try {
      const values = await form.validateFields();
      setCreating(true);
      const result = await createToken(session, {
        name: values.name,
        scopes: values.scopes || ["read:feed"],
        expires_in_days: values.expires_in_days || 90,
      });
      setCreatedToken(result);
      form.resetFields();
      void loadTokens();
    } catch (e) {
      if (typeof e === "object" && e !== null && "errorFields" in e) return;
      message.error(`创建失败: ${e}`);
    } finally {
      setCreating(false);
    }
  };

  const handleRevoke = async (tokenId: string) => {
    try {
      await revokeToken(session, tokenId);
      message.success("Token 已吊销");
      void loadTokens();
    } catch (e) {
      message.error(`吊销失败: ${e}`);
    }
  };

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      message.success("已复制到剪贴板");
    } catch {
      // Fallback for older browsers
      const textarea = document.createElement("textarea");
      textarea.value = text;
      textarea.style.position = "fixed";
      textarea.style.opacity = "0";
      document.body.appendChild(textarea);
      textarea.select();
      try {
        document.execCommand("copy");
        message.success("已复制到剪贴板");
      } catch {
        message.error("复制失败，请手动复制");
      }
      document.body.removeChild(textarea);
    }
  };

  const statusTag = (record: AgentToken) => {
    if (record.revoked_at) {
      return <Tag icon={<CloseCircleOutlined />} color="error">已吊销</Tag>;
    }
    if (!record.enabled) {
      return <Tag icon={<WarningOutlined />} color="warning">已禁用</Tag>;
    }
    if (record.expires_at && new Date(record.expires_at) < new Date()) {
      return <Tag icon={<ClockCircleOutlined />} color="warning">已过期</Tag>;
    }
    return <Tag icon={<CheckCircleOutlined />} color="success">有效</Tag>;
  };

  const columns = [
    {
      title: "名称",
      dataIndex: "name",
      key: "name",
      render: (v: string, r: AgentToken) => (
        <Space>
          <KeyOutlined />
          <Text strong>{v}</Text>
          {statusTag(r)}
        </Space>
      ),
    },
    {
      title: "Token 前缀",
      dataIndex: "prefix",
      key: "prefix",
      render: (v: string) => <Text code>{v}...</Text>,
    },
    {
      title: "权限",
      dataIndex: "scopes",
      key: "scopes",
      render: (scopes: string[]) => (
        <Space wrap>
          {scopes.map((s) => (
            <Tag key={s} color="blue">{s}</Tag>
          ))}
        </Space>
      ),
    },
    {
      title: "最后使用",
      dataIndex: "last_used_at",
      key: "last_used_at",
      width: 160,
      render: (v: string | null) =>
        v ? new Date(v).toLocaleString("zh-CN") : "从未使用",
    },
    {
      title: "过期时间",
      dataIndex: "expires_at",
      key: "expires_at",
      width: 160,
      render: (v: string | null) =>
        v ? new Date(v).toLocaleDateString("zh-CN") : "永不过期",
    },
    {
      title: "",
      key: "actions",
      width: 60,
      render: (_: unknown, r: AgentToken) => (
        !r.revoked_at ? (
          <Popconfirm
            title="确定吊销此 Token？吊销后立即失效。"
            onConfirm={() => handleRevoke(r.id)}
          >
            <Button type="text" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        ) : null
      ),
    },
  ];

  return (
    <div className="agent-tokens-page">
      <Title level={3}>
        <KeyOutlined /> Agent Token
      </Title>
      <Paragraph type="secondary">
        创建 API Token 供外部 Agent 或脚本访问平台数据。Token 仅在创建时显示一次，请妥善保存。
      </Paragraph>

      <Card
        title={`Token 列表 (${tokens.length})`}
        extra={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setModalOpen(true)}
          >
            创建 Token
          </Button>
        }
      >
        <Table
          dataSource={tokens}
          columns={columns}
          rowKey="id"
          loading={loading}
          pagination={false}
        />
      </Card>

      {/* 创建 Modal */}
      <Modal
        title="创建 Agent Token"
        open={modalOpen}
        onOk={handleCreate}
        onCancel={() => {
          setModalOpen(false);
          setCreatedToken(null);
        }}
        okText="创建"
        cancelText="取消"
        okButtonProps={{ loading: creating }}
        destroyOnHidden
      >
        {createdToken ? (
          <div>
            <Alert
              type="success"
              showIcon
              message="Token 创建成功！"
              description="请立即复制保存此 Token，关闭后将无法再次查看。"
              style={{ marginBottom: 16 }}
            />
            <div style={{ marginBottom: 16 }}>
              <Text strong>Token 名称：</Text>
              <Text>{createdToken.name}</Text>
            </div>
            <div style={{ marginBottom: 16 }}>
              <Text strong>权限：</Text>
              <Space>
                {createdToken.scopes.map((s) => (
                  <Tag key={s} color="blue">{s}</Tag>
                ))}
              </Space>
            </div>
            <div style={{ marginBottom: 16 }}>
              <Text strong>Token：</Text>
              <div style={{
                background: "var(--color-bg-subtle)",
                padding: 12,
                borderRadius: 6,
                fontFamily: "monospace",
                fontSize: 12,
                wordBreak: "break-all",
                marginTop: 8,
              }}>
                {createdToken.token}
                <Tooltip title="复制">
                  <Button
                    type="link"
                    size="small"
                    icon={<CopyOutlined />}
                    onClick={() => copyToClipboard(createdToken.token)}
                  />
                </Tooltip>
              </div>
            </div>
            <Alert
              type="warning"
              showIcon
              message="使用示例"
              description={
                <div style={{ fontFamily: "monospace", fontSize: 12 }}>
                  curl -H "Authorization: Bearer {createdToken.prefix}..." \<br />
                  &nbsp;&nbsp;http://your-host/api/agent-tokens/export
                </div>
              }
            />
          </div>
        ) : (
          <Form form={form} layout="vertical">
            <Form.Item
              name="name"
              label="Token 名称"
              rules={[{ required: true, message: "请输入名称" }]}
            >
              <Input placeholder="如：我的自动化脚本" />
            </Form.Item>
            <Form.Item
              name="scopes"
              label="权限范围"
              rules={[{ required: true, message: "请选择权限" }]}
              initialValue={["read:feed"]}
            >
              <Checkbox.Group options={SCOPE_OPTIONS} />
            </Form.Item>
            <Form.Item
              name="expires_in_days"
              label="有效期（天）"
              initialValue={90}
            >
              <Select
                options={[
                  { label: "30 天", value: 30 },
                  { label: "90 天", value: 90 },
                  { label: "180 天", value: 180 },
                  { label: "365 天", value: 365 },
                ]}
              />
            </Form.Item>
          </Form>
        )}
      </Modal>
    </div>
  );
}
