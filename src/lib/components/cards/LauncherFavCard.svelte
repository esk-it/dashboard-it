<script>
  import { onMount } from 'svelte';
  import GlassCard from '../GlassCard.svelte';

  let favorites = [];
  let loading = true;

  export async function refresh() { await load(); }

  onMount(load);

  async function load() {
    loading = true;
    try {
      const res = await fetch('http://localhost:8010/api/launcher');
      const all = await res.json();
      favorites = all.filter(l => l.favorite);
    } catch { favorites = []; }
    loading = false;
  }

  function getIconSrc(link) {
    if (link.icon_type === 'local') return `http://localhost:8010/api/launcher/${link.id}/icon`;
    if (link.icon_type === 'url' && link.icon_value) return link.icon_value;
    return null;
  }

  async function openLink(url) {
    try {
      const { open } = await import('@tauri-apps/plugin-shell');
      await open(url);
    } catch {
      window.open(url, '_blank');
    }
  }
</script>

<GlassCard padding="0">
  <div class="card-inner">
    <div class="card-header">
      <h3>{'\u{1F680}'} Liens favoris</h3>
    </div>
    <div class="fav-list">
      {#if loading}
        <div class="fav-empty">Chargement...</div>
      {:else if favorites.length === 0}
        <div class="fav-empty">Aucun favori — ajoutez-en dans le Lanceur</div>
      {:else}
        {#each favorites as link}
          <button class="fav-item" on:click={() => openLink(link.url)}>
            <div class="fav-icon" style="background:{link.color}18; border-color:{link.color}30">
              {#if getIconSrc(link)}
                <img src={getIconSrc(link)} alt="" class="fav-img" />
              {:else}
                <span class="fav-emoji">{link.icon_value || '\u{1F517}'}</span>
              {/if}
            </div>
            <span class="fav-name">{link.name}</span>
          </button>
        {/each}
      {/if}
    </div>
  </div>
</GlassCard>

<style>
  .card-inner { display: flex; flex-direction: column; flex: 1; }
  .card-header {
    padding: 16px 20px 12px;
    border-bottom: 1px solid var(--border-subtle);
  }
  .card-header h3 { font-size: 14px; font-weight: 600; color: var(--text-primary); margin: 0; }

  .fav-list {
    display: flex; flex-wrap: wrap; gap: 8px; padding: 14px 16px;
  }
  .fav-empty {
    padding: 16px; text-align: center; color: var(--text-muted); font-size: 12px; width: 100%;
  }
  .fav-item {
    display: flex; flex-direction: column; align-items: center; gap: 6px;
    padding: 10px 12px; border-radius: 10px; cursor: pointer;
    background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.04);
    transition: all 0.15s; font-family: inherit; color: inherit;
    min-width: 72px;
  }
  .fav-item:hover {
    background: rgba(255,255,255,0.06); border-color: rgba(255,255,255,0.1);
    transform: translateY(-2px);
  }
  .fav-icon {
    width: 40px; height: 40px; border-radius: 10px; border: 1px solid;
    display: flex; align-items: center; justify-content: center;
  }
  .fav-img { width: 24px; height: 24px; object-fit: contain; border-radius: 4px; }
  .fav-emoji { font-size: 20px; }
  .fav-name { font-size: 11px; font-weight: 600; color: var(--text-primary); text-align: center; max-width: 80px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>
