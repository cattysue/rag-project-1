export type UploadStatus = "idle" | "processing" | "completed" | "failed";

export interface AdminStatus {
  status: UploadStatus;
  error?: string;
}

export interface UploadResponse {
  status: UploadStatus;
}
