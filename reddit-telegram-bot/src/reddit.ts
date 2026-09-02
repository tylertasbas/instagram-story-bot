import { config } from './config';
import { RedditComment, RedditPost } from './types';

interface RedditListingChild<T> {
  kind: string;
  data: T;
}

interface RedditListing<T> {
  data: {
    children: RedditListingChild<T>[];
  };
}

interface RawPostData {
  id: string;
  title: string;
  author: string;
  subreddit: string;
  score: number;
  num_comments: number;
  permalink: string;
  url: string;
  created_utc: number;
  stickied: boolean;
  over_18: boolean;
}

interface RawCommentData {
  author: string;
  body: string;
  score: number;
}

let cachedToken: { token: string; expiresAt: number } | null = null;

async function getAccessToken(): Promise<string> {
  if (cachedToken && cachedToken.expiresAt > Date.now() + 30_000) {
    return cachedToken.token;
  }

  const basicAuth = Buffer.from(`${config.redditClientId}:${config.redditClientSecret}`).toString('base64');
  const res = await fetch('https://www.reddit.com/api/v1/access_token', {
    method: 'POST',
    headers: {
      Authorization: `Basic ${basicAuth}`,
      'Content-Type': 'application/x-www-form-urlencoded',
      'User-Agent': config.redditUserAgent,
    },
    body: 'grant_type=client_credentials',
  });

  if (!res.ok) {
    throw new Error(`Reddit OAuth token alınamadı (${res.status}): ${await res.text()}`);
  }

  const json = (await res.json()) as { access_token: string; expires_in: number };
  cachedToken = { token: json.access_token, expiresAt: Date.now() + json.expires_in * 1000 };
  return cachedToken.token;
}

async function redditFetch(path: string): Promise<any> {
  const token = await getAccessToken();
  const res = await fetch(`https://oauth.reddit.com${path}`, {
    headers: {
      Authorization: `Bearer ${token}`,
      'User-Agent': config.redditUserAgent,
    },
  });

  if (res.status === 401) {
    cachedToken = null;
    throw new Error(`Reddit isteği yetkisiz (401), token yenilenecek: ${path}`);
  }
  if (!res.ok) {
    throw new Error(`Reddit isteği başarısız (${res.status}): ${path}`);
  }
  return res.json();
}

export async function fetchNewPosts(subreddit: string): Promise<RedditPost[]> {
  const json = (await redditFetch(
    `/r/${encodeURIComponent(subreddit)}/new?limit=25&raw_json=1`
  )) as RedditListing<RawPostData>;

  return json.data.children
    .filter((child) => child.kind === 't3' && !child.data.stickied)
    .map((child) => ({
      id: child.data.id,
      title: child.data.title,
      author: child.data.author,
      subreddit: child.data.subreddit,
      score: child.data.score,
      numComments: child.data.num_comments,
      permalink: `https://www.reddit.com${child.data.permalink}`,
      url: child.data.url,
      createdUtc: child.data.created_utc,
    }));
}

export async function fetchTopComments(
  subreddit: string,
  postId: string,
  count: number
): Promise<RedditComment[]> {
  const json = (await redditFetch(
    `/r/${encodeURIComponent(subreddit)}/comments/${postId}?limit=${count}&sort=top&raw_json=1`
  )) as RedditListing<RawPostData | RawCommentData>[];

  const commentListing = json[1] as RedditListing<RawCommentData>;
  if (!commentListing?.data?.children) return [];

  return commentListing.data.children
    .filter((child) => child.kind === 't1')
    .map((child) => child.data as RawCommentData)
    .filter((c) => c.body && c.body !== '[deleted]' && c.body !== '[removed]')
    .slice(0, count)
    .map((c) => ({ author: c.author, body: c.body, score: c.score }));
}
