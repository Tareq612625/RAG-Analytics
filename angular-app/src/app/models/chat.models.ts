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
