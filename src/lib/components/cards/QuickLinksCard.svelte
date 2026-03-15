<script>
  import { currentPage } from '../../stores/navigation.js';
  import GlassCard from '../GlassCard.svelte';

  const links = [
    { emoji: '\u{1F4DD}', label: 'Nouvelle tâche', action: () => currentPage.set('/tasks') },
    { emoji: '\u{1F4C4}', label: 'Documents', action: () => currentPage.set('/documents') },
    { emoji: '\u{1F4C5}', label: 'Planning', action: () => currentPage.set('/planning') },
    { emoji: '\u{1F6E1}\uFE0F', label: 'Sécurité', action: () => currentPage.set('/security') },
    { emoji: '\u{1F5A5}\uFE0F', label: 'Parc info', action: () => currentPage.set('/parc') },
    { emoji: '\u{1F4D6}', label: 'Procédures', action: () => currentPage.set('/wiki') },
  ];
</script>

<GlassCard padding="0">
  <div class="card-inner">
    <div class="card-header">
      <h3>{'\u26A1'} Acc&egrave;s rapides</h3>
    </div>

    <div class="links-grid">
      {#each links as link}
        <!-- svelte-ignore a11y_click_events_have_key_events -->
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div class="link-item" on:click={link.action}>
          <span class="link-emoji">{link.emoji}</span>
          <span class="link-label">{link.label}</span>
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

  .links-grid {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 6px;
    padding: 12px;
  }

  .link-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
    padding: 14px 8px;
    border-radius: 10px;
    cursor: pointer;
    transition: background 0.15s;
  }

  .link-item:hover {
    background: var(--bg-hover);
  }

  .link-emoji {
    font-size: 22px;
  }

  .link-label {
    font-size: 11.5px;
    color: var(--text-secondary);
    text-align: center;
    white-space: nowrap;
  }
</style>
