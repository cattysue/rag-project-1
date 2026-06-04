export type UploadStatus = "idle" | "processing" | "completed" | "failed";

export interface AdminStatus {
  status: UploadStatus;
  error?: string;
}

export interface UploadResponse {
  status: UploadStatus;
}

export type ChatRole = "user" | "assistant";

export interface Source {
  article_number: string | null;
  article_title: string | null;
}

export interface ChatMessage {
  _key?: string;  // client-side stable render key; never sent to backend
  role: ChatRole;
  content: string;
  sources?: Source[];
}

export interface ChatRequest {
  question: string;
  messages: { role: ChatRole; content: string }[];
}

export interface ChatResponse {
  answer: string;
  sources: Source[];
}
