/**
 * Format a date string as relative time (e.g., "3分钟前", "2小时前", "昨天")
 */
export function relativeTime(isoDate: string | null | undefined): string {
  if (!isoDate) return "刚刚";
  const now = Date.now();
  const then = new Date(isoDate).getTime();
  if (isNaN(then)) return "刚刚";

  const diffMs = now - then;
  const diffSec = Math.floor(diffMs / 1000);

  // Future dates
  if (diffMs < 0) {
    const absDiff = Math.abs(diffMs);
    if (absDiff < 60_000) return "即将";
    if (absDiff < 3_600_000) return `${Math.floor(absDiff / 60_000)} 分钟后`;
    if (absDiff < 86_400_000) return `${Math.floor(absDiff / 3_600_000)} 小时后`;
    return `${Math.floor(absDiff / 86_400_000)} 天后`;
  }

  // Past dates
  if (diffSec < 60) return "刚刚";
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}分钟前`;
  const diffHour = Math.floor(diffMin / 60);
  if (diffHour < 24) return `${diffHour}小时前`;
  const diffDay = Math.floor(diffHour / 24);
  if (diffDay === 1) return "昨天";
  if (diffDay < 30) return `${diffDay}天前`;
  const diffMonth = Math.floor(diffDay / 30);
  if (diffMonth < 12) return `${diffMonth}个月前`;
  return `${Math.floor(diffMonth / 12)}年前`;
}
