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
  // Retry — backend sidecar takes a few seconds to start
  for (let attempt = 0; attempt < 8; attempt++) {
    try {
      const data = await api.get('/api/settings/general');
      if (data && typeof data === 'object') {
        settings.set(data);
        break;
      }
    } catch (e) {
      if (attempt < 7) {
        await new Promise(r => setTimeout(r, 2000));
      } else {
        console.warn('Failed to load settings after retries:', e);
      }
    }
  }

  // Apply saved theme on startup
  try {
    const theme = await api.get('/api/settings/theme');
    if (theme?.theme === 'glass-light') {
      document.documentElement.setAttribute('data-theme', 'glass-light');
      document.documentElement.style.colorScheme = 'light';
      document.body.style.background = '#F3F0EC';
    } else {
      document.documentElement.removeAttribute('data-theme');
    }
    if (theme?.accent) {
      document.documentElement.style.setProperty('--accent', theme.accent);
    }
  } catch (e) {
    console.warn('Failed to load theme:', e);
  }

  // Apply compact mode from localStorage
  if (localStorage.getItem('itm-compact') === '1') {
    document.documentElement.setAttribute('data-compact', 'true');
  }
}
