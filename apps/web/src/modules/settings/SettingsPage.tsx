import {
  CheckOutlined,
  GlobalOutlined,
  MoonOutlined,
  SunOutlined,
  DesktopOutlined,
  UnorderedListOutlined,
  AppstoreOutlined,
  CompressOutlined,
  SettingOutlined,
  PictureOutlined,
  DeleteOutlined,
  UploadOutlined,
} from "@ant-design/icons";
import {
  Button,
  Card,
  Col,
  Row,
  Segmented,
  Space,
  Typography,
  Upload,
  message,
} from "antd";
import type { UploadChangeParam } from "antd/es/upload/interface";
import type { UploadRequestOption } from "rc-upload/lib/interface";
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { AuthSession } from "../../shared/api/auth";
import {
  DefaultView,
  Language,
  Theme,
  UserPreference,
  getPreference,
  updatePreference,
} from "../../shared/api/preferences";
import { uploadLoginBackground } from "../../shared/api/upload";

const { Title, Text } = Typography;

type Props = {
  session: AuthSession;
  onPreferenceChange?: (pref: UserPreference) => void;
};

export function SettingsPage({ session, onPreferenceChange }: Props) {
  const { t, i18n } = useTranslation();
  const [preference, setPreference] = useState<UserPreference | null>(null);
  const [loading, setLoading] = useState(true);

  const loadPreference = useCallback(async () => {
    try {
      const pref = await getPreference(session);
      setPreference(pref);
      if (i18n.language !== pref.language) {
        await i18n.changeLanguage(pref.language);
      }
    } catch (e) {
      message.error(`加载偏好失败: ${e}`);
    } finally {
      setLoading(false);
    }
  }, [session, i18n]);

  useEffect(() => {
    void loadPreference();
  }, [loadPreference]);

  const handleLanguageChange = async (lang: Language) => {
    try {
      const pref = await updatePreference(session, { language: lang });
      setPreference(pref);
      await i18n.changeLanguage(lang);
      message.success(t("settings.saveSuccess"));
      onPreferenceChange?.(pref);
    } catch (e) {
      message.error(t("settings.saveFailed"));
    }
  };

  const handleThemeChange = async (theme: Theme) => {
    try {
      const pref = await updatePreference(session, { theme });
      setPreference(pref);
      message.success(t("settings.saveSuccess"));
      onPreferenceChange?.(pref);
    } catch (e) {
      message.error(t("settings.saveFailed"));
    }
  };

  const handleViewChange = async (view: DefaultView) => {
    try {
      const pref = await updatePreference(session, { default_view: view });
      setPreference(pref);
      message.success(t("settings.saveSuccess"));
      onPreferenceChange?.(pref);
    } catch (e) {
      message.error(t("settings.saveFailed"));
    }
  };

  const handleUploadChange = async (info: UploadChangeParam) => {
    const { file } = info;
    if (file.status === "uploading") {
      return;
    }
    if (file.status === "done") {
      message.success("背景图已上传");
    }
  };

  const customUpload = async (options: UploadRequestOption) => {
    try {
      const file = options.file as File;
      const { url } = await uploadLoginBackground(session, file);
      const pref = await updatePreference(session, { login_background_url: url });
      setPreference(pref);
      onPreferenceChange?.(pref);
      (options.onSuccess as (value: unknown) => void)?.(url);
    } catch (e) {
      message.error(e instanceof Error ? e.message : "上传失败");
      (options.onError as (error: Error) => void)?.(e instanceof Error ? e : new Error("上传失败"));
    }
  };

  const handleClearBackground = async () => {
    try {
      const pref = await updatePreference(session, { login_background_url: null });
      setPreference(pref);
      onPreferenceChange?.(pref);
      message.success("已恢复默认背景");
    } catch (e) {
      message.error(t("settings.saveFailed"));
    }
  };

  if (loading || !preference) {
    return (
      <div style={{ padding: 24, textAlign: "center" }}>
        <Typography.Text type="secondary">{t("common.loading")}</Typography.Text>
      </div>
    );
  }

  return (
    <div className="settings-page">
      <div className="source-section-header">
        <div>
          <Typography.Title level={4} style={{ marginBottom: 4 }}>
            <Space>
              <SettingOutlined />
              {t("settings.title")}
            </Space>
          </Typography.Title>
          <Typography.Text type="secondary">{t("settings.subtitle")}</Typography.Text>
        </div>
      </div>

      <Row gutter={[24, 24]}>
        <Col xs={24} md={12}>
          <Card
            title={
              <Space>
                <GlobalOutlined />
                {t("settings.language")}
              </Space>
            }
            styles={{ body: { padding: "20px 24px" } }}
            style={{ borderRadius: "var(--radius-md)", height: "100%" }}
          >
            <Text type="secondary" style={{ display: "block", marginBottom: 16 }}>
              {t("settings.languageDesc")}
            </Text>
            <Segmented
              block
              value={preference.language}
              onChange={(value) => handleLanguageChange(value as Language)}
              options={[
                {
                  label: (
                    <Space>
                      <span>🇨🇳</span>
                      <span>{t("settings.chineseSimplified")}</span>
                      {preference.language === "zh-CN" && <CheckOutlined />}
                    </Space>
                  ),
                  value: "zh-CN",
                },
                {
                  label: (
                    <Space>
                      <span>🇺🇸</span>
                      <span>English</span>
                      {preference.language === "en-US" && <CheckOutlined />}
                    </Space>
                  ),
                  value: "en-US",
                },
              ]}
            />
          </Card>
        </Col>

        <Col xs={24} md={12}>
          <Card
            title={
              <Space>
                <SunOutlined />
                {t("settings.theme")}
              </Space>
            }
            styles={{ body: { padding: "20px 24px" } }}
            style={{ borderRadius: "var(--radius-md)", height: "100%" }}
          >
            <Text type="secondary" style={{ display: "block", marginBottom: 16 }}>
              {t("settings.themeDesc")}
            </Text>
            <Segmented
              block
              value={preference.theme}
              onChange={(value) => handleThemeChange(value as Theme)}
              options={[
                {
                  label: (
                    <Space>
                      <SunOutlined />
                      <span>{t("settings.themeLight")}</span>
                      {preference.theme === "light" && <CheckOutlined />}
                    </Space>
                  ),
                  value: "light",
                },
                {
                  label: (
                    <Space>
                      <MoonOutlined />
                      <span>{t("settings.themeDark")}</span>
                      {preference.theme === "dark" && <CheckOutlined />}
                    </Space>
                  ),
                  value: "dark",
                },
                {
                  label: (
                    <Space>
                      <DesktopOutlined />
                      <span>{t("settings.themeSystem")}</span>
                      {preference.theme === "system" && <CheckOutlined />}
                    </Space>
                  ),
                  value: "system",
                },
              ]}
            />
          </Card>
        </Col>

        <Col xs={24} md={12}>
          <Card
            title={
              <Space>
                <AppstoreOutlined />
                {t("settings.defaultView")}
              </Space>
            }
            styles={{ body: { padding: "20px 24px" } }}
            style={{ borderRadius: "var(--radius-md)", height: "100%" }}
          >
            <Text type="secondary" style={{ display: "block", marginBottom: 16 }}>
              {t("settings.defaultViewDesc")}
            </Text>
            <Segmented
              block
              value={preference.default_view}
              onChange={(value) => handleViewChange(value as DefaultView)}
              options={[
                {
                  label: (
                    <Space>
                      <UnorderedListOutlined />
                      <span>{t("settings.viewList")}</span>
                      {preference.default_view === "list" && <CheckOutlined />}
                    </Space>
                  ),
                  value: "list",
                },
                {
                  label: (
                    <Space>
                      <AppstoreOutlined />
                      <span>{t("settings.viewGrid")}</span>
                      {preference.default_view === "grid" && <CheckOutlined />}
                    </Space>
                  ),
                  value: "grid",
                },
                {
                  label: (
                    <Space>
                      <CompressOutlined />
                      <span>{t("settings.viewCompact")}</span>
                      {preference.default_view === "compact" && <CheckOutlined />}
                    </Space>
                  ),
                  value: "compact",
                },
              ]}
            />
          </Card>
        </Col>

        <Col xs={24} md={12}>
          <Card
            title={
              <Space>
                <PictureOutlined />
                登录页背景
              </Space>
            }
            styles={{ body: { padding: "20px 24px" } }}
            style={{ borderRadius: "var(--radius-md)", height: "100%" }}
          >
            <Text type="secondary" style={{ display: "block", marginBottom: 16 }}>
              自定义登录页背景图，留空则使用默认渐变。
            </Text>
            {preference.login_background_url ? (
              <Space direction="vertical" style={{ width: "100%" }}>
                <div
                  style={{
                    width: "100%",
                    height: 100,
                    borderRadius: 8,
                    backgroundImage: `url(${import.meta.env.VITE_API_BASE_URL ?? ""}${preference.login_background_url})`,
                    backgroundSize: "cover",
                    backgroundPosition: "center",
                    border: "1px solid var(--color-border-subtle)",
                  }}
                />
                <Button icon={<DeleteOutlined />} danger onClick={handleClearBackground}>
                  清除背景图
                </Button>
              </Space>
            ) : (
              <Upload
                accept="image/jpeg,image/png,image/webp,image/gif"
                customRequest={customUpload}
                onChange={handleUploadChange}
                showUploadList={false}
              >
                <Button icon={<UploadOutlined />}>上传背景图</Button>
              </Upload>
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
}
