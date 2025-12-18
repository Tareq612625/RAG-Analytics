import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { HealthCheck } from '../models/chat.models';

@Injectable({
  providedIn: 'root'
})
export class ChatStateService {
  private readonly MOBILE_BREAKPOINT = 768;

  // Start collapsed on mobile, expanded on desktop
  private sidebarOpen = new BehaviorSubject<boolean>(this.isDesktop());
  private healthStatus = new BehaviorSubject<HealthCheck | null>(null);
  private clearChatTrigger = new BehaviorSubject<number>(0);

  sidebarOpen$ = this.sidebarOpen.asObservable();
  healthStatus$ = this.healthStatus.asObservable();
  clearChatTrigger$ = this.clearChatTrigger.asObservable();

  private isDesktop(): boolean {
    return typeof window !== 'undefined' && window.innerWidth > this.MOBILE_BREAKPOINT;
  }

  toggleSidebar(): void {
    this.sidebarOpen.next(!this.sidebarOpen.value);
  }

  setSidebarOpen(open: boolean): void {
    this.sidebarOpen.next(open);
  }

  getSidebarOpen(): boolean {
    return this.sidebarOpen.value;
  }

  setHealthStatus(status: HealthCheck | null): void {
    this.healthStatus.next(status);
  }

  getHealthStatus(): HealthCheck | null {
    return this.healthStatus.value;
  }

  triggerClearChat(): void {
    this.clearChatTrigger.next(Date.now());
  }
}
