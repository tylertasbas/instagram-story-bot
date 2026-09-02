import fs from 'fs/promises';
import path from 'path';
import { ChatState, SubscriptionStore } from './types';

const DATA_FILE = path.join(__dirname, '..', 'data', 'subscriptions.json');
const MAX_SEEN_PER_SUBREDDIT = 500;

let store: SubscriptionStore = {};
let loaded = false;

async function ensureLoaded(): Promise<void> {
  if (loaded) return;
  try {
    const raw = await fs.readFile(DATA_FILE, 'utf-8');
    store = JSON.parse(raw);
  } catch {
    store = {};
  }
  loaded = true;
}

async function persist(): Promise<void> {
  await fs.mkdir(path.dirname(DATA_FILE), { recursive: true });
  await fs.writeFile(DATA_FILE, JSON.stringify(store, null, 2), 'utf-8');
}

function getOrCreateChat(chatId: string): ChatState {
  if (!store[chatId]) {
    store[chatId] = { subreddits: [], seenPostIds: {} };
  }
  return store[chatId];
}

export async function addSubreddit(chatId: string, subreddit: string): Promise<boolean> {
  await ensureLoaded();
  const chat = getOrCreateChat(chatId);
  const normalized = subreddit.toLowerCase();
  if (chat.subreddits.includes(normalized)) return false;
  chat.subreddits.push(normalized);
  await persist();
  return true;
}

export async function removeSubreddit(chatId: string, subreddit: string): Promise<boolean> {
  await ensureLoaded();
  const chat = getOrCreateChat(chatId);
  const normalized = subreddit.toLowerCase();
  const index = chat.subreddits.indexOf(normalized);
  if (index === -1) return false;
  chat.subreddits.splice(index, 1);
  delete chat.seenPostIds[normalized];
  await persist();
  return true;
}

export async function listSubreddits(chatId: string): Promise<string[]> {
  await ensureLoaded();
  return getOrCreateChat(chatId).subreddits;
}

export async function getAllChats(): Promise<Array<{ chatId: string; subreddits: string[] }>> {
  await ensureLoaded();
  return Object.entries(store).map(([chatId, state]) => ({ chatId, subreddits: state.subreddits }));
}

export async function isSeen(chatId: string, subreddit: string, postId: string): Promise<boolean> {
  await ensureLoaded();
  const chat = getOrCreateChat(chatId);
  return (chat.seenPostIds[subreddit] ?? []).includes(postId);
}

export async function markSeen(chatId: string, subreddit: string, postIds: string[]): Promise<void> {
  await ensureLoaded();
  const chat = getOrCreateChat(chatId);
  const existing = chat.seenPostIds[subreddit] ?? [];
  const merged = [...existing, ...postIds.filter((id) => !existing.includes(id))];
  chat.seenPostIds[subreddit] = merged.slice(-MAX_SEEN_PER_SUBREDDIT);
  await persist();
}
