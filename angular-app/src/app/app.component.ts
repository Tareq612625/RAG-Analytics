import { Component, OnInit, OnDestroy } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive, Router, NavigationEnd } from '@angular/router';
import { CommonModule } from '@angular/common';
import { Subscription, filter } from 'rxjs';
import { ChatStateService } from './services/chat-state.service';
import { HealthCheck } from './models/chat.models';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, RouterOutlet, RouterLink, RouterLinkActive],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss'
})
export class AppComponent implements OnInit, OnDestroy {
  title = 'RAG Analytics';
  healthStatus: HealthCheck | null = null;
  showHelpModal = false;
  currentRoute = '';

  private subscriptions: Subscription[] = [];

  constructor(
    private router: Router,
    private chatStateService: ChatStateService
  ) {}

  ngOnInit(): void {
    // Subscribe to route changes
    this.subscriptions.push(
      this.router.events.pipe(
        filter(event => event instanceof NavigationEnd)
      ).subscribe((event: NavigationEnd) => {
        this.currentRoute = event.urlAfterRedirects;
      })
    );

    // Subscribe to health status from chat state service
    this.subscriptions.push(
      this.chatStateService.healthStatus$.subscribe(status => {
        this.healthStatus = status;
      })
    );

    // Set initial route
    this.currentRoute = this.router.url;
  }

  ngOnDestroy(): void {
    this.subscriptions.forEach(sub => sub.unsubscribe());
  }

  isOnChatRoute(): boolean {
    return this.currentRoute.includes('/chat') || this.currentRoute === '/';
  }

  toggleSidebar(): void {
    this.chatStateService.toggleSidebar();
  }

  toggleHelp(): void {
    this.showHelpModal = !this.showHelpModal;
  }

  clearChat(): void {
    this.chatStateService.triggerClearChat();
  }
}
