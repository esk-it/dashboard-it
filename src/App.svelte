<script>
  import { onMount } from 'svelte';
  import { currentPage } from './lib/stores/navigation.js';
  import { loadSettings } from './lib/stores/settings.js';
  import GlassBackground from './lib/components/GlassBackground.svelte';
  import SplashScreen from './lib/components/SplashScreen.svelte';
  import Sidebar from './lib/components/Sidebar.svelte';
  import Toast from './lib/components/Toast.svelte';
  import SearchPalette from './lib/components/SearchPalette.svelte';
  import HomePage from './lib/pages/HomePage.svelte';
  import PlaceholderPage from './lib/pages/PlaceholderPage.svelte';
  import PlanningPage from './lib/pages/PlanningPage.svelte';
  import TasksPage from './lib/pages/TasksPage.svelte';
  import DocumentsPage from './lib/pages/DocumentsPage.svelte';
  import NewsPage from './lib/pages/NewsPage.svelte';
  import ChangelogPage from './lib/pages/ChangelogPage.svelte';
  import WikiPage from './lib/pages/WikiPage.svelte';
  import SuppliersPage from './lib/pages/SuppliersPage.svelte';
  import ParcPage from './lib/pages/ParcPage.svelte';
  import SecurityPage from './lib/pages/SecurityPage.svelte';
  import MonitoringPage from './lib/pages/MonitoringPage.svelte';
  import ToolsPage from './lib/pages/ToolsPage.svelte';
  import SettingsPage from './lib/pages/SettingsPage.svelte';

  let showSearch = false;
  let splashDone = false;

  onMount(() => {
    loadSettings();

    function handleKeydown(e) {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        showSearch = !showSearch;
      }
    }

    window.addEventListener('keydown', handleKeydown);
    return () => window.removeEventListener('keydown', handleKeydown);
  });
</script>

<SplashScreen on:done={() => splashDone = true} />

<GlassBackground />

{#if splashDone}
  <Sidebar />

<main class="content">
  {#if $currentPage === '/'}
    <HomePage />
  {:else if $currentPage === '/news'}
    <NewsPage />
  {:else if $currentPage === '/planning'}
    <PlanningPage />
  {:else if $currentPage === '/tasks'}
    <TasksPage />
  {:else if $currentPage === '/documents'}
    <DocumentsPage />
  {:else if $currentPage === '/suppliers'}
    <SuppliersPage />
  {:else if $currentPage === '/parc'}
    <ParcPage />
  {:else if $currentPage === '/security'}
    <SecurityPage />
  {:else if $currentPage === '/wiki'}
    <WikiPage />
  {:else if $currentPage === '/changelog'}
    <ChangelogPage />
  {:else if $currentPage === '/monitoring'}
    <MonitoringPage />
  {:else if $currentPage === '/tools'}
    <ToolsPage />
  {:else if $currentPage === '/settings'}
    <SettingsPage />
  {:else}
    <PlaceholderPage title="Page introuvable" emoji={'\u{1F50D}'} />
  {/if}
</main>

<Toast />

{#if showSearch}
  <SearchPalette on:close={() => showSearch = false} />
{/if}
{/if}

<style>
  .content {
    flex: 1;
    overflow-y: auto;
    overflow-x: hidden;
    padding: 28px 32px;
    min-height: 100vh;
  }
</style>
