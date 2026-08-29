"use client";

import { MessageSquare, Pin, Plus, Trash2, Edit2 } from "lucide-react";
import type { ChatSession } from "@/types/chat";

interface ChatSidebarProps {
  sessions: ChatSession[];
  activeSessionId: string | null;
  onSelectSession: (id: string) => void;
  onCreateSession: () => void;
  onRenameSession: (id: string, title: string) => void;
  onTogglePin: (id: string, isPinned: boolean) => void;
  onDeleteSession: (id: string) => void;
  isLoading: boolean;
}

export function ChatSidebar({
  sessions,
  activeSessionId,
  onSelectSession,
  onCreateSession,
  onRenameSession,
  onTogglePin,
  onDeleteSession,
  isLoading,
}: ChatSidebarProps) {
  const pinnedSessions = sessions.filter((s) => s.is_pinned);
  const unpinnedSessions = sessions.filter((s) => !s.is_pinned);

  const renderSession = (session: ChatSession) => {
    const isActive = activeSessionId === session.id;
    return (
      <div
        key={session.id}
        className={`group flex cursor-pointer items-center justify-between rounded-md p-2 text-sm transition-colors ${
          isActive ? "bg-accent text-accent-foreground" : "text-ink-soft hover:bg-muted hover:text-ink"
        }`}
        onClick={() => onSelectSession(session.id)}
      >
        <div className="flex items-center gap-2 overflow-hidden">
          <MessageSquare className="h-4 w-4 shrink-0" />
          <span className="truncate">{session.title || "New Chat"}</span>
        </div>
        <div className="flex shrink-0 gap-1 opacity-0 transition-opacity group-hover:opacity-100">
          <button
            onClick={(e) => {
              e.stopPropagation();
              onTogglePin(session.id, !session.is_pinned);
            }}
            className="p-1 hover:text-ink"
            title={session.is_pinned ? "Unpin" : "Pin"}
          >
            <Pin className={`h-3 w-3 ${session.is_pinned ? "fill-current" : ""}`} />
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              const newTitle = prompt("Enter new title:", session.title || "");
              if (newTitle !== null) onRenameSession(session.id, newTitle);
            }}
            className="p-1 hover:text-ink"
            title="Rename"
          >
            <Edit2 className="h-3 w-3" />
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              if (confirm("Are you sure you want to delete this chat?")) onDeleteSession(session.id);
            }}
            className="p-1 text-red-500 hover:text-red-700"
            title="Delete"
          >
            <Trash2 className="h-3 w-3" />
          </button>
        </div>
      </div>
    );
  };

  return (
    <div className="flex h-full w-64 flex-col border-r border-line bg-surface">
      <div className="p-4">
        <button
          onClick={onCreateSession}
          disabled={isLoading}
          className="flex w-full items-center justify-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          <Plus className="h-4 w-4" />
          New Chat
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 pt-0">
        {pinnedSessions.length > 0 && (
          <div className="mb-6">
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-ink-soft">Pinned</h3>
            <div className="space-y-1">{pinnedSessions.map(renderSession)}</div>
          </div>
        )}

        <div>
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-ink-soft">Recent</h3>
          {unpinnedSessions.length === 0 && pinnedSessions.length === 0 ? (
            <p className="text-xs text-ink-soft">No chat sessions yet.</p>
          ) : (
            <div className="space-y-1">{unpinnedSessions.map(renderSession)}</div>
          )}
        </div>
      </div>
    </div>
  );
}
