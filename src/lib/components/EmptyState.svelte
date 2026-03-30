<script>
  export let emoji = '📭';
  export let title = 'Rien ici';
  export let description = '';
  export let actionLabel = '';
  export let onAction = null;
</script>

<div class="empty-state">
  <div class="empty-visual">
    <div class="empty-circle">
      <span class="empty-emoji">{emoji}</span>
    </div>
    <div class="empty-ring ring-1"></div>
    <div class="empty-ring ring-2"></div>
  </div>
  <h3 class="empty-title">{title}</h3>
  {#if description}
    <p class="empty-desc">{description}</p>
  {/if}
  {#if actionLabel && onAction}
    <button class="empty-action" on:click={onAction}>{actionLabel}</button>
  {/if}
</div>

<style>
  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 60px 20px;
    animation: fadeIn 0.5s ease;
  }

  .empty-visual {
    position: relative;
    width: 100px;
    height: 100px;
    margin-bottom: 20px;
  }

  .empty-circle {
    position: absolute;
    inset: 0;
    background: rgba(var(--accent-rgb, 108,99,255), 0.08);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    border: 1px solid rgba(var(--accent-rgb, 108,99,255), 0.15);
  }

  .empty-emoji {
    font-size: 36px;
    animation: floatEmoji 3s ease-in-out infinite;
  }

  .empty-ring {
    position: absolute;
    inset: -8px;
    border-radius: 50%;
    border: 1px solid rgba(var(--accent-rgb, 108,99,255), 0.08);
    animation: ringPulse 3s ease-in-out infinite;
  }
  .ring-2 {
    inset: -18px;
    animation-delay: 0.5s;
    border-color: rgba(var(--accent-rgb, 108,99,255), 0.04);
  }

  .empty-title {
    margin: 0 0 6px;
    font-size: 18px;
    font-weight: 700;
    color: var(--text-primary);
  }

  .empty-desc {
    margin: 0 0 18px;
    font-size: 13px;
    color: var(--text-muted);
    text-align: center;
    max-width: 320px;
    line-height: 1.5;
  }

  .empty-action {
    background: var(--accent);
    color: #fff;
    border: none;
    border-radius: 10px;
    padding: 10px 24px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    font-family: inherit;
    box-shadow: 0 4px 16px rgba(var(--accent-rgb, 108,99,255), 0.3);
    transition: all 0.2s;
  }
  .empty-action:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 24px rgba(var(--accent-rgb, 108,99,255), 0.4);
  }

  @keyframes floatEmoji {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-6px); }
  }

  @keyframes ringPulse {
    0%, 100% { transform: scale(1); opacity: 1; }
    50% { transform: scale(1.05); opacity: 0.5; }
  }

  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
  }
</style>
