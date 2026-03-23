<script>
  import { onMount, onDestroy } from 'svelte';
  import { api } from '../api/client.js';
  import { success, error as toastError } from '../stores/toast.js';
  import { marked } from 'marked';

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
    'Procédure':     '#029AC0',
  };

  // ── Markdown config ─────────────────────────────────────
  marked.setOptions({
    breaks: true,
    gfm: true,
  });

  /**
   * Parse markdown content with [TOC] support.
   * Returns { html, toc } where toc is an array of { id, text, level }.
   */
  function parseMarkdown(content) {
    if (!content) return { html: '', toc: [] };

    const toc = [];
    const renderer = new marked.Renderer();

    // Capture headings for TOC and add IDs
    renderer.heading = function({ tokens, depth }) {
      const text = this.parser.parseInline(tokens);
      const rawText = tokens.map(t => t.raw || t.text || '').join('');
      const id = rawText.toLowerCase().replace(/[^\w\u00C0-\u024F]+/g, '-').replace(/^-|-$/g, '');
      toc.push({ id, text, level: depth });
      return `<h${depth} id="${id}">${text}</h${depth}>`;
    };

    let html = marked.parse(content, { renderer });

    // Replace [TOC] placeholder with generated table of contents
    if (html.includes('[TOC]') || html.includes('<p>[TOC]</p>')) {
      const tocHtml = generateTocHtml(toc);
      html = html.replace(/<p>\[TOC\]<\/p>/g, tocHtml).replace(/\[TOC\]/g, tocHtml);
    }

    return { html, toc };
  }

  function generateTocHtml(toc) {
    if (toc.length === 0) return '';
    let html = '<nav class="procedure-toc"><div class="toc-title">Sommaire</div><ul>';
    for (const item of toc) {
      const indent = (item.level - 1) * 16;
      html += `<li style="padding-left: ${indent}px"><a href="#${item.id}">${item.text}</a></li>`;
    }
    html += '</ul></nav>';
    return html;
  }

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
  let mdTextarea;

  // Markdown toolbar helpers
  function mdWrap(before, after) {
    if (!mdTextarea) return;
    const start = mdTextarea.selectionStart;
    const end = mdTextarea.selectionEnd;
    const selected = form.content.substring(start, end) || 'texte';
    form.content = form.content.substring(0, start) + before + selected + after + form.content.substring(end);
    setTimeout(() => {
      mdTextarea.focus();
      mdTextarea.selectionStart = start + before.length;
      mdTextarea.selectionEnd = start + before.length + selected.length;
    }, 0);
  }
  function mdPrefix(prefix) {
    if (!mdTextarea) return;
    const start = mdTextarea.selectionStart;
    const lineStart = form.content.lastIndexOf('\n', start - 1) + 1;
    form.content = form.content.substring(0, lineStart) + prefix + form.content.substring(lineStart);
    setTimeout(() => { mdTextarea.focus(); mdTextarea.selectionStart = mdTextarea.selectionEnd = start + prefix.length; }, 0);
  }
  function mdInsert(text) {
    if (!mdTextarea) return;
    const pos = mdTextarea.selectionStart;
    form.content = form.content.substring(0, pos) + text + form.content.substring(pos);
    setTimeout(() => { mdTextarea.focus(); mdTextarea.selectionStart = mdTextarea.selectionEnd = pos + text.length; }, 0);
  }

  // Delete confirmation
  let confirmDeleteId = null;

  // Import
  let fileInputEl;

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

  $: renderedContent = (() => {
    if (!selectedArticle) return '';
    if (selectedArticle.content_format === 'markdown') {
      return parseMarkdown(selectedArticle.content).html;
    }
    return selectedArticle.content || '';
  })();

  // ── Helpers ────────────────────────────────────────────
  function defaultForm() {
    return {
      title: '',
      category: '',
      content: '',
      tags: '',
      pinned: false,
      content_format: 'html',
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
        content_format: article.content_format || 'html',
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
      content_format: article.content_format || 'html',
    };
    showDialog = true;
  }

  function closeDialog() {
    showDialog = false;
    editingArticle = null;
  }

  // ── Import .md file ─────────────────────────────────────
  function triggerImport() {
    fileInputEl?.click();
  }

  async function handleFileImport(e) {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      const content = await file.text();
      const baseName = file.name.replace(/\.md$/i, '');

      // ── 1. Extract reference + title from filename pattern "REF - Titre" ──
      let reference = '';
      let title = baseName;
      const filenameMatch = baseName.match(/^(PROC[-\w]+)\s*[-–—]\s*(.+)$/);
      if (filenameMatch) {
        reference = filenameMatch[1].trim();          // ex: "PROC-SI-GLPI-FORM"
        title = filenameMatch[2].trim();              // ex: "Formulaire de support informatique"
      }

      // ── 2. Fallback: try > **Procédure** : ... in blockquote metadata ──
      if (!filenameMatch) {
        const procMatch = content.match(/\*\*Procédure\*\*\s*:\s*(.+)/);
        if (procMatch) {
          title = procMatch[1].trim();
        }
      }

      // ── 3. Fallback: markdown # heading (outside code blocks) ──
      if (!filenameMatch && title === baseName) {
        const withoutCodeBlocks = content.replace(/```[\s\S]*?```/g, '');
        const h1Match = withoutCodeBlocks.match(/^#\s+(.+)$/m);
        if (h1Match) {
          title = h1Match[1].trim();
        }
      }

      // ── 4. Extract reference from blockquote if not found in filename ──
      if (!reference) {
        const refMatch = content.match(/\*\*Référence\*\*\s*:\s*(PROC[-\w]+)/);
        if (refMatch) {
          reference = refMatch[1].trim();
        }
      }

      // ── Build tags with reference ──
      const tags = ['procédure', 'importé', reference].filter(Boolean).join(', ');

      // Pre-fill the dialog
      editingArticle = null;
      form = {
        title,
        category: 'Procédure',
        content,
        tags,
        pinned: false,
        content_format: 'markdown',
        source_path: file.name,
      };
      showDialog = true;
      success('Fichier importé — vérifiez et validez');
    } catch (err) {
      toastError('Erreur lors de la lecture du fichier');
    }

    // Reset input
    e.target.value = '';
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
            <button class="btn-import" on:click={triggerImport} title="Importer un fichier Markdown (.md)">
              📄 Importer .md
            </button>
            <input
              type="file"
              accept=".md,.markdown,.txt"
              style="display: none"
              bind:this={fileInputEl}
              on:change={handleFileImport}
            />
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
          <div class="articles-list">
            {#each filteredArticles.sort((a, b) => (b.pinned ? 1 : 0) - (a.pinned ? 1 : 0)) as article (article.id)}
              <div class="article-row" on:click={() => viewArticle(article)}>
                <div class="article-row-left">
                  {#if article.pinned}
                    <span class="pin-indicator" title="Épinglé">📌</span>
                  {/if}
                  {#if article.content_format === 'markdown'}
                    <span class="format-badge format-md">MD</span>
                  {/if}
                  <h3 class="article-row-title">{article.title}</h3>
                </div>
                <div class="article-row-meta">
                  {#if article.category}
                    <span class="wiki-category-badge" style="background: {getCategoryColor(article.category)}20; color: {getCategoryColor(article.category)}; border: 1px solid {getCategoryColor(article.category)}40">
                      {article.category}
                    </span>
                  {/if}
                  {#if article.tags}
                    {#each article.tags.split(',').map(t => t.trim()).filter(Boolean).filter(t => t !== 'procédure' && t !== 'importé').slice(0, 2) as tag}
                      <span class="tag-chip">{tag}</span>
                    {/each}
                  {/if}
                  {#if article.updated_at}
                    <span class="article-updated">{formatDate(article.updated_at)}</span>
                  {/if}
                  <div class="article-row-actions">
                    <button class="btn-icon" on:click|stopPropagation={() => togglePin(article)} title={article.pinned ? 'Désépingler' : 'Épingler'}>
                      {article.pinned ? '📌' : '📍'}
                    </button>
                    <button class="btn-icon" on:click|stopPropagation={() => openEditDialog(article)} title="Modifier">✏️</button>
                    <button class="btn-icon btn-icon-danger" on:click|stopPropagation={() => { confirmDeleteId = article.id; }} title="Supprimer">🗑️</button>
                  </div>
                </div>
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
        <div class="article-view-card" class:kreisker-mode={selectedArticle.content_format === 'markdown'}>
          <div class="article-view-top">
            <h1 class="article-view-title">{selectedArticle.title}</h1>
            <div class="article-view-meta">
              {#if selectedArticle.content_format === 'markdown'}
                <span class="format-badge format-md">Markdown</span>
              {/if}
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
          <div class="article-content" class:kreisker-content={selectedArticle.content_format === 'markdown'}>
            {@html renderedContent || '<p style="color: var(--text-muted)">Aucun contenu</p>'}
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

        <div class="form-row">
          <label class="form-label form-half">
            Format
            <select class="form-input" bind:value={form.content_format}>
              <option value="html">HTML</option>
              <option value="markdown">Markdown</option>
            </select>
          </label>
        </div>

        <label class="form-label">
          Contenu ({form.content_format === 'markdown' ? 'Markdown' : 'HTML'})
          {#if form.content_format === 'markdown'}
            <div class="md-toolbar">
              <button type="button" class="md-btn" title="Gras" on:click={() => mdWrap('**','**')}><b>B</b></button>
              <button type="button" class="md-btn" title="Italique" on:click={() => mdWrap('*','*')}><i>I</i></button>
              <button type="button" class="md-btn" title="Barr{'\u00e9'}" on:click={() => mdWrap('~~','~~')}><s>S</s></button>
              <span class="md-sep"></span>
              <button type="button" class="md-btn" title="Titre 1" on:click={() => mdPrefix('# ')}>H1</button>
              <button type="button" class="md-btn" title="Titre 2" on:click={() => mdPrefix('## ')}>H2</button>
              <button type="button" class="md-btn" title="Titre 3" on:click={() => mdPrefix('### ')}>H3</button>
              <span class="md-sep"></span>
              <button type="button" class="md-btn" title="Liste" on:click={() => mdPrefix('- ')}>{'\u2022'}</button>
              <button type="button" class="md-btn" title="Liste num{'\u00e9'}rot{'\u00e9'}e" on:click={() => mdPrefix('1. ')}>1.</button>
              <button type="button" class="md-btn" title="Case {'\u00e0'} cocher" on:click={() => mdPrefix('- [ ] ')}>{'\u2610'}</button>
              <span class="md-sep"></span>
              <button type="button" class="md-btn" title="Code inline" on:click={() => mdWrap('`','`')}>{'\u{1F4BB}'}</button>
              <button type="button" class="md-btn" title="Bloc de code" on:click={() => mdWrap('\n```\n','\n```\n')}>{'\u{1F4C4}'}</button>
              <button type="button" class="md-btn" title="Lien" on:click={() => mdWrap('[','](url)')}>{'\u{1F517}'}</button>
              <button type="button" class="md-btn" title="Citation" on:click={() => mdPrefix('> ')}>{'\u275D'}</button>
              <button type="button" class="md-btn" title="Ligne horizontale" on:click={() => mdInsert('\n---\n')}>—</button>
            </div>
          {/if}
          <textarea class="form-input form-textarea form-content" bind:this={mdTextarea} bind:value={form.content} rows="12" placeholder={form.content_format === 'markdown' ? '\u00C9crivez en Markdown...' : '\u00C9crivez le contenu HTML...'}></textarea>
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

  .btn-import {
    background: rgba(var(--accent-rgb), 0.12);
    border: 1px solid rgba(var(--accent-rgb), 0.3);
    border-radius: 8px;
    color: var(--accent);
    font-size: 13px;
    font-weight: 500;
    padding: 7px 14px;
    cursor: pointer;
    transition: all 0.15s;
    font-family: inherit;
  }

  .btn-import:hover {
    background: rgba(var(--accent-rgb), 0.2);
    border-color: var(--accent);
  }

  .format-badge {
    font-size: 10px;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 6px;
  }

  .format-md {
    background: rgba(2, 154, 192, 0.15);
    color: #029AC0;
    border: 1px solid rgba(2, 154, 192, 0.3);
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

  /* ── Articles list (compact rows) ──────────────────────── */
  .articles-list {
    display: flex;
    flex-direction: column;
    gap: 2px;
    flex: 1;
    overflow-y: auto;
    padding-bottom: 20px;
  }

  .article-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: 8px;
    padding: 10px 16px;
    cursor: pointer;
    transition: border-color 0.15s, background 0.15s;
    position: relative;
  }

  .article-row:hover {
    border-color: var(--border-hover);
    background: rgba(255, 255, 255, 0.03);
  }

  .article-row-left {
    display: flex;
    align-items: center;
    gap: 8px;
    min-width: 0;
    flex: 1;
  }

  .pin-indicator {
    flex-shrink: 0;
    font-size: 12px;
  }

  .article-row-title {
    margin: 0;
    font-size: 13.5px;
    font-weight: 600;
    color: var(--text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    line-height: 1.3;
  }

  .article-row-meta {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-shrink: 0;
  }

  .article-row-actions {
    display: flex;
    gap: 2px;
    flex-shrink: 0;
    opacity: 0;
    transition: opacity 0.15s;
    position: absolute;
    right: 8px;
    top: 50%;
    transform: translateY(-50%);
    background: var(--bg-card);
    padding: 2px 6px;
    border-radius: 6px;
    border: 1px solid var(--border-subtle);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
  }

  .article-row:hover .article-row-actions {
    opacity: 1;
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

  /* ================================================================
     KREISKER PROCEDURE THEME — adapted from Typora theme
     Applied only when article has content_format = 'markdown'
  ================================================================ */

  .kreisker-mode {
    overflow-y: auto;
    max-height: calc(100vh - 180px);
  }

  .kreisker-content {
    --kr-primary: #029AC0;
    --kr-secondary: #C084FC;
    --kr-code-bg: rgba(0, 0, 0, 0.25);
    --kr-code-border: #0099B8;
    --kr-blockquote-bg: rgba(236, 72, 153, 0.08);
    --kr-blockquote-border: #EC4899;
    --kr-blockquote-text: #F9A8D4;
    --kr-h2-bg: rgba(255, 255, 255, 0.04);
    --kr-h3-bg: rgba(255, 255, 255, 0.03);
    --kr-h4-bg: rgba(255, 255, 255, 0.02);

    font-family: "Segoe UI", Inter, sans-serif;
    line-height: 1.7;
    max-width: 1100px;
    margin: 0 auto;
    padding: 10px 20px;
  }

  /* ── Kreisker Headings ── */
  .kreisker-content :global(h1) {
    color: var(--kr-primary);
    border-bottom: 4px solid var(--kr-primary);
    padding-bottom: 12px;
    margin-bottom: 32px;
    margin-top: 32px;
    font-size: 1.6rem;
  }

  .kreisker-content :global(h2) {
    color: var(--kr-secondary);
    background-color: var(--kr-h2-bg);
    padding: 16px 20px;
    margin-top: 40px;
    margin-bottom: 8px;
    border-left: 6px solid var(--kr-secondary);
    border-bottom: 2px solid rgba(255, 255, 255, 0.04);
    border-radius: 6px;
    font-size: 1.45rem;
  }

  .kreisker-content :global(h3) {
    background-color: var(--kr-h3-bg);
    padding: 8px 14px;
    border-left: 5px solid var(--kr-primary);
    border-radius: 6px;
    font-size: 1.2rem;
    margin-top: 12px;
    margin-bottom: 12px;
    color: var(--text-primary);
  }

  .kreisker-content :global(h3::before) {
    content: "▶ ";
    color: var(--kr-primary);
    font-weight: bold;
  }

  .kreisker-content :global(h4) {
    background-color: var(--kr-h4-bg);
    color: var(--kr-secondary);
    padding: 6px 10px 6px 12px;
    border-left: 4px solid #F59E0B;
    border-radius: 4px;
    font-size: 1.05rem;
    margin-top: 16px;
    margin-bottom: 8px;
    font-weight: 600;
  }

  /* ── Kreisker Paragraphs ── */
  .kreisker-content :global(p) {
    margin: 12px 0;
    color: var(--text-secondary);
  }

  /* ── Kreisker Blockquotes / Callouts ── */
  .kreisker-content :global(blockquote) {
    background-color: var(--kr-blockquote-bg);
    border-left: 6px solid var(--kr-blockquote-border);
    color: var(--kr-blockquote-text);
    padding: 14px;
    border-radius: 6px;
    margin: 24px 20px;
  }

  .kreisker-content :global(blockquote strong) {
    color: #F472B6;
  }

  /* ── Kreisker Code ── */
  .kreisker-content :global(pre) {
    background-color: rgba(0, 0, 0, 0.3);
    color: #E2E8F0;
    padding: 16px;
    border-radius: 8px;
    border-left: 4px solid #7C6F64;
    font-size: 0.92em;
    overflow-x: auto;
    margin: 10px 20px 14px;
  }

  .kreisker-content :global(code) {
    color: #FBD38D;
    background-color: rgba(0, 0, 0, 0.25);
    padding: 2px 6px;
    border-radius: 4px;
    font-weight: 500;
    font-family: 'Consolas', 'Fira Code', monospace;
    font-size: 0.9em;
  }

  .kreisker-content :global(pre code) {
    color: #E2E8F0;
    background-color: transparent;
    padding: 0;
    font-weight: normal;
  }

  /* ── Kreisker Lists ── */
  .kreisker-content :global(ul),
  .kreisker-content :global(ol) {
    padding-left: 24px;
    margin: 8px 0 12px;
  }

  .kreisker-content :global(li) {
    margin-bottom: 4px;
    color: var(--text-secondary);
  }

  .kreisker-content :global(ul li::marker) {
    color: var(--kr-primary);
  }

  /* ── Kreisker Tables ── */
  .kreisker-content :global(table) {
    width: 100%;
    border-collapse: collapse;
    margin-top: 16px;
    margin-bottom: 16px;
  }

  .kreisker-content :global(th) {
    background-color: var(--kr-primary);
    color: white;
    padding: 10px;
    text-align: left;
    font-size: 13px;
  }

  .kreisker-content :global(td) {
    border: 1px solid var(--border-subtle);
    padding: 10px;
    font-size: 13px;
    color: var(--text-secondary);
  }

  .kreisker-content :global(tr:nth-child(even) td) {
    background: rgba(236, 72, 153, 0.04);
  }

  /* ── Kreisker Links ── */
  .kreisker-content :global(a) {
    color: var(--kr-secondary);
    text-decoration: none;
  }

  .kreisker-content :global(a:hover) {
    text-decoration: underline;
  }

  /* ── Kreisker HR ── */
  .kreisker-content :global(hr) {
    border: none;
    height: 2px;
    background-color: var(--border-subtle);
    margin: 48px 0;
  }

  /* ── Kreisker Images ── */
  .kreisker-content :global(img) {
    display: block;
    margin: 24px auto;
    max-height: 120px;
    border-radius: 8px;
  }

  /* ── TOC (Table of Contents) ── */
  .kreisker-content :global(.procedure-toc) {
    background-color: rgba(255, 255, 255, 0.03);
    border: 1px solid var(--border-subtle);
    border-radius: 8px;
    padding: 14px 18px;
    margin: 24px 20px 32px;
  }

  .kreisker-content :global(.toc-title) {
    color: var(--kr-secondary);
    font-weight: 600;
    margin-bottom: 10px;
    font-size: 15px;
  }

  .kreisker-content :global(.procedure-toc ul) {
    list-style: none;
    padding-left: 0;
    margin: 0;
  }

  .kreisker-content :global(.procedure-toc li) {
    margin: 2px 0;
    line-height: 1.6;
  }

  .kreisker-content :global(.procedure-toc a) {
    color: var(--kr-primary);
    text-decoration: none;
    font-size: 13px;
  }

  .kreisker-content :global(.procedure-toc a:hover) {
    text-decoration: underline;
  }

  /* ── Kreisker inline HTML support ── */
  .kreisker-content :global(div[style*="text-align: center"]) {
    text-align: center;
  }

  .kreisker-content :global(p[align="center"]) {
    text-align: center;
  }

  /* Override dark inline colors that are invisible on dark theme */
  .kreisker-content :global(h1[style*="color"]),
  .kreisker-content :global(h2[style*="color"]),
  .kreisker-content :global(h3[style*="color"]),
  .kreisker-content :global(h4[style*="color"]) {
    color: var(--kr-primary) !important;
  }

  .kreisker-content :global(h3[style*="color: #00A0C6"]),
  .kreisker-content :global(h3[style*="color:#00A0C6"]) {
    color: var(--kr-secondary) !important;
  }

  /* Override dark text colors in inline styles */
  .kreisker-content :global(p[style*="color: #7a7a7a"]),
  .kreisker-content :global(p[style*="color:#7a7a7a"]) {
    color: var(--text-muted) !important;
  }

  .kreisker-content :global([style*="color: #2c3e50"]),
  .kreisker-content :global([style*="color:#2c3e50"]) {
    color: var(--text-primary) !important;
  }

  /* Hide broken images gracefully */
  .kreisker-content :global(img[src$=".png"]:not([src^="http"]):not([src^="data:"])) {
    display: none;
  }

  /* Blockquote line breaks — ensure <br> works inside blockquotes */
  .kreisker-content :global(blockquote br) {
    display: block;
    content: "";
    margin-top: 2px;
  }

  /* ── Markdown Toolbar ───────────────────────────────── */
  .md-toolbar {
    display: flex; align-items: center; gap: 2px; flex-wrap: wrap;
    padding: 6px 8px; margin-bottom: 4px;
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 8px 8px 0 0;
    border-bottom: none;
  }
  .md-btn {
    background: none; border: none; color: rgba(255,255,255,0.6);
    padding: 4px 8px; border-radius: 5px; cursor: pointer;
    font-size: 0.8rem; font-family: inherit; transition: all 0.15s;
    min-width: 28px; text-align: center;
  }
  .md-btn:hover { background: rgba(255,255,255,0.1); color: #fff; }
  .md-sep {
    width: 1px; height: 18px; background: rgba(255,255,255,0.1);
    margin: 0 4px;
  }
</style>
