<script>
  import { onMount } from 'svelte';
  import { api } from '../api/client.js';
  import { success, error as toastError } from '../stores/toast.js';

  const API_BASE = 'http://localhost:8010';

  // ── State ──────────────────────────────────────────────────
  let suppliers = [];
  let domains = [];
  let loading = true;

  // Filters
  let searchQuery = '';
  let filterDomain = '';

  // Supplier dialog
  let showSupplierDialog = false;
  let editingSupplier = null;
  let form = defaultForm();
  let logoFile = null;
  let logoPreview = null;
  let fileInputEl;
  let saving = false;

  // Domain management dialog
  let showDomainDialog = false;
  let domainEdits = [];
  let newDomain = { name: '', color_hex: '#64748B', icon_key: '', sort_order: 0 };

  // Delete confirmation
  let confirmDeleteSupplier = null;
  let deleting = false;

  // Logo error tracking
  let logoErrors = {};

  // Detail panel
  let selectedSupplier = null;
  let supplierDocuments = [];
  let loadingDocs = false;

  async function openDetail(s) {
    selectedSupplier = s;
    loadingDocs = true;
    try {
      const docs = await api.get('/api/documents');
      // Find documents linked to this supplier
      supplierDocuments = docs.filter(d => d.supplier_id === s.id);
    } catch { supplierDocuments = []; }
    loadingDocs = false;
  }

  function closeDetail() {
    selectedSupplier = null;
    supplierDocuments = [];
  }

  // ── Helpers ────────────────────────────────────────────────
  function defaultForm() {
    return { name: '', domain: '', phone: '', email: '', contact: '', notes: '' };
  }

  function getInitials(name) {
    if (!name) return '??';
    const parts = name.trim().split(/\s+/);
    if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
    return name.slice(0, 2).toUpperCase();
  }

  function getDomainColor(domainName) {
    const d = domains.find(dm => dm.name === domainName);
    return d ? (d.color_hex || '#64748B') : '#64748B';
  }

  function copyToClipboard(text, label) {
    navigator.clipboard.writeText(text).then(() => {
      success(label + ' copié');
    }).catch(() => {
      toastError('Erreur copie');
    });
  }

  // ── Derived ────────────────────────────────────────────────
  $: filteredSuppliers = suppliers.filter(s => {
    if (filterDomain && s.domain !== filterDomain) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      const fields = [s.name, s.domain, s.phone, s.email, s.contact, s.notes].filter(Boolean);
      if (!fields.some(f => f.toLowerCase().includes(q))) return false;
    }
    return true;
  });

  $: totalCount = suppliers.length;

  $: domainCounts = (() => {
    const counts = {};
    suppliers.forEach(s => {
      if (s.domain) counts[s.domain] = (counts[s.domain] || 0) + 1;
    });
    return counts;
  })();

  // Group filtered suppliers by domain
  $: groupedSuppliers = (() => {
    const groups = {};
    filteredSuppliers.forEach(s => {
      const key = s.domain || 'Autre';
      if (!groups[key]) groups[key] = [];
      groups[key].push(s);
    });
    const sorted = Object.entries(groups).sort((a, b) => {
      const da = domains.find(d => d.name === a[0]);
      const db = domains.find(d => d.name === b[0]);
      return (da?.sort_order || 999) - (db?.sort_order || 999);
    });
    return sorted;
  })();

  $: domainList = [...new Set(suppliers.map(s => s.domain).filter(Boolean))].sort();

  // ── Data loading ───────────────────────────────────────────
  async function loadSuppliers() {
    try { suppliers = await api.get('/api/suppliers'); } catch (e) { toastError('Erreur chargement prestataires'); }
  }
  async function loadDomains() {
    try { domains = await api.get('/api/suppliers/domains'); } catch (e) { toastError('Erreur chargement domaines'); }
  }

  onMount(async () => {
    await Promise.all([loadSuppliers(), loadDomains()]);
    loading = false;
  });

  // ── CRUD ───────────────────────────────────────────────────
  function openNew() {
    editingSupplier = null;
    form = defaultForm();
    logoFile = null;
    logoPreview = null;
    showSupplierDialog = true;
  }
  function openEdit(s) {
    editingSupplier = s;
    form = { name: s.name, domain: s.domain, phone: s.phone, email: s.email, contact: s.contact, notes: s.notes };
    logoFile = null;
    logoPreview = s.logo_path ? `${API_BASE}/api/suppliers/${s.id}/logo` : null;
    showSupplierDialog = true;
  }

  async function saveSupplier() {
    if (!form.name.trim()) return;
    saving = true;
    try {
      let supplier;
      if (editingSupplier) {
        supplier = await api.put(`/api/suppliers/${editingSupplier.id}`, form);
      } else {
        supplier = await api.post('/api/suppliers', form);
      }
      if (logoFile) {
        const fd = new FormData();
        fd.append('file', logoFile);
        await fetch(`${API_BASE}/api/suppliers/${supplier.id}/logo`, { method: 'POST', body: fd });
      }
      success(editingSupplier ? 'Prestataire modifié' : 'Prestataire ajouté');
      showSupplierDialog = false;
      await loadSuppliers();
    } catch (e) { toastError('Erreur : ' + e.message); }
    saving = false;
  }

  async function deleteSupplier() {
    if (!confirmDeleteSupplier) return;
    deleting = true;
    try {
      await api.delete(`/api/suppliers/${confirmDeleteSupplier.id}`);
      success('Prestataire supprimé');
      confirmDeleteSupplier = null;
      await loadSuppliers();
    } catch (e) { toastError('Erreur : ' + e.message); }
    deleting = false;
  }

  function onLogoChange(e) {
    const f = e.target.files?.[0];
    if (!f) return;
    logoFile = f;
    logoPreview = URL.createObjectURL(f);
  }

  // ── Domain management ──────────────────────────────────────
  function openDomainManager() {
    domainEdits = domains.map(d => ({ ...d }));
    newDomain = { name: '', color_hex: '#64748B', icon_key: '', sort_order: 0 };
    showDomainDialog = true;
  }

  async function addDomain() {
    if (!newDomain.name.trim()) return;
    try {
      await api.post('/api/suppliers/domains', newDomain);
      await loadDomains();
      domainEdits = domains.map(d => ({ ...d }));
      newDomain = { name: '', color_hex: '#64748B', icon_key: '', sort_order: 0 };
      success('Domaine ajouté');
    } catch (e) { toastError('Erreur : ' + e.message); }
  }

  async function saveDomain(d) {
    try {
      await api.put(`/api/suppliers/domains/${d.id}`, { name: d.name, color_hex: d.color_hex, icon_key: d.icon_key, sort_order: d.sort_order });
      await loadDomains();
      success('Domaine mis à jour');
    } catch (e) { toastError('Erreur : ' + e.message); }
  }

  async function deleteDomain(d) {
    try {
      await api.delete(`/api/suppliers/domains/${d.id}`);
      await loadDomains();
      domainEdits = domains.map(dm => ({ ...dm }));
      success('Domaine supprimé');
    } catch (e) { toastError('Erreur : ' + e.message); }
  }
</script>

<!-- ── Stats Bar ──────────────────────────────────────────── -->
<div class="page-header">
  <div class="title-row">
    <h1>Prestataires</h1>
    <div class="header-actions">
      <button class="btn-ghost" on:click={openDomainManager}>⚙️ Domaines</button>
      <button class="btn-primary" on:click={openNew}>+ Ajouter</button>
    </div>
  </div>

  <div class="stats-bar">
    <div class="stat-chip total">
      <span class="chip-count">{totalCount}</span>
      <span class="chip-label">Total</span>
    </div>
    {#each Object.entries(domainCounts).sort((a,b) => b[1] - a[1]) as [dName, dCount]}
      <button class="stat-chip"
              style="background: {getDomainColor(dName)}22; border-color: {getDomainColor(dName)}44; color: {getDomainColor(dName)}"
              class:active={filterDomain === dName}
              on:click={() => filterDomain = filterDomain === dName ? '' : dName}>
        <span class="chip-count">{dCount}</span>
        <span class="chip-label">{dName}</span>
      </button>
    {/each}
  </div>
</div>

<!-- ── Filter Bar ─────────────────────────────────────────── -->
<div class="filters-bar">
  <select class="filter-select" bind:value={filterDomain}>
    <option value="">— Tous domaines —</option>
    {#each domainList as d}<option value={d}>{d}</option>{/each}
  </select>
  <input type="text" class="search-input" placeholder="Rechercher nom, contact, tel, email…"
         bind:value={searchQuery} />
  <span class="result-count">{filteredSuppliers.length} résultat{filteredSuppliers.length !== 1 ? 's' : ''}</span>
</div>

<!-- ── Supplier List (grouped by domain) ──────────────────── -->
{#if loading}
  <div class="loading">Chargement…</div>
{:else if filteredSuppliers.length === 0}
  <div class="empty-state">
    <span class="empty-icon">📇</span>
    <p>Aucun prestataire trouvé</p>
  </div>
{:else}
  <div class="supplier-list">
    {#each groupedSuppliers as [domainName, group]}
      <!-- Domain Section Header -->
      <div class="domain-section-header" style="border-left-color: {getDomainColor(domainName)}">
        <span class="domain-header-dot" style="background: {getDomainColor(domainName)}"></span>
        <span class="domain-header-name">{domainName}</span>
        <span class="domain-header-count" style="background: {getDomainColor(domainName)}22; color: {getDomainColor(domainName)}">{group.length}</span>
        <div class="domain-header-line" style="background: {getDomainColor(domainName)}33"></div>
      </div>

      <!-- Supplier Rows -->
      {#each group as s (s.id)}
        <div class="supplier-row" class:selected-row={selectedSupplier?.id === s.id} on:click={() => openDetail(s)} role="button" tabindex="0">
          <!-- Avatar -->
          <div class="avatar" style="border-color: {getDomainColor(s.domain)}">
            {#if s.logo_path && !logoErrors[s.id]}
              <img src="{API_BASE}/api/suppliers/{s.id}/logo"
                   alt=""
                   on:error={() => { logoErrors[s.id] = true; logoErrors = logoErrors; }} />
            {:else}
              <span class="initials" style="background: {getDomainColor(s.domain)}33; color: {getDomainColor(s.domain)}">{getInitials(s.name)}</span>
            {/if}
          </div>

          <!-- Info -->
          <div class="supplier-info">
            <span class="supplier-name">{s.name}</span>
            <span class="supplier-meta">
              {#if s.contact}<span class="meta-item">👤 {s.contact}</span>{/if}
              {#if s.phone}<span class="meta-item">📞 {s.phone}</span>{/if}
              {#if s.email}<span class="meta-item">✉️ {s.email}</span>{/if}
            </span>
          </div>

          <!-- Domain badge -->
          <span class="domain-badge" style="background: {getDomainColor(s.domain)}22; color: {getDomainColor(s.domain)}; border-color: {getDomainColor(s.domain)}44">
            {s.domain}
          </span>

          <!-- Actions -->
          <div class="row-actions" on:click|stopPropagation>
            {#if s.email}
              <button class="btn-action" title="Copier email" on:click|stopPropagation={() => copyToClipboard(s.email, 'Email')}>✉️</button>
            {/if}
            {#if s.phone}
              <button class="btn-action" title="Copier téléphone" on:click|stopPropagation={() => copyToClipboard(s.phone, 'Téléphone')}>📞</button>
            {/if}
            <button class="btn-action danger" title="Supprimer" on:click|stopPropagation={() => confirmDeleteSupplier = s}>🗑️</button>
          </div>
        </div>
      {/each}
    {/each}
  </div>
{/if}

<!-- ── Detail Panel (slide-in) ─────────────────────────────── -->
{#if selectedSupplier}
  {@const s = selectedSupplier}
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="detail-overlay" on:click={closeDetail}>
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="detail-panel" on:click|stopPropagation>
      <div class="detail-header">
        <div class="detail-avatar" style="border-color: {getDomainColor(s.domain)}">
          {#if s.logo_path && !logoErrors[s.id]}
            <img src="{API_BASE}/api/suppliers/{s.id}/logo" alt="" on:error={() => { logoErrors[s.id] = true; logoErrors = logoErrors; }} />
          {:else}
            <span class="detail-initials" style="background: {getDomainColor(s.domain)}33; color: {getDomainColor(s.domain)}">{getInitials(s.name)}</span>
          {/if}
        </div>
        <div class="detail-title">
          <h2>{s.name}</h2>
          <span class="domain-badge" style="background: {getDomainColor(s.domain)}22; color: {getDomainColor(s.domain)}; border-color: {getDomainColor(s.domain)}44">{s.domain || 'Autre'}</span>
        </div>
        <div class="detail-header-actions">
          <button class="btn-action" on:click={() => { closeDetail(); openEdit(s); }} title="Modifier">{'\u270F\uFE0F'}</button>
          <button class="btn-close-detail" on:click={closeDetail}>{'\u2715'}</button>
        </div>
      </div>

      <div class="detail-body">
        <!-- Contact info -->
        <div class="detail-section">
          <h3>{'\u{1F4CB}'} Coordonn{'\u00e9'}es</h3>
          <div class="detail-fields">
            {#if s.contact}
              <div class="detail-field">
                <span class="df-icon">{'\u{1F464}'}</span>
                <span class="df-label">Contact</span>
                <span class="df-value">{s.contact}</span>
              </div>
            {/if}
            {#if s.phone}
              <div class="detail-field clickable" on:click={() => copyToClipboard(s.phone, 'T\u00e9l\u00e9phone')}>
                <span class="df-icon">{'\u{1F4DE}'}</span>
                <span class="df-label">T{'\u00e9'}l{'\u00e9'}phone</span>
                <span class="df-value">{s.phone}</span>
                <span class="df-copy">{'\u{1F4CB}'}</span>
              </div>
            {/if}
            {#if s.email}
              <div class="detail-field clickable" on:click={() => copyToClipboard(s.email, 'Email')}>
                <span class="df-icon">{'\u2709\uFE0F'}</span>
                <span class="df-label">Email</span>
                <span class="df-value">{s.email}</span>
                <span class="df-copy">{'\u{1F4CB}'}</span>
              </div>
            {/if}
            {#if !s.contact && !s.phone && !s.email}
              <p class="detail-empty">Aucune coordonn{'\u00e9'}e renseign{'\u00e9'}e</p>
            {/if}
          </div>
        </div>

        <!-- Notes -->
        {#if s.notes}
          <div class="detail-section">
            <h3>{'\u{1F4DD}'} Notes</h3>
            <p class="detail-notes">{s.notes}</p>
          </div>
        {/if}

        <!-- Documents liés -->
        <div class="detail-section">
          <h3>{'\u{1F4C4}'} Documents li{'\u00e9'}s</h3>
          {#if loadingDocs}
            <p class="detail-empty">Chargement...</p>
          {:else if supplierDocuments.length > 0}
            <div class="detail-docs">
              {#each supplierDocuments as doc}
                <div class="detail-doc-row">
                  <span class="doc-type-badge">{doc.doc_type}</span>
                  <span class="doc-title">{doc.title}</span>
                  {#if doc.doc_date}
                    <span class="doc-date">{new Date(doc.doc_date).toLocaleDateString('fr-FR')}</span>
                  {/if}
                </div>
              {/each}
            </div>
          {:else}
            <p class="detail-empty">Aucun document li{'\u00e9'} {'\u00e0'} ce prestataire</p>
          {/if}
        </div>

        <!-- Metadata -->
        <div class="detail-section detail-meta-section">
          <span class="detail-meta">{'\u{1F4C5}'} Ajout{'\u00e9'} le {s.created_at ? new Date(s.created_at).toLocaleDateString('fr-FR') : '—'}</span>
        </div>
      </div>
    </div>
  </div>
{/if}

<!-- ── Supplier Dialog ────────────────────────────────────── -->
{#if showSupplierDialog}
<div class="dialog-overlay" on:click|self={() => showSupplierDialog = false}>
  <div class="dialog">
    <div class="dialog-header">
      <h2>{editingSupplier ? 'Modifier le prestataire' : 'Nouveau prestataire'}</h2>
      <button class="btn-close" on:click={() => showSupplierDialog = false}>&times;</button>
    </div>
    <div class="dialog-body">
      <div class="logo-name-row">
        <div class="logo-picker" on:click={() => fileInputEl?.click()}>
          {#if logoPreview}
            <img src={logoPreview} alt="Logo" class="logo-img" />
          {:else}
            <span class="logo-placeholder">📷</span>
          {/if}
          <input type="file" accept="image/*" bind:this={fileInputEl} on:change={onLogoChange} style="display:none" />
        </div>
        <div class="name-domain">
          <label>Nom *<input type="text" bind:value={form.name} placeholder="Nom du prestataire" /></label>
          <label>Domaine
            <select bind:value={form.domain}>
              <option value="">— Aucun —</option>
              {#each domains as d}<option value={d.name}>{d.name}</option>{/each}
            </select>
          </label>
        </div>
      </div>
      <div class="form-row">
        <label>Contact<input type="text" bind:value={form.contact} placeholder="Nom du contact" /></label>
        <label>Téléphone<input type="tel" bind:value={form.phone} placeholder="01 23 45 67 89" /></label>
      </div>
      <div class="form-row">
        <label class="full-width">Email<input type="email" bind:value={form.email} placeholder="contact@example.com" /></label>
      </div>
      <label class="full-width">Notes<textarea bind:value={form.notes} rows="3" placeholder="Notes, commentaires…"></textarea></label>
    </div>
    <div class="dialog-footer">
      <button class="btn-secondary" on:click={() => showSupplierDialog = false}>Annuler</button>
      <button class="btn-primary" on:click={saveSupplier} disabled={saving || !form.name.trim()}>
        {saving ? 'Enregistrement…' : 'Enregistrer'}
      </button>
    </div>
  </div>
</div>
{/if}

<!-- ── Delete Confirm ─────────────────────────────────────── -->
{#if confirmDeleteSupplier}
<div class="dialog-overlay" on:click|self={() => confirmDeleteSupplier = null}>
  <div class="dialog small">
    <div class="dialog-header">
      <h2>Supprimer</h2>
      <button class="btn-close" on:click={() => confirmDeleteSupplier = null}>&times;</button>
    </div>
    <div class="dialog-body">
      <p>Supprimer <strong>{confirmDeleteSupplier.name}</strong> ?</p>
    </div>
    <div class="dialog-footer">
      <button class="btn-secondary" on:click={() => confirmDeleteSupplier = null}>Annuler</button>
      <button class="btn-danger" on:click={deleteSupplier} disabled={deleting}>
        {deleting ? 'Suppression…' : 'Supprimer'}
      </button>
    </div>
  </div>
</div>
{/if}

<!-- ── Domain Manager Dialog ──────────────────────────────── -->
{#if showDomainDialog}
<div class="dialog-overlay" on:click|self={() => showDomainDialog = false}>
  <div class="dialog wide">
    <div class="dialog-header">
      <h2>Gestion des domaines</h2>
      <button class="btn-close" on:click={() => showDomainDialog = false}>&times;</button>
    </div>
    <div class="dialog-body">
      <div class="domain-add-row">
        <input type="text" bind:value={newDomain.name} placeholder="Nouveau domaine" class="domain-input" />
        <input type="color" bind:value={newDomain.color_hex} class="color-picker" title="Couleur" />
        <input type="number" bind:value={newDomain.sort_order} class="sort-input" min="0" max="999" title="Ordre" />
        <button class="btn-primary small" on:click={addDomain} disabled={!newDomain.name.trim()}>Ajouter</button>
      </div>
      <div class="domain-list">
        {#each domainEdits as d (d.id)}
          <div class="domain-edit-row">
            <span class="domain-color-dot" style="background: {d.color_hex}"></span>
            <input type="text" bind:value={d.name} class="domain-input" />
            <input type="color" bind:value={d.color_hex} class="color-picker" />
            <input type="number" bind:value={d.sort_order} class="sort-input" min="0" max="999" />
            <button class="btn-ghost small" on:click={() => saveDomain(d)}>💾</button>
            <button class="btn-ghost small danger" on:click={() => deleteDomain(d)}>🗑️</button>
          </div>
        {/each}
      </div>
    </div>
    <div class="dialog-footer">
      <button class="btn-secondary" on:click={() => showDomainDialog = false}>Fermer</button>
    </div>
  </div>
</div>
{/if}

<style>
  .page-header { margin-bottom: 16px; }
  .title-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
  .title-row h1 { font-size: 1.5rem; font-weight: 700; color: #fff; margin: 0; }
  .header-actions { display: flex; gap: 8px; }

  .stats-bar { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 16px; }
  .stat-chip {
    display: flex; align-items: center; gap: 6px;
    padding: 5px 12px; border-radius: 20px; font-size: 0.8rem;
    border: 1px solid transparent; cursor: pointer;
    background: rgba(255,255,255,0.06); color: rgba(255,255,255,0.7);
    transition: all 0.2s;
  }
  .stat-chip:hover { filter: brightness(1.2); }
  .stat-chip.active { filter: brightness(1.3); box-shadow: 0 0 8px rgba(255,255,255,0.1); }
  .stat-chip.total { cursor: default; }
  .chip-count { font-weight: 700; }
  .chip-label { font-weight: 500; }

  .filters-bar { display: flex; gap: 10px; align-items: center; margin-bottom: 16px; flex-wrap: wrap; }
  .search-input {
    flex: 1; min-width: 220px; padding: 8px 14px;
    background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.1);
    border-radius: 8px; color: #fff; font-size: 0.85rem;
  }
  .search-input::placeholder { color: rgba(255,255,255,0.3); }
  .filter-select {
    padding: 8px 12px; background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.1); border-radius: 8px;
    color: #fff; font-size: 0.85rem;
  }
  .filter-select option { background: #1e1e2e; color: #fff; }
  .result-count { font-size: 0.8rem; color: rgba(255,255,255,0.4); white-space: nowrap; }

  .supplier-list { display: flex; flex-direction: column; gap: 2px; }
  .domain-section-header {
    display: flex; align-items: center; gap: 10px;
    padding: 12px 16px 6px; margin-top: 8px;
    border-left: 3px solid transparent;
  }
  .domain-header-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
  .domain-header-name { font-size: 0.85rem; font-weight: 700; color: rgba(255,255,255,0.7); text-transform: uppercase; letter-spacing: 0.05em; }
  .domain-header-count { font-size: 0.7rem; font-weight: 700; border-radius: 10px; padding: 1px 8px; }
  .domain-header-line { flex: 1; height: 1px; }

  .supplier-row {
    display: flex; align-items: center; gap: 14px;
    padding: 10px 16px; border-radius: 10px;
    background: var(--bg-card, rgba(255,255,255,0.04));
    border: 1px solid transparent;
    cursor: pointer; transition: all 0.15s; width: 100%;
    text-align: left; color: inherit; font: inherit;
  }
  .supplier-row:hover { background: rgba(255,255,255,0.07); border-color: rgba(255,255,255,0.08); }

  .avatar {
    width: 48px; height: 48px; border-radius: 50%; flex-shrink: 0;
    border: 2px solid; overflow: hidden;
    display: flex; align-items: center; justify-content: center;
  }
  .avatar img { width: 100%; height: 100%; object-fit: cover; }
  .initials { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 0.85rem; }

  .supplier-info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
  .supplier-name { font-weight: 600; color: #fff; font-size: 0.92rem; }
  .supplier-meta { display: flex; gap: 12px; flex-wrap: wrap; }
  .meta-item { font-size: 0.78rem; color: rgba(255,255,255,0.5); white-space: nowrap; }

  .domain-badge {
    font-size: 0.75rem; font-weight: 600; padding: 3px 10px;
    border-radius: 12px; border: 1px solid; white-space: nowrap; flex-shrink: 0;
  }

  .row-actions { display: flex; gap: 4px; flex-shrink: 0; }
  .btn-action {
    background: rgba(255,255,255,0.06); border: none; border-radius: 6px;
    padding: 4px 8px; cursor: pointer; font-size: 0.82rem; transition: background 0.15s;
  }
  .btn-action:hover { background: rgba(255,255,255,0.12); }
  .btn-action.danger:hover { background: rgba(239,68,68,0.2); }

  .empty-state { text-align: center; padding: 60px; color: rgba(255,255,255,0.4); }
  .empty-icon { font-size: 2.5rem; display: block; margin-bottom: 12px; }
  .loading { text-align: center; color: rgba(255,255,255,0.4); padding: 40px; }

  /* ── Detail Panel ───────────────────────────────────────── */
  .selected-row { background: rgba(var(--accent-rgb, 108,99,255), 0.08) !important; border-color: rgba(var(--accent-rgb, 108,99,255), 0.2) !important; }
  .detail-overlay {
    position: fixed; inset: 0; background: rgba(0,0,0,0.4); z-index: 90;
    display: flex; justify-content: flex-end;
    backdrop-filter: blur(2px); animation: fadeIn 0.15s ease;
  }
  .detail-panel {
    width: 480px; max-width: 90vw; height: 100vh;
    background: var(--bg-card-solid, #1a1a2e); border-left: 1px solid var(--border-subtle);
    display: flex; flex-direction: column; overflow: hidden;
    animation: slideInRight 0.25s ease;
    box-shadow: -8px 0 40px rgba(0,0,0,0.3);
  }
  @keyframes slideInRight { from { transform: translateX(100%); } to { transform: translateX(0); } }
  .detail-header {
    display: flex; align-items: center; gap: 14px;
    padding: 20px 24px; border-bottom: 1px solid var(--border-subtle);
  }
  .detail-avatar {
    width: 56px; height: 56px; border-radius: 14px; border: 2px solid;
    overflow: hidden; flex-shrink: 0; display: flex; align-items: center; justify-content: center;
    background: rgba(255,255,255,0.04);
  }
  .detail-avatar img { width: 100%; height: 100%; object-fit: contain; }
  .detail-initials { font-size: 20px; font-weight: 700; }
  .detail-title { flex: 1; min-width: 0; }
  .detail-title h2 { margin: 0; font-size: 18px; font-weight: 700; color: var(--text-primary); }
  .detail-header-actions { display: flex; gap: 6px; }
  .btn-close-detail {
    background: none; border: none; color: var(--text-muted); font-size: 18px;
    cursor: pointer; padding: 4px 8px; border-radius: 6px;
  }
  .btn-close-detail:hover { background: var(--bg-hover); color: var(--text-primary); }

  .detail-body { flex: 1; overflow-y: auto; padding: 20px 24px; }
  .detail-section { margin-bottom: 22px; }
  .detail-section h3 { margin: 0 0 10px; font-size: 13px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px; }
  .detail-fields { display: flex; flex-direction: column; gap: 6px; }
  .detail-field {
    display: flex; align-items: center; gap: 10px;
    padding: 8px 12px; border-radius: 8px; background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.04);
  }
  .detail-field.clickable { cursor: pointer; transition: all 0.15s; }
  .detail-field.clickable:hover { background: rgba(255,255,255,0.06); border-color: rgba(255,255,255,0.08); }
  .df-icon { font-size: 16px; flex-shrink: 0; }
  .df-label { font-size: 11px; color: var(--text-muted); min-width: 65px; }
  .df-value { flex: 1; font-size: 13px; color: var(--text-primary); }
  .df-copy { font-size: 12px; opacity: 0; transition: opacity 0.15s; }
  .detail-field.clickable:hover .df-copy { opacity: 0.5; }

  .detail-notes { font-size: 13px; color: var(--text-secondary); line-height: 1.6; margin: 0; white-space: pre-wrap; }
  .detail-empty { font-size: 12px; color: var(--text-muted); margin: 0; }

  .detail-docs { display: flex; flex-direction: column; gap: 4px; }
  .detail-doc-row {
    display: flex; align-items: center; gap: 8px;
    padding: 6px 10px; border-radius: 6px; background: rgba(255,255,255,0.02);
    border: 1px solid rgba(255,255,255,0.04);
  }
  .doc-type-badge {
    font-size: 10px; font-weight: 600; padding: 2px 7px; border-radius: 4px;
    background: rgba(var(--accent-rgb, 108,99,255), 0.1); color: var(--accent);
    flex-shrink: 0;
  }
  .doc-title { flex: 1; font-size: 12px; color: var(--text-primary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .doc-date { font-size: 11px; color: var(--text-muted); flex-shrink: 0; }

  .detail-meta-section { border-top: 1px solid var(--border-subtle); padding-top: 12px; }
  .detail-meta { font-size: 11px; color: var(--text-muted); }

  .dialog-overlay {
    position: fixed; inset: 0; background: rgba(0,0,0,0.6);
    display: flex; align-items: center; justify-content: center; z-index: 100;
    backdrop-filter: blur(4px);
  }
  .dialog {
    background: var(--bg-dialog, #1e1e2e);
    border: 1px solid var(--border-subtle, rgba(255,255,255,0.12));
    border-radius: 16px; width: 540px; max-width: 95vw;
    max-height: 90vh; overflow-y: auto;
    box-shadow: 0 20px 60px rgba(0,0,0,0.5);
  }
  .dialog.small { width: 400px; }
  .dialog.wide { width: 640px; }
  .dialog-header {
    display: flex; justify-content: space-between; align-items: center;
    padding: 18px 24px; border-bottom: 1px solid rgba(255,255,255,0.08);
  }
  .dialog-header h2 { margin: 0; font-size: 1.1rem; color: #fff; }
  .btn-close { background: none; border: none; color: rgba(255,255,255,0.5); font-size: 1.4rem; cursor: pointer; }
  .dialog-body { padding: 20px 24px; }
  .dialog-footer {
    display: flex; justify-content: flex-end; gap: 10px;
    padding: 14px 24px; border-top: 1px solid rgba(255,255,255,0.08);
  }

  .logo-name-row { display: flex; gap: 16px; margin-bottom: 16px; }
  .logo-picker {
    width: 80px; height: 80px; border-radius: 12px; flex-shrink: 0;
    background: rgba(255,255,255,0.06); border: 2px dashed rgba(255,255,255,0.15);
    display: flex; align-items: center; justify-content: center; cursor: pointer;
    overflow: hidden; transition: border-color 0.2s;
  }
  .logo-picker:hover { border-color: var(--accent, #6C63FF); }
  .logo-img { width: 100%; height: 100%; object-fit: cover; }
  .logo-placeholder { font-size: 1.5rem; opacity: 0.4; }
  .name-domain { flex: 1; display: flex; flex-direction: column; gap: 8px; }

  .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 12px; }
  .full-width { display: block; margin-bottom: 12px; }
  label { display: flex; flex-direction: column; gap: 4px; font-size: 0.82rem; color: rgba(255,255,255,0.6); }
  input, select, textarea {
    padding: 8px 12px; background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.1); border-radius: 8px;
    color: #fff; font-size: 0.85rem; font-family: inherit;
  }
  input:focus, select:focus, textarea:focus { outline: none; border-color: var(--accent, #6C63FF); }
  select option { background: #1e1e2e; color: #fff; }
  textarea { resize: vertical; }

  .domain-add-row { display: flex; gap: 8px; align-items: center; margin-bottom: 16px; padding-bottom: 16px; border-bottom: 1px solid rgba(255,255,255,0.08); }
  .domain-input { flex: 1; min-width: 120px; }
  .color-picker { width: 36px; height: 36px; border: none; cursor: pointer; border-radius: 6px; padding: 0; background: none; }
  .sort-input { width: 60px; text-align: center; }
  .domain-list { display: flex; flex-direction: column; gap: 6px; }
  .domain-edit-row { display: flex; gap: 8px; align-items: center; }
  .domain-color-dot { width: 12px; height: 12px; border-radius: 50%; flex-shrink: 0; }

  .btn-primary {
    background: var(--accent, #6C63FF); color: #fff; border: none;
    border-radius: 8px; padding: 8px 20px; cursor: pointer; font-size: 0.85rem;
    font-weight: 600; transition: opacity 0.2s;
  }
  .btn-primary:hover { opacity: 0.9; }
  .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
  .btn-primary.small { padding: 6px 14px; font-size: 0.8rem; }
  .btn-secondary {
    background: rgba(255,255,255,0.08); color: rgba(255,255,255,0.8);
    border: 1px solid rgba(255,255,255,0.1); border-radius: 8px;
    padding: 8px 20px; cursor: pointer; font-size: 0.85rem;
  }
  .btn-danger {
    background: #EF4444; color: #fff; border: none;
    border-radius: 8px; padding: 8px 20px; cursor: pointer; font-size: 0.85rem; font-weight: 600;
  }
  .btn-danger:disabled { opacity: 0.5; cursor: not-allowed; }
  .btn-ghost {
    background: rgba(255,255,255,0.06); color: rgba(255,255,255,0.7);
    border: 1px solid rgba(255,255,255,0.08); border-radius: 8px;
    padding: 8px 14px; cursor: pointer; font-size: 0.85rem;
  }
  .btn-ghost:hover { background: rgba(255,255,255,0.1); }
  .btn-ghost.small { padding: 4px 10px; font-size: 0.82rem; }
  .btn-ghost.danger:hover { background: rgba(239,68,68,0.2); }
</style>
