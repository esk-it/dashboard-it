import { writable } from 'svelte/store';
import { api } from '../api/client.js';

export const settings = writable({
  username: '',
  auto_refresh_minutes: 5,
  max_home_tasks: 10,
  language: 'fr',
  enabled_modules: {},
  card_order: [],
  card_layout: [],
});

export async function loadSettings() {
  try {
    const data = await api.get('/api/settings/general');
    settings.set(data);
  } catch (e) {
    console.warn('Failed to load settings:', e);
  }

  // Apply saved theme on startup
  try {
    const theme = await api.get('/api/settings/theme');
    if (theme?.theme === 'glass-light') {
      const root = document.documentElement;
      root.style.setProperty('--bg-base', '#E8ECF2');
      root.style.setProperty('--bg-card', 'rgba(255, 255, 255, 0.72)');
      root.style.setProperty('--bg-card-solid', '#F5F7FA');
      root.style.setProperty('--bg-sidebar', 'rgba(240, 243, 248, 0.92)');
      root.style.setProperty('--bg-hover', 'rgba(0, 0, 0, 0.04)');
      root.style.setProperty('--border-subtle', 'rgba(0, 0, 0, 0.08)');
      root.style.setProperty('--border-hover', 'rgba(0, 0, 0, 0.14)');
      root.style.setProperty('--text-primary', 'rgba(15, 23, 42, 0.92)');
      root.style.setProperty('--text-secondary', 'rgba(51, 65, 85, 0.85)');
      root.style.setProperty('--text-muted', 'rgba(100, 116, 139, 0.7)');
      root.style.colorScheme = 'light';
      document.body.style.background = '#E8ECF2';
    }
    if (theme?.accent) {
      document.documentElement.style.setProperty('--accent', theme.accent);
    }
  } catch (e) {
    console.warn('Failed to load theme:', e);
  }
}
