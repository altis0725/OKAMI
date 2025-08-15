import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Message } from "@/types/chat";
import { Bot, User } from "lucide-react";
import { cn } from "@/lib/utils";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface ChatMessageProps {
  message: Message;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === "user";

  return (
    <div
      className={cn(
        "flex w-full items-end gap-3",
        isUser ? "justify-end" : "justify-start"
      )}
    >
      {!isUser && (
        <Avatar className="h-8 w-8">
          <AvatarImage src="/ai-avatar.png" alt="AI Assistant" />
          <AvatarFallback className="bg-[#10a37f] text-white">
            <Bot className="h-4 w-4" />
          </AvatarFallback>
        </Avatar>
      )}
      <div
        className={cn(
          "flex flex-col gap-1 max-w-[80%]",
          isUser ? "items-end" : "items-start"
        )}
      >
        <div
          className={cn(
            "rounded-xl px-4 py-3 text-sm break-words",
            isUser
              ? "bg-[#2a2b32] text-white rounded-br-md whitespace-pre-wrap"
              : message.isError
              ? "bg-red-500/20 text-red-200 border border-red-500/50 rounded-bl-md whitespace-pre-wrap"
              : "bg-[#444654] text-white rounded-bl-md"
          )}
        >
          {isUser || message.isError ? (
            <>
              {message.content}
              {message.isStreaming && (
                <span className="inline-block w-2 h-4 bg-current animate-pulse ml-1" />
              )}
            </>
          ) : (
            <div className="prose prose-invert prose-sm max-w-none">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  // カスタムスタイリング
                  h1: ({ children }) => <h1 className="text-lg font-bold mb-2 text-white">{children}</h1>,
                  h2: ({ children }) => <h2 className="text-base font-semibold mb-2 text-white">{children}</h2>,
                  h3: ({ children }) => <h3 className="text-sm font-medium mb-1 text-white">{children}</h3>,
                  p: ({ children }) => <p className="mb-2 text-white leading-relaxed">{children}</p>,
                  code: ({ inline, children, ...props }: any) => 
                    inline ? (
                      <code className="bg-gray-700 text-gray-100 px-1 py-0.5 rounded text-xs" {...props}>{children}</code>
                    ) : (
                      <code className="block bg-gray-800 text-gray-100 p-2 rounded text-xs overflow-x-auto" {...props}>{children}</code>
                    ),
                  pre: ({ children }) => <pre className="bg-gray-800 text-gray-100 p-3 rounded mb-2 overflow-x-auto">{children}</pre>,
                  ul: ({ children }) => <ul className="list-disc list-inside mb-2 text-white">{children}</ul>,
                  ol: ({ children }) => <ol className="list-decimal list-inside mb-2 text-white">{children}</ol>,
                  li: ({ children }) => <li className="mb-1 text-white">{children}</li>,
                  blockquote: ({ children }) => <blockquote className="border-l-4 border-gray-500 pl-3 italic text-gray-300 mb-2">{children}</blockquote>,
                  a: ({ href, children }) => <a href={href} className="text-blue-300 hover:text-blue-200 underline" target="_blank" rel="noopener noreferrer">{children}</a>,
                  table: ({ children }) => <table className="border-collapse border border-gray-600 mb-2">{children}</table>,
                  th: ({ children }) => <th className="border border-gray-600 px-2 py-1 bg-gray-700 text-white font-medium">{children}</th>,
                  td: ({ children }) => <td className="border border-gray-600 px-2 py-1 text-white">{children}</td>,
                }}
              >
                {message.content}
              </ReactMarkdown>
              {message.isStreaming && (
                <span className="inline-block w-2 h-4 bg-current animate-pulse ml-1" />
              )}
            </div>
          )}
        </div>
        <span className="text-xs text-gray-400 mt-1">
          {message.timestamp.toLocaleTimeString()}
        </span>
      </div>
      {isUser && (
        <Avatar className="h-8 w-8">
          <AvatarImage src="/user-avatar.png" alt="User" />
          <AvatarFallback className="bg-gray-500 text-white">
            <User className="h-4 w-4" />
          </AvatarFallback>
        </Avatar>
      )}
    </div>
  );
} 