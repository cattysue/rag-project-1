import type { Metadata } from "next";
import FileUpload from "@/components/admin/FileUpload";

export const metadata: Metadata = {
  title: "관리자 페이지 - 규정이",
  description: "규정 PDF 업로드 관리",
};

export default function AdminPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-gray-50 px-4 py-12">
      <div className="w-full max-w-md rounded-xl border border-gray-200 bg-white p-8 shadow-sm">
        <h1 className="mb-6 text-xl font-semibold text-gray-900">
          관리자 페이지
        </h1>
        <FileUpload />
      </div>
    </main>
  );
}
