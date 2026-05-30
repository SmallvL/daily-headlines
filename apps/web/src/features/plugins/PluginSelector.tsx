import { useEffect, useState } from "react";
import { Card, Col, Empty, Row, Skeleton, Space, Tag, Typography, Image } from "antd";
import { CheckCircleFilled, LockOutlined, ScanOutlined, SafetyCertificateOutlined } from "@ant-design/icons";
import { AuthSession } from "../../shared/api/auth";
import { pluginsApi, SourcePlugin, AuthMethod } from "./api";

const { Text, Title } = Typography;

interface PluginSelectorProps {
  session: AuthSession;
  value?: string;
  onChange?: (pluginId: string) => void;
  showAuthMethods?: boolean;
}

export function PluginSelector({ session, value, onChange, showAuthMethods = true }: PluginSelectorProps) {
  const [plugins, setPlugins] = useState<SourcePlugin[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    pluginsApi.list(session).then(setPlugins).catch(console.error).finally(() => setLoading(false));
  }, [session]);

  const getAuthMethodIcon = (method: AuthMethod) => {
    switch (method) {
      case "qrcode": return <ScanOutlined />;
      case "none": return <SafetyCertificateOutlined />;
      default: return <LockOutlined />;
    }
  };

  const getAuthMethodLabel = (method: AuthMethod) => {
    switch (method) {
      case "qrcode": return "扫码";
      case "cookie": return "Cookie";
      case "token": return "Token";
      case "oauth": return "OAuth";
      case "none": return "无需";
      default: return method;
    }
  };

  if (loading) {
    return (
      <Row gutter={[12, 12]}>
        {[1, 2, 3, 4].map((i) => (
          <Col key={i} span={6}>
            <Card><Skeleton active avatar paragraph={{ rows: 1 }} /></Card>
          </Col>
        ))}
      </Row>
    );
  }

  if (plugins.length === 0) {
    return <Empty description="暂无可用插件" />;
  }

  return (
    <Row gutter={[12, 12]}>
      {plugins.map((plugin) => (
        <Col key={plugin.id} span={6}>
          <Card
            hoverable
            onClick={() => onChange?.(plugin.id)}
            style={{
              height: "100%",
              borderColor: value === plugin.id ? "#1890ff" : undefined,
              backgroundColor: value === plugin.id ? "#e6f7ff" : undefined,
            }}
            styles={{ body: { padding: 12 } }}
          >
            <Space direction="vertical" style={{ width: "100%" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                {plugin.icon_url ? (
                  <Image
                    src={plugin.icon_url}
                    alt={plugin.name}
                    width={28}
                    height={28}
                    preview={false}
                    fallback="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
                    style={{ borderRadius: 4 }}
                  />
                ) : (
                  <div
                    style={{
                      width: 28,
                      height: 28,
                      borderRadius: 4,
                      backgroundColor: "#f0f0f0",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: 16,
                    }}
                  >
                    {plugin.name[0]}
                  </div>
                )}
                <div style={{ flex: 1 }}>
                  <Title level={5} style={{ margin: 0, fontSize: 14 }}>{plugin.name}</Title>
                  <Text type="secondary" style={{ fontSize: 11 }}>{plugin.description}</Text>
                </div>
                {value === plugin.id && <CheckCircleFilled style={{ color: "#1890ff", fontSize: 18 }} />}
              </div>

              {showAuthMethods && (
                <div style={{ marginTop: 4 }}>
                  {plugin.auth_methods.map((method) => (
                    <Tag key={method} icon={getAuthMethodIcon(method)} style={{ marginBottom: 2, fontSize: 11 }}>
                      {getAuthMethodLabel(method)}
                    </Tag>
                  ))}
                </div>
              )}
            </Space>
          </Card>
        </Col>
      ))}
    </Row>
  );
}
