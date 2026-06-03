"use client";

import { useState, useEffect, useRef } from "react";
import { uploadPdf, getAdminStatus } from "@/lib/api";
import type { UploadStatus } from "@/lib/types";

type Step = "password" | "upload";

const MAX_FILE_SIZE_MB = 50;
const MAX_POLL_COUNT = 30; // 30 × 2s = 60s timeout

export default function FileUpload() {
  const [step, setStep] = useState<Step>("password");
  const [password, setPassword] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadStatus, setUploadStatus] = useState<UploadStatus>("idle");
  const [errorMessage, setErrorMessage] = useState("");
  const [showReplaceWarning, setShowReplaceWarning] = useState(false);
  const [fileInputKey, setFileInputKey] = useState(0); // P12: resets file input DOM on change

  // P5: useRef for interval ID avoids stale-closure issues with concurrent ticks
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  // P8: AbortController cancels in-flight fetches when effect cleans up
  const abortControllerRef = useRef<AbortController | null>(null);
  const pollCountRef = useRef(0);

  // Polling effect — only active while uploadStatus === "processing"
  useEffect(() => {
    if (uploadStatus !== "processing") return;

    pollCountRef.current = 0;
    abortControllerRef.current = new AbortController();

    intervalRef.current = setInterval(async () => {
      // P3: 60-second timeout — stops infinite spinner on hung backend
      pollCountRef.current += 1;
      if (pollCountRef.current >= MAX_POLL_COUNT) {
        setUploadStatus("failed");
        setErrorMessage("처리 시간이 초과되었습니다. 다시 시도해 주세요.");
        if (intervalRef.current) clearInterval(intervalRef.current);
        return;
      }

      try {
        const data = await getAdminStatus(
          password,
          abortControllerRef.current?.signal
        );
        if (data.status === "completed") {
          setUploadStatus("completed");
          setPassword(""); // P7: clear plaintext password from state after success
          if (intervalRef.current) clearInterval(intervalRef.current);
        } else if (data.status === "failed") {
          setUploadStatus("failed");
          if (data.error) setErrorMessage(data.error);
          if (intervalRef.current) clearInterval(intervalRef.current);
        }
      } catch (err) {
        // Ignore AbortError — component is unmounting, skip state update
        if (err instanceof Error && err.name === "AbortError") return;
        setUploadStatus("failed");
        if (intervalRef.current) clearInterval(intervalRef.current);
      }
    }, 2000);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      // P8: abort any in-flight status fetch when cleanup runs
      abortControllerRef.current?.abort();
    };
  }, [uploadStatus, password]);

  // D2: validate password against the server before entering the upload screen
  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!password.trim()) {
      setErrorMessage("비밀번호를 입력해 주세요.");
      return;
    }
    setErrorMessage("");

    try {
      await getAdminStatus(password);
      setStep("upload");
    } catch (err) {
      if (err instanceof Error && err.message === "UNAUTHORIZED") {
        setErrorMessage("비밀번호가 올바르지 않습니다.");
      } else {
        setErrorMessage("서버에 연결할 수 없습니다. 백엔드가 실행 중인지 확인해 주세요.");
      }
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) return;

    // P10: client-side validation before making a network call
    const isPdf =
      selectedFile.name.toLowerCase().endsWith(".pdf") ||
      selectedFile.type === "application/pdf";
    if (!isPdf) {
      setErrorMessage("PDF 파일만 업로드 가능합니다.");
      return;
    }
    if (selectedFile.size > MAX_FILE_SIZE_MB * 1024 * 1024) {
      setErrorMessage(`파일 크기는 ${MAX_FILE_SIZE_MB}MB 이하여야 합니다.`);
      return;
    }

    setShowReplaceWarning(true);
    setErrorMessage("");

    try {
      await uploadPdf(selectedFile, password);
      // P1: set "processing" only after POST succeeds — prevents polling a stale previous status
      setUploadStatus("processing");
    } catch (err) {
      // P4: always reset warning on failure so retry starts clean
      setShowReplaceWarning(false);
      if (err instanceof Error && err.message === "UNAUTHORIZED") {
        setErrorMessage("비밀번호가 올바르지 않습니다.");
        setStep("password");
        setPassword("");
        setSelectedFile(null);
        setFileInputKey((k) => k + 1); // P12: reset file input DOM
      } else {
        setUploadStatus("failed");
      }
    }
  };

  // P2: retry resets everything back to idle for a clean re-attempt
  const handleRetry = () => {
    setUploadStatus("idle");
    setShowReplaceWarning(false);
    setSelectedFile(null);
    setErrorMessage("");
    setFileInputKey((k) => k + 1); // P12: reset file input DOM
  };

  if (step === "password") {
    return (
      <form onSubmit={handlePasswordSubmit} className="flex flex-col gap-4">
        <div className="flex flex-col gap-2">
          <label
            htmlFor="password"
            className="text-sm font-medium text-gray-700"
          >
            관리자 비밀번호
          </label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="비밀번호를 입력하세요"
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
          />
        </div>
        {errorMessage && (
          <p className="text-sm text-red-600">{errorMessage}</p>
        )}
        <button
          type="submit"
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700"
        >
          확인
        </button>
      </form>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <form onSubmit={handleUpload} className="flex flex-col gap-4">
        <div className="flex flex-col gap-2">
          <label
            htmlFor="pdfFile"
            className="text-sm font-medium text-gray-700"
          >
            PDF 파일 선택
          </label>
          <input
            key={fileInputKey}
            id="pdfFile"
            type="file"
            accept=".pdf"
            onChange={(e) => setSelectedFile(e.target.files?.[0] ?? null)}
            disabled={uploadStatus === "processing"}
            className="text-sm text-gray-600 file:mr-4 file:rounded-lg file:border-0 file:bg-blue-50 file:px-4 file:py-2 file:text-sm file:font-medium file:text-blue-700 hover:file:bg-blue-100"
          />
        </div>

        {showReplaceWarning && (
          <p className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-700">
            기존 규정 파일을 새 파일로 교체합니다.
          </p>
        )}

        {uploadStatus === "idle" && (
          <button
            type="submit"
            disabled={!selectedFile}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            업로드
          </button>
        )}

        {uploadStatus === "processing" && (
          <div className="flex items-center gap-2 text-sm text-blue-600">
            <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" />
            처리 중...
          </div>
        )}
      </form>

      {uploadStatus === "completed" && (
        <div className="rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700">
          업로드 완료
        </div>
      )}

      {/* P2: retry button — shown after any failure so user can re-attempt without page refresh */}
      {uploadStatus === "failed" && (
        <div className="flex flex-col gap-2">
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {errorMessage || "처리 실패. 다시 시도해 주세요."}
          </div>
          <button
            type="button"
            onClick={handleRetry}
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50"
          >
            다시 시도
          </button>
        </div>
      )}

      {uploadStatus !== "failed" && errorMessage && (
        <p className="text-sm text-red-600">{errorMessage}</p>
      )}
    </div>
  );
}
