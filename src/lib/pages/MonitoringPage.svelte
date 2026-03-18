<script>
  import { onMount } from 'svelte';
  import { api } from '../api/client.js';
  import { success, error as toastError } from '../stores/toast.js';

  // ── State ──────────────────────────────────────────────────
  let stats = { total_hosts: 0, available: 0, unavailable: 0, unknown: 0, active_problems: 0, synced_at: null };
  let hosts = [];
  let problems = [];
  let config = { configured: false, url: '', api_token: '' };
  let loading = true;
  let syncing = false;
  let searchQuery = '';

  // Config dialog
  let showConfigDialog = false;
  let configForm = { url: '', api_token: '' };
  let savingConfig = false;

  // Tabs
  let activeTab = 'hosts';

  // Derived
  $: filteredHosts = hosts.filter(h => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (h.name || '').toLowerCase().includes(q) ||
           (h.host || '').toLowerCase().includes(q) ||
           (h.ip || '').toLowerCase().includes(q) ||
           (h.groups || []).some(g => g.toLowerCase().includes(q));
  });

  $: filteredProblems = problems.filter(p => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (p.host || '').toLowerCase().includes(q) ||
           (p.name || '').toLowerCase().includes(q) ||
           (p.severity || '').toLowerCase().includes(q);
  });

  // ── Load ───────────────────────────────────────────────────
  onMount(() => { loadAll(); });

  async function loadAll() {
    loading = true;
    try {
      const [cfg, st] = await Promise.all([
        api.get('/api/monitoring/config'),
        api.get('/api/monitoring/stats'),
      ]);
      config = cfg;
      stats = st;
      if (cfg.configured) {
        const [h, p] = await Promise.all([
          api.get('/api/monitoring/hosts'),
          api.get('/api/monitoring/problems'),
        ]);
        hosts = h;
        problems = p;
      }
    } catch (e) {
      toastError('Erreur chargement monitoring : ' + e.message);
    }
    loading = false;
  }

  async function triggerSync() {
    syncing = true;
    try {
      const result = await api.post('/api/monitoring/sync');
      success(`Sync terminée — ${result.total_hosts} hôtes, ${result.total_problems} problèmes`);
      await loadAll();
    } catch (e) {
      toastError('Erreur sync : ' + e.message);
    }
    syncing = false;
  }

  // ── Config Dialog ──────────────────────────────────────────
  function openConfig() {
    configForm = {
      url: config.configured ? config.url : '',
      api_token: '',
    };
    showConfigDialog = true;
  }

  async function saveMonitoringConfig() {
    if (!configForm.url || !configForm.api_token) {
      toastError('Remplissez les deux champs');
      return;
    }
    savingConfig = true;
    try {
      await api.put('/api/monitoring/config', configForm);
      success('Configuration sauvegardée');
      showConfigDialog = false;
      await loadAll();
    } catch (e) {
      toastError('Erreur : ' + e.message);
    }
    savingConfig = false;
  }

  async function deleteMonitoringConfig() {
    try {
      await api.delete('/api/monitoring/config');
      success('Configuration supprimée');
      showConfigDialog = false;
      hosts = [];
      problems = [];
      await loadAll();
    } catch (e) {
      toastError('Erreur : ' + e.message);
    }
  }

  function formatDate(iso) {
    if (!iso) return '—';
    try {
      return new Date(iso).toLocaleDateString('fr-FR', {
        day: '2-digit', month: '2-digit', year: 'numeric',
        hour: '2-digit', minute: '2-digit'
      });
    } catch { return iso; }
  }

  function severityClass(sev) {
    const s = (sev || '').toLowerCase();
    if (s === 'catastrophe') return 'disaster';
    if (s === 'élevé') return 'high';
    if (s === 'moyen') return 'average';
    if (s === 'avertissement') return 'warning';
    if (s === 'information') return 'info';
    return 'default';
  }
</script>

<!-- ── Header + Stats ─────────────────────────────────────── -->
<div class="page-header">
  <div class="title-row">
    <h1>📡 Monitoring — Zabbix</h1>
    <div class="header-actions">
      <button class="btn-icon-text" on:click={openConfig} title="Configuration">
        ⚙️ Config
      </button>
      <button class="btn-primary" on:click={triggerSync} disabled={syncing || !config.configured}>
        {syncing ? '⏳ Sync en cours…' : '🔄 Synchroniser'}
      </button>
    </div>
  </div>

  {#if stats.synced_at}
    <p class="sync-info">Dernière sync : {formatDate(stats.synced_at)}</p>
  {/if}

  {#if config.configured}
    <div class="stats-row">
      <div class="stat-card accent">
        <span class="stat-value">{stats.total_hosts}</span>
        <span class="stat-label">Hôtes</span>
      </div>
      <div class="stat-card online">
        <span class="stat-value">{stats.available}</span>
        <span class="stat-label">Disponibles</span>
      </div>
      <div class="stat-card offline">
        <span class="stat-value">{stats.unavailable}</span>
        <span class="stat-label">Indisponibles</span>
      </div>
      <div class="stat-card problems" class:has-alerts={stats.active_problems > 0}>
        <span class="stat-value">{stats.active_problems}</span>
        <span class="stat-label">Problèmes</span>
      </div>
    </div>
  {/if}
</div>

<!-- ── Content ────────────────────────────────────────────── -->
{#if !config.configured}
  <div class="empty-state">
    <div class="empty-card">
      <span class="empty-icon">📡</span>
      <h2>Zabbix non configuré</h2>
      <p>Configurez votre serveur Zabbix pour superviser l'état de votre infrastructure réseau.</p>
      <div class="setup-steps">
        <h3>Pour commencer :</h3>
        <ol>
          <li>Installez Zabbix sur votre serveur</li>
          <li>Créez un API token dans <strong>Administration → API tokens</strong></li>
          <li>Cliquez sur <strong>Configurer</strong> ci-dessous et entrez l'URL + token</li>
        </ol>
      </div>
      <button class="btn-primary" on:click={openConfig}>Configurer</button>
    </div>
  </div>
{:else if loading}
  <div class="loading">Chargement…</div>
{:else}
  <!-- Tabs -->
  <div class="tabs">
    <button class="tab" class:active={activeTab === 'hosts'} on:click={() => activeTab = 'hosts'}>
      Hôtes <span class="badge neutral">{hosts.length}</span>
    </button>
    <button class="tab" class:active={activeTab === 'problems'} on:click={() => activeTab = 'problems'}>
      Problèmes <span class="badge" class:danger={problems.length > 0} class:neutral={problems.length === 0}>{problems.length}</span>
    </button>
  </div>

  <div class="filters-bar">
    <input type="text" placeholder="Rechercher hôte, IP, groupe…"
           class="search-input" bind:value={searchQuery} />
    <span class="result-count">
      {activeTab === 'hosts' ? filteredHosts.length : filteredProblems.length} résultat{(activeTab === 'hosts' ? filteredHosts.length : filteredProblems.length) !== 1 ? 's' : ''}
    </span>
  </div>

  {#if activeTab === 'hosts'}
    <div class="table-wrapper">
      <table>
        <thead>
          <tr>
            <th>Nom</th>
            <th>IP</th>
            <th>Groupes</th>
            <th>Statut</th>
            <th>Description</th>
          </tr>
        </thead>
        <tbody>
          {#each filteredHosts as host}
            <tr>
              <td class="hostname">{host.name || host.host}</td>
              <td class="mono">{host.ip || '—'}</td>
              <td>
                {#each (host.groups || []) as group}
                  <span class="group-tag">{group}</span>
                {/each}
                {#if !(host.groups || []).length}—{/if}
              </td>
              <td>
                <span class="status-badge" class:enabled={host.status === 'enabled'} class:disabled={host.status === 'disabled'}>
                  {host.status === 'enabled' ? 'Actif' : 'Désactivé'}
                </span>
              </td>
              <td class="desc">{host.description || '—'}</td>
            </tr>
          {/each}
          {#if filteredHosts.length === 0}
            <tr><td colspan="5" class="empty-row">Aucun hôte trouvé</td></tr>
          {/if}
        </tbody>
      </table>
    </div>

  {:else if activeTab === 'problems'}
    <div class="table-wrapper">
      <table>
        <thead>
          <tr>
            <th>Sévérité</th>
            <th>Hôte</th>
            <th>Problème</th>
            <th>Depuis</th>
            <th>Acquitté</th>
          </tr>
        </thead>
        <tbody>
          {#each filteredProblems as problem}
            <tr>
              <td>
                <span class="severity-badge {severityClass(problem.severity)}">
                  {problem.severity}
                </span>
              </td>
              <td class="hostname">{problem.host || '—'}</td>
              <td>{problem.name || '—'}</td>
              <td>{formatDate(problem.timestamp)}</td>
              <td>{problem.acknowledged ? '✅' : '—'}</td>
            </tr>
          {/each}
          {#if filteredProblems.length === 0}
            <tr><td colspan="5" class="empty-row">Aucun problème actif 🎉</td></tr>
          {/if}
        </tbody>
      </table>
    </div>
  {/if}
{/if}

<!-- ── Config Dialog ──────────────────────────────────────── -->
{#if showConfigDialog}
<div class="dialog-overlay" on:click|self={() => showConfigDialog = false}>
  <div class="dialog">
    <div class="dialog-header">
      <h2>Configuration Zabbix</h2>
      <button class="btn-close" on:click={() => showConfigDialog = false}>×</button>
    </div>
    <div class="dialog-body">
      <p class="config-help">
        Entrez l'URL de votre serveur Zabbix et un API token.<br>
        <small>Le token se crée dans Zabbix → Administration → API tokens.</small>
      </p>
      <label>
        URL du serveur
        <input type="text" bind:value={configForm.url} placeholder="https://zabbix.example.com" />
      </label>
      <label>
        API Token
        <input type="password" bind:value={configForm.api_token}
               placeholder={config.configured ? 'Laisser vide pour ne pas changer' : 'votre-api-token'} />
      </label>
    </div>
    <div class="dialog-footer">
      {#if config.configured}
        <button class="btn-danger" on:click={deleteMonitoringConfig}>Supprimer config</button>
      {/if}
      <div class="spacer"></div>
      <button class="btn-secondary" on:click={() => showConfigDialog = false}>Annuler</button>
      <button class="btn-primary" on:click={saveMonitoringConfig} disabled={savingConfig}>
        {savingConfig ? 'Enregistrement…' : 'Enregistrer'}
      </button>
    </div>
  </div>
</div>
{/if}

<style>
  /* ── Layout ─────────────────────────────────────────────── */
  .page-header { margin-bottom: 20px; }
  .title-row {
    display: flex; justify-content: space-between; align-items: center;
    margin-bottom: 8px;
  }
  .title-row h1 { font-size: 1.5rem; font-weight: 700; color: #fff; margin: 0; }
  .header-actions { display: flex; gap: 10px; align-items: center; }
  .sync-info { font-size: 0.8rem; color: rgba(255,255,255,0.4); margin: 0 0 12px; }

  .stats-row { display: flex; gap: 12px; flex-wrap: wrap; }
  .stat-card {
    background: var(--bg-card, rgba(255,255,255,0.06));
    border: 1px solid var(--border-subtle, rgba(255,255,255,0.08));
    border-radius: 12px; padding: 14px 20px;
    text-align: center; min-width: 110px;
    backdrop-filter: blur(12px);
  }
  .stat-card.accent { border-color: var(--accent, #6C63FF); }
  .stat-card.online { border-color: #22C55E; }
  .stat-card.offline { border-color: #EF4444; }
  .stat-card.problems { border-color: #F59E0B; }
  .stat-card.has-alerts { background: rgba(245,158,11,0.08); }
  .stat-value { display: block; font-size: 1.5rem; font-weight: 700; color: #fff; }
  .stat-label { font-size: 0.75rem; color: rgba(255,255,255,0.5); text-transform: uppercase; letter-spacing: 0.05em; }

  /* ── Empty state ────────────────────────────────────────── */
  .empty-state {
    display: flex; justify-content: center; align-items: center;
    min-height: 400px;
  }
  .empty-card {
    background: var(--bg-card, rgba(255,255,255,0.06));
    border: 1px solid var(--border-subtle, rgba(255,255,255,0.08));
    border-radius: 16px; padding: 48px; text-align: center;
    max-width: 500px; backdrop-filter: blur(12px);
  }
  .empty-icon { font-size: 3rem; display: block; margin-bottom: 16px; }
  .empty-card h2 { margin: 0 0 8px; color: #fff; font-size: 1.2rem; }
  .empty-card p { color: rgba(255,255,255,0.5); font-size: 0.9rem; margin-bottom: 20px; }

  .setup-steps {
    text-align: left;
    background: rgba(255,255,255,0.04);
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 20px;
  }
  .setup-steps h3 { margin: 0 0 8px; color: rgba(255,255,255,0.7); font-size: 0.85rem; }
  .setup-steps ol { margin: 0; padding-left: 20px; color: rgba(255,255,255,0.5); font-size: 0.82rem; line-height: 1.8; }
  .setup-steps li strong { color: rgba(255,255,255,0.8); }

  /* ── Tabs ────────────────────────────────────────────────── */
  .tabs {
    display: flex; gap: 4px; margin-bottom: 16px;
    border-bottom: 1px solid var(--border-subtle, rgba(255,255,255,0.08));
  }
  .tab {
    background: none; border: none; color: rgba(255,255,255,0.5);
    padding: 10px 20px; cursor: pointer; font-size: 0.9rem;
    border-bottom: 2px solid transparent; transition: all 0.2s;
  }
  .tab:hover { color: rgba(255,255,255,0.8); }
  .tab.active { color: #fff; border-bottom-color: var(--accent, #6C63FF); }

  .badge { border-radius: 10px; padding: 1px 7px; font-size: 0.7rem; margin-left: 4px; font-weight: 600; }
  .badge.danger { background: rgba(239,68,68,0.2); color: #EF4444; }
  .badge.neutral { background: rgba(255,255,255,0.1); color: rgba(255,255,255,0.5); }

  /* ── Filters ────────────────────────────────────────────── */
  .filters-bar { display: flex; gap: 10px; align-items: center; margin-bottom: 12px; }
  .search-input {
    flex: 1; min-width: 200px; padding: 8px 14px;
    background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.1);
    border-radius: 8px; color: #fff; font-size: 0.85rem;
  }
  .search-input::placeholder { color: rgba(255,255,255,0.3); }
  .result-count { font-size: 0.8rem; color: rgba(255,255,255,0.4); white-space: nowrap; }

  /* ── Table ──────────────────────────────────────────────── */
  .table-wrapper {
    background: var(--bg-card, rgba(255,255,255,0.06));
    border: 1px solid var(--border-subtle, rgba(255,255,255,0.08));
    border-radius: 12px; overflow: auto; max-height: 65vh;
    backdrop-filter: blur(12px);
  }
  table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
  thead { position: sticky; top: 0; z-index: 2; }
  th {
    background: rgba(255,255,255,0.04); color: rgba(255,255,255,0.6);
    padding: 10px 12px; text-align: left; font-weight: 600; white-space: nowrap;
    border-bottom: 1px solid rgba(255,255,255,0.08);
  }
  td {
    padding: 8px 12px; border-bottom: 1px solid rgba(255,255,255,0.04);
    color: rgba(255,255,255,0.85); white-space: nowrap;
  }
  tr:hover td { background: rgba(255,255,255,0.03); }
  .hostname { font-weight: 600; color: #fff; }
  .mono { font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; }
  .desc { max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .empty-row { text-align: center; color: rgba(255,255,255,0.3); padding: 32px !important; }
  .loading { text-align: center; color: rgba(255,255,255,0.4); padding: 40px; }

  /* Groups */
  .group-tag {
    display: inline-block;
    background: rgba(108,99,255,0.15); color: var(--accent, #6C63FF);
    border-radius: 6px; padding: 1px 8px; font-size: 0.72rem; font-weight: 600;
    margin-right: 4px;
  }

  /* Status badge */
  .status-badge {
    border-radius: 6px; padding: 2px 8px; font-size: 0.75rem; font-weight: 600;
  }
  .status-badge.enabled { background: rgba(34,197,94,0.15); color: #22C55E; }
  .status-badge.disabled { background: rgba(255,255,255,0.08); color: rgba(255,255,255,0.4); }

  /* Severity badges */
  .severity-badge {
    border-radius: 6px; padding: 2px 10px; font-size: 0.75rem; font-weight: 600;
    text-transform: capitalize;
  }
  .severity-badge.disaster { background: rgba(239,68,68,0.2); color: #EF4444; }
  .severity-badge.high { background: rgba(249,115,22,0.2); color: #F97316; }
  .severity-badge.average { background: rgba(245,158,11,0.2); color: #F59E0B; }
  .severity-badge.warning { background: rgba(234,179,8,0.2); color: #EAB308; }
  .severity-badge.info { background: rgba(59,130,246,0.2); color: #3B82F6; }
  .severity-badge.default { background: rgba(255,255,255,0.08); color: rgba(255,255,255,0.4); }

  /* ── Dialog ─────────────────────────────────────────────── */
  .dialog-overlay {
    position: fixed; inset: 0; background: rgba(0,0,0,0.6);
    display: flex; align-items: center; justify-content: center; z-index: 100;
    backdrop-filter: blur(4px);
  }
  .dialog {
    background: var(--bg-dialog, #1e1e2e);
    border: 1px solid var(--border-subtle, rgba(255,255,255,0.12));
    border-radius: 16px; width: 480px; max-width: 95vw;
    box-shadow: 0 20px 60px rgba(0,0,0,0.5);
  }
  .dialog-header {
    display: flex; justify-content: space-between; align-items: center;
    padding: 18px 24px; border-bottom: 1px solid rgba(255,255,255,0.08);
  }
  .dialog-header h2 { margin: 0; font-size: 1.1rem; color: #fff; }
  .btn-close {
    background: none; border: none; color: rgba(255,255,255,0.5);
    font-size: 1.4rem; cursor: pointer; padding: 0 4px;
  }
  .dialog-body { padding: 20px 24px; }
  .config-help { font-size: 0.85rem; color: rgba(255,255,255,0.5); margin: 0 0 16px; }
  .config-help small { color: rgba(255,255,255,0.35); }
  .dialog-footer {
    display: flex; align-items: center; gap: 10px;
    padding: 14px 24px; border-top: 1px solid rgba(255,255,255,0.08);
  }
  .spacer { flex: 1; }

  label { display: flex; flex-direction: column; gap: 4px; font-size: 0.82rem; color: rgba(255,255,255,0.6); margin-bottom: 12px; }
  input {
    padding: 8px 12px; background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.1); border-radius: 8px;
    color: #fff; font-size: 0.85rem;
  }
  input:focus { outline: none; border-color: var(--accent, #6C63FF); }

  /* ── Buttons ────────────────────────────────────────────── */
  .btn-primary {
    background: var(--accent, #6C63FF); color: #fff; border: none;
    border-radius: 8px; padding: 8px 20px; cursor: pointer; font-size: 0.85rem;
    font-weight: 600; transition: opacity 0.2s;
  }
  .btn-primary:hover { opacity: 0.9; }
  .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
  .btn-secondary {
    background: rgba(255,255,255,0.08); color: rgba(255,255,255,0.8);
    border: 1px solid rgba(255,255,255,0.1); border-radius: 8px;
    padding: 8px 20px; cursor: pointer; font-size: 0.85rem;
  }
  .btn-danger {
    background: #EF4444; color: #fff; border: none;
    border-radius: 8px; padding: 8px 16px; cursor: pointer; font-size: 0.82rem;
    font-weight: 600;
  }
  .btn-icon-text {
    background: rgba(255,255,255,0.08); color: rgba(255,255,255,0.8);
    border: 1px solid rgba(255,255,255,0.1); border-radius: 8px;
    padding: 8px 14px; cursor: pointer; font-size: 0.85rem;
  }
  .btn-icon-text:hover { background: rgba(255,255,255,0.12); }
</style>
