<script>
  import { onMount, onDestroy } from 'svelte';
  import { currentPage, navItems } from '../stores/navigation.js';
  import logoUrl from '../../assets/logo.png';

  let hovered = false;
  let appVersion = '';
  let overdueCount = 0;
  let interval;

  onMount(async () => {
    try {
      const { getVersion } = await import('@tauri-apps/api/app');
      appVersion = await getVersion();
    } catch {
      appVersion = '3.5.1';
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

  $: mainItems = navItems.filter(item => item.type === 'separator' || !item.bottom);
  $: bottomItems = navItems.filter(item => item.bottom);
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<aside
  class="sidebar"
  class:expanded={hovered}
  on:mouseenter={() => hovered = true}
  on:mouseleave={() => hovered = false}
>
  <div class="sidebar-inner">
    <!-- Brand -->
    <div class="brand">
      <img src={logoUrl} alt="Logo" class="brand-logo" />
      {#if hovered}
        <span class="brand-text">ITManager</span>
      {/if}
    </div>

    <!-- Main nav -->
    <nav class="nav-main">
      {#each mainItems as item}
        {#if item.type === 'separator'}
          <div class="separator"></div>
        {:else}
          <!-- svelte-ignore a11y_click_events_have_key_events -->
          <!-- svelte-ignore a11y_no_static_element_interactions -->
          <div
            class="nav-item"
            class:active={$currentPage === item.path}
            title={hovered ? '' : item.label}
            on:click={() => navigate(item.path)}
          >
            <span class="nav-emoji">{item.emoji}</span>
            {#if hovered}
              <span class="nav-label">{item.label}</span>
            {/if}
            {#if item.key === 'tasks' && overdueCount > 0}
              <span class="overdue-badge">{overdueCount}</span>
            {/if}
          </div>
        {/if}
      {/each}
    </nav>

    <!-- Bottom nav -->
    <nav class="nav-bottom">
      {#each bottomItems as item}
        <!-- svelte-ignore a11y_click_events_have_key_events -->
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div
          class="nav-item"
          class:active={$currentPage === item.path}
          title={hovered ? '' : item.label}
          on:click={() => navigate(item.path)}
        >
          <span class="nav-emoji">{item.emoji}</span>
          {#if hovered}
            <span class="nav-label">{item.label}</span>
          {/if}
        </div>
      {/each}

      <!-- Version -->
      <div class="version">
        {#if hovered}
          <span>v{appVersion}</span>
        {:else}
          <span class="version-dot"></span>
        {/if}
      </div>
    </nav>
  </div>
</aside>

<style>
  .sidebar {
    width: var(--sidebar-width-collapsed);
    min-width: var(--sidebar-width-collapsed);
    height: 100vh;
    background: var(--bg-sidebar);
    border-right: 1px solid var(--border-subtle);
    backdrop-filter: blur(24px);
    -webkit-backdrop-filter: blur(24px);
    transition: width 220ms cubic-bezier(0.4, 0, 0.2, 1),
                min-width 220ms cubic-bezier(0.4, 0, 0.2, 1);
    overflow: hidden;
    display: flex;
    flex-direction: column;
    z-index: 100;
    user-select: none;
  }

  .sidebar.expanded {
    width: var(--sidebar-width-expanded);
    min-width: var(--sidebar-width-expanded);
  }

  .sidebar-inner {
    display: flex;
    flex-direction: column;
    height: 100%;
    padding: 8px;
  }

  /* Brand */
  .brand {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 12px 8px;
    margin-bottom: 8px;
    white-space: nowrap;
    overflow: hidden;
  }

  .brand-logo {
    width: 30px;
    height: 30px;
    object-fit: contain;
    flex-shrink: 0;
    border-radius: 6px;
  }

  .brand-icon {
    font-size: 22px;
    flex-shrink: 0;
    width: 30px;
    text-align: center;
  }

  .brand-text {
    font-size: 16px;
    font-weight: 600;
    color: var(--text-primary);
    letter-spacing: -0.3px;
    opacity: 0;
    animation: fadeLabel 180ms ease forwards;
  }

  /* Navigation */
  .nav-main {
    flex: 1;
    overflow-y: auto;
    overflow-x: hidden;
  }

  .nav-bottom {
    margin-top: auto;
    padding-top: 8px;
    border-top: 1px solid var(--border-subtle);
  }

  .nav-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 9px 10px;
    margin: 2px 0;
    border-radius: 10px;
    cursor: pointer;
    white-space: nowrap;
    overflow: hidden;
    transition: background 0.15s ease, box-shadow 0.15s ease;
    position: relative;
  }

  .nav-item:hover {
    background: var(--bg-hover);
  }

  .nav-item.active {
    background: rgba(var(--accent-rgb), 0.15);
    box-shadow: 0 0 12px rgba(var(--accent-rgb), 0.2);
  }

  .nav-item.active .nav-emoji {
    filter: drop-shadow(0 0 4px rgba(var(--accent-rgb), 0.5));
  }

  .nav-item.active .nav-label {
    color: var(--accent);
    font-weight: 500;
  }

  .nav-emoji {
    font-size: 18px;
    flex-shrink: 0;
    width: 26px;
    text-align: center;
    line-height: 1;
  }

  .nav-label {
    font-size: 13.5px;
    color: var(--text-secondary);
    opacity: 0;
    animation: fadeLabel 180ms ease forwards;
  }

  .separator {
    height: 1px;
    background: var(--border-subtle);
    margin: 8px 10px;
  }

  /* Version */
  .version {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 10px 0 4px;
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

  /* Overdue badge */
  .overdue-badge {
    position: absolute;
    top: 4px; right: 4px;
    background: #EF4444;
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
    box-shadow: 0 0 6px rgba(239,68,68,0.4);
    animation: badgePulse 2s ease-in-out infinite;
  }
  @keyframes badgePulse {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.1); }
  }

  @keyframes fadeLabel {
    from {
      opacity: 0;
      transform: translateX(-4px);
    }
    to {
      opacity: 1;
      transform: translateX(0);
    }
  }
</style>
