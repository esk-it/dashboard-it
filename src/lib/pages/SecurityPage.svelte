<script>
  import { onMount } from 'svelte';
  import { api } from '../api/client.js';
  import { success, error as toastError } from '../stores/toast.js';

  // ── State ──────────────────────────────────────────────────
  let stats = { total: 0, online: 0, offline: 0, protection_alerts: 0, synced_at: null };
  let devices = [];
  let config = { configured: false, client_id: '', client_secret: '' };
  let loading = true;
  let syncing = false;
  let searchQuery = '';

  // Config dialog
  let showConfigDialog = false;
  let configForm = { client_id: '', client_secret: '' };
  let savingConfig = false;

  // Tabs
  let activeTab = 'devices';

  // Cross-reference
  let crossRef = null;
  let crossRefLoading = false;
  let crossRefSubTab = 'unprotected';
  let crossRefSearch = '';

  // Derived
  $: filteredDevices = devices.filter(d => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (d.name || '').toLowerCase().includes(q) ||
           (d.os || '').toLowerCase().includes(q) ||
           (d.profileName || '').toLowerCase().includes(q) ||
           (d.ipAddress || '').toLowerCase().includes(q);
  });

  // Profiles: extract unique profiles and count devices per profile
  $: profiles = buildProfiles(devices);

  function buildProfiles(devs) {
    const map = {};
    for (const d of devs) {
      const name = d.profileName || 'Sans profil';
      if (!map[name]) {
        map[name] = { name, devices: [], online: 0, offline: 0, alerts: 0 };
      }
      map[name].devices.push(d);
      if (d.online) map[name].online++;
      else map[name].offline++;
      if (d.malwareProtection && d.malwareProtection.toLowerCase() !== 'ok' && d.malwareProtection !== '') {
        map[name].alerts++;
      }
    }
    return Object.values(map).sort((a, b) => b.devices.length - a.devices.length);
  }

  let selectedProfile = null;

  $: crossRefFiltered = crossRef ? filterCrossRef(crossRef, crossRefSubTab, crossRefSearch) : [];

  function filterCrossRef(cr, tab, search) {
    const list = cr[tab] || [];
    if (!search) return list;
    const q = search.toLowerCase();
    return list.filter(item => {
      const values = Object.values(item).map(v => String(v).toLowerCase());
      return values.some(v => v.includes(q));
    });
  }

  // ── Load ───────────────────────────────────────────────────
  onMount(() => { loadAll(); });

  async function loadAll() {
    loading = true;
    try {
      const [cfg, st, devs] = await Promise.all([
        api.get('/api/security/config'),
        api.get('/api/security/stats'),
        api.get('/api/security/devices'),
      ]);
      config = cfg;
      stats = st;
      devices = devs;
    } catch (e) {
      toastError('Erreur chargement sécurité : ' + e.message);
    }
    loading = false;
  }

  async function triggerSync() {
    syncing = true;
    try {
      const result = await api.post('/api/security/sync');
      success(`Sync terminée — ${result.total} appareils`);
      await loadAll();
    } catch (e) {
      toastError('Erreur sync : ' + e.message);
    }
    syncing = false;
  }

  // ── Config Dialog ──────────────────────────────────────────
  function openConfig() {
    configForm = {
      client_id: config.configured ? config.client_id : '',
      client_secret: '',
    };
    showConfigDialog = true;
  }

  async function saveSecurityConfig() {
    if (!configForm.client_id || !configForm.client_secret) {
      toastError('Remplissez les deux champs');
      return;
    }
    savingConfig = true;
    try {
      await api.put('/api/security/config', configForm);
      success('Configuration sauvegardée');
      showConfigDialog = false;
      await loadAll();
    } catch (e) {
      toastError('Erreur : ' + e.message);
    }
    savingConfig = false;
  }

  async function deleteSecurityConfig() {
    try {
      await api.delete('/api/security/config');
      success('Configuration supprimée');
      showConfigDialog = false;
      await loadAll();
    } catch (e) {
      toastError('Erreur : ' + e.message);
    }
  }

  function switchTab(tab) {
    activeTab = tab;
    if (tab === 'coverage' && !crossRef) loadCrossRef();
  }

  async function loadCrossRef() {
    crossRefLoading = true;
    try {
      crossRef = await api.get('/api/security/crossref');
    } catch (e) {
      toastError('Erreur chargement couverture : ' + e.message);
    }
    crossRefLoading = false;
  }

  function formatDate(iso) {
    if (!iso) return '—';
    try {
      return new Date(iso).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric' });
    } catch { return iso; }
  }
</script>

<!-- ── Header + Stats ─────────────────────────────────────── -->
<div class="page-header">
  <div class="title-row">
    <h1>Sécurité — WithSecure</h1>
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

  <div class="stats-row">
    <div class="stat-card accent">
      <span class="stat-value">{stats.total}</span>
      <span class="stat-label">Total</span>
    </div>
    <div class="stat-card online">
      <span class="stat-value">{stats.online}</span>
      <span class="stat-label">En ligne</span>
    </div>
    <div class="stat-card offline">
      <span class="stat-value">{stats.offline}</span>
      <span class="stat-label">Hors ligne</span>
    </div>
    <div class="stat-card alerts" class:has-alerts={stats.protection_alerts > 0}>
      <span class="stat-value">{stats.protection_alerts}</span>
      <span class="stat-label">Alertes</span>
    </div>
  </div>
</div>

<!-- ── Tabs ────────────────────────────────────────────────── -->
<div class="tabs">
  <button class="tab" class:active={activeTab === 'devices'} on:click={() => switchTab('devices')}>
    Appareils
  </button>
  <button class="tab" class:active={activeTab === 'coverage'} on:click={() => switchTab('coverage')}>
    Couverture
  </button>
  <button class="tab" class:active={activeTab === 'profiles'} on:click={() => switchTab('profiles')}>
    Profils
  </button>
</div>

<!-- ── Content ────────────────────────────────────────────── -->
{#if activeTab === 'devices'}
  {#if !config.configured}
    <div class="empty-state">
      <div class="empty-card">
        <span class="empty-icon">🛡️</span>
        <h2>WithSecure non configuré</h2>
        <p>Configurez vos identifiants API WithSecure Elements pour voir l'état de vos appareils protégés.</p>
        <button class="btn-primary" on:click={openConfig}>Configurer</button>
      </div>
    </div>
  {:else if loading}
    <div class="loading">Chargement…</div>
  {:else}
    <div class="filters-bar">
      <input type="text" placeholder="Rechercher hostname, OS, IP…"
             class="search-input" bind:value={searchQuery} />
      <span class="result-count">{filteredDevices.length} appareil{filteredDevices.length !== 1 ? 's' : ''}</span>
    </div>

    <div class="table-wrapper">
      <table>
        <thead>
          <tr>
            <th>Statut</th>
            <th>Hostname</th>
            <th>OS</th>
            <th>Profil</th>
            <th>Souscription</th>
            <th>Version client</th>
            <th>Malware</th>
            <th>Mises à jour</th>
            <th>IP</th>
            <th>Enregistré</th>
          </tr>
        </thead>
        <tbody>
          {#each filteredDevices as device}
            <tr>
              <td>
                <span class="status-dot" class:online={device.online} class:offline={!device.online}
                      title={device.online ? 'En ligne' : 'Hors ligne'}></span>
              </td>
              <td class="hostname">{device.name || '—'}</td>
              <td>{device.os || '—'}</td>
              <td>{device.profileName || '—'}</td>
              <td class="sub-name">{device.subscriptionName || '—'}</td>
              <td>{device.clientVersion || '—'}</td>
              <td>
                {#if device.malwareProtection}
                  <span class="protection-badge"
                        class:ok={device.malwareProtection.toLowerCase() === 'ok'}
                        class:alert={device.malwareProtection.toLowerCase() !== 'ok'}>
                    {device.malwareProtection}
                  </span>
                {:else}—{/if}
              </td>
              <td>{device.updatesStatus || '—'}</td>
              <td class="mono">{device.ipAddress || '—'}</td>
              <td>{formatDate(device.registeredAt)}</td>
            </tr>
          {/each}
          {#if filteredDevices.length === 0}
            <tr><td colspan="10" class="empty-row">Aucun appareil trouvé</td></tr>
          {/if}
        </tbody>
      </table>
    </div>
  {/if}

{:else if activeTab === 'coverage'}
  <!-- ── Coverage Tab ──────────────────────────────────────── -->
  {#if crossRefLoading}
    <div class="loading">Chargement couverture…</div>
  {:else if crossRef}
    <!-- Coverage Stats -->
    <div class="stats-row coverage-stats">
      <div class="stat-card accent">
        <span class="stat-value">{crossRef.stats.total_parc}</span>
        <span class="stat-label">Postes Parc</span>
      </div>
      <div class="stat-card protected">
        <span class="stat-value">{crossRef.stats.protected}</span>
        <span class="stat-label">Protégés</span>
      </div>
      <div class="stat-card unprotected" class:has-alerts={crossRef.stats.unprotected > 0}>
        <span class="stat-value">{crossRef.stats.unprotected}</span>
        <span class="stat-label">Non protégés</span>
      </div>
      <div class="stat-card unknown-card">
        <span class="stat-value">{crossRef.stats.unknown}</span>
        <span class="stat-label">Inconnus WS</span>
      </div>
      <div class="stat-card coverage-pct">
        <span class="stat-value">{crossRef.stats.coverage_percent}%</span>
        <span class="stat-label">Couverture</span>
      </div>
    </div>

    <!-- Sub-tabs -->
    <div class="sub-tabs">
      <button class="sub-tab" class:active={crossRefSubTab === 'unprotected'}
              on:click={() => crossRefSubTab = 'unprotected'}>
        Non protégés <span class="badge danger">{crossRef.stats.unprotected}</span>
      </button>
      <button class="sub-tab" class:active={crossRefSubTab === 'protected'}
              on:click={() => crossRefSubTab = 'protected'}>
        Protégés <span class="badge ok">{crossRef.stats.protected}</span>
      </button>
      <button class="sub-tab" class:active={crossRefSubTab === 'unknown'}
              on:click={() => crossRefSubTab = 'unknown'}>
        Inconnus <span class="badge warn">{crossRef.stats.unknown}</span>
      </button>
    </div>

    <div class="filters-bar">
      <input type="text" placeholder="Rechercher…"
             class="search-input" bind:value={crossRefSearch} />
      <span class="result-count">{crossRefFiltered.length} résultat{crossRefFiltered.length !== 1 ? 's' : ''}</span>
      <button class="btn-refresh" on:click={loadCrossRef} title="Rafraîchir">🔄</button>
    </div>

    <div class="table-wrapper">
      {#if crossRefSubTab === 'unprotected'}
        <table>
          <thead>
            <tr>
              <th>Hostname</th>
              <th>Type</th>
              <th>OS</th>
              <th>Site</th>
              <th>Bâtiment</th>
              <th>N° Série</th>
            </tr>
          </thead>
          <tbody>
            {#each crossRefFiltered as item}
              <tr>
                <td class="hostname">{item.hostname || '—'}</td>
                <td><span class="type-badge">{item.equip_type}</span></td>
                <td>{item.os || '—'}</td>
                <td>{item.site_name || '—'}</td>
                <td>{item.building_name || '—'}</td>
                <td>{item.serial_number || '—'}</td>
              </tr>
            {/each}
            {#if crossRefFiltered.length === 0}
              <tr><td colspan="6" class="empty-row">Aucun poste non protégé</td></tr>
            {/if}
          </tbody>
        </table>

      {:else if crossRefSubTab === 'protected'}
        <table>
          <thead>
            <tr>
              <th>Hostname</th>
              <th>Type</th>
              <th>OS</th>
              <th>Site</th>
              <th>Statut WS</th>
              <th>Protection</th>
              <th>IP</th>
            </tr>
          </thead>
          <tbody>
            {#each crossRefFiltered as item}
              <tr>
                <td class="hostname">{item.hostname || '—'}</td>
                <td><span class="type-badge">{item.equip_type}</span></td>
                <td>{item.os || '—'}</td>
                <td>{item.site_name || '—'}</td>
                <td>
                  <span class="status-dot" class:online={item.ws_online} class:offline={!item.ws_online}></span>
                  {item.ws_online ? 'En ligne' : 'Hors ligne'}
                </td>
                <td>
                  {#if item.ws_malwareProtection}
                    <span class="protection-badge"
                          class:ok={item.ws_malwareProtection.toLowerCase() === 'ok'}
                          class:alert={item.ws_malwareProtection.toLowerCase() !== 'ok'}>
                      {item.ws_malwareProtection}
                    </span>
                  {:else}—{/if}
                </td>
                <td class="mono">{item.ws_ipAddress || '—'}</td>
              </tr>
            {/each}
            {#if crossRefFiltered.length === 0}
              <tr><td colspan="7" class="empty-row">Aucun poste protégé trouvé</td></tr>
            {/if}
          </tbody>
        </table>

      {:else if crossRefSubTab === 'unknown'}
        <table>
          <thead>
            <tr>
              <th>Nom WithSecure</th>
              <th>OS</th>
              <th>Statut</th>
              <th>IP</th>
              <th>Profil</th>
            </tr>
          </thead>
          <tbody>
            {#each crossRefFiltered as item}
              <tr>
                <td class="hostname">{item.ws_name || '—'}</td>
                <td>{item.ws_os || '—'}</td>
                <td>
                  <span class="status-dot" class:online={item.ws_online} class:offline={!item.ws_online}></span>
                  {item.ws_online ? 'En ligne' : 'Hors ligne'}
                </td>
                <td class="mono">{item.ws_ipAddress || '—'}</td>
                <td>{item.ws_profileName || '—'}</td>
              </tr>
            {/each}
            {#if crossRefFiltered.length === 0}
              <tr><td colspan="5" class="empty-row">Aucun appareil inconnu</td></tr>
            {/if}
          </tbody>
        </table>
      {/if}
    </div>
  {:else}
    <div class="empty-state">
      <div class="empty-card">
        <span class="empty-icon">📊</span>
        <h2>Couverture sécurité</h2>
        <p>Synchronisez le module Parc et WithSecure pour voir la couverture de protection.</p>
      </div>
    </div>
  {/if}

{:else if activeTab === 'profiles'}
  <!-- ── Profiles Tab ──────────────────────────────────────── -->
  {#if devices.length === 0}
    <div class="empty-state">
      <div class="empty-card">
        <span class="empty-icon">🛡️</span>
        <h2>Aucun appareil</h2>
        <p>Synchronisez WithSecure pour voir les profils de protection.</p>
      </div>
    </div>
  {:else}
    <div class="profiles-grid">
      {#each profiles as profile}
        <button
          class="profile-card"
          class:selected={selectedProfile === profile.name}
          on:click={() => selectedProfile = selectedProfile === profile.name ? null : profile.name}
        >
          <div class="profile-header">
            <span class="profile-icon">🛡️</span>
            <h3 class="profile-name">{profile.name}</h3>
          </div>
          <div class="profile-stats">
            <div class="profile-stat">
              <span class="profile-stat-value">{profile.devices.length}</span>
              <span class="profile-stat-label">Appareils</span>
            </div>
            <div class="profile-stat">
              <span class="profile-stat-value online-text">{profile.online}</span>
              <span class="profile-stat-label">En ligne</span>
            </div>
            <div class="profile-stat">
              <span class="profile-stat-value offline-text">{profile.offline}</span>
              <span class="profile-stat-label">Hors ligne</span>
            </div>
            {#if profile.alerts > 0}
              <div class="profile-stat">
                <span class="profile-stat-value alert-text">{profile.alerts}</span>
                <span class="profile-stat-label">Alertes</span>
              </div>
            {/if}
          </div>
        </button>
      {/each}
    </div>

    {#if selectedProfile}
      <h3 class="profile-detail-title">Appareils du profil « {selectedProfile} »</h3>
      <div class="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Statut</th>
              <th>Hostname</th>
              <th>OS</th>
              <th>État profil</th>
              <th>Souscription</th>
              <th>Malware</th>
              <th>Version client</th>
              <th>IP</th>
            </tr>
          </thead>
          <tbody>
            {#each profiles.find(p => p.name === selectedProfile)?.devices || [] as device}
              <tr>
                <td>
                  <span class="status-dot" class:online={device.online} class:offline={!device.online}></span>
                </td>
                <td class="hostname">{device.name || '—'}</td>
                <td>{device.os || '—'}</td>
                <td>
                  {#if device.profileState}
                    <span class="profile-state-badge"
                          class:uptodate={device.profileState === 'upToDate'}
                          class:inprogress={device.profileState.includes('InProgress')}>
                      {device.profileState === 'upToDate' ? '✅ À jour' : device.profileState === 'assignInProgress' ? '⏳ Attribution' : device.profileState === 'updateInProgress' ? '⏳ Mise à jour' : device.profileState}
                    </span>
                  {:else}—{/if}
                </td>
                <td>{device.subscriptionName || '—'}</td>
                <td>
                  {#if device.malwareProtection}
                    <span class="protection-badge"
                          class:ok={device.malwareProtection.toLowerCase() === 'ok'}
                          class:alert={device.malwareProtection.toLowerCase() !== 'ok'}>
                      {device.malwareProtection}
                    </span>
                  {:else}—{/if}
                </td>
                <td>{device.clientVersion || '—'}</td>
                <td class="mono">{device.ipAddress || '—'}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  {/if}
{/if}

<!-- ── Config Dialog ──────────────────────────────────────── -->
{#if showConfigDialog}
<div class="dialog-overlay" on:click|self={() => showConfigDialog = false}>
  <div class="dialog">
    <div class="dialog-header">
      <h2>Configuration WithSecure</h2>
      <button class="btn-close" on:click={() => showConfigDialog = false}>×</button>
    </div>
    <div class="dialog-body">
      <p class="config-help">
        Entrez vos identifiants API WithSecure Elements (OAuth2 Client Credentials).
      </p>
      <label>
        Client ID
        <input type="text" bind:value={configForm.client_id} placeholder="votre-client-id" />
      </label>
      <label>
        Client Secret
        <input type="password" bind:value={configForm.client_secret}
               placeholder={config.configured ? 'Laisser vide pour ne pas changer' : 'votre-client-secret'} />
      </label>
    </div>
    <div class="dialog-footer">
      {#if config.configured}
        <button class="btn-danger" on:click={deleteSecurityConfig}>Supprimer config</button>
      {/if}
      <div class="spacer"></div>
      <button class="btn-secondary" on:click={() => showConfigDialog = false}>Annuler</button>
      <button class="btn-primary" on:click={saveSecurityConfig} disabled={savingConfig}>
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
  .stat-card.has-alerts { border-color: #F59E0B; background: rgba(245,158,11,0.08); }
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
    max-width: 420px; backdrop-filter: blur(12px);
  }
  .empty-icon { font-size: 3rem; display: block; margin-bottom: 16px; }
  .empty-card h2 { margin: 0 0 8px; color: #fff; font-size: 1.2rem; }
  .empty-card p { color: rgba(255,255,255,0.5); font-size: 0.9rem; margin-bottom: 20px; }

  /* ── Filters ────────────────────────────────────────────── */
  .filters-bar {
    display: flex; gap: 10px; align-items: center; margin-bottom: 12px;
  }
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
  .empty-row { text-align: center; color: rgba(255,255,255,0.3); padding: 32px !important; }
  .loading { text-align: center; color: rgba(255,255,255,0.4); padding: 40px; }

  /* Status dot */
  .status-dot {
    display: inline-block; width: 10px; height: 10px; border-radius: 50%;
  }
  .status-dot.online { background: #22C55E; box-shadow: 0 0 6px rgba(34,197,94,0.4); }
  .status-dot.offline { background: #EF4444; }

  /* Protection badge */
  .protection-badge {
    border-radius: 6px; padding: 2px 8px; font-size: 0.75rem; font-weight: 600;
  }
  .protection-badge.ok { background: rgba(34,197,94,0.15); color: #22C55E; }
  .protection-badge.alert { background: rgba(245,158,11,0.15); color: #F59E0B; }

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

  /* ── Tabs ────────────────────────────────────────────────── */
  .tabs {
    display: flex; gap: 4px; margin-bottom: 16px;
    border-bottom: 1px solid var(--border-subtle, rgba(255,255,255,0.08));
    padding-bottom: 0;
  }
  .tab {
    background: none; border: none; color: rgba(255,255,255,0.5);
    padding: 10px 20px; cursor: pointer; font-size: 0.9rem;
    border-bottom: 2px solid transparent; transition: all 0.2s;
  }
  .tab:hover { color: rgba(255,255,255,0.8); }
  .tab.active {
    color: #fff; border-bottom-color: var(--accent, #6C63FF);
  }

  /* ── Sub-tabs ─────────────────────────────────────────────── */
  .sub-tabs {
    display: flex; gap: 6px; margin-bottom: 12px;
  }
  .sub-tab {
    background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08);
    color: rgba(255,255,255,0.6); border-radius: 8px;
    padding: 7px 14px; cursor: pointer; font-size: 0.82rem;
    transition: all 0.2s;
  }
  .sub-tab:hover { background: rgba(255,255,255,0.08); color: rgba(255,255,255,0.9); }
  .sub-tab.active {
    background: rgba(108,99,255,0.15); border-color: var(--accent, #6C63FF);
    color: #fff;
  }
  .badge { border-radius: 10px; padding: 1px 7px; font-size: 0.7rem; margin-left: 4px; font-weight: 600; }
  .badge.danger { background: rgba(239,68,68,0.2); color: #EF4444; }
  .badge.ok { background: rgba(34,197,94,0.2); color: #22C55E; }
  .badge.warn { background: rgba(245,158,11,0.2); color: #F59E0B; }

  /* ── Coverage stats ───────────────────────────────────────── */
  .coverage-stats { margin-bottom: 16px; }
  .stat-card.protected { border-color: #22C55E; }
  .stat-card.unprotected { border-color: #EF4444; }
  .stat-card.unprotected.has-alerts { background: rgba(239,68,68,0.08); }
  .stat-card.unknown-card { border-color: #F59E0B; }
  .stat-card.coverage-pct { border-color: var(--accent, #6C63FF); }

  .type-badge {
    background: rgba(108,99,255,0.2); color: var(--accent, #6C63FF);
    border-radius: 6px; padding: 2px 8px; font-size: 0.75rem; font-weight: 600;
  }
  .btn-refresh {
    background: none; border: none; cursor: pointer; font-size: 1rem;
    padding: 4px 8px; border-radius: 6px; transition: background 0.15s;
  }
  .btn-refresh:hover { background: rgba(255,255,255,0.08); }

  /* ── Profiles tab ─────────────────────────────────────────── */
  .profiles-grid {
    display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 12px; margin-bottom: 20px;
  }
  .profile-card {
    background: var(--bg-card, rgba(255,255,255,0.06));
    border: 1px solid var(--border-subtle, rgba(255,255,255,0.08));
    border-radius: 12px; padding: 16px 20px;
    cursor: pointer; text-align: left; font-family: inherit;
    transition: all 0.2s; backdrop-filter: blur(12px);
    display: flex; flex-direction: column; gap: 12px;
    color: inherit;
  }
  .profile-card:hover {
    border-color: rgba(108,99,255,0.3); background: rgba(108,99,255,0.06);
  }
  .profile-card.selected {
    border-color: var(--accent, #6C63FF); background: rgba(108,99,255,0.1);
    box-shadow: 0 0 12px rgba(108,99,255,0.15);
  }
  .profile-header { display: flex; align-items: center; gap: 10px; }
  .profile-icon { font-size: 1.4rem; }
  .profile-name {
    margin: 0; font-size: 0.95rem; font-weight: 600; color: #fff;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }
  .profile-stats { display: flex; gap: 16px; }
  .profile-stat { display: flex; flex-direction: column; align-items: center; }
  .profile-stat-value { font-size: 1.2rem; font-weight: 700; color: #fff; }
  .profile-stat-label { font-size: 0.7rem; color: rgba(255,255,255,0.4); text-transform: uppercase; }
  .online-text { color: #22C55E; }
  .offline-text { color: #EF4444; }
  .alert-text { color: #F59E0B; }

  .profile-detail-title {
    font-size: 1rem; font-weight: 600; color: #fff; margin: 0 0 12px;
  }

  .profile-state-badge {
    border-radius: 6px; padding: 2px 8px; font-size: 0.75rem; font-weight: 600;
    background: rgba(255,255,255,0.06); color: rgba(255,255,255,0.6);
  }
  .profile-state-badge.uptodate { background: rgba(34,197,94,0.15); color: #22C55E; }
  .profile-state-badge.inprogress { background: rgba(245,158,11,0.15); color: #F59E0B; }
  .sub-name { font-size: 0.78rem; max-width: 160px; overflow: hidden; text-overflow: ellipsis; }
</style>
