import 'dotenv/config';

function required(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Ortam değişkeni eksik: ${name} (.env dosyasını kontrol edin)`);
  }
  return value;
}

export const config = {
  telegramToken: required('TELEGRAM_BOT_TOKEN'),
  redditClientId: required('REDDIT_CLIENT_ID'),
  redditClientSecret: required('REDDIT_CLIENT_SECRET'),
  minComments: Number(process.env.MIN_COMMENTS ?? 10),
  scanIntervalMinutes: Number(process.env.SCAN_INTERVAL_MINUTES ?? 15),
  maxPostsPerScan: Number(process.env.MAX_POSTS_PER_SCAN ?? 5),
  topCommentsCount: Number(process.env.TOP_COMMENTS_COUNT ?? 5),
  redditUserAgent: process.env.REDDIT_USER_AGENT ?? 'reddit-telegram-bot/1.0 (by u/anonymous)',
};
