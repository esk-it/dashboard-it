<script>
  import { onMount } from 'svelte';
  import { api } from '../api/client.js';
  import { success, error as toastError } from '../stores/toast.js';

  // ── State ──────────────────────────────────────────────
  let feeds = [];
  let allArticles = [];
  let selectedFeed = null;
  let loadingFeeds = true;
  let loadingArticles = false;
  let viewMode = 'grid';       // 'grid' | 'list'
  let searchQuery = '';
  let showUnreadOnly = false;

  // Read state stored as { [articleLink]: true } in localStorage
  let readArticles = {};

  // Color palette for feed sources
  const FEED_COLORS = [
    '#3B82F6', '#10B981', '#F59E0B', '#EC4899',
    '#8B5CF6', '#06B6D4', '#EF4444', '#F97316',
  ];

  // ── Helpers ────────────────────────────────────────────
  function loadReadState() {
    try {
      const raw = localStorage.getItem('news_read_articles');
      if (raw) readArticles = JSON.parse(raw);
    } catch { readArticles = {}; }
  }

  function saveReadState() {
    try {
      localStorage.setItem('news_read_articles', JSON.stringify(readArticles));
    } catch {}
  }

  function isRead(link) {
    return !!readArticles[link];
  }

  function toggleRead(link, ev) {
    if (ev) { ev.stopPropagation(); ev.preventDefault(); }
    if (readArticles[link]) {
      delete readArticles[link];
    } else {
      readArticles[link] = true;
    }
    readArticles = readArticles; // trigger reactivity
    saveReadState();
  }

  function markRead(link) {
    if (!readArticles[link]) {
      readArticles[link] = true;
      readArticles = readArticles;
      saveReadState();
    }
  }

  function getFeedColor(feedName) {
    if (!feedName) return FEED_COLORS[0];
    let hash = 0;
    for (let i = 0; i < feedName.length; i++) {
      hash = feedName.charCodeAt(i) + ((hash << 5) - hash);
    }
    return FEED_COLORS[Math.abs(hash) % FEED_COLORS.length];
  }

  function formatDate(dateStr) {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr;
    return d.toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
  }

  function formatDayHeader(dateStr) {
    if (!dateStr) return 'Date inconnue';
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return 'Date inconnue';
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    if (d.toDateString() === today.toDateString()) return "Aujourd'hui";
    if (d.toDateString() === yesterday.toDateString()) return 'Hier';
    return d.toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
  }

  function truncate(text, maxLen = 180) {
    if (!text) return '';
    // Strip HTML tags
    const clean = text.replace(/<[^>]*>/g, '').replace(/&nbsp;/g, ' ').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&#\d+;/g, '');
    return clean.length > maxLen ? clean.slice(0, maxLen) + '...' : clean;
  }

  function getDayKey(dateStr) {
    if (!dateStr) return '9999-99-99';
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return '9999-99-99';
    return d.toISOString().slice(0, 10);
  }

  // ── Computed / Reactive ────────────────────────────────
  $: filteredArticles = allArticles.filter(a => {
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      if (!(a.title || '').toLowerCase().includes(q)) return false;
    }
    if (showUnreadOnly && isRead(a.link)) return false;
    return true;
  });

  $: groupedByDay = (() => {
    const groups = {};
    for (const a of filteredArticles) {
      const key = getDayKey(a.published);
      if (!groups[key]) groups[key] = { date: a.published, articles: [] };
      groups[key].articles.push(a);
    }
    return Object.entries(groups)
      .sort(([a], [b]) => a < b ? 1 : a > b ? -1 : 0)
      .map(([, v]) => v);
  })();

  $: totalCount = allArticles.length;
  $: unreadCount = allArticles.filter(a => !isRead(a.link)).length;

  $: feedUnreadCounts = (() => {
    // Only meaningful when we have all articles loaded for the current feed
    const counts = {};
    for (const feed of feeds) {
      counts[feed.url] = 0;
    }
    // We track unread for current feed
    if (selectedFeed) {
      counts[selectedFeed.url] = unreadCount;
    }
    return counts;
  })();

  // ── API ────────────────────────────────────────────────
  async function fetchFeeds() {
    loadingFeeds = true;
    try {
      feeds = await api.get('/api/news/feeds');
      if (feeds.length > 0) {
        selectFeed(feeds[0]);
      }
    } catch (e) {
      toastError('Erreur lors du chargement des flux');
    } finally {
      loadingFeeds = false;
    }
  }

  async function selectFeed(feed) {
    selectedFeed = feed;
    loadingArticles = true;
    allArticles = [];
    try {
      const raw = await api.get(`/api/news/articles?feed_url=${encodeURIComponent(feed.url)}`);
      // Attach feed metadata to each article
      allArticles = raw.map(a => ({ ...a, feedName: feed.name, feedUrl: feed.url }));
    } catch (e) {
      toastError('Erreur lors du chargement des articles');
    } finally {
      loadingArticles = false;
    }
  }

  function openArticle(article) {
    if (article.link) {
      markRead(article.link);
      window.open(article.link, '_blank', 'noopener');
    }
  }

  // ── Lifecycle ──────────────────────────────────────────
  onMount(() => {
    loadReadState();
    fetchFeeds();
  });
</script>

<div class="news-page">
  <div class="news-layout">
    <!-- ── Sidebar: Feeds ─────────────────────────────── -->
    <aside class="feeds-panel">
      <div class="feeds-header">
        <h3>Flux RSS</h3>
        <span class="feeds-header-icon">&#x1F4E1;</span>
      </div>

      {#if loadingFeeds}
        <div class="loading-msg-small">
          <div class="mini-spinner"></div>
          Chargement...
        </div>
      {:else if feeds.length === 0}
        <div class="loading-msg-small">Aucun flux configure</div>
      {:else}
        <div class="feeds-list">
          {#each feeds as feed}
            <button
              class="feed-item"
              class:feed-active={selectedFeed && selectedFeed.url === feed.url}
              on:click={() => selectFeed(feed)}
            >
              <span class="feed-color-dot" style="background: {getFeedColor(feed.name)}"></span>
              <span class="feed-name">{feed.name || feed.url}</span>
              {#if selectedFeed && selectedFeed.url === feed.url && unreadCount > 0}
                <span class="feed-unread-badge">{unreadCount}</span>
              {/if}
            </button>
          {/each}
        </div>
      {/if}
    </aside>

    <!-- ── Main: Articles ─────────────────────────────── -->
    <div class="articles-panel">
      {#if !selectedFeed}
        <div class="empty-msg">Selectionnez un flux RSS</div>
      {:else}
        <!-- Header -->
        <div class="articles-header">
          <div class="articles-header-left">
            <h2>{selectedFeed.name || 'Articles'}</h2>
            <span class="article-count">{totalCount} articles &middot; {unreadCount} non lus</span>
          </div>
          <div class="articles-header-right">
            <!-- Search -->
            <div class="search-box">
              <span class="search-icon">&#x1F50D;</span>
              <input
                type="text"
                placeholder="Rechercher..."
                bind:value={searchQuery}
                class="search-input"
              />
              {#if searchQuery}
                <button class="search-clear" on:click={() => searchQuery = ''}>&times;</button>
              {/if}
            </div>

            <!-- Unread filter -->
            <label class="unread-filter">
              <input type="checkbox" bind:checked={showUnreadOnly} />
              <span class="unread-filter-label">Non lus uniquement</span>
            </label>

            <!-- View mode toggle -->
            <div class="view-toggle">
              <button
                class="view-toggle-btn"
                class:active={viewMode === 'grid'}
                on:click={() => viewMode = 'grid'}
                title="Vue grille"
              >
                <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                  <rect x="1" y="1" width="6" height="6" rx="1"/>
                  <rect x="9" y="1" width="6" height="6" rx="1"/>
                  <rect x="1" y="9" width="6" height="6" rx="1"/>
                  <rect x="9" y="9" width="6" height="6" rx="1"/>
                </svg>
                Grille
              </button>
              <button
                class="view-toggle-btn"
                class:active={viewMode === 'list'}
                on:click={() => viewMode = 'list'}
                title="Vue liste"
              >
                <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                  <rect x="1" y="2" width="14" height="2.5" rx="1"/>
                  <rect x="1" y="6.75" width="14" height="2.5" rx="1"/>
                  <rect x="1" y="11.5" width="14" height="2.5" rx="1"/>
                </svg>
                Liste
              </button>
            </div>
          </div>
        </div>

        {#if loadingArticles}
          <div class="loading-spinner">
            <div class="spinner"></div>
            <span>Chargement des articles...</span>
          </div>
        {:else if filteredArticles.length === 0}
          <div class="empty-msg">
            {#if searchQuery || showUnreadOnly}
              Aucun article correspondant aux filtres
            {:else}
              Aucun article disponible
            {/if}
          </div>
        {:else}
          <div class="articles-scroll">
            {#if viewMode === 'grid'}
              <!-- Grid View grouped by day -->
              {#each groupedByDay as group}
                <div class="day-group">
                  <div class="day-header">
                    <span class="day-header-line"></span>
                    <span class="day-header-text">{formatDayHeader(group.date)}</span>
                    <span class="day-header-line"></span>
                  </div>
                  <div class="articles-grid">
                    {#each group.articles as article}
                      {@const feedColor = getFeedColor(article.feedName)}
                      {@const read = isRead(article.link)}
                      <div
                        class="article-card"
                        class:article-read={read}
                        style="border-left: 3px solid {feedColor}"
                        on:click={() => openArticle(article)}
                      >
                        <div class="card-top-row">
                          <span class="source-badge" style="background: {feedColor}20; color: {feedColor}">
                            {(article.feedName || '').toUpperCase()}
                          </span>
                          <button
                            class="read-toggle"
                            class:is-read={read}
                            title={read ? 'Marquer comme non lu' : 'Marquer comme lu'}
                            on:click={(e) => toggleRead(article.link, e)}
                          >
                            {#if read}
                              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                            {:else}
                              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/></svg>
                            {/if}
                          </button>
                        </div>
                        {#if article.published}
                          <span class="article-date">{formatDate(article.published)}</span>
                        {/if}
                        <h3 class="article-title">{article.title || 'Sans titre'}</h3>
                        {#if article.summary}
                          <p class="article-summary">{truncate(article.summary)}</p>
                        {/if}
                        <span class="article-link-icon" title="Ouvrir dans le navigateur">&#x2197;</span>
                      </div>
                    {/each}
                  </div>
                </div>
              {/each}
            {:else}
              <!-- List View -->
              <div class="articles-list-view">
                {#each filteredArticles as article}
                  {@const feedColor = getFeedColor(article.feedName)}
                  {@const read = isRead(article.link)}
                  <div
                    class="article-list-item"
                    class:article-read={read}
                    style="border-left: 3px solid {feedColor}"
                    on:click={() => openArticle(article)}
                  >
                    <div class="list-item-left">
                      <span class="source-badge source-badge-sm" style="background: {feedColor}20; color: {feedColor}">
                        {(article.feedName || '').toUpperCase()}
                      </span>
                      <h3 class="list-item-title">{article.title || 'Sans titre'}</h3>
                      {#if article.summary}
                        <p class="list-item-summary">{truncate(article.summary, 120)}</p>
                      {/if}
                    </div>
                    <div class="list-item-right">
                      {#if article.published}
                        <span class="article-date">{formatDate(article.published)}</span>
                      {/if}
                      <div class="list-item-actions">
                        <button
                          class="read-toggle"
                          class:is-read={read}
                          title={read ? 'Marquer comme non lu' : 'Marquer comme lu'}
                          on:click={(e) => toggleRead(article.link, e)}
                        >
                          {#if read}
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                          {:else}
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/></svg>
                          {/if}
                        </button>
                        <span class="article-link-icon">&#x2197;</span>
                      </div>
                    </div>
                  </div>
                {/each}
              </div>
            {/if}
          </div>
        {/if}
      {/if}
    </div>
  </div>
</div>

<style>
  /* ── Page ──────────────────────────────────────────────── */
  .news-page {
    animation: fadeIn 0.35s ease-out;
    height: calc(100vh - 56px);
  }

  .news-layout {
    display: flex;
    gap: 16px;
    height: 100%;
  }

  /* ── Feeds Panel ────────────────────────────────────────── */
  .feeds-panel {
    width: 260px;
    flex-shrink: 0;
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: 14px;
    backdrop-filter: blur(16px);
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .feeds-header {
    padding: 16px 18px;
    border-bottom: 1px solid var(--border-subtle);
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .feeds-header h3 {
    margin: 0;
    font-size: 15px;
    font-weight: 600;
    color: var(--text-primary);
  }

  .feeds-header-icon {
    font-size: 16px;
  }

  .feeds-list {
    flex: 1;
    overflow-y: auto;
    padding: 8px;
  }

  .feed-item {
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
    padding: 10px 12px;
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

  .feed-item:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
  }

  .feed-item.feed-active {
    background: rgba(var(--accent-rgb), 0.12);
    border-color: rgba(var(--accent-rgb), 0.3);
    color: var(--accent);
  }

  .feed-color-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .feed-name {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .feed-unread-badge {
    font-size: 10px;
    font-weight: 700;
    background: var(--accent);
    color: #fff;
    padding: 1px 6px;
    border-radius: 10px;
    min-width: 18px;
    text-align: center;
    flex-shrink: 0;
  }

  /* ── Articles Panel ─────────────────────────────────────── */
  .articles-panel {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
  }

  .articles-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
    flex-wrap: wrap;
    gap: 12px;
  }

  .articles-header-left {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .articles-header-left h2 {
    margin: 0;
    font-size: 20px;
    font-weight: 600;
    color: var(--text-primary);
  }

  .article-count {
    font-size: 12px;
    color: var(--text-muted);
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    padding: 4px 12px;
    border-radius: 12px;
    white-space: nowrap;
  }

  .articles-header-right {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  /* ── Search ──────────────────────────────────────────────── */
  .search-box {
    position: relative;
    display: flex;
    align-items: center;
  }

  .search-icon {
    position: absolute;
    left: 10px;
    font-size: 13px;
    pointer-events: none;
    color: var(--text-muted);
  }

  .search-input {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: 8px;
    padding: 6px 28px 6px 32px;
    font-size: 13px;
    font-family: inherit;
    color: var(--text-primary);
    width: 200px;
    outline: none;
    transition: border-color 0.2s;
  }

  .search-input::placeholder {
    color: var(--text-muted);
  }

  .search-input:focus {
    border-color: rgba(var(--accent-rgb), 0.5);
  }

  .search-clear {
    position: absolute;
    right: 6px;
    background: none;
    border: none;
    color: var(--text-muted);
    font-size: 16px;
    cursor: pointer;
    padding: 0 4px;
    font-family: inherit;
  }

  .search-clear:hover {
    color: var(--text-primary);
  }

  /* ── Unread Filter ───────────────────────────────────────── */
  .unread-filter {
    display: flex;
    align-items: center;
    gap: 6px;
    cursor: pointer;
    white-space: nowrap;
  }

  .unread-filter input[type="checkbox"] {
    accent-color: var(--accent);
    width: 14px;
    height: 14px;
    cursor: pointer;
  }

  .unread-filter-label {
    font-size: 12px;
    color: var(--text-secondary);
  }

  /* ── View Toggle ─────────────────────────────────────────── */
  .view-toggle {
    display: flex;
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: 8px;
    overflow: hidden;
  }

  .view-toggle-btn {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 5px 10px;
    background: transparent;
    border: none;
    color: var(--text-muted);
    font-size: 11px;
    font-family: inherit;
    cursor: pointer;
    transition: all 0.15s;
  }

  .view-toggle-btn:first-child {
    border-right: 1px solid var(--border-subtle);
  }

  .view-toggle-btn.active {
    background: rgba(var(--accent-rgb), 0.15);
    color: var(--accent);
  }

  .view-toggle-btn:hover:not(.active) {
    background: var(--bg-hover);
    color: var(--text-primary);
  }

  /* ── Day Header ──────────────────────────────────────────── */
  .day-group {
    margin-bottom: 8px;
  }

  .day-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 12px;
    padding: 0 4px;
  }

  .day-header-line {
    flex: 1;
    height: 1px;
    background: var(--border-subtle);
  }

  .day-header-text {
    font-size: 12px;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: capitalize;
    white-space: nowrap;
  }

  /* ── Articles Scroll ─────────────────────────────────────── */
  .articles-scroll {
    flex: 1;
    overflow-y: auto;
    padding-bottom: 20px;
  }

  /* ── Grid Layout ─────────────────────────────────────────── */
  .articles-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
    margin-bottom: 16px;
  }

  /* ── Card (Grid) ─────────────────────────────────────────── */
  .article-card {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: 12px;
    padding: 14px 16px;
    cursor: pointer;
    transition: border-color 0.2s, background 0.2s, opacity 0.2s;
    backdrop-filter: blur(16px);
    display: flex;
    flex-direction: column;
    gap: 6px;
    position: relative;
  }

  .article-card:hover {
    border-color: var(--border-hover);
    background: rgba(255, 255, 255, 0.04);
  }

  .article-card.article-read {
    opacity: 0.55;
  }

  .article-card.article-read:hover {
    opacity: 0.75;
  }

  /* ── Card Top Row ────────────────────────────────────────── */
  .card-top-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  .source-badge {
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.5px;
    padding: 2px 8px;
    border-radius: 4px;
    white-space: nowrap;
  }

  .source-badge-sm {
    font-size: 8px;
    padding: 1px 6px;
  }

  /* ── Read Toggle ─────────────────────────────────────────── */
  .read-toggle {
    background: none;
    border: none;
    padding: 2px;
    cursor: pointer;
    color: var(--text-muted);
    display: flex;
    align-items: center;
    transition: color 0.15s;
    flex-shrink: 0;
  }

  .read-toggle:hover {
    color: var(--accent);
  }

  .read-toggle.is-read {
    color: var(--success);
  }

  /* ── Article Date ────────────────────────────────────────── */
  .article-date {
    font-size: 11px;
    color: var(--text-muted);
    display: block;
  }

  /* ── Article Title ───────────────────────────────────────── */
  .article-title {
    margin: 0;
    font-size: 14px;
    font-weight: 600;
    color: var(--text-primary);
    line-height: 1.35;
  }

  /* ── Article Summary ─────────────────────────────────────── */
  .article-summary {
    font-size: 12px;
    color: var(--text-secondary);
    line-height: 1.5;
    margin: 0;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  /* ── External Link Icon ──────────────────────────────────── */
  .article-link-icon {
    position: absolute;
    bottom: 12px;
    right: 14px;
    font-size: 14px;
    color: var(--text-muted);
    transition: color 0.15s;
  }

  .article-card:hover .article-link-icon,
  .article-list-item:hover .article-link-icon {
    color: var(--accent);
  }

  /* ── List View ───────────────────────────────────────────── */
  .articles-list-view {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .article-list-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: 10px;
    padding: 10px 14px;
    cursor: pointer;
    transition: border-color 0.2s, background 0.2s, opacity 0.2s;
    backdrop-filter: blur(16px);
  }

  .article-list-item:hover {
    border-color: var(--border-hover);
    background: rgba(255, 255, 255, 0.04);
  }

  .article-list-item.article-read {
    opacity: 0.55;
  }

  .article-list-item.article-read:hover {
    opacity: 0.75;
  }

  .list-item-left {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .list-item-title {
    margin: 0;
    font-size: 13px;
    font-weight: 600;
    color: var(--text-primary);
    line-height: 1.3;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .list-item-summary {
    margin: 0;
    font-size: 11px;
    color: var(--text-secondary);
    line-height: 1.4;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .list-item-right {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-shrink: 0;
  }

  .list-item-actions {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  /* ── Loading / Empty ────────────────────────────────────── */
  .loading-msg-small {
    padding: 20px;
    text-align: center;
    color: var(--text-muted);
    font-size: 13px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
  }

  .empty-msg {
    text-align: center;
    padding: 40px;
    color: var(--text-muted);
    font-size: 14px;
  }

  .loading-spinner {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 14px;
    padding: 60px;
    color: var(--text-muted);
    font-size: 13px;
  }

  .spinner {
    width: 36px;
    height: 36px;
    border: 3px solid var(--border-subtle);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  .mini-spinner {
    width: 18px;
    height: 18px;
    border: 2px solid var(--border-subtle);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }
</style>
