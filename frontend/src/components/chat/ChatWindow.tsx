"use client";

import { useState, useRef, useEffect } from "react";
import ChatMessageComponent from "@/components/chat/ChatMessage";
import ChatInput from "@/components/chat/ChatInput";
import { sendChatMessage } from "@/lib/api";
import type { ChatMessage } from "@/lib/types";

export default function ChatWindow() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const keyCounterRef = useRef(0);
  const nextKey = () => `msg-${++keyCounterRef.current}`;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, errorMessage]);

  // Abort in-flight request on unmount
  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  const handleSend = async (question: string) => {
    setErrorMessage(null);

    const userMessage: ChatMessage = { _key: nextKey(), role: "user", content: question };
    // history = prior conversation only (excludes current question, which is sent separately)
    const history = messages.map(({ role, content }) => ({ role, content }));

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    abortControllerRef.current?.abort();  // cancel any previous in-flight request
    abortControllerRef.current = new AbortController();

    try {
      const res = await sendChatMessage(question, history, abortControllerRef.current.signal);

      const botMessage: ChatMessage = {
        _key: nextKey(),
        role: "assistant",
        content: res.answer,
        sources: res.sources,
      };
      setMessages((prev) => [...prev, botMessage]);
    } catch (err) {
      if (err instanceof Error && err.name === "AbortError") return;
      setErrorMessage("서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="mx-auto flex max-w-2xl flex-col gap-4">
          {messages.length === 0 && !errorMessage && (
            <p className="text-center text-sm text-gray-400">
              규정에 대해 궁금한 점을 질문해 보세요.
            </p>
          )}
          {messages.map((msg) => (
            <ChatMessageComponent key={msg._key} message={msg} />
          ))}
          {errorMessage && (
            <p className="text-center text-sm text-red-500">{errorMessage}</p>
          )}
          <div ref={bottomRef} />
        </div>
      </div>

      <div className="mx-auto w-full max-w-2xl">
        <ChatInput onSend={handleSend} isLoading={isLoading} />
      </div>
    </div>
  );
}
