<script>
  export let title = '';
  export let emoji = '';
</script>

<div class="placeholder">
  <span class="placeholder-emoji">{emoji}</span>
  <h2>{title}</h2>
  <p>Ce module sera bient&ocirc;t disponible.</p>
</div>

<style>
  .placeholder {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 60vh;
    animation: fadeIn 0.3s ease-out;
    gap: 12px;
  }

  .placeholder-emoji {
    font-size: 56px;
    margin-bottom: 8px;
    opacity: 0.6;
  }

  h2 {
    font-size: 24px;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0;
  }

  p {
    font-size: 15px;
    color: var(--text-muted);
    margin: 0;
  }
</style>
