import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import {
  QueryRequest,
  QueryResponse,
  HealthCheck,
  TableDataResponse,
  ChatHistoryResponse,
  ChatMessagesResponse
} from '../models/chat.models';

@Injectable({
  providedIn: 'root'
})
export class ChatService {
  private baseUrl = 'http://localhost:8009/api/v1';

  constructor(private http: HttpClient) {}

  chat(request: QueryRequest): Observable<QueryResponse> {
    return this.http.post<QueryResponse>(`${this.baseUrl}/chat`, request);
  }

  healthCheck(): Observable<HealthCheck> {
    return this.http.get<HealthCheck>(`${this.baseUrl}/health`);
  }

  getMetrics(): Observable<any> {
    return this.http.get(`${this.baseUrl}/metrics`);
  }

  getTables(): Observable<any> {
    return this.http.get(`${this.baseUrl}/tables`);
  }

  getSchema(): Observable<any> {
    return this.http.get(`${this.baseUrl}/schema`);
  }

  // Database explorer methods
  getDatabaseTables(): Observable<{ tables: string[] }> {
    return this.http.get<{ tables: string[] }>(`${this.baseUrl}/database/tables`);
  }

  getTableData(tableName: string, limit: number = 100, offset: number = 0): Observable<TableDataResponse> {
    return this.http.get<TableDataResponse>(
      `${this.baseUrl}/database/tables/${tableName}?limit=${limit}&offset=${offset}`
    );
  }

  // Chat history methods
  getChatHistory(days: number = 1): Observable<ChatHistoryResponse> {
    return this.http.get<ChatHistoryResponse>(`${this.baseUrl}/chat/history?days=${days}`);
  }

  getChatMessages(conversationId: string): Observable<ChatMessagesResponse> {
    return this.http.get<ChatMessagesResponse>(`${this.baseUrl}/chat/history/${conversationId}/messages`);
  }

  deleteConversation(conversationId: string): Observable<{ message: string }> {
    return this.http.delete<{ message: string }>(`${this.baseUrl}/conversation/${conversationId}`);
  }

  updateChatTitle(conversationId: string, title: string): Observable<{ message: string }> {
    return this.http.put<{ message: string }>(
      `${this.baseUrl}/chat/history/${conversationId}/title?title=${encodeURIComponent(title)}`,
      {}
    );
  }
}
