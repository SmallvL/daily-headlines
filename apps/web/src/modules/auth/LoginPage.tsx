import { LockOutlined, UserOutlined } from "@ant-design/icons";
import { Alert, Button, Form, Input, Typography, theme } from "antd";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { AuthSession, login } from "../../shared/api/auth";

type LoginPageProps = {
  onLogin: (session: AuthSession) => void;
};

type LoginValues = {
  username: string;
  password: string;
};

export function LoginPage({ onLogin }: LoginPageProps) {
  const { t } = useTranslation();
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { token } = theme.useToken();

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

  return (
    <main className="login-page" style={{ background: token.colorBgLayout }}>
      <section
        className="login-panel"
        style={{
          background: token.colorBgContainer,
          borderColor: token.colorBorderSecondary,
          boxShadow: token.boxShadowTertiary
        }}
      >
        <Typography.Title level={2}>{t("common.appName")}</Typography.Title>
        <Typography.Paragraph type="secondary">
          {t("auth.loginSubtitle")}
        </Typography.Paragraph>
        {error ? <Alert type="error" message={error} showIcon className="form-alert" /> : null}
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
            <Input prefix={<UserOutlined />} autoComplete="username" />
          </Form.Item>
          <Form.Item
            label={t("auth.password")}
            name="password"
            rules={[{ required: true, message: t("auth.password") }]}
          >
            <Input.Password prefix={<LockOutlined />} autoComplete="current-password" />
          </Form.Item>
          <Button type="primary" htmlType="submit" loading={isSubmitting} block>
            {t("auth.loginButton")}
          </Button>
        </Form>
      </section>
    </main>
  );
}
