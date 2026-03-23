<script>
  import { onMount } from 'svelte';
  import { api } from '../api/client.js';
  import { success, error as toastError } from '../stores/toast.js';

  // ── State ──────────────────────────────────────────────────
  let equipment = [];
  let sites = [];
  let buildings = {};   // { site_id: [...] }
  let rooms = {};       // { building_id: [...] }
  let stats = { total: 0, by_type: {}, by_site: {}, by_source: {} };
  let loading = true;

  // Filters
  let searchQuery = '';
  let filterType = '';
  let filterSource = '';
  let selectedSiteId = null;
  let selectedBuildingId = null;
  let selectedRoomId = null;

  // Sidebar expand state
  let expandedSites = {};
  let expandedBuildings = {};

  // Tab: 'inventory' or 'audit'
  let activeTab = 'inventory';

  // Audit data (smart)
  let auditData = null;  // { rules, issues, summary }
  let auditLoaded = false;
  let showRulesPanel = false;
  let auditRules = {};
  let savingRules = false;
  let auditFilterType = '';
  let auditFilterSeverity = '';

  // Equipment dialog
  let showDialog = false;
  let editingEquipment = null;
  let form = defaultForm();
  let saving = false;

  // Delete
  let confirmDelete = null;
  let deleting = false;

  // GLPI integration
  let glpiConfig = null;
  let glpiSyncing = false;
  let glpiStats = null;

  // Derived
  $: typeList = [...new Set(equipment.map(e => e.equip_type).filter(Boolean))].sort();
  $: sourceList = [...new Set(equipment.map(e => e.source).filter(Boolean))].sort();

  $: filteredEquipment = equipment.filter(e => {
    if (filterType && e.equip_type !== filterType) return false;
    if (filterSource && e.source !== filterSource) return false;
    if (selectedSiteId && e.site_id !== selectedSiteId) return false;
    if (selectedBuildingId && e.building_id !== selectedBuildingId) return false;
    if (selectedRoomId && e.room_id !== selectedRoomId) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      if (!(e.hostname || '').toLowerCase().includes(q) &&
          !(e.serial_number || '').toLowerCase().includes(q) &&
          !(e.brand || '').toLowerCase().includes(q) &&
          !(e.model || '').toLowerCase().includes(q) &&
          !(e.os || '').toLowerCase().includes(q)) return false;
    }
    return true;
  });

  // Cascading selects for dialog
  $: dialogBuildings = form.site_id ? (buildings[form.site_id] || []) : [];
  $: dialogRooms = form.building_id ? (rooms[form.building_id] || []) : [];

  function defaultForm() {
    return {
      hostname: '', equip_type: 'PC', os: '', serial_number: '',
      brand: '', model: '', site_id: null, building_id: null, room_id: null,
      source: 'manual', notes: '', warranty_end: '', purchase_date: '',
    };
  }

  // ── Load ───────────────────────────────────────────────────
  onMount(() => { loadAll(); loadGlpiConfig(); });

  async function loadAll() {
    loading = true;
    try {
      const [eq, st, siteList] = await Promise.all([
        api.get('/api/parc/equipment'),
        api.get('/api/parc/stats'),
        api.get('/api/parc/sites'),
      ]);
      equipment = eq;
      stats = st;
      sites = siteList;

      // Load buildings for each site
      for (const site of siteList) {
        const bl = await api.get(`/api/parc/sites/${site.id}/buildings`);
        buildings[site.id] = bl;
        buildings = buildings; // trigger reactivity
        for (const b of bl) {
          const rm = await api.get(`/api/parc/buildings/${b.id}/rooms`);
          rooms[b.id] = rm;
        }
        rooms = rooms;
      }
    } catch (e) {
      toastError('Erreur chargement parc : ' + e.message);
    }
    loading = false;
  }

  // Audit derived filters
  $: filteredAuditIssues = (auditData?.issues || []).filter(i => {
    if (auditFilterType && i.equip_type !== auditFilterType) return false;
    if (auditFilterSeverity && i.severity !== auditFilterSeverity) return false;
    return true;
  });

  $: auditEquipTypes = auditData ? Object.keys(auditData.summary?.by_type || {}).sort() : [];

  async function loadAudit() {
    try {
      auditData = await api.get('/api/parc/audit');
      auditRules = auditData.rules || {};
      auditLoaded = true;
    } catch (e) {
      toastError('Erreur chargement audit : ' + e.message);
    }
  }

  function switchTab(tab) {
    activeTab = tab;
    if (tab === 'audit' && !auditLoaded) loadAudit();
  }

  async function saveAuditRules() {
    savingRules = true;
    try {
      await api.put('/api/parc/audit/rules', auditRules);
      // Reload audit with new rules
      auditLoaded = false;
      await loadAudit();
      success('R\u00e8gles d\u2019audit sauvegard\u00e9es');
    } catch (e) {
      toastError('Erreur sauvegarde r\u00e8gles');
    }
    savingRules = false;
  }

  function resetAuditRules() {
    auditRules = {
      "PC":          {"site": true, "building": true, "room": true, "os": true, "user": false},
      "Portable":    {"site": true, "building": true, "room": true, "os": true, "user": false},
      "Chromebook":  {"site": true, "building": false, "room_or_user": true, "os": false, "user": false},
      "Imprimante":  {"site": true, "building": true, "room": false, "os": false, "user": false},
      "Switch":      {"site": true, "building": true, "room": false, "os": false, "user": false},
      "AP Wi-Fi":    {"site": true, "building": true, "room": false, "os": false, "user": false},
      "Serveur":     {"site": true, "building": true, "room": true, "os": true, "user": false},
      "_default":    {"site": true, "building": false, "room": false, "os": false, "user": false},
    };
  }

  function missingLabel(key) {
    const labels = { site: 'Site', building: 'B\u00e2timent', room: 'Salle', os: 'OS', user: 'Utilisateur', room_or_user: 'Salle ou Utilisateur' };
    return labels[key] || key;
  }

  // ── Sidebar ────────────────────────────────────────────────
  function toggleSite(siteId) {
    expandedSites[siteId] = !expandedSites[siteId];
    expandedSites = expandedSites;
  }
  function toggleBuilding(buildingId) {
    expandedBuildings[buildingId] = !expandedBuildings[buildingId];
    expandedBuildings = expandedBuildings;
  }
  function selectSite(siteId) {
    selectedSiteId = selectedSiteId === siteId ? null : siteId;
    selectedBuildingId = null;
    selectedRoomId = null;
  }
  function selectBuilding(buildingId) {
    selectedBuildingId = selectedBuildingId === buildingId ? null : buildingId;
    selectedRoomId = null;
  }
  function selectRoom(roomId) {
    selectedRoomId = selectedRoomId === roomId ? null : roomId;
  }
  function clearTreeFilter() {
    selectedSiteId = null;
    selectedBuildingId = null;
    selectedRoomId = null;
  }

  // ── Equipment count per node ───────────────────────────────
  function countBySite(siteId) { return equipment.filter(e => e.site_id === siteId).length; }
  function countByBuilding(bId) { return equipment.filter(e => e.building_id === bId).length; }
  function countByRoom(rId) { return equipment.filter(e => e.room_id === rId).length; }

  // ── CRUD ───────────────────────────────────────────────────
  function openNew() {
    editingEquipment = null;
    form = defaultForm();
    showDialog = true;
  }
  function openEdit(eq) {
    editingEquipment = eq;
    form = {
      hostname: eq.hostname, equip_type: eq.equip_type, os: eq.os,
      serial_number: eq.serial_number, brand: eq.brand, model: eq.model,
      site_id: eq.site_id, building_id: eq.building_id, room_id: eq.room_id,
      source: eq.source, notes: eq.notes,
      warranty_end: eq.warranty_end || '', purchase_date: eq.purchase_date || '',
    };
    showDialog = true;
  }

  async function saveEquipment() {
    saving = true;
    try {
      const payload = {
        ...form,
        site_id: form.site_id || null,
        building_id: form.building_id || null,
        room_id: form.room_id || null,
        warranty_end: form.warranty_end || null,
        purchase_date: form.purchase_date || null,
      };
      if (editingEquipment) {
        await api.put(`/api/parc/equipment/${editingEquipment.id}`, payload);
        success('Équipement modifié');
      } else {
        await api.post('/api/parc/equipment', payload);
        success('Équipement ajouté');
      }
      showDialog = false;
      await loadAll();
    } catch (e) {
      toastError('Erreur : ' + e.message);
    }
    saving = false;
  }

  async function deleteEquipment() {
    if (!confirmDelete) return;
    deleting = true;
    try {
      await api.delete(`/api/parc/equipment/${confirmDelete.id}`);
      success('Équipement supprimé');
      confirmDelete = null;
      await loadAll();
    } catch (e) {
      toastError('Erreur : ' + e.message);
    }
    deleting = false;
  }

  // Cascading selects handlers
  async function onSiteChange() {
    form.building_id = null;
    form.room_id = null;
    if (form.site_id && !buildings[form.site_id]) {
      buildings[form.site_id] = await api.get(`/api/parc/sites/${form.site_id}/buildings`);
      buildings = buildings;
    }
  }
  async function onBuildingChange() {
    form.room_id = null;
    if (form.building_id && !rooms[form.building_id]) {
      rooms[form.building_id] = await api.get(`/api/parc/buildings/${form.building_id}/rooms`);
      rooms = rooms;
    }
  }

  // ── GLPI ─────────────────────────────────────────────────
  async function loadGlpiConfig() {
    try {
      const cfg = await api.get('/api/glpi/config');
      glpiConfig = cfg.configured ? cfg : null;
      if (glpiConfig) {
        const st = await api.get('/api/glpi/stats');
        glpiStats = st;
      }
    } catch (e) {
      glpiConfig = null;
    }
  }

  async function triggerGlpiSync() {
    glpiSyncing = true;
    try {
      const result = await api.post('/api/glpi/sync');
      success(`Sync GLPI : ${result.created} créés, ${result.updated} mis à jour, ${result.unchanged} inchangés`);
      await loadGlpiConfig();
      await loadAll();
    } catch (e) {
      toastError('Erreur sync GLPI : ' + e.message);
    }
    glpiSyncing = false;
  }
</script>

<!-- ── KPI Stats ──────────────────────────────────────────── -->
<div class="page-header">
  <div class="title-row">
    <h1>Parc Informatique</h1>
    <div class="header-actions">
      {#if glpiConfig}
        <button class="btn-sync" on:click={triggerGlpiSync} disabled={glpiSyncing} title="Synchroniser avec GLPI">
          {glpiSyncing ? '⏳ Sync…' : '🔄 Sync GLPI'}
        </button>
        {#if glpiStats?.last_sync}
          <span class="sync-info">Dernière sync : {new Date(glpiStats.last_sync).toLocaleString('fr-FR')}</span>
        {/if}
      {/if}
      <button class="btn-primary" on:click={openNew}>+ Ajouter</button>
    </div>
  </div>

  <div class="stats-row">
    <div class="stat-card accent">
      <span class="stat-value">{stats.total}</span>
      <span class="stat-label">Total</span>
    </div>
    {#each Object.entries(stats.by_type) as [type, count]}
      <div class="stat-card">
        <span class="stat-value">{count}</span>
        <span class="stat-label">{type}</span>
      </div>
    {/each}
  </div>
</div>

<!-- ── Tabs ────────────────────────────────────────────────── -->
<div class="tabs">
  <button class="tab" class:active={activeTab === 'inventory'} on:click={() => switchTab('inventory')}>
    Inventaire
  </button>
  <button class="tab" class:active={activeTab === 'audit'} on:click={() => switchTab('audit')}>
    Audit
    {#if auditLoaded && auditData}
      <span class="badge">{auditData.issues.length}</span>
    {/if}
  </button>
</div>

{#if activeTab === 'inventory'}
<!-- ── Inventory Tab ──────────────────────────────────────── -->
<div class="inventory-layout">
  <!-- Sidebar Tree -->
  <aside class="tree-sidebar">
    <div class="tree-header">
      <span class="tree-header-icon">{'\u{1F5C2}\uFE0F'}</span>
      <strong>Sites</strong>
      {#if selectedSiteId || selectedBuildingId || selectedRoomId}
        <button class="btn-clear" on:click={clearTreeFilter}>Effacer</button>
      {/if}
    </div>
    <div class="tree-list">
      {#each sites as site}
        <div class="tree-node">
          <button class="tree-item site-level"
                  class:selected={selectedSiteId === site.id}
                  on:click={() => selectSite(site.id)}>
            <span class="tree-toggle" on:click|stopPropagation={() => toggleSite(site.id)}>
              <svg class="chevron" class:open={expandedSites[site.id]} width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="9 18 15 12 9 6"/></svg>
            </span>
            <span class="tree-ico">{'\u{1F3E2}'}</span>
            <span class="tree-label">{site.code || site.name}</span>
            <span class="tree-count">{countBySite(site.id)}</span>
          </button>
          {#if expandedSites[site.id] && buildings[site.id]}
            <div class="tree-children">
              {#each buildings[site.id] as building}
                <div class="tree-node">
                  <button class="tree-item building-level"
                          class:selected={selectedBuildingId === building.id}
                          on:click={() => selectBuilding(building.id)}>
                    <span class="tree-toggle" on:click|stopPropagation={() => toggleBuilding(building.id)}>
                      <svg class="chevron" class:open={expandedBuildings[building.id]} width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="9 18 15 12 9 6"/></svg>
                    </span>
                    <span class="tree-ico">{'\u{1F3D7}\uFE0F'}</span>
                    <span class="tree-label">{building.name}</span>
                    <span class="tree-count">{countByBuilding(building.id)}</span>
                  </button>
                  {#if expandedBuildings[building.id] && rooms[building.id]}
                    <div class="tree-children">
                      {#each rooms[building.id] as room}
                        <div class="tree-node">
                          <button class="tree-item room-level"
                                  class:selected={selectedRoomId === room.id}
                                  on:click={() => selectRoom(room.id)}>
                            <span class="tree-ico">{'\u{1F6AA}'}</span>
                            <span class="tree-label">{room.name}</span>
                            <span class="tree-count">{countByRoom(room.id)}</span>
                          </button>
                        </div>
                      {/each}
                    </div>
                  {/if}
                </div>
              {/each}
            </div>
          {/if}
        </div>
      {/each}
    </div>
  </aside>

  <!-- Main Content -->
  <div class="main-content">
    <!-- Filters -->
    <div class="filters-bar">
      <input type="text" placeholder="Rechercher hostname, SN, marque…"
             class="search-input" bind:value={searchQuery} />
      <select class="filter-select" bind:value={filterType}>
        <option value="">— Type —</option>
        {#each typeList as t}<option value={t}>{t}</option>{/each}
      </select>
      <select class="filter-select" bind:value={filterSource}>
        <option value="">— Source —</option>
        {#each sourceList as s}<option value={s}>{s}</option>{/each}
      </select>
      <span class="result-count">{filteredEquipment.length} résultat{filteredEquipment.length !== 1 ? 's' : ''}</span>
    </div>

    <!-- Equipment Table -->
    {#if loading}
      <div class="loading">Chargement…</div>
    {:else}
      <div class="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Hostname</th>
              <th>Type</th>
              <th>OS</th>
              <th>N° Série</th>
              <th>Marque / Modèle</th>
              <th>Localisation</th>
              <th>Source</th>
              <th>Dernier utilisateur</th>
              <th class="actions-col">Actions</th>
            </tr>
          </thead>
          <tbody>
            {#each filteredEquipment as eq}
              <tr>
                <td class="hostname">{eq.hostname}</td>
                <td><span class="type-badge">{eq.equip_type}</span></td>
                <td class="os-cell">{eq.os}</td>
                <td>{eq.serial_number || '—'}</td>
                <td>{[eq.brand, eq.model].filter(Boolean).join(' ') || '—'}</td>
                <td class="loc-cell">
                  {#if eq.site_name}
                    <span class="loc-part">{eq.site_name}</span>
                    {#if eq.building_name}<span class="loc-sep">›</span><span class="loc-part">{eq.building_name}</span>{/if}
                    {#if eq.room_name}<span class="loc-sep">›</span><span class="loc-part">{eq.room_name}</span>{/if}
                  {:else}
                    <span class="muted">—</span>
                  {/if}
                </td>
                <td><span class="source-tag">{eq.source}</span></td>
                <td>{eq.last_user || '—'}</td>
                <td class="actions-col">
                  <button class="btn-icon" title="Modifier" on:click={() => openEdit(eq)}>✏️</button>
                  <button class="btn-icon danger" title="Supprimer" on:click={() => confirmDelete = eq}>🗑️</button>
                </td>
              </tr>
            {/each}
            {#if filteredEquipment.length === 0}
              <tr><td colspan="9" class="empty-row">Aucun équipement trouvé</td></tr>
            {/if}
          </tbody>
        </table>
      </div>
    {/if}
  </div>
</div>

{:else}
<!-- ── Audit Tab (Smart) ──────────────────────────────────── -->
<div class="audit-section">
  {#if !auditLoaded}
    <div class="loading">Chargement audit…</div>
  {:else if auditData}
    <!-- Summary bar -->
    <div class="audit-summary">
      <div class="audit-stat-card compliance">
        <div class="audit-pct">{auditData.summary.compliance_percent}%</div>
        <div class="audit-pct-bar"><div class="audit-pct-fill" style="width:{auditData.summary.compliance_percent}%"></div></div>
        <span class="audit-stat-label">Conformit{'\u00e9'}</span>
      </div>
      <div class="audit-stat-card">
        <span class="audit-stat-value">{auditData.summary.total_checked}</span>
        <span class="audit-stat-label">V{'\u00e9'}rifi{'\u00e9'}s</span>
      </div>
      <div class="audit-stat-card ok-card">
        <span class="audit-stat-value">{auditData.summary.compliant}</span>
        <span class="audit-stat-label">Conformes</span>
      </div>
      <div class="audit-stat-card warn-card" class:has-issues={auditData.summary.warnings > 0}>
        <span class="audit-stat-value">{auditData.summary.warnings}</span>
        <span class="audit-stat-label">Avertissements</span>
      </div>
      <div class="audit-stat-card crit-card" class:has-issues={auditData.summary.critical > 0}>
        <span class="audit-stat-value">{auditData.summary.critical}</span>
        <span class="audit-stat-label">Critiques</span>
      </div>
      <button class="btn-rules" on:click={() => showRulesPanel = !showRulesPanel}>
        {'\u2699\uFE0F'} R{'\u00e8'}gles
      </button>
    </div>

    <!-- Rules panel (collapsible) -->
    {#if showRulesPanel}
      <div class="rules-panel">
        <h3>{'\u{1F4CB}'} R{'\u00e8'}gles d'audit par type</h3>
        <p class="rules-help">Cochez les champs obligatoires pour chaque type d'{'\u00e9'}quipement. L'audit v{'\u00e9'}rifiera que ces champs sont renseign{'\u00e9'}s.</p>
        <div class="rules-table-wrap">
          <table class="rules-table">
            <thead>
              <tr>
                <th>Type</th>
                <th>Site</th>
                <th>B{'\u00e2'}timent</th>
                <th>Salle</th>
                <th>OS</th>
                <th>Utilisateur</th>
                <th title="Salle OU Utilisateur (au moins un)">Salle/User</th>
              </tr>
            </thead>
            <tbody>
              {#each Object.keys(auditRules).filter(k => k !== '_default') as type}
                <tr>
                  <td class="rule-type">{type}</td>
                  <td><input type="checkbox" bind:checked={auditRules[type].site} /></td>
                  <td><input type="checkbox" bind:checked={auditRules[type].building} /></td>
                  <td><input type="checkbox" bind:checked={auditRules[type].room} /></td>
                  <td><input type="checkbox" bind:checked={auditRules[type].os} /></td>
                  <td><input type="checkbox" bind:checked={auditRules[type].user} /></td>
                  <td><input type="checkbox" bind:checked={auditRules[type].room_or_user} /></td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
        <div class="rules-actions">
          <button class="btn-secondary" on:click={resetAuditRules}>R{'\u00e9'}initialiser</button>
          <button class="btn-primary" on:click={saveAuditRules} disabled={savingRules}>
            {savingRules ? 'Sauvegarde...' : 'Sauvegarder'}
          </button>
        </div>
      </div>
    {/if}

    <!-- Issues list -->
    {#if auditData.issues.length === 0}
      <div class="audit-all-ok">
        <span class="audit-ok-icon">{'\u2705'}</span>
        <h3>Tous les {'\u00e9'}quipements sont conformes !</h3>
        <p>Aucune anomalie d{'\u00e9'}tect{'\u00e9'}e selon vos r{'\u00e8'}gles d'audit.</p>
      </div>
    {:else}
      <div class="filters-bar" style="margin-top:16px">
        <select class="filter-select" bind:value={auditFilterType}>
          <option value="">— Tous les types —</option>
          {#each auditEquipTypes as t}<option value={t}>{t}</option>{/each}
        </select>
        <select class="filter-select" bind:value={auditFilterSeverity}>
          <option value="">— Toutes s{'\u00e9'}v{'\u00e9'}rit{'\u00e9'}s —</option>
          <option value="critical">{'\u{1F534}'} Critique</option>
          <option value="warning">{'\u{1F7E1}'} Avertissement</option>
        </select>
        <span class="result-count">{filteredAuditIssues.length} probl{'\u00e8'}me{filteredAuditIssues.length !== 1 ? 's' : ''}</span>
      </div>

      <div class="table-wrapper" style="margin-top:8px">
        <table>
          <thead>
            <tr>
              <th>S{'\u00e9'}v{'\u00e9'}rit{'\u00e9'}</th>
              <th>Hostname</th>
              <th>Type</th>
              <th>Champs manquants</th>
              <th>Localisation actuelle</th>
              <th>Utilisateur</th>
              <th class="actions-col">Action</th>
            </tr>
          </thead>
          <tbody>
            {#each filteredAuditIssues as issue}
              <tr>
                <td>
                  {#if issue.severity === 'critical'}
                    <span class="severity-badge critical">{'\u{1F534}'} Critique</span>
                  {:else}
                    <span class="severity-badge warning">{'\u{1F7E1}'} Avertissement</span>
                  {/if}
                </td>
                <td class="hostname">{issue.hostname}</td>
                <td><span class="type-badge">{issue.equip_type}</span></td>
                <td>
                  <div class="missing-tags">
                    {#each issue.missing as m}
                      <span class="missing-tag">{missingLabel(m)}</span>
                    {/each}
                  </div>
                </td>
                <td class="loc-cell">
                  {#if issue.site_name}
                    {issue.site_name}
                    {#if issue.building_name} › {issue.building_name}{/if}
                    {#if issue.room_name} › {issue.room_name}{/if}
                  {:else}
                    <span class="muted">—</span>
                  {/if}
                </td>
                <td>{issue.last_user || '—'}</td>
                <td class="actions-col">
                  <button class="btn-icon" title="Modifier"
                    on:click={() => { const eq = equipment.find(e => e.id === issue.id); if (eq) openEdit(eq); }}>
                    {'\u270F\uFE0F'}
                  </button>
                </td>
              </tr>
            {/each}
            {#if filteredAuditIssues.length === 0}
              <tr><td colspan="7" class="empty-row">Aucun probl{'\u00e8'}me avec ces filtres</td></tr>
            {/if}
          </tbody>
        </table>
      </div>
    {/if}
  {/if}
</div>
{/if}

<!-- ── Equipment Dialog ───────────────────────────────────── -->
{#if showDialog}
<div class="dialog-overlay" on:click|self={() => showDialog = false}>
  <div class="dialog">
    <div class="dialog-header">
      <h2>{editingEquipment ? 'Modifier' : 'Ajouter'} un équipement</h2>
      <button class="btn-close" on:click={() => showDialog = false}>×</button>
    </div>
    <div class="dialog-body">
      <div class="form-row">
        <label>Hostname<input type="text" bind:value={form.hostname} /></label>
        <label>Type
          <select bind:value={form.equip_type}>
            <option value="PC">PC</option>
            <option value="Portable">Portable</option>
            <option value="Imprimante">Imprimante</option>
            <option value="Switch">Switch</option>
            <option value="AP Wi-Fi">AP Wi-Fi</option>
            <option value="Serveur">Serveur</option>
            <option value="Écran">Écran</option>
            <option value="Autre">Autre</option>
          </select>
        </label>
      </div>
      <div class="form-row">
        <label>OS<input type="text" bind:value={form.os} /></label>
        <label>N° Série<input type="text" bind:value={form.serial_number} /></label>
      </div>
      <div class="form-row">
        <label>Marque<input type="text" bind:value={form.brand} /></label>
        <label>Modèle<input type="text" bind:value={form.model} /></label>
      </div>
      <div class="form-row triple">
        <label>Site
          <select bind:value={form.site_id} on:change={onSiteChange}>
            <option value={null}>— Aucun —</option>
            {#each sites as s}<option value={s.id}>{s.code || s.name}</option>{/each}
          </select>
        </label>
        <label>Bâtiment
          <select bind:value={form.building_id} on:change={onBuildingChange} disabled={!form.site_id}>
            <option value={null}>— Aucun —</option>
            {#each dialogBuildings as b}<option value={b.id}>{b.name}</option>{/each}
          </select>
        </label>
        <label>Salle
          <select bind:value={form.room_id} disabled={!form.building_id}>
            <option value={null}>— Aucune —</option>
            {#each dialogRooms as r}<option value={r.id}>{r.name}</option>{/each}
          </select>
        </label>
      </div>
      <div class="form-row">
        <label>Source
          <select bind:value={form.source}>
            <option value="manual">Manuel</option>
            <option value="glpi">GLPI</option>
            <option value="ad_admin">AD Admin</option>
            <option value="ad_pedago_ndk">AD Pédago NDK</option>
            <option value="ad_pedago_su">AD Pédago SU</option>
          </select>
        </label>
      </div>
      <div class="form-row">
        <label>Date d'achat<input type="date" bind:value={form.purchase_date} /></label>
        <label>Fin garantie<input type="date" bind:value={form.warranty_end} /></label>
      </div>
      <label class="full-width">Notes<textarea bind:value={form.notes} rows="3"></textarea></label>
    </div>
    <div class="dialog-footer">
      <button class="btn-secondary" on:click={() => showDialog = false}>Annuler</button>
      <button class="btn-primary" on:click={saveEquipment} disabled={saving || !form.hostname}>
        {saving ? 'Enregistrement…' : 'Enregistrer'}
      </button>
    </div>
  </div>
</div>
{/if}

<!-- ── Delete Confirm ─────────────────────────────────────── -->
{#if confirmDelete}
<div class="dialog-overlay" on:click|self={() => confirmDelete = null}>
  <div class="dialog small">
    <div class="dialog-header">
      <h2>Supprimer</h2>
      <button class="btn-close" on:click={() => confirmDelete = null}>×</button>
    </div>
    <div class="dialog-body">
      <p>Supprimer <strong>{confirmDelete.hostname}</strong> ?</p>
    </div>
    <div class="dialog-footer">
      <button class="btn-secondary" on:click={() => confirmDelete = null}>Annuler</button>
      <button class="btn-danger" on:click={deleteEquipment} disabled={deleting}>
        {deleting ? 'Suppression…' : 'Supprimer'}
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
    margin-bottom: 16px;
  }
  .title-row h1 { font-size: 1.5rem; font-weight: 700; color: #fff; margin: 0; }

  .stats-row {
    display: flex; gap: 12px; flex-wrap: wrap;
  }
  .stat-card {
    background: var(--bg-card, rgba(255,255,255,0.06));
    border: 1px solid var(--border-subtle, rgba(255,255,255,0.08));
    border-radius: 12px; padding: 14px 20px;
    text-align: center; min-width: 100px;
    backdrop-filter: blur(12px);
  }
  .stat-card.accent { border-color: var(--accent, #6C63FF); }
  .stat-value { display: block; font-size: 1.5rem; font-weight: 700; color: #fff; }
  .stat-label { font-size: 0.75rem; color: rgba(255,255,255,0.5); text-transform: uppercase; letter-spacing: 0.05em; }

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
  .badge {
    background: var(--accent, #6C63FF); color: #fff;
    border-radius: 10px; padding: 1px 7px; font-size: 0.7rem;
    margin-left: 6px; vertical-align: middle;
  }

  /* ── Inventory layout ───────────────────────────────────── */
  .inventory-layout { display: flex; gap: 16px; min-height: 500px; }

  /* ── Tree Sidebar ───────────────────────────────────────── */
  .tree-sidebar {
    width: 260px; min-width: 260px;
    background: var(--bg-card, rgba(255,255,255,0.06));
    border: 1px solid var(--border-subtle, rgba(255,255,255,0.08));
    border-radius: 14px; padding: 14px;
    backdrop-filter: blur(16px); overflow-y: auto; max-height: 70vh;
    box-shadow: 0 4px 20px rgba(0,0,0,0.1);
  }
  .tree-header {
    display: flex; align-items: center; gap: 6px;
    margin-bottom: 12px; padding-bottom: 10px;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    font-size: 0.9rem; color: rgba(255,255,255,0.7);
  }
  .tree-header-icon { font-size: 1rem; }
  .tree-header strong { flex: 1; letter-spacing: 0.3px; }
  .btn-clear {
    background: none; border: none; color: var(--accent, #6C63FF);
    cursor: pointer; font-size: 0.75rem; opacity: 0.8;
  }
  .btn-clear:hover { opacity: 1; text-decoration: underline; }
  .tree-list { display: flex; flex-direction: column; gap: 2px; }
  .tree-item {
    display: flex; align-items: center; gap: 6px; width: 100%;
    background: none; border: none; color: rgba(255,255,255,0.75);
    padding: 6px 8px; border-radius: 8px; cursor: pointer;
    font-size: 0.82rem; text-align: left; transition: all 0.15s;
    border: 1px solid transparent; font-family: inherit;
  }
  .tree-item:hover {
    background: rgba(255,255,255,0.05);
    border-color: rgba(255,255,255,0.06);
  }
  .tree-item.selected {
    background: rgba(108,99,255,0.15); color: #fff;
    border-color: rgba(108,99,255,0.3);
    box-shadow: 0 0 8px rgba(108,99,255,0.1);
  }
  .tree-toggle {
    width: 16px; display: flex; align-items: center; justify-content: center;
    flex-shrink: 0; color: rgba(255,255,255,0.35);
  }
  .chevron { transition: transform 0.2s ease; }
  .chevron.open { transform: rotate(90deg); }
  .tree-ico { font-size: 0.85rem; flex-shrink: 0; line-height: 1; }
  .tree-label { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 500; }
  .tree-count {
    font-size: 0.68rem; color: rgba(var(--accent-rgb, 108,99,255), 0.8);
    background: rgba(var(--accent-rgb, 108,99,255), 0.1);
    border-radius: 10px; padding: 2px 7px; font-weight: 600;
    min-width: 22px; text-align: center;
  }
  .site-level { font-weight: 600; }
  .tree-children {
    margin-left: 12px; padding-left: 10px;
    border-left: 1px solid rgba(255,255,255,0.06);
  }
  .building-level .tree-label { font-weight: 500; }
  .room-level { padding-left: 24px; }
  .room-level .tree-label { font-weight: 400; color: rgba(255,255,255,0.65); }

  /* ── Main content ───────────────────────────────────────── */
  .main-content { flex: 1; min-width: 0; }

  .filters-bar {
    display: flex; gap: 10px; align-items: center; margin-bottom: 12px; flex-wrap: wrap;
  }
  .search-input {
    flex: 1; min-width: 200px; padding: 8px 14px;
    background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.1);
    border-radius: 8px; color: #fff; font-size: 0.85rem;
  }
  .search-input::placeholder { color: rgba(255,255,255,0.3); }
  .filter-select {
    padding: 8px 12px;
    background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.1);
    border-radius: 8px; color: #fff; font-size: 0.85rem;
  }
  .filter-select option { background: #1e1e2e; color: #fff; }
  .result-count { font-size: 0.8rem; color: rgba(255,255,255,0.4); white-space: nowrap; }

  /* ── Table ──────────────────────────────────────────────── */
  .table-wrapper {
    background: var(--bg-card, rgba(255,255,255,0.06));
    border: 1px solid var(--border-subtle, rgba(255,255,255,0.08));
    border-radius: 12px; overflow: auto; max-height: 60vh;
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
  .os-cell { max-width: 160px; overflow: hidden; text-overflow: ellipsis; }
  .type-badge {
    background: rgba(108,99,255,0.2); color: var(--accent, #6C63FF);
    border-radius: 6px; padding: 2px 8px; font-size: 0.75rem; font-weight: 600;
  }
  .source-tag {
    background: rgba(255,255,255,0.06); border-radius: 6px;
    padding: 2px 8px; font-size: 0.75rem;
  }
  .loc-cell { max-width: 220px; overflow: hidden; text-overflow: ellipsis; }
  .loc-sep { color: rgba(255,255,255,0.3); margin: 0 2px; }
  .loc-part { }
  .muted { color: rgba(255,255,255,0.3); }
  .actions-col { width: 80px; text-align: center; }
  .empty-row { text-align: center; color: rgba(255,255,255,0.3); padding: 32px !important; }
  .loading { text-align: center; color: rgba(255,255,255,0.4); padding: 40px; }

  .btn-icon {
    background: none; border: none; cursor: pointer; font-size: 0.9rem;
    padding: 4px; border-radius: 6px; transition: background 0.15s;
  }
  .btn-icon:hover { background: rgba(255,255,255,0.08); }

  /* ── Audit (Smart) ──────────────────────────────────────── */
  .audit-summary {
    display: flex; gap: 10px; align-items: stretch; flex-wrap: wrap; margin-bottom: 16px;
  }
  .audit-stat-card {
    background: var(--bg-card, rgba(255,255,255,0.06));
    border: 1px solid var(--border-subtle, rgba(255,255,255,0.08));
    border-radius: 12px; padding: 12px 18px; text-align: center;
    min-width: 100px; backdrop-filter: blur(12px);
    display: flex; flex-direction: column; justify-content: center; gap: 4px;
  }
  .audit-stat-card.compliance { min-width: 140px; }
  .audit-stat-card.ok-card { border-color: rgba(34,197,94,0.3); }
  .audit-stat-card.warn-card.has-issues { border-color: #F59E0B; background: rgba(245,158,11,0.06); }
  .audit-stat-card.crit-card.has-issues { border-color: #EF4444; background: rgba(239,68,68,0.06); }
  .audit-stat-value { font-size: 1.4rem; font-weight: 700; color: #fff; }
  .audit-stat-label { font-size: 0.7rem; color: rgba(255,255,255,0.45); text-transform: uppercase; letter-spacing: 0.05em; }
  .audit-pct { font-size: 1.6rem; font-weight: 800; color: #22C55E; }
  .audit-pct-bar {
    height: 5px; background: rgba(255,255,255,0.08); border-radius: 4px;
    overflow: hidden; margin: 4px 0;
  }
  .audit-pct-fill {
    height: 100%; background: linear-gradient(90deg, #22C55E, #4ADE80);
    border-radius: 4px; transition: width 0.5s ease;
  }
  .btn-rules {
    background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.1);
    border-radius: 10px; padding: 10px 16px; cursor: pointer;
    color: rgba(255,255,255,0.7); font-size: 0.85rem; font-family: inherit;
    transition: all 0.15s; display: flex; align-items: center; gap: 6px;
  }
  .btn-rules:hover { background: rgba(255,255,255,0.1); color: #fff; }

  /* Rules panel */
  .rules-panel {
    background: var(--bg-card, rgba(255,255,255,0.06));
    border: 1px solid var(--border-subtle, rgba(255,255,255,0.08));
    border-radius: 12px; padding: 20px; margin-bottom: 16px;
    backdrop-filter: blur(12px);
  }
  .rules-panel h3 { margin: 0 0 6px; font-size: 1rem; color: #fff; }
  .rules-help { font-size: 0.8rem; color: rgba(255,255,255,0.45); margin: 0 0 14px; }
  .rules-table-wrap { overflow-x: auto; }
  .rules-table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
  .rules-table th {
    padding: 8px 10px; text-align: center; color: rgba(255,255,255,0.5);
    font-weight: 600; font-size: 0.75rem; text-transform: uppercase;
    border-bottom: 1px solid rgba(255,255,255,0.08);
  }
  .rules-table th:first-child { text-align: left; }
  .rules-table td { padding: 6px 10px; text-align: center; border-bottom: 1px solid rgba(255,255,255,0.04); }
  .rules-table td:first-child { text-align: left; }
  .rule-type { font-weight: 600; color: #fff; }
  .rules-table input[type="checkbox"] { width: 16px; height: 16px; accent-color: var(--accent, #6C63FF); cursor: pointer; }
  .rules-actions { display: flex; gap: 10px; justify-content: flex-end; margin-top: 14px; }

  /* Severity badges */
  .severity-badge {
    border-radius: 6px; padding: 3px 8px; font-size: 0.72rem; font-weight: 600;
  }
  .severity-badge.critical { background: rgba(239,68,68,0.15); color: #EF4444; }
  .severity-badge.warning { background: rgba(245,158,11,0.15); color: #F59E0B; }

  /* Missing tags */
  .missing-tags { display: flex; gap: 4px; flex-wrap: wrap; }
  .missing-tag {
    background: rgba(239,68,68,0.1); color: #F87171;
    border-radius: 5px; padding: 2px 7px; font-size: 0.7rem; font-weight: 500;
    white-space: nowrap;
  }

  /* All OK state */
  .audit-all-ok {
    text-align: center; padding: 60px 20px;
    color: rgba(255,255,255,0.6);
  }
  .audit-ok-icon { font-size: 3rem; display: block; margin-bottom: 12px; }
  .audit-all-ok h3 { color: #22C55E; margin: 0 0 8px; font-size: 1.2rem; }
  .audit-all-ok p { margin: 0; font-size: 0.9rem; }

  /* ── Dialog ─────────────────────────────────────────────── */
  .dialog-overlay {
    position: fixed; inset: 0; background: rgba(0,0,0,0.6);
    display: flex; align-items: center; justify-content: center; z-index: 100;
    backdrop-filter: blur(4px);
  }
  .dialog {
    background: var(--bg-dialog, #1e1e2e);
    border: 1px solid var(--border-subtle, rgba(255,255,255,0.12));
    border-radius: 16px; width: 640px; max-width: 95vw;
    max-height: 90vh; overflow-y: auto;
    box-shadow: 0 20px 60px rgba(0,0,0,0.5);
  }
  .dialog.small { width: 400px; }
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
  .dialog-footer {
    display: flex; justify-content: flex-end; gap: 10px;
    padding: 14px 24px; border-top: 1px solid rgba(255,255,255,0.08);
  }

  .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 12px; }
  .form-row.triple { grid-template-columns: 1fr 1fr 1fr; }
  .full-width { display: block; margin-bottom: 12px; }
  label { display: flex; flex-direction: column; gap: 4px; font-size: 0.82rem; color: rgba(255,255,255,0.6); }
  input, select, textarea {
    padding: 8px 12px; background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.1); border-radius: 8px;
    color: #fff; font-size: 0.85rem; font-family: inherit;
  }
  input:focus, select:focus, textarea:focus {
    outline: none; border-color: var(--accent, #6C63FF);
  }
  select option { background: #1e1e2e; color: #fff; }
  textarea { resize: vertical; }

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
    border-radius: 8px; padding: 8px 20px; cursor: pointer; font-size: 0.85rem;
    font-weight: 600;
  }
  .btn-danger:disabled { opacity: 0.5; cursor: not-allowed; }

  /* ── Header actions ──────────────────────────────────────── */
  .header-actions {
    display: flex; gap: 8px; align-items: center;
  }
  .btn-sync {
    background: rgba(34,197,94,0.15); color: #22C55E;
    border: 1px solid rgba(34,197,94,0.3); border-radius: 8px;
    padding: 8px 14px; cursor: pointer; font-size: 0.82rem;
    font-weight: 600; transition: all 0.2s;
  }
  .btn-sync:hover { background: rgba(34,197,94,0.25); }
  .btn-sync:disabled { opacity: 0.5; cursor: not-allowed; }
  .sync-info {
    font-size: 0.72rem; color: rgba(255,255,255,0.4);
    white-space: nowrap;
  }
</style>
