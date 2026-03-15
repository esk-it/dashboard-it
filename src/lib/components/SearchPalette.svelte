<script>
  import { createEventDispatcher, onMount } from 'svelte';
  import { api } from '../api/client.js';
  import { currentPage } from '../stores/navigation.js';

  const dispatch = createEventDispatcher();

  let query = '';
  let results = [];
  let selectedIndex = 0;
  let loading = false;
  let inputEl;
  let debounceTimer;

  onMount(() => {
    if (inputEl) inputEl.focus();
  });

  function close() {
    dispatch('close');
  }

  function handleKeydown(e) {
    if (e.key === 'Escape') {
      close();
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      selectedIndex = Math.min(selectedIndex + 1, flatResults.length - 1);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      selectedIndex = Math.max(selectedIndex - 1, 0);
    } else if (e.key === 'Enter' && flatResults[selectedIndex]) {
      selectResult(flatResults[selectedIndex]);
    }
  }

  function handleInput() {
    clearTimeout(debounceTimer);
    if (!query.trim()) {
      results = [];
      return;
    }
    debounceTimer = setTimeout(async () => {
      loading = true;
      try {
        const data = await api.get(`/api/search?q=${encodeURIComponent(query)}`);
        results = data.results || data || [];
      } catch (e) {
        results = [];
      }
      loading = false;
      selectedIndex = 0;
    }, 300);
  }

  function selectResult(item) {
    if (item.path) {
      currentPage.set(item.path);
    }
    close();
  }

  function handleOverlayClick(e) {
    if (e.target === e.currentTarget) close();
  }

  $: groupedResults = groupBy(results, 'type');
  $: flatResults = results;

  function groupBy(arr, key) {
    const groups = {};
    for (const item of arr) {
      const g = item[key] || 'Autre';
      if (!groups[g]) groups[g] = [];
      groups[g].push(item);
    }
    return groups;
  }

  const typeEmojis = {
    'task': '✅',
    'document': '\u{1F4C4}',
    'supplier': '\u{1F4C7}',
    'page': '\u{1F4C3}',
  };
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<!-- svelte-ignore a11y_click_events_have_key_events -->
<div class="overlay" on:click={handleOverlayClick} on:keydown={handleKeydown}>
  <div class="palette">
    <div class="search-header">
      <span class="search-icon">{'\u{1F50D}'}</span>
      <input
        bind:this={inputEl}
        bind:value={query}
        on:input={handleInput}
        type="text"
        placeholder="Rechercher partout... (taches, documents, prestataires)"
        class="search-input"
      />
      <kbd class="kbd">Esc</kbd>
    </div>

    <div class="results">
      {#if loading}
        <div class="results-empty">Recherche en cours...</div>
      {:else if query && flatResults.length === 0}
        <div class="results-empty">Aucun r&eacute;sultat pour &laquo; {query} &raquo;</div>
      {:else}
        {#each Object.entries(groupedResults) as [type, items]}
          <div class="result-group">
            <div class="group-label">
              <span>{typeEmojis[type] || '\u{1F4C3}'}</span>
              <span>{type}</span>
            </div>
            {#each items as item, i}
              <!-- svelte-ignore a11y_click_events_have_key_events -->
              <!-- svelte-ignore a11y_no_static_element_interactions -->
              <div
                class="result-item"
                class:selected={flatResults.indexOf(item) === selectedIndex}
                on:click={() => selectResult(item)}
              >
                <span class="result-title">{item.title || item.name || ''}</span>
                {#if item.subtitle}
                  <span class="result-sub">{item.subtitle}</span>
                {/if}
              </div>
            {/each}
          </div>
        {/each}
      {/if}

      {#if !query}
        <div class="results-empty">
          Tapez pour rechercher dans les t&acirc;ches, documents et prestataires
        </div>
      {/if}
    </div>
  </div>
</div>

<style>
  .overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.6);
    backdrop-filter: blur(4px);
    z-index: 9000;
    display: flex;
    align-items: flex-start;
    justify-content: center;
    padding-top: 15vh;
  }

  .palette {
    background: var(--bg-card-solid);
    border: 1px solid var(--border-subtle);
    border-radius: 16px;
    width: 560px;
    max-width: 90vw;
    max-height: 60vh;
    overflow: hidden;
    box-shadow: 0 24px 64px rgba(0, 0, 0, 0.5);
    animation: fadeIn 0.15s ease-out;
  }

  .search-header {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 14px 18px;
    border-bottom: 1px solid var(--border-subtle);
  }

  .search-icon {
    font-size: 18px;
    flex-shrink: 0;
  }

  .search-input {
    flex: 1;
    background: none;
    border: none;
    outline: none;
    color: var(--text-primary);
    font-size: 15px;
    font-family: inherit;
  }

  .search-input::placeholder {
    color: var(--text-muted);
  }

  .kbd {
    font-size: 11px;
    padding: 2px 6px;
    border-radius: 4px;
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid var(--border-subtle);
    color: var(--text-muted);
    font-family: inherit;
  }

  .results {
    overflow-y: auto;
    max-height: calc(60vh - 56px);
    padding: 8px;
  }

  .results-empty {
    padding: 24px;
    text-align: center;
    color: var(--text-muted);
    font-size: 13.5px;
  }

  .result-group {
    margin-bottom: 8px;
  }

  .group-label {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 10px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--text-muted);
  }

  .result-item {
    display: flex;
    flex-direction: column;
    gap: 2px;
    padding: 10px 12px;
    border-radius: 10px;
    cursor: pointer;
    transition: background 0.1s ease;
  }

  .result-item:hover,
  .result-item.selected {
    background: var(--bg-hover);
  }

  .result-title {
    font-size: 14px;
    color: var(--text-primary);
  }

  .result-sub {
    font-size: 12px;
    color: var(--text-muted);
  }
</style>
