export interface RedditPost {
  id: string;
  title: string;
  author: string;
  subreddit: string;
  score: number;
  numComments: number;
  permalink: string;
  url: string;
  createdUtc: number;
}

export interface RedditComment {
  author: string;
  body: string;
  score: number;
}

export interface ChatState {
  subreddits: string[];
  seenPostIds: { [subreddit: string]: string[] };
}

export interface SubscriptionStore {
  [chatId: string]: ChatState;
}
