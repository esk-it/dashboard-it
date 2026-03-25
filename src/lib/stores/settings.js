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
  // Retry a few times since backend sidecar takes a moment to start
  for (let attempt = 0; attempt < 5; attempt++) {
    try {
      const data = await api.get('/api/settings/general');
      settings.set(data);
      break;
    } catch (e) {
      if (attempt < 4) {
        await new Promise(r => setTimeout(r, 1500));
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
      document.body.style.background = '#E8ECF2';
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
