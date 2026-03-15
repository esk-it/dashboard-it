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
}
