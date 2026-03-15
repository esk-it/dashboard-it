<script>
  import { onMount, onDestroy } from 'svelte';
  import { api } from '../api/client.js';
  import { success, error as toastError } from '../stores/toast.js';

  // ── Constants ──────────────────────────────────────────────
  const IMPACT_LEVELS = [
    { value: 'low',      label: 'Faible',    color: '#22C55E' },
    { value: 'medium',   label: 'Moyen',     color: '#F59E0B' },
    { value: 'high',     label: 'Élevé',     color: '#F97316' },
    { value: 'critical', label: 'Critique',  color: '#EF4444' },
  ];

  const CATEGORY_COLORS = {
    'Réseau':        '#3B82F6',
    'Serveur':       '#8B5CF6',
    'Sécurité':      '#EF4444',
    'Application':   '#22C55E',
    'Infrastructure':'#F59E0B',
    'Poste':         '#EC4899',
    'Active Directory': '#06A6C9',
    'Messagerie':    '#F97316',
  };

  // ── State ──────────────────────────────────────────────
  let entries = [];
  let categories = [];
  let loading = true;

  // Filters
  let filterCategory = '';
  let filterImpact = '';
  let searchQuery = '';
  let searchDebounceTimer;

  // Dialog
  let showDialog = false;
  let editingEntry = null;
  let form = defaultForm();

  // Delete confirmation
  let confirmDeleteId = null;

  // ── Derived ────────────────────────────────────────────
  $: filteredEntries = entries.filter(e => {
    if (filterCategory && e.category !== filterCategory) return false;
    if (filterImpact && e.impact !== filterImpact) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return (e.title || '').toLowerCase().includes(q)
        || (e.description || '').toLowerCase().includes(q)
        || (e.author || '').toLowerCase().includes(q);
    }
    return true;
  }).sort((a, b) => {
    const da = a.event_date || a.created_at || '';
    const db = b.event_date || b.created_at || '';
    return db.localeCompare(da);
  });

  $: totalEntries = entries.length;
  $: categoryCounts = entries.reduce((acc, e) => {
    const cat = e.category || 'Autre';
    acc[cat] = (acc[cat] || 0) + 1;
    return acc;
  }, {});

  // ── Helpers ────────────────────────────────────────────
  function defaultForm() {
    return {
      title: '',
      description: '',
      category: '',
      impact: 'low',
      author: '',
      event_date: new Date().toISOString().slice(0, 10),
    };
  }

  function getImpactInfo(impact) {
    return IMPACT_LEVELS.find(l => l.value === impact) || IMPACT_LEVELS[0];
  }

  function getCategoryColor(category) {
    return CATEGORY_COLORS[category] || '#64748B';
  }

  function formatDate(dateStr) {
    if (!dateStr) return '—';
    const d = new Date(dateStr);
    return d.toLocaleDateString('fr-FR', { day: '2-digit', month: 'long', year: 'numeric' });
  }

  function formatDateShort(dateStr) {
    if (!dateStr) return '—';
    const d = new Date(dateStr);
    return d.toLocaleDateString('fr-FR', { day: '2-digit', month: 'short' });
  }

  // ── API ────────────────────────────────────────────────
  async function fetchEntries() {
    loading = true;
    try {
      entries = await api.get('/api/changelog');
    } catch (e) {
      toastError('Erreur lors du chargement du changelog');
    } finally {
      loading = false;
    }
  }

  async function fetchCategories() {
    try {
      const raw = await api.get('/api/changelog/categories');
      categories = raw.map(c => c.name);
    } catch (_) {}
  }

  async function saveEntry() {
    if (!form.title.trim()) return;
    try {
      if (editingEntry) {
        const updated = await api.put(`/api/changelog/${editingEntry.id}`, form);
        entries = entries.map(e => e.id === updated.id ? updated : e);
        success('Entrée modifiée');
      } else {
        const created = await api.post('/api/changelog', form);
        entries = [...entries, created];
        success('Entrée créée');
      }
      closeDialog();
    } catch (e) {
      toastError('Erreur lors de la sauvegarde');
    }
  }

  async function deleteEntry(id) {
    try {
      await api.delete(`/api/changelog/${id}`);
      entries = entries.filter(e => e.id !== id);
      confirmDeleteId = null;
      success('Entrée supprimée');
    } catch (e) {
      toastError('Erreur lors de la suppression');
    }
  }

  // ── Dialog management ──────────────────────────────────
  function openCreateDialog() {
    editingEntry = null;
    form = defaultForm();
    showDialog = true;
  }

  function openEditDialog(entry) {
    editingEntry = entry;
    form = {
      title: entry.title || '',
      description: entry.description || '',
      category: entry.category || '',
      impact: entry.impact || 'low',
      author: entry.author || '',
      event_date: entry.event_date || '',
    };
    showDialog = true;
  }

  function closeDialog() {
    showDialog = false;
    editingEntry = null;
  }

  // ── Search debounce ────────────────────────────────────
  function onSearchInput(e) {
    clearTimeout(searchDebounceTimer);
    searchDebounceTimer = setTimeout(() => {
      searchQuery = e.target.value;
    }, 250);
  }

  // ── Lifecycle ──────────────────────────────────────────
  onMount(() => {
    fetchEntries();
    fetchCategories();
  });

  onDestroy(() => {
    clearTimeout(searchDebounceTimer);
  });
</script>

<div class="changelog-page">
  <!-- ── Stats Bar ──────────────────────────────────────── -->
  <div class="stats-bar">
    <div class="stat-card">
      <div class="stat-value" style="color: var(--accent)">{totalEntries}</div>
      <div class="stat-label">Total</div>
    </div>
    {#each Object.entries(categoryCounts) as [cat, count]}
      <div class="stat-card">
        <div class="stat-value" style="color: {getCategoryColor(cat)}">{count}</div>
        <div class="stat-label">{cat}</div>
      </div>
    {/each}
  </div>

  <!-- ── Action bar ─────────────────────────────────────── -->
  <div class="action-bar">
    <div class="action-left">
      <button class="btn-primary" on:click={openCreateDialog}>+ Nouvelle entrée</button>
    </div>
    <div class="action-right">
      <select class="filter-select" bind:value={filterCategory}>
        <option value="">— Toutes catégories —</option>
        {#each categories as cat}
          <option value={cat}>{cat}</option>
        {/each}
      </select>
      <select class="filter-select" bind:value={filterImpact}>
        <option value="">— Tout impact —</option>
        {#each IMPACT_LEVELS as lvl}
          <option value={lvl.value}>{lvl.label}</option>
        {/each}
      </select>
      <div class="search-box">
        <span class="search-icon">🔍</span>
        <input type="text" placeholder="Rechercher..." on:input={onSearchInput} class="search-input" />
      </div>
    </div>
  </div>

  <!-- ── Timeline ───────────────────────────────────────── -->
  {#if loading}
    <div class="loading-msg">Chargement...</div>
  {:else if filteredEntries.length === 0}
    <div class="empty-msg">Aucune entrée trouvée</div>
  {:else}
    <div class="timeline">
      {#each filteredEntries as entry (entry.id)}
        <div class="timeline-entry">
          <div class="timeline-line">
            <div class="timeline-dot" style="background: {getCategoryColor(entry.category)}; box-shadow: 0 0 8px {getCategoryColor(entry.category)}40"></div>
          </div>
          <div class="timeline-card">
            <div class="timeline-card-header">
              <div class="timeline-badges">
                <span class="category-badge" style="background: {getCategoryColor(entry.category)}20; color: {getCategoryColor(entry.category)}; border: 1px solid {getCategoryColor(entry.category)}40">
                  {entry.category || 'Autre'}
                </span>
                <span class="impact-badge" style="background: {getImpactInfo(entry.impact).color}20; color: {getImpactInfo(entry.impact).color}; border: 1px solid {getImpactInfo(entry.impact).color}40">
                  {getImpactInfo(entry.impact).label}
                </span>
              </div>
              <div class="timeline-actions">
                <button class="btn-icon" on:click={() => openEditDialog(entry)} title="Modifier">✏️</button>
                <button class="btn-icon btn-icon-danger" on:click={() => { confirmDeleteId = entry.id; }} title="Supprimer">🗑️</button>
              </div>
            </div>
            <h3 class="timeline-title">{entry.title}</h3>
            {#if entry.description}
              <p class="timeline-desc">{entry.description}</p>
            {/if}
            <div class="timeline-meta">
              {#if entry.event_date}
                <span class="meta-item">📅 {formatDate(entry.event_date)}</span>
              {/if}
              {#if entry.author}
                <span class="meta-item">👤 {entry.author}</span>
              {/if}
            </div>
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

<!-- ── Delete Confirmation ──────────────────────────────── -->
{#if confirmDeleteId}
  <div class="modal-overlay" on:click={() => confirmDeleteId = null}>
    <div class="modal-box modal-small" on:click|stopPropagation>
      <div class="modal-header">
        <h2>Confirmer la suppression</h2>
        <button class="modal-close" on:click={() => confirmDeleteId = null}>✕</button>
      </div>
      <div class="modal-body">
        <p style="color: var(--text-secondary); font-size: 14px;">
          Êtes-vous sûr de vouloir supprimer cette entrée ? Cette action est irréversible.
        </p>
      </div>
      <div class="modal-footer">
        <button class="btn-ghost" on:click={() => confirmDeleteId = null}>Annuler</button>
        <button class="btn-danger" on:click={() => deleteEntry(confirmDeleteId)}>Supprimer</button>
      </div>
    </div>
  </div>
{/if}

<!-- ── Entry Dialog (Modal) ──────────────────────────────── -->
{#if showDialog}
  <div class="modal-overlay" on:click={closeDialog}>
    <div class="modal-box" on:click|stopPropagation>
      <div class="modal-header">
        <h2>{editingEntry ? 'Modifier l\'entrée' : 'Nouvelle entrée'}</h2>
        <button class="modal-close" on:click={closeDialog}>✕</button>
      </div>
      <div class="modal-body">
        <label class="form-label">
          Titre *
          <input type="text" class="form-input" bind:value={form.title} placeholder="Titre de l'entrée" />
        </label>

        <label class="form-label">
          Description
          <textarea class="form-input form-textarea" bind:value={form.description} rows="4" placeholder="Décrivez les changements..."></textarea>
        </label>

        <div class="form-row">
          <label class="form-label form-half">
            Catégorie
            <select class="form-input" bind:value={form.category}>
              <option value="">— Sélectionner —</option>
              {#each categories as cat}
                <option value={cat}>{cat}</option>
              {/each}
            </select>
          </label>
          <label class="form-label form-half">
            Impact
            <div class="impact-selector">
              {#each IMPACT_LEVELS as lvl}
                <button
                  class="impact-btn"
                  class:impact-active={form.impact === lvl.value}
                  style="--impact-color: {lvl.color}"
                  on:click={() => form.impact = lvl.value}
                >
                  {lvl.label}
                </button>
              {/each}
            </div>
          </label>
        </div>

        <div class="form-row">
          <label class="form-label form-half">
            Auteur
            <input type="text" class="form-input" bind:value={form.author} placeholder="Nom de l'auteur" />
          </label>
          <label class="form-label form-half">
            Date
            <input type="date" class="form-input" bind:value={form.event_date} />
          </label>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn-ghost" on:click={closeDialog}>Annuler</button>
        <button class="btn-primary" on:click={saveEntry} disabled={!form.title.trim()}>
          {editingEntry ? 'Modifier' : 'Créer'}
        </button>
      </div>
    </div>
  </div>
{/if}

<style>
  /* ── Page ──────────────────────────────────────────────── */
  .changelog-page {
    animation: fadeIn 0.35s ease-out;
  }

  /* ── Stats bar ─────────────────────────────────────────── */
  .stats-bar {
    display: flex;
    gap: 12px;
    margin-bottom: 18px;
    flex-wrap: wrap;
  }

  .stat-card {
    background: var(--bg-card);
    backdrop-filter: blur(16px);
    border: 1px solid var(--border-subtle);
    border-radius: 12px;
    padding: 14px 18px;
    text-align: center;
    transition: border-color 0.2s;
    min-width: 90px;
    flex: 1;
  }

  .stat-card:hover {
    border-color: var(--border-hover);
  }

  .stat-value {
    font-size: 28px;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
  }

  .stat-label {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    color: var(--text-muted);
    margin-top: 2px;
  }

  /* ── Action bar ────────────────────────────────────────── */
  .action-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 18px;
    flex-wrap: wrap;
  }

  .action-left, .action-right {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .btn-primary {
    background: var(--accent);
    border: none;
    border-radius: 8px;
    color: #fff;
    font-size: 13px;
    font-weight: 600;
    padding: 7px 16px;
    cursor: pointer;
    transition: all 0.15s;
    font-family: inherit;
    box-shadow: 0 2px 12px rgba(var(--accent-rgb), 0.3);
  }

  .btn-primary:hover {
    filter: brightness(1.15);
    box-shadow: 0 4px 20px rgba(var(--accent-rgb), 0.4);
  }

  .btn-primary:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  .filter-select {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: 8px;
    color: var(--text-primary);
    font-size: 13px;
    padding: 6px 10px;
    font-family: inherit;
    cursor: pointer;
    outline: none;
  }

  .filter-select:focus {
    border-color: var(--accent);
  }

  .search-box {
    position: relative;
    display: flex;
    align-items: center;
  }

  .search-icon {
    position: absolute;
    left: 8px;
    font-size: 13px;
    pointer-events: none;
  }

  .search-input {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: 8px;
    color: var(--text-primary);
    font-size: 13px;
    padding: 6px 10px 6px 28px;
    width: 180px;
    font-family: inherit;
    outline: none;
    transition: border-color 0.15s;
  }

  .search-input:focus {
    border-color: var(--accent);
  }

  /* ── Timeline ───────────────────────────────────────────── */
  .timeline {
    position: relative;
    padding-left: 24px;
  }

  .timeline-entry {
    display: flex;
    gap: 16px;
    margin-bottom: 16px;
    position: relative;
  }

  .timeline-line {
    position: relative;
    width: 16px;
    flex-shrink: 0;
    display: flex;
    justify-content: center;
  }

  .timeline-line::after {
    content: '';
    position: absolute;
    top: 16px;
    bottom: -16px;
    width: 2px;
    background: var(--border-subtle);
    left: 50%;
    transform: translateX(-50%);
  }

  .timeline-entry:last-child .timeline-line::after {
    display: none;
  }

  .timeline-dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    flex-shrink: 0;
    margin-top: 6px;
    position: relative;
    z-index: 1;
  }

  .timeline-card {
    flex: 1;
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: 12px;
    padding: 16px 18px;
    backdrop-filter: blur(16px);
    transition: border-color 0.2s;
  }

  .timeline-card:hover {
    border-color: var(--border-hover);
  }

  .timeline-card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;
  }

  .timeline-badges {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
  }

  .category-badge, .impact-badge {
    font-size: 11px;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 6px;
    white-space: nowrap;
  }

  .timeline-actions {
    display: flex;
    gap: 4px;
    opacity: 0;
    transition: opacity 0.15s;
  }

  .timeline-card:hover .timeline-actions {
    opacity: 1;
  }

  .timeline-title {
    margin: 0 0 6px;
    font-size: 15px;
    font-weight: 600;
    color: var(--text-primary);
  }

  .timeline-desc {
    margin: 0 0 10px;
    font-size: 13px;
    color: var(--text-secondary);
    line-height: 1.5;
    white-space: pre-wrap;
  }

  .timeline-meta {
    display: flex;
    gap: 14px;
    flex-wrap: wrap;
  }

  .meta-item {
    font-size: 12px;
    color: var(--text-muted);
  }

  .btn-icon {
    background: none;
    border: none;
    cursor: pointer;
    font-size: 14px;
    padding: 4px;
    border-radius: 6px;
    transition: background 0.15s;
  }

  .btn-icon:hover {
    background: rgba(255, 255, 255, 0.08);
  }

  .btn-icon-danger:hover {
    background: rgba(239, 68, 68, 0.15);
  }

  /* ── Loading / Empty ────────────────────────────────────── */
  .loading-msg, .empty-msg {
    text-align: center;
    padding: 40px;
    color: var(--text-muted);
    font-size: 14px;
  }

  /* ── Modal ──────────────────────────────────────────────── */
  .modal-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
    backdrop-filter: blur(4px);
  }

  .modal-box {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: 14px;
    width: 520px;
    max-width: 95vw;
    max-height: 90vh;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.4);
  }

  .modal-small {
    width: 400px;
  }

  .modal-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 18px 24px 0;
  }

  .modal-header h2 {
    font-size: 18px;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0;
  }

  .modal-close {
    background: none;
    border: none;
    color: var(--text-muted);
    font-size: 18px;
    cursor: pointer;
    padding: 4px;
    border-radius: 6px;
    transition: background 0.15s;
  }

  .modal-close:hover {
    background: rgba(255, 255, 255, 0.08);
    color: var(--text-primary);
  }

  .modal-body {
    padding: 18px 24px;
    display: flex;
    flex-direction: column;
    gap: 14px;
  }

  .modal-footer {
    padding: 0 24px 18px;
    display: flex;
    justify-content: flex-end;
    gap: 8px;
  }

  .btn-ghost {
    background: transparent;
    border: 1px solid var(--border-subtle);
    border-radius: 8px;
    color: var(--text-secondary);
    font-size: 13px;
    padding: 6px 14px;
    cursor: pointer;
    transition: all 0.15s;
    font-family: inherit;
  }

  .btn-ghost:hover {
    background: var(--bg-hover);
    border-color: var(--border-hover);
    color: var(--text-primary);
  }

  .btn-danger {
    background: #EF4444;
    border: none;
    border-radius: 8px;
    color: #fff;
    font-size: 13px;
    font-weight: 600;
    padding: 7px 16px;
    cursor: pointer;
    transition: all 0.15s;
    font-family: inherit;
  }

  .btn-danger:hover {
    filter: brightness(1.15);
  }

  /* ── Form ───────────────────────────────────────────────── */
  .form-label {
    display: flex;
    flex-direction: column;
    gap: 4px;
    font-size: 12px;
    font-weight: 500;
    color: var(--text-secondary);
  }

  .form-input {
    background: var(--bg-input, rgba(255,255,255,0.05));
    border: 1px solid var(--border-subtle);
    border-radius: 8px;
    color: var(--text-primary);
    font-size: 13px;
    padding: 8px 10px;
    font-family: inherit;
    outline: none;
    transition: border-color 0.15s;
  }

  .form-input:focus {
    border-color: var(--accent);
  }

  .form-textarea {
    resize: vertical;
  }

  .form-row {
    display: flex;
    gap: 12px;
  }

  .form-half {
    flex: 1;
  }

  /* ── Impact selector ────────────────────────────────────── */
  .impact-selector {
    display: flex;
    gap: 4px;
    margin-top: 4px;
  }

  .impact-btn {
    flex: 1;
    padding: 6px 4px;
    border: 1px solid var(--border-subtle);
    border-radius: 6px;
    background: transparent;
    color: var(--text-secondary);
    font-size: 11px;
    font-family: inherit;
    cursor: pointer;
    transition: all 0.15s;
  }

  .impact-btn:hover {
    border-color: var(--impact-color);
    color: var(--impact-color);
  }

  .impact-btn.impact-active {
    background: color-mix(in srgb, var(--impact-color) 15%, transparent);
    border-color: var(--impact-color);
    color: var(--impact-color);
    font-weight: 600;
  }
</style>
