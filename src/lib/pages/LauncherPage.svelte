<script>
  import { onMount } from 'svelte';
  import { api } from '../api/client.js';
  import { success, error as toastError } from '../stores/toast.js';

  const API = 'http://localhost:8010/api/launcher';

  // Predefined icon/logo suggestions for common services
  const PRESETS = [
    { name: 'Google', icon: '🔍', color: '#4285F4', url: 'https://google.com' },
    { name: 'Gmail', icon: '📧', color: '#EA4335', url: 'https://mail.google.com' },
    { name: 'Google Admin', icon: '🔧', color: '#4285F4', url: 'https://admin.google.com' },
    { name: 'Zyxel Nebula', icon: '📡', color: '#FF6600', url: 'https://nebula.zyxel.com' },
    { name: 'GLPI', icon: '🖥️', color: '#6C63FF', url: '' },
    { name: 'Windows Admin', icon: '🪟', color: '#0078D4', url: '' },
    { name: 'Active Directory', icon: '🏢', color: '#0078D4', url: '' },
    { name: 'WithSecure', icon: '🛡️', color: '#2D6CDF', url: 'https://elements.withsecure.com' },
    { name: 'GitHub', icon: '🐙', color: '#333333', url: 'https://github.com' },
    { name: 'Office 365', icon: '📋', color: '#D83B01', url: 'https://portal.office.com' },
    { name: 'Azure Portal', icon: '☁️', color: '#0089D6', url: 'https://portal.azure.com' },
    { name: 'OVH', icon: '🌐', color: '#123F6D', url: 'https://www.ovh.com/manager' },
    { name: 'Zabbix', icon: '📊', color: '#D40000', url: '' },
  ];

  // Get favicon URL from a site URL
  function getFaviconUrl(siteUrl, size = 64) {
    try {
      const domain = new URL(siteUrl).hostname;
      return `https://www.google.com/s2/favicons?domain=${domain}&sz=${size}`;
    } catch { return null; }
  }

  // Auto-detect: use favicon if URL is set, otherwise emoji
  function getIconDisplay(link) {
    if (link.icon_type === 'emoji') return { type: 'emoji', value: link.icon_value };
    if (link.icon_type === 'favicon' && link.icon_value) return { type: 'img', value: link.icon_value };
    // Auto: try favicon from URL
    const fav = getFaviconUrl(link.url, 64);
    if (fav) return { type: 'img', value: fav };
    return { type: 'emoji', value: link.icon_value || '🔗' };
  }

  const CATEGORIES = ['Administration', 'Réseau', 'Cloud', 'Sécurité', 'Outils', 'Supervision', 'Communication', 'Autre'];
  const EMOJI_PALETTE = ['🔗','🌐','🖥️','📡','🛡️','🔧','📧','📋','☁️','🏢','🔍','📊','🐙','🪟','💾','📁','🔒','📞','🖨️','⚡'];
  const COLOR_PALETTE = ['#4285F4','#EA4335','#FBBC04','#34A853','#FF6600','#0078D4','#6C63FF','#D83B01','#8B5CF6','#EC4899','#22C55E','#EF4444','#F59E0B','#06B6D4','#333333'];

  let links = [];
  let categories = [];
  let loading = true;
  let filterCategory = '';
  let searchQuery = '';

  // Dialog
  let showDialog = false;
  let editingLink = null;
  let form = defaultForm();
  let showPresets = false;

  // Delete
  let confirmDeleteId = null;

  function defaultForm() {
    return { name: '', url: 'https://', description: '', category: '', icon_type: 'auto', icon_value: '🔗', color: '#6C63FF', favorite: false, sort_order: 100 };
  }

  $: filteredLinks = links.filter(l => {
    if (filterCategory && l.category !== filterCategory) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return l.name.toLowerCase().includes(q) || (l.description || '').toLowerCase().includes(q) || l.url.toLowerCase().includes(q);
    }
    return true;
  });

  $: favorites = links.filter(l => l.favorite);
  $: groupedLinks = groupByCategory(filteredLinks);

  function groupByCategory(list) {
    const groups = {};
    for (const l of list) {
      const cat = l.category || 'Autre';
      if (!groups[cat]) groups[cat] = [];
      groups[cat].push(l);
    }
    return Object.entries(groups).sort((a, b) => a[0].localeCompare(b[0]));
  }

  async function loadLinks() {
    loading = true;
    try { links = await api.get('/api/launcher'); } catch { links = []; }
    loading = false;
  }

  onMount(loadLinks);

  async function openLink(link) {
    try {
      const { open } = await import('@tauri-apps/plugin-shell');
      await open(link.url);
    } catch {
      window.open(link.url, '_blank');
    }
  }

  function openNew() {
    editingLink = null;
    form = defaultForm();
    showPresets = false;
    showDialog = true;
  }

  function openEdit(link) {
    editingLink = link;
    form = { ...link };
    showPresets = false;
    showDialog = true;
  }

  function applyPreset(preset) {
    form.name = preset.name;
    form.icon_value = preset.icon;
    form.color = preset.color;
    if (preset.url) form.url = preset.url;
    showPresets = false;
  }

  async function saveLink() {
    if (!form.name.trim() || !form.url.trim()) return;
    try {
      if (editingLink) {
        await api.put(`/api/launcher/${editingLink.id}`, form);
        success('Lien modifié');
      } else {
        await api.post('/api/launcher', form);
        success('Lien créé');
      }
      showDialog = false;
      await loadLinks();
    } catch (e) { toastError('Erreur: ' + e.message); }
  }

  async function deleteLink(id) {
    try {
      await api.delete(`/api/launcher/${id}`);
      confirmDeleteId = null;
      success('Lien supprimé');
      await loadLinks();
    } catch (e) { toastError('Erreur: ' + e.message); }
  }

  async function toggleFavorite(link) {
    try {
      await api.put(`/api/launcher/${link.id}`, { ...link, favorite: !link.favorite });
      await loadLinks();
    } catch {}
  }
</script>

<div class="launcher-page">
  <header class="launcher-header">
    <div class="header-left">
      <h1>{'\u{1F680}'} Lanceur</h1>
      <p class="header-sub">{links.length} lien{links.length !== 1 ? 's' : ''} rapide{links.length !== 1 ? 's' : ''}</p>
    </div>
    <div class="header-right">
      <input type="text" class="search-input" bind:value={searchQuery} placeholder="Rechercher..." />
      <select class="filter-select" bind:value={filterCategory}>
        <option value="">Toutes cat{'\u00e9'}gories</option>
        {#each CATEGORIES as cat}<option value={cat}>{cat}</option>{/each}
      </select>
      <button class="btn-primary" on:click={openNew}>+ Nouveau lien</button>
    </div>
  </header>

  {#if loading}
    <div class="loading">Chargement...</div>
  {:else if links.length === 0}
    <div class="empty-state">
      <span class="empty-icon">{'\u{1F680}'}</span>
      <h2>Aucun lien rapide</h2>
      <p>Ajoutez vos premiers liens vers vos outils d'administration</p>
      <button class="btn-primary" on:click={openNew}>+ Ajouter un lien</button>
    </div>
  {:else}
    <!-- Favorites row -->
    {#if favorites.length > 0}
      <div class="fav-section">
        <h2 class="section-title">{'\u2B50'} Favoris</h2>
        <div class="links-grid fav-grid">
          {#each favorites as link}
            {@const ico = getIconDisplay(link)}
            <button class="link-card fav-card" on:click={() => openLink(link)}>
              <div class="card-glow" style="background:{link.color}"></div>
              <div class="card-icon" style="background:{link.color}22; border-color:{link.color}44">
                {#if ico.type === 'img'}
                  <img src={ico.value} alt="" class="icon-img" />
                {:else}
                  <span class="icon-display">{ico.value}</span>
                {/if}
              </div>
              <span class="card-name">{link.name}</span>
            </button>
          {/each}
        </div>
      </div>
    {/if}

    <!-- Grouped links -->
    {#each groupedLinks as [catName, catLinks]}
      <div class="cat-section">
        <h2 class="section-title">{catName}</h2>
        <div class="links-grid">
          {#each catLinks as link}
            <!-- svelte-ignore a11y_no_static_element_interactions -->
            {@const ico2 = getIconDisplay(link)}
            <div class="link-card" on:click={() => openLink(link)}>
              <div class="card-glow" style="background:{link.color}"></div>
              <div class="card-top">
                <div class="card-icon-lg" style="background:{link.color}15; border-color:{link.color}30">
                  {#if ico2.type === 'img'}
                    <img src={ico2.value} alt="" class="icon-img-lg" />
                  {:else}
                    <span class="icon-lg">{ico2.value}</span>
                  {/if}
                </div>
                <div class="card-actions" on:click|stopPropagation>
                  <button class="card-btn" class:fav-active={link.favorite} on:click={() => toggleFavorite(link)} title="Favori">{'\u2B50'}</button>
                  <button class="card-btn" on:click={() => openEdit(link)} title="Modifier">{'\u270F\uFE0F'}</button>
                  <button class="card-btn danger" on:click={() => confirmDeleteId = link.id} title="Supprimer">{'\u{1F5D1}\uFE0F'}</button>
                </div>
              </div>
              <h3 class="card-title">{link.name}</h3>
              {#if link.description}
                <p class="card-desc">{link.description}</p>
              {/if}
              <span class="card-url">{link.url.replace(/^https?:\/\//, '').split('/')[0]}</span>
            </div>
          {/each}
        </div>
      </div>
    {/each}
  {/if}
</div>

<!-- Delete confirmation -->
{#if confirmDeleteId}
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="modal-overlay" on:click={() => confirmDeleteId = null}>
    <div class="modal-box modal-small" on:click|stopPropagation>
      <h3>Supprimer ce lien ?</h3>
      <div class="modal-actions">
        <button class="btn-ghost" on:click={() => confirmDeleteId = null}>Annuler</button>
        <button class="btn-danger" on:click={() => deleteLink(confirmDeleteId)}>Supprimer</button>
      </div>
    </div>
  </div>
{/if}

<!-- Add/Edit Dialog -->
{#if showDialog}
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="modal-overlay" on:click={() => showDialog = false}>
    <div class="modal-box" on:click|stopPropagation>
      <div class="modal-header">
        <h2>{editingLink ? 'Modifier le lien' : 'Nouveau lien rapide'}</h2>
        <button class="modal-close" on:click={() => showDialog = false}>{'\u2715'}</button>
      </div>

      <div class="modal-body">
        <!-- Presets -->
        {#if !editingLink}
          <button class="btn-presets-toggle" on:click={() => showPresets = !showPresets}>
            {'\u26A1'} {showPresets ? 'Masquer' : 'Choisir un mod\u00e8le'}
          </button>
          {#if showPresets}
            <div class="presets-grid">
              {#each PRESETS as preset}
                <button class="preset-btn" on:click={() => applyPreset(preset)} style="border-color:{preset.color}33">
                  <span class="preset-icon" style="background:{preset.color}22">{preset.icon}</span>
                  <span class="preset-name">{preset.name}</span>
                </button>
              {/each}
            </div>
          {/if}
        {/if}

        <!-- Preview -->
        {@const previewIco = getIconDisplay(form)}
        <div class="form-preview">
          <div class="preview-card" style="border-color:{form.color}30">
            <div class="preview-icon" style="background:{form.color}22">
              {#if previewIco.type === 'img'}
                <img src={previewIco.value} alt="" class="preview-icon-img" />
              {:else}
                {previewIco.value}
              {/if}
            </div>
            <div>
              <strong>{form.name || 'Nom du lien'}</strong>
              <span class="preview-url">{form.url || 'https://...'}</span>
            </div>
          </div>
        </div>

        <div class="form-row">
          <label class="form-label form-half">
            Nom *
            <input type="text" class="form-input" bind:value={form.name} placeholder="Ex: Zyxel Nebula" />
          </label>
          <label class="form-label form-half">
            URL *
            <input type="text" class="form-input" bind:value={form.url} placeholder="https://..." />
          </label>
        </div>

        <label class="form-label">
          Description
          <input type="text" class="form-input" bind:value={form.description} placeholder="Optionnel" />
        </label>

        <div class="form-row">
          <label class="form-label form-half">
            Cat{'\u00e9'}gorie
            <select class="form-input" bind:value={form.category}>
              <option value="">— Aucune —</option>
              {#each CATEGORIES as cat}<option value={cat}>{cat}</option>{/each}
            </select>
          </label>
          <label class="form-label form-half">
            Ic{'\u00f4'}ne
            <div class="icon-type-toggle">
              <button class="icon-type-btn" class:active={form.icon_type === 'auto'} on:click={() => form.icon_type = 'auto'}>
                {'\u{1F310}'} Logo auto
              </button>
              <button class="icon-type-btn" class:active={form.icon_type === 'emoji'} on:click={() => form.icon_type = 'emoji'}>
                {'\u{1F600}'} Emoji
              </button>
            </div>
            {#if form.icon_type === 'emoji'}
              <div class="emoji-picker">
                {#each EMOJI_PALETTE as emoji}
                  <button class="emoji-btn" class:emoji-selected={form.icon_value === emoji} on:click={() => form.icon_value = emoji}>{emoji}</button>
                {/each}
              </div>
            {:else}
              <p class="icon-auto-hint">Le logo sera r{'\u00e9'}cup{'\u00e9'}r{'\u00e9'} automatiquement depuis l'URL du site</p>
              {#if form.url && form.url !== 'https://'}
                <div class="icon-auto-preview">
                  <img src={getFaviconUrl(form.url, 64)} alt="favicon" class="favicon-preview" />
                  <span class="favicon-domain">{(() => { try { return new URL(form.url).hostname; } catch { return ''; } })()}</span>
                </div>
              {/if}
            {/if}
          </label>
        </div>

        <label class="form-label">
          Couleur
          <div class="color-picker">
            {#each COLOR_PALETTE as color}
              <button class="color-btn" class:color-selected={form.color === color} style="background:{color}" on:click={() => form.color = color}></button>
            {/each}
          </div>
        </label>

        <label class="form-checkbox">
          <input type="checkbox" bind:checked={form.favorite} />
          <span>{'\u2B50'} Ajouter aux favoris (visible sur le Dashboard)</span>
        </label>
      </div>

      <div class="modal-footer">
        <button class="btn-ghost" on:click={() => showDialog = false}>Annuler</button>
        <button class="btn-primary" on:click={saveLink} disabled={!form.name.trim() || !form.url.trim()}>
          {editingLink ? 'Modifier' : 'Cr\u00e9er'}
        </button>
      </div>
    </div>
  </div>
{/if}

<style>
  .launcher-page { animation: fadeIn 0.35s ease-out; }

  .launcher-header {
    display: flex; justify-content: space-between; align-items: center;
    margin-bottom: 24px; flex-wrap: wrap; gap: 12px;
  }
  .header-left h1 { margin: 0; font-size: 1.5rem; color: var(--text-primary); }
  .header-sub { margin: 4px 0 0; font-size: 0.82rem; color: var(--text-muted); }
  .header-right { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }

  .search-input {
    padding: 7px 14px; background: var(--bg-card); border: 1px solid var(--border-subtle);
    border-radius: 8px; color: var(--text-primary); font-size: 0.85rem; min-width: 180px;
    font-family: inherit;
  }
  .search-input:focus { outline: none; border-color: var(--accent); }
  .search-input::placeholder { color: var(--text-muted); }
  .filter-select {
    padding: 7px 10px; background: var(--bg-card); border: 1px solid var(--border-subtle);
    border-radius: 8px; color: var(--text-primary); font-size: 0.85rem; font-family: inherit;
  }

  .btn-primary {
    background: var(--accent); color: #fff; border: none; border-radius: 8px;
    padding: 8px 18px; font-size: 0.85rem; font-weight: 600; cursor: pointer;
    font-family: inherit; box-shadow: 0 2px 10px rgba(var(--accent-rgb), 0.3);
    transition: all 0.15s;
  }
  .btn-primary:hover { filter: brightness(1.15); }
  .btn-primary:disabled { opacity: 0.4; }

  /* ── Empty state ───────────────────────────────────────── */
  .empty-state { text-align: center; padding: 80px 20px; }
  .empty-icon { font-size: 4rem; display: block; margin-bottom: 16px; }
  .empty-state h2 { margin: 0 0 8px; color: var(--text-primary); font-size: 1.3rem; }
  .empty-state p { color: var(--text-muted); margin: 0 0 20px; }
  .loading { text-align: center; padding: 60px; color: var(--text-muted); }

  /* ── Sections ──────────────────────────────────────────── */
  .section-title {
    font-size: 0.9rem; font-weight: 700; color: var(--text-secondary);
    margin: 0 0 12px; text-transform: uppercase; letter-spacing: 0.5px;
  }
  .fav-section { margin-bottom: 28px; }
  .cat-section { margin-bottom: 24px; }

  /* ── Cards Grid ────────────────────────────────────────── */
  .links-grid {
    display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 14px;
  }
  .fav-grid { grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); }

  /* ── Link Card ─────────────────────────────────────────── */
  .link-card {
    position: relative; background: var(--bg-card); border: 1px solid var(--border-subtle);
    border-radius: 14px; padding: 18px; cursor: pointer; overflow: hidden;
    transition: all 0.2s; backdrop-filter: blur(12px); font-family: inherit;
    text-align: left; color: inherit; display: flex; flex-direction: column;
  }
  .link-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 8px 30px rgba(0,0,0,0.2);
    border-color: rgba(255,255,255,0.12);
  }
  .card-glow {
    position: absolute; top: -40px; right: -40px; width: 100px; height: 100px;
    border-radius: 50%; opacity: 0.08; filter: blur(30px); pointer-events: none;
    transition: opacity 0.3s;
  }
  .link-card:hover .card-glow { opacity: 0.15; }

  .card-top { display: flex; justify-content: space-between; margin-bottom: 12px; }
  .card-icon-lg {
    width: 48px; height: 48px; border-radius: 12px; border: 1px solid;
    display: flex; align-items: center; justify-content: center;
  }
  .icon-lg { font-size: 24px; }
  .card-actions { display: flex; gap: 2px; opacity: 0; transition: opacity 0.15s; }
  .link-card:hover .card-actions { opacity: 1; }
  .card-btn {
    background: none; border: none; cursor: pointer; font-size: 12px;
    padding: 4px; border-radius: 6px; transition: background 0.15s; opacity: 0.6;
  }
  .card-btn:hover { background: rgba(255,255,255,0.1); opacity: 1; }
  .card-btn.danger:hover { background: rgba(239,68,68,0.15); }
  .card-btn.fav-active { opacity: 1; }

  .card-title { margin: 0 0 4px; font-size: 15px; font-weight: 700; color: var(--text-primary); }
  .card-desc { margin: 0 0 8px; font-size: 12px; color: var(--text-secondary); line-height: 1.4; }
  .card-url { font-size: 11px; color: var(--text-muted); margin-top: auto; }

  /* Favorite compact card */
  .fav-card {
    flex-direction: column; align-items: center; text-align: center;
    padding: 14px 10px; gap: 8px;
  }
  .fav-card .card-glow { top: -30px; right: auto; left: 50%; transform: translateX(-50%); }
  .card-icon { width: 44px; height: 44px; border-radius: 12px; border: 1px solid; display: flex; align-items: center; justify-content: center; }
  .icon-display { font-size: 22px; }
  .card-name { font-size: 12px; font-weight: 600; color: var(--text-primary); }

  /* ── Modal ─────────────────────────────────────────────── */
  .modal-overlay {
    position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 100;
    display: flex; align-items: center; justify-content: center;
    backdrop-filter: blur(4px); animation: fadeIn 0.15s ease;
  }
  .modal-box {
    background: var(--bg-card-solid, #1a1a2e); border: 1px solid var(--border-subtle);
    border-radius: 16px; width: 560px; max-width: 95vw; max-height: 90vh;
    overflow-y: auto; box-shadow: 0 20px 60px rgba(0,0,0,0.4);
  }
  .modal-small { width: 380px; padding: 24px; text-align: center; }
  .modal-small h3 { margin: 0 0 16px; color: var(--text-primary); }
  .modal-actions { display: flex; gap: 8px; justify-content: center; }
  .modal-header { display: flex; justify-content: space-between; align-items: center; padding: 18px 24px; }
  .modal-header h2 { margin: 0; font-size: 1.1rem; color: var(--text-primary); }
  .modal-close { background: none; border: none; color: var(--text-muted); font-size: 18px; cursor: pointer; padding: 4px 8px; border-radius: 6px; }
  .modal-close:hover { background: var(--bg-hover); }
  .modal-body { padding: 0 24px 18px; display: flex; flex-direction: column; gap: 14px; }
  .modal-footer { padding: 0 24px 18px; display: flex; justify-content: flex-end; gap: 8px; }
  .btn-ghost { background: transparent; border: 1px solid var(--border-subtle); border-radius: 8px; color: var(--text-secondary); padding: 7px 16px; cursor: pointer; font-family: inherit; font-size: 0.85rem; }
  .btn-ghost:hover { background: var(--bg-hover); }
  .btn-danger { background: #EF4444; border: none; border-radius: 8px; color: #fff; padding: 7px 16px; cursor: pointer; font-family: inherit; font-size: 0.85rem; font-weight: 600; }

  .form-label { display: flex; flex-direction: column; gap: 4px; font-size: 12px; color: var(--text-secondary); }
  .form-input { background: rgba(255,255,255,0.05); border: 1px solid var(--border-subtle); border-radius: 8px; color: var(--text-primary); font-size: 13px; padding: 8px 10px; font-family: inherit; }
  .form-input:focus { outline: none; border-color: var(--accent); }
  .form-row { display: flex; gap: 12px; }
  .form-half { flex: 1; }
  .form-checkbox { display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--text-secondary); cursor: pointer; }
  .form-checkbox input { width: 16px; height: 16px; accent-color: var(--accent); }

  /* Presets */
  .btn-presets-toggle {
    background: rgba(var(--accent-rgb), 0.08); border: 1px solid rgba(var(--accent-rgb), 0.15);
    border-radius: 8px; padding: 8px 14px; color: var(--accent); font-size: 13px;
    cursor: pointer; font-family: inherit; width: 100%; text-align: center; transition: all 0.15s;
  }
  .btn-presets-toggle:hover { background: rgba(var(--accent-rgb), 0.15); }
  .presets-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 6px; }
  .preset-btn {
    display: flex; align-items: center; gap: 6px; padding: 6px 10px;
    background: rgba(255,255,255,0.03); border: 1px solid; border-radius: 8px;
    cursor: pointer; font-family: inherit; font-size: 12px; color: var(--text-primary); transition: all 0.15s;
  }
  .preset-btn:hover { background: rgba(255,255,255,0.08); }
  .preset-icon { width: 24px; height: 24px; border-radius: 6px; display: flex; align-items: center; justify-content: center; font-size: 14px; }
  .preset-name { font-weight: 500; }

  /* Preview */
  .form-preview { display: flex; justify-content: center; }
  .preview-card {
    display: flex; align-items: center; gap: 12px; padding: 10px 16px;
    background: rgba(255,255,255,0.03); border: 1px solid; border-radius: 10px; min-width: 240px;
  }
  .preview-icon { width: 36px; height: 36px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 20px; }
  .preview-card strong { display: block; font-size: 13px; color: var(--text-primary); }
  .preview-url { font-size: 11px; color: var(--text-muted); }

  /* Emoji picker */
  .emoji-picker { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 4px; }
  .emoji-btn {
    width: 32px; height: 32px; border: 1px solid var(--border-subtle); border-radius: 6px;
    background: transparent; cursor: pointer; font-size: 16px; transition: all 0.15s;
    display: flex; align-items: center; justify-content: center;
  }
  .emoji-btn:hover { background: rgba(255,255,255,0.08); }
  .emoji-btn.emoji-selected { border-color: var(--accent); background: rgba(var(--accent-rgb), 0.15); }

  /* Color picker */
  .color-picker { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 4px; }
  .color-btn {
    width: 28px; height: 28px; border-radius: 50%; border: 2px solid transparent;
    cursor: pointer; transition: all 0.15s;
  }
  .color-btn:hover { transform: scale(1.15); }
  .color-btn.color-selected { border-color: #fff; box-shadow: 0 0 8px rgba(255,255,255,0.3); transform: scale(1.15); }

  /* Favicon / logo images */
  .icon-img { width: 28px; height: 28px; object-fit: contain; border-radius: 4px; }
  .icon-img-lg { width: 32px; height: 32px; object-fit: contain; border-radius: 6px; }
  .preview-icon-img { width: 24px; height: 24px; object-fit: contain; border-radius: 4px; }

  /* Icon type toggle */
  .icon-type-toggle { display: flex; gap: 4px; margin-top: 4px; }
  .icon-type-btn {
    flex: 1; padding: 5px 8px; font-size: 11px; border: 1px solid var(--border-subtle);
    border-radius: 6px; background: transparent; color: var(--text-secondary);
    cursor: pointer; font-family: inherit; transition: all 0.15s; text-align: center;
  }
  .icon-type-btn:hover { background: rgba(255,255,255,0.05); }
  .icon-type-btn.active {
    background: rgba(var(--accent-rgb), 0.15); border-color: var(--accent); color: var(--accent);
  }
  .icon-auto-hint { font-size: 11px; color: var(--text-muted); margin: 6px 0 0; }
  .icon-auto-preview {
    display: flex; align-items: center; gap: 8px; margin-top: 6px;
    padding: 6px 10px; background: rgba(255,255,255,0.03); border-radius: 6px;
  }
  .favicon-preview { width: 32px; height: 32px; border-radius: 6px; }
  .favicon-domain { font-size: 12px; color: var(--text-secondary); }
</style>
