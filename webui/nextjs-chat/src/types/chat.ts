export interface Message {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: Date;
  isStreaming?: boolean;
  isError?: boolean;
  metadata?: {
    task_id?: string;
    status?: string;
    created_at?: string;
    execution_time?: number;
  };
}

export interface ChatSession {
  id: string;
  title: string;
  messages: Message[];
  createdAt: Date;
  updatedAt: Date;
  isFavorite?: boolean;
} 