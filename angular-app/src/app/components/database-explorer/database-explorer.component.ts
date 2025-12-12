import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ChatService } from '../../services/chat.service';
import { TableDataResponse } from '../../models/chat.models';

@Component({
  selector: 'app-database-explorer',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './database-explorer.component.html',
  styleUrl: './database-explorer.component.scss'
})
export class DatabaseExplorerComponent implements OnInit {
  tables: string[] = [];
  selectedTable: string = '';
  tableData: TableDataResponse | null = null;
  loading = false;
  error = '';

  // Pagination
  currentPage = 1;
  pageSize = 20;
  totalPages = 1;

  constructor(private chatService: ChatService) {}

  ngOnInit() {
    this.loadTables();
  }

  loadTables() {
    this.chatService.getDatabaseTables().subscribe({
      next: (response) => {
        this.tables = response.tables;
        if (this.tables.length > 0) {
          this.selectTable(this.tables[0]);
        }
      },
      error: (err) => {
        this.error = 'Failed to load tables: ' + err.message;
      }
    });
  }

  selectTable(tableName: string) {
    this.selectedTable = tableName;
    this.currentPage = 1;
    this.loadTableData();
  }

  loadTableData() {
    if (!this.selectedTable) return;

    this.loading = true;
    this.error = '';
    const offset = (this.currentPage - 1) * this.pageSize;

    this.chatService.getTableData(this.selectedTable, this.pageSize, offset).subscribe({
      next: (response) => {
        this.tableData = response;
        this.totalPages = Math.ceil(response.total / this.pageSize);
        this.loading = false;
      },
      error: (err) => {
        this.error = 'Failed to load table data: ' + err.message;
        this.loading = false;
      }
    });
  }

  getColumns(): string[] {
    if (!this.tableData || !this.tableData.data || this.tableData.data.length === 0) {
      return this.tableData?.columns || [];
    }
    return Object.keys(this.tableData.data[0]);
  }

  formatValue(value: any): string {
    if (value === null || value === undefined) return '-';
    if (typeof value === 'number') {
      return value.toLocaleString();
    }
    return String(value);
  }

  previousPage() {
    if (this.currentPage > 1) {
      this.currentPage--;
      this.loadTableData();
    }
  }

  nextPage() {
    if (this.currentPage < this.totalPages) {
      this.currentPage++;
      this.loadTableData();
    }
  }

  goToPage(page: number) {
    if (page >= 1 && page <= this.totalPages) {
      this.currentPage = page;
      this.loadTableData();
    }
  }

  getTableIcon(tableName: string): string {
    const icons: { [key: string]: string } = {
      'regions': '🌍',
      'products': '📦',
      'customers': '👥',
      'sales': '💰',
      'invoices': '📄',
      'expenses': '💸'
    };
    return icons[tableName.toLowerCase()] || '📋';
  }

  getVisiblePages(): number[] {
    const pages: number[] = [];
    const start = Math.max(1, this.currentPage - 2);
    const end = Math.min(this.totalPages, this.currentPage + 2);

    for (let i = start; i <= end; i++) {
      pages.push(i);
    }
    return pages;
  }
}
