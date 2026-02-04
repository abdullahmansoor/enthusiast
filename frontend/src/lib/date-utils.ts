/**
 * Simple relative time formatter without dependencies
 */
export function formatDistanceToNow(date: Date, options?: { addSuffix?: boolean }): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSeconds = Math.floor(diffMs / 1000);
  const diffMinutes = Math.floor(diffSeconds / 60);
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);
  const diffMonths = Math.floor(diffDays / 30);
  const diffYears = Math.floor(diffDays / 365);

  let result: string;

  if (diffSeconds < 60) {
    result = `${diffSeconds} second${diffSeconds !== 1 ? 's' : ''}`;
  } else if (diffMinutes < 60) {
    result = `${diffMinutes} minute${diffMinutes !== 1 ? 's' : ''}`;
  } else if (diffHours < 24) {
    result = `${diffHours} hour${diffHours !== 1 ? 's' : ''}`;
  } else if (diffDays < 30) {
    result = `${diffDays} day${diffDays !== 1 ? 's' : ''}`;
  } else if (diffMonths < 12) {
    result = `${diffMonths} month${diffMonths !== 1 ? 's' : ''}`;
  } else {
    result = `${diffYears} year${diffYears !== 1 ? 's' : ''}`;
  }

  return options?.addSuffix ? `${result} ago` : result;
}
