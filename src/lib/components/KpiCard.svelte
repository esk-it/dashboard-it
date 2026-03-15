<script>
  import { onMount } from 'svelte';

  export let title = '';
  export let value = 0;
  export let hint = '';
  export let orbColor = [6, 166, 201];
  export let onClick = null;

  let displayValue = 0;
  let el;
  let tiltX = 0;
  let tiltY = 0;
  let flashing = false;

  // Count-up animation
  $: if (value !== undefined) {
    animateValue(value);
  }

  function animateValue(target) {
    const start = displayValue;
    const diff = target - start;
    const duration = 600;
    const startTime = performance.now();
    flashing = true;
    setTimeout(() => flashing = false, 400);

    function step(now) {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      displayValue = Math.round(start + diff * eased);
      if (progress < 1) {
        requestAnimationFrame(step);
      }
    }
    requestAnimationFrame(step);
  }

  function handleMouseMove(e) {
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width;
    const y = (e.clientY - rect.top) / rect.height;
    tiltX = (y - 0.5) * -8;
    tiltY = (x - 0.5) * 8;
  }

  function handleMouseLeave() {
    tiltX = 0;
    tiltY = 0;
  }
</script>

<!-- svelte-ignore a11y_click_events_have_key_events -->
<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
  class="kpi-card"
  class:clickable={!!onClick}
  class:flash={flashing}
  bind:this={el}
  on:mousemove={handleMouseMove}
  on:mouseleave={handleMouseLeave}
  on:click={onClick}
  style="transform: perspective(800px) rotateX({tiltX}deg) rotateY({tiltY}deg);"
>
  <!-- Orb gradient -->
  <div
    class="orb"
    style="background: radial-gradient(circle at 80% 20%, rgba({orbColor[0]},{orbColor[1]},{orbColor[2]}, 0.25) 0%, transparent 60%);"
  ></div>

  <div class="kpi-content">
    <span class="kpi-title">{title}</span>
    <span class="kpi-value">{displayValue}</span>
    {#if hint}
      <span class="kpi-hint">{hint}</span>
    {/if}
  </div>
</div>

<style>
  .kpi-card {
    position: relative;
    background: var(--bg-card);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid var(--border-subtle);
    border-radius: 16px;
    padding: 20px;
    overflow: hidden;
    transition: border-color 0.2s ease, transform 0.15s ease, box-shadow 0.3s ease;
    will-change: transform;
    min-width: 0;
  }

  .kpi-card:hover {
    border-color: var(--border-hover);
  }

  .kpi-card.clickable {
    cursor: pointer;
  }

  .kpi-card.flash {
    animation: kpiFlash 0.4s ease;
  }

  .orb {
    position: absolute;
    inset: 0;
    pointer-events: none;
    z-index: 0;
  }

  .kpi-content {
    position: relative;
    z-index: 1;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .kpi-title {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.8px;
    text-transform: uppercase;
    color: var(--text-muted);
  }

  .kpi-value {
    font-size: 32px;
    font-weight: 700;
    color: var(--text-primary);
    line-height: 1.1;
    animation: countUp 0.6s ease-out;
  }

  .kpi-hint {
    font-size: 12px;
    color: var(--text-secondary);
    margin-top: 2px;
  }

  @keyframes kpiFlash {
    0% { box-shadow: 0 0 0 rgba(var(--accent-rgb), 0); }
    50% { box-shadow: 0 0 20px rgba(var(--accent-rgb), 0.3); }
    100% { box-shadow: 0 0 0 rgba(var(--accent-rgb), 0); }
  }
</style>
