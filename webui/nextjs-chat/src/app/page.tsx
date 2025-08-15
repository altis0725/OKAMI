"use client";

import { useState, useCallback, useEffect } from "react";
import { Sidebar } from "@/components/sidebar";
import { Chat } from "@/components/chat";
import { Message, ChatSession } from "@/types/chat";

export default function Home() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | undefined>();
  const [isLoading, setIsLoading] = useState(false);

  const currentSession = sessions.find(s => s.id === currentSessionId);
  
  // デバッグ用ログ
  useEffect(() => {
    console.log('[Debug] currentSessionId:', currentSessionId);
    console.log('[Debug] sessions:', sessions);
    console.log('[Debug] currentSession:', currentSession);
    console.log('[Debug] messages:', currentSession?.messages);
  }, [currentSessionId, sessions, currentSession]);

  const createNewSession = useCallback(() => {
    const newSession: ChatSession = {
      id: Date.now().toString(),
      title: "新しいチャット",
      messages: [],
      createdAt: new Date(),
      updatedAt: new Date(),
    };
    
    setSessions(prev => [newSession, ...prev]);
    setCurrentSessionId(newSession.id);
  }, []);

  const deleteSession = useCallback((sessionId: string) => {
    setSessions(prev => prev.filter(s => s.id !== sessionId));
    if (currentSessionId === sessionId) {
      setCurrentSessionId(sessions[0]?.id);
    }
  }, [currentSessionId, sessions]);

  const renameSession = useCallback((sessionId: string, newTitle: string) => {
    setSessions(prev => prev.map(session =>
      session.id === sessionId ? { ...session, title: newTitle, updatedAt: new Date() } : session
    ));
  }, []);

  // お気に入り追加・解除
  const toggleFavoriteSession = useCallback((sessionId: string) => {
    setSessions(prev => prev.map(session =>
      session.id === sessionId ? { ...session, isFavorite: !session.isFavorite } : session
    ));
  }, []);

  const handleSendMessage = useCallback(async (content: string, files?: File[]) => {
    console.log('[handleSendMessage] 開始', { content, filesCount: files?.length, currentSessionId });
    
    // 新しいセッションIDを作成（必要な場合）
    let sessionId = currentSessionId;
    if (!sessionId) {
      const newSession: ChatSession = {
        id: Date.now().toString(),
        title: content.slice(0, 30) + "...",
        messages: [],
        createdAt: new Date(),
        updatedAt: new Date(),
      };
      
      console.log('[handleSendMessage] 新しいセッション作成', newSession.id);
      setSessions(prev => [newSession, ...prev]);
      setCurrentSessionId(newSession.id);
      sessionId = newSession.id;
    }

    const userMessage: Message = {
      id: Date.now().toString(),
      content: files && files.length > 0 
        ? `${content}${content ? '\n\n' : ''}添付ファイル: ${files.map(f => f.name).join(', ')}`
        : content,
      role: "user",
      timestamp: new Date(),
    };

    console.log('[handleSendMessage] ユーザーメッセージ作成', userMessage);

    // ユーザーメッセージを追加
    setSessions(prev => prev.map(session => {
      if (session.id === sessionId) {
        console.log('[handleSendMessage] セッションにユーザーメッセージ追加', sessionId);
        return {
          ...session,
          messages: [...session.messages, userMessage],
          updatedAt: new Date(),
          title: session.messages.length === 0 ? content.slice(0, 30) + "..." : session.title,
        };
      }
      return session;
    }));

    setIsLoading(true);

    try {
      console.log('[handleSendMessage] API呼び出し開始');
      
      // APIのベースURLを決定（本番環境では同一オリジン、開発環境ではlocalhost:8000）
      const apiBase = typeof window !== 'undefined' && window.location.hostname !== 'localhost' 
        ? '' // 本番環境では同一オリジン
        : 'http://localhost:8000'; // 開発環境
      
      // OKAMIバックエンドAPIを直接呼び出し
      const response = await fetch(`${apiBase}/tasks`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          crew_name: 'main_crew',
          task: content,
          async_execution: false
        }),
      });

      console.log('[handleSendMessage] APIレスポンス受信', { status: response.status });

      if (!response.ok) {
        throw new Error(`API Error: ${response.status}`);
      }

      const data = await response.json();
      console.log('[handleSendMessage] APIデータ取得', data);

      // resultがオブジェクトの場合はrawフィールドを取得
      const responseContent = typeof data.result === 'object' && data.result !== null 
        ? (data.result.raw || JSON.stringify(data.result))
        : (data.result || 'レスポンスがありません');

      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: responseContent,
        role: "assistant",
        timestamp: new Date(),
        metadata: {
          task_id: data.task_id,
          status: data.status,
          created_at: data.created_at,
          execution_time: data.execution_time
        },
      };

      console.log('[handleSendMessage] AIメッセージ作成', aiMessage);

      setSessions(prev => {
        const updatedSessions = prev.map(session => {
          if (session.id === sessionId) {
            console.log('[handleSendMessage] セッションにAIメッセージ追加', sessionId);
            const updatedSession = {
              ...session,
              messages: [...session.messages, aiMessage],
              updatedAt: new Date(),
            };
            console.log('[handleSendMessage] 更新後のメッセージ数', updatedSession.messages.length);
            return updatedSession;
          }
          return session;
        });
        console.log('[handleSendMessage] 全セッション更新完了', updatedSessions.length);
        return updatedSessions;
      });
      
      console.log('[handleSendMessage] 処理完了');
    } catch (error) {
      console.error('[handleSendMessage] エラー発生:', error);
      
      // エラーメッセージを表示
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: 'エラーが発生しました。バックエンドサーバーが起動していることを確認してください。',
        role: "assistant",
        timestamp: new Date(),
        isError: true,
      };

      setSessions(prev => prev.map(session => {
        if (session.id === sessionId) {
          console.log('[handleSendMessage] エラーメッセージ追加', sessionId);
          return {
            ...session,
            messages: [...session.messages, errorMessage],
            updatedAt: new Date(),
          };
        }
        return session;
      }));
    } finally {
      setIsLoading(false);
      console.log('[handleSendMessage] ローディング状態解除');
    }
  }, [currentSessionId]);

  return (
    <div className="min-h-screen bg-background text-foreground">
      <Sidebar
        sessions={sessions}
        currentSessionId={currentSessionId}
        onNewChat={createNewSession}
        onSelectSession={setCurrentSessionId}
        onDeleteSession={deleteSession}
        onRenameSession={renameSession}
        onToggleFavoriteSession={toggleFavoriteSession}
      />
      <main className="ml-64 flex-1 flex flex-col min-h-screen">
        {/* チャットエリア */}
        <div className="flex-1 flex flex-col">
          <Chat
            messages={currentSession?.messages || []}
            onSendMessage={handleSendMessage}
            isLoading={isLoading}
            welcomeTitle="Okamichan"
          />
        </div>
      </main>
    </div>
  );
}
