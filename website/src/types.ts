export interface ForumPost {
  link: string;
  title?: string;
  comment?: string;
  negativity_detected?: boolean;
  gpt_response?: string;
}

export interface ApiResponse<T> {
  success: boolean;
  error?: string;
  data?: T;
}