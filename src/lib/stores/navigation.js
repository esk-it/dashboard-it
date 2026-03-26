import { writable } from 'svelte/store';

export const currentPage = writable('/');

export const navItems = [
  { key: 'home', path: '/', icon: 'Home', label: 'Accueil', emoji: '\u{1F3E0}' },
  { key: 'news', path: '/news', icon: 'Globe', label: 'Actualités', emoji: '\u{1F310}' },
  { key: 'planning', path: '/planning', icon: 'Calendar', label: 'Planning', emoji: '\u{1F4C5}' },
  { key: 'tasks', path: '/tasks', icon: 'CheckSquare', label: 'Tâches', emoji: '✅' },
  { key: 'documents', path: '/documents', icon: 'FileText', label: 'Documents', emoji: '\u{1F4C1}' },
  { key: 'suppliers', path: '/suppliers', icon: 'Users', label: 'Prestataires', emoji: '\u{1F4C7}' },
  { key: 'parc', path: '/parc', icon: 'Monitor', label: 'Parc', emoji: '\u{1F5A5}\uFE0F' },
  { type: 'separator' },
  { key: 'security', path: '/security', icon: 'Shield', label: 'Sécurité', emoji: '\u{1F6E1}\uFE0F' },
  { key: 'wiki', path: '/wiki', icon: 'BookOpen', label: 'Procédures', emoji: '\u{1F4D6}' },
  { key: 'changelog', path: '/changelog', icon: 'ClipboardList', label: 'Changelog', emoji: '\u{1F4CB}' },
  { key: 'monitoring', path: '/monitoring', icon: 'Activity', label: 'Monitoring', emoji: '\u{1F4E1}' },
  { type: 'separator' },
  { key: 'launcher', path: '/launcher', icon: 'Rocket', label: 'Lanceur', emoji: '\u{1F680}' },
  { type: 'separator' },
  { key: 'tools', path: '/tools', icon: 'Wrench', label: 'Outils', emoji: '\u{1F527}', bottom: true },
  { key: 'settings', path: '/settings', icon: 'Settings', label: 'Paramètres', emoji: '\u2699\uFE0F', bottom: true },
];
