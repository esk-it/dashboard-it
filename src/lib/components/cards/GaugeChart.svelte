<script>
  import { onMount } from 'svelte';
  import { api } from '../../api/client.js';
  import GlassCard from '../GlassCard.svelte';

  let percent = 0;
  let loading = true;

  export function refresh() {
    fetchData();
  }

  onMount(() => {
    fetchData();
  });

  async function fetchData() {
    loading = true;
    try {
      const data = await api.get('/api/dashboard/stats/completion');
      percent = data.percent || data.completion || 0;
    } catch (e) {
      percent = 0;
    }
    loading = false;
  }

  // SVG arc math
  const cx = 100;
  const cy = 100;
  const r = 80;
  const startAngle = Math.PI;
  const endAngle = 2 * Math.PI;

  function polarToCartesian(angle) {
    return {
      x: cx + r * Math.cos(angle),
      y: cy + r * Math.sin(angle),
    };
  }

  function describeArc(startA, endA) {
    const start = polarToCartesian(startA);
    const end = polarToCartesian(endA);
    const largeArc = endA - startA > Math.PI ? 1 : 0;
    return `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArc} 1 ${end.x} ${end.y}`;
  }

  $: filledAngle = startAngle + (percent / 100) * (endAngle - startAngle);
  $: trackPath = describeArc(startAngle, endAngle);
  $: fillPath = percent > 0 ? describeArc(startAngle, Math.min(filledAngle, endAngle - 0.01)) : '';
</script>

<GlassCard padding="0">
  <div class="card-inner">
    <div class="card-header">
      <h3>{'\u{1F4C8}'} Compl&eacute;tion du mois</h3>
    </div>

    <div class="gauge-container">
      <svg viewBox="0 0 200 120" class="gauge-svg">
        <!-- Track -->
        <path
          d={trackPath}
          fill="none"
          stroke="rgba(255,255,255,0.06)"
          stroke-width="14"
          stroke-linecap="round"
        />
        <!-- Fill -->
        {#if percent > 0}
          <path
            d={fillPath}
            fill="none"
            stroke="var(--accent)"
            stroke-width="14"
            stroke-linecap="round"
            class="gauge-fill"
          />
        {/if}
      </svg>
      <div class="gauge-label">
        <span class="gauge-value">{Math.round(percent)}%</span>
      </div>
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

  .gauge-container {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 8px 20px 20px;
  }

  .gauge-svg {
    width: 100%;
    max-width: 220px;
  }

  .gauge-fill {
    filter: drop-shadow(0 0 6px rgba(var(--accent-rgb), 0.5));
    transition: d 0.6s ease;
  }

  .gauge-label {
    position: absolute;
    bottom: 28px;
    display: flex;
    flex-direction: column;
    align-items: center;
  }

  .gauge-value {
    font-size: 28px;
    font-weight: 700;
    color: var(--text-primary);
  }
</style>
