<script>
  import GlassCard from '../GlassCard.svelte';

  const placeholderItems = [
    { emoji: '✅', text: 'Tâche "Mise à jour serveur" complétée', time: 'Il y a 2h' },
    { emoji: '\u{1F4C4}', text: 'Document "Procédure VPN" ajouté', time: 'Il y a 4h' },
    { emoji: '\u{1F5A5}\uFE0F', text: 'Nouvel équipement ajouté au parc', time: 'Hier' },
  ];
</script>

<GlassCard padding="0">
  <div class="card-inner">
    <div class="card-header">
      <h3>{'\u{1F553}'} Activit&eacute; r&eacute;cente</h3>
    </div>

    <div class="activity-list">
      {#each placeholderItems as item}
        <div class="activity-item">
          <span class="activity-emoji">{item.emoji}</span>
          <div class="activity-info">
            <span class="activity-text">{item.text}</span>
            <span class="activity-time">{item.time}</span>
          </div>
        </div>
      {/each}
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
</style>
