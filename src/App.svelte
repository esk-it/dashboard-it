<script>
  import { onMount } from 'svelte';
  import { currentPage } from './lib/stores/navigation.js';
  import { loadSettings } from './lib/stores/settings.js';
  import GlassBackground from './lib/components/GlassBackground.svelte';
  import SplashScreen from './lib/components/SplashScreen.svelte';
  import Sidebar from './lib/components/Sidebar.svelte';
  import Toast from './lib/components/Toast.svelte';
  import SearchPalette from './lib/components/SearchPalette.svelte';
  import QuickCreate from './lib/components/QuickCreate.svelte';
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
  import LauncherPage from './lib/pages/LauncherPage.svelte';
  import ToolsPage from './lib/pages/ToolsPage.svelte';
  import SettingsPage from './lib/pages/SettingsPage.svelte';

  let showSearch = false;
  let showQuickCreate = false;
  let splashDone = false;

  // Reload settings after splash is done (backend is ready by then)
  $: if (splashDone) loadSettings();

  // Warn before closing if a form might be open (global beforeunload)
  function handleBeforeUnload(e) {
    // Check if any dialog/modal is open by looking for overlay elements
    const hasOpenDialog = document.querySelector('.dialog-overlay, .modal-overlay');
    if (hasOpenDialog) {
      e.preventDefault();
      e.returnValue = '';
    }
  }

  onMount(() => {
    loadSettings();

    function handleKeydown(e) {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        showSearch = !showSearch;
      }
      if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
        // Don't override browser new window if not in Tauri
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
        e.preventDefault();
        showQuickCreate = !showQuickCreate;
      }
    }

    window.addEventListener('keydown', handleKeydown);
    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => {
      window.removeEventListener('keydown', handleKeydown);
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  });
</script>

<SplashScreen on:done={() => splashDone = true} />

<GlassBackground />

{#if splashDone}
  <Sidebar />

<main class="content">
  {#key $currentPage}
  <div class="page-transition">
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
  {:else if $currentPage === '/launcher'}
    <LauncherPage />
  {:else if $currentPage === '/tools'}
    <ToolsPage />
  {:else if $currentPage === '/settings'}
    <SettingsPage />
  {:else}
    <PlaceholderPage title="Page introuvable" emoji={'\u{1F50D}'} />
  {/if}
  </div>
  {/key}
</main>

<Toast />

{#if showSearch}
  <SearchPalette on:close={() => showSearch = false} />
{/if}
{#if showQuickCreate}
  <QuickCreate on:close={() => showQuickCreate = false} />
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
  .page-transition {
    animation: pageIn 0.25s ease-out;
  }
  @keyframes pageIn {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: translateY(0); }
  }
</style>
