<script>
  export let padding = '20px';
  export let hover = true;
</script>

<div class="glass-card" class:hoverable={hover} style="padding: {padding}">
  <slot />
</div>

<style>
  .glass-card {
    background: var(--bg-card);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid var(--border-subtle);
    border-radius: 16px;
    transition: border-color 0.2s ease, transform 0.2s ease;
  }

  .hoverable:hover {
    border-color: var(--border-hover);
    transform: translateY(-1px);
  }
</style>
