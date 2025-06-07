import { ForumPost } from "./types";

const API_URL = 'http://158.160.33.79:5000/api';

export const fetchForumLinks = async (): Promise<string[]> => {
  const response = await fetch(`${API_URL}/parse_forum`);
  const data = await response.json();
  if (data.success) {
    return data.links;
  }
  throw new Error(data.error || 'Failed to fetch forum links');
};

export const fetchTopicDetails = async (links: string[]): Promise<ForumPost[]> => {
  const response = await fetch(`${API_URL}/parse_topics`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ links }),
  });
  const data = await response.json();
  if (data.success) {
    return data.results;
  }
  throw new Error(data.error || 'Failed to fetch topic details');
};

export const checkNegativityBatch = async (posts: ForumPost[]): Promise<ForumPost[]> => {
  const response = await fetch(`${API_URL}/check_negativity_batch`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ posts }),
  });
  const data = await response.json();
  if (data.success) {
    return data.results;
  }
  throw new Error(data.error || 'Failed to check negativity');
};

export const sendForumPost = async (url: string, message: string): Promise<boolean> => {
  const response = await fetch(`${API_URL}/send_post`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ forum_url: url, message }),
  });
  const data = await response.json();
  return data.success;
};
