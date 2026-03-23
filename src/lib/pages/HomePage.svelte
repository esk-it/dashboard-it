<script>
  import { onMount, onDestroy } from 'svelte';
  import { api } from '../api/client.js';
  import { settings } from '../stores/settings.js';
  import { currentPage } from '../stores/navigation.js';
  import { success } from '../stores/toast.js';
  import KpiCard from '../components/KpiCard.svelte';
  import PriorityCard from '../components/cards/PriorityCard.svelte';
  import SysMonCard from '../components/cards/SysMonCard.svelte';
  import GaugeChart from '../components/cards/GaugeChart.svelte';
  import SparklineChart from '../components/cards/SparklineChart.svelte';
  import DonutChart from '../components/cards/DonutChart.svelte';
  import QuickLinksCard from '../components/cards/QuickLinksCard.svelte';

  const JOURS = ['Dimanche', 'Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi'];
  const MOIS = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'ao\u00fbt', 'septembre', 'octobre', 'novembre', 'décembre'];

  let clockStr = '';
  let clockTimer;
  let refreshTimer;

  // Widget config — order, visibility, and size
  const WIDGET_DEFS = [
    { id: 'priority', label: 'T\u00e2ches prioritaires', emoji: '\u{1F4CB}' },
    { id: 'sysmon', label: 'Monitoring syst\u00e8me', emoji: '\u{1F4BB}' },
    { id: 'gauge', label: 'Taux de compl\u00e9tion', emoji: '\u{1F4CA}' },
    { id: 'sparkline', label: 'Activit\u00e9 hebdo', emoji: '\u{1F4C8}' },
    { id: 'donut', label: 'Cat\u00e9gories', emoji: '\u{1F369}' },
    { id: 'quicklinks', label: 'Acc\u00e8s rapides', emoji: '\u26A1' },
  ];

  const SIZE_LABELS = { 1: '1/3', 2: '1/2', 3: 'Pleine' };
  const DEFAULT_CONFIG = WIDGET_DEFS.map((w, i) => ({ id: w.id, visible: true, size: 2, order: i }));

  let widgetConfig = []; // [{id, visible, size, order}]
  let showWidgetConfig = false;

  // Derived: sorted visible widgets
  $: orderedWidgets = [...widgetConfig].sort((a, b) => a.order - b.order).filter(w => w.visible);

  function loadWidgetConfig() {
    try {
      const saved = localStorage.getItem('itm-widgets-v2');
      if (saved) { widgetConfig = JSON.parse(saved); return; }
    } catch {}
    widgetConfig = [...DEFAULT_CONFIG];
  }

  function saveWidgetConfig() {
    localStorage.setItem('itm-widgets-v2', JSON.stringify(widgetConfig));
    widgetConfig = [...widgetConfig]; // trigger reactivity
  }

  function toggleWidget(id) {
    const w = widgetConfig.find(w => w.id === id);
    if (w) { w.visible = !w.visible; saveWidgetConfig(); }
  }

  function cycleSize(id) {
    const w = widgetConfig.find(w => w.id === id);
    if (w) {
      // Cycle: 2 -> 3 -> 1 -> 2
      w.size = w.size === 2 ? 3 : w.size === 3 ? 1 : 2;
      saveWidgetConfig();
    }
  }

  function moveWidget(id, dir) {
    const idx = widgetConfig.findIndex(w => w.id === id);
    const swapIdx = idx + dir;
    if (swapIdx < 0 || swapIdx >= widgetConfig.length) return;
    // Swap orders
    const tmp = widgetConfig[idx].order;
    widgetConfig[idx].order = widgetConfig[swapIdx].order;
    widgetConfig[swapIdx].order = tmp;
    saveWidgetConfig();
  }

  function resetWidgetConfig() {
    widgetConfig = [...DEFAULT_CONFIG];
    saveWidgetConfig();
  }

  function getWidgetDef(id) {
    return WIDGET_DEFS.find(w => w.id === id);
  }

  function sizeToSpan(size) {
    if (size === 3) return 'span 6';
    if (size === 1) return 'span 2';
    return 'span 3'; // default: half
  }

  // ── Drag & Drop ─────────────────────────────────────────
  let dragId = null;
  let dragReady = false;
  let holdTimer = null;

  function onDragHandleDown(e, id) {
    // Start a timer — after 1.5s, enable dragging
    dragReady = false;
    holdTimer = setTimeout(() => {
      dragReady = true;
      dragId = id;
    }, 1200);
  }

  function onDragHandleUp() {
    clearTimeout(holdTimer);
    if (!dragReady) { dragId = null; }
  }

  function onDragStart(e, id) {
    if (!dragReady) { e.preventDefault(); return; }
    dragId = id;
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', id);
  }

  function onDragOver(e, targetId) {
    if (!dragId || dragId === targetId) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  }

  function onDrop(e, targetId) {
    e.preventDefault();
    if (!dragId || dragId === targetId) return;
    // Swap orders
    const srcWc = widgetConfig.find(w => w.id === dragId);
    const tgtWc = widgetConfig.find(w => w.id === targetId);
    if (srcWc && tgtWc) {
      const tmp = srcWc.order;
      srcWc.order = tgtWc.order;
      tgtWc.order = tmp;
      saveWidgetConfig();
    }
    dragId = null;
    dragReady = false;
  }

  function onDragEnd() {
    dragId = null;
    dragReady = false;
  }

  // KPI data
  let kpiTasks = 0;
  let kpiOverdue = 0;
  let kpiWeek = 0;
  let kpiDocs = 0;
  let kpiParc = 0;

  // Component refs
  let priorityCard;
  let sysMonCard;
  let gaugeChart;
  let sparklineChart;
  let donutChart;

  $: greeting = getGreeting();
  $: username = $settings.username || 'Utilisateur';
  $: dateStr = getDateStr();

  function getGreeting() {
    const h = new Date().getHours();
    return h >= 18 || h < 6 ? 'Bonsoir' : 'Bonjour';
  }

  function getDateStr() {
    const d = new Date();
    return `${JOURS[d.getDay()]} ${d.getDate()} ${MOIS[d.getMonth()]} ${d.getFullYear()}`;
  }

  function updateClock() {
    const d = new Date();
    clockStr = d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  }

  async function fetchKpis() {
    try {
      const data = await api.get('/api/dashboard/kpis');
      kpiTasks = data.open_tasks || 0;
      kpiOverdue = data.overdue_tasks || 0;
      kpiWeek = data.week_tasks || 0;
      kpiDocs = data.documents || 0;
      kpiParc = data.equipment || 0;
    } catch (e) {
      // keep defaults
    }
  }

  function refreshAll() {
    fetchKpis();
    if (priorityCard?.refresh) priorityCard.refresh();
    if (gaugeChart?.refresh) gaugeChart.refresh();
    if (sparklineChart?.refresh) sparklineChart.refresh();
    if (donutChart?.refresh) donutChart.refresh();
    success('Données actualisées');
  }

  function goNewTask() {
    currentPage.set('/tasks');
  }

  onMount(() => {
    loadWidgetConfig();
    updateClock();
    clockTimer = setInterval(updateClock, 1000);
    fetchKpis();

    // Auto-refresh
    const mins = $settings.auto_refresh_minutes || 5;
    refreshTimer = setInterval(() => {
      fetchKpis();
    }, mins * 60 * 1000);
  });

  onDestroy(() => {
    if (clockTimer) clearInterval(clockTimer);
    if (refreshTimer) clearInterval(refreshTimer);
  });
</script>

<div class="home-page">
  <!-- Header -->
  <header class="home-header">
    <div class="header-left">
      <h1 class="greeting">{greeting}, <span class="username">{username}</span></h1>
      <p class="date-str">{dateStr}</p>
    </div>
    <div class="header-right">
      <div class="clock-frame">
        <span class="clock">{clockStr}</span>
      </div>
      <button class="btn-ghost" on:click={() => showWidgetConfig = !showWidgetConfig} title="Configurer les widgets">
        {'\u2699\uFE0F'} Widgets
      </button>
      <button class="btn-ghost" on:click={refreshAll}>
        {'\u{1F504}'} Actualiser
      </button>
      <button class="btn-primary" on:click={goNewTask}>
        + T&acirc;che
      </button>
    </div>
  </header>

  <!-- KPI Row -->
  <div class="kpi-row">
    <KpiCard
      title="T&Acirc;CHES EN COURS"
      value={kpiTasks}
      orbColor={[75, 139, 255]}
      onClick={() => currentPage.set('/tasks')}
    />
    <KpiCard
      title="EN RETARD"
      value={kpiOverdue}
      orbColor={kpiOverdue > 0 ? [239, 68, 68] : [34, 197, 94]}
      hint={kpiOverdue > 0 ? 'Action requise' : 'Tout est à jour'}
    />
    <KpiCard
      title="CETTE SEMAINE"
      value={kpiWeek}
      orbColor={[45, 212, 191]}
    />
    <KpiCard
      title="DOCUMENTS"
      value={kpiDocs}
      orbColor={[245, 158, 11]}
      onClick={() => currentPage.set('/documents')}
    />
    <KpiCard
      title="PARC INFORMATIQUE"
      value={kpiParc}
      orbColor={[162, 89, 255]}
      onClick={() => currentPage.set('/parc')}
    />
  </div>

  <!-- Widget Config Panel -->
  {#if showWidgetConfig}
    <div class="widget-config">
      <div class="widget-config-header">
        <span>{'\u2699\uFE0F'} Configuration des widgets</span>
        <div style="display:flex;gap:6px;align-items:center">
          <button class="btn-reset-sm" on:click={resetWidgetConfig}>R{'\u00e9'}initialiser</button>
          <button class="btn-close-sm" on:click={() => showWidgetConfig = false}>{'\u2715'}</button>
        </div>
      </div>
      <div class="widget-config-list">
        {#each [...widgetConfig].sort((a,b) => a.order - b.order) as wc, i (wc.id)}
          {@const def = getWidgetDef(wc.id)}
          {#if def}
            <div class="widget-config-row" class:disabled={!wc.visible}>
              <div class="wc-move">
                <button class="wc-arrow" on:click={() => moveWidget(wc.id, -1)} disabled={i === 0}>{'\u25B2'}</button>
                <button class="wc-arrow" on:click={() => moveWidget(wc.id, 1)} disabled={i === widgetConfig.length - 1}>{'\u25BC'}</button>
              </div>
              <label class="wc-toggle">
                <input type="checkbox" checked={wc.visible} on:change={() => toggleWidget(wc.id)} />
              </label>
              <span class="wc-emoji">{def.emoji}</span>
              <span class="wc-label">{def.label}</span>
              <button class="wc-size" on:click={() => cycleSize(wc.id)} title="Changer la taille">
                {SIZE_LABELS[wc.size] || '1/2'}
              </button>
            </div>
          {/if}
        {/each}
      </div>
    </div>
  {/if}

  <!-- Cards Grid (6-column base for flexible sizing) -->
  <div class="cards-grid-flex">
    {#each orderedWidgets as wc (wc.id)}
      {@const def = getWidgetDef(wc.id)}
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <div
        class="card-slot-flex"
        class:dragging={dragId === wc.id}
        class:drag-ready={dragReady && dragId === wc.id}
        style="grid-column:{sizeToSpan(wc.size)}"
        draggable={dragReady && dragId === wc.id}
        on:dragstart={(e) => onDragStart(e, wc.id)}
        on:dragover={(e) => onDragOver(e, wc.id)}
        on:drop={(e) => onDrop(e, wc.id)}
        on:dragend={onDragEnd}
      >
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div
          class="widget-drag-handle"
          on:mousedown={(e) => onDragHandleDown(e, wc.id)}
          on:mouseup={onDragHandleUp}
          on:mouseleave={onDragHandleUp}
        >
          <span class="drag-dots">{'\u2630'}</span>
          <span class="drag-title">{def?.emoji} {def?.label}</span>
          <button class="drag-size-btn" on:mousedown|stopPropagation on:click={() => cycleSize(wc.id)} title="Changer la taille">
            {SIZE_LABELS[wc.size]}
          </button>
        </div>
        <div class="widget-body">
          {#if wc.id === 'priority'}<PriorityCard bind:this={priorityCard} />
          {:else if wc.id === 'sysmon'}<SysMonCard bind:this={sysMonCard} />
          {:else if wc.id === 'gauge'}<GaugeChart bind:this={gaugeChart} />
          {:else if wc.id === 'sparkline'}<SparklineChart bind:this={sparklineChart} />
          {:else if wc.id === 'donut'}<DonutChart bind:this={donutChart} />
          {:else if wc.id === 'quicklinks'}<QuickLinksCard />
          {/if}
        </div>
      </div>
    {/each}
  </div>
</div>

<style>
  .home-page {
    animation: fadeIn 0.35s ease-out;
  }

  /* Header */
  .home-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    margin-bottom: 28px;
    gap: 16px;
    flex-wrap: wrap;
  }

  .header-left {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .greeting {
    font-size: 26px;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0;
    letter-spacing: -0.3px;
  }

  .username {
    color: var(--accent);
  }

  .date-str {
    font-size: 14px;
    color: var(--text-secondary);
    margin: 0;
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .clock-frame {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: 10px;
    padding: 6px 14px;
    backdrop-filter: blur(12px);
  }

  .clock {
    font-size: 15px;
    font-weight: 600;
    color: var(--text-primary);
    font-variant-numeric: tabular-nums;
    letter-spacing: 0.5px;
  }

  .btn-ghost {
    background: transparent;
    border: 1px solid var(--border-subtle);
    border-radius: 10px;
    color: var(--text-secondary);
    font-size: 13px;
    padding: 7px 14px;
    cursor: pointer;
    transition: all 0.15s;
    font-family: inherit;
  }

  .btn-ghost:hover {
    background: var(--bg-hover);
    border-color: var(--border-hover);
    color: var(--text-primary);
  }

  .btn-primary {
    background: var(--accent);
    border: none;
    border-radius: 10px;
    color: #fff;
    font-size: 13px;
    font-weight: 600;
    padding: 8px 16px;
    cursor: pointer;
    transition: all 0.15s;
    font-family: inherit;
    box-shadow: 0 2px 12px rgba(var(--accent-rgb), 0.3);
  }

  .btn-primary:hover {
    filter: brightness(1.15);
    box-shadow: 0 4px 20px rgba(var(--accent-rgb), 0.4);
  }

  /* KPI Row */
  .kpi-row {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 14px;
    margin-bottom: 20px;
  }

  @media (max-width: 1200px) {
    .kpi-row {
      grid-template-columns: repeat(3, 1fr);
    }
  }

  @media (max-width: 768px) {
    .kpi-row {
      grid-template-columns: repeat(2, 1fr);
    }
  }

  /* Flexible Cards Grid — 6 columns base */
  .cards-grid-flex {
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    gap: 16px;
    align-items: stretch;
  }

  @media (max-width: 900px) {
    .cards-grid-flex {
      grid-template-columns: 1fr;
    }
    .card-slot-flex {
      grid-column: span 1 !important;
    }
  }

  .card-slot-flex {
    animation: fadeIn 0.4s ease-out;
    animation-fill-mode: both;
    min-width: 0;
    display: flex;
    flex-direction: column;
    border-radius: 14px;
    overflow: hidden;
    background: var(--bg-card, rgba(255,255,255,0.06));
    border: 1px solid var(--border-subtle, rgba(255,255,255,0.08));
    backdrop-filter: blur(12px);
    transition: box-shadow 0.2s, border-color 0.2s, opacity 0.2s;
  }
  .card-slot-flex.drag-ready {
    border-color: var(--accent, #6C63FF);
    box-shadow: 0 0 16px rgba(108,99,255,0.2);
    cursor: grabbing;
  }
  .card-slot-flex.dragging {
    opacity: 0.5;
  }

  /* Drag handle (title bar) */
  .widget-drag-handle {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 12px;
    background: rgba(255,255,255,0.02);
    border-bottom: 1px solid rgba(255,255,255,0.04);
    cursor: grab;
    user-select: none;
    flex-shrink: 0;
  }
  .widget-drag-handle:active { cursor: grabbing; }
  .drag-dots {
    font-size: 12px;
    color: rgba(255,255,255,0.15);
    line-height: 1;
  }
  .drag-title {
    flex: 1;
    font-size: 0.72rem;
    font-weight: 600;
    color: rgba(255,255,255,0.35);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  .drag-size-btn {
    background: rgba(var(--accent-rgb, 108,99,255), 0.1);
    color: var(--accent, #6C63FF);
    border: 1px solid rgba(var(--accent-rgb, 108,99,255), 0.15);
    border-radius: 5px;
    padding: 1px 8px;
    font-size: 0.65rem;
    font-weight: 600;
    cursor: pointer;
    font-family: inherit;
    transition: all 0.15s;
  }
  .drag-size-btn:hover { background: rgba(var(--accent-rgb, 108,99,255), 0.2); }

  .widget-body {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
  }
  /* Make cards inside widget-body fill the space */
  .widget-body > :global(*) {
    flex: 1;
    border: none !important;
    border-radius: 0 !important;
    background: transparent !important;
    backdrop-filter: none !important;
  }

  .card-slot-flex:nth-child(1) { animation-delay: 0.05s; }
  .card-slot-flex:nth-child(2) { animation-delay: 0.1s; }
  .card-slot-flex:nth-child(3) { animation-delay: 0.15s; }
  .card-slot-flex:nth-child(4) { animation-delay: 0.2s; }
  .card-slot-flex:nth-child(5) { animation-delay: 0.25s; }
  .card-slot-flex:nth-child(6) { animation-delay: 0.3s; }

  /* Widget config panel */
  .widget-config {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 16px;
    backdrop-filter: blur(12px);
    animation: fadeIn 0.2s ease-out;
  }
  .widget-config-header {
    display: flex; justify-content: space-between; align-items: center;
    margin-bottom: 12px; font-size: 0.9rem; font-weight: 600; color: var(--text-primary);
  }
  .btn-close-sm {
    background: none; border: none; color: var(--text-secondary);
    cursor: pointer; font-size: 1rem; padding: 2px 6px; border-radius: 4px;
  }
  .btn-close-sm:hover { background: var(--bg-hover); color: var(--text-primary); }
  .btn-reset-sm {
    background: rgba(255,255,255,0.06); border: 1px solid var(--border-subtle);
    border-radius: 6px; padding: 3px 10px; font-size: 0.72rem; color: var(--text-secondary);
    cursor: pointer; font-family: inherit;
  }
  .btn-reset-sm:hover { background: var(--bg-hover); color: var(--text-primary); }

  .widget-config-list {
    display: flex; flex-direction: column; gap: 6px;
  }
  .widget-config-row {
    display: flex; align-items: center; gap: 10px;
    padding: 6px 8px; border-radius: 8px;
    background: rgba(255,255,255,0.02);
    transition: background 0.15s;
  }
  .widget-config-row:hover { background: rgba(255,255,255,0.04); }
  .widget-config-row.disabled { opacity: 0.4; }
  .wc-move { display: flex; flex-direction: column; gap: 1px; }
  .wc-arrow {
    background: none; border: none; color: var(--text-muted); cursor: pointer;
    font-size: 0.6rem; padding: 0 4px; line-height: 1; border-radius: 3px;
  }
  .wc-arrow:hover:not(:disabled) { color: var(--text-primary); background: var(--bg-hover); }
  .wc-arrow:disabled { opacity: 0.2; cursor: default; }
  .wc-toggle input[type="checkbox"] {
    width: 16px; height: 16px; accent-color: var(--accent); cursor: pointer;
  }
  .wc-emoji { font-size: 1rem; width: 20px; text-align: center; }
  .wc-label { flex: 1; font-size: 0.82rem; color: var(--text-secondary); }
  .wc-size {
    background: rgba(var(--accent-rgb), 0.1); color: var(--accent);
    border: 1px solid rgba(var(--accent-rgb), 0.2); border-radius: 6px;
    padding: 2px 10px; font-size: 0.72rem; font-weight: 600; cursor: pointer;
    font-family: inherit; min-width: 50px; text-align: center;
    transition: all 0.15s;
  }
  .wc-size:hover { background: rgba(var(--accent-rgb), 0.2); }
</style>
