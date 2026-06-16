import {
  DeleteOutlined,
  EditOutlined,
  ExperimentOutlined,
  PlusOutlined,
  RocketOutlined,
  RobotOutlined,
} from "@ant-design/icons";
import {
  Alert,
  Button,
  Card,
  Col,
  Divider,
  Form,
  Input,
  Modal,
  Popconfirm,
  Row,
  Select,
  Space,
  Steps,
  Switch,
  Table,
  Tag,
  Typography,
  message,
} from "antd";
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { AuthSession } from "../../shared/api/auth";
import {
  AgentDraft,
  ApiFormat,
  LlmProvider,
  LlmProviderCreate,
  SourceDraft,
  confirmDraft,
  createProvider,
  deleteDraft,
  deleteProvider,
  generateDraft,
  listDrafts,
  listProviders,
} from "../../shared/api/agent";

const { TextArea } = Input;
const { Text, Title, Paragraph } = Typography;

type Props = { session: AuthSession; onCreateSource?: () => void };

export function AgentPage({ session, onCreateSource }: Props) {
  const { t } = useTranslation();
  // ── Provider state ──
  const [providers, setProviders] = useState<LlmProvider[]>([]);
  const [providerModalOpen, setProviderModalOpen] = useState(false);
  const [providerForm] = Form.useForm<LlmProviderCreate>();

  // ── Draft state ──
  const [drafts, setDrafts] = useState<AgentDraft[]>([]);
  const [draftTotal, setDraftTotal] = useState(0);
  const [currentStep, setCurrentStep] = useState(0);
  const [selectedProvider, setSelectedProvider] = useState<string>("");
  const [promptMd, setPromptMd] = useState("");
  const [generating, setGenerating] = useState(false);
  const [currentDraft, setCurrentDraft] = useState<AgentDraft | null>(null);
  const [editedJson, setEditedJson] = useState("");
  const [confirming, setConfirming] = useState(false);
  const [createdSource, setCreatedSource] = useState<{ id: string; name: string; type: string } | null>(null);

  // ── Load data ──

  const loadProviders = useCallback(async () => {
    try {
      const items = await listProviders(session);
      setProviders(items);
      if (items.length > 0 && !selectedProvider) {
        const def = items.find((p) => p.is_default) ?? items[0];
        setSelectedProvider(def.id);
      }
    } catch (e) {
      message.error(`加载 Provider 失败: ${e}`);
    }
  }, [session, selectedProvider]);

  const loadDrafts = useCallback(async () => {
    try {
      const res = await listDrafts(session, 20, 0);
      setDrafts(res.items);
      setDraftTotal(res.total);
    } catch (e) {
      message.error(`加载草稿失败: ${e}`);
    }
  }, [session]);

  useEffect(() => {
    void loadProviders();
    void loadDrafts();
  }, [loadProviders, loadDrafts]);

  // ── Provider actions ──

  const handleCreateProvider = async () => {
    try {
      const values = await providerForm.validateFields();
      await createProvider(session, values);
      message.success("Provider 创建成功");
      setProviderModalOpen(false);
      providerForm.resetFields();
      void loadProviders();
    } catch (e) {
      if (typeof e === "object" && e !== null && "errorFields" in e) return;
      message.error(`创建失败: ${e}`);
    }
  };

  const handleDeleteProvider = async (id: string) => {
    try {
      await deleteProvider(session, id);
      message.success("已删除");
      void loadProviders();
    } catch (e) {
      message.error(`删除失败: ${e}`);
    }
  };

  // ── Draft generation ──

  const handleGenerate = async () => {
    if (!selectedProvider) {
      message.warning("请先选择一个 LLM Provider");
      return;
    }
    if (!promptMd.trim()) {
      message.warning("请输入需求描述");
      return;
    }
    setGenerating(true);
    try {
      const draft = await generateDraft(session, {
        provider_id: selectedProvider,
        prompt_md: promptMd,
      });
      setCurrentDraft(draft);
      setEditedJson(draft.source_draft_json);
      setCurrentStep(1);
      message.success("草稿生成成功");
      void loadDrafts();
    } catch (e) {
      message.error(`生成失败: ${e}`);
    } finally {
      setGenerating(false);
    }
  };

  // ── Confirm draft → create source ──

  const handleConfirm = async () => {
    if (!currentDraft) return;
    setConfirming(true);
    try {
      const result = await confirmDraft(
        session,
        currentDraft.id,
        editedJson,
      );
      message.success(`信息源已创建: ${result.source_name || result.name}`);
      setCreatedSource({
        id: result.source_id || "",
        name: result.source_name || result.name,
        type: result.source_type || result.type,
      });
      setCurrentStep(2);
      void loadDrafts();
      if (onCreateSource) onCreateSource();
    } catch (e) {
      message.error(`确认失败: ${e}`);
    } finally {
      setConfirming(false);
    }
  };

  const handleReset = () => {
    setCurrentStep(0);
    setCurrentDraft(null);
    setEditedJson("");
    setPromptMd("");
    setCreatedSource(null);
  };

  // ── Load existing draft ──

  const handleLoadDraft = (draft: AgentDraft) => {
    setCurrentDraft(draft);
    setEditedJson(draft.source_draft_json);
    setCurrentStep(draft.status === "ready" ? 1 : 0);
    setPromptMd(draft.prompt_md);
    if (providers.length > 0) {
      setSelectedProvider(draft.provider_id);
    }
  };

  const handleDeleteDraft = async (id: string) => {
    try {
      await deleteDraft(session, id);
      message.success("草稿已删除");
      if (currentDraft?.id === id) handleReset();
      void loadDrafts();
    } catch (e) {
      message.error(`删除失败: ${e}`);
    }
  };

  // ── Status tag ──

  const statusTag = (status: string) => {
    const map: Record<string, { color: string; label: string }> = {
      drafting: { color: "processing", label: t("agent.generating") },
      ready: { color: "success", label: t("agent.ready") },
      confirmed: { color: "default", label: t("agent.confirmed") },
      failed: { color: "error", label: "失败" },
    };
    const s = map[status] ?? { color: "default", label: status };
    return <Tag color={s.color}>{s.label}</Tag>;
  };

  // ── API format tag ──

  const formatTag = (fmt: string) => {
    if (fmt === "anthropic") return <Tag color="purple">Anthropic</Tag>;
    return <Tag color="blue">OpenAI</Tag>;
  };

  // ── Example prompts ──

  const examplePrompts = [
    "抓取 V2EX 最新帖子，提取标题和链接",
    "获取 Hacker News 首页 Top 30 的标题、链接和得分",
    "监控 GitHub Trending 仓库，提取仓库名、描述和 Star 数",
    "抓取少数派最新文章，包含标题、摘要和封面图",
  ];

  // ── Render ──

  return (
    <div className="agent-page">
      <Title level={3}>
        <RobotOutlined /> {t("agent.title")}
      </Title>
      <Paragraph type="secondary">
        {t("agent.subtitle")}
      </Paragraph>

      {/* ── Steps ── */}
      <Steps
        current={currentStep}
        items={[
          { title: t("agent.step1"), description: "描述信息源" },
          { title: t("agent.editDraft"), description: "AI 生成" },
          { title: t("agent.complete"), description: "创建信息源" },
        ]}
        style={{ marginBottom: 24 }}
      />

      {/* ── Step 0: Input ── */}
      {currentStep === 0 && (
        <Row gutter={24}>
          <Col span={16}>
            <Card title={t("agent.inputRequirement")}>
              <Form layout="vertical">
                <Form.Item label="LLM Provider">
                  <Space.Compact style={{ width: "100%" }}>
                    <Select
                      value={selectedProvider || undefined}
                      onChange={setSelectedProvider}
                      placeholder="选择 Provider"
                      style={{ flex: 1 }}
                      options={providers.map((p) => ({
                        value: p.id,
                        label: `${p.name} (${p.model}) [${p.api_format === "anthropic" ? "Anthropic" : "OpenAI"}]`,
                      }))}
                    />
                    <Button
                      icon={<PlusOutlined />}
                      onClick={() => setProviderModalOpen(true)}
                    />
                  </Space.Compact>
                </Form.Item>

                <Form.Item label="需求描述 (Markdown)">
                  <TextArea
                    value={promptMd}
                    onChange={(e) => setPromptMd(e.target.value)}
                    rows={8}
                    placeholder={`描述你想要的信息源，例如：\n\n抓取 V2EX 最新帖子\n- URL: https://v2ex.com\n- 提取标题和链接\n- 每次抓取 Top 20`}
                  />
                </Form.Item>

                <Form.Item>
                  <Button
                    type="primary"
                    icon={<ExperimentOutlined />}
                    loading={generating}
                    onClick={handleGenerate}
                    size="large"
                  >
                    {t("agent.generateDraft")}
                  </Button>
                </Form.Item>
              </Form>

              {/* Example prompts */}
              <Divider dashed>快速示例</Divider>
              <Space wrap>
                {examplePrompts.map((ex) => (
                  <Tag
                    key={ex}
                    style={{ cursor: "pointer", marginBottom: 4 }}
                    onClick={() => setPromptMd(ex)}
                  >
                    {ex}
                  </Tag>
                ))}
              </Space>
            </Card>
          </Col>

          <Col span={8}>
            <Card title={t("agent.providerManagement")} size="small">
              {providers.length === 0 ? (
                <Alert
                  message="未配置 Provider"
                  description="请先添加一个 LLM Provider（如 OpenAI、DeepSeek、Claude 等）"
                  type="warning"
                  showIcon
                />
              ) : (
                <Table
                  dataSource={providers}
                  rowKey="id"
                  size="small"
                  pagination={false}
                  columns={[
                    {
                      title: "名称",
                      dataIndex: "name",
                      render: (v, r) => (
                        <Space>
                          {v}
                          {r.is_default && <Tag color="blue">默认</Tag>}
                        </Space>
                      ),
                    },
                    { title: "模型", dataIndex: "model", ellipsis: true },
                    {
                      title: "格式",
                      dataIndex: "api_format",
                      width: 80,
                      render: formatTag,
                    },
                    {
                      title: "",
                      width: 40,
                      render: (_, r) => (
                        <Popconfirm
                          title="确定删除？"
                          onConfirm={() => void handleDeleteProvider(r.id)}
                        >
                          <Button
                            type="text"
                            size="small"
                            danger
                            icon={<DeleteOutlined />}
                          />
                        </Popconfirm>
                      ),
                    },
                  ]}
                />
              )}
              <Button
                type="dashed"
                block
                icon={<PlusOutlined />}
                onClick={() => setProviderModalOpen(true)}
                style={{ marginTop: 8 }}
              >
                {t("agent.addProvider")}
              </Button>
            </Card>
          </Col>
        </Row>
      )}

      {/* ── Step 1: Edit draft ── */}
      {currentStep === 1 && currentDraft && (
        <Row gutter={24}>
          <Col span={14}>
            <Card
              title={t("agent.draftPreview")}
              extra={
                <Space>
                  <Button onClick={handleReset}>{t("agent.reenter")}</Button>
                  <Button
                    type="primary"
                    icon={<RocketOutlined />}
                    loading={confirming}
                    onClick={handleConfirm}
                  >
                    {t("agent.confirmAndCreate")}
                  </Button>
                </Space>
              }
            >
              <Alert
                message="以下是 AI 生成的配置，请检查并编辑后确认"
                type="info"
                showIcon
                style={{ marginBottom: 16 }}
              />
              <TextArea
                value={editedJson}
                onChange={(e) => setEditedJson(e.target.value)}
                rows={16}
                style={{ fontFamily: "monospace", fontSize: 13 }}
              />
            </Card>
          </Col>

          <Col span={10}>
            <Card title="草稿预览" size="small">
              {(() => {
                try {
                  const d: SourceDraft = JSON.parse(editedJson);
                  return (
                    <div>
                      <Paragraph>
                        <strong>名称：</strong> {d.name}
                      </Paragraph>
                      <Paragraph>
                        <strong>类型：</strong>{" "}
                        <Tag
                          color={
                            d.type === "rss"
                              ? "green"
                              : d.type === "api"
                                ? "blue"
                                : "orange"
                          }
                        >
                          {d.type.toUpperCase()}
                        </Tag>
                      </Paragraph>
                      <Paragraph>
                        <strong>端点：</strong>{" "}
                        <Text copyable ellipsis>
                          {d.endpoint}
                        </Text>
                      </Paragraph>
                      {d.config && Object.keys(d.config).length > 0 && (
                        <>
                          <Divider dashed />
                          <Paragraph strong>配置项：</Paragraph>
                          {Object.entries(d.config).map(([k, v]) => (
                            <Paragraph key={k} style={{ marginBottom: 4 }}>
                              <Text code>{k}</Text>: <Text code>{String(v)}</Text>
                            </Paragraph>
                          ))}
                        </>
                      )}
                      {d.schedule_enabled && (
                        <Paragraph>
                          <strong>定时：</strong> 每{" "}
                          {d.schedule_interval_minutes} 分钟
                        </Paragraph>
                      )}
                    </div>
                  );
                } catch {
                  return (
                    <Alert message="JSON 格式错误" type="error" showIcon />
                  );
                }
              })()}
            </Card>

            <Card title={t("agent.originalRequirement")} size="small" style={{ marginTop: 16 }}>
              <Paragraph style={{ whiteSpace: "pre-wrap" }}>
                {currentDraft.prompt_md}
              </Paragraph>
              {currentDraft.llm_tokens_used > 0 && (
                <Text type="secondary">
                  Token: {currentDraft.llm_tokens_used.toLocaleString()} | 模型:{" "}
                  {currentDraft.llm_model}
                </Text>
              )}
            </Card>
          </Col>
        </Row>
      )}

      {/* ── Step 2: Done ── */}
      {currentStep === 2 && (
        <Card>
          <div style={{ textAlign: "center", padding: 40 }}>
            <Title level={2} style={{ color: "#52c41a" }}>
              ✅ 信息源已创建
            </Title>
            {createdSource && (
              <div style={{ marginBottom: 24 }}>
                <Paragraph>
                  <Tag color={createdSource.type === "web" ? "orange" : createdSource.type === "rss" ? "green" : "blue"}>
                    {createdSource.type.toUpperCase()}
                  </Tag>
                  <Text strong style={{ fontSize: 16 }}>{createdSource.name}</Text>
                </Paragraph>
                <Paragraph type="secondary">
                  源 ID: <Text code>{createdSource.id}</Text>
                </Paragraph>
              </div>
            )}
            <Paragraph>
              AI 生成的配置已确认并创建为正式信息源，请前往「信息源」页面查看和管理。
            </Paragraph>
            <Space>
              <Button type="primary" onClick={onCreateSource}>
                查看信息源
              </Button>
              <Button onClick={handleReset}>{t("agent.createNew")}</Button>
            </Space>
          </div>
        </Card>
      )}

      {/* ── Draft history ── */}
      <Divider />
      <Card title={`${t("agent.draftHistoryTab")} (${draftTotal})`} size="small">
        <Table
          dataSource={drafts}
          rowKey="id"
          size="small"
          pagination={{ pageSize: 10 }}
          columns={[
            {
              title: "ID",
              dataIndex: "id",
              width: 100,
              ellipsis: true,
            },
            {
              title: "状态",
              dataIndex: "status",
              width: 80,
              render: statusTag,
            },
            {
              title: "需求",
              dataIndex: "prompt_md",
              ellipsis: true,
            },
            {
              title: "模型",
              dataIndex: "llm_model",
              width: 120,
            },
            {
              title: "Token",
              dataIndex: "llm_tokens_used",
              width: 80,
              render: (v: number) => v.toLocaleString(),
            },
            {
              title: "时间",
              dataIndex: "created_at",
              width: 160,
              render: (v: string) =>
                v ? new Date(v).toLocaleString("zh-CN") : "-",
            },
            {
              title: "",
              width: 80,
              render: (_, r) => (
                <Space>
                  {r.status === "ready" && (
                    <Button
                      type="link"
                      size="small"
                      icon={<EditOutlined />}
                      onClick={() => handleLoadDraft(r)}
                  >
                    {t("agent.edit")}
                  </Button>
                  )}
                  <Popconfirm
                    title="确定删除？"
                    onConfirm={() => void handleDeleteDraft(r.id)}
                  >
                    <Button
                      type="text"
                      size="small"
                      danger
                      icon={<DeleteOutlined />}
                    />
                  </Popconfirm>
                </Space>
              ),
            },
          ]}
        />
      </Card>

      {/* ── Provider modal ── */}
      <Modal
        title="添加 LLM Provider"
        open={providerModalOpen}
        onOk={handleCreateProvider}
        onCancel={() => {
          setProviderModalOpen(false);
          providerForm.resetFields();
        }}
        okText="创建"
        cancelText="取消"
      >
        <Form form={providerForm} layout="vertical" initialValues={{ api_format: "openai", is_default: false }}>
          <Form.Item
            name="name"
            label="名称"
            rules={[{ required: true, message: "请输入名称" }]}
          >
            <Input placeholder="如：MiMo、DeepSeek、Claude" />
          </Form.Item>
          <Form.Item
            name="api_format"
            label="API 格式"
            rules={[{ required: true }]}
          >
            <Select
              options={[
                { value: "openai", label: "OpenAI 兼容 (/v1/chat/completions)" },
                { value: "anthropic", label: "Anthropic (/v1/messages)" },
              ]}
            />
          </Form.Item>
          <Form.Item
            name="base_url"
            label="Base URL"
            rules={[{ required: true, message: "请输入 Base URL" }]}
          >
            <Input placeholder="如：https://api.deepseek.com/v1" />
          </Form.Item>
          <Form.Item
            name="api_key"
            label="API Key"
            rules={[{ required: true, message: "请输入 API Key" }]}
          >
            <Input.Password placeholder="sk-..." />
          </Form.Item>
          <Form.Item
            name="model"
            label="模型"
            rules={[{ required: true, message: "请输入模型名称" }]}
          >
            <Input placeholder="如：deepseek-chat、mimo-v2.5" />
          </Form.Item>
          <Form.Item name="is_default" label="设为默认">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
