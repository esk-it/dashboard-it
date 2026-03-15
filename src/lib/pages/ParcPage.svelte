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

  // Audit data
  let auditNoSite = [];
  let auditNoRoom = [];
  let auditStaleAd = [];
  let auditWarranty = [];
  let auditLoaded = false;

  // Equipment dialog
  let showDialog = false;
  let editingEquipment = null;
  let form = defaultForm();
  let saving = false;

  // Delete
  let confirmDelete = null;
  let deleting = false;

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
  onMount(() => { loadAll(); });

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

  async function loadAudit() {
    try {
      const [ns, nr, sa, wa] = await Promise.all([
        api.get('/api/parc/audit/no-site'),
        api.get('/api/parc/audit/no-room'),
        api.get('/api/parc/audit/stale-ad'),
        api.get('/api/parc/audit/warranty'),
      ]);
      auditNoSite = ns;
      auditNoRoom = nr;
      auditStaleAd = sa;
      auditWarranty = wa;
      auditLoaded = true;
    } catch (e) {
      toastError('Erreur chargement audit : ' + e.message);
    }
  }

  function switchTab(tab) {
    activeTab = tab;
    if (tab === 'audit' && !auditLoaded) loadAudit();
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
</script>

<!-- ── KPI Stats ──────────────────────────────────────────── -->
<div class="page-header">
  <div class="title-row">
    <h1>Parc Informatique</h1>
    <button class="btn-primary" on:click={openNew}>+ Ajouter</button>
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
    {#if auditLoaded}
      <span class="badge">{auditNoSite.length + auditNoRoom.length + auditStaleAd.length + auditWarranty.length}</span>
    {/if}
  </button>
</div>

{#if activeTab === 'inventory'}
<!-- ── Inventory Tab ──────────────────────────────────────── -->
<div class="inventory-layout">
  <!-- Sidebar Tree -->
  <aside class="tree-sidebar">
    <div class="tree-header">
      <strong>Sites</strong>
      {#if selectedSiteId || selectedBuildingId || selectedRoomId}
        <button class="btn-clear" on:click={clearTreeFilter}>Effacer</button>
      {/if}
    </div>
    {#each sites as site}
      <div class="tree-node">
        <button class="tree-item site-item"
                class:selected={selectedSiteId === site.id}
                on:click={() => selectSite(site.id)}>
          <span class="tree-toggle" on:click|stopPropagation={() => toggleSite(site.id)}>
            {expandedSites[site.id] ? '▾' : '▸'}
          </span>
          <span class="tree-label">{site.code || site.name}</span>
          <span class="tree-count">{countBySite(site.id)}</span>
        </button>
        {#if expandedSites[site.id] && buildings[site.id]}
          {#each buildings[site.id] as building}
            <div class="tree-node indent-1">
              <button class="tree-item"
                      class:selected={selectedBuildingId === building.id}
                      on:click={() => selectBuilding(building.id)}>
                <span class="tree-toggle" on:click|stopPropagation={() => toggleBuilding(building.id)}>
                  {expandedBuildings[building.id] ? '▾' : '▸'}
                </span>
                <span class="tree-label">{building.name}</span>
                <span class="tree-count">{countByBuilding(building.id)}</span>
              </button>
              {#if expandedBuildings[building.id] && rooms[building.id]}
                {#each rooms[building.id] as room}
                  <div class="tree-node indent-2">
                    <button class="tree-item"
                            class:selected={selectedRoomId === room.id}
                            on:click={() => selectRoom(room.id)}>
                      <span class="tree-label">{room.name}</span>
                      <span class="tree-count">{countByRoom(room.id)}</span>
                    </button>
                  </div>
                {/each}
              {/if}
            </div>
          {/each}
        {/if}
      </div>
    {/each}
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
              <th>Dernier vu AD</th>
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
                <td>{eq.last_seen_ad || '—'}</td>
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
<!-- ── Audit Tab ──────────────────────────────────────────── -->
<div class="audit-section">
  {#if !auditLoaded}
    <div class="loading">Chargement audit…</div>
  {:else}
    <div class="audit-grid">
      <div class="audit-card" class:warning={auditNoSite.length > 0}>
        <h3>Sans site <span class="badge">{auditNoSite.length}</span></h3>
        {#if auditNoSite.length > 0}
          <ul>{#each auditNoSite as eq}<li>{eq.hostname}</li>{/each}</ul>
        {:else}<p class="ok">Aucun</p>{/if}
      </div>
      <div class="audit-card" class:warning={auditNoRoom.length > 0}>
        <h3>Sans salle <span class="badge">{auditNoRoom.length}</span></h3>
        {#if auditNoRoom.length > 0}
          <ul>{#each auditNoRoom.slice(0, 20) as eq}<li>{eq.hostname}</li>{/each}
          {#if auditNoRoom.length > 20}<li class="muted">… et {auditNoRoom.length - 20} autres</li>{/if}</ul>
        {:else}<p class="ok">Aucun</p>{/if}
      </div>
      <div class="audit-card" class:warning={auditStaleAd.length > 0}>
        <h3>Inactifs AD &gt; 30j <span class="badge">{auditStaleAd.length}</span></h3>
        {#if auditStaleAd.length > 0}
          <ul>{#each auditStaleAd.slice(0, 20) as eq}<li>{eq.hostname} <span class="muted">({eq.last_seen_ad})</span></li>{/each}
          {#if auditStaleAd.length > 20}<li class="muted">… et {auditStaleAd.length - 20} autres</li>{/if}</ul>
        {:else}<p class="ok">Tous actifs</p>{/if}
      </div>
      <div class="audit-card" class:warning={auditWarranty.length > 0}>
        <h3>Garantie &lt; 6 mois <span class="badge">{auditWarranty.length}</span></h3>
        {#if auditWarranty.length > 0}
          <ul>{#each auditWarranty as eq}<li>{eq.hostname} <span class="muted">({eq.warranty_end})</span></li>{/each}</ul>
        {:else}<p class="ok">Aucune alerte</p>{/if}
      </div>
    </div>
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
    width: 240px; min-width: 240px;
    background: var(--bg-card, rgba(255,255,255,0.06));
    border: 1px solid var(--border-subtle, rgba(255,255,255,0.08));
    border-radius: 12px; padding: 12px;
    backdrop-filter: blur(12px); overflow-y: auto; max-height: 70vh;
  }
  .tree-header {
    display: flex; justify-content: space-between; align-items: center;
    margin-bottom: 10px; font-size: 0.85rem; color: rgba(255,255,255,0.6);
  }
  .btn-clear {
    background: none; border: none; color: var(--accent, #6C63FF);
    cursor: pointer; font-size: 0.75rem;
  }
  .tree-item {
    display: flex; align-items: center; gap: 4px; width: 100%;
    background: none; border: none; color: rgba(255,255,255,0.8);
    padding: 5px 6px; border-radius: 6px; cursor: pointer;
    font-size: 0.82rem; text-align: left; transition: background 0.15s;
  }
  .tree-item:hover { background: rgba(255,255,255,0.06); }
  .tree-item.selected { background: rgba(108,99,255,0.2); color: #fff; }
  .tree-toggle { width: 16px; text-align: center; font-size: 0.75rem; flex-shrink: 0; }
  .tree-label { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .tree-count {
    font-size: 0.7rem; color: rgba(255,255,255,0.35);
    background: rgba(255,255,255,0.06); border-radius: 8px; padding: 1px 6px;
  }
  .indent-1 { padding-left: 16px; }
  .indent-2 { padding-left: 32px; }

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

  /* ── Audit ──────────────────────────────────────────────── */
  .audit-grid {
    display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px;
  }
  .audit-card {
    background: var(--bg-card, rgba(255,255,255,0.06));
    border: 1px solid var(--border-subtle, rgba(255,255,255,0.08));
    border-radius: 12px; padding: 16px; backdrop-filter: blur(12px);
  }
  .audit-card.warning { border-color: #F59E0B; }
  .audit-card h3 { margin: 0 0 10px; font-size: 0.95rem; color: #fff; }
  .audit-card ul { list-style: none; padding: 0; margin: 0; max-height: 250px; overflow-y: auto; }
  .audit-card li { padding: 3px 0; font-size: 0.82rem; color: rgba(255,255,255,0.75); }
  .audit-card .ok { color: #22C55E; font-size: 0.85rem; }

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
</style>
