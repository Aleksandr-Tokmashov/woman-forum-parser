export interface Thread {
  link: string;
  title: string;
  comment: string;
  date?: string;
  is_negative: boolean;
  gpt_response?: string;
  is_answer_sent: boolean;
}

export interface ApiResponse {
  success: boolean;
  error?: string;
  links?: string[];
  results?: Thread[];
  count?: number;
}