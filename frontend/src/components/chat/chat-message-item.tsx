"use client";

import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import { Check, Copy, User, Bot, FileCode2 } from "lucide-react";
import type { ChatMessage } from "@/types/chat";

interface ChatMessageItemProps {
  message: ChatMessage | { id: string; role: "user" | "assistant"; content: string; sources?: any[] };
}

export function ChatMessageItem({ message }: ChatMessageItemProps) {
  const isUser = message.role === "user";

  return (
    <div className={`flex gap-4 p-6 ${isUser ? "bg-surface" : "bg-muted"}`}>
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
        {isUser ? <User className="h-5 w-5" /> : <Bot className="h-5 w-5" />}
      </div>
      <div className="min-w-0 flex-1 space-y-4">
        <div className="prose prose-sm dark:prose-invert max-w-none break-words">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              code({ node, inline, className, children, ...props }: any) {
                const match = /language-(\w+)/.exec(className || "");
                const codeString = String(children).replace(/\n$/, "");

                if (!inline && match && match[1]) {
                  return (
                    <CodeBlock language={match[1]} value={codeString} />
                  );
                } else if (!inline) {
                  return <CodeBlock language="text" value={codeString} />;
                }
                return (
                  <code className="rounded bg-accent px-1.5 py-0.5 text-accent-foreground font-mono text-sm" {...props}>
                    {children}
                  </code>
                );
              },
            }}
          >
            {message.content}
          </ReactMarkdown>
        </div>

        {/* Source Citations */}
        {message.sources && message.sources.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-2">
            {message.sources.map((source: any, idx: number) => (
              <div
                key={`${source.source_id}-${idx}`}
                className="flex items-center gap-1.5 rounded-md border border-line bg-surface px-2.5 py-1 text-xs text-ink-soft transition-colors hover:bg-accent hover:text-accent-foreground"
                title={`Score: ${source.score?.toFixed(3)}`}
              >
                <FileCode2 className="h-3 w-3" />
                <span className="max-w-[200px] truncate">{source.label}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function CodeBlock({ language, value }: { language: string; value: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(value);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="relative my-4 rounded-md border border-line bg-[#1E1E1E] overflow-hidden">
      <div className="flex items-center justify-between bg-zinc-900 px-4 py-1.5">
        <span className="text-xs font-medium text-zinc-400">{language}</span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 text-xs text-zinc-400 transition-colors hover:text-white"
        >
          {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
          {copied ? "Copied!" : "Copy"}
        </button>
      </div>
      <div className="overflow-x-auto p-4 text-sm">
        <SyntaxHighlighter
          language={language}
          style={vscDarkPlus}
          customStyle={{ margin: 0, padding: 0, background: "transparent" }}
        >
          {value}
        </SyntaxHighlighter>
      </div>
    </div>
  );
}
