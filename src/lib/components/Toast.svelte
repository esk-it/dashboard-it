<script>
  import { toasts } from '../stores/toast.js';

  const typeColors = {
    success: 'var(--success)',
    error: 'var(--danger)',
    warning: 'var(--warning)',
    info: 'var(--info)',
  };

  const typeEmojis = {
    success: '✅',
    error: '\u274C',
    warning: '\u26A0\uFE0F',
    info: 'ℹ\uFE0F',
  };
</script>

<div class="toast-container">
  {#each $toasts as toast (toast.id)}
    <div class="toast-item" style="border-left-color: {typeColors[toast.type] || typeColors.info};">
      <span class="toast-icon">{typeEmojis[toast.type] || typeEmojis.info}</span>
      <span class="toast-message">{toast.message}</span>
    </div>
  {/each}
</div>

<style>
  .toast-container {
    position: fixed;
    top: 16px;
    right: 16px;
    z-index: 9999;
    display: flex;
    flex-direction: column;
    gap: 8px;
    pointer-events: none;
  }

  .toast-item {
    pointer-events: auto;
    background: var(--bg-card-solid);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid var(--border-subtle);
    border-left: 4px solid var(--accent);
    border-radius: 12px;
    padding: 12px 16px;
    display: flex;
    align-items: center;
    gap: 10px;
    min-width: 280px;
    max-width: 400px;
    animation: slideInFromRight 0.3s ease-out;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  }

  .toast-icon {
    font-size: 16px;
    flex-shrink: 0;
  }

  .toast-message {
    font-size: 13.5px;
    color: var(--text-primary);
    line-height: 1.4;
  }
</style>
