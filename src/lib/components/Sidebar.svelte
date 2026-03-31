<script>
  import { onMount, onDestroy } from 'svelte';
  import { currentPage, navItems } from '../stores/navigation.js';
  import logoUrl from '../../assets/logo.png';

  let appVersion = '';
  let overdueCount = 0;
  let interval;
  let collapsed = false;

  onMount(async () => {
    try {
      const { getVersion } = await import('@tauri-apps/api/app');
      appVersion = await getVersion();
    } catch {
      appVersion = '4.0.1';
    }
    loadOverdueCount();
    interval = setInterval(loadOverdueCount, 60000);
  });

  onDestroy(() => { if (interval) clearInterval(interval); });

  async function loadOverdueCount() {
    try {
      const res = await fetch('http://localhost:8010/api/tasks?status=open');
      const tasks = await res.json();
      const today = new Date().toISOString().slice(0, 10);
      overdueCount = tasks.filter(t => t.due_date && t.due_date < today && !t.done).length;
    } catch { /* ignore */ }
  }

  function navigate(path) {
    currentPage.set(path);
  }

  // Split nav items into sections
  $: topItems = navItems.filter(item => !item.bottom && item.type !== 'separator' && ['home','news','planning','tasks','documents'].includes(item.key));
  $: moduleItems = navItems.filter(item => !item.bottom && item.type !== 'separator' && ['suppliers','parc','security','wiki','changelog','monitoring','launcher'].includes(item.key));
  $: bottomItems = navItems.filter(item => item.bottom);
</script>

<aside class="sidebar" class:collapsed>
  <!-- Brand header -->
  <div class="brand">
    <img src={logoUrl} alt="Logo" class="brand-logo" />
    {#if !collapsed}
      <span class="brand-name">ITManager</span>
    {/if}
    <button class="collapse-btn" on:click={() => collapsed = !collapsed}>
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        {#if collapsed}
          <polyline points="9 18 15 12 9 6"/>
        {:else}
          <polyline points="15 18 9 12 15 6"/>
        {/if}
      </svg>
    </button>
  </div>

  <nav class="nav-scroll">
    <!-- Section: General -->
    {#if !collapsed}
      <div class="nav-section-title">GÉNÉRAL</div>
    {/if}
    {#each topItems as item}
      <!-- svelte-ignore a11y_click_events_have_key_events -->
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <div
        class="nav-item"
        class:active={$currentPage === item.path}
        title={collapsed ? item.label : ''}
        on:click={() => navigate(item.path)}
      >
        <span class="nav-emoji">{item.emoji}</span>
        {#if !collapsed}
          <span class="nav-label">{item.label}</span>
        {/if}
        {#if item.key === 'tasks' && overdueCount > 0}
          <span class="overdue-badge">{overdueCount}</span>
        {/if}
      </div>
    {/each}

    <!-- Section: Modules -->
    {#if !collapsed}
      <div class="nav-section-title">MODULES</div>
    {:else}
      <div class="nav-divider"></div>
    {/if}
    {#each moduleItems as item}
      <!-- svelte-ignore a11y_click_events_have_key_events -->
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <div
        class="nav-item"
        class:active={$currentPage === item.path}
        title={collapsed ? item.label : ''}
        on:click={() => navigate(item.path)}
      >
        <span class="nav-emoji">{item.emoji}</span>
        {#if !collapsed}
          <span class="nav-label">{item.label}</span>
        {/if}
      </div>
    {/each}
  </nav>

  <!-- Bottom: Tools + Settings -->
  <div class="nav-bottom">
    <div class="nav-divider"></div>
    {#each bottomItems as item}
      <!-- svelte-ignore a11y_click_events_have_key_events -->
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <div
        class="nav-item"
        class:active={$currentPage === item.path}
        title={collapsed ? item.label : ''}
        on:click={() => navigate(item.path)}
      >
        <span class="nav-emoji">{item.emoji}</span>
        {#if !collapsed}
          <span class="nav-label">{item.label}</span>
        {/if}
      </div>
    {/each}
    <div class="version-info">
      {#if !collapsed}
        <span>v{appVersion}</span>
      {:else}
        <span class="version-dot"></span>
      {/if}
    </div>
  </div>
</aside>

<style>
  .sidebar {
    width: var(--sidebar-width-expanded);
    min-width: var(--sidebar-width-expanded);
    height: 100vh;
    background: var(--bg-sidebar);
    border-right: 1px solid var(--border-subtle);
    display: flex;
    flex-direction: column;
    z-index: 100;
    user-select: none;
    transition: width 250ms ease, min-width 250ms ease;
    overflow: hidden;
  }

  .sidebar.collapsed {
    width: var(--sidebar-width-collapsed);
    min-width: var(--sidebar-width-collapsed);
  }

  /* Brand */
  .brand {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 16px 16px 12px;
    border-bottom: 1px solid var(--border-subtle);
    flex-shrink: 0;
  }

  .brand-logo {
    width: 36px;
    height: 36px;
    object-fit: contain;
    border-radius: 8px;
    flex-shrink: 0;
  }

  .brand-name {
    font-size: 18px;
    font-weight: 700;
    color: var(--text-heading);
    letter-spacing: -0.3px;
    white-space: nowrap;
  }

  .collapse-btn {
    margin-left: auto;
    background: none;
    border: none;
    color: var(--text-muted);
    cursor: pointer;
    padding: 4px;
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.15s;
    flex-shrink: 0;
  }
  .collapse-btn:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
  }

  .collapsed .brand {
    justify-content: center;
    padding: 16px 8px 12px;
    gap: 0;
  }
  .collapsed .collapse-btn {
    margin-left: 0;
  }

  /* Navigation */
  .nav-scroll {
    flex: 1;
    overflow-y: auto;
    overflow-x: hidden;
    padding: 8px;
  }

  .nav-section-title {
    font-size: 11px;
    font-weight: 600;
    color: var(--text-muted);
    letter-spacing: 1px;
    padding: 16px 12px 6px;
    text-transform: uppercase;
  }

  .nav-divider {
    height: 1px;
    background: var(--border-subtle);
    margin: 8px 12px;
  }

  .nav-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 12px;
    margin: 2px 0;
    border-radius: 0.5rem;
    cursor: pointer;
    white-space: nowrap;
    overflow: hidden;
    transition: all 0.15s;
    position: relative;
    color: var(--text-secondary);
  }

  .nav-item:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
  }

  .nav-item.active {
    background: rgba(var(--primary-rgb), 0.15);
    color: var(--accent);
  }

  .nav-item.active::before {
    content: '';
    position: absolute;
    left: 0;
    top: 6px;
    bottom: 6px;
    width: 3px;
    background: var(--accent);
    border-radius: 0 3px 3px 0;
  }

  .nav-emoji {
    font-size: 18px;
    flex-shrink: 0;
    width: 26px;
    text-align: center;
    line-height: 1;
  }

  .nav-label {
    font-size: 14px;
    font-weight: 500;
  }

  .nav-item.active .nav-label {
    font-weight: 600;
  }

  /* Collapsed alignment */
  .collapsed .nav-item {
    justify-content: center;
    padding: 10px 8px;
  }
  .collapsed .nav-section-title { display: none; }

  /* Overdue badge */
  .overdue-badge {
    position: absolute;
    top: 4px; right: 6px;
    background: var(--danger);
    color: #fff;
    font-size: 10px;
    font-weight: 700;
    min-width: 18px;
    height: 18px;
    border-radius: 9px;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0 4px;
    box-shadow: 0 0 6px rgba(255, 94, 94, 0.4);
    animation: badgePulse 2s ease-in-out infinite;
  }
  @keyframes badgePulse {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.1); }
  }

  /* Bottom nav */
  .nav-bottom {
    flex-shrink: 0;
    padding: 0 8px 8px;
  }

  .version-info {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 8px 0 4px;
    font-size: 11px;
    color: var(--text-muted);
  }

  .version-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--text-muted);
    opacity: 0.5;
  }
</style>
