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

async function redditFetch(url: string): Promise<any> {
  const res = await fetch(url, {
    headers: { 'User-Agent': config.redditUserAgent },
  });
  if (!res.ok) {
    throw new Error(`Reddit isteği başarısız (${res.status}): ${url}`);
  }
  return res.json();
}

export async function fetchNewPosts(subreddit: string): Promise<RedditPost[]> {
  const json = (await redditFetch(
    `https://www.reddit.com/r/${encodeURIComponent(subreddit)}/new.json?limit=25&raw_json=1`
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
    `https://www.reddit.com/r/${encodeURIComponent(subreddit)}/comments/${postId}.json?limit=${count}&sort=top&raw_json=1`
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
