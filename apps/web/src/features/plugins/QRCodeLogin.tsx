import { useEffect, useRef, useState } from "react";
import { Alert, Button, Image, Space, Spin, Tag, Typography, message } from "antd";
import {
  ReloadOutlined,
  ScanOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
} from "@ant-design/icons";
import { AuthSession } from "../../shared/api/auth";
import { pluginsApi, QRCodeStatus } from "./api";

const { Text } = Typography;

interface QRCodeLoginProps {
  session: AuthSession;
  pluginId: string;
  pluginName: string;
  pluginIcon?: string;
  onSuccess?: (credentials?: Record<string, unknown>, userInfo?: Record<string, string>) => void;
  onError?: (error: string) => void;
}

export function QRCodeLogin({
  session,
  pluginId,
  pluginName,
  pluginIcon,
  onSuccess,
  onError,
}: QRCodeLoginProps) {
  const [loading, setLoading] = useState(true);
  const [qrcodeImage, setQrcodeImage] = useState<string>("");
  const [sessionId, setSessionId] = useState<string>("");
  const [countdown, setCountdown] = useState<number>(0);
  const [status, setStatus] = useState<
    "loading" | "ready" | "scanned" | "confirmed" | "expired" | "error"
  >("loading");
  const [statusMessage, setStatusMessage] = useState<string>("");
  const [userInfo, setUserInfo] = useState<Record<string, string> | null>(null);

  const pollingRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const countdownRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const stopPolling = () => {
    if (pollingRef.current) {
      clearTimeout(pollingRef.current);
      pollingRef.current = null;
    }
  };
  const stopCountdown = () => {
    if (countdownRef.current) {
      clearTimeout(countdownRef.current);
      countdownRef.current = null;
    }
  };

  const generateQRCode = async () => {
    try {
      setLoading(true);
      setStatus("loading");
      setStatusMessage("正在生成二维码...");

      const result = await pluginsApi.initAuth(session, pluginId, "qrcode");

      if (result.success && result.qrcode_image) {
        setQrcodeImage(result.qrcode_image);
        setSessionId(result.session_id || "");
        const exp = result.expires_in || 300;
        setCountdown(exp);
        setStatus("ready");
        setStatusMessage("请使用手机扫描二维码");

        startPolling(result.session_id || "", exp);
      } else {
        setStatus("error");
        setStatusMessage("生成二维码失败");
        onError?.("生成二维码失败");
      }
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : "生成二维码失败";
      setStatus("error");
      setStatusMessage(msg);
      onError?.(msg);
    } finally {
      setLoading(false);
    }
  };

  const startPolling = (sid: string, ttl: number) => {
    stopPolling();
    stopCountdown();

    let remaining = ttl;
    const tick = () => {
      remaining -= 1;
      setCountdown(remaining);
      if (remaining <= 0) {
        setStatus("expired");
        setStatusMessage("二维码已过期，请刷新");
        stopCountdown();
        return;
      }
      countdownRef.current = setTimeout(tick, 1000);
    };
    countdownRef.current = setTimeout(tick, 1000);

    const poll = async () => {
      try {
        const result: QRCodeStatus = await pluginsApi.checkQRCodeStatus(session, pluginId, sid);

        if (result.status === "confirmed") {
          setStatus("confirmed");
          setStatusMessage("登录成功！");
          setUserInfo(result.user_info || null);
          stopPolling();
          stopCountdown();
          onSuccess?.(result.credentials, result.user_info);
          return;
        }
        if (result.status === "scanned") {
          setStatus("scanned");
          setStatusMessage("已扫码，请在手机上确认");
        } else if (result.status === "expired") {
          setStatus("expired");
          setStatusMessage("二维码已过期，请刷新");
          stopPolling();
          stopCountdown();
          return;
        } else if (result.status === "cancelled") {
          setStatus("error");
          setStatusMessage(result.error || "登录已取消");
          stopPolling();
          stopCountdown();
          onError?.(result.error || "登录已取消");
          return;
        }
        pollingRef.current = setTimeout(poll, 2000);
      } catch (error: unknown) {
        const msg = error instanceof Error ? error.message : "检查状态失败";
        setStatus("error");
        setStatusMessage(msg);
        stopPolling();
        stopCountdown();
      }
    };

    pollingRef.current = setTimeout(poll, 1000);
  };

  const handleRefresh = () => {
    stopPolling();
    stopCountdown();
    generateQRCode();
  };

  useEffect(() => {
    generateQRCode();
    return () => {
      stopPolling();
      stopCountdown();
    };
  }, [pluginId]);

  const formatCountdown = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  const renderStatusIcon = () => {
    switch (status) {
      case "ready":
        return <ScanOutlined style={{ color: "var(--ant-color-primary)" }} />;
      case "scanned":
        return <LoadingOutlined style={{ color: "var(--ant-color-warning)" }} />;
      case "confirmed":
        return <CheckCircleOutlined style={{ color: "var(--ant-color-success)" }} />;
      case "expired":
      case "error":
        return <CloseCircleOutlined style={{ color: "var(--ant-color-error)" }} />;
      default:
        return <Spin size="small" />;
    }
  };

  const getStatusColor = () => {
    switch (status) {
      case "ready":
        return "processing";
      case "scanned":
        return "warning";
      case "confirmed":
        return "success";
      case "expired":
      case "error":
        return "error";
      default:
        return "default";
    }
  };

  return (
    <div style={{ textAlign: "center", padding: "20px" }}>
      {/* Plugin Header */}
      <Space style={{ marginBottom: 20 }}>
        {pluginIcon && (
          <Image src={pluginIcon} alt={pluginName} width={32} height={32} preview={false} />
        )}
        <Typography.Title level={5} style={{ margin: 0 }}>
          登录 {pluginName}
        </Typography.Title>
      </Space>

      {/* QR Code */}
      <div
        style={{
          width: 280,
          height: 280,
          margin: "0 auto 20px",
          border: "1px solid var(--ant-color-border)",
          borderRadius: 8,
          overflow: "hidden",
          position: "relative",
          backgroundColor: status === "confirmed" ? "var(--ant-color-success-bg)" : "var(--ant-color-bg-container)",
        }}
      >
        {loading ? (
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%" }}>
            <Spin tip="生成中..." />
          </div>
        ) : qrcodeImage ? (
          <img
            src={qrcodeImage}
            alt="QR Code"
            style={{
              width: "100%",
              height: "100%",
              objectFit: "contain",
              opacity: status === "expired" ? 0.5 : 1,
            }}
          />
        ) : (
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", color: "var(--ant-color-text-tertiary)" }}>
            二维码生成失败
          </div>
        )}

        {/* Overlay for expired/confirmed */}
        {(status === "expired" || status === "confirmed") && (
          <div
            style={{
              position: "absolute",
              inset: 0,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              backgroundColor: status === "confirmed" ? "rgba(82,196,26,0.9)" : "rgba(0,0,0,0.7)",
              color: "#fff",
            }}
          >
            {status === "confirmed" ? (
              <>
                <CheckCircleOutlined style={{ fontSize: 48, marginBottom: 16 }} />
                <Text strong style={{ color: "#fff", fontSize: 16 }}>登录成功</Text>
                {userInfo?.username && <Text style={{ color: "#fff", marginTop: 8 }}>{userInfo.username}</Text>}
              </>
            ) : (
              <>
                <CloseCircleOutlined style={{ fontSize: 48, marginBottom: 16 }} />
                <Text strong style={{ color: "#fff", fontSize: 16 }}>二维码已过期</Text>
                <Button type="primary" ghost icon={<ReloadOutlined />} onClick={handleRefresh} style={{ marginTop: 16 }}>
                  刷新二维码
                </Button>
              </>
            )}
          </div>
        )}
      </div>

      {/* Status */}
      <Space direction="vertical" size={8}>
        <Tag icon={renderStatusIcon()} color={getStatusColor()} style={{ fontSize: 14, padding: "4px 12px" }}>
          {statusMessage}
        </Tag>
        {(status === "ready" || status === "scanned") && countdown > 0 && (
          <Text type="secondary" style={{ fontSize: 12 }}>
            有效期：{formatCountdown(countdown)}
          </Text>
        )}
        {status === "ready" && (
          <Button type="link" icon={<ReloadOutlined />} onClick={handleRefresh} size="small">
            刷新二维码
          </Button>
        )}
      </Space>

      {/* Instructions */}
      <div style={{ marginTop: 24, textAlign: "left" }}>
        <Alert
          message="扫码步骤"
          description={
            <ol style={{ margin: 0, paddingLeft: 20 }}>
              <li>打开 {pluginName} App</li>
              <li>进入「我的」或「个人中心」</li>
              <li>点击右上角扫一扫图标</li>
              <li>扫描上方二维码</li>
              <li>在手机上确认登录</li>
            </ol>
          }
          type="info"
          showIcon
        />
      </div>
    </div>
  );
}
