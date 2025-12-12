import { Component, OnInit, ViewChild, ElementRef, AfterViewChecked } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ChatService } from '../../services/chat.service';
import { ChatMessage, HealthCheck } from '../../models/chat.models';

@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './chat.component.html',
  styleUrls: ['./chat.component.scss']
})
export class ChatComponent implements OnInit, AfterViewChecked {
  @ViewChild('messagesContainer') private messagesContainer!: ElementRef;
  @ViewChild('inputField') private inputField!: ElementRef;

  messages: ChatMessage[] = [];
  userInput: string = '';
  isLoading: boolean = false;
  conversationId: string | undefined;
  healthStatus: HealthCheck | null = null;
  showDetails: boolean = false;
  selectedMessageIndex: number | null = null;

  suggestedQuestions: string[] = [
    'What is the total sales?',
    'Show me sales by region',
    'What are the top selling products?',
    'How many orders today?',
    'What is the total revenue this month?'
  ];

  constructor(private chatService: ChatService) {}

  ngOnInit(): void {
    this.checkHealth();
    this.addWelcomeMessage();
  }

  ngAfterViewChecked(): void {
    this.scrollToBottom();
  }

  checkHealth(): void {
    this.chatService.healthCheck().subscribe({
      next: (health) => {
        this.healthStatus = health;
      },
      error: (err) => {
        console.error('Health check failed:', err);
        this.healthStatus = null;
      }
    });
  }

  addWelcomeMessage(): void {
    this.messages.push({
      role: 'assistant',
      content: `Welcome to the Analytics Assistant! I can help you query your business data using natural language.

Try asking questions like:
- "What is the total sales?"
- "Show me sales by region"
- "What are the top selling products?"

How can I help you today?`,
      timestamp: new Date()
    });
  }

  sendMessage(): void {
    if (!this.userInput.trim() || this.isLoading) return;

    const userMessage: ChatMessage = {
      role: 'user',
      content: this.userInput.trim(),
      timestamp: new Date()
    };
    this.messages.push(userMessage);

    const loadingMessage: ChatMessage = {
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      isLoading: true
    };
    this.messages.push(loadingMessage);

    this.isLoading = true;
    const question = this.userInput;
    this.userInput = '';

    this.chatService.chat({
      question: question,
      conversation_id: this.conversationId
    }).subscribe({
      next: (response) => {
        // Remove loading message
        this.messages.pop();

        const assistantMessage: ChatMessage = {
          role: 'assistant',
          content: response.final_answer,
          timestamp: new Date(),
          sql: response.sql,
          table: response.table,
          refined_question: response.refined_question
        };
        this.messages.push(assistantMessage);

        this.conversationId = response.conversation_id;
        this.isLoading = false;
      },
      error: (err) => {
        // Remove loading message
        this.messages.pop();

        const errorMessage: ChatMessage = {
          role: 'assistant',
          content: `Sorry, I encountered an error: ${err.error?.detail || err.message || 'Unknown error'}. Please try again.`,
          timestamp: new Date()
        };
        this.messages.push(errorMessage);

        this.isLoading = false;
      }
    });
  }

  askSuggested(question: string): void {
    this.userInput = question;
    this.sendMessage();
  }

  toggleDetails(index: number): void {
    if (this.selectedMessageIndex === index) {
      this.selectedMessageIndex = null;
    } else {
      this.selectedMessageIndex = index;
    }
  }

  clearChat(): void {
    this.messages = [];
    this.conversationId = undefined;
    this.selectedMessageIndex = null;
    this.addWelcomeMessage();
  }

  onKeyPress(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.sendMessage();
    }
  }

  private scrollToBottom(): void {
    try {
      if (this.messagesContainer) {
        this.messagesContainer.nativeElement.scrollTop =
          this.messagesContainer.nativeElement.scrollHeight;
      }
    } catch (err) {}
  }

  getTableHeaders(table: any[]): string[] {
    if (!table || table.length === 0) return [];
    return Object.keys(table[0]);
  }

  formatValue(value: any): string {
    if (value === null || value === undefined) return '-';
    if (typeof value === 'number') {
      return value.toLocaleString('en-IN');
    }
    return String(value);
  }
}
