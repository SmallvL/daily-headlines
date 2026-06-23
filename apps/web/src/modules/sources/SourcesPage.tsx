import {
  ApiOutlined,
  CheckOutlined,
  ClockCircleOutlined,
  CloudDownloadOutlined,
  DeleteOutlined,
  DownOutlined,
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
  SettingOutlined,
  SyncOutlined,
  UpOutlined,
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
  Steps,
  Switch,
  Tag,
  Tooltip,
  Typography,
  message,
} from "antd";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { AuthSession } from "../../shared/api/auth";
import {
  Source,
  SourcePayload,
  SourceTemplate,
  AuthType,
  AuthConfig,
  createSource,
  deleteSource,
  exportSourceTemplate,
  fetchSourceNow,
  importSourceTemplate,
  listSourceFetchLogs,
  listSources,
  refreshSourceAuth,
  testSource,
  updateSource,
  updateSourceSchedule,
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
const DAY_LABELS_SHORT = ["日", "一", "二", "三", "四", "五", "六"];

const STATUS_COLORS: Record<string, string> = {
  active: "green",
  error: "red",
  disabled: "default",
  pending: "orange",
};

const STATUS_LABELS: Record<string, string> = {
  active: "正常",
  error: "异常",
  disabled: "已禁用",
  pending: "待验证",
};

// UI-facing auth types. The backend still receives the original AuthType values.
type UiAuthType = "none" | "cookie" | "token" | "custom";

const AUTH_BACKEND_TO_UI: Record<AuthType, UiAuthType | null> = {
  none: "none",
  cookie: "cookie",
  bearer: "token",
  api_key: "token",
  custom_headers: "custom",
  qrcode: null,
  plugin: null,
};

function uiAuthToBackend(ui: UiAuthType, original?: AuthType): AuthType {
  if (ui === "token") {
    // Preserve api_key when editing an existing api_key source; otherwise default to bearer.
    return original === "api_key" ? "api_key" : "bearer";
  }
  if (ui === "custom") return "custom_headers";
  return ui;
}

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

function extractDomainName(endpoint?: string): string {
  if (!endpoint) return "";
  try {
    const url = endpoint.startsWith("http") ? endpoint : `https://${endpoint}`;
    const hostname = new URL(url).hostname;
    return hostname.replace(/^www\./, "").split(".")[0] || "";
  } catch {
    return "";
  }
}

  function titleCase(str: string): string {
    return str.charAt(0).toUpperCase() + str.slice(1);
  }

export function SourcesPage({ session }: SourcesPageProps) {
  const { t } = useTranslation();
  const [form] = Form.useForm<ScheduleFormValues>();
  const queryClient = useQueryClient();
  const [messageApi, contextHolder] = message.useMessage();

  // Wizard / UI state
  const [wizardStep, setWizardStep] = useState(0);
  const [showAdvancedAuth, setShowAdvancedAuth] = useState(false);
  const [showAdvancedConfig, setShowAdvancedConfig] = useState(true);
  const [authExpanded, setAuthExpanded] = useState(true);
  const [scheduleExpanded, setScheduleExpanded] = useState(true);
  // Local source type state — Form.useWatch("type") doesn't reliably update
  // on form.setFieldValue, so we mirror it in local state for responsive UI.
  const [sourceTypeState, setSourceTypeState] = useState<string>("rss");

  /** Set source type in both form store and local state for responsive UI. */
  function setSourceType(value: string) {
    setSourceTypeState(value);
    form.setFieldValue("type", value);
  }

  // Preview / async state
  const [previewTitle, setPreviewTitle] = useState<string | null>(null);
  const [previewItems, setPreviewItems] = useState<Array<{ id: string; title: string; url: string | null }>>([]);
  const [fetchingSourceId, setFetchingSourceId] = useState<string | null>(null);
  const [deletingSourceId, setDeletingSourceId] = useState<string | null>(null);
  const [updatingScheduleSourceId, setUpdatingScheduleSourceId] = useState<string | null>(null);
  const [editingSourceId, setEditingSourceId] = useState<string | null>(null);

  // Plugin auth state
  const [showQRCodeModal, setShowQRCodeModal] = useState(false);
  const [pluginCredentials, setPluginCredentials] = useState<Record<string, unknown> | null>(null);
  const [selectedPluginId, setSelectedPluginId] = useState<string>("");
  const [subscriptionTypes, setSubscriptionTypes] = useState<Array<{ id: string; name: string; description: string }>>([]);
  const [selectedFetchType, setSelectedFetchType] = useState<string>("");
  const [cookieChecking, setCookieChecking] = useState(false);
  const [cookieCheckResult, setCookieCheckResult] = useState<string>("");

  // Plugin login status — persisted by pluginId across source creation/editing sessions
  const [pluginLoginStatus, setPluginLoginStatus] = useState<
    Record<string, { loggedIn: boolean; userInfo?: Record<string, string>; credentials?: Record<string, unknown> }>
  >({});

  // Watched form values
  const watchedType = Form.useWatch("type", form);
  const sourceType = sourceTypeState || watchedType || "rss";
  const authType: AuthType = Form.useWatch(["auth", "auth_type"], form) ?? "none";
  const uiAuthType: UiAuthType = AUTH_BACKEND_TO_UI[authType] ?? "none";
  const scheduleEnabled: boolean = Form.useWatch("schedule_enabled", form) ?? false;
  const scheduleMode: "interval" | "cron" = Form.useWatch("schedule_mode", form) ?? "interval";
  const intervalValue = Form.useWatch("interval_value", form) ?? 1;
  const intervalUnit = Form.useWatch("interval_unit", form) ?? "hours";
  const cronDays: number[] = Form.useWatch("cron_days", form) ?? [];
  const cronHour = Form.useWatch("cron_hour", form) ?? 8;
  const cronMinute = Form.useWatch("cron_minute", form) ?? 0;

  const sourcesQuery = useQuery({
    queryKey: ["sources"],
    queryFn: () => listSources(session),
  });
  const firstSourceId = sourcesQuery.data?.[0]?.id;
  const fetchLogsQuery = useQuery({
    queryKey: ["source-fetch-logs", firstSourceId],
    queryFn: () => listSourceFetchLogs(session, firstSourceId ?? ""),
    enabled: Boolean(firstSourceId),
  });

  const testMutation = useMutation({
    mutationFn: (payload: SourcePayload) => testSource(session, payload),
    onSuccess: (result) => {
      setPreviewTitle(result.title);
      setPreviewItems(result.items.map((item) => ({ id: item.id, title: item.title, url: item.url })));
      messageApi.success("预览成功");
    },
    onError: (error) => messageApi.error(error instanceof Error ? error.message : "预览失败"),
  });

  const createMutation = useMutation({
    mutationFn: (payload: SourcePayload) => createSource(session, payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["sources"] });
      messageApi.success("信息源已保存");
      resetForm();
    },
    onError: (error) => messageApi.error(error instanceof Error ? error.message : "保存失败"),
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
    onSettled: () => setFetchingSourceId(null),
  });

  const deleteMutation = useMutation({
    mutationFn: (sourceId: string) => deleteSource(session, sourceId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["sources"] });
      await queryClient.invalidateQueries({ queryKey: ["feed-items"] });
      messageApi.success("信息源已删除");
    },
    onError: (error) => messageApi.error(error instanceof Error ? error.message : "删除失败"),
    onSettled: () => setDeletingSourceId(null),
  });

  const scheduleMutation = useMutation({
    mutationFn: (payload: {
      sourceId: string;
      schedulePayload: Parameters<typeof updateSourceSchedule>[2];
    }) => updateSourceSchedule(session, payload.sourceId, payload.schedulePayload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["sources"] });
      messageApi.success("定时设置已更新");
    },
    onError: (error) => messageApi.error(error instanceof Error ? error.message : "更新失败"),
    onSettled: () => setUpdatingScheduleSourceId(null),
  });

  const updateMutation = useMutation({
    mutationFn: (payload: {
      sourceId: string;
      data: Partial<Pick<SourcePayload, "name" | "type" | "endpoint" | "config" | "auth">>;
    }) => updateSource(session, payload.sourceId, payload.data),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["sources"] });
      messageApi.success("信息源已更新");
      resetForm();
    },
    onError: (error) => messageApi.error(error instanceof Error ? error.message : "更新失败"),
    onSettled: () => setEditingSourceId(null),
  });

  // Reset form and wizard to defaults
  function resetForm() {
    setEditingSourceId(null);
    setWizardStep(0);
    setAuthExpanded(true);
    setScheduleExpanded(true);
    setShowAdvancedAuth(false);
    setShowAdvancedConfig(true);
    setPluginCredentials(null);
    setSelectedPluginId("");
    setSelectedFetchType("");
    setSubscriptionTypes([]);
    setCookieCheckResult("");
    setPreviewItems([]);
    setPreviewTitle(null);
    setSourceTypeState("rss");
    form.resetFields();
    // Note: pluginLoginStatus is NOT cleared — it persists across wizard sessions
    form.setFieldsValue({
      type: "rss",
      auth: { auth_type: "none" },
      schedule_enabled: false,
      schedule_mode: "interval",
      interval_value: 1,
      interval_unit: "hours",
      cron_days: [],
      cron_hour: 8,
      cron_minute: 0,
      config: {
        selector_type: "css",
        items_path: "",
        mappings: {
          id: "id",
          title: "title",
          url: "url",
          summary: "summary",
          author: "author",
          published_at: "published_at",
          image_url: "image_url",
        },
      },
    });
  }

  // Auto-fill name from endpoint domain when name is empty
  const endpointValue = Form.useWatch("endpoint", form);
  useEffect(() => {
    if (editingSourceId) return;
    const currentName = form.getFieldValue("name");
    if (!currentName && endpointValue) {
      const domain = extractDomainName(endpointValue);
      if (domain) {
        form.setFieldValue("name", titleCase(domain));
      }
    }
  }, [endpointValue, editingSourceId, form]);

  // Detect plugin login status from existing sources on page load
  // Use plugin_has_credentials directly — no API call needed, credentials are stored server-side
  const pluginStatusInitRef = useRef(false);
  useEffect(() => {
    if (pluginStatusInitRef.current) return;
    const sources = sourcesQuery.data;
    if (!sources || sources.length === 0) return;
    const pluginSources = sources.filter((s) => s.plugin_id && s.plugin_has_credentials);
    if (pluginSources.length === 0) return;
    // Group by unique plugin_id, keep the first source per plugin
    const uniquePlugins = new Map<string, Source>();
    for (const s of pluginSources) {
      if (!uniquePlugins.has(s.plugin_id!)) {
        uniquePlugins.set(s.plugin_id!, s);
      }
    }
    pluginStatusInitRef.current = true;
    // Immediately mark as logged in based on plugin_has_credentials
    uniquePlugins.forEach((src) => {
      setPluginLoginStatus((prev) => {
        if (prev[src.plugin_id!]?.loggedIn) return prev;
        return {
          ...prev,
          [src.plugin_id!]: {
            loggedIn: true,
            userInfo: src.plugin_user_info ?? undefined,
          },
        };
      });
    });
    // Optionally refresh auth in the background to update user_info silently
    uniquePlugins.forEach((src) => {
      refreshSourceAuth(session, src.id).then((result) => {
        if (result.user_info) {
          setPluginLoginStatus((prev) => ({
            ...prev,
            [src.plugin_id!]: {
              ...prev[src.plugin_id!],
              loggedIn: true,
              userInfo: result.user_info ?? prev[src.plugin_id!]?.userInfo,
            },
          }));
        }
      }).catch(() => {});
    });
  }, [sourcesQuery.data]); // Only depend on sourcesQuery.data — session removed to prevent re-run loops

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
    setEditingSourceId(source.id);
    setWizardStep(1);
    setAuthExpanded(source.has_auth);
    setScheduleExpanded(source.schedule_enabled);
    // Use "plugin" as the UI type for plugin sources, otherwise the real type
    setSourceTypeState(source.plugin_id ? "plugin" : source.type);
    if (source.plugin_id) {
      setSelectedPluginId(source.plugin_id);
      setShowAdvancedAuth(true);
    }

    const initial: ScheduleFormValues = {
      name: source.name,
      type: source.type as SourcePayload["type"],
      endpoint: source.endpoint,
      auth: {
        auth_type: source.auth_type,
        cookies: undefined,
        token: undefined,
        api_key: undefined,
        header_name: undefined,
        headers: undefined,
        plugin_id: source.plugin_id ?? undefined,
      },
      schedule_enabled: source.schedule_enabled,
      schedule_mode: source.schedule_mode,
      schedule_interval_minutes: source.schedule_interval_minutes,
      cron_expression: source.cron_expression,
      cron_days_of_week: source.cron_days_of_week,
      cron_hour: source.cron_hour,
      cron_minute: source.cron_minute,
      interval_value: 1,
      interval_unit: "hours",
              cron_days: [],
            };

    if (source.schedule_mode === "interval" && source.schedule_interval_minutes) {
      const mins = source.schedule_interval_minutes;
      if (mins % 1440 === 0) {
        initial.interval_value = mins / 1440;
        initial.interval_unit = "days";
      } else if (mins % 60 === 0) {
        initial.interval_value = mins / 60;
        initial.interval_unit = "hours";
      } else {
        initial.interval_value = mins;
        initial.interval_unit = "minutes";
      }
    }
    if (source.schedule_mode === "cron" && source.cron_days_of_week) {
      initial.cron_days = source.cron_days_of_week
        .split(",")
        .map((d) => Number(d.trim()))
        .filter((d) => !isNaN(d));
    }

    form.setFieldsValue(initial);
  }

  /**
   * Normalize wizard-only fields (interval_value/interval_unit, cron_days)
   * into the canonical backend shape (schedule_interval_minutes,
   * cron_days_of_week comma-string). When schedule is disabled, clear all
   * derived fields. Mutates and returns the passed-in payload reference for
   * convenience.
   */
  function normalizeSchedulePayload(payload: ScheduleFormValues): SourcePayload {
    const enabled = payload.schedule_enabled ?? false;
    if (!enabled) {
      payload.schedule_enabled = false;
      payload.schedule_mode = "interval";
      payload.schedule_interval_minutes = null;
      payload.cron_expression = null;
      payload.cron_days_of_week = null;
      payload.cron_hour = null;
      payload.cron_minute = null;
    } else if (payload.schedule_mode === "cron") {
      const selectedDays = payload.cron_days ?? [];
      payload.cron_days_of_week =
        selectedDays.length > 0
          ? [...selectedDays].sort((a, b) => a - b).join(",")
          : null;
      payload.schedule_interval_minutes = null;
      payload.cron_expression = null;
      payload.cron_hour = payload.cron_hour ?? 8;
      payload.cron_minute = payload.cron_minute ?? 0;
    } else {
      // interval mode
      const value = payload.interval_value ?? 1;
      const unit = payload.interval_unit ?? "hours";
      let minutes = value;
      if (unit === "hours") minutes = value * 60;
      else if (unit === "days") minutes = value * 1440;
      payload.schedule_interval_minutes = Math.max(5, minutes);
      payload.cron_expression = null;
      payload.cron_days_of_week = null;
      payload.cron_hour = null;
      payload.cron_minute = null;
    }
    // Strip wizard-only fields that don't belong in the API payload.
    delete payload.interval_value;
    delete payload.interval_unit;
    delete payload.cron_days;
    return payload;
  }

  async function getPayload(): Promise<SourcePayload> {
    const values = (await form.validateFields()) as ScheduleFormValues;
    // Build a fresh authConfig object to avoid mutating frozen form values
    const authConfig: AuthConfig = { ...(values.auth || { auth_type: "none" }) };
    const authTypeStr = authConfig.auth_type as string;

    // Ensure name is set — for plugin types, generate from user info if missing
    if (!values.name) {
      if (sourceType === "plugin" && selectedPluginId) {
        const userInfo = pluginLoginStatus[selectedPluginId]?.userInfo;
        const username = userInfo?.username || selectedPluginId;
        values.name = `${username}的订阅`;
      } else {
        values.name = "未命名信息源";
      }
    }

    // Plugin type: map to "api" on the backend with plugin auth.
    // The "plugin://..." endpoint stored in the form would fail the backend
    // HttpUrl validation, so substitute a deterministic https URL keyed on
    // the plugin id.
    if (sourceType === "plugin" || authTypeStr === "qrcode" || authTypeStr === "plugin") {
      // Try pluginCredentials state first, then fall back to pluginLoginStatus
      const activeCredentials = pluginCredentials ?? pluginLoginStatus[selectedPluginId]?.credentials;
      const pluginId =
        selectedPluginId ||
        authConfig.plugin_id ||
        (values.endpoint?.startsWith("plugin://")
          ? values.endpoint.slice("plugin://".length)
          : "");
      // Validate plugin selection
      if (!pluginId) {
        throw new Error("请先选择平台并扫码登录");
      }
      // For NEW sources, credentials must be present locally.
      // For EDIT (existing source), backend will preserve stored credentials.
      if (!editingSourceId && !activeCredentials) {
        throw new Error("登录凭证缺失，请重新扫码登录");
      }
      // Verify credentials have actual cookies (B站 may return empty cookies on auth failure)
      if (activeCredentials && typeof activeCredentials === "object") {
        const creds = activeCredentials as Record<string, unknown>;
        const cookies = creds.cookies as Record<string, unknown> | undefined;
        const cookieStr = creds.cookie_string as string | undefined;
        if ((!cookies || Object.keys(cookies).length === 0) && !cookieStr) {
          throw new Error("登录凭证无效（cookie 为空），请重新扫码登录");
        }
      }
      // Always set plugin auth
      authConfig.auth_type = "qrcode";
      authConfig.plugin_id = pluginId;
      if (activeCredentials) {
        authConfig.plugin_credentials = activeCredentials;
        authConfig.plugin_config = { fetch_type: selectedFetchType || "dynamic" };
      }
      const endpoint =
        !values.endpoint || values.endpoint.startsWith("plugin://")
          ? `https://plugin.local/${pluginId || "unknown"}/${selectedFetchType || "dynamic"}`
          : values.endpoint;
      return normalizeSchedulePayload({
        ...values,
        type: "api",
        endpoint,
        auth: authConfig,
        config: {},
      });
    }

    if ((authTypeStr === "qrcode" || authTypeStr === "plugin") && (pluginCredentials || pluginLoginStatus[selectedPluginId]?.credentials)) {
      authConfig.plugin_credentials = pluginCredentials ?? pluginLoginStatus[selectedPluginId]?.credentials;
      authConfig.plugin_config = { fetch_type: selectedFetchType || "dynamic" };
    }

    if (values.type === "api") {
      return normalizeSchedulePayload({
        ...values,
        auth: authConfig,
        config: {
          title_path: values.config?.title_path,
          items_path: values.config?.items_path,
          mappings: values.config?.mappings ?? {},
        },
      });
    }
    if (values.type === "web") {
      const allowedDomains =
        typeof values.config?.allowed_domains === "string"
          ? (values.config.allowed_domains as string).split(",").map((d: string) => d.trim()).filter(Boolean)
          : values.config?.allowed_domains ?? [];
      return normalizeSchedulePayload({
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
          allowed_domains: allowedDomains,
        },
      });
    }
    return normalizeSchedulePayload({ ...values, type: "rss", config: {}, auth: authConfig });
  }

  function buildScheduleSummary(): string {
    if (!scheduleEnabled) return "未启用定时抓取";
    if (scheduleMode === "interval") {
      const unitLabel = intervalUnit === "minutes" ? "分钟" : intervalUnit === "hours" ? "小时" : "天";
      return `每 ${intervalValue} ${unitLabel}抓取一次`;
    }
    const hour = String(cronHour).padStart(2, "0");
    const minute = String(cronMinute).padStart(2, "0");
    const timeStr = `${hour}:${minute}`;
    if (cronDays.length === 0) {
      return `每天 ${timeStr} 抓取`;
    }
    const dayNames = [...cronDays].sort((a, b) => a - b).map((d) => DAY_LABELS[d]);
    return `${dayNames.join("、")} ${timeStr} 抓取`;
  }

  const sourceTypeIcon = (type: string) => {
    switch (type) {
      case "rss": return <ApiOutlined />;
      case "api": return <CloudDownloadOutlined />;
      case "web": return <GlobalOutlined />;
      case "plugin": return <ScanOutlined />;
      default: return <ApiOutlined />;
    }
  };

  const sourceTypeLabel = (type: string) => {
    switch (type) {
      case "rss": return "RSS";
      case "api": return "JSON API";
      case "web": return "网页爬虫";
      case "plugin": return "扫码登录";
      default: return type;
    }
  };

  const authTypeLabel = (type: AuthType) => {
    switch (type) {
      case "cookie": return "Cookie";
      case "bearer": return "Bearer";
      case "api_key": return "API Key";
      case "custom_headers": return "自定义 Header";
      case "qrcode": return "扫码登录";
      case "plugin": return "插件认证";
      default: return "无认证";
    }
  };

  // ── Wizard step rendering ──

  const typeOptions = [
    {
      key: "rss",
      icon: <ApiOutlined style={{ fontSize: 28 }} />,
      title: t("sources.wizard.typeRss"),
      desc: t("sources.wizard.typeRssDesc"),
    },
    {
      key: "api",
      icon: <CloudDownloadOutlined style={{ fontSize: 28 }} />,
      title: t("sources.wizard.typeApi"),
      desc: t("sources.wizard.typeApiDesc"),
    },
    {
      key: "web",
      icon: <GlobalOutlined style={{ fontSize: 28 }} />,
      title: t("sources.wizard.typeWeb"),
      desc: t("sources.wizard.typeWebDesc"),
    },
    {
      key: "plugin",
      icon: <ScanOutlined style={{ fontSize: 28 }} />,
      title: t("sources.wizard.typePlugin"),
      desc: t("sources.wizard.typePluginDesc"),
    },
  ];

  const renderStep0 = () => {
    // Check if any plugin is already logged in
    const loggedInPlugins = Object.entries(pluginLoginStatus).filter(([, status]) => status.loggedIn);

    return (
    <div className="source-type-wizard">
      <Row gutter={[16, 16]}>
        {typeOptions.map((opt) => {
          const isPluginType = opt.key === "plugin";
          const pluginLoginInfo = loggedInPlugins.find(([pid]) => pid);
          const isLoggedIn = isPluginType && loggedInPlugins.length > 0;
          return (
          <Col xs={24} sm={12} md={6} key={opt.key}>
            <Card
              hoverable={!editingSourceId}
              className={`source-type-card ${sourceType === opt.key ? "active" : ""} ${editingSourceId && sourceType !== opt.key ? "disabled" : ""} ${isLoggedIn ? "logged-in" : ""}`}
              onClick={() => {
                if (editingSourceId && sourceType !== opt.key) return;
                setSourceType(opt.key);
                if (isPluginType && isLoggedIn) {
                  // Already logged in — jump straight to step 2 (schedule)
                  const info = loggedInPlugins[0][1];
                  setSelectedPluginId(loggedInPlugins[0][0]);
                  const username = info.userInfo?.username || loggedInPlugins[0][0];
                  form.setFieldsValue({
                    name: `${username}的订阅`,
                    type: "api",
                    endpoint: `https://${loggedInPlugins[0][0]}.com`,
                    auth: {
                      auth_type: "qrcode",
                      plugin_id: loggedInPlugins[0][0],
                    },
                  });
                  setSourceTypeState("plugin");
                  setPluginCredentials(info.credentials ?? null);
                  setWizardStep(2);
                } else {
                  setWizardStep(1);
                }
              }}
            >
              <div className={`source-type-icon ${isLoggedIn ? "logged-in" : ""}`}>
                {opt.icon}
                {isLoggedIn && <CheckOutlined className="source-type-check" />}
              </div>
              <Typography.Text strong style={{ fontSize: 16, display: "block", marginTop: 12 }}>
                {opt.title}
              </Typography.Text>
              <Typography.Text type="secondary" style={{ fontSize: 13 }}>
                {isLoggedIn && pluginLoginInfo
                  ? `已登录 · ${pluginLoginInfo[1].userInfo?.username || "点击直接添加"}`
                  : opt.desc}
              </Typography.Text>
            </Card>
          </Col>
        );
        })}
      </Row>
      {editingSourceId && (
        <div style={{ textAlign: "center", marginTop: 16 }}>
          <Button type="primary" onClick={() => setWizardStep(1)}>
            {t("sources.wizard.continueEdit")}
          </Button>
        </div>
      )}
    </div>
    );
  };

  const renderAuthSection = () => {
    const isPluginAuth = authType === "qrcode" || authType === "plugin";

    if (isPluginAuth) {
      return (
        <div className="auth-config-section">
          <Alert
            message={t("sources.wizard.authTitle")}
            description={
              <Space direction="vertical" size={4}>
                <span>{t("sources.wizard.pluginAuthAlert")}</span>
                {selectedPluginId && (
                  <span>Plugin ID: <Typography.Text code>{selectedPluginId}</Typography.Text></span>
                )}
              </Space>
            }
            type="info"
            showIcon
          />
          <div style={{ marginTop: 12 }}>
            <Button
              type="link"
              size="small"
              icon={showAdvancedAuth ? <UpOutlined /> : <DownOutlined />}
              onClick={() => setShowAdvancedAuth((v) => !v)}
            >
              {t("sources.wizard.reScanLogin")}
            </Button>
          </div>
          {showAdvancedAuth && (
            <div style={{ marginTop: 12, padding: 16, background: "var(--color-bg-subtle)", borderRadius: 8 }}>
              <PluginSelector
                session={session}
                value={selectedPluginId}
                onChange={async (pluginId) => {
                  setSelectedPluginId(pluginId);
                  form.setFieldsValue({ auth: { auth_type: "qrcode", plugin_id: pluginId } });
                      setPluginCredentials(null);
                      try {
                    const detail = await pluginsApi.get(session, pluginId);
                    setSubscriptionTypes(detail.subscription_types || []);
                    if (detail.subscription_types?.length) {
                      setSelectedFetchType(detail.subscription_types[0].id);
                    }
                  } catch {
                    // plugin detail fetch failure is non-critical
                  }
                }}
                showAuthMethods={false}
              />
              {selectedPluginId && (
                <Button
                  type="primary"
                  icon={<ScanOutlined />}
                  onClick={() => setShowQRCodeModal(true)}
                  style={{ width: "100%", marginTop: 16 }}
                  disabled={!!pluginCredentials}
                >
                  {pluginCredentials ? `${t("common.success")} ✓` : t("sources.wizard.scanLogin")}
                </Button>
              )}
              {pluginCredentials && subscriptionTypes.length > 0 && (
                <div style={{ marginTop: 16 }}>
                  <Typography.Text strong style={{ display: "block", marginBottom: 8 }}>
                    {t("sources.wizard.selectSubscription")}
                  </Typography.Text>
                  <Select
                    value={selectedFetchType}
                    onChange={(v) => setSelectedFetchType(v)}
                    style={{ width: "100%" }}
                    options={subscriptionTypes.map((st) => ({ label: `${st.name} - ${st.description}`, value: st.id }))}
                  />
                </div>
              )}
            </div>
          )}
        </div>
      );
    }

    return (
      <div className="auth-config-section">
        <Form.Item name={["auth", "auth_type"]} hidden>
          <Input />
        </Form.Item>

        <Segmented
          block
          value={uiAuthType}
          onChange={(value) => {
            const ui = value as UiAuthType;
            const backend = uiAuthToBackend(ui, authType);
            form.setFieldsValue({ auth: { auth_type: backend } });
            setCookieCheckResult("");
          }}
          options={[
            { label: t("sources.wizard.authNone"), value: "none" },
            { label: t("sources.wizard.authCookie"), value: "cookie" },
            { label: t("sources.wizard.authToken"), value: "token" },
            { label: t("sources.wizard.authCustom"), value: "custom" },
          ]}
        />

        {uiAuthType === "cookie" && (
          <Form.Item label={t("sources.wizard.authCookie")} style={{ marginTop: 16 }}>
            <Input.TextArea
              placeholder={t("sources.wizard.cookiePlaceholder")}
              rows={3}
              style={{ fontFamily: "monospace", fontSize: 12 }}
              value={form.getFieldValue(["auth", "cookies"]) ?? ""}
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
              {t("sources.wizard.cookieCheck")}
            </Button>
            {cookieCheckResult && (
              <Typography.Text
                type={cookieCheckResult.includes("✓") ? "success" : "secondary"}
                style={{ fontSize: 12, display: "block", marginTop: 4 }}
              >
                {cookieCheckResult}
              </Typography.Text>
            )}
          </Form.Item>
        )}

        {uiAuthType === "token" && (
          <>
            <Form.Item
              label="Token"
              name={["auth", "token"]}
              style={{ marginTop: 16, marginBottom: 12 }}
              tooltip={t("sources.wizard.tokenTooltip")}
            >
              <Input.Password prefix={<KeyOutlined />} placeholder="Bearer Token / API Key" />
            </Form.Item>
            <div style={{ display: "flex", gap: 12 }}>
              <Form.Item label="Header" name={["auth", "header_name"]} style={{ flex: 1, marginBottom: 0 }}>
                <Input placeholder="X-API-Key (optional)" />
              </Form.Item>
              <Form.Item label="API Key" name={["auth", "api_key"]} style={{ flex: 1, marginBottom: 0 }}>
                <Input.Password placeholder="optional" />
              </Form.Item>
            </div>
          </>
        )}

        {uiAuthType === "custom" && (
          <Form.Item label={t("sources.wizard.authCustom")} name={["auth", "headers"]} style={{ marginTop: 16 }}>
            <Input.TextArea
              placeholder={t("sources.wizard.customHeadersPlaceholder")}
              rows={3}
              style={{ fontFamily: "monospace", fontSize: 12 }}
            />
          </Form.Item>
        )}

        {isPluginAuth && (
          <Alert
            message="插件认证"
            description="当前信息源使用插件认证，配置由扫码登录生成。"
            type="info"
            showIcon
            style={{ marginTop: 16 }}
          />
        )}

        <div style={{ marginTop: 12 }}>
          <Button
            type="link"
            size="small"
            icon={showAdvancedAuth ? <UpOutlined /> : <DownOutlined />}
            onClick={() => setShowAdvancedAuth((v) => !v)}
          >
            {t("sources.wizard.authAdvanced")}
          </Button>
        </div>

        {showAdvancedAuth && (
          <div style={{ marginTop: 12, padding: 16, background: "var(--color-bg-subtle)", borderRadius: 8 }}>
            <Typography.Text type="secondary" style={{ display: "block", marginBottom: 12, fontSize: 13 }}>
              {t("sources.wizard.authPluginHint")}
            </Typography.Text>
            <PluginSelector
              session={session}
              value={selectedPluginId}
              onChange={async (pluginId) => {
                setSelectedPluginId(pluginId);
                form.setFieldsValue({ auth: { auth_type: "qrcode", plugin_id: pluginId } });
                    setPluginCredentials(null);
                    try {
                  const detail = await pluginsApi.get(session, pluginId);
                  setSubscriptionTypes(detail.subscription_types || []);
                  if (detail.subscription_types?.length) {
                    setSelectedFetchType(detail.subscription_types[0].id);
                  }
                } catch {
                  // plugin detail fetch failure is non-critical
                }
              }}
              showAuthMethods={false}
            />
            {selectedPluginId && (
              <Button
                type="primary"
                icon={<ScanOutlined />}
                onClick={() => setShowQRCodeModal(true)}
                style={{ width: "100%", marginTop: 16 }}
                disabled={!!pluginCredentials}
              >
                {pluginCredentials ? "已登录 ✓" : "扫码登录"}
              </Button>
            )}
            {pluginCredentials && subscriptionTypes.length > 0 && (
              <div style={{ marginTop: 16 }}>
                <Typography.Text strong style={{ display: "block", marginBottom: 8 }}>
                  选择订阅内容
                </Typography.Text>
                <Select
                  value={selectedFetchType}
                  onChange={(v) => setSelectedFetchType(v)}
                  style={{ width: "100%" }}
                  options={subscriptionTypes.map((st) => ({ label: `${st.name} - ${st.description}`, value: st.id }))}
                />
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  const renderScheduleSection = () => {
    return (
      <div className="schedule-section">
        {/* 启用开关 */}
        <div className="schedule-row">
          <div className="schedule-row-label">
            <SyncOutlined style={{ marginRight: 8, color: scheduleEnabled ? "var(--ant-color-primary)" : "var(--ant-color-text-tertiary)" }} />
            <span style={{ fontWeight: 500 }}>启用定时抓取</span>
          </div>
          <Form.Item name="schedule_enabled" valuePropName="checked" noStyle>
            <Switch />
          </Form.Item>
        </div>

        {scheduleEnabled && (
          <>
            {/* 模式切换 */}
            <div className="schedule-row schedule-row-divider">
              <div className="schedule-row-label">
                <span style={{ color: "var(--ant-color-text-secondary)", fontSize: 13 }}>抓取模式</span>
              </div>
              <Form.Item name="schedule_mode" noStyle>
                <Segmented
                  options={[
                    { label: "按间隔", value: "interval" },
                    { label: "按时间", value: "cron" },
                  ]}
                />
              </Form.Item>
            </div>

            {/* 间隔模式 */}
            {scheduleMode === "interval" && (
              <div className="schedule-config-block">
                <Typography.Text type="secondary" style={{ fontSize: 13, display: "block", marginBottom: 12 }}>
                  每隔多长时间抓取一次
                </Typography.Text>
                {/* 快捷预设 */}
                <Space wrap style={{ marginBottom: 12 }}>
                  {[
                    { label: "15 分钟", value: 15, unit: "minutes" },
                    { label: "30 分钟", value: 30, unit: "minutes" },
                    { label: "1 小时", value: 1, unit: "hours" },
                    { label: "6 小时", value: 6, unit: "hours" },
                    { label: "12 小时", value: 12, unit: "hours" },
                    { label: "1 天", value: 1, unit: "days" },
                  ].map((preset) => {
                    const active = intervalValue === preset.value && intervalUnit === preset.unit;
                    return (
                      <Button
                        key={`${preset.value}-${preset.unit}`}
                        size="small"
                        type={active ? "primary" : "default"}
                        onClick={() => {
                          form.setFieldsValue({
                            interval_value: preset.value,
                            interval_unit: preset.unit,
                          });
                        }}
                      >
                        {preset.label}
                      </Button>
                    );
                  })}
                </Space>
                {/* 自定义输入 */}
                <Space align="center" wrap>
                  <span style={{ color: "var(--ant-color-text-secondary)", fontSize: 13 }}>自定义：每</span>
                  <Form.Item name="interval_value" noStyle rules={[{ required: true, type: "number", min: 1 }]}>
                    <InputNumber min={1} max={10080} style={{ width: 90 }} />
                  </Form.Item>
                  <Form.Item name="interval_unit" noStyle>
                    <Select style={{ width: 96 }} options={[
                      { label: "分钟", value: "minutes" },
                      { label: "小时", value: "hours" },
                      { label: "天", value: "days" },
                    ]} />
                  </Form.Item>
                  <span style={{ color: "var(--ant-color-text-secondary)", fontSize: 13 }}>抓取一次</span>
                </Space>
              </div>
            )}

            {/* Cron 模式 */}
            {scheduleMode === "cron" && (
              <div className="schedule-config-block">
                {/* 周几 */}
                <Typography.Text type="secondary" style={{ fontSize: 13, display: "block", marginBottom: 8 }}>
                  选择周几执行 <span style={{ opacity: 0.7 }}>（不选则每天）</span>
                </Typography.Text>
                <div className="schedule-day-btns" style={{ marginBottom: 16 }}>
                  {[1, 2, 3, 4, 5, 6, 0].map((day) => {
                    const isActive = cronDays.includes(day);
                    return (
                      <div
                        key={day}
                        className={`schedule-day-btn ${isActive ? "active" : ""} ${day === 0 || day === 6 ? "weekend" : ""}`}
                        onClick={() => {
                          const next = isActive
                            ? cronDays.filter((d) => d !== day)
                            : [...cronDays, day].sort((a, b) => a - b);
                          form.setFieldsValue({ cron_days: next });
                        }}
                      >
                        {DAY_LABELS_SHORT[day]}
                      </div>
                    );
                  })}
                </div>
                {/* 时间 */}
                <Typography.Text type="secondary" style={{ fontSize: 13, display: "block", marginBottom: 8 }}>
                  执行时间
                </Typography.Text>
                <Space align="center" wrap>
                  {/* 时间快捷 */}
                  {[
                    { label: "08:00", h: 8, m: 0 },
                    { label: "09:00", h: 9, m: 0 },
                    { label: "12:00", h: 12, m: 0 },
                    { label: "18:00", h: 18, m: 0 },
                    { label: "21:00", h: 21, m: 0 },
                  ].map((t) => {
                    const active = cronHour === t.h && cronMinute === t.m;
                    return (
                      <Button
                        key={t.label}
                        size="small"
                        type={active ? "primary" : "default"}
                        onClick={() => form.setFieldsValue({ cron_hour: t.h, cron_minute: t.m })}
                      >
                        {t.label}
                      </Button>
                    );
                  })}
                  <span style={{ color: "var(--ant-color-text-secondary)", marginLeft: 8, fontSize: 13 }}>或</span>
                  <ClockCircleOutlined style={{ color: "var(--ant-color-primary)" }} />
                  <Form.Item name="cron_hour" noStyle>
                    <InputNumber min={0} max={23} style={{ width: 64 }} formatter={(v) => String(v ?? 0).padStart(2, "0")} />
                  </Form.Item>
                  <span style={{ fontWeight: 600 }}>:</span>
                  <Form.Item name="cron_minute" noStyle>
                    <InputNumber min={0} max={59} style={{ width: 64 }} formatter={(v) => String(v ?? 0).padStart(2, "0")} />
                  </Form.Item>
                </Space>
              </div>
            )}

            {/* 摘要 */}
            <div className="schedule-summary">
              <SyncOutlined />
              <span>{buildScheduleSummary()}</span>
            </div>
          </>
        )}
      </div>
    );
  };

  const renderApiConfig = () => (
    <div className="api-mapping-grid">
      <Alert
        message={t("sources.wizard.apiConfig")}
        description={t("sources.wizard.apiHint")}
        type="info"
        showIcon
        style={{ gridColumn: "1 / -1", marginBottom: 8 }}
      />
      <Form.Item label="Items path" name={["config", "items_path"]}>
        <Input placeholder="e.g. data.items" />
      </Form.Item>
      <Form.Item label="Title path" name={["config", "mappings", "title"]}>
        <Input placeholder="title" />
      </Form.Item>

      <div style={{ gridColumn: "1 / -1" }}>
        <Button
          type="link"
          size="small"
          icon={showAdvancedConfig ? <UpOutlined /> : <DownOutlined />}
          onClick={() => setShowAdvancedConfig((v) => !v)}
        >
          {t("sources.wizard.advancedFieldMapping")}
        </Button>
      </div>

      {showAdvancedConfig && (
        <>
          <Form.Item label="链接路径" name={["config", "mappings", "url"]}>
            <Input placeholder="url" />
          </Form.Item>
          <Form.Item label="摘要路径" name={["config", "mappings", "summary"]}>
            <Input placeholder="summary" />
          </Form.Item>
          <Form.Item label="唯一 ID 路径" name={["config", "mappings", "id"]}>
            <Input placeholder="id" />
          </Form.Item>
          <Form.Item label="作者路径" name={["config", "mappings", "author"]}>
            <Input placeholder="author" />
          </Form.Item>
          <Form.Item label="发布时间路径" name={["config", "mappings", "published_at"]}>
            <Input placeholder="published_at" />
          </Form.Item>
          <Form.Item label="图片路径" name={["config", "mappings", "image_url"]}>
            <Input placeholder="image_url" />
          </Form.Item>
        </>
      )}
    </div>
  );

  const renderWebConfig = () => (
    <div className="api-mapping-grid">
      <Form.Item label="选择器类型" name={["config", "selector_type"]} initialValue="css">
        <Segmented
          options={[
            { label: "CSS", value: "css" },
            { label: "XPath", value: "xpath" },
          ]}
        />
      </Form.Item>
      <div />
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

      <div style={{ gridColumn: "1 / -1" }}>
        <Button
          type="link"
          size="small"
          icon={showAdvancedConfig ? <UpOutlined /> : <DownOutlined />}
          onClick={() => setShowAdvancedConfig((v) => !v)}
        >
          {t("sources.wizard.moreSelectors")}
        </Button>
      </div>

      {showAdvancedConfig && (
        <>
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
        </>
      )}
    </div>
  );

  const renderPluginConfig = () => {
    const loginStatus = selectedPluginId ? pluginLoginStatus[selectedPluginId] : undefined;
    const isPluginLoggedIn = !!pluginCredentials || !!loginStatus?.loggedIn;
    const effectiveCredentials = pluginCredentials ?? loginStatus?.credentials;

    return (
    <div className="source-plugin-config">
      {isPluginLoggedIn && loginStatus?.userInfo ? (
        <Alert
          message="已登录"
          description={
            <Space direction="vertical" size={4}>
              <span>
                {loginStatus.userInfo.username
                  ? `当前账号：${loginStatus.userInfo.username}`
                  : "凭证有效"}
              </span>
              <span style={{ fontSize: 12, color: "var(--ant-color-text-secondary)" }}>
                可直接添加信息源，无需重新扫码
              </span>
            </Space>
          }
          type="success"
          showIcon
          icon={<CheckOutlined />}
          style={{ marginBottom: 16 }}
          action={
            <Button
              size="small"
              type="link"
              danger
              onClick={() => {
                setPluginCredentials(null);
                setPluginLoginStatus((prev) => {
                  const next = { ...prev };
                  delete next[selectedPluginId];
                  return next;
                });
                form.setFieldsValue({ auth: { auth_type: "qrcode", plugin_id: selectedPluginId } });
              }}
            >
              重新登录
            </Button>
          }
        />
      ) : (
        <Alert
          message={t("sources.wizard.typePlugin")}
          description={t("sources.wizard.typePluginDesc")}
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      {!isPluginLoggedIn && (
        <>
          <Typography.Text strong style={{ display: "block", marginBottom: 12 }}>
            {t("sources.wizard.pluginSelectPlatform")}
          </Typography.Text>
          <PluginSelector
            session={session}
            value={selectedPluginId}
            onChange={async (pluginId) => {
              setSelectedPluginId(pluginId);
              setPluginCredentials(null);
              form.setFieldsValue({ auth: { auth_type: "qrcode", plugin_id: pluginId } });
              try {
                const detail = await pluginsApi.get(session, pluginId);
                setSubscriptionTypes(detail.subscription_types || []);
                if (detail.subscription_types?.length) {
                  setSelectedFetchType(detail.subscription_types[0].id);
                }
              } catch {
                // plugin detail fetch failure is non-critical
              }
            }}
            showAuthMethods={false}
          />
        </>
      )}

      {selectedPluginId && !isPluginLoggedIn && (
        <Button
          type="primary"
          icon={<ScanOutlined />}
          onClick={() => setShowQRCodeModal(true)}
          style={{ width: "100%", marginTop: 16 }}
        >
          {t("sources.wizard.pluginScanToLogin")}
        </Button>
      )}

      {(isPluginLoggedIn || pluginCredentials) && subscriptionTypes.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <Typography.Text strong style={{ display: "block", marginBottom: 8 }}>
            {t("sources.wizard.pluginSelectContent")}
          </Typography.Text>
          <Select
            value={selectedFetchType}
            onChange={(v) => setSelectedFetchType(v)}
            style={{ width: "100%" }}
            options={subscriptionTypes.map((st) => ({ label: `${st.name} - ${st.description}`, value: st.id }))}
          />
        </div>
      )}

      {isPluginLoggedIn && (
        <Form.Item label={t("sources.name")} name="name" rules={[{ required: true }]} style={{ marginTop: 16 }}>
          <Input placeholder={t("sources.namePlaceholder")} />
        </Form.Item>
      )}
    </div>
    );
  };

  const renderStep1 = () => (
    <div className="source-wizard-step">
      {/* ── 基本信息区 ── */}
      <div className="source-config-card">
        <div className="source-config-card-header">
          <ApiOutlined />
          <span>基本信息</span>
        </div>
        <div className="source-config-card-body">
          <Row gutter={[16, 0]}>
            <Col span={24} md={24}>
              <Form.Item
                label={t("sources.type")}
                tooltip="选择信息源的来源类型"
                style={{ marginBottom: 16 }}
              >
                <Segmented
                  block
                  value={sourceType}
                  disabled={!!editingSourceId}
                  onChange={(value) => setSourceType(value as string)}
                  options={[
                    { label: <Space><ApiOutlined /> {t("sources.wizard.typeRss")}</Space>, value: "rss" },
                    { label: <Space><CloudDownloadOutlined /> {t("sources.wizard.typeApi")}</Space>, value: "api" },
                    { label: <Space><GlobalOutlined /> {t("sources.wizard.typeWeb")}</Space>, value: "web" },
                    { label: <Space><ScanOutlined /> {t("sources.wizard.typePlugin")}</Space>, value: "plugin" },
                  ]}
                />
              </Form.Item>
            </Col>

            {sourceType === "plugin" ? (
              <Col span={24}>
                {renderPluginConfig()}
              </Col>
            ) : (
              <>
                <Col span={24} md={10}>
                  <Form.Item
                    label={t("sources.name")}
                    name="name"
                    rules={[{ required: true, message: "请输入信息源名称" }]}
                    tooltip="信息源的显示名称（用于卡片和列表）"
                  >
                    <Input placeholder={t("sources.namePlaceholder")} />
                  </Form.Item>
                </Col>
                <Col span={24} md={14}>
                  <Form.Item
                    label={
                      sourceType === "api"
                        ? "API 地址"
                        : sourceType === "web"
                          ? "网页地址"
                          : "RSS 订阅地址"
                    }
                    name="endpoint"
                    rules={[{ required: true, message: "请输入信息源 URL" }]}
                    tooltip={
                      sourceType === "rss"
                        ? "RSS/Atom 订阅源完整 URL"
                        : sourceType === "api"
                          ? "返回 JSON 数据的 API URL"
                          : "要抓取的网页 URL"
                    }
                  >
                    <Input
                      placeholder={
                        sourceType === "api"
                          ? "https://example.com/api/news"
                          : sourceType === "web"
                            ? "https://example.com/news"
                            : "https://example.com/feed.xml"
                      }
                    />
                  </Form.Item>
                </Col>
              </>
            )}
          </Row>
        </div>
      </div>

      {/* ── 认证设置区 ── (非 plugin 类型) */}
      {sourceType !== "plugin" && (
        <div className="source-config-card">
          <div
            className="source-config-card-header source-config-card-header-clickable"
            onClick={() => setAuthExpanded((v) => !v)}
          >
            <LockOutlined />
            <span>认证设置</span>
            {!authExpanded && uiAuthType !== "none" && (
              <Tag color="blue" style={{ margin: "0 0 0 auto" }}>{authTypeLabel(authType)}</Tag>
            )}
            {authExpanded && uiAuthType === "none" && (
              <Tag style={{ margin: "0 0 0 auto" }}>无需认证</Tag>
            )}
            <span className="source-config-card-toggle">
              {authExpanded ? <UpOutlined /> : <DownOutlined />}
            </span>
          </div>
          {authExpanded && (
            <div className="source-config-card-body">
              {renderAuthSection()}
            </div>
          )}
        </div>
      )}

      {/* ── 抓取配置区 ── (非 RSS / 非 plugin) */}
      {sourceType !== "rss" && sourceType !== "plugin" && (
        <div className="source-config-card">
          <div
            className="source-config-card-header source-config-card-header-clickable"
            onClick={() => setShowAdvancedConfig((v) => !v)}
          >
            <SettingOutlined />
            <span>
              {sourceType === "api" ? "API 字段映射" : "网页解析规则"}
            </span>
            <Tag style={{ margin: "0 0 0 auto" }} color={showAdvancedConfig ? "blue" : "default"}>
              {sourceType === "api" ? "JSON Path" : "CSS / XPath"}
            </Tag>
            <span className="source-config-card-toggle">
              {showAdvancedConfig ? <UpOutlined /> : <DownOutlined />}
            </span>
          </div>
          {showAdvancedConfig && (
            <div className="source-config-card-body">
              {sourceType === "api" ? renderApiConfig() : renderWebConfig()}
            </div>
          )}
        </div>
      )}

      <div className="source-wizard-actions">
        <Space wrap>
          <Button onClick={() => setWizardStep(0)}>{t("common.previous")}</Button>
          <Button
            icon={<ExperimentOutlined />}
            loading={testMutation.isPending}
            onClick={() => {
              getPayload()
                .then((payload) => testMutation.mutate(payload))
                .catch((err) => {
                  const msg = err instanceof Error ? err.message : "测试预览失败";
                  messageApi.error(msg);
                });
            }}
          >
            {t("sources.testPreview")}
          </Button>
          <Button type="primary" onClick={() => setWizardStep(2)}>
            {t("common.next")}
          </Button>
        </Space>
      </div>
    </div>
  );

  const renderStep2 = () => (
    <div className="source-wizard-step">
      <div className="source-config-card">
        <div
          className="source-config-card-header source-config-card-header-clickable"
          onClick={() => setScheduleExpanded((v) => !v)}
        >
          <ClockCircleOutlined />
          <span>定时抓取</span>
          <Tag
            style={{ margin: "0 0 0 auto" }}
            color={scheduleEnabled ? "blue" : "default"}
          >
            {scheduleEnabled ? "已启用" : "已关闭"}
          </Tag>
          <span className="source-config-card-toggle">
            {scheduleExpanded ? <UpOutlined /> : <DownOutlined />}
          </span>
        </div>
        {scheduleExpanded && <div className="source-config-card-body">{renderScheduleSection()}</div>}
      </div>

      <div className="source-wizard-actions">
        <Space wrap>
          <Button onClick={() => setWizardStep(1)}>{t("common.previous")}</Button>
          <Button
            type="primary"
            icon={<SaveOutlined />}
            loading={createMutation.isPending || updateMutation.isPending}
            onClick={() => {
              getPayload()
                .then((payload) => {
                  if (editingSourceId) {
                    updateMutation.mutate({ sourceId: editingSourceId, data: payload });
                  } else {
                    createMutation.mutate(payload);
                  }
                })
                .catch((err) => {
                  const msg = err instanceof Error ? err.message : "保存失败";
                  messageApi.error(msg);
                });
            }}
          >
            {editingSourceId ? t("sources.updateSource") : t("sources.saveSource")}
          </Button>
          <Button onClick={resetForm}>{t("common.cancel")}</Button>
        </Space>
      </div>
    </div>
  );

  // ── Render source list card ──

  const renderSourceCard = (source: Source) => (
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
          <Tag color={STATUS_COLORS[source.status] ?? "default"} style={{ margin: 0 }}>
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
          <Button type="text" size="small" icon={<EditOutlined />} onClick={() => handleStartEdit(source)} />
        </Tooltip>
        <Tooltip title={t("sources.export")}>
          <Button type="text" size="small" icon={<FileDoneOutlined />} onClick={() => handleExportTemplate(source.id, source.name)} />
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
        {source.plugin_id && source.status === "error" && (
          <Tooltip title="刷新认证状态">
            <Button
              type="text"
              size="small"
              icon={<ScanOutlined />}
              onClick={async () => {
                try {
                  const result = await refreshSourceAuth(session, source.id);
                  if (result.valid) {
                    messageApi.success("认证有效，信息源已恢复");
                    await queryClient.invalidateQueries({ queryKey: ["sources"] });
                  } else {
                    messageApi.warning(result.message || "认证失效，请重新扫码登录");
                  }
                } catch {
                  messageApi.error("认证刷新失败");
                }
              }}
            />
          </Tooltip>
        )}
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
                },
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
  );

  return (
    <div className="sources-page">
      {contextHolder}

      {/* ── Wizard Form ── */}
      <section className="source-form-section">
        <div className="source-section-header">
          <div>
            <Typography.Title level={4} style={{ marginBottom: 4 }}>
              {editingSourceId ? t("sources.edit") : t("sources.create")}
            </Typography.Title>
            <Typography.Text type="secondary">{t("sources.subtitle")}</Typography.Text>
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
              type: "rss",
              name: "",
              endpoint: "",
              auth: { auth_type: "none" },
              schedule_enabled: false,
              schedule_mode: "interval",
              schedule_interval_minutes: 60,
              interval_value: 1,
              interval_unit: "hours",
              cron_days: [],
              cron_hour: 8,
              cron_minute: 0,
              config: {
                selector_type: "css",
                items_path: "",
                mappings: {
                  id: "id",
                  title: "title",
                  url: "url",
                  summary: "summary",
                  author: "author",
                  published_at: "published_at",
                  image_url: "image_url",
                },
              },
            }}
            className="source-form"
          >
            <Steps
              current={wizardStep}
              items={[
                { title: t("sources.wizard.step1"), icon: <ApiOutlined /> },
                { title: t("sources.wizard.step2"), icon: <SettingOutlined /> },
                { title: t("sources.wizard.step3"), icon: <ClockCircleOutlined /> },
              ]}
              style={{ marginBottom: 24 }}
              onChange={(step) => setWizardStep(step)}
            />

            {wizardStep === 0 && renderStep0()}
            {wizardStep === 1 && renderStep1()}
            {wizardStep === 2 && renderStep2()}
          </Form>
        </Card>
      </section>

      {/* ── Preview ── */}
      {previewItems.length > 0 ? (
        <Alert
          type="success"
          showIcon
          icon={<ExperimentOutlined />}
          message={previewTitle ? `${t("sources.preview")}：${previewTitle}` : t("sources.preview")}
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
        />
      ) : null}

      {/* ── Source List ── */}
      <section className="source-list-section">
        <div className="source-section-header">
          <div>
            <Typography.Title level={4} style={{ marginBottom: 4 }}>{t("sources.mySources")}</Typography.Title>
            <Typography.Text type="secondary">{t("sources.count", { count: sourcesQuery.data?.length ?? 0 })}</Typography.Text>
          </div>
        </div>

        {sourcesQuery.isLoading ? (
          <Card loading style={{ height: 120 }} />
        ) : (sourcesQuery.data?.length ?? 0) === 0 ? (
          <Card>
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={t("sources.empty")}>
              <Button type="primary" icon={<ImportOutlined />} onClick={handleImportTemplate}>
                {t("sources.import")}
              </Button>
            </Empty>
          </Card>
        ) : (
          <>
            {sourcesQuery.data!.some((s) => s.plugin_id) && (
              <>
                <Typography.Title level={5} style={{ margin: "16px 0 8px" }}>
                  <ScanOutlined style={{ marginRight: 8 }} />
                  {t("sources.wizard.typePlugin")}
                </Typography.Title>
                <div className="source-cards-grid">
                  {sourcesQuery.data!.filter((s) => s.plugin_id).map((source) => renderSourceCard(source))}
                </div>
              </>
            )}

            {sourcesQuery.data!.some((s) => !s.plugin_id) && (
              <>
                <Typography.Title level={5} style={{ margin: "16px 0 8px" }}>
                  <ApiOutlined style={{ marginRight: 8 }} />
                  RSS / API 信息源
                </Typography.Title>
                <div className="source-cards-grid">
                  {sourcesQuery.data!.filter((s) => !s.plugin_id).map((source) => renderSourceCard(source))}
                </div>
              </>
            )}
          </>
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
                        <Tag color={log.status === "success" ? "green" : "red"} style={{ margin: 0, fontSize: 11 }}>
                          {log.status === "success" ? "成功" : "失败"}
                        </Tag>
                        <Tag style={{ margin: 0, fontSize: 11 }}>{log.trigger === "manual" ? "手动" : "定时"}</Tag>
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
            // Persist login status per plugin
            if (credentials) {
              setPluginLoginStatus((prev) => ({
                ...prev,
                [selectedPluginId]: {
                  loggedIn: true,
                  userInfo: userInfo ?? prev[selectedPluginId]?.userInfo,
                  credentials,
                },
              }));
            }
            const pluginName = userInfo?.username || selectedPluginId;
            form.setFieldsValue({
              name: `${pluginName}的订阅`,
              type: "api",
              endpoint: `https://${selectedPluginId}.com`,
              auth: {
                auth_type: "qrcode",
                plugin_id: selectedPluginId,
              },
            });
            // Keep the UI type as "plugin" even though backend stores "api"
            setSourceTypeState("plugin");
            messageApi.success(userInfo?.username ? `登录成功：${userInfo.username}` : "登录成功！请选择内容类型并保存");
          }}
          onError={(error) => {
            messageApi.error(error);
          }}
        />
      </Modal>
    </div>
  );
}
