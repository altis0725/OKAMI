import { useRef, useEffect, useState } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ChatMessage } from "./chat-message";
import { ChatInput } from "./chat-input";
import { Message } from "@/types/chat";
import { Bot } from "lucide-react";
import { useTheme } from "next-themes";
import { OkamichanIcon } from "@/components/ui/okamichan-icon";

interface ChatProps {
  messages: Message[];
  onSendMessage: (message: string) => void;
  isLoading?: boolean;
  disabled?: boolean;
  welcomeTitle?: string;
}

export function Chat({ messages, onSendMessage, isLoading = false, disabled = false, welcomeTitle }: ChatProps) {
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const { theme } = useTheme();
  const [mounted, setMounted] = useState(false);
  useEffect(() => { setMounted(true); }, []);

  // 新しいメッセージが追加されたときに自動スクロール
  useEffect(() => {
    if (scrollAreaRef.current) {
      scrollAreaRef.current.scrollTop = scrollAreaRef.current.scrollHeight;
    }
  }, [messages]);

  const titleColor = !mounted ? "" : theme === "dark" ? "text-white" : "text-gray-900";
  const descColor = !mounted ? "" : theme === "dark" ? "text-gray-400" : "text-gray-600";

  return (
    <div className="flex flex-col h-full w-full">
      <div className="flex-1 overflow-auto" ref={scrollAreaRef}>
                 <div className="flex flex-col items-center justify-center min-h-[60vh] py-16 px-2">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center p-8 w-full max-w-2xl mx-auto">
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               <div className="w-32 h-32 rounded-full bg-primary/10 flex items-center justify-center mb-0 mt-4">
                 <OkamichanIcon 
                   className="h-28 w-28" 
                   isDark={mounted && theme === "dark"}
                 />
               </div>
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               <p className={`${descColor} max-w-md text-base mb-2`}>
                      いつもあなたのそばに
                     </p>
                     <h2 className={`text-4xl font-bold mb-2 ${titleColor}`}>{welcomeTitle || "お手伝いできることはありますか？"}</h2>
               <div className="w-full">
                 <ChatInput
                   onSendMessage={onSendMessage}
                   isLoading={isLoading}
                   disabled={disabled}
                 />
               </div>
            </div>
          ) : (
            <div className="w-full max-w-2xl flex flex-col gap-4 mx-auto">
              {messages.map((message) => (
                <ChatMessage key={message.id} message={message} />
              ))}
              {isLoading && (
                <div className="flex items-start gap-3 p-4">
                  <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                    <Bot className="h-4 w-4 text-primary" />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-sm font-medium text-white">Okamichan</span>
                      <span className="text-xs text-gray-400">入力中...</span>
                    </div>
                    <div className="flex space-x-1">
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "0.1s" }} />
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "0.2s" }} />
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
      {messages.length > 0 && (
        <div className="w-full max-w-2xl mx-auto pb-2 px-2">
          <ChatInput
            onSendMessage={onSendMessage}
            isLoading={isLoading}
            disabled={disabled}
          />
        </div>
      )}
    </div>
  );
} 