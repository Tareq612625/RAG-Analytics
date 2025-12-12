import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { QueryRequest, QueryResponse, HealthCheck, TableDataResponse } from '../models/chat.models';

@Injectable({
  providedIn: 'root'
})
export class ChatService {
  private baseUrl = 'http://localhost:8000/api/v1';

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
}
