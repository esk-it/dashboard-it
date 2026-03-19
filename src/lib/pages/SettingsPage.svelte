<script>
  import { onMount } from 'svelte';

  const API = 'http://localhost:8010/api/settings';

  let activePanel = 0;

  // Theme settings
  let theme = { theme: 'glass', accent: '#06A6C9', brand_icon: '\u26A1' };

  // General settings
  let general = {
    username: '',
    auto_refresh_minutes: 5,
    max_home_tasks: 10,
    language: 'fr',
    enabled_modules: {},
    card_order: [],
    card_layout: [],
    show_alert_ws: true,
    show_alert_warranty: true,
  };

  // RSS feeds
  let feeds = [];
  let newFeedName = '';
  let newFeedUrl = '';
  let newFeedCategory = 'Autre';

  // RDP status
  let rdpStatus = { docker: {}, guacd: {}, ready: false };

  // DB info
  let dbInfo = null;
  let dbCheckResult = null;
  let dbCheckType = '';
  let dbChecking = false;

  // Backups
  let backups = [];
  let backupRunning = false;
  let backupResult = null;
  let autoBackup = { enabled: true, interval_hours: 6 };

  // Danger zone
  let showResetConfirm = false;
  let resetConfirmText = '';
  let resetting = false;

  // GLPI integration
  let glpiConfig = null;
  let glpiForm = { url: '', app_token: '', user_token: '' };
  let glpiSaving = false;
  let glpiStats = null;

  // Status
  let saved = false;
  let saveTimer = null;

  // Card layout editor
  const allCards = [
    { key: 'tasks', label: 'T\u00e2ches', emoji: '\u2705' },
    { key: 'planning', label: 'Planning', emoji: '\u{1F4C5}' },
    { key: 'documents', label: 'Documents', emoji: '\u{1F4C1}' },
    { key: 'security', label: 'S\u00e9curit\u00e9', emoji: '\u{1F6E1}\uFE0F' },
    { key: 'suppliers', label: 'Prestataires', emoji: '\u{1F4C7}' },
    { key: 'parc', label: 'Parc', emoji: '\u{1F5A5}\uFE0F' },
    { key: 'news', label: 'Actualit\u00e9s', emoji: '\u{1F310}' },
  ];

  const accentPresets = [
    { name: 'Cyan', color: '#06A6C9' },
    { name: 'Bleu', color: '#3B82F6' },
    { name: 'Violet', color: '#8B5CF6' },
    { name: 'Rose', color: '#EC4899' },
    { name: 'Rouge', color: '#EF4444' },
    { name: 'Orange', color: '#F59E0B' },
    { name: 'Vert', color: '#10B981' },
    { name: 'Emeraude', color: '#059669' },
  ];

  const brandIcons = ['\u26A1', '\u{1F680}', '\u{1F4BB}', '\u{1F5A5}\uFE0F', '\u{1F6E1}\uFE0F', '\u{1F50C}', '\u{1F527}', '\u{1F3E2}', '\u{1F310}', '\u2699\uFE0F'];

  const moduleList = [
    { key: 'news', label: 'Actualit\u00e9s', emoji: '\u{1F310}' },
    { key: 'planning', label: 'Planning', emoji: '\u{1F4C5}' },
    { key: 'tasks', label: 'T\u00e2ches', emoji: '\u2705' },
    { key: 'documents', label: 'Documents', emoji: '\u{1F4C1}' },
    { key: 'suppliers', label: 'Prestataires', emoji: '\u{1F4C7}' },
    { key: 'parc', label: 'Parc', emoji: '\u{1F5A5}\uFE0F' },
    { key: 'security', label: 'S\u00e9curit\u00e9', emoji: '\u{1F6E1}\uFE0F' },
    { key: 'wiki', label: 'Proc\u00e9dures', emoji: '\u{1F4D6}' },
    { key: 'changelog', label: 'Changelog', emoji: '\u{1F4CB}' },
    { key: 'bastion', label: 'Bastion', emoji: '\u{1F50C}' },
    { key: 'tools', label: 'Outils', emoji: '\u{1F527}' },
  ];

  const feedCategories = ['S\u00e9curit\u00e9', 'Tech', 'Infra', 'Autre'];

  const panels = [
    { label: 'Apparence', emoji: '\u{1F3A8}' },
    { label: 'G\u00e9n\u00e9ral', emoji: '\u2699\uFE0F' },
    { label: 'Int\u00e9grations', emoji: '\u{1F50C}' },
    { label: 'S\u00e9curit\u00e9 DB', emoji: '\u{1F512}' },
    { label: 'Flux RSS', emoji: '\u{1F4E1}' },
    { label: 'Sauvegarde', emoji: '\u{1F4BE}' },
  ];

  onMount(async () => {
    await Promise.all([loadTheme(), loadGeneral(), loadFeeds(), loadRdpStatus(), loadAutoBackup()]);
  });

  async function loadTheme() {
    try {
      const res = await fetch(`${API}/theme`);
      theme = await res.json();
    } catch(e) {}
  }

  async function loadGeneral() {
    try {
      const res = await fetch(`${API}/general`);
      general = await res.json();
    } catch(e) {}
  }

  async function loadFeeds() {
    try {
      const res = await fetch(`${API}/rss-feeds`);
      feeds = await res.json();
    } catch(e) {}
  }

  async function loadRdpStatus() {
    try {
      const res = await fetch('http://localhost:8010/api/bastion/rdp-check');
      rdpStatus = await res.json();
    } catch(e) {}
  }

  async function loadDbInfo() {
    try {
      const res = await fetch(`${API}/db-info`);
      dbInfo = await res.json();
    } catch(e) {}
  }

  async function loadBackups() {
    try {
      const res = await fetch(`${API}/backups`);
      backups = await res.json();
    } catch(e) {}
  }

  async function loadAutoBackup() {
    try {
      const res = await fetch(`${API}/auto-backup`);
      autoBackup = await res.json();
    } catch(e) {}
  }

  async function saveAutoBackup() {
    await fetch(`${API}/auto-backup`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(autoBackup),
    });
    showSaved();
  }

  async function saveTheme() {
    await fetch(`${API}/theme`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(theme),
    });
    showSaved();
    document.documentElement.style.setProperty('--accent', theme.accent);
  }

  async function saveGeneral() {
    await fetch(`${API}/general`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(general),
    });
    showSaved();
  }

  function showSaved() {
    saved = true;
    if (saveTimer) clearTimeout(saveTimer);
    saveTimer = setTimeout(() => { saved = false; }, 2000);
  }

  function toggleModule(key) {
    general.enabled_modules = {
      ...general.enabled_modules,
      [key]: !general.enabled_modules[key],
    };
    saveGeneral();
  }

  function setAccent(color) { theme.accent = color; saveTheme(); }
  function setBrandIcon(icon) { theme.brand_icon = icon; saveTheme(); }

  // ── RSS Feeds ─────────────────────────────────────────
  async function addFeed() {
    if (!newFeedName.trim() || !newFeedUrl.trim()) return;
    if (!newFeedUrl.startsWith('http')) return;
    try {
      const res = await fetch(`${API}/rss-feeds`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newFeedName, url: newFeedUrl, category: newFeedCategory }),
      });
      feeds = await res.json();
      newFeedName = '';
      newFeedUrl = '';
      showSaved();
    } catch(e) {}
  }

  async function toggleFeed(idx) {
    try {
      const res = await fetch(`${API}/rss-feeds/${idx}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: !feeds[idx].enabled }),
      });
      feeds = await res.json();
      showSaved();
    } catch(e) {}
  }

  async function deleteFeed(idx) {
    try {
      const res = await fetch(`${API}/rss-feeds/${idx}`, { method: 'DELETE' });
      feeds = await res.json();
      showSaved();
    } catch(e) {}
  }

  // ── DB Checks ─────────────────────────────────────────
  async function runDbCheck(type) {
    dbChecking = true;
    dbCheckType = type;
    dbCheckResult = null;
    try {
      const res = await fetch(`${API}/db-${type}`, { method: 'POST' });
      dbCheckResult = await res.json();
    } catch(e) {
      dbCheckResult = { ok: false, result: e.message };
    }
    dbChecking = false;
  }

  // ── Backup ────────────────────────────────────────────
  async function createBackup() {
    backupRunning = true;
    backupResult = null;
    try {
      const res = await fetch(`${API}/backup`, { method: 'POST' });
      backupResult = await res.json();
      await loadBackups();
    } catch(e) {
      backupResult = { error: e.message };
    }
    backupRunning = false;
  }

  // ── Export ────────────────────────────────────────────
  async function exportCsv(type) {
    try {
      const res = await fetch(`${API}/export/${type}`, { method: 'POST' });
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${type}_export.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch(e) {
      console.error('Export failed:', e);
    }
  }

  // ── Reset ─────────────────────────────────────────────
  async function confirmReset() {
    if (resetConfirmText !== 'RESET') return;
    resetting = true;
    try {
      const res = await fetch(`${API}/reset-data`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ confirmation: 'RESET' }),
      });
      const data = await res.json();
      if (data.ok) {
        showResetConfirm = false;
        resetConfirmText = '';
        await Promise.all([loadTheme(), loadGeneral(), loadFeeds()]);
      }
    } catch(e) {}
    resetting = false;
  }

  function copyToClipboard(text) {
    navigator.clipboard.writeText(text);
  }

  // ── GLPI ─────────────────────────────────────────────
  const GLPI_API = 'http://localhost:8010/api/glpi';

  async function loadGlpiConfig() {
    try {
      const res = await fetch(`${GLPI_API}/config`);
      const cfg = await res.json();
      glpiConfig = cfg.configured ? cfg : null;
      if (glpiConfig) {
        const st = await fetch(`${GLPI_API}/stats`);
        glpiStats = await st.json();
      } else {
        glpiStats = null;
      }
    } catch (e) {
      glpiConfig = null;
    }
  }

  async function saveGlpiConfig() {
    if (!glpiForm.url || !glpiForm.app_token || !glpiForm.user_token) return;
    glpiSaving = true;
    try {
      await fetch(`${GLPI_API}/config`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(glpiForm),
      });
      showSaved();
      await loadGlpiConfig();
      glpiForm = { url: '', app_token: '', user_token: '' };
    } catch (e) {
      console.error('GLPI config save failed:', e);
    }
    glpiSaving = false;
  }

  async function deleteGlpiConfig() {
    try {
      await fetch(`${GLPI_API}/config`, { method: 'DELETE' });
      glpiConfig = null;
      glpiStats = null;
      glpiForm = { url: '', app_token: '', user_token: '' };
      showSaved();
    } catch (e) {}
  }

  // Load DB info & backups when switching to those panels
  $: if (activePanel === 2) loadGlpiConfig();
  $: if (activePanel === 3) loadDbInfo();
  $: if (activePanel === 5) loadBackups();

  // Card layout helpers
  function moveCardUp(idx) {
    if (idx <= 0) return;
    const layout = [...(general.card_layout.length ? general.card_layout : allCards.map(c => ({ key: c.key, visible: true })))];
    [layout[idx], layout[idx-1]] = [layout[idx-1], layout[idx]];
    general.card_layout = layout;
    saveGeneral();
  }

  function moveCardDown(idx) {
    const layout = general.card_layout.length ? [...general.card_layout] : allCards.map(c => ({ key: c.key, visible: true }));
    if (idx >= layout.length - 1) return;
    [layout[idx], layout[idx+1]] = [layout[idx+1], layout[idx]];
    general.card_layout = layout;
    saveGeneral();
  }

  function toggleCardVisible(idx) {
    const layout = general.card_layout.length ? [...general.card_layout] : allCards.map(c => ({ key: c.key, visible: true }));
    layout[idx] = { ...layout[idx], visible: !layout[idx].visible };
    general.card_layout = layout;
    saveGeneral();
  }

  $: cardLayout = general.card_layout && general.card_layout.length
    ? general.card_layout
    : allCards.map(c => ({ key: c.key, visible: true }));
</script>

<div class="settings-page">
  <div class="page-header">
    <h1>{'\u2699\uFE0F'} Param{'\u00e8'}tres</h1>
    {#if saved}
      <span class="saved-badge">{'\u2705'} Enregistr{'\u00e9'}</span>
    {/if}
  </div>

  <div class="settings-layout">
    <!-- Panel selector -->
    <div class="panel-nav">
      {#each panels as p, idx}
        <button class="panel-btn" class:active={activePanel === idx} on:click={() => activePanel = idx}>
          <span class="panel-emoji">{p.emoji}</span>
          {p.label}
        </button>
      {/each}
    </div>

    <!-- Panel content -->
    <div class="panel-content">

      <!-- ═══════════════ 0: APPARENCE ═══════════════ -->
      {#if activePanel === 0}
        <div class="panel">
          <h2>{'\u{1F3A8}'} Apparence</h2>

          <div class="setting-section">
            <h3>Couleur d'accent</h3>
            <div class="color-presets">
              {#each accentPresets as preset}
                <button class="color-btn" class:active={theme.accent === preset.color}
                  style="background:{preset.color}" on:click={() => setAccent(preset.color)}
                  title={preset.name}>
                </button>
              {/each}
              <input type="color" bind:value={theme.accent} on:change={saveTheme} class="custom-color" title="Couleur personnalis{'\u00e9'}e" />
            </div>
          </div>

          <div class="setting-section">
            <h3>Ic{'\u00f4'}ne de marque</h3>
            <div class="icon-presets">
              {#each brandIcons as icon}
                <button class="icon-btn" class:active={theme.brand_icon === icon}
                  on:click={() => setBrandIcon(icon)}>
                  {icon}
                </button>
              {/each}
            </div>
          </div>

          <div class="setting-section">
            <h3>Th{'\u00e8'}me</h3>
            <div class="theme-options">
              <button class="theme-card" class:active={theme.theme === 'glass'} on:click={() => { theme.theme = 'glass'; saveTheme(); }}>
                <div class="theme-preview glass-preview"></div>
                <span>Glass Dark</span>
              </button>
            </div>
          </div>
        </div>

      <!-- ═══════════════ 1: GENERAL ═══════════════ -->
      {:else if activePanel === 1}
        <div class="panel">
          <h2>{'\u2699\uFE0F'} G{'\u00e9'}n{'\u00e9'}ral</h2>

          <div class="setting-section">
            <h3>Profil</h3>
            <label class="setting-row">
              <span>Nom d'utilisateur</span>
              <input type="text" bind:value={general.username} on:change={saveGeneral} placeholder="Admin" />
            </label>
          </div>

          <div class="setting-section">
            <h3>Comportement</h3>
            <label class="setting-row">
              <span>Rafra{'\u00ee'}chissement auto (minutes)</span>
              <select bind:value={general.auto_refresh_minutes} on:change={saveGeneral}>
                <option value={0}>D{'\u00e9'}sactiv{'\u00e9'}</option>
                <option value={1}>1 min</option>
                <option value={5}>5 min</option>
                <option value={15}>15 min</option>
                <option value={30}>30 min</option>
              </select>
            </label>
            <label class="setting-row">
              <span>T{'\u00e2'}ches max sur l'accueil</span>
              <input type="number" bind:value={general.max_home_tasks} on:change={saveGeneral} min="1" max="50" />
            </label>
            <label class="setting-row">
              <span>Langue</span>
              <select bind:value={general.language} on:change={saveGeneral}>
                <option value="fr">Fran{'\u00e7'}ais</option>
                <option value="en">English</option>
              </select>
            </label>
          </div>

          <div class="setting-section">
            <h3>Alertes page d'accueil</h3>
            <label class="setting-toggle">
              <input type="checkbox" bind:checked={general.show_alert_ws} on:change={saveGeneral} />
              <span>Alertes WithSecure (s{'\u00e9'}curit{'\u00e9'})</span>
            </label>
            <label class="setting-toggle">
              <input type="checkbox" bind:checked={general.show_alert_warranty} on:change={saveGeneral} />
              <span>Alertes garantie (parc)</span>
            </label>
          </div>

          <div class="setting-section">
            <h3>Modules activ{'\u00e9'}s</h3>
            <div class="module-grid">
              {#each moduleList as mod}
                <label class="module-toggle">
                  <input type="checkbox" checked={general.enabled_modules[mod.key] !== false}
                    on:change={() => toggleModule(mod.key)} />
                  <span class="module-emoji">{mod.emoji}</span>
                  <span>{mod.label}</span>
                </label>
              {/each}
            </div>
          </div>

          <div class="setting-section">
            <h3>Disposition cards accueil</h3>
            <div class="card-layout-editor">
              {#each cardLayout as card, idx}
                {@const meta = allCards.find(c => c.key === card.key)}
                {#if meta}
                  <div class="card-layout-item" class:disabled={!card.visible}>
                    <div class="card-layout-arrows">
                      <button class="arrow-btn" on:click={() => moveCardUp(idx)} disabled={idx === 0}>{'\u25B2'}</button>
                      <button class="arrow-btn" on:click={() => moveCardDown(idx)} disabled={idx === cardLayout.length - 1}>{'\u25BC'}</button>
                    </div>
                    <span class="card-layout-emoji">{meta.emoji}</span>
                    <span class="card-layout-label">{meta.label}</span>
                    <label class="card-layout-toggle">
                      <input type="checkbox" checked={card.visible} on:change={() => toggleCardVisible(idx)} />
                      <span class="toggle-label">{card.visible ? 'Visible' : 'Masqu\u00e9'}</span>
                    </label>
                  </div>
                {/if}
              {/each}
            </div>
          </div>

          <div class="setting-section">
            <h3>Export de donn{'\u00e9'}es</h3>
            <div class="export-buttons">
              <button class="btn-export" on:click={() => exportCsv('tasks')}>
                {'\u{1F4E5}'} Exporter t{'\u00e2'}ches (CSV)
              </button>
              <button class="btn-export" on:click={() => exportCsv('documents')}>
                {'\u{1F4E5}'} Exporter documents (CSV)
              </button>
            </div>
          </div>

          <div class="setting-section danger-section">
            <h3>{'\u26A0\uFE0F'} Zone dangereuse</h3>
            {#if !showResetConfirm}
              <button class="btn-danger" on:click={() => showResetConfirm = true}>
                {'\u{1F5D1}\uFE0F'} R{'\u00e9'}initialiser toutes les donn{'\u00e9'}es
              </button>
            {:else}
              <div class="reset-confirm">
                <p class="reset-warning">
                  {'\u26A0\uFE0F'} Cette action supprimera la base de donn{'\u00e9'}es et r{'\u00e9'}initialisera tous les param{'\u00e8'}tres.
                  Un backup sera cr{'\u00e9'}{'\u00e9'} automatiquement avant la suppression.
                </p>
                <div class="reset-input-row">
                  <span>Tapez <strong>RESET</strong> pour confirmer :</span>
                  <input type="text" bind:value={resetConfirmText} placeholder="RESET" class="reset-input" />
                  <button class="btn-danger-confirm" on:click={confirmReset}
                    disabled={resetConfirmText !== 'RESET' || resetting}>
                    {resetting ? '\u23F3 ...' : 'Confirmer'}
                  </button>
                  <button class="btn-cancel" on:click={() => { showResetConfirm = false; resetConfirmText = ''; }}>
                    Annuler
                  </button>
                </div>
              </div>
            {/if}
          </div>
        </div>

      <!-- ═══════════════ 2: INTEGRATIONS ═══════════════ -->
      {:else if activePanel === 2}
        <div class="panel">
          <h2>{'\u{1F50C}'} Int{'\u00e9'}grations</h2>

          <div class="integration-card">
            <div class="int-header">
              <span class="int-icon">{'\u{1F6E1}\uFE0F'}</span>
              <div class="int-info">
                <h3>WithSecure</h3>
                <p>Protection endpoint — configuration dans le module S{'\u00e9'}curit{'\u00e9'}</p>
              </div>
              <a href="#" class="int-link" on:click|preventDefault={() => {
                const { currentPage } = window.__stores || {};
                if (currentPage) currentPage.set('/security');
              }}>Configurer {'\u2192'}</a>
            </div>
          </div>

          <div class="integration-card">
            <div class="int-header">
              <span class="int-icon">{'\u{1F4BB}'}</span>
              <div class="int-info">
                <h3>GLPI</h3>
                <p>Inventaire du parc informatique via l'API REST GLPI</p>
              </div>
              <span class="int-badge" class:active-badge={glpiConfig} class:soon={!glpiConfig}>
                {glpiConfig ? 'Actif' : 'Non configur\u00e9'}
              </span>
            </div>
            <div class="gw-config-form">
              {#if glpiConfig}
                <div class="gw-status-grid">
                  <div class="gw-status-item">
                    <span>{'\u2705'}</span>
                    <span>URL : {glpiConfig.url}</span>
                  </div>
                  <div class="gw-status-item">
                    <span>{'\u{1F511}'}</span>
                    <span>App-Token : {glpiConfig.app_token}</span>
                  </div>
                  <div class="gw-status-item">
                    <span>{'\u{1F464}'}</span>
                    <span>User-Token : {glpiConfig.user_token}</span>
                  </div>
                  {#if glpiStats}
                    <div class="gw-status-item">
                      <span>{'\u{1F4E6}'}</span>
                      <span>{glpiStats.total_items} {'\u00e9'}l{'\u00e9'}ments ({glpiStats.computers} PC, {glpiStats.monitors} moniteurs, {glpiStats.printers} imprimantes)</span>
                    </div>
                    {#if glpiStats.last_sync}
                      <div class="gw-status-item">
                        <span>{'\u{1F552}'}</span>
                        <span>Derni{'\u00e8'}re sync : {new Date(glpiStats.last_sync).toLocaleString('fr-FR')}</span>
                      </div>
                    {/if}
                  {/if}
                </div>
                <div style="display:flex;gap:8px;margin-top:8px">
                  <button class="btn-danger" on:click={deleteGlpiConfig} style="font-size:0.75rem;padding:4px 10px">
                    Supprimer la configuration
                  </button>
                </div>
              {/if}
              <div class="glpi-form">
                <p class="gw-help" style="margin-bottom:8px">
                  {glpiConfig ? 'Modifier la configuration :' : 'Entrez vos identifiants GLPI pour activer la synchronisation :'}
                </p>
                <div class="glpi-fields">
                  <input type="text" bind:value={glpiForm.url}
                    placeholder={glpiConfig ? glpiConfig.url : 'https://glpi.mondomaine.fr'}
                    class="glpi-input" />
                  <input type="text" bind:value={glpiForm.app_token}
                    placeholder={glpiConfig ? glpiConfig.app_token : 'App-Token'}
                    class="glpi-input" />
                  <input type="text" bind:value={glpiForm.user_token}
                    placeholder={glpiConfig ? glpiConfig.user_token : 'User-Token'}
                    class="glpi-input" />
                  <button class="btn-small" style="background:var(--accent,#06A6C9);color:#fff;font-weight:600"
                    on:click={saveGlpiConfig}
                    disabled={(!glpiForm.url || !glpiForm.app_token || !glpiForm.user_token) || glpiSaving}>
                    {glpiSaving ? '\u23F3...' : 'Enregistrer'}
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div class="integration-card">
            <div class="int-header">
              <span class="int-icon">{'\u{1F5A5}\uFE0F'}</span>
              <div class="int-info">
                <h3>RDP int{'\u00e9'}gr{'\u00e9'} (Guacamole)</h3>
                <p>Bureau {'\u00e0'} distance dans le navigateur via Docker + guacd</p>
              </div>
              <span class="int-badge" class:active-badge={rdpStatus.ready} class:soon={!rdpStatus.ready}>
                {rdpStatus.ready ? 'Actif' : 'Inactif'}
              </span>
            </div>
            <div class="gw-config-form">
              <div class="gw-status-grid">
                <div class="gw-status-item">
                  <span>{rdpStatus.docker?.installed ? '\u2705' : '\u274C'}</span>
                  <span>Docker : {rdpStatus.docker?.installed ? (rdpStatus.docker?.running ? 'En cours' : 'Arrêté') : 'Non installé'}</span>
                </div>
                <div class="gw-status-item">
                  <span>{rdpStatus.guacd?.port_reachable ? '\u2705' : '\u274C'}</span>
                  <span>guacd : {rdpStatus.guacd?.port_reachable ? 'Actif (port 4822)' : 'Inactif'}</span>
                </div>
              </div>
              <div style="display:flex;gap:8px;margin-top:8px">
                <button class="btn-small" on:click={loadRdpStatus}>{'\u{1F504}'} Rafra{'\u00ee'}chir</button>
              </div>
              <p class="gw-help">
                Configurez le RDP int{'\u00e9'}gr{'\u00e9'} depuis la page <strong>Bastion</strong> {'\u2192'} bouton "RDP Fichier" dans l'en-t{'\u00ea'}te.
              </p>
            </div>
          </div>

          <div class="integration-card">
            <div class="int-header">
              <span class="int-icon">{'\u{1F4E1}'}</span>
              <div class="int-info">
                <h3>Flux RSS</h3>
                <p>Sources d'actualit{'\u00e9'}s — {feeds.length} flux configur{'\u00e9'}s</p>
              </div>
              <button class="int-link" on:click={() => activePanel = 4}>Configurer {'\u2192'}</button>
            </div>
          </div>

          <div class="int-note">
            <p>{'\u{1F4A1}'} Les imports Active Directory ont {'\u00e9'}t{'\u00e9'} remplac{'\u00e9'}s par :</p>
            <ul>
              <li><strong>GLPI</strong> pour l'inventaire du parc (synchronisation depuis le module Parc)</li>
              <li><strong>Croisement Parc {'\u00D7'} WithSecure</strong> pour d{'\u00e9'}tecter les postes sans agent de protection</li>
            </ul>
          </div>
        </div>

      <!-- ═══════════════ 3: SECURITE DB ═══════════════ -->
      {:else if activePanel === 3}
        <div class="panel">
          <h2>{'\u{1F512}'} S{'\u00e9'}curit{'\u00e9'} Base de donn{'\u00e9'}es</h2>

          {#if dbInfo}
            <div class="setting-section">
              <h3>Informations</h3>
              <div class="db-info-grid">
                <div class="db-info-item">
                  <span class="db-label">Chemin</span>
                  <div class="db-value-row">
                    <code class="db-value">{dbInfo.path}</code>
                    <button class="btn-tiny" on:click={() => copyToClipboard(dbInfo.path)} title="Copier">{'\u{1F4CB}'}</button>
                  </div>
                </div>
                <div class="db-info-item">
                  <span class="db-label">Taille</span>
                  <span class="db-value">{dbInfo.size_human}</span>
                </div>
                <div class="db-info-item">
                  <span class="db-label">Mode journal</span>
                  <span class="db-value">{dbInfo.journal_mode}</span>
                </div>
                <div class="db-info-item">
                  <span class="db-label">Tables</span>
                  <span class="db-value">{dbInfo.tables.length} ({dbInfo.tables.join(', ')})</span>
                </div>
              </div>
            </div>
          {/if}

          <div class="setting-section">
            <h3>V{'\u00e9'}rifications</h3>
            <div class="db-actions">
              <button class="btn-db" on:click={() => runDbCheck('integrity')} disabled={dbChecking}>
                {'\u{1F50D}'} V{'\u00e9'}rifier int{'\u00e9'}grit{'\u00e9'}
              </button>
              <button class="btn-db" on:click={() => runDbCheck('fk-check')} disabled={dbChecking}>
                {'\u{1F517}'} V{'\u00e9'}rifier cl{'\u00e9'}s {'\u00e9'}trang{'\u00e8'}res
              </button>
              <button class="btn-db" on:click={() => runDbCheck('vacuum')} disabled={dbChecking}>
                {'\u{1F9F9}'} VACUUM (optimiser)
              </button>
            </div>

            {#if dbChecking}
              <div class="db-result loading">{'\u23F3'} V{'\u00e9'}rification en cours...</div>
            {:else if dbCheckResult}
              <div class="db-result" class:ok={dbCheckResult.ok} class:err={!dbCheckResult.ok}>
                <span class="db-result-icon">{dbCheckResult.ok ? '\u2705' : '\u274C'}</span>
                <pre class="db-result-text">{dbCheckResult.result}</pre>
              </div>
            {/if}
          </div>
        </div>

      <!-- ═══════════════ 4: FLUX RSS ═══════════════ -->
      {:else if activePanel === 4}
        <div class="panel">
          <h2>{'\u{1F4E1}'} Flux RSS</h2>

          <div class="setting-section">
            <h3>Sources configur{'\u00e9'}es ({feeds.length})</h3>
            <div class="feeds-list">
              {#each feeds as feed, idx}
                <div class="feed-item" class:disabled-feed={!feed.enabled}>
                  <label class="feed-toggle">
                    <input type="checkbox" checked={feed.enabled} on:change={() => toggleFeed(idx)} />
                  </label>
                  <div class="feed-info">
                    <span class="feed-name">{feed.name}</span>
                    <span class="feed-url" title={feed.url}>{feed.url.length > 50 ? feed.url.slice(0, 50) + '...' : feed.url}</span>
                  </div>
                  <span class="feed-category">{feed.category}</span>
                  <button class="btn-delete-feed" on:click={() => deleteFeed(idx)} title="Supprimer">
                    {'\u{1F5D1}\uFE0F'}
                  </button>
                </div>
              {/each}
            </div>
          </div>

          <div class="setting-section">
            <h3>Ajouter un flux</h3>
            <div class="add-feed-form">
              <div class="feed-form-row">
                <input type="text" bind:value={newFeedName} placeholder="Nom du flux" class="feed-input" />
                <select bind:value={newFeedCategory} class="feed-select">
                  {#each feedCategories as cat}
                    <option value={cat}>{cat}</option>
                  {/each}
                </select>
              </div>
              <div class="feed-form-row">
                <input type="url" bind:value={newFeedUrl} placeholder="URL du flux RSS (https://...)" class="feed-input feed-url-input"
                  on:keydown={(e) => e.key === 'Enter' && addFeed()} />
                <button class="btn-add-feed" on:click={addFeed}
                  disabled={!newFeedName.trim() || !newFeedUrl.startsWith('http')}>
                  {'\u2795'} Ajouter
                </button>
              </div>
            </div>
          </div>
        </div>

      <!-- ═══════════════ 5: SAUVEGARDE ═══════════════ -->
      {:else if activePanel === 5}
        <div class="panel">
          <h2>{'\u{1F4BE}'} Sauvegarde</h2>

          <!-- Auto-backup config -->
          <div class="setting-section">
            <h3>{'\u{1F504}'} Sauvegarde automatique</h3>
            <p class="setting-desc">
              Une sauvegarde automatique est cr{'\u00e9'}{'\u00e9'}e p{'\u00e9'}riodiquement en arri{'\u00e8'}re-plan.
              Une sauvegarde est aussi cr{'\u00e9'}{'\u00e9'}e automatiquement avant chaque mise {'\u00e0'} jour.
            </p>
            <div class="setting-row">
              <label class="toggle-label">
                <input type="checkbox" bind:checked={autoBackup.enabled} on:change={saveAutoBackup} />
                <span>Activ{'\u00e9'}e</span>
              </label>
            </div>
            <div class="setting-row" style="margin-top:8px;">
              <label class="setting-label">Intervalle (heures)</label>
              <select bind:value={autoBackup.interval_hours} on:change={saveAutoBackup} class="setting-select">
                <option value={1}>1h</option>
                <option value={3}>3h</option>
                <option value={6}>6h</option>
                <option value={12}>12h</option>
                <option value={24}>24h</option>
                <option value={48}>48h</option>
              </select>
            </div>
          </div>

          <!-- Manual backup -->
          <div class="setting-section">
            <h3>Cr{'\u00e9'}er une sauvegarde manuelle</h3>
            <p class="setting-desc">
              La sauvegarde inclut la base de donn{'\u00e9'}es, les param{'\u00e8'}tres, les flux RSS et les logos.
              Les 10 derni{'\u00e8'}res sauvegardes de chaque type sont conserv{'\u00e9'}es.
            </p>
            <button class="btn-backup" on:click={createBackup} disabled={backupRunning}>
              {#if backupRunning}
                {'\u23F3'} Sauvegarde en cours...
              {:else}
                {'\u{1F4BE}'} Sauvegarder maintenant
              {/if}
            </button>

            {#if backupResult}
              {#if backupResult.error}
                <div class="backup-msg err">{'\u274C'} {backupResult.error}</div>
              {:else}
                <div class="backup-msg ok">{'\u2705'} Sauvegarde cr{'\u00e9'}{'\u00e9'}e : {backupResult.filename}</div>
              {/if}
            {/if}
          </div>

          <div class="setting-section">
            <h3>Sauvegardes existantes ({backups.length})</h3>
            <button class="btn-small" on:click={() => loadBackups()} style="margin-bottom:8px;">{'\u{1F504}'} Rafra{'\u00ee'}chir</button>
            {#if backups.length === 0}
              <p class="setting-desc">Aucune sauvegarde trouv{'\u00e9'}e.</p>
            {:else}
              <div class="backups-list">
                {#each backups as backup}
                  <div class="backup-item">
                    <span class="backup-type" class:auto={backup.type === 'Auto'} class:pre-maj={backup.type === 'Pré-MAJ'} class:pre-reset={backup.type === 'Pré-reset'}>{backup.type || 'Manuel'}</span>
                    <span class="backup-name">{backup.filename}</span>
                    <span class="backup-size">{backup.size_human}</span>
                    <span class="backup-date">{new Date(backup.modified).toLocaleString('fr-FR')}</span>
                  </div>
                {/each}
              </div>
            {/if}
          </div>
        </div>
      {/if}
    </div>
  </div>
</div>

<style>
  .settings-page {
    display: flex;
    flex-direction: column;
    height: calc(100vh - 56px);
    gap: 12px;
  }

  .page-header {
    display: flex;
    align-items: center;
    gap: 16px;
  }

  .page-header h1 {
    color: var(--text, #E6EAF2);
    font-size: 1.5rem;
    font-weight: 700;
    margin: 0;
  }

  .saved-badge {
    background: rgba(16,185,129,0.15);
    color: #10B981;
    padding: 4px 12px;
    border-radius: 8px;
    font-size: 0.8rem;
    font-weight: 600;
  }

  .settings-layout {
    display: flex;
    flex: 1;
    gap: 12px;
    min-height: 0;
  }

  /* ── Panel nav ────────────────────────────────────────── */

  .panel-nav {
    width: 200px;
    display: flex;
    flex-direction: column;
    gap: 4px;
    flex-shrink: 0;
  }

  .panel-btn {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 14px;
    background: transparent;
    border: 1px solid transparent;
    border-radius: 10px;
    color: var(--text-dim, #94A3B8);
    cursor: pointer;
    font-size: 0.85rem;
    text-align: left;
    transition: all 0.15s;
  }
  .panel-btn:hover { background: rgba(255,255,255,0.03); }
  .panel-btn.active {
    background: var(--bg-card, rgba(13,24,42,0.7));
    border-color: var(--border-subtle, rgba(255,255,255,0.06));
    color: var(--text, #E6EAF2);
  }
  .panel-emoji { font-size: 1.1rem; }

  /* ── Panel content ────────────────────────────────────── */

  .panel-content {
    flex: 1;
    min-width: 0;
    overflow-y: auto;
  }

  .panel {
    background: var(--bg-card, rgba(13,24,42,0.7));
    border: 1px solid var(--border-subtle, rgba(255,255,255,0.06));
    border-radius: 12px;
    padding: 24px;
  }

  .panel h2 {
    color: var(--text, #E6EAF2);
    font-size: 1.15rem;
    font-weight: 700;
    margin: 0 0 20px 0;
  }

  .setting-section {
    margin-bottom: 24px;
  }
  .setting-section h3 {
    color: var(--text-dim, #94A3B8);
    font-size: 0.8rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin: 0 0 10px 0;
  }
  .setting-desc {
    color: var(--text-dim, #94A3B8);
    font-size: 0.85rem;
    line-height: 1.6;
    margin: 0 0 12px 0;
  }

  /* ── Appearance ───────────────────────────────────────── */

  .color-presets {
    display: flex;
    gap: 8px;
    align-items: center;
    flex-wrap: wrap;
  }
  .color-btn {
    width: 32px; height: 32px;
    border-radius: 8px;
    border: 2px solid transparent;
    cursor: pointer;
    transition: all 0.15s;
  }
  .color-btn:hover { transform: scale(1.1); }
  .color-btn.active { border-color: #fff; box-shadow: 0 0 8px rgba(255,255,255,0.3); }

  .custom-color {
    width: 32px; height: 32px;
    border: 2px solid var(--border-subtle, rgba(255,255,255,0.1));
    border-radius: 8px;
    cursor: pointer;
    background: transparent;
    padding: 0;
  }

  .icon-presets {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }
  .icon-btn {
    width: 40px; height: 40px;
    border-radius: 8px;
    border: 2px solid transparent;
    background: rgba(0,0,0,0.2);
    cursor: pointer;
    font-size: 1.2rem;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.15s;
  }
  .icon-btn:hover { background: rgba(255,255,255,0.05); }
  .icon-btn.active { border-color: var(--accent, #06A6C9); background: rgba(6,166,201,0.1); }

  .theme-options { display: flex; gap: 12px; }
  .theme-card {
    padding: 12px;
    border-radius: 10px;
    border: 2px solid transparent;
    background: rgba(0,0,0,0.2);
    cursor: pointer;
    color: var(--text-dim, #94A3B8);
    font-size: 0.8rem;
    text-align: center;
    transition: all 0.15s;
  }
  .theme-card.active { border-color: var(--accent, #06A6C9); }
  .theme-preview {
    width: 80px; height: 50px;
    border-radius: 6px;
    margin-bottom: 6px;
  }
  .glass-preview {
    background: linear-gradient(135deg, #0D1826 0%, #1a2740 50%, #0D1826 100%);
    border: 1px solid rgba(255,255,255,0.06);
  }

  /* ── General ──────────────────────────────────────────── */

  .setting-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 0;
    gap: 16px;
  }
  .setting-row span {
    color: var(--text, #E6EAF2);
    font-size: 0.85rem;
  }
  .setting-row input, .setting-row select {
    background: rgba(0,0,0,0.3);
    border: 1px solid var(--border-subtle, rgba(255,255,255,0.06));
    border-radius: 8px;
    padding: 6px 10px;
    color: var(--text, #E6EAF2);
    font-size: 0.85rem;
    outline: none;
    min-width: 120px;
  }
  .setting-row input:focus, .setting-row select:focus {
    border-color: var(--accent, #06A6C9);
  }
  .setting-row select {
    background: rgba(0,0,0,0.3);
  }
  .setting-row input[type="number"] { width: 80px; min-width: 80px; }

  .setting-toggle {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 6px 0;
    cursor: pointer;
  }
  .setting-toggle span {
    color: var(--text, #E6EAF2);
    font-size: 0.85rem;
  }
  .setting-toggle input[type="checkbox"] {
    width: 18px; height: 18px;
    accent-color: var(--accent, #06A6C9);
    cursor: pointer;
  }

  .module-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    gap: 8px;
  }
  .module-toggle {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    background: rgba(0,0,0,0.15);
    border-radius: 8px;
    cursor: pointer;
    transition: background 0.15s;
  }
  .module-toggle:hover { background: rgba(0,0,0,0.25); }
  .module-toggle input[type="checkbox"] {
    accent-color: var(--accent, #06A6C9);
    cursor: pointer;
  }
  .module-toggle span {
    color: var(--text, #E6EAF2);
    font-size: 0.8rem;
  }
  .module-emoji { font-size: 1rem; }

  /* ── Card layout editor ────────────────────────────────── */

  .card-layout-editor {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .card-layout-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 12px;
    background: rgba(0,0,0,0.15);
    border: 1px solid var(--border-subtle, rgba(255,255,255,0.06));
    border-radius: 8px;
    transition: opacity 0.15s;
  }
  .card-layout-item.disabled { opacity: 0.4; }
  .card-layout-arrows {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  .arrow-btn {
    background: transparent;
    border: 1px solid var(--border-subtle, rgba(255,255,255,0.06));
    border-radius: 4px;
    padding: 1px 6px;
    color: var(--text-dim, #94A3B8);
    cursor: pointer;
    font-size: 0.55rem;
    line-height: 1;
  }
  .arrow-btn:disabled { opacity: 0.3; cursor: default; }
  .arrow-btn:not(:disabled):hover { background: rgba(255,255,255,0.05); }
  .card-layout-emoji { font-size: 1rem; }
  .card-layout-label {
    flex: 1;
    color: var(--text, #E6EAF2);
    font-size: 0.85rem;
  }
  .card-layout-toggle {
    display: flex;
    align-items: center;
    gap: 6px;
    cursor: pointer;
  }
  .card-layout-toggle input { accent-color: var(--accent, #06A6C9); cursor: pointer; }
  .toggle-label {
    color: var(--text-dim, #94A3B8);
    font-size: 0.7rem;
  }

  /* ── Export ────────────────────────────────────────────── */

  .export-buttons {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }
  .btn-export {
    background: rgba(0,0,0,0.3);
    border: 1px solid var(--border-subtle, rgba(255,255,255,0.06));
    border-radius: 8px;
    padding: 8px 16px;
    color: var(--text, #E6EAF2);
    cursor: pointer;
    font-size: 0.8rem;
    transition: all 0.15s;
  }
  .btn-export:hover { background: rgba(255,255,255,0.05); }

  /* ── Danger zone ───────────────────────────────────────── */

  .danger-section {
    border-top: 1px solid rgba(239,68,68,0.2);
    padding-top: 20px;
  }
  .danger-section h3 { color: #EF4444; }

  .btn-danger {
    background: rgba(239,68,68,0.1);
    border: 1px solid rgba(239,68,68,0.3);
    border-radius: 8px;
    padding: 8px 20px;
    color: #EF4444;
    cursor: pointer;
    font-size: 0.85rem;
    font-weight: 600;
    transition: all 0.15s;
  }
  .btn-danger:hover { background: rgba(239,68,68,0.2); }

  .reset-confirm {
    background: rgba(239,68,68,0.05);
    border: 1px solid rgba(239,68,68,0.2);
    border-radius: 10px;
    padding: 16px;
  }
  .reset-warning {
    color: #F59E0B;
    font-size: 0.85rem;
    margin: 0 0 12px 0;
    line-height: 1.5;
  }
  .reset-input-row {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }
  .reset-input-row span {
    color: var(--text-dim, #94A3B8);
    font-size: 0.8rem;
  }
  .reset-input-row strong { color: #EF4444; }
  .reset-input {
    background: rgba(0,0,0,0.3);
    border: 1px solid rgba(239,68,68,0.3);
    border-radius: 6px;
    padding: 6px 10px;
    color: var(--text, #E6EAF2);
    font-size: 0.85rem;
    width: 100px;
    outline: none;
  }
  .btn-danger-confirm {
    background: #EF4444;
    border: none;
    border-radius: 6px;
    padding: 6px 14px;
    color: #fff;
    cursor: pointer;
    font-size: 0.8rem;
    font-weight: 600;
  }
  .btn-danger-confirm:disabled { opacity: 0.5; cursor: not-allowed; }
  .btn-cancel {
    background: transparent;
    border: 1px solid var(--border-subtle, rgba(255,255,255,0.06));
    border-radius: 6px;
    padding: 6px 14px;
    color: var(--text-dim, #94A3B8);
    cursor: pointer;
    font-size: 0.8rem;
  }

  /* ── Integrations ────────────────────────────────────── */

  .integration-card {
    background: rgba(0,0,0,0.15);
    border: 1px solid var(--border-subtle, rgba(255,255,255,0.06));
    border-radius: 10px;
    padding: 16px;
    margin-bottom: 10px;
  }
  .int-header {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .int-icon { font-size: 1.5rem; }
  .int-info { flex: 1; }
  .int-info h3 {
    color: var(--text, #E6EAF2);
    font-size: 0.9rem;
    font-weight: 600;
    margin: 0;
  }
  .int-info p {
    color: var(--text-dim, #94A3B8);
    font-size: 0.75rem;
    margin: 2px 0 0;
  }
  .int-link {
    color: var(--accent, #06A6C9);
    font-size: 0.8rem;
    text-decoration: none;
    cursor: pointer;
    white-space: nowrap;
    background: transparent;
    border: none;
    font-family: inherit;
  }
  .int-link:hover { text-decoration: underline; }
  .int-badge {
    font-size: 0.7rem;
    padding: 2px 8px;
    border-radius: 6px;
    font-weight: 600;
  }
  .int-badge.soon { background: rgba(245,158,11,0.15); color: #F59E0B; }
  .int-badge.active-badge { background: rgba(16,185,129,0.15); color: #10B981; }

  .glpi-form { margin-top: 10px; }
  .glpi-fields {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .glpi-input {
    background: rgba(0,0,0,0.3);
    border: 1px solid var(--border-subtle, rgba(255,255,255,0.06));
    border-radius: 6px;
    padding: 7px 10px;
    color: var(--text, #E6EAF2);
    font-size: 0.8rem;
    outline: none;
    width: 100%;
    box-sizing: border-box;
  }
  .glpi-input:focus { border-color: var(--accent, #06A6C9); }

  .gw-config-form {
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px solid var(--border-subtle, rgba(255,255,255,0.06));
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .gw-help {
    color: var(--text-dim, #64748B);
    font-size: 0.75rem;
    margin: 4px 0 0;
  }
  .gw-help a, .gw-help strong { color: var(--accent, #06A6C9); }

  .gw-status-grid {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .gw-status-item {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.8rem;
    color: var(--text-dim, #94A3B8);
  }
  .btn-small {
    background: var(--bg-card, rgba(13,24,42,0.7));
    border: 1px solid var(--border-subtle, rgba(255,255,255,0.06));
    border-radius: 6px;
    padding: 4px 10px;
    color: var(--text-dim, #94A3B8);
    cursor: pointer;
    font-size: 0.75rem;
    transition: all 0.15s;
  }
  .btn-small:hover { background: rgba(255,255,255,0.05); color: var(--text, #E6EAF2); }

  .int-note {
    margin-top: 20px;
    padding: 14px 16px;
    background: rgba(6,166,201,0.06);
    border: 1px solid rgba(6,166,201,0.15);
    border-radius: 10px;
  }
  .int-note p {
    color: var(--text, #E6EAF2);
    font-size: 0.85rem;
    margin: 0 0 8px 0;
  }
  .int-note ul {
    margin: 0;
    padding-left: 20px;
  }
  .int-note li {
    color: var(--text-dim, #94A3B8);
    font-size: 0.8rem;
    line-height: 1.8;
  }
  .int-note li strong { color: var(--text, #E6EAF2); }

  /* ── DB Security ──────────────────────────────────────── */

  .db-info-grid {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .db-info-item {
    display: flex;
    flex-direction: column;
    gap: 2px;
    padding: 8px 12px;
    background: rgba(0,0,0,0.15);
    border-radius: 8px;
  }
  .db-label {
    color: var(--text-dim, #64748B);
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.3px;
  }
  .db-value {
    color: var(--text, #E6EAF2);
    font-size: 0.85rem;
    font-family: 'Consolas', monospace;
  }
  .db-value-row {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .btn-tiny {
    background: transparent;
    border: 1px solid var(--border-subtle, rgba(255,255,255,0.06));
    border-radius: 4px;
    padding: 2px 6px;
    color: var(--text-dim, #94A3B8);
    cursor: pointer;
    font-size: 0.7rem;
  }
  .btn-tiny:hover { background: rgba(255,255,255,0.05); }

  .db-actions {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    margin-bottom: 12px;
  }
  .btn-db {
    background: rgba(0,0,0,0.3);
    border: 1px solid var(--border-subtle, rgba(255,255,255,0.06));
    border-radius: 8px;
    padding: 8px 16px;
    color: var(--text, #E6EAF2);
    cursor: pointer;
    font-size: 0.8rem;
    transition: all 0.15s;
  }
  .btn-db:disabled { opacity: 0.5; cursor: not-allowed; }
  .btn-db:not(:disabled):hover { background: rgba(255,255,255,0.05); }

  .db-result {
    padding: 12px 16px;
    border-radius: 8px;
    display: flex;
    align-items: flex-start;
    gap: 10px;
  }
  .db-result.loading { color: #F59E0B; background: rgba(245,158,11,0.05); }
  .db-result.ok { background: rgba(16,185,129,0.1); border: 1px solid rgba(16,185,129,0.2); }
  .db-result.err { background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.2); }
  .db-result-icon { font-size: 1rem; flex-shrink: 0; }
  .db-result-text {
    color: var(--text, #E6EAF2);
    font-size: 0.8rem;
    font-family: 'Consolas', monospace;
    margin: 0;
    white-space: pre-wrap;
    word-break: break-all;
  }

  /* ── RSS Feeds ────────────────────────────────────────── */

  .feeds-list {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .feed-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 12px;
    background: rgba(0,0,0,0.15);
    border: 1px solid var(--border-subtle, rgba(255,255,255,0.06));
    border-radius: 8px;
    transition: opacity 0.15s;
  }
  .feed-item.disabled-feed { opacity: 0.4; }
  .feed-toggle input {
    accent-color: var(--accent, #06A6C9);
    cursor: pointer;
    width: 16px; height: 16px;
  }
  .feed-info {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 1px;
    min-width: 0;
  }
  .feed-name {
    color: var(--text, #E6EAF2);
    font-size: 0.85rem;
    font-weight: 600;
  }
  .feed-url {
    color: var(--text-dim, #64748B);
    font-size: 0.65rem;
    font-family: 'Consolas', monospace;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .feed-category {
    background: rgba(6,166,201,0.1);
    color: var(--accent, #06A6C9);
    padding: 2px 8px;
    border-radius: 6px;
    font-size: 0.65rem;
    font-weight: 600;
    white-space: nowrap;
  }
  .btn-delete-feed {
    background: transparent;
    border: none;
    cursor: pointer;
    font-size: 0.85rem;
    padding: 2px 4px;
    opacity: 0.5;
    transition: opacity 0.15s;
  }
  .btn-delete-feed:hover { opacity: 1; }

  .add-feed-form {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .feed-form-row {
    display: flex;
    gap: 8px;
    align-items: center;
  }
  .feed-input {
    flex: 1;
    background: rgba(0,0,0,0.3);
    border: 1px solid var(--border-subtle, rgba(255,255,255,0.06));
    border-radius: 8px;
    padding: 8px 12px;
    color: var(--text, #E6EAF2);
    font-size: 0.85rem;
    outline: none;
  }
  .feed-input:focus { border-color: var(--accent, #06A6C9); }
  .feed-url-input {
    font-family: 'Consolas', monospace;
    font-size: 0.8rem;
  }
  .feed-select {
    background: rgba(0,0,0,0.3);
    border: 1px solid var(--border-subtle, rgba(255,255,255,0.06));
    border-radius: 8px;
    padding: 8px 12px;
    color: var(--text, #E6EAF2);
    font-size: 0.85rem;
    outline: none;
    min-width: 120px;
  }
  .btn-add-feed {
    background: var(--accent, #06A6C9);
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    color: #fff;
    cursor: pointer;
    font-size: 0.8rem;
    font-weight: 600;
    white-space: nowrap;
    transition: opacity 0.15s;
  }
  .btn-add-feed:disabled { opacity: 0.5; cursor: not-allowed; }
  .btn-add-feed:not(:disabled):hover { opacity: 0.85; }

  /* ── Backup ───────────────────────────────────────────── */

  .btn-backup {
    background: var(--accent, #06A6C9);
    border: none;
    border-radius: 8px;
    padding: 10px 24px;
    color: #fff;
    cursor: pointer;
    font-size: 0.85rem;
    font-weight: 600;
    transition: opacity 0.15s;
  }
  .btn-backup:disabled { opacity: 0.5; cursor: not-allowed; }
  .btn-backup:not(:disabled):hover { opacity: 0.85; }

  .backup-msg {
    margin-top: 10px;
    padding: 10px 14px;
    border-radius: 8px;
    font-size: 0.85rem;
  }
  .backup-msg.ok {
    background: rgba(16,185,129,0.1);
    border: 1px solid rgba(16,185,129,0.2);
    color: #10B981;
  }
  .backup-msg.err {
    background: rgba(239,68,68,0.1);
    border: 1px solid rgba(239,68,68,0.2);
    color: #EF4444;
  }

  .backups-list {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .backup-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 12px;
    background: rgba(0,0,0,0.15);
    border-radius: 8px;
    font-size: 0.8rem;
  }
  .backup-type {
    font-size: 0.65rem;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 4px;
    background: rgba(255,255,255,0.1);
    color: var(--text-dim, #94a3b8);
    min-width: 60px;
    text-align: center;
  }
  .backup-type.auto { background: rgba(16,185,129,0.2); color: #10b981; }
  .backup-type.pre-maj { background: rgba(139,92,246,0.2); color: #8b5cf6; }
  .backup-type.pre-reset { background: rgba(239,68,68,0.2); color: #ef4444; }
  .backup-name {
    flex: 1;
    color: var(--text, #E6EAF2);
    font-family: 'Consolas', monospace;
    font-size: 0.8rem;
  }
  .backup-size {
    color: var(--accent, #06A6C9);
    font-weight: 600;
    font-size: 0.75rem;
  }
  .backup-date {
    color: var(--text-dim, #64748B);
    font-size: 0.7rem;
    white-space: nowrap;
  }
</style>
