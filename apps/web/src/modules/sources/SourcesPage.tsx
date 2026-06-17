import {
  ApiOutlined,
  CalendarOutlined,
  CheckOutlined,
  ClockCircleOutlined,
  CloudDownloadOutlined,
  DeleteOutlined,
  EditOutlined,
  ExperimentOutlined,
  FileDoneOutlined,
  GlobalOutlined,
  ImportOutlined,
  KeyOutlined,
  LockOutlined,
  ReloadOutlined,
  SaveOutlined,
  ScanOutlined,
  SearchOutlined,
  SettingOutlined,
  SyncOutlined,
  ThunderboltOutlined
} from "@ant-design/icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  Button,
  Card,
  Col,
  Divider,
  Empty,
  Form,
  Input,
  InputNumber,
  List,
  Modal,
  Row,
  Segmented,
  Select,
  Space,
  Switch,
  Tag,
  Tooltip,
  Typography,
  message
} from "antd";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { AuthSession } from "../../shared/api/auth";
import {
  Source,
  SourcePayload,
  SourceTemplate,
  AuthType,
  createSource,
  deleteSource,
  exportSourceTemplate,
  fetchSourceNow,
  importSourceTemplate,
  listSourceFetchLogs,
  listSources,
  testSource,
  updateSource,
  updateSourceSchedule
} from "../../shared/api/sources";
import { relativeTime } from "../../shared/utils/time";
import { PluginSelector, QRCodeLogin } from "../../features/plugins";
import { pluginsApi } from "../../features/plugins/api";

type SourcesPageProps = {
  session: AuthSession;
};

type ScheduleFormValues = SourcePayload & {
  interval_value?: number;
  interval_unit?: string;
  cron_days?: number[];
};

const DAY_LABELS = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"];

const STATUS_COLORS: Record<string, string> = {
  active: "green",
  error: "red",
  disabled: "default",
  pending: "orange"
};

const STATUS_LABELS: Record<string, string> = {
  active: "正常",
  error: "异常",
  disabled: "已禁用",
  pending: "待验证"
};

function formatScheduleLabel(source: Source): string {
  if (!source.schedule_enabled) return "手动抓取";
  if (source.schedule_mode === "cron") {
    const hour = String(source.cron_hour ?? 0).padStart(2, "0");
    const minute = String(source.cron_minute ?? 0).padStart(2, "0");
    const timeStr = `${hour}:${minute}`;
    if (source.cron_days_of_week) {
      const days = source.cron_days_of_week
        .split(",")
        .map((d) => DAY_LABELS[Number(d.trim())] ?? "");
      return `${days.join("/")} ${timeStr}`;
    }
    return `每天 ${timeStr}`;
  }
  const mins = source.schedule_interval_minutes ?? 60;
  if (mins >= 1440 && mins % 1440 === 0) return `每 ${mins / 1440} 天`;
  if (mins >= 60 && mins % 60 === 0) return `每 ${mins / 60} 小时`;
  return `每 ${mins} 分钟`;
}

export function SourcesPage({ session }: SourcesPageProps) {
  const { t } = useTranslation();
  const [form] = Form.useForm<ScheduleFormValues>();
  const [previewTitle, setPreviewTitle] = useState<string | null>(null);
  const [previewItems, setPreviewItems] = useState<Array<{ id: string; title: string; url: string | null }>>([]);
  const [fetchingSourceId, setFetchingSourceId] = useState<string | null>(null);
  const [deletingSourceId, setDeletingSourceId] = useState<string | null>(null);
  const [updatingScheduleSourceId, setUpdatingScheduleSourceId] = useState<string | null>(null);
  const [editingSource, setEditingSource] = useState<Source | null>(null);
  const [editingSourceId, setEditingSourceId] = useState<string | null>(null);
  const [showQRCodeModal, setShowQRCodeModal] = useState(false);
  const [pluginCredentials, setPluginCredentials] = useState<Record<string, any> | null>(null);
  const [selectedPluginId, setSelectedPluginId] = useState<string>("");
  const [cookieChecking, setCookieChecking] = useState(false);
  const [cookieCheckResult, setCookieCheckResult] = useState<string>("");
  const sourceType = Form.useWatch("type", form) ?? "rss";
  const scheduleEnabled = Form.useWatch("schedule_enabled", form) ?? false;
  const scheduleMode = Form.useWatch("schedule_mode", form) ?? "interval";
  const authType = Form.useWatch(["auth", "auth_type"], form) ?? "none";
  const intervalValue = Form.useWatch("interval_value", form) ?? 1;
  const intervalUnit = Form.useWatch("interval_unit", form) ?? "hours";
  const queryClient = useQueryClient();
  const [messageApi, contextHolder] = message.useMessage();

  const sourcesQuery = useQuery({
    queryKey: ["sources"],
    queryFn: () => listSources(session)
  });
  const firstSourceId = sourcesQuery.data?.[0]?.id;
  const fetchLogsQuery = useQuery({
    queryKey: ["source-fetch-logs", firstSourceId],
    queryFn: () => listSourceFetchLogs(session, firstSourceId ?? ""),
    enabled: Boolean(firstSourceId)
  });

  const testMutation = useMutation({
    mutationFn: (payload: SourcePayload) => testSource(session, payload),
    onSuccess: (result) => {
      setPreviewTitle(result.title);
      setPreviewItems(result.items.map((item) => ({ id: item.id, title: item.title, url: item.url })));
      messageApi.success("预览成功");
    },
    onError: (error) => messageApi.error(error instanceof Error ? error.message : "预览失败")
  });

  const createMutation = useMutation({
    mutationFn: (payload: SourcePayload) => createSource(session, payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["sources"] });
      messageApi.success("信息源已保存");
    },
    onError: (error) => messageApi.error(error instanceof Error ? error.message : "保存失败")
  });

  const fetchMutation = useMutation({
    mutationFn: (sourceId: string) => fetchSourceNow(session, sourceId),
    onSuccess: async (result) => {
      await queryClient.invalidateQueries({ queryKey: ["feed-items"] });
      await queryClient.invalidateQueries({ queryKey: ["sources"] });
      await queryClient.invalidateQueries({ queryKey: ["source-fetch-logs"] });
      messageApi.success(`抓取完成，新增 ${result.inserted} 条，跳过 ${result.skipped} 条`);
    },
    onError: (error) => messageApi.error(error instanceof Error ? error.message : "抓取失败"),
    onSettled: () => setFetchingSourceId(null)
  });

  const deleteMutation = useMutation({
    mutationFn: (sourceId: string) => deleteSource(session, sourceId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["sources"] });
      await queryClient.invalidateQueries({ queryKey: ["feed-items"] });
      messageApi.success("信息源已删除");
    },
    onError: (error) => messageApi.error(error instanceof Error ? error.message : "删除失败"),
    onSettled: () => setDeletingSourceId(null)
  });

  const scheduleMutation = useMutation({
    mutationFn: (payload: {
      sourceId: string;
      schedulePayload: Parameters<typeof updateSourceSchedule>[2];
    }) =>
      updateSourceSchedule(
        session,
        payload.sourceId,
        payload.schedulePayload
      ),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["sources"] });
      messageApi.success("定时设置已更新");
    },
    onError: (error) => messageApi.error(error instanceof Error ? error.message : "更新失败"),
    onSettled: () => setUpdatingScheduleSourceId(null)
  });

  const updateMutation = useMutation({
    mutationFn: (payload: { sourceId: string; data: Partial<Pick<SourcePayload, "name" | "type" | "endpoint" | "config">> }) =>
      updateSource(session, payload.sourceId, payload.data),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["sources"] });
      setEditingSource(null);
      setEditingSourceId(null);
      form.resetFields();
      messageApi.success("信息源已更新");
    },
    onError: (error) => messageApi.error(error instanceof Error ? error.message : "更新失败"),
    onSettled: () => setEditingSourceId(null)
  });

  async function handleExportTemplate(sourceId: string, sourceName: string) {
    try {
      const template = await exportSourceTemplate(session, sourceId);
      const blob = new Blob([JSON.stringify(template, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `source-template-${sourceName}.json`;
      a.click();
      URL.revokeObjectURL(url);
      messageApi.success("模板已导出");
    } catch (e) {
      messageApi.error(e instanceof Error ? e.message : "导出失败");
    }
  }

  function handleImportTemplate() {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".json";
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;
      try {
        const text = await file.text();
        const template: SourceTemplate = JSON.parse(text);
        if (!template.name || !template.type || !template.endpoint) {
          throw new Error("模板格式无效：缺少 name/type/endpoint");
        }
        await importSourceTemplate(session, template);
        await queryClient.invalidateQueries({ queryKey: ["sources"] });
        messageApi.success(`已导入信息源：${template.name}`);
      } catch (err) {
        messageApi.error(err instanceof Error ? err.message : "导入失败");
      }
    };
    input.click();
  }

  function handleStartEdit(source: Source) {
    setEditingSource(source);
    setEditingSourceId(source.id);
    form.setFieldsValue({
      name: source.name,
      type: source.type as SourcePayload["type"],
      endpoint: source.endpoint,
    });
  }

  async function getPayload(): Promise<SourcePayload> {
    const values = await form.validateFields();

    // Build auth config
    const authConfig = values.auth || { auth_type: "none" };

    // If using plugin auth, include plugin credentials
    if (authConfig.auth_type === "qrcode" && pluginCredentials) {
      authConfig.plugin_credentials = pluginCredentials;
    }

    if (values.type === "api") {
      return {
        ...values,
        auth: authConfig,
        config: {
          title_path: values.config?.title_path,
          items_path: values.config?.items_path,
          mappings: values.config?.mappings ?? {}
        }
      };
    }
    if (values.type === "web") {
      const allowedDomains = typeof values.config?.allowed_domains === "string"
        ? (values.config.allowed_domains as string).split(",").map((d: string) => d.trim()).filter(Boolean)
        : values.config?.allowed_domains ?? [];
      return {
        ...values,
        auth: authConfig,
        config: {
          selector_type: values.config?.selector_type ?? "css",
          item_selector: values.config?.item_selector ?? "",
          title_selector: values.config?.title_selector,
          url_selector: values.config?.url_selector,
          summary_selector: values.config?.summary_selector,
          image_selector: values.config?.image_selector,
          author_selector: values.config?.author_selector,
          date_selector: values.config?.date_selector,
          allowed_domains: allowedDomains
        }
      };
    }
    return { ...values, type: "rss", config: {}, auth: authConfig };
  }

  function buildScheduleSummary(): string {
    const enabled = form.getFieldValue("schedule_enabled") ?? false;
    if (!enabled) return "未启用";
    const mode = form.getFieldValue("schedule_mode") ?? "interval";
    if (mode === "interval") {
      const value = form.getFieldValue("interval_value") ?? 1;
      const unit = form.getFieldValue("interval_unit") ?? "minutes";
      const unitLabel = unit === "minutes" ? "分钟" : unit === "hours" ? "小时" : "天";
      return `每 ${value} ${unitLabel}自动抓取一次`;
    }
    // cron mode
    const days: number[] = form.getFieldValue("cron_days") ?? [];
    const hour = String(form.getFieldValue("cron_hour") ?? 8).padStart(2, "0");
    const minute = String(form.getFieldValue("cron_minute") ?? 0).padStart(2, "0");
    const timeStr = `${hour}:${minute}`;
    if (days.length === 0) {
      return `每天 ${timeStr} 自动抓取`;
    }
    const dayNames = days.sort((a, b) => a - b).map((d) => DAY_LABELS[d]);
    return `${dayNames.join("、")} ${timeStr} 自动抓取`;
  }

  function buildSchedulePayload() {
    const enabled = form.getFieldValue("schedule_enabled") ?? false;
    const mode = form.getFieldValue("schedule_mode") ?? "interval";
    if (!enabled) {
      return {
        schedule_enabled: false,
        schedule_mode: "interval" as const,
        schedule_interval_minutes: null,
        cron_expression: null,
        cron_days_of_week: null,
        cron_hour: null,
        cron_minute: null,
      };
    }
    if (mode === "cron") {
      const selectedDays: number[] = form.getFieldValue("cron_days") ?? [];
      const daysStr = selectedDays.length > 0
        ? selectedDays.sort((a: number, b: number) => a - b).join(",")
        : null;
      return {
        schedule_enabled: true,
        schedule_mode: "cron" as const,
        schedule_interval_minutes: null,
        cron_expression: null,
        cron_days_of_week: daysStr,
        cron_hour: form.getFieldValue("cron_hour") ?? 8,
        cron_minute: form.getFieldValue("cron_minute") ?? 0,
      };
    }
    const intervalValue = form.getFieldValue("interval_value") ?? 1;
    const intervalUnit = form.getFieldValue("interval_unit") ?? "minutes";
    let minutes = intervalValue;
    if (intervalUnit === "hours") minutes = intervalValue * 60;
    if (intervalUnit === "days") minutes = intervalValue * 1440;
    return {
      schedule_enabled: true,
      schedule_mode: "interval" as const,
      schedule_interval_minutes: Math.max(5, minutes),
      cron_expression: null,
      cron_days_of_week: null,
      cron_hour: null,
      cron_minute: null,
    };
  }

  const sourceTypeIcon = (type: string) => {
    switch (type) {
      case "rss": return <ApiOutlined />;
      case "api": return <CloudDownloadOutlined />;
      case "web": return <GlobalOutlined />;
      default: return <ApiOutlined />;
    }
  };

  const sourceTypeLabel = (type: string) => {
    switch (type) {
      case "rss": return "RSS";
      case "api": return "JSON API";
      case "web": return "网页爬虫";
      default: return type;
    }
  };

  const authTypeLabel = (type: AuthType) => {
    switch (type) {
      case "cookie": return "Cookie";
      case "bearer": return "Bearer Token";
      case "api_key": return "API Key";
      case "custom_headers": return "自定义 Header";
      case "qrcode": return "扫码登录";
      case "plugin": return "插件认证";
      default: return "已认证";
    }
  };

  return (
    <div className="sources-page">
      {contextHolder}

      {/* ── Add / Edit Form ── */}
      <section className="source-form-section">
        <div className="source-section-header">
          <div>
            <Typography.Title level={4} style={{ marginBottom: 4 }}>
              {editingSource ? t("sources.edit") : t("sources.create")}
            </Typography.Title>
            <Typography.Text type="secondary">
              {t("sources.subtitle")}
            </Typography.Text>
          </div>
          <Button icon={<ImportOutlined />} onClick={handleImportTemplate}>
            {t("sources.import")}
          </Button>
        </div>

        <Card className="source-form-card" styles={{ body: { padding: "20px 24px" } }}>
          <Form<ScheduleFormValues>
            form={form}
            layout="vertical"
            initialValues={{
              name: "示例 RSS",
              type: "rss",
              endpoint: "https://hnrss.org/frontpage",
              auth: {
                auth_type: "none",
              },
              schedule_enabled: false,
              schedule_mode: "interval",
              schedule_interval_minutes: 60,
              interval_value: 1,
              interval_unit: "hours",
              cron_days: [],
              cron_hour: 8,
              cron_minute: 0,
              config: {
                items_path: "",
                mappings: {
                  id: "id",
                  title: "title",
                  url: "url",
                  summary: "summary",
                  author: "author",
                  published_at: "published_at",
                  image_url: "image_url"
                }
              }
            }}
            className="source-form"
          >
            {/* Type Selector */}
            <Form.Item label="类型" name="type">
              <Segmented
                block
                options={[
                  { label: <Space><ApiOutlined /> RSS</Space>, value: "rss" },
                  { label: <Space><CloudDownloadOutlined /> JSON API</Space>, value: "api" },
                  { label: <Space><GlobalOutlined /> 网页爬虫</Space>, value: "web" }
                ]}
              />
            </Form.Item>

            <Row gutter={16}>
              <Col span={8}>
                <Form.Item label="名称" name="name" rules={[{ required: true, message: "请输入名称" }]}>
                  <Input prefix={<SearchOutlined />} placeholder="例如：Hacker News" />
                </Form.Item>
              </Col>
              <Col span={16}>
                <Form.Item
                  label={sourceType === "api" ? "API 地址" : sourceType === "web" ? "网页地址" : "RSS 地址"}
                  name="endpoint"
                  rules={[{ required: true, message: "请输入地址" }]}
                >
                  <Input
                    prefix={sourceType === "web" ? <GlobalOutlined /> : <ApiOutlined />}
                    placeholder={sourceType === "api" ? "https://example.com/api/news" : sourceType === "web" ? "https://example.com/news" : "https://example.com/feed.xml"}
                  />
                </Form.Item>
              </Col>
            </Row>

            {/* ── Auth Section ── */}
            <Divider orientation="left" plain>
              <Space>
                <LockOutlined />
                认证配置
              </Space>
            </Divider>

            <div className="auth-config-section">
              <Form.Item label="认证方式" name={["auth", "auth_type"]}>
                <Segmented
                  block
                  options={[
                    { label: "无需认证", value: "none" },
                    { label: "Cookie", value: "cookie" },
                    { label: "Bearer Token", value: "bearer" },
                    { label: "API Key", value: "api_key" },
                    { label: "自定义 Header", value: "custom_headers" },
                    { label: <Space><ScanOutlined /> 扫码登录</Space>, value: "qrcode" }
                  ]}
                />
              </Form.Item>

              {authType === "qrcode" && (
                <div style={{ marginBottom: 24 }}>
                  <div style={{ marginBottom: 12 }}>
                    <Typography.Text strong>选择平台</Typography.Text>
                  </div>
                  <PluginSelector
                    session={session}
                    value={selectedPluginId}
                    onChange={(pluginId) => {
                      setSelectedPluginId(pluginId);
                      form.setFieldsValue({ auth: { ...form.getFieldValue("auth"), plugin_id: pluginId } });
                    }}
                    showAuthMethods={false}
                  />

                  {selectedPluginId && (
                    <Button
                      type="primary"
                      icon={<ScanOutlined />}
                      onClick={() => setShowQRCodeModal(true)}
                      style={{ width: "100%", marginTop: 16 }}
                    >
                      扫码登录
                    </Button>
                  )}
                </div>
              )}

              {authType === "cookie" && (
                <Form.Item label="Cookie">
                  <Input.TextArea
                    placeholder="从浏览器复制 Cookie，例如：SESSDATA=xxx; bili_jct=xxx"
                    rows={3}
                    style={{ fontFamily: "monospace", fontSize: 12 }}
                    onChange={(e) => {
                      form.setFieldValue(["auth", "cookies"], e.target.value);
                      setCookieCheckResult("");
                    }}
                  />
                  <Button
                    size="small"
                    style={{ marginTop: 8 }}
                    loading={cookieChecking}
                    onClick={async () => {
                      const cookie = form.getFieldValue(["auth", "cookies"]);
                      if (!cookie) return;
                      setCookieChecking(true);
                      setCookieCheckResult("");
                      try {
                        const result = await pluginsApi.initAuth(session, selectedPluginId || "bilibili", "cookie", { cookie_string: cookie });
                        if (result.success && result.user_info) {
                          setCookieCheckResult(`已登录 ✓ ${result.user_info.username || result.user_info.uname || ""}`);
                        } else {
                          setCookieCheckResult("Cookie 无效或已过期");
                        }
                      } catch {
                        setCookieCheckResult("检测失败，请稍后重试");
                      } finally {
                        setCookieChecking(false);
                      }
                    }}
                  >
                    检测登录
                  </Button>
                  {cookieCheckResult && (
                    <Typography.Text type={cookieCheckResult.includes("✓") ? "success" : "secondary"} style={{ fontSize: 12, display: "block", marginTop: 4 }}>
                      {cookieCheckResult}
                    </Typography.Text>
                  )}
                </Form.Item>
              )}

              {authType === "bearer" && (
                <Form.Item label="Bearer Token" name={["auth", "token"]}>
                  <Input.Password
                    prefix={<KeyOutlined />}
                    placeholder="输入 Bearer Token"
                  />
                </Form.Item>
              )}

              {authType === "api_key" && (
                <>
                  <Form.Item label="Header 名称" name={["auth", "header_name"]}>
                    <Input placeholder="X-API-Key" />
                  </Form.Item>
                  <Form.Item label="API Key" name={["auth", "api_key"]}>
                    <Input.Password
                      prefix={<KeyOutlined />}
                      placeholder="输入 API Key"
                    />
                  </Form.Item>
                </>
              )}

              {authType === "custom_headers" && (
                <Form.Item label="自定义 Headers (JSON)" name={["auth", "headers"]}>
                  <Input.TextArea
                    placeholder={'{"Authorization": "Bearer xxx", "X-Custom": "value"}'}
                    rows={3}
                    style={{ fontFamily: "monospace", fontSize: 12 }}
                  />
                </Form.Item>
              )}

              <Alert
                message="认证说明"
                description={
                  <ul style={{ margin: 0, paddingLeft: 20 }}>
                    <li><strong>Cookie</strong>: 从浏览器开发者工具复制 Cookie，用于需要登录的网站（如 Bilibili）</li>
                    <li><strong>Bearer Token</strong>: 用于 OAuth2 认证的 API</li>
                    <li><strong>API Key</strong>: 用于需要 API Key 的服务</li>
                    <li><strong>自定义 Header</strong>: 用于需要特殊 Header 的 API</li>
                  </ul>
                }
                type="info"
                showIcon
                style={{ marginTop: 8 }}
              />
            </div>

            {/* ── Schedule Section ── */}
            <Divider orientation="left" plain>
              <Space>
                <ClockCircleOutlined />
                定时抓取
              </Space>
            </Divider>

            <div className={`schedule-panel ${scheduleEnabled ? "schedule-panel-active" : ""}`}>
              <div className="schedule-panel-header">
                <div className="schedule-panel-header-left">
                  <div className={`schedule-status-dot ${scheduleEnabled ? "active" : ""}`} />
                  <div>
                    <Typography.Text strong style={{ fontSize: 14 }}>
                      {scheduleEnabled ? "自动抓取已启用" : "自动抓取已关闭"}
                    </Typography.Text>
                    <Typography.Text type="secondary" style={{ display: "block", fontSize: 12 }}>
                      {scheduleEnabled
                        ? "系统将按照设定的时间自动抓取内容"
                        : "开启后系统将定期自动抓取最新内容"
                      }
                    </Typography.Text>
                  </div>
                </div>
                <Form.Item name="schedule_enabled" valuePropName="checked" style={{ marginBottom: 0 }}>
                  <Switch
                    checkedChildren={<CheckOutlined />}
                    unCheckedChildren="OFF"
                  />
                </Form.Item>
              </div>

              {scheduleEnabled ? (
                <div className="schedule-panel-body">
                  {/* Mode Selector */}
                  <div className="schedule-mode-tabs">
                    <div
                      className={`schedule-mode-tab ${scheduleMode === "interval" ? "active" : ""}`}
                      onClick={() => form.setFieldsValue({ schedule_mode: "interval" })}
                    >
                      <ThunderboltOutlined />
                      <span>间隔模式</span>
                      <Typography.Text type="secondary" style={{ fontSize: 11 }}>固定间隔重复</Typography.Text>
                    </div>
                    <div
                      className={`schedule-mode-tab ${scheduleMode === "cron" ? "active" : ""}`}
                      onClick={() => form.setFieldsValue({ schedule_mode: "cron" })}
                    >
                      <CalendarOutlined />
                      <span>定时模式</span>
                      <Typography.Text type="secondary" style={{ fontSize: 11 }}>指定日期和时间</Typography.Text>
                    </div>
                    <Form.Item name="schedule_mode" noStyle>
                      <input type="hidden" />
                    </Form.Item>
                  </div>

                  {scheduleMode === "interval" ? (
                    <div className="schedule-interval-body">
                      {/* Quick Presets */}
                      <div className="schedule-presets">
                        <Typography.Text type="secondary" style={{ fontSize: 12, marginBottom: 6, display: "block" }}>
                          快捷选择
                        </Typography.Text>
                        <div className="schedule-presets-grid">
                          {[
                            { label: "5 分钟", value: 5, unit: "minutes" },
                            { label: "15 分钟", value: 15, unit: "minutes" },
                            { label: "30 分钟", value: 30, unit: "minutes" },
                            { label: "1 小时", value: 1, unit: "hours" },
                            { label: "2 小时", value: 2, unit: "hours" },
                            { label: "6 小时", value: 6, unit: "hours" },
                            { label: "12 小时", value: 12, unit: "hours" },
                            { label: "1 天", value: 1, unit: "days" },
                          ].map((preset) => {
                            const isActive = intervalValue === preset.value && intervalUnit === preset.unit;
                            return (
                              <div
                                key={`${preset.value}-${preset.unit}`}
                                className={`schedule-preset-btn ${isActive ? "active" : ""}`}
                                onClick={() => {
                                  form.setFieldsValue({
                                    interval_value: preset.value,
                                    interval_unit: preset.unit,
                                  });
                                }}
                              >
                                {isActive && <CheckOutlined style={{ fontSize: 10 }} />}
                                {preset.label}
                              </div>
                            );
                          })}
                        </div>
                      </div>

                      {/* Custom Input */}
                      <div className="schedule-custom-interval">
                        <Typography.Text type="secondary" style={{ fontSize: 12, marginBottom: 6, display: "block" }}>
                          自定义间隔
                        </Typography.Text>
                        <Space align="center">
                          <span style={{ color: "var(--ant-color-text-secondary)", fontSize: 13 }}>每</span>
                          <Form.Item name="interval_value" noStyle rules={[{ required: true }]}>
                            <InputNumber min={1} max={10080} style={{ width: 80 }} size="small" />
                          </Form.Item>
                          <Form.Item name="interval_unit" noStyle>
                            <Select
                              style={{ width: 80 }}
                              size="small"
                              options={[
                                { label: "分钟", value: "minutes" },
                                { label: "小时", value: "hours" },
                                { label: "天", value: "days" }
                              ]}
                            />
                          </Form.Item>
                          <span style={{ color: "var(--ant-color-text-secondary)", fontSize: 13 }}>抓取一次</span>
                        </Space>
                      </div>
                    </div>
                  ) : (
                    <div className="schedule-cron-body">
                      {/* Day of Week */}
                      <div className="schedule-days">
                        <Typography.Text type="secondary" style={{ fontSize: 12, marginBottom: 8, display: "block" }}>
                          重复日 <span style={{ fontSize: 11, opacity: 0.7 }}>（不选则每天）</span>
                        </Typography.Text>
                        <Form.Item name="cron_days" noStyle>
                          <div className="schedule-day-btns">
                            {[
                              { value: 1, short: "一", full: "周一" },
                              { value: 2, short: "二", full: "周二" },
                              { value: 3, short: "三", full: "周三" },
                              { value: 4, short: "四", full: "周四" },
                              { value: 5, short: "五", full: "周五" },
                              { value: 6, short: "六", full: "周六" },
                              { value: 0, short: "日", full: "周日" },
                            ].map((day) => {
                              const cronDays: number[] = form.getFieldValue("cron_days") ?? [];
                              const isActive = cronDays.includes(day.value);
                              return (
                                <div
                                  key={day.value}
                                  className={`schedule-day-btn ${isActive ? "active" : ""} ${day.value === 0 || day.value === 6 ? "weekend" : ""}`}
                                  onClick={() => {
                                    const current: number[] = form.getFieldValue("cron_days") ?? [];
                                    const next = current.includes(day.value)
                                      ? current.filter((d) => d !== day.value)
                                      : [...current, day.value].sort((a, b) => a - b);
                                    form.setFieldsValue({ cron_days: next });
                                  }}
                                >
                                  {day.short}
                                </div>
                              );
                            })}
                          </div>
                        </Form.Item>
                      </div>

                      {/* Time Picker */}
                      <div className="schedule-time">
                        <Typography.Text type="secondary" style={{ fontSize: 12, marginBottom: 8, display: "block" }}>
                          执行时间
                        </Typography.Text>
                        <div className="schedule-time-inputs">
                          <div className="schedule-time-display">
                            <ClockCircleOutlined style={{ fontSize: 16, color: "var(--ant-color-primary)" }} />
                            <Form.Item name="cron_hour" noStyle>
                              <InputNumber
                                min={0}
                                max={23}
                                style={{ width: 56 }}
                                size="small"
                                formatter={(v) => String(v ?? 0).padStart(2, "0")}
                                parser={(v) => Number(v?.replace(/^0/, "") ?? 0) as unknown as 0}
                              />
                            </Form.Item>
                            <span className="schedule-time-colon">:</span>
                            <Form.Item name="cron_minute" noStyle>
                              <InputNumber
                                min={0}
                                max={59}
                                style={{ width: 56 }}
                                size="small"
                                formatter={(v) => String(v ?? 0).padStart(2, "0")}
                                parser={(v) => Number(v?.replace(/^0/, "") ?? 0) as unknown as 0}
                              />
                            </Form.Item>
                          </div>
                          {/* Quick time presets */}
                          <div className="schedule-time-presets">
                            {[
                              { label: "早8点", h: 8, m: 0 },
                              { label: "午12点", h: 12, m: 0 },
                              { label: "晚6点", h: 18, m: 0 },
                              { label: "午夜", h: 0, m: 0 },
                            ].map((tp) => (
                              <div
                                key={tp.label}
                                className="schedule-time-preset"
                                onClick={() => {
                                  form.setFieldsValue({ cron_hour: tp.h, cron_minute: tp.m });
                                }}
                              >
                                {tp.label}
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Schedule Summary */}
                  <div className="schedule-summary">
                    <SyncOutlined style={{ fontSize: 13 }} />
                    <span>{buildScheduleSummary()}</span>
                  </div>
                </div>
              ) : null}
            </div>

            {/* ── Source Config ── */}
            {sourceType !== "rss" ? (
              <>
                <Divider orientation="left" plain>
                  <Space>
                    <SettingOutlined />
                    {sourceType === "api" ? "API 配置" : "爬虫配置"}
                  </Space>
                </Divider>

                {sourceType === "api" ? (
                  <div className="api-mapping-grid">
                    <Form.Item label="数组路径" name={["config", "items_path"]}>
                      <Input placeholder="例如：data.items；根数组可留空" />
                    </Form.Item>
                    <Form.Item label="标题路径" name={["config", "mappings", "title"]}>
                      <Input placeholder="title" />
                    </Form.Item>
                    <Form.Item label="链接路径" name={["config", "mappings", "url"]}>
                      <Input placeholder="url" />
                    </Form.Item>
                    <Form.Item label="摘要路径" name={["config", "mappings", "summary"]}>
                      <Input placeholder="summary" />
                    </Form.Item>
                    <Form.Item label="唯一 ID 路径" name={["config", "mappings", "id"]}>
                      <Input placeholder="id" />
                    </Form.Item>
                    <Form.Item label="发布时间路径" name={["config", "mappings", "published_at"]}>
                      <Input placeholder="published_at" />
                    </Form.Item>
                  </div>
                ) : (
                  <div className="api-mapping-grid">
                    <Form.Item label="选择器类型" name={["config", "selector_type"]} initialValue="css">
                      <Segmented
                        options={[
                          { label: "CSS", value: "css" },
                          { label: "XPath", value: "xpath" }
                        ]}
                      />
                    </Form.Item>
                    <Form.Item
                      label="列表项选择器"
                      name={["config", "item_selector"]}
                      rules={[{ required: true, message: "请输入列表项选择器" }]}
                    >
                      <Input placeholder="CSS: .news-item | XPath: //div[@class='item']" />
                    </Form.Item>
                    <Form.Item label="标题选择器" name={["config", "title_selector"]}>
                      <Input placeholder="CSS: h2.title | XPath: .//h2" />
                    </Form.Item>
                    <Form.Item label="链接选择器" name={["config", "url_selector"]}>
                      <Input placeholder="CSS: a.title-link | XPath: .//a/@href" />
                    </Form.Item>
                    <Form.Item label="摘要选择器" name={["config", "summary_selector"]}>
                      <Input placeholder="CSS: p.summary | XPath: .//p" />
                    </Form.Item>
                    <Form.Item label="图片选择器" name={["config", "image_selector"]}>
                      <Input placeholder="CSS: img.thumb | XPath: .//img/@src" />
                    </Form.Item>
                    <Form.Item label="作者选择器" name={["config", "author_selector"]}>
                      <Input placeholder="CSS: span.author | XPath: .//span[@class='author']" />
                    </Form.Item>
                    <Form.Item label="日期选择器" name={["config", "date_selector"]}>
                      <Input placeholder="CSS: time.date | XPath: .//time/@datetime" />
                    </Form.Item>
                    <Form.Item label="允许的域名" name={["config", "allowed_domains"]} className="full-width">
                      <Input placeholder="逗号分隔，如：news.ycombinator.com, github.com" />
                    </Form.Item>
                  </div>
                )}
              </>
            ) : null}

            {/* Actions */}
            <Divider style={{ margin: "12px 0 16px" }} />
            <Space wrap>
              <Button
                icon={<ExperimentOutlined />}
                loading={testMutation.isPending}
                onClick={() => getPayload().then((payload) => testMutation.mutate(payload))}
              >
                {t("sources.testPreview")}
              </Button>
              <Button
                type="primary"
                icon={<SaveOutlined />}
                loading={createMutation.isPending || updateMutation.isPending}
                onClick={() => {
                  getPayload().then((payload) => {
                    if (editingSourceId) {
                      updateMutation.mutate({ sourceId: editingSourceId, data: payload });
                    } else {
                      createMutation.mutate(payload);
                    }
                  });
                }}
              >
                {editingSourceId ? t("sources.updateSource") : t("sources.saveSource")}
              </Button>
              {editingSourceId ? (
                <Button
                  onClick={() => {
                    setEditingSource(null);
                    setEditingSourceId(null);
                    form.resetFields();
                  }}
                >
                  {t("sources.cancelEdit")}
                </Button>
              ) : null}
            </Space>
          </Form>
        </Card>
      </section>

      {/* ── Preview ── */}
      {previewItems.length > 0 ? (
        <Alert
          type="success"
          showIcon
          icon={<SearchOutlined />}
          message={previewTitle ? t("sources.preview") + "：" + previewTitle : t("sources.preview")}
          description={
            <List
              size="small"
              dataSource={previewItems}
              renderItem={(item, index) => (
                <List.Item style={{ padding: "6px 0" }}>
                  <Typography.Text type="secondary" style={{ marginRight: 8, fontSize: 12, minWidth: 20 }}>
                    {index + 1}.
                  </Typography.Text>
                  {item.url ? <a href={item.url} target="_blank" rel="noreferrer">{item.title}</a> : item.title}
                </List.Item>
              )}
            />
          }
          style={{ marginBottom: 0 }}
        />
      ) : null}

      {/* ── Source List ── */}
      <section className="source-list-section">
        <div className="source-section-header">
          <div>
            <Typography.Title level={4} style={{ marginBottom: 4 }}>{t("sources.mySources")}</Typography.Title>
            <Typography.Text type="secondary">
              {t("sources.count", { count: sourcesQuery.data?.length ?? 0 })}
            </Typography.Text>
          </div>
        </div>

        {sourcesQuery.isLoading ? (
          <Card loading style={{ height: 120 }} />
        ) : (sourcesQuery.data?.length ?? 0) === 0 ? (
          <Card>
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description={t("sources.empty")}
            >
              <Button type="primary" icon={<ImportOutlined />} onClick={handleImportTemplate}>
                {t("sources.import")}
              </Button>
            </Empty>
          </Card>
        ) : (
          <div className="source-cards-grid">
            {sourcesQuery.data!.map((source) => (
              <Card
                key={source.id}
                className={`source-card ${editingSourceId === source.id ? "source-card-editing" : ""}`}
                styles={{ body: { padding: "16px 20px" } }}
              >
                <div className="source-card-header">
                  <div className="source-card-title-row">
                    <Space size={8}>
                      {sourceTypeIcon(source.type)}
                      <Typography.Text strong style={{ fontSize: 15 }}>{source.name}</Typography.Text>
                    </Space>
                    <Tag
                      color={STATUS_COLORS[source.status] ?? "default"}
                      style={{ margin: 0 }}
                    >
                      {STATUS_LABELS[source.status] ?? source.status}
                    </Tag>
                  </div>

                  <div className="source-card-meta">
                    <Tag icon={sourceTypeIcon(source.type)}>{sourceTypeLabel(source.type)}</Tag>
                    {source.has_auth && (
                      <Tag 
                        icon={source.plugin_id ? <ScanOutlined /> : <LockOutlined />} 
                        color={source.plugin_id ? "blue" : "orange"}
                      >
                        {source.plugin_name || authTypeLabel(source.auth_type)}
                        {source.plugin_user_info?.username && ` (${source.plugin_user_info.username})`}
                      </Tag>
                    )}
                    {source.schedule_enabled ? (
                      <Tag icon={<SyncOutlined spin={false} />} color="blue">
                        {formatScheduleLabel(source)}
                      </Tag>
                    ) : (
                      <Tag>{t("sources.manualFetch")}</Tag>
                    )}
                  </div>

                  <Typography.Text
                    type="secondary"
                    className="source-card-endpoint"
                    copyable={{ text: source.endpoint }}
                  >
                    {source.endpoint}
                  </Typography.Text>

                  <div className="source-card-stats">
                    {source.last_fetch_at ? (
                      <Space size={4}>
                        <ClockCircleOutlined style={{ fontSize: 12, color: "var(--ant-color-text-tertiary)" }} />
                        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                          上次 {relativeTime(source.last_fetch_at)}
                        </Typography.Text>
                      </Space>
                    ) : null}
                    {source.next_fetch_at && source.schedule_enabled ? (
                      <Space size={4}>
                        <SyncOutlined style={{ fontSize: 12, color: "var(--ant-color-text-tertiary)" }} />
                        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                          下次 {relativeTime(source.next_fetch_at)}
                        </Typography.Text>
                      </Space>
                    ) : null}
                  </div>
                </div>

                <Divider style={{ margin: "12px 0" }} />

                <div className="source-card-actions">
                  <Tooltip title={t("sources.edit")}>
                    <Button
                      type="text"
                      size="small"
                      icon={<EditOutlined />}
                      onClick={() => handleStartEdit(source)}
                    />
                  </Tooltip>
                  <Tooltip title={t("sources.export")}>
                    <Button
                      type="text"
                      size="small"
                      icon={<FileDoneOutlined />}
                      onClick={() => handleExportTemplate(source.id, source.name)}
                    />
                  </Tooltip>
                  <Tooltip title={t("sources.manualFetch")}>
                    <Button
                      type="text"
                      size="small"
                      icon={<ReloadOutlined />}
                      loading={fetchingSourceId === source.id}
                      onClick={() => {
                        setFetchingSourceId(source.id);
                        fetchMutation.mutate(source.id);
                      }}
                    />
                  </Tooltip>
                  <Tooltip title={source.schedule_enabled ? t("sources.scheduleDisableTitle") : t("sources.scheduleEnableTitle")}>
                    <Button
                      type="text"
                      size="small"
                      icon={<ClockCircleOutlined />}
                      loading={updatingScheduleSourceId === source.id}
                      style={source.schedule_enabled ? { color: "var(--ant-color-primary)" } : undefined}
                      onClick={() => {
                        setUpdatingScheduleSourceId(source.id);
                        scheduleMutation.mutate({
                          sourceId: source.id,
                          schedulePayload: {
                            schedule_enabled: !source.schedule_enabled,
                            schedule_mode: source.schedule_mode ?? "interval",
                            schedule_interval_minutes: source.schedule_interval_minutes ?? 60,
                            cron_expression: source.cron_expression,
                            cron_days_of_week: source.cron_days_of_week,
                            cron_hour: source.cron_hour,
                            cron_minute: source.cron_minute,
                          }
                        });
                      }}
                    />
                  </Tooltip>
                  <Tooltip title={t("sources.delete")}>
                    <Button
                      type="text"
                      size="small"
                      danger
                      icon={<DeleteOutlined />}
                      loading={deletingSourceId === source.id}
                      onClick={() => {
                        setDeletingSourceId(source.id);
                        deleteMutation.mutate(source.id);
                      }}
                    />
                  </Tooltip>
                </div>
              </Card>
            ))}
          </div>
        )}

        {/* ── Fetch Logs ── */}
        {firstSourceId ? (
          <section className="source-log-section">
            <Typography.Title level={5} style={{ marginBottom: 12 }}>
              <Space>
                <ClockCircleOutlined />
                {t("sources.fetchLogs")}
              </Space>
            </Typography.Title>
            {fetchLogsQuery.isLoading ? (
              <Card loading style={{ height: 80 }} />
            ) : (fetchLogsQuery.data?.length ?? 0) === 0 ? (
              <Typography.Text type="secondary">暂无抓取日志</Typography.Text>
            ) : (
              <div className="log-timeline">
                {fetchLogsQuery.data!.slice(0, 10).map((log) => (
                  <div key={log.id} className="log-item">
                    <div className="log-item-dot" data-status={log.status} />
                    <div className="log-item-content">
                      <Space size={8} wrap>
                        <Tag
                          color={log.status === "success" ? "green" : "red"}
                          style={{ margin: 0, fontSize: 11 }}
                        >
                          {log.status === "success" ? "成功" : "失败"}
                        </Tag>
                        <Tag style={{ margin: 0, fontSize: 11 }}>
                          {log.trigger === "manual" ? "手动" : "定时"}
                        </Tag>
                        <Typography.Text style={{ fontSize: 13 }}>
                          新增 {log.inserted_count}，跳过 {log.skipped_count}
                        </Typography.Text>
                      </Space>
                      <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                        {new Date(log.started_at).toLocaleString()}
                      </Typography.Text>
                      {log.error_message ? (
                        <Typography.Text type="danger" style={{ fontSize: 12 }}>
                          {log.error_message}
                        </Typography.Text>
                      ) : null}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        ) : null}
      </section>

      {/* ── QR Code Login Modal ── */}
      <Modal
        title="扫码登录"
        open={showQRCodeModal}
        onCancel={() => setShowQRCodeModal(false)}
        footer={null}
        width={420}
        destroyOnHidden
      >
        <QRCodeLogin
          session={session}
          pluginId={selectedPluginId}
          pluginName={selectedPluginId || "平台"}
          onSuccess={(credentials, userInfo) => {
            setShowQRCodeModal(false);
            setPluginCredentials(credentials || null);
            messageApi.success(userInfo?.username ? `登录成功：${userInfo.username}` : "登录成功！");
          }}
          onError={(error) => {
            messageApi.error(error);
          }}
        />
      </Modal>
    </div>
  );
}
