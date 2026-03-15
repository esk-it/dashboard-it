<script>
  import { onMount } from 'svelte';
  import { api } from '../../api/client.js';
  import GlassCard from '../GlassCard.svelte';
  import { Doughnut } from 'svelte-chartjs';
  import {
    Chart as ChartJS,
    ArcElement,
    Tooltip,
    Legend,
  } from 'chart.js';

  ChartJS.register(ArcElement, Tooltip, Legend);

  let categories = [];
  let loading = true;

  const colors = ['#4B8BFF', '#22C55E', '#F59E0B', '#EC4899', '#8B5CF6', '#14B8A6', '#F97316'];

  export function refresh() {
    fetchData();
  }

  onMount(() => {
    fetchData();
  });

  async function fetchData() {
    loading = true;
    try {
      const data = await api.get('/api/dashboard/stats/categories');
      categories = data.categories || data || [];
    } catch (e) {
      categories = [];
    }
    loading = false;
  }

  $: total = categories.reduce((sum, c) => sum + (c.count || c.value || 0), 0);

  $: chartData = {
    labels: categories.map(c => c.name || c.label || ''),
    datasets: [
      {
        data: categories.map(c => c.count || c.value || 0),
        backgroundColor: colors.slice(0, categories.length),
        borderColor: 'rgba(14, 20, 36, 0.8)',
        borderWidth: 2,
        hoverBorderColor: 'rgba(255, 255, 255, 0.2)',
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    cutout: '65%',
    plugins: {
      legend: {
        position: 'bottom',
        labels: {
          color: 'rgba(148, 163, 184, 0.85)',
          font: { size: 11 },
          padding: 12,
          usePointStyle: true,
          pointStyleWidth: 8,
        },
      },
      tooltip: {
        backgroundColor: 'rgba(14, 20, 36, 0.95)',
        borderColor: 'rgba(255, 255, 255, 0.08)',
        borderWidth: 1,
        titleColor: 'rgba(226, 232, 240, 0.92)',
        bodyColor: 'rgba(148, 163, 184, 0.85)',
        padding: 10,
        cornerRadius: 8,
      },
    },
  };
</script>

<GlassCard padding="0">
  <div class="card-inner">
    <div class="card-header">
      <h3>{'\u{1F4CA}'} R&eacute;partition par cat&eacute;gorie</h3>
    </div>

    <div class="chart-wrap">
      {#if !loading && categories.length > 0}
        <div class="chart-container">
          <Doughnut data={chartData} options={chartOptions} />
          <div class="center-label">
            <span class="center-value">{total}</span>
          </div>
        </div>
      {:else if loading}
        <div class="empty">Chargement...</div>
      {:else}
        <div class="empty">Aucune donn&eacute;e</div>
      {/if}
    </div>
  </div>
</GlassCard>

<style>
  .card-inner {
    display: flex;
    flex-direction: column;
  }

  .card-header {
    padding: 16px 20px 0;
  }

  .card-header h3 {
    font-size: 14px;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0;
  }

  .chart-wrap {
    padding: 12px 16px 16px;
  }

  .chart-container {
    position: relative;
    height: 220px;
  }

  .center-label {
    position: absolute;
    top: 42%;
    left: 50%;
    transform: translate(-50%, -50%);
    text-align: center;
  }

  .center-value {
    font-size: 26px;
    font-weight: 700;
    color: var(--text-primary);
  }

  .empty {
    padding: 40px;
    text-align: center;
    color: var(--text-muted);
    font-size: 13px;
  }
</style>
