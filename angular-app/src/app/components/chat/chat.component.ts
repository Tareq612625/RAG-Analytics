import { Component, OnInit, OnDestroy, ViewChild, ElementRef, AfterViewChecked, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';
import { ChatService } from '../../services/chat.service';
import { ChatStateService } from '../../services/chat-state.service';
import { ChatMessage, HealthCheck, ChatSession } from '../../models/chat.models';

@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './chat.component.html',
  styleUrls: ['./chat.component.scss']
})
export class ChatComponent implements OnInit, OnDestroy, AfterViewChecked {
  @ViewChild('messagesContainer') private messagesContainer!: ElementRef;

  messages: ChatMessage[] = [];
  userInput: string = '';
  isLoading: boolean = false;
  conversationId: string | undefined;
  healthStatus: HealthCheck | null = null;
  showDetails: boolean = false;
  selectedMessageIndex: number | null = null;

  // Chat history sidebar (controlled via ChatStateService from app nav)
  chatHistory: ChatSession[] = [];
  isSidebarOpen: boolean = true;
  isLoadingHistory: boolean = false;

  suggestedQuestions: string[] = [
    'What is the total sales?',
    'Show me sales by region',
    'What are the top selling products?',
    'How many orders today?',
    'What is the total revenue this month?'
  ];

  private subscriptions: Subscription[] = [];

  constructor(
    private chatService: ChatService,
    private chatStateService: ChatStateService
  ) {}

  ngOnInit(): void {
    this.checkHealth();
    this.addWelcomeMessage();
    this.loadChatHistory();

    // Subscribe to sidebar toggle from nav
    this.subscriptions.push(
      this.chatStateService.sidebarOpen$.subscribe(open => {
        this.isSidebarOpen = open;
      })
    );

    // Subscribe to clear chat trigger from nav
    this.subscriptions.push(
      this.chatStateService.clearChatTrigger$.subscribe(timestamp => {
        if (timestamp > 0) {
          this.clearChat();
        }
      })
    );
  }

  ngOnDestroy(): void {
    this.subscriptions.forEach(sub => sub.unsubscribe());
  }

  ngAfterViewChecked(): void {
    this.scrollToBottom();
  }

  @HostListener('window:resize')
  onResize(): void {
    const isMobile = window.innerWidth <= 768;

    // Close sidebar when resizing to mobile
    if (isMobile && this.isSidebarOpen) {
      this.chatStateService.setSidebarOpen(false);
    }
    // Open sidebar when resizing to desktop
    else if (!isMobile && !this.isSidebarOpen) {
      this.chatStateService.setSidebarOpen(true);
    }
  }

  checkHealth(): void {
    this.chatService.healthCheck().subscribe({
      next: (health) => {
        this.healthStatus = health;
        // Update the state service so app component can display it
        this.chatStateService.setHealthStatus(health);
      },
      error: (err) => {
        console.error('Health check failed:', err);
        this.healthStatus = null;
        this.chatStateService.setHealthStatus(null);
      }
    });
  }

  addWelcomeMessage(): void {
    this.messages.push({
      role: 'assistant',
      content: `Hello! I'm your Analytics Assistant. Ask me anything about your business data.`,
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
        // Refresh chat history to show/update current session
        this.loadChatHistory();
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

  // Chat History Methods
  loadChatHistory(): void {
    this.isLoadingHistory = true;
    this.chatService.getChatHistory(1).subscribe({
      next: (response) => {
        this.chatHistory = response.sessions;
        this.isLoadingHistory = false;
      },
      error: (err) => {
        console.error('Failed to load chat history:', err);
        this.isLoadingHistory = false;
      }
    });
  }

  loadConversation(session: ChatSession): void {
    this.isLoading = true;
    this.chatService.getChatMessages(session.conversation_id).subscribe({
      next: (response) => {
        this.messages = [];
        this.conversationId = session.conversation_id;
        this.selectedMessageIndex = null;

        // Convert messages from API to ChatMessage format
        response.messages.forEach(msg => {
          this.messages.push({
            role: msg.role,
            content: msg.content,
            timestamp: new Date(msg.timestamp),
            sql: msg.sql,
            table: msg.table,
            refined_question: msg.refined_question
          });
        });

        this.isLoading = false;
      },
      error: (err) => {
        console.error('Failed to load conversation:', err);
        this.isLoading = false;
      }
    });
  }

  startNewChat(): void {
    this.clearChat();
    this.loadChatHistory();
  }

  deleteSession(session: ChatSession, event: Event): void {
    event.stopPropagation();
    if (confirm('Are you sure you want to delete this chat?')) {
      this.chatService.deleteConversation(session.conversation_id).subscribe({
        next: () => {
          this.chatHistory = this.chatHistory.filter(
            s => s.conversation_id !== session.conversation_id
          );
          // If deleted session is currently active, start new chat
          if (this.conversationId === session.conversation_id) {
            this.startNewChat();
          }
        },
        error: (err) => {
          console.error('Failed to delete session:', err);
        }
      });
    }
  }

  formatDate(dateStr: string): string {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return date.toLocaleDateString();
  }

  isActiveSession(session: ChatSession): boolean {
    return this.conversationId === session.conversation_id;
  }

  onKeyDown(event: KeyboardEvent): void {
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
