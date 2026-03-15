<script>
  import { onMount } from 'svelte';
  import { api } from '../../api/client.js';
  import GlassCard from '../GlassCard.svelte';
  import { Line } from 'svelte-chartjs';
  import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Filler,
    Tooltip,
  } from 'chart.js';

  ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Filler, Tooltip);

  let weeklyData = [];
  let loading = true;

  const labels = ['S-7', 'S-6', 'S-5', 'S-4', 'S-3', 'S-2', 'S-1', 'Cur.'];

  export function refresh() {
    fetchData();
  }

  onMount(() => {
    fetchData();
  });

  async function fetchData() {
    loading = true;
    try {
      const data = await api.get('/api/dashboard/stats/weekly');
      weeklyData = data.values || data.weekly || data || [];
    } catch (e) {
      weeklyData = [0, 0, 0, 0, 0, 0, 0, 0];
    }
    loading = false;
  }

  $: chartData = {
    labels: labels.slice(0, weeklyData.length || 8),
    datasets: [
      {
        data: weeklyData,
        borderColor: 'rgba(6, 166, 201, 1)',
        backgroundColor: (ctx) => {
          if (!ctx.chart?.ctx) return 'rgba(6, 166, 201, 0.1)';
          const gradient = ctx.chart.ctx.createLinearGradient(0, 0, 0, ctx.chart.height);
          gradient.addColorStop(0, 'rgba(6, 166, 201, 0.3)');
          gradient.addColorStop(1, 'rgba(6, 166, 201, 0.02)');
          return gradient;
        },
        fill: true,
        tension: 0.4,
        borderWidth: 2,
        pointRadius: 3,
        pointBackgroundColor: 'rgba(6, 166, 201, 1)',
        pointBorderColor: 'transparent',
        pointHoverRadius: 5,
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
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
    scales: {
      x: {
        grid: { display: false },
        ticks: {
          color: 'rgba(148, 163, 184, 0.5)',
          font: { size: 10 },
        },
        border: { display: false },
      },
      y: {
        display: false,
        beginAtZero: true,
      },
    },
  };
</script>

<GlassCard padding="0">
  <div class="card-inner">
    <div class="card-header">
      <h3>{'\u{1F4CA}'} Tendance hebdomadaire</h3>
    </div>

    <div class="chart-container">
      {#if !loading}
        <Line data={chartData} options={chartOptions} />
      {:else}
        <div class="loading">Chargement...</div>
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

  .chart-container {
    padding: 12px 16px 16px;
    height: 180px;
  }

  .loading {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    color: var(--text-muted);
    font-size: 13px;
  }
</style>
