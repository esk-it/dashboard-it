<script>
  import { createEventDispatcher } from 'svelte';
  import { currentPage } from '../stores/navigation.js';
  import { api } from '../api/client.js';
  import { success, error as toastError } from '../stores/toast.js';

  const dispatch = createEventDispatcher();

  const ACTIONS = [
    { key: 'task', emoji: '\u2705', label: 'Nouvelle t\u00e2che', path: '/tasks', fields: ['title', 'category'] },
    { key: 'event', emoji: '\u{1F4C5}', label: 'Nouvel \u00e9v\u00e9nement', path: '/planning', fields: ['title'] },
    { key: 'changelog', emoji: '\u{1F4CB}', label: 'Entr\u00e9e changelog', path: '/changelog', fields: ['title'] },
    { key: 'document', emoji: '\u{1F4C4}', label: 'Nouveau document', path: '/documents' },
    { key: 'supplier', emoji: '\u{1F4C7}', label: 'Nouveau prestataire', path: '/suppliers' },
    { key: 'wiki', emoji: '\u{1F4D6}', label: 'Nouvelle proc\u00e9dure', path: '/wiki' },
    { key: 'link', emoji: '\u{1F680}', label: 'Nouveau lien rapide', path: '/launcher' },
  ];

  let selectedAction = null;
  let quickTitle = '';
  let saving = false;

  function close() { dispatch('close'); }

  function selectAction(action) {
    if (action.fields) {
      selectedAction = action;
      quickTitle = '';
      setTimeout(() => {
        const el = document.querySelector('.quick-title-input');
        if (el) el.focus();
      }, 50);
    } else {
      // Navigate to the module
      currentPage.set(action.path);
      close();
    }
  }

  async function quickSave() {
    if (!quickTitle.trim() || !selectedAction) return;
    saving = true;
    try {
      if (selectedAction.key === 'task') {
        await api.post('/api/tasks', {
          title: quickTitle, category: '', priority: 2, due_date: null,
          notes: '', site: '', recurrence: '', checklist: [],
        });
        success('T\u00e2che cr\u00e9\u00e9e');
      } else if (selectedAction.key === 'event') {
        const today = new Date().toISOString().slice(0, 10);
        await api.post('/api/planning/events', {
          title: quickTitle, event_type: 'other', date_start: today,
          date_end: today, all_day: true, time_start: null, time_end: null,
          person: '', notes: '', task_id: null,
        });
        success('\u00c9v\u00e9nement cr\u00e9\u00e9');
      } else if (selectedAction.key === 'changelog') {
        await api.post('/api/changelog', {
          title: quickTitle, description: '', category: '', impact: 'low',
          author: '', event_date: new Date().toISOString().slice(0, 10), tags: '',
        });
        success('Entr\u00e9e changelog cr\u00e9\u00e9e');
      }
      close();
    } catch (e) {
      toastError('Erreur: ' + e.message);
    }
    saving = false;
  }

  function handleKeydown(e) {
    if (e.key === 'Escape') {
      if (selectedAction) { selectedAction = null; }
      else { close(); }
    }
    if (e.key === 'Enter' && selectedAction && quickTitle.trim()) {
      quickSave();
    }
  }
</script>

<!-- svelte-ignore a11y_click_events_have_key_events -->
<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="qc-overlay" on:click|self={close} on:keydown={handleKeydown}>
  <div class="qc-panel">
    <div class="qc-header">
      <span class="qc-icon">{'\u26A1'}</span>
      <span class="qc-title">Cr{'\u00e9'}ation rapide</span>
      <kbd class="qc-kbd">Ctrl+N</kbd>
    </div>

    {#if !selectedAction}
      <div class="qc-actions">
        {#each ACTIONS as action}
          <!-- svelte-ignore a11y_click_events_have_key_events -->
          <!-- svelte-ignore a11y_no_static_element_interactions -->
          <div class="qc-action" on:click={() => selectAction(action)}>
            <span class="qc-action-emoji">{action.emoji}</span>
            <span class="qc-action-label">{action.label}</span>
            {#if action.fields}
              <span class="qc-action-hint">Rapide</span>
            {:else}
              <span class="qc-action-hint">Ouvrir</span>
            {/if}
          </div>
        {/each}
      </div>
    {:else}
      <div class="qc-quick-form">
        <div class="qc-form-header">
          <button class="qc-back" on:click={() => selectedAction = null}>{'\u2190'} Retour</button>
          <span>{selectedAction.emoji} {selectedAction.label}</span>
        </div>
        <input
          type="text"
          class="qc-title-input quick-title-input"
          bind:value={quickTitle}
          placeholder="Titre..."
          on:keydown={handleKeydown}
        />
        <button class="qc-submit" on:click={quickSave} disabled={saving || !quickTitle.trim()}>
          {saving ? 'Cr\u00e9ation...' : 'Cr\u00e9er'}
        </button>
      </div>
    {/if}
  </div>
</div>

<style>
  .qc-overlay {
    position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 9500;
    display: flex; align-items: flex-start; justify-content: center;
    padding-top: 18vh; backdrop-filter: blur(4px);
    animation: fadeIn 0.12s ease;
  }
  @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }

  .qc-panel {
    width: 420px; max-width: 95vw; background: #1a1a2e;
    border: 1px solid rgba(255,255,255,0.12); border-radius: 16px;
    box-shadow: 0 24px 80px rgba(0,0,0,0.6); overflow: hidden;
    animation: slideDown 0.2s ease;
  }
  @keyframes slideDown { from { transform: translateY(-12px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }

  .qc-header {
    display: flex; align-items: center; gap: 8px;
    padding: 14px 18px; border-bottom: 1px solid rgba(255,255,255,0.08);
  }
  .qc-icon { font-size: 18px; }
  .qc-title { flex: 1; font-size: 14px; font-weight: 600; color: #fff; }
  .qc-kbd {
    font-size: 10px; padding: 2px 7px; border-radius: 4px;
    background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.1);
    color: rgba(255,255,255,0.4); font-family: inherit;
  }

  .qc-actions { padding: 6px; }
  .qc-action {
    display: flex; align-items: center; gap: 10px;
    padding: 10px 14px; border-radius: 10px; cursor: pointer;
    transition: background 0.1s;
  }
  .qc-action:hover { background: rgba(108,99,255,0.12); }
  .qc-action-emoji { font-size: 18px; width: 26px; text-align: center; }
  .qc-action-label { flex: 1; font-size: 14px; color: #fff; }
  .qc-action-hint {
    font-size: 10px; color: rgba(255,255,255,0.3);
    padding: 2px 8px; border-radius: 4px;
    background: rgba(255,255,255,0.04);
  }

  .qc-quick-form { padding: 16px 18px; }
  .qc-form-header {
    display: flex; align-items: center; gap: 10px;
    margin-bottom: 12px; font-size: 14px; color: rgba(255,255,255,0.7);
  }
  .qc-back {
    background: none; border: none; color: var(--accent, #6C63FF);
    cursor: pointer; font-size: 14px; padding: 2px 6px; border-radius: 4px;
    font-family: inherit;
  }
  .qc-back:hover { background: rgba(108,99,255,0.1); }

  .qc-title-input {
    width: 100%; background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.1); border-radius: 10px;
    color: #fff; font-size: 15px; padding: 12px 14px;
    font-family: inherit; outline: none; margin-bottom: 12px;
  }
  .qc-title-input:focus { border-color: var(--accent, #6C63FF); }
  .qc-title-input::placeholder { color: rgba(255,255,255,0.25); }

  .qc-submit {
    width: 100%; background: var(--accent, #6C63FF); color: #fff;
    border: none; border-radius: 10px; padding: 10px;
    font-size: 14px; font-weight: 600; cursor: pointer;
    font-family: inherit; transition: all 0.15s;
    box-shadow: 0 4px 12px rgba(var(--accent-rgb, 108,99,255), 0.3);
  }
  .qc-submit:hover { filter: brightness(1.1); }
  .qc-submit:disabled { opacity: 0.4; cursor: not-allowed; }
</style>
