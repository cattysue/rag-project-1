import type { Metadata } from "next";
import ChatWindow from "@/components/chat/ChatWindow";

export const metadata: Metadata = {
  title: "규정이 — 학업성적관리규정 챗봇",
  description: "K고 학업성적관리규정에 대해 질문하세요",
};

export default function Home() {
  return (
    <main className="flex flex-1 flex-col overflow-hidden">
      <header className="border-b border-gray-200 bg-white px-4 py-3">
        <div className="mx-auto max-w-2xl">
          <h1 className="text-lg font-semibold text-gray-900">규정이</h1>
          <p className="text-xs text-gray-500">학업성적관리규정 안내 챗봇</p>
        </div>
      </header>

      <ChatWindow />
    </main>
  );
}
