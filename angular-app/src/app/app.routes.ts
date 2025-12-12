import { Routes } from '@angular/router';
import { ChatComponent } from './components/chat/chat.component';
import { DatabaseExplorerComponent } from './components/database-explorer/database-explorer.component';

export const routes: Routes = [
  { path: '', redirectTo: 'chat', pathMatch: 'full' },
  { path: 'chat', component: ChatComponent },
  { path: 'database', component: DatabaseExplorerComponent },
  { path: '**', redirectTo: 'chat' }
];
