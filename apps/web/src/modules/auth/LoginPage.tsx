import { LockOutlined, UserOutlined } from "@ant-design/icons";
import { Alert, Button, Form, Input, Typography } from "antd";
import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { AuthSession, login } from "../../shared/api/auth";
import { getLoginBackground } from "../../shared/api/preferences";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";
const DEFAULT_GRADIENT = "linear-gradient(135deg, #f5f7fa 0%, #e4e7f1 100%)";

type LoginValues = {
  username: string;
  password: string;
};

type LoginPageProps = {
  onLogin: (session: AuthSession) => void;
};

export function LoginPage({ onLogin }: LoginPageProps) {
  const { t } = useTranslation();
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [backgroundUrl, setBackgroundUrl] = useState<string | null>(null);

  useEffect(() => {
    getLoginBackground()
      .then((url) => setBackgroundUrl(url))
      .catch(() => setBackgroundUrl(null));
  }, []);

  async function handleFinish(values: LoginValues) {
    setError(null);
    setIsSubmitting(true);
    try {
      const session = await login(values);
      onLogin(session);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("auth.loginFailed"));
    } finally {
      setIsSubmitting(false);
    }
  }

  const backgroundStyle = backgroundUrl
    ? {
        backgroundImage: `url(${API_BASE_URL}${backgroundUrl})`,
        backgroundSize: "cover",
        backgroundPosition: "center",
      }
    : { background: DEFAULT_GRADIENT };

  const cardBackground = backgroundUrl
    ? "rgba(255, 255, 255, 0.96)"
    : "#ffffff";

  return (
    <main
      style={{
        minHeight: "100vh",
        display: "grid",
        placeItems: "center",
        padding: 24,
        ...backgroundStyle,
      }}
    >
      <motion.section
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45, ease: "easeOut" }}
        style={{
          width: "100%",
          maxWidth: 360,
          padding: "40px 32px",
          borderRadius: 20,
          background: cardBackground,
          boxShadow: backgroundUrl
            ? "0 20px 60px rgba(0, 0, 0, 0.12)"
            : "0 20px 60px rgba(0, 0, 0, 0.08)",
          backdropFilter: backgroundUrl ? "blur(8px)" : undefined,
          textAlign: "center",
        }}
      >
        <div
          style={{
            width: 48,
            height: 48,
            borderRadius: 12,
            background: "linear-gradient(135deg, #1677ff 0%, #36cfc9 100%)",
            margin: "0 auto 16px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "#fff",
            fontSize: 24,
          }}
        >
          📰
        </div>
        <Typography.Title level={3} style={{ margin: "0 0 4px" }}>
          {t("common.appName")}
        </Typography.Title>
        <Typography.Paragraph
          type="secondary"
          style={{ marginBottom: 28, fontSize: 13 }}
        >
          {t("auth.loginSlogan")}
        </Typography.Paragraph>

        {error ? (
          <Alert
            type="error"
            message={error}
            showIcon
            style={{ marginBottom: 16, textAlign: "left" }}
          />
        ) : null}

        <Form<LoginValues>
          layout="vertical"
          initialValues={{ username: "", password: "" }}
          onFinish={handleFinish}
        >
          <Form.Item
            label={t("auth.username")}
            name="username"
            rules={[{ required: true, message: t("auth.username") }]}
          >
            <Input
              prefix={<UserOutlined />}
              autoComplete="username"
              size="large"
              style={{ borderRadius: 10 }}
            />
          </Form.Item>
          <Form.Item
            label={t("auth.password")}
            name="password"
            rules={[{ required: true, message: t("auth.password") }]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              autoComplete="current-password"
              size="large"
              style={{ borderRadius: 10 }}
            />
          </Form.Item>
          <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
            <Button
              type="primary"
              htmlType="submit"
              loading={isSubmitting}
              block
              size="large"
              style={{ borderRadius: 10 }}
            >
              {t("auth.loginButton")}
            </Button>
          </motion.div>
        </Form>
      </motion.section>
    </main>
  );
}
