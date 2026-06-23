import { useMutation, useQuery } from "@tanstack/react-query";
import {
  Button,
  Card,
  Checkbox,
  Drawer,
  Empty,
  Input,
  List,
  Segmented,
  Select,
  Skeleton,
  Space,
  Typography,
  message,
  theme,
  Tooltip,
} from "antd";
import { useCallback, useState } from "react";
import { useTranslation } from "react-i18next";
import { motion } from "framer-motion";

import { AuthSession } from "../../shared/api/auth";
import { proxiedImageUrl } from "../../shared/utils/imageProxy";
import { relativeTime } from "../../shared/utils/time";
import {
  FeedQuery,
  FeedItem,
  hideFeedItem,
  listFeedItems,
  readFeedItem,
  saveFeedItem,
  unsaveFeedItem,
} from "../../shared/api/feed";
import {
  createSavedSearch,
  deleteSavedSearch,
  fromApiQuery,
  listSavedSearches,
} from "../../shared/api/search";
import { listSources } from "../../shared/api/sources";

/* ───────── SVG Icons ───────── */

const SearchIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="11" cy="11" r="8" />
    <path d="M21 21l-4.35-4.35" />
  </svg>
);

const FilterIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" />
  </svg>
);

const GridIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="3" width="7" height="7" />
    <rect x="14" y="3" width="7" height="7" />
    <rect x="3" y="14" width="7" height="7" />
    <rect x="14" y="14" width="7" height="7" />
  </svg>
);

const ListIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="8" y1="6" x2="21" y2="6" />
    <line x1="8" y1="12" x2="21" y2="12" />
    <line x1="8" y1="18" x2="21" y2="18" />
    <line x1="3" y1="6" x2="3.01" y2="6" />
    <line x1="3" y1="12" x2="3.01" y2="12" />
    <line x1="3" y1="18" x2="3.01" y2="18" />
  </svg>
);

const CompactIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="4" y1="6" x2="20" y2="6" />
    <line x1="4" y1="12" x2="20" y2="12" />
    <line x1="4" y1="18" x2="16" y2="18" />
  </svg>
);

const StarIcon = ({ filled }: { filled?: boolean }) => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill={filled ? "currentColor" : "none"} stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
  </svg>
);

const CheckIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="20 6 9 17 4 12" />
  </svg>
);

const EyeHideIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
    <line x1="1" y1="1" x2="23" y2="23" />
  </svg>
);

const ClockIcon = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10" />
    <polyline points="12 6 12 12 16 14" />
  </svg>
);

const PersonIcon = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
    <circle cx="12" cy="7" r="4" />
  </svg>
);

/* ───────── Helpers ───────── */

type ViewMode = "grid" | "list" | "compact";

const cardVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.35, ease: "easeOut" as const, delay: i * 0.04 },
  }),
};

const containerVariants = {
  hidden: {},
  visible: {
    transition: { staggerChildren: 0.06 },
  },
};

/* ───────── Component ───────── */

type DashboardPageProps = {
  session: AuthSession;
  onCreateSource: () => void;
};

export function DashboardPage({ session, onCreateSource }: DashboardPageProps) {
  const { t } = useTranslation();
  const { token } = theme.useToken();
  const [query, setQuery] = useState<FeedQuery>({});
  const [draftKeyword, setDraftKeyword] = useState("");
  const [isFilterOpen, setIsFilterOpen] = useState(false);
  const [saveName, setSaveName] = useState("");
  const [viewMode, setViewMode] = useState<ViewMode>("grid");
  const [messageApi, contextHolder] = message.useMessage();

  /* ── Queries ── */
  const feedQuery = useQuery({
    queryKey: ["feed-items", query],
    queryFn: () => listFeedItems(session, query),
  });

  const savedSearchesQuery = useQuery({
    queryKey: ["saved-searches"],
    queryFn: () => listSavedSearches(session),
  });

  const sourcesQuery = useQuery({
    queryKey: ["sources-list"],
    queryFn: () => listSources(session),
  });

  /* ── Mutations ── */
  const saveSearchMutation = useMutation({
    mutationFn: () => createSavedSearch(session, saveName || t("common.unnamedSearch"), query),
    onSuccess: async () => {
      setSaveName("");
      await savedSearchesQuery.refetch();
      messageApi.success("搜索已保存");
    },
    onError: (error) => messageApi.error(error instanceof Error ? error.message : "保存失败"),
  });

  const deleteSearchMutation = useMutation({
    mutationFn: (searchId: string) => deleteSavedSearch(session, searchId),
    onSuccess: async () => {
      await savedSearchesQuery.refetch();
      messageApi.success("已删除保存搜索");
    },
    onError: (error) => messageApi.error(error instanceof Error ? error.message : "删除失败"),
  });

  const toggleSaveMutation = useMutation({
    mutationFn: (item: { id: string; isSaved: boolean }) =>
      item.isSaved ? unsaveFeedItem(session, item.id) : saveFeedItem(session, item.id),
    onSuccess: async () => {
      await feedQuery.refetch();
    },
    onError: (error) => messageApi.error(error instanceof Error ? error.message : "收藏失败"),
  });

  const markReadMutation = useMutation({
    mutationFn: (itemId: string) => readFeedItem(session, itemId),
    onSuccess: async () => {
      await feedQuery.refetch();
    },
    onError: (error) => messageApi.error(error instanceof Error ? error.message : "标记已读失败"),
  });

  const hideMutation = useMutation({
    mutationFn: (itemId: string) => hideFeedItem(session, itemId),
    onSuccess: async () => {
      await feedQuery.refetch();
    },
    onError: (error) => messageApi.error(error instanceof Error ? error.message : "隐藏失败"),
  });

  function applyKeyword(value: string) {
    setQuery((current) => ({ ...current, q: value.trim() || undefined }));
  }

  const handleTitleClick = useCallback(
    (item: FeedItem) => {
      if (!item.is_read) {
        markReadMutation.mutate(item.id);
      }
    },
    [markReadMutation],
  );

  /* ── Shared action buttons for each item ── */
  const renderActions = (item: FeedItem) => (
    <Space size={4} style={{ flexShrink: 0 }}>
      <Tooltip title={item.is_saved ? "取消收藏" : "收藏"}>
        <Button
          type="text"
          size="small"
          style={{ color: item.is_saved ? token.colorPrimary : token.colorTextSecondary }}
          icon={<StarIcon filled={item.is_saved} />}
          loading={toggleSaveMutation.isPending}
          onClick={(e) => {
            e.stopPropagation();
            toggleSaveMutation.mutate({ id: item.id, isSaved: item.is_saved });
          }}
        />
      </Tooltip>
      <Tooltip title={item.is_read ? "已读" : "标记已读"}>
        <Button
          type="text"
          size="small"
          disabled={item.is_read}
          style={{ color: item.is_read ? token.colorPrimary : token.colorTextSecondary }}
          icon={<CheckIcon />}
          loading={markReadMutation.isPending}
          onClick={(e) => {
            e.stopPropagation();
            if (!item.is_read) markReadMutation.mutate(item.id);
          }}
        />
      </Tooltip>
      <Tooltip title="隐藏">
        <Button
          type="text"
          size="small"
          danger
          style={{ color: token.colorTextSecondary }}
          icon={<EyeHideIcon />}
          loading={hideMutation.isPending}
          onClick={(e) => {
            e.stopPropagation();
            hideMutation.mutate(item.id);
          }}
        />
      </Tooltip>
    </Space>
  );

  /* ── Title with optional link icon ── */
  const renderTitle = (item: FeedItem) => {
    const titleEl = (
      <Typography.Text
        strong
        ellipsis={{ tooltip: item.title }}
        style={{
          fontSize: 14,
          lineHeight: 1.5,
          opacity: item.is_read ? 0.6 : 1,
          cursor: item.url ? "pointer" : "default",
          transition: "opacity 0.2s, color 0.2s",
          display: "-webkit-box",
          WebkitLineClamp: 2,
          WebkitBoxOrient: "vertical",
          overflow: "hidden",
        }}
        onClick={() => {
          handleTitleClick(item);
          if (item.url) window.open(item.url, "_blank", "noopener,noreferrer");
        }}
      >
        {item.title}
      </Typography.Text>
    );
    return titleEl;
  };

  /* ── Meta row: source name + time + author ── */
  const renderMeta = (item: FeedItem) => {
    // Clean up author - extract name from email format like "name@domain.com (Display Name)"
    let displayAuthor = item.author || "";
    const match = displayAuthor.match(/\(([^)]+)\)/);
    if (match) {
      displayAuthor = match[1];
    } else if (displayAuthor.includes("@")) {
      displayAuthor = displayAuthor.split("@")[0];
    }
    // Truncate long author names
    if (displayAuthor.length > 20) {
      displayAuthor = displayAuthor.substring(0, 20) + "…";
    }

    return (
      <Space size={10} style={{ fontSize: 12, color: token.colorTextSecondary, marginTop: 4, flexWrap: "wrap" }}>
        <span style={{ 
          fontWeight: 500, 
          color: token.colorPrimary,
          maxWidth: 120,
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
          display: "inline-block"
        }}>
          {item.source_name}
        </span>
        <span style={{ display: "inline-flex", alignItems: "center", gap: 3 }}>
          <ClockIcon /> {relativeTime(item.published_at ?? item.fetched_at)}
        </span>
        {displayAuthor ? (
          <span style={{ display: "inline-flex", alignItems: "center", gap: 3, maxWidth: 120, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            <PersonIcon /> {displayAuthor}
          </span>
        ) : null}
      </Space>
    );
  };

  /* ── Gradient placeholder when no image ── */
  const placeholderGradient = (id: string) => {
    const hue = (id.charCodeAt(0) * 37 + id.charCodeAt(1) * 13) % 360;
    return `linear-gradient(135deg, hsl(${hue}, 60%, 65%) 0%, hsl(${(hue + 40) % 360}, 50%, 55%) 100%)`;
  };

  /* ───────── Skeletons ───────── */
  const renderGridSkeletons = () => (
    <div className="dashboard-feed-grid">
      {Array.from({ length: 6 }).map((_, i) => (
        <Card key={i} className="dashboard-card-skeleton" styles={{ body: { padding: 0 } }}>
          <Skeleton.Image active style={{ width: "100%", height: 160 }} />
          <div style={{ padding: 12 }}>
            <Skeleton active title={{ width: "90%" }} paragraph={{ rows: 1, width: "60%" }} />
          </div>
        </Card>
      ))}
    </div>
  );

  const renderListSkeletons = () => (
    <div className="dashboard-feed-list">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="dashboard-list-item" style={{ alignItems: "center" }}>
          <Skeleton.Image active style={{ width: 160, height: 100 }} />
          <div style={{ flex: 1, minWidth: 0 }}>
            <Skeleton active title={{ width: "70%" }} paragraph={{ rows: 2, width: ["90%", "50%"] }} />
          </div>
        </div>
      ))}
    </div>
  );

  const renderCompactSkeletons = () => (
    <div className="dashboard-feed-compact">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="dashboard-compact-row">
          <Skeleton active title={{ width: "60%" }} paragraph={false} />
        </div>
      ))}
    </div>
  );

  /* ───────── Grid Card ───────── */
  const renderGridCard = (item: FeedItem) => {
    const readOpacity = item.is_read ? 0.5 : 1;
    const handleCardClick = (e: React.MouseEvent) => {
      // Don't navigate if clicking an action button or interactive element
      const target = e.target as HTMLElement;
      if (target.closest("button, a, [data-no-card-click]")) return;
      handleTitleClick(item);
      if (item.url) window.open(item.url, "_blank", "noopener,noreferrer");
    };
    return (
      <div
        key={item.id}
        className="dashboard-card dashboard-card-clickable"
        style={{ opacity: readOpacity, cursor: item.url ? "pointer" : "default" }}
        onClick={handleCardClick}
      >
        {/* Image */}
        <div className="dashboard-card-cover">
          {item.image_url ? (
            <img
              src={proxiedImageUrl(item.image_url) ?? undefined}
              alt=""
              loading="lazy"
              referrerPolicy="no-referrer"
              style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
              onError={(e) => {
                (e.target as HTMLImageElement).style.display = "none";
              }}
            />
          ) : (
            <div
              className="cover-placeholder"
              style={{ background: placeholderGradient(item.id) }}
            >
              <span className="cover-char">
                {item.title.charAt(0)}
              </span>
              <span className="cover-source">
                {item.source_name}
              </span>
            </div>
          )}
          <span className="cover-source-tag">
            {item.source_name}
          </span>
          <span className="cover-badge cover-badge-right">
            {relativeTime(item.published_at ?? item.fetched_at)}
          </span>
        </div>

        {/* Body */}
        <div className="dashboard-card-body">
          <Typography.Text
            strong
            ellipsis={{ tooltip: item.title }}
            style={{
              fontSize: 14,
              lineHeight: 1.5,
              display: "-webkit-box",
              WebkitLineClamp: 2,
              WebkitBoxOrient: "vertical",
              overflow: "hidden",
            }}
          >
            {item.title}
          </Typography.Text>
        </div>

        {/* Actions */}
        <div
          className="dashboard-card-actions"
          style={{ opacity: item.is_read ? 0.5 : 1 }}
          data-no-card-click
        >
          {renderActions(item)}
        </div>
      </div>
    );
  };

  /* ───────── List Item ───────── */
  const renderListItem = (item: FeedItem) => {
    const readOpacity = item.is_read ? 0.55 : 1;
    const handleRowClick = (e: React.MouseEvent) => {
      const target = e.target as HTMLElement;
      if (target.closest("button, a, [data-no-card-click]")) return;
      handleTitleClick(item);
      if (item.url) window.open(item.url, "_blank", "noopener,noreferrer");
    };
    return (
      <div
        key={item.id}
        className="dashboard-list-item dashboard-list-item-clickable"
        style={{ opacity: readOpacity, cursor: item.url ? "pointer" : "default" }}
        onClick={handleRowClick}
      >
        {/* Thumbnail */}
        <div className="dashboard-list-thumb">
          {item.image_url ? (
            <img
              src={proxiedImageUrl(item.image_url) ?? undefined}
              alt=""
              loading="lazy"
              referrerPolicy="no-referrer"
              style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
              onError={(e) => {
                (e.target as HTMLImageElement).style.display = "none";
              }}
            />
          ) : (
            <div
              style={{
                width: "100%",
                height: "100%",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 32,
                color: "rgba(255,255,255,0.7)",
                fontWeight: 700,
                background: placeholderGradient(item.id),
              }}
            >
              {item.title.charAt(0)}
            </div>
          )}
        </div>

        {/* Text content */}
        <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", gap: 4 }}>
          {renderTitle(item)}
          {item.summary ? (
            <Typography.Paragraph
              ellipsis={{ rows: 2 }}
              style={{ margin: 0, fontSize: 13, opacity: item.is_read ? 0.45 : 0.75 }}
              type="secondary"
            >
              {item.summary}
            </Typography.Paragraph>
          ) : null}
          <div style={{ flex: 1 }} />
          {renderMeta(item)}
        </div>

        {/* Actions on right */}
        <div style={{ display: "flex", alignItems: "center", flexShrink: 0 }} data-no-card-click>
          {renderActions(item)}
        </div>
      </div>
    );
  };

  /* ───────── Compact Row ───────── */
  const renderCompactRow = (item: FeedItem) => {
    const handleRowClick = (e: React.MouseEvent) => {
      const target = e.target as HTMLElement;
      if (target.closest("button, a, [data-no-card-click]")) return;
      handleTitleClick(item);
      if (item.url) window.open(item.url, "_blank", "noopener,noreferrer");
    };
    return (
    <div
      key={item.id}
      className="dashboard-compact-row dashboard-compact-row-clickable"
      style={{ opacity: item.is_read ? 0.55 : 1, cursor: item.url ? "pointer" : "default" }}
      onClick={handleRowClick}
    >
      {/* Title */}
      <div style={{ flex: 1, minWidth: 0 }}>{renderTitle(item)}</div>

      {/* Source */}
      <span className="compact-source">
        {item.source_name}
      </span>

      {/* Time */}
      <span className="compact-time">
        <ClockIcon /> {relativeTime(item.published_at ?? item.fetched_at)}
      </span>

      {/* Actions */}
      <div data-no-card-click>{renderActions(item)}</div>
    </div>
    );
  };

  /* ───────── Feed container per view mode ───────── */
  const feedData = feedQuery.data;
  const items = feedData?.items ?? [];
  const totalItems = feedData?.total ?? 0;

  /* ───────── Segmented options with SVG icons ───────── */
  const segmentedOptions = [
    {
      label: (
        <Tooltip title="宫格">
          <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
            <GridIcon /> <span>宫格</span>
          </span>
        </Tooltip>
      ),
      value: "grid" as const,
    },
    {
      label: (
        <Tooltip title="列表">
          <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
            <ListIcon /> <span>列表</span>
          </span>
        </Tooltip>
      ),
      value: "list" as const,
    },
    {
      label: (
        <Tooltip title="紧凑">
          <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
            <CompactIcon /> <span>紧凑</span>
          </span>
        </Tooltip>
      ),
      value: "compact" as const,
    },
  ];

  /* ───────── Render ───────── */
  return (
    <div className="dashboard-page">
      {contextHolder}

      {/* Toolbar */}
      <div className="dashboard-toolbar">
        <div className="toolbar-left">
          <Input
            prefix={<SearchIcon />}
            placeholder="搜索标题、摘要、来源或标签"
            className="search-input"
            value={draftKeyword}
            onChange={(event) => setDraftKeyword(event.target.value)}
            onPressEnter={() => applyKeyword(draftKeyword)}
            allowClear
            onClear={() => {
              setDraftKeyword("");
              applyKeyword("");
            }}
          />
        </div>
        <div className="toolbar-right">
          <Segmented
            options={segmentedOptions}
            value={viewMode}
            onChange={(val) => setViewMode(val as ViewMode)}
          />
          <Tooltip title="过滤">
            <Button icon={<FilterIcon />} onClick={() => setIsFilterOpen(true)}>
              过滤
            </Button>
          </Tooltip>
          <Button type="primary" onClick={onCreateSource}>
            新增信息源
          </Button>
        </div>
      </div>

      {/* Quick Source Filters */}
      {sourcesQuery.data && sourcesQuery.data.length > 0 && (
        <div className="source-filter-bar">
          <div className="source-filter-scroll">
            <Button
              size="small"
              type={!query.sourceId ? "primary" : "default"}
              className="source-filter-btn"
              onClick={() => setQuery((current) => ({ ...current, sourceId: undefined }))}
            >
              全部
            </Button>
            {sourcesQuery.data.map((source) => (
              <Button
                key={source.id}
                size="small"
                type={query.sourceId === source.id ? "primary" : "default"}
                className="source-filter-btn"
                onClick={() =>
                  setQuery((current) => ({
                    ...current,
                    sourceId: current.sourceId === source.id ? undefined : source.id,
                  }))
                }
              >
                {source.name}
              </Button>
            ))}
          </div>
        </div>
      )}

      {/* Feed section */}
      <section className="feed-section">
        <div className="feed-header">
          <h2>今日信息流</h2>
          <p>
            {feedQuery.isLoading ? t("common.loading") : `共 ${totalItems} 条内容`}
          </p>
        </div>

        {feedQuery.isError ? (
          <div className="error-banner">
            {feedQuery.error instanceof Error ? feedQuery.error.message : "信息流加载失败"}
          </div>
        ) : null}

        {/* Grid view needs special container */}
        {feedQuery.isLoading ? (
          viewMode === "grid" ? renderGridSkeletons() : viewMode === "list" ? renderListSkeletons() : renderCompactSkeletons()
        ) : items.length === 0 ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={
              <Space direction="vertical" size={8} style={{ textAlign: "center" }}>
                <Typography.Text strong style={{ fontSize: 16 }}>
                  {t("feed.empty")}
                </Typography.Text>
                <Typography.Text type="secondary">
                  添加 RSS、API 或网页爬虫信息源后，这里会展示聚合内容。
                </Typography.Text>
                <Button type="primary" onClick={onCreateSource} style={{ marginTop: 8 }}>
                  {t("feed.addSource")}
                </Button>
              </Space>
            }
            className="empty-container"
          />
        ) : viewMode === "grid" ? (
          <motion.div
            className="dashboard-feed-grid"
            variants={containerVariants}
            initial="hidden"
            animate="visible"
          >
            {items.map((item, i) => (
              <motion.div
                key={item.id}
                variants={cardVariants}
                custom={i}
                whileHover={{ scale: 1.02 }}
                transition={{ type: "spring", stiffness: 300, damping: 20 }}
              >
                {renderGridCard(item)}
              </motion.div>
            ))}
          </motion.div>
        ) : viewMode === "list" ? (
          <motion.div className="dashboard-feed-list" initial="hidden" animate="visible">
            {items.map((item, i) => (
              <motion.div key={item.id} variants={cardVariants} custom={i}>
                {renderListItem(item)}
              </motion.div>
            ))}
          </motion.div>
        ) : (
          <motion.div className="dashboard-feed-compact" initial="hidden" animate="visible">
            {items.map((item, i) => (
              <motion.div key={item.id} variants={cardVariants} custom={i}>
                {renderCompactRow(item)}
              </motion.div>
            ))}
          </motion.div>
        )}
      </section>

      {/* Filter Drawer */}
      <Drawer
        title="过滤"
        open={isFilterOpen}
        onClose={() => setIsFilterOpen(false)}
        width={340}
        extra={
          <Button
            onClick={() => {
              setQuery({});
              setDraftKeyword("");
            }}
          >
            清空
          </Button>
        }
      >
        <Space direction="vertical" size={18} className="filter-drawer-content">
          <div>
            <Typography.Text strong>来源类型</Typography.Text>
            <Select
              allowClear
              className="filter-control"
              placeholder="全部"
              value={query.sourceType}
              options={[
                { label: "RSS", value: "rss" },
                { label: "JSON API", value: "api" },
              ]}
              onChange={(value) => setQuery((current) => ({ ...current, sourceType: value }))}
            />
          </div>
          <Checkbox
            checked={query.hasImage === true}
            onChange={(event) =>
              setQuery((current) => ({
                ...current,
                hasImage: event.target.checked ? true : undefined,
              }))
            }
          >
            只看含图片
          </Checkbox>
          <Checkbox
            checked={query.saved === true}
            onChange={(event) =>
              setQuery((current) => ({
                ...current,
                saved: event.target.checked ? true : undefined,
              }))
            }
          >
            只看收藏
          </Checkbox>
          <div>
            <Typography.Text strong>阅读状态</Typography.Text>
            <Select
              allowClear
              className="filter-control"
              placeholder="全部"
              value={query.read === undefined ? undefined : String(query.read)}
              options={[
                { label: "未读", value: "false" },
                { label: "已读", value: "true" },
              ]}
              onChange={(value) =>
                setQuery((current) => ({
                  ...current,
                  read: value === undefined ? undefined : value === "true",
                }))
              }
            />
          </div>
          <Checkbox
            checked={query.includeHidden === true}
            onChange={(event) =>
              setQuery((current) => ({
                ...current,
                includeHidden: event.target.checked ? true : undefined,
              }))
            }
          >
            显示隐藏项
          </Checkbox>
          <div>
            <Typography.Text strong>保存当前条件</Typography.Text>
            <Space.Compact className="filter-control">
              <Input
                value={saveName}
                placeholder="例如：RSS 有图"
                onChange={(event) => setSaveName(event.target.value)}
              />
              <Button
                type="primary"
                loading={saveSearchMutation.isPending}
                onClick={() => saveSearchMutation.mutate()}
              >
                保存
              </Button>
            </Space.Compact>
          </div>
          <div>
            <Typography.Text strong>已保存搜索</Typography.Text>
            <List
              size="small"
              loading={savedSearchesQuery.isLoading}
              dataSource={savedSearchesQuery.data ?? []}
              locale={{ emptyText: "暂无保存搜索" }}
              renderItem={(savedSearch) => (
                <List.Item
                  actions={[
                    <Button
                      key="apply"
                      type="link"
                      onClick={() => {
                        const nextQuery = fromApiQuery(savedSearch);
                        setQuery(nextQuery);
                        setDraftKeyword(nextQuery.q ?? "");
                      }}
                    >
                      使用
                    </Button>,
                    <Button
                      key="delete"
                      type="link"
                      danger
                      onClick={() => deleteSearchMutation.mutate(savedSearch.id)}
                    >
                      删除
                    </Button>,
                  ]}
                >
                  {savedSearch.name}
                </List.Item>
              )}
            />
          </div>
        </Space>
      </Drawer>
    </div>
  );
}
