<script>
  import GlassCard from '../GlassCard.svelte';
</script>

<GlassCard padding="0">
  <div class="card-inner">
    <div class="card-header">
      <h3>{'\u{1F4C5}'} &Eacute;v&eacute;nements &agrave; venir</h3>
    </div>
    <div class="empty">
      <span class="empty-emoji">{'\u{1F4AD}'}</span>
      <p>Aucun &eacute;v&eacute;nement &agrave; venir</p>
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

  .empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    padding: 32px 20px;
  }

  .empty-emoji {
    font-size: 28px;
    opacity: 0.5;
  }

  .empty p {
    font-size: 13px;
    color: var(--text-muted);
    margin: 0;
  }
</style>
