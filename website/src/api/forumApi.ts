// api/forumApi.ts
const API_URL = 'http://localhost:5000/api';

interface ThreadContent {
  title?: string;
  content?: string;
  date?: string;
}

interface AnalysisResult {
  negativity_detected: boolean;
  constructive_response?: string;
}

export const fetchForumThreads = async (): Promise<string[]> => {
  const response = await fetch(`${API_URL}/parse_forum`);
  const data = await response.json();
  return data.links || [];
};

export const fetchThreadContent = async (url: string): Promise<ThreadContent> => {
  const response = await fetch(`${API_URL}/parse_topic?url=${encodeURIComponent(url)}`);
  return response.json();
};

export const analyzeText = async (text: string): Promise<AnalysisResult> => {
  const response = await fetch(`${API_URL}/analyze_text`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text })
  });
  return response.json();
};

export const sendForumResponse = async (url: string, message: string): Promise<boolean> => {
  const response = await fetch(`${API_URL}/send_post`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ forum_url: url, message })
  });
  const data = await response.json();
  return data.success || false;
};

export const sendForumPost = async (forumUrl: string, message: string): Promise<boolean> => {
  const response = await fetch(`${API_URL}/send_post`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ forum_url: forumUrl, message }),
  });
  const data = await response.json();
  return data.success;
};