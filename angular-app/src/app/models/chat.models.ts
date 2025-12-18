export interface QueryRequest {
  question: string;
  conversation_id?: string;
}

export interface QueryResponse {
  refined_question: string;
  sql: string;
  table: any[];
  final_answer: string;
  conversation_id: string;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  isLoading?: boolean;
  sql?: string;
  table?: any[];
  refined_question?: string;
}

export interface HealthCheck {
  status: string;
  llm_provider: string;
  llm_model: string;
  llm_configured: boolean;
  database_url: string;
  environment: string;
}

export interface TableDataResponse {
  table: string;
  columns: string[];
  data: any[];
  total: number;
  limit: number;
  offset: number;
}

export interface ChatSession {
  conversation_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  first_question?: string;
}

export interface ChatHistoryResponse {
  sessions: ChatSession[];
  total: number;
}

export interface ChatMessagesResponse {
  conversation_id: string;
  messages: {
    role: 'user' | 'assistant';
    content: string;
    timestamp: string;
    sql?: string;
    table?: any[];
    refined_question?: string;
  }[];
}
