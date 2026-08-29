"use client";

import React, { useState, useEffect, useRef } from "react";
import { ChatSidebar } from "./chat-sidebar";
import { ChatMessageItem } from "./chat-message-item";
import { SSEParser } from "@/lib/sse-parser";
import { apiClientFetch, getApiUrl } from "@/lib/api-client";
import { Send, Loader2, MessageSquare } from "lucide-react";
import type { ChatSession, ChatMessage } from "@/types/chat";

interface ChatInterfaceProps {
  repositoryId: string;
  initialSessions: ChatSession[];
  accessToken?: string;
}

export function ChatInterface({ repositoryId, initialSessions, accessToken }: ChatInterfaceProps) {
  const [sessions, setSessions] = useState<ChatSession[]>(initialSessions);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(
    initialSessions.length > 0 ? initialSessions[0]!.id : null
  );
  
  const [messages, setMessages] = useState<any[]>([]);
  const [input, setInput] = useState("");
  
  const [isStreaming, setIsStreaming] = useState(false);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Load messages when active session changes
  useEffect(() => {
    if (!activeSessionId) {
      setMessages([]);
      return;
    }

    const loadMessages = async () => {
      setIsLoadingMessages(true);
      try {
        const res = await apiClientFetch(`/api/v1/chat/sessions/${activeSessionId}/messages`, {}, accessToken);
        if (res.ok) {
          const data = await res.json();
          // Backend orders ascending by created_at, so we can just set them
          setMessages(data);
        }
      } catch (e) {
        console.error("Failed to load messages", e);
      } finally {
        setIsLoadingMessages(false);
      }
    };

    loadMessages();
  }, [activeSessionId, accessToken]);

  const handleCreateSession = async () => {
    try {
      const res = await apiClientFetch("/api/v1/chat/sessions", {
        method: "POST",
        body: JSON.stringify({ repository_id: repositoryId }),
      }, accessToken);
      if (res.ok) {
        const newSession = await res.json();
        setSessions((prev) => [newSession, ...prev]);
        setActiveSessionId(newSession.id);
      }
    } catch (e) {
      console.error("Failed to create session", e);
    }
  };

  const handleRenameSession = async (id: string, title: string) => {
    if (!title.trim()) return;
    try {
      const res = await apiClientFetch(`/api/v1/chat/sessions/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ title }),
      }, accessToken);
      if (res.ok) {
        const updated = await res.json();
        setSessions((prev) => prev.map((s) => (s.id === id ? updated : s)));
      }
    } catch (e) {
      console.error("Failed to rename session", e);
    }
  };

  const handleTogglePin = async (id: string, isPinned: boolean) => {
    try {
      const res = await apiClientFetch(`/api/v1/chat/sessions/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ is_pinned: isPinned }),
      }, accessToken);
      if (res.ok) {
        const updated = await res.json();
        setSessions((prev) => prev.map((s) => (s.id === id ? updated : s)));
      }
    } catch (e) {
      console.error("Failed to pin session", e);
    }
  };

  const handleDeleteSession = async (id: string) => {
    try {
      const res = await apiClientFetch(`/api/v1/chat/sessions/${id}`, {
        method: "DELETE",
      }, accessToken);
      if (res.ok) {
        setSessions((prev) => prev.filter((s) => s.id !== id));
        if (activeSessionId === id) {
          setActiveSessionId(null);
        }
      }
    } catch (e) {
      console.error("Failed to delete session", e);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isStreaming || !activeSessionId) return;

    const userMessageContent = input.trim();
    setInput("");
    
    // Optimistically add user message and empty assistant message
    const tempUserMsg = { id: `user-${Date.now()}`, role: "user", content: userMessageContent };
    const tempAsstMsg = { id: `asst-${Date.now()}`, role: "assistant", content: "", sources: [] };
    
    setMessages((prev) => [...prev, tempUserMsg, tempAsstMsg]);
    setIsStreaming(true);

    try {
      const res = await fetch(getApiUrl(`/api/v1/chat/sessions/${activeSessionId}/stream`), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
        },
        body: JSON.stringify({ content: userMessageContent }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        setMessages((prev) => {
          const newMsgs = [...prev];
          newMsgs[newMsgs.length - 1].content = `**Error:** ${err.error?.message || res.statusText}`;
          return newMsgs;
        });
        setIsStreaming(false);
        return;
      }

      if (!res.body) {
        throw new Error("No response body");
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder("utf-8");
      const parser = new SSEParser();

      let streamDone = false;

      while (!streamDone) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const events = parser.parseChunk(chunk);

        for (const event of events) {
          if (event.data.done) {
            streamDone = true;
          } else if (event.data.error) {
            setMessages((prev) => {
              const newMsgs = [...prev];
              newMsgs[newMsgs.length - 1].content += `\n\n**Stream Error:** ${event.data.error}`;
              return newMsgs;
            });
            streamDone = true;
          } else if (event.data.content) {
            setMessages((prev) => {
              const newMsgs = [...prev];
              newMsgs[newMsgs.length - 1].content += event.data.content;
              return newMsgs;
            });
          } else if (event.data.sources) {
            // Some backend protocols emit sources at the end
            setMessages((prev) => {
              const newMsgs = [...prev];
              newMsgs[newMsgs.length - 1].sources = event.data.sources;
              return newMsgs;
            });
          }
        }
      }
    } catch (e: any) {
      console.error("Stream failed", e);
      setMessages((prev) => {
        const newMsgs = [...prev];
        newMsgs[newMsgs.length - 1].content += `\n\n**Network Error:** ${e.message}`;
        return newMsgs;
      });
    } finally {
      setIsStreaming(false);
      
      // Force a reload of messages to get the actual IDs and final sources from the DB
      // This is safe because we're done streaming
      const reloadRes = await apiClientFetch(`/api/v1/chat/sessions/${activeSessionId}/messages`, {}, accessToken);
      if (reloadRes.ok) {
        setMessages(await reloadRes.json());
      }
    }
  };

  return (
    <div className="flex h-[calc(100vh-8rem)] w-full overflow-hidden rounded-lg border border-line bg-background shadow-sm">
      <ChatSidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelectSession={setActiveSessionId}
        onCreateSession={handleCreateSession}
        onRenameSession={handleRenameSession}
        onTogglePin={handleTogglePin}
        onDeleteSession={handleDeleteSession}
        isLoading={isStreaming}
      />
      
      <div className="flex flex-1 flex-col overflow-hidden relative">
        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto">
          {!activeSessionId ? (
            <div className="flex h-full flex-col items-center justify-center text-ink-soft">
              <MessageSquare className="mb-4 h-12 w-12 opacity-20" />
              <p>Select a chat or start a new one.</p>
            </div>
          ) : isLoadingMessages ? (
            <div className="flex h-full items-center justify-center">
              <Loader2 className="h-8 w-8 animate-spin text-ink-soft opacity-50" />
            </div>
          ) : messages.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center text-ink-soft">
              <p>Send a message to start the conversation.</p>
            </div>
          ) : (
            <div className="pb-4">
              {messages.map((msg) => (
                <ChatMessageItem key={msg.id} message={msg} />
              ))}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="border-t border-line bg-surface p-4">
          <form onSubmit={handleSubmit} className="relative flex items-center">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={isStreaming || !activeSessionId}
              placeholder={activeSessionId ? "Ask a question about this repository..." : "Select a session first"}
              className="w-full rounded-md border border-line bg-background px-4 py-3 pr-12 text-sm text-ink placeholder-ink-soft shadow-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={!input.trim() || isStreaming || !activeSessionId}
              className="absolute right-2 flex h-8 w-8 items-center justify-center rounded bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
            >
              {isStreaming ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            </button>
          </form>
          <div className="mt-2 text-center text-xs text-ink-soft">
            GitBrain uses AI. Check for accuracy before trusting the output.
          </div>
        </div>
      </div>
    </div>
  );
}
