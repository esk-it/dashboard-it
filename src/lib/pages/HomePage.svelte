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

  // Widget config
  const WIDGETS = [
    { id: 'priority', label: 'T\u00e2ches prioritaires', emoji: '\u{1F4CB}' },
    { id: 'sysmon', label: 'Monitoring syst\u00e8me', emoji: '\u{1F4BB}' },
    { id: 'gauge', label: 'Taux de compl\u00e9tion', emoji: '\u{1F4CA}' },
    { id: 'sparkline', label: 'Activit\u00e9 hebdo', emoji: '\u{1F4C8}' },
    { id: 'donut', label: 'Cat\u00e9gories', emoji: '\u{1F369}' },
    { id: 'quicklinks', label: 'Acc\u00e8s rapides', emoji: '\u26A1' },
  ];

  let visibleWidgets = {};
  let showWidgetConfig = false;

  function loadWidgetConfig() {
    try {
      const saved = localStorage.getItem('itm-widgets');
      if (saved) { visibleWidgets = JSON.parse(saved); return; }
    } catch {}
    // Default: all visible
    WIDGETS.forEach(w => visibleWidgets[w.id] = true);
  }

  function saveWidgetConfig() {
    localStorage.setItem('itm-widgets', JSON.stringify(visibleWidgets));
    visibleWidgets = { ...visibleWidgets }; // trigger reactivity
  }

  function toggleWidget(id) {
    visibleWidgets[id] = !visibleWidgets[id];
    saveWidgetConfig();
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
        <span>{'\u2699\uFE0F'} Widgets affich{'\u00e9'}s</span>
        <button class="btn-close-sm" on:click={() => showWidgetConfig = false}>{'\u2715'}</button>
      </div>
      <div class="widget-toggles">
        {#each WIDGETS as w}
          <label class="widget-toggle">
            <input type="checkbox" checked={visibleWidgets[w.id] !== false} on:change={() => toggleWidget(w.id)} />
            <span>{w.emoji} {w.label}</span>
          </label>
        {/each}
      </div>
    </div>
  {/if}

  <!-- Cards Grid -->
  <div class="cards-grid">
    {#if visibleWidgets.priority !== false}
      <div class="card-slot"><PriorityCard bind:this={priorityCard} /></div>
    {/if}
    {#if visibleWidgets.sysmon !== false}
      <div class="card-slot"><SysMonCard bind:this={sysMonCard} /></div>
    {/if}
    {#if visibleWidgets.gauge !== false}
      <div class="card-slot"><GaugeChart bind:this={gaugeChart} /></div>
    {/if}
    {#if visibleWidgets.sparkline !== false}
      <div class="card-slot"><SparklineChart bind:this={sparklineChart} /></div>
    {/if}
    {#if visibleWidgets.donut !== false}
      <div class="card-slot"><DonutChart bind:this={donutChart} /></div>
    {/if}
    {#if visibleWidgets.quicklinks !== false}
      <div class="card-slot"><QuickLinksCard /></div>
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

  /* Cards Grid */
  .cards-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
  }

  @media (max-width: 900px) {
    .cards-grid {
      grid-template-columns: 1fr;
    }
  }

  .card-slot {
    animation: fadeIn 0.4s ease-out;
    animation-fill-mode: both;
  }

  .card-slot:nth-child(1) { animation-delay: 0.05s; }
  .card-slot:nth-child(2) { animation-delay: 0.1s; }
  .card-slot:nth-child(3) { animation-delay: 0.15s; }
  .card-slot:nth-child(4) { animation-delay: 0.2s; }
  .card-slot:nth-child(5) { animation-delay: 0.25s; }
  .card-slot:nth-child(6) { animation-delay: 0.3s; }

  /* Widget config panel */
  .widget-config {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: 12px;
    padding: 14px 18px;
    margin-bottom: 16px;
    backdrop-filter: blur(12px);
    animation: fadeIn 0.2s ease-out;
  }
  .widget-config-header {
    display: flex; justify-content: space-between; align-items: center;
    margin-bottom: 10px; font-size: 0.9rem; font-weight: 600; color: var(--text-primary);
  }
  .btn-close-sm {
    background: none; border: none; color: var(--text-secondary);
    cursor: pointer; font-size: 1rem; padding: 2px 6px; border-radius: 4px;
  }
  .btn-close-sm:hover { background: var(--bg-hover); color: var(--text-primary); }
  .widget-toggles {
    display: flex; flex-wrap: wrap; gap: 12px;
  }
  .widget-toggle {
    display: flex; align-items: center; gap: 6px;
    font-size: 0.82rem; color: var(--text-secondary); cursor: pointer;
  }
  .widget-toggle input[type="checkbox"] {
    width: 16px; height: 16px; accent-color: var(--accent);
    cursor: pointer;
  }
</style>
