<script>
  import { onMount, onDestroy } from 'svelte';
  import { api } from '../api/client.js';
  import { success, error as toastError } from '../stores/toast.js';

  // ── Constants ──────────────────────────────────────────────
  const CATEGORY_COLORS = {
    'Réseau':        '#3B82F6',
    'Serveur':       '#8B5CF6',
    'Sécurité':      '#EF4444',
    'Application':   '#22C55E',
    'Poste':         '#F59E0B',
    'Infrastructure':'#EC4899',
    'Messagerie':    '#F97316',
    'Active Directory': '#06A6C9',
  };

  // ── State ──────────────────────────────────────────────
  let articles = [];
  let categories = [];
  let loading = true;

  // Filters
  let filterCategory = '';
  let searchQuery = '';
  let searchDebounceTimer;

  // View
  let viewMode = 'list'; // 'list' | 'article'
  let selectedArticle = null;
  let articleLoading = false;

  // Dialog
  let showDialog = false;
  let editingArticle = null;
  let form = defaultForm();

  // Delete confirmation
  let confirmDeleteId = null;

  // ── Derived ────────────────────────────────────────────
  $: filteredArticles = articles.filter(a => {
    if (filterCategory && a.category !== filterCategory) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return (a.title || '').toLowerCase().includes(q)
        || (a.category || '').toLowerCase().includes(q)
        || (a.tags || '').toLowerCase().includes(q)
        || (a.content || '').toLowerCase().includes(q);
    }
    return true;
  });

  // ── Helpers ────────────────────────────────────────────
  function defaultForm() {
    return {
      title: '',
      category: '',
      content: '',
      tags: '',
      pinned: false,
    };
  }

  function getCategoryColor(category) {
    const found = categories.find(c => c.name === category);
    if (found && found.color_hex) return found.color_hex;
    return CATEGORY_COLORS[category] || '#64748B';
  }

  function formatDate(dateStr) {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    return d.toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric' });
  }

  // ── API ────────────────────────────────────────────────
  async function fetchArticles() {
    loading = true;
    try {
      articles = await api.get('/api/wiki');
    } catch (e) {
      toastError('Erreur lors du chargement du wiki');
    } finally {
      loading = false;
    }
  }

  async function fetchCategories() {
    try {
      categories = await api.get('/api/wiki/categories');
    } catch (_) {}
  }

  async function viewArticle(article) {
    articleLoading = true;
    viewMode = 'article';
    try {
      selectedArticle = await api.get(`/api/wiki/${article.id}`);
    } catch (e) {
      toastError('Erreur lors du chargement de l\'article');
      selectedArticle = article;
    } finally {
      articleLoading = false;
    }
  }

  function backToList() {
    viewMode = 'list';
    selectedArticle = null;
  }

  async function togglePin(article) {
    try {
      const updated = await api.put(`/api/wiki/${article.id}`, {
        title: article.title,
        category: article.category,
        content: article.content,
        tags: article.tags,
        pinned: !article.pinned,
      });
      articles = articles.map(a => a.id === updated.id ? updated : a);
      if (selectedArticle && selectedArticle.id === updated.id) {
        selectedArticle = updated;
      }
      success(updated.pinned ? 'Article épinglé' : 'Article désépinglé');
    } catch (e) {
      toastError('Erreur');
    }
  }

  async function saveArticle() {
    if (!form.title.trim()) return;
    try {
      if (editingArticle) {
        const updated = await api.put(`/api/wiki/${editingArticle.id}`, form);
        articles = articles.map(a => a.id === updated.id ? updated : a);
        if (selectedArticle && selectedArticle.id === updated.id) {
          selectedArticle = updated;
        }
        success('Article modifié');
      } else {
        const created = await api.post('/api/wiki', form);
        articles = [...articles, created];
        success('Article créé');
      }
      closeDialog();
    } catch (e) {
      toastError('Erreur lors de la sauvegarde');
    }
  }

  async function deleteArticle(id) {
    try {
      await api.delete(`/api/wiki/${id}`);
      articles = articles.filter(a => a.id !== id);
      confirmDeleteId = null;
      if (selectedArticle && selectedArticle.id === id) {
        backToList();
      }
      success('Article supprimé');
    } catch (e) {
      toastError('Erreur lors de la suppression');
    }
  }

  // ── Dialog management ──────────────────────────────────
  function openCreateDialog() {
    editingArticle = null;
    form = defaultForm();
    if (filterCategory) form.category = filterCategory;
    showDialog = true;
  }

  function openEditDialog(article) {
    editingArticle = article;
    form = {
      title: article.title || '',
      category: article.category || '',
      content: article.content || '',
      tags: article.tags || '',
      pinned: article.pinned || false,
    };
    showDialog = true;
  }

  function closeDialog() {
    showDialog = false;
    editingArticle = null;
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
    fetchArticles();
    fetchCategories();
  });

  onDestroy(() => {
    clearTimeout(searchDebounceTimer);
  });
</script>

<div class="wiki-page">
  {#if viewMode === 'list'}
    <div class="wiki-layout">
      <!-- ── Sidebar: Categories ──────────────────────── -->
      <aside class="categories-panel">
        <div class="categories-header">
          <h3>📂 Catégories</h3>
        </div>
        <div class="categories-list">
          <button
            class="cat-item"
            class:cat-active={filterCategory === ''}
            on:click={() => filterCategory = ''}
          >
            <span>Toutes</span>
            <span class="cat-count">{articles.length}</span>
          </button>
          {#each categories as cat}
            <button
              class="cat-item"
              class:cat-active={filterCategory === cat.name}
              on:click={() => filterCategory = cat.name}
            >
              <span class="cat-dot" style="background: {cat.color_hex || getCategoryColor(cat.name)}"></span>
              <span class="cat-name">{cat.name}</span>
              <span class="cat-count">{articles.filter(a => a.category === cat.name).length}</span>
            </button>
          {/each}
        </div>
      </aside>

      <!-- ── Main: Articles ───────────────────────────── -->
      <div class="articles-panel">
        <!-- Action bar -->
        <div class="action-bar">
          <div class="action-left">
            <button class="btn-primary" on:click={openCreateDialog}>+ Nouvel article</button>
          </div>
          <div class="action-right">
            <div class="search-box">
              <span class="search-icon">🔍</span>
              <input type="text" placeholder="Rechercher dans le wiki..." on:input={onSearchInput} class="search-input" />
            </div>
          </div>
        </div>

        <!-- Articles list -->
        {#if loading}
          <div class="loading-msg">Chargement...</div>
        {:else if filteredArticles.length === 0}
          <div class="empty-msg">Aucun article trouvé</div>
        {:else}
          <div class="articles-grid">
            {#each filteredArticles.sort((a, b) => (b.pinned ? 1 : 0) - (a.pinned ? 1 : 0)) as article (article.id)}
              <div class="article-card" on:click={() => viewArticle(article)}>
                <div class="article-card-top">
                  {#if article.pinned}
                    <span class="pin-indicator" title="Épinglé">📌</span>
                  {/if}
                  <h3 class="article-card-title">{article.title}</h3>
                  <div class="article-card-actions">
                    <button class="btn-icon" on:click|stopPropagation={() => togglePin(article)} title={article.pinned ? 'Désépingler' : 'Épingler'}>
                      {article.pinned ? '📌' : '📍'}
                    </button>
                    <button class="btn-icon" on:click|stopPropagation={() => openEditDialog(article)} title="Modifier">✏️</button>
                    <button class="btn-icon btn-icon-danger" on:click|stopPropagation={() => { confirmDeleteId = article.id; }} title="Supprimer">🗑️</button>
                  </div>
                </div>
                <div class="article-card-meta">
                  {#if article.category}
                    <span class="wiki-category-badge" style="background: {getCategoryColor(article.category)}20; color: {getCategoryColor(article.category)}; border: 1px solid {getCategoryColor(article.category)}40">
                      {article.category}
                    </span>
                  {/if}
                  {#if article.tags}
                    {#each article.tags.split(',').map(t => t.trim()).filter(Boolean).slice(0, 3) as tag}
                      <span class="tag-chip">{tag}</span>
                    {/each}
                  {/if}
                </div>
                {#if article.updated_at}
                  <span class="article-updated">Mis à jour le {formatDate(article.updated_at)}</span>
                {/if}
              </div>
            {/each}
          </div>
        {/if}
      </div>
    </div>

  {:else}
    <!-- ── Article View ─────────────────────────────────── -->
    <div class="article-view">
      <div class="article-view-header">
        <button class="btn-back" on:click={backToList}>← Retour</button>
        {#if selectedArticle}
          <div class="article-view-actions">
            <button class="btn-ghost" on:click={() => togglePin(selectedArticle)}>
              {selectedArticle.pinned ? '📌 Désépingler' : '📍 Épingler'}
            </button>
            <button class="btn-ghost" on:click={() => openEditDialog(selectedArticle)}>✏️ Modifier</button>
            <button class="btn-ghost btn-ghost-danger" on:click={() => { confirmDeleteId = selectedArticle.id; }}>🗑️ Supprimer</button>
          </div>
        {/if}
      </div>

      {#if articleLoading}
        <div class="loading-msg">Chargement de l'article...</div>
      {:else if selectedArticle}
        <div class="article-view-card">
          <div class="article-view-top">
            <h1 class="article-view-title">{selectedArticle.title}</h1>
            <div class="article-view-meta">
              {#if selectedArticle.category}
                <span class="wiki-category-badge" style="background: {getCategoryColor(selectedArticle.category)}20; color: {getCategoryColor(selectedArticle.category)}; border: 1px solid {getCategoryColor(selectedArticle.category)}40">
                  {selectedArticle.category}
                </span>
              {/if}
              {#if selectedArticle.tags}
                {#each selectedArticle.tags.split(',').map(t => t.trim()).filter(Boolean) as tag}
                  <span class="tag-chip">{tag}</span>
                {/each}
              {/if}
              {#if selectedArticle.updated_at}
                <span class="article-updated">Mis à jour le {formatDate(selectedArticle.updated_at)}</span>
              {/if}
            </div>
          </div>
          <div class="article-content">
            {@html selectedArticle.content || '<p style="color: var(--text-muted)">Aucun contenu</p>'}
          </div>
        </div>
      {/if}
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
          Êtes-vous sûr de vouloir supprimer cet article ? Cette action est irréversible.
        </p>
      </div>
      <div class="modal-footer">
        <button class="btn-ghost" on:click={() => confirmDeleteId = null}>Annuler</button>
        <button class="btn-danger" on:click={() => deleteArticle(confirmDeleteId)}>Supprimer</button>
      </div>
    </div>
  </div>
{/if}

<!-- ── Article Dialog (Modal) ────────────────────────────── -->
{#if showDialog}
  <div class="modal-overlay" on:click={closeDialog}>
    <div class="modal-box modal-wide" on:click|stopPropagation>
      <div class="modal-header">
        <h2>{editingArticle ? 'Modifier l\'article' : 'Nouvel article'}</h2>
        <button class="modal-close" on:click={closeDialog}>✕</button>
      </div>
      <div class="modal-body">
        <label class="form-label">
          Titre *
          <input type="text" class="form-input" bind:value={form.title} placeholder="Titre de l'article" />
        </label>

        <div class="form-row">
          <label class="form-label form-half">
            Catégorie
            <select class="form-input" bind:value={form.category}>
              <option value="">— Sélectionner —</option>
              {#each categories as cat}
                <option value={cat.name}>{cat.name}</option>
              {/each}
            </select>
          </label>
          <label class="form-label form-half">
            Tags (séparés par des virgules)
            <input type="text" class="form-input" bind:value={form.tags} placeholder="tag1, tag2, ..." />
          </label>
        </div>

        <label class="form-label">
          Contenu (HTML)
          <textarea class="form-input form-textarea form-content" bind:value={form.content} rows="12" placeholder="Écrivez le contenu de l'article..."></textarea>
        </label>

        <label class="form-label checkbox-field">
          <input type="checkbox" bind:checked={form.pinned} />
          <span>Épingler cet article</span>
        </label>
      </div>
      <div class="modal-footer">
        <button class="btn-ghost" on:click={closeDialog}>Annuler</button>
        <button class="btn-primary" on:click={saveArticle} disabled={!form.title.trim()}>
          {editingArticle ? 'Modifier' : 'Créer'}
        </button>
      </div>
    </div>
  </div>
{/if}

<style>
  /* ── Page ──────────────────────────────────────────────── */
  .wiki-page {
    animation: fadeIn 0.35s ease-out;
    height: calc(100vh - 56px);
  }

  .wiki-layout {
    display: flex;
    gap: 16px;
    height: 100%;
  }

  /* ── Categories Panel ───────────────────────────────────── */
  .categories-panel {
    width: 240px;
    flex-shrink: 0;
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: 14px;
    backdrop-filter: blur(16px);
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .categories-header {
    padding: 16px 18px;
    border-bottom: 1px solid var(--border-subtle);
  }

  .categories-header h3 {
    margin: 0;
    font-size: 15px;
    font-weight: 600;
    color: var(--text-primary);
  }

  .categories-list {
    flex: 1;
    overflow-y: auto;
    padding: 8px;
  }

  .cat-item {
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
    padding: 8px 12px;
    background: transparent;
    border: 1px solid transparent;
    border-radius: 8px;
    color: var(--text-secondary);
    font-size: 13px;
    font-family: inherit;
    cursor: pointer;
    transition: all 0.15s;
    text-align: left;
  }

  .cat-item:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
  }

  .cat-item.cat-active {
    background: rgba(var(--accent-rgb), 0.12);
    border-color: rgba(var(--accent-rgb), 0.3);
    color: var(--accent);
  }

  .cat-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .cat-name {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .cat-count {
    font-size: 11px;
    color: var(--text-muted);
    background: rgba(255, 255, 255, 0.06);
    padding: 1px 6px;
    border-radius: 8px;
    flex-shrink: 0;
  }

  /* ── Articles Panel ─────────────────────────────────────── */
  .articles-panel {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
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
    width: 240px;
    font-family: inherit;
    outline: none;
    transition: border-color 0.15s;
  }

  .search-input:focus {
    border-color: var(--accent);
  }

  /* ── Articles grid ──────────────────────────────────────── */
  .articles-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 12px;
    flex: 1;
    overflow-y: auto;
    padding-bottom: 20px;
  }

  .article-card {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: 12px;
    padding: 16px 18px;
    cursor: pointer;
    transition: border-color 0.2s, background 0.2s;
    backdrop-filter: blur(16px);
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .article-card:hover {
    border-color: var(--border-hover);
    background: rgba(255, 255, 255, 0.03);
  }

  .article-card-top {
    display: flex;
    align-items: flex-start;
    gap: 6px;
  }

  .pin-indicator {
    flex-shrink: 0;
    font-size: 14px;
  }

  .article-card-title {
    margin: 0;
    font-size: 15px;
    font-weight: 600;
    color: var(--text-primary);
    flex: 1;
    line-height: 1.35;
  }

  .article-card-actions {
    display: flex;
    gap: 2px;
    flex-shrink: 0;
    opacity: 0;
    transition: opacity 0.15s;
  }

  .article-card:hover .article-card-actions {
    opacity: 1;
  }

  .article-card-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    align-items: center;
  }

  .wiki-category-badge {
    font-size: 11px;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 6px;
    white-space: nowrap;
  }

  .tag-chip {
    font-size: 10px;
    background: rgba(var(--accent-rgb), 0.12);
    color: var(--accent);
    padding: 2px 8px;
    border-radius: 10px;
    border: 1px solid rgba(var(--accent-rgb), 0.25);
  }

  .article-updated {
    font-size: 11px;
    color: var(--text-muted);
  }

  .btn-icon {
    background: none;
    border: none;
    cursor: pointer;
    font-size: 13px;
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

  /* ── Article View ───────────────────────────────────────── */
  .article-view {
    animation: fadeIn 0.25s ease-out;
  }

  .article-view-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 18px;
    flex-wrap: wrap;
    gap: 8px;
  }

  .btn-back {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: 8px;
    color: var(--text-secondary);
    font-size: 13px;
    padding: 6px 14px;
    cursor: pointer;
    transition: all 0.15s;
    font-family: inherit;
  }

  .btn-back:hover {
    background: var(--bg-hover);
    border-color: var(--border-hover);
    color: var(--text-primary);
  }

  .article-view-actions {
    display: flex;
    gap: 6px;
  }

  .article-view-card {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: 14px;
    padding: 28px 32px;
    backdrop-filter: blur(16px);
  }

  .article-view-top {
    margin-bottom: 24px;
    padding-bottom: 16px;
    border-bottom: 1px solid var(--border-subtle);
  }

  .article-view-title {
    margin: 0 0 12px;
    font-size: 24px;
    font-weight: 700;
    color: var(--text-primary);
  }

  .article-view-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    align-items: center;
  }

  .article-content {
    font-size: 14px;
    color: var(--text-secondary);
    line-height: 1.7;
  }

  .article-content :global(h1),
  .article-content :global(h2),
  .article-content :global(h3) {
    color: var(--text-primary);
    margin-top: 24px;
    margin-bottom: 8px;
  }

  .article-content :global(h1) { font-size: 22px; }
  .article-content :global(h2) { font-size: 18px; }
  .article-content :global(h3) { font-size: 16px; }

  .article-content :global(p) {
    margin: 0 0 12px;
  }

  .article-content :global(ul), .article-content :global(ol) {
    padding-left: 24px;
    margin: 0 0 12px;
  }

  .article-content :global(li) {
    margin-bottom: 4px;
  }

  .article-content :global(code) {
    background: rgba(0, 0, 0, 0.3);
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 13px;
    font-family: 'Consolas', monospace;
    color: var(--accent);
  }

  .article-content :global(pre) {
    background: rgba(0, 0, 0, 0.3);
    border: 1px solid var(--border-subtle);
    border-radius: 8px;
    padding: 14px;
    overflow-x: auto;
    margin: 0 0 12px;
  }

  .article-content :global(pre code) {
    background: none;
    padding: 0;
    color: var(--text-primary);
  }

  .article-content :global(table) {
    width: 100%;
    border-collapse: collapse;
    margin: 0 0 12px;
  }

  .article-content :global(th),
  .article-content :global(td) {
    border: 1px solid var(--border-subtle);
    padding: 8px 12px;
    text-align: left;
    font-size: 13px;
  }

  .article-content :global(th) {
    background: rgba(0, 0, 0, 0.2);
    color: var(--text-primary);
    font-weight: 600;
  }

  .article-content :global(a) {
    color: var(--accent);
    text-decoration: none;
  }

  .article-content :global(a:hover) {
    text-decoration: underline;
  }

  .article-content :global(blockquote) {
    border-left: 3px solid var(--accent);
    padding: 8px 16px;
    margin: 0 0 12px;
    background: rgba(var(--accent-rgb), 0.05);
    border-radius: 0 8px 8px 0;
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

  .modal-wide {
    width: 700px;
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

  .btn-ghost-danger:hover {
    border-color: #EF4444;
    color: #EF4444;
    background: rgba(239, 68, 68, 0.1);
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

  .form-content {
    font-family: 'Consolas', monospace;
    font-size: 12px;
    line-height: 1.5;
  }

  .form-row {
    display: flex;
    gap: 12px;
  }

  .form-half {
    flex: 1;
  }

  .checkbox-field {
    flex-direction: row;
    align-items: center;
    gap: 8px;
  }

  .checkbox-field input[type="checkbox"] {
    width: 16px;
    height: 16px;
    accent-color: var(--accent);
  }
</style>
