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
  import WeatherCard from '../components/cards/WeatherCard.svelte';
  import ActivityCard from '../components/cards/ActivityCard.svelte';

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
    { id: 'weather', label: 'M\u00e9t\u00e9o', emoji: '\u{1F326}\uFE0F' },
    { id: 'activity', label: 'Activit\u00e9 r\u00e9cente', emoji: '\u{1F553}' },
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
      if (saved) {
        const parsed = JSON.parse(saved);
        // Merge in any new widgets not in saved config
        for (const def of DEFAULT_CONFIG) {
          if (!parsed.find(w => w.id === def.id)) {
            parsed.push({ ...def, order: parsed.length });
          }
        }
        widgetConfig = parsed;
        return;
      }
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

  // ── Widget reorder with drop zones ──────────────────────
  // Long press selects a widget, then drop zones appear BETWEEN widgets
  // Click a drop zone to insert the widget at that position
  let moveSourceId = null;
  let holdTimer = null;

  function onWidgetMouseDown(e, id) {
    if (e.target.closest('button, input, select, a, textarea')) return;
    holdTimer = setTimeout(() => {
      moveSourceId = id;
    }, 1200);
  }

  function onWidgetMouseUp() {
    clearTimeout(holdTimer);
  }

  function onWidgetMouseLeave() {
    clearTimeout(holdTimer);
  }

  function insertWidgetAt(targetOrder) {
    if (!moveSourceId) return;
    const sorted = [...widgetConfig].sort((a, b) => a.order - b.order);
    const srcIdx = sorted.findIndex(w => w.id === moveSourceId);
    if (srcIdx === -1) { moveSourceId = null; return; }

    // Remove source
    const [moved] = sorted.splice(srcIdx, 1);
    // Insert at the target position (clamped)
    const insertAt = Math.min(targetOrder, sorted.length);
    sorted.splice(insertAt, 0, moved);

    // Reassign sequential orders
    sorted.forEach((w, i) => {
      const cfg = widgetConfig.find(c => c.id === w.id);
      if (cfg) cfg.order = i;
    });

    saveWidgetConfig();
    moveSourceId = null;
  }

  function cancelMove() {
    moveSourceId = null;
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
  let weatherCard;
  let activityCard;

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

  <!-- Move mode hint -->
  {#if moveSourceId}
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="move-hint" on:click={cancelMove}>
      {'\u2195\uFE0F'} Cliquez sur une zone verte pour placer le widget, ou cliquez ici pour annuler
    </div>
  {/if}

  <!-- Cards Grid (6-column base for flexible sizing) -->
  <div class="cards-grid-flex">
    {#each orderedWidgets as wc, i (wc.id)}
      <!-- Drop zone BEFORE this widget (only in move mode) -->
      {#if moveSourceId && moveSourceId !== wc.id}
        <!-- svelte-ignore a11y_click_events_have_key_events -->
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div class="drop-zone" style="grid-column:{sizeToSpan(wc.size)}" on:click={() => insertWidgetAt(i)}>
          <div class="drop-zone-line"></div>
          <span class="drop-zone-label">{'\u2B07'} Ins{'\u00e9'}rer ici</span>
          <div class="drop-zone-line"></div>
        </div>
      {/if}

      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <div
        class="card-slot-flex"
        class:move-source={moveSourceId === wc.id}
        style="grid-column:{sizeToSpan(wc.size)}"
        on:mousedown={(e) => onWidgetMouseDown(e, wc.id)}
        on:mouseup={onWidgetMouseUp}
        on:mouseleave={onWidgetMouseLeave}
      >
        {#if wc.id === 'priority'}<PriorityCard bind:this={priorityCard} />
        {:else if wc.id === 'sysmon'}<SysMonCard bind:this={sysMonCard} />
        {:else if wc.id === 'gauge'}<GaugeChart bind:this={gaugeChart} />
        {:else if wc.id === 'sparkline'}<SparklineChart bind:this={sparklineChart} />
        {:else if wc.id === 'donut'}<DonutChart bind:this={donutChart} />
        {:else if wc.id === 'quicklinks'}<QuickLinksCard />
        {:else if wc.id === 'weather'}<WeatherCard bind:this={weatherCard} />
        {:else if wc.id === 'activity'}<ActivityCard bind:this={activityCard} />
        {/if}
      </div>
    {/each}

    <!-- Drop zone at the END (to move widget to last position) -->
    {#if moveSourceId}
      <!-- svelte-ignore a11y_click_events_have_key_events -->
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <div class="drop-zone drop-zone-end" style="grid-column:span 6" on:click={() => insertWidgetAt(orderedWidgets.length)}>
        <div class="drop-zone-line"></div>
        <span class="drop-zone-label">{'\u2B07'} Ins{'\u00e9'}rer en dernier</span>
        <div class="drop-zone-line"></div>
      </div>
    {/if}
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
    transition: box-shadow 0.3s, border-color 0.3s, transform 0.2s;
    border-radius: 14px;
    position: relative;
    display: flex;
    flex-direction: column;
  }
  /* Force child card components to fill the full height */
  .card-slot-flex > :global(*) {
    flex: 1;
    display: flex;
    flex-direction: column;
  }

  /* Move mode styles */
  .card-slot-flex.move-source {
    box-shadow: 0 0 20px rgba(108,99,255,0.35);
    transform: scale(0.96);
    opacity: 0.6;
    z-index: 2;
  }
  .card-slot-flex.move-source::after {
    content: '\u2705 S\00e9lectionn\00e9';
    position: absolute;
    top: 50%; left: 50%;
    transform: translate(-50%, -50%);
    background: var(--accent, #6C63FF);
    color: #fff;
    font-size: 0.85rem;
    font-weight: 700;
    padding: 8px 20px;
    border-radius: 10px;
    z-index: 10;
    pointer-events: none;
    box-shadow: 0 4px 16px rgba(108,99,255,0.4);
  }

  /* Drop zones between widgets */
  .drop-zone {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 0;
    cursor: pointer;
    border-radius: 10px;
    transition: all 0.15s;
    min-height: 36px;
  }
  .drop-zone:hover {
    background: rgba(34,197,94,0.08);
  }
  .drop-zone:hover .drop-zone-line {
    background: #22C55E;
    height: 3px;
  }
  .drop-zone:hover .drop-zone-label {
    color: #22C55E;
    opacity: 1;
  }
  .drop-zone-line {
    flex: 1;
    height: 2px;
    background: rgba(34,197,94,0.3);
    border-radius: 2px;
    transition: all 0.15s;
  }
  .drop-zone-label {
    font-size: 0.72rem;
    font-weight: 600;
    color: rgba(34,197,94,0.5);
    white-space: nowrap;
    transition: all 0.15s;
    opacity: 0.7;
  }

  .move-hint {
    background: rgba(108,99,255,0.1);
    border: 1px solid rgba(108,99,255,0.2);
    border-radius: 10px;
    padding: 10px 16px;
    margin-bottom: 12px;
    font-size: 0.82rem;
    color: var(--accent, #6C63FF);
    text-align: center;
    cursor: pointer;
    animation: fadeIn 0.2s ease;
  }
  .move-hint:hover { background: rgba(108,99,255,0.15); }

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
