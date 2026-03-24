<script>
  import { onMount } from 'svelte';
  import GlassCard from '../GlassCard.svelte';

  let activities = [];
  let loading = true;

  export async function refresh() { await load(); }

  onMount(load);

  async function load() {
    loading = true;
    try {
      const res = await fetch('http://localhost:8010/api/dashboard/activity?limit=10');
      activities = await res.json();
    } catch { activities = []; }
    loading = false;
  }

  function timeAgo(dateStr) {
    if (!dateStr) return '';
    try {
      const d = new Date(dateStr);
      const now = new Date();
      const diffMs = now - d;
      const mins = Math.floor(diffMs / 60000);
      if (mins < 1) return "À l'instant";
      if (mins < 60) return `Il y a ${mins} min`;
      const hours = Math.floor(mins / 60);
      if (hours < 24) return `Il y a ${hours}h`;
      const days = Math.floor(hours / 24);
      if (days === 1) return 'Hier';
      if (days < 7) return `Il y a ${days}j`;
      return d.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' });
    } catch { return ''; }
  }
</script>

<GlassCard padding="0">
  <div class="card-inner">
    <div class="card-header">
      <h3>{'\u{1F553}'} Activit{'\u00e9'} r{'\u00e9'}cente</h3>
    </div>

    <div class="activity-list">
      {#if loading}
        <div class="activity-empty">Chargement...</div>
      {:else if activities.length === 0}
        <div class="activity-empty">Aucune activit{'\u00e9'} r{'\u00e9'}cente</div>
      {:else}
        {#each activities as item}
          <div class="activity-item">
            <span class="activity-emoji">{item.emoji}</span>
            <div class="activity-info">
              <span class="activity-text">{item.text}</span>
              <span class="activity-time">{timeAgo(item.date)}</span>
            </div>
          </div>
        {/each}
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
    padding: 16px 20px 12px;
    border-bottom: 1px solid var(--border-subtle);
  }

  .card-header h3 {
    font-size: 14px;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0;
  }

  .activity-list {
    padding: 8px 12px;
  }

  .activity-item {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 10px 8px;
    border-radius: 8px;
    transition: background 0.15s;
  }

  .activity-item:hover {
    background: var(--bg-hover);
  }

  .activity-emoji {
    font-size: 16px;
    flex-shrink: 0;
    margin-top: 1px;
  }

  .activity-info {
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 0;
  }

  .activity-text {
    font-size: 13px;
    color: var(--text-primary);
    line-height: 1.35;
  }

  .activity-time {
    font-size: 11px;
    color: var(--text-muted);
  }

  .activity-empty {
    padding: 24px;
    text-align: center;
    color: var(--text-muted);
    font-size: 13px;
  }
</style>
