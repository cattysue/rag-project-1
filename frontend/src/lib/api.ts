import type { AdminStatus, UploadResponse, ChatRequest, ChatResponse } from "@/lib/types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// P9: warn on missing env var so production misconfiguration is visible in the browser console
if (!process.env.NEXT_PUBLIC_API_URL) {
  console.warn(
    "[규정이] NEXT_PUBLIC_API_URL이 설정되지 않았습니다. http://localhost:8000으로 연결합니다."
  );
}

const VALID_STATUSES = ["idle", "processing", "completed", "failed"] as const;

export async function uploadPdf(
  file: File,
  password: string,
  signal?: AbortSignal
): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${BASE_URL}/admin/upload`, {
    method: "POST",
    headers: { Authorization: password },
    body: formData,
    signal,
    // Content-Type은 FormData일 때 브라우저가 boundary와 함께 자동 설정
  });

  if (res.status === 401) throw new Error("UNAUTHORIZED");
  if (!res.ok) throw new Error("UPLOAD_FAILED");
  return res.json();
}

// D2: password required — backend GET /admin/status uses Depends(verify_admin)
export async function getAdminStatus(
  password: string,
  signal?: AbortSignal
): Promise<AdminStatus> {
  const res = await fetch(`${BASE_URL}/admin/status`, {
    headers: { Authorization: password },
    signal,
  });

  if (res.status === 401) throw new Error("UNAUTHORIZED");
  if (!res.ok) throw new Error("STATUS_FETCH_FAILED");

  const data = await res.json();

  // P6: runtime validation — unexpected status values would cause infinite polling
  if (!VALID_STATUSES.includes(data.status)) {
    throw new Error(`INVALID_STATUS:${data.status}`);
  }

  return data as AdminStatus;
}

export async function sendChatMessage(
  question: string,
  messages: ChatRequest["messages"],
  signal?: AbortSignal
): Promise<ChatResponse> {
  const res = await fetch(`${BASE_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, messages }),
    signal,
  });

  if (!res.ok) throw new Error("CHAT_FAILED");
  return res.json();
}
