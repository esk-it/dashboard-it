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

  <!-- Cards Grid -->
  <div class="cards-grid">
    <div class="card-slot">
      <PriorityCard bind:this={priorityCard} />
    </div>
    <div class="card-slot">
      <SysMonCard bind:this={sysMonCard} />
    </div>
    <div class="card-slot">
      <GaugeChart bind:this={gaugeChart} />
    </div>
    <div class="card-slot">
      <SparklineChart bind:this={sparklineChart} />
    </div>
    <div class="card-slot">
      <DonutChart bind:this={donutChart} />
    </div>
    <div class="card-slot">
      <QuickLinksCard />
    </div>
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
</style>
