<script>
  import { onMount, onDestroy } from 'svelte';
  import '@xterm/xterm/css/xterm.css';

  const API = 'http://localhost:8010/api/bastion';
  const WS_BASE = 'ws://localhost:8010/api/bastion';

  let groups = [];
  let servers = [];
  let stats = null;
  let selectedGroup = '';
  let protocolFilter = '';
  let search = '';
  let loading = true;

  // Sessions / tabs
  let sessions = []; // { id, server, ws, status, termEl, type: 'ssh'|'rdp' }
  let activeSessionIdx = -1;

  // RDP password prompt
  let showRdpPasswordDialog = false;
  let rdpPasswordServer = null;
  let rdpPassword = '';

  // Dialogs
  let showServerDialog = false;
  let editingServer = null;
  let showGroupDialog = false;
  let showDeleteConfirm = false;
  let deletingServer = null;

  // Server form
  let form = { name: '', hostname: '', port: 22, username: '', protocol: 'SSH', group_name: '', notes: '', ssh_key_path: '' };

  // Ping states
  let pingStates = {}; // server_id -> { alive, ms, loading }

  // Group colors map
  $: groupColors = Object.fromEntries(groups.map(g => [g.name, g.color_hex]));

  // Filtered servers
  $: filteredServers = servers.filter(s => {
    if (selectedGroup && s.group_name !== selectedGroup) return false;
    if (protocolFilter && s.protocol !== protocolFilter) return false;
    if (search) {
      const q = search.toLowerCase();
      if (!s.name.toLowerCase().includes(q) && !s.hostname.toLowerCase().includes(q) &&
          !s.username.toLowerCase().includes(q)) return false;
    }
    return true;
  });

  // Grouped servers for display
  $: groupedServers = (() => {
    const map = {};
    for (const s of filteredServers) {
      const g = s.group_name || '(sans groupe)';
      if (!map[g]) map[g] = [];
      map[g].push(s);
    }
    // Sort groups by sort_order
    const ordered = groups.map(g => g.name).filter(n => map[n]);
    if (map['(sans groupe)']) ordered.push('(sans groupe)');
    return ordered.map(name => ({ name, servers: map[name] || [] }));
  })();

  onMount(async () => {
    await loadData();
  });

  onDestroy(() => {
    // Close all WebSocket sessions
    for (const sess of sessions) {
      if (sess.ws) {
        try { sess.ws.close(); } catch(e) {}
      }
    }
  });

  async function loadData() {
    loading = true;
    try {
      const [gRes, sRes, stRes] = await Promise.all([
        fetch(`${API}/groups`), fetch(`${API}/servers`), fetch(`${API}/stats`),
      ]);
      groups = await gRes.json();
      servers = await sRes.json();
      stats = await stRes.json();
    } catch (e) { console.error(e); }
    loading = false;
  }

  async function loadServers() {
    try {
      const res = await fetch(`${API}/servers`);
      servers = await res.json();
    } catch(e) {}
  }

  // ── Server CRUD ──────────────────────────────────────────────────────────

  function openAddServer(groupName = '') {
    editingServer = null;
    form = { name: '', hostname: '', port: 22, username: '', protocol: 'SSH', group_name: groupName, notes: '', ssh_key_path: '' };
    showServerDialog = true;
  }

  function openEditServer(server) {
    editingServer = server;
    form = { ...server };
    showServerDialog = true;
  }

  async function saveServer() {
    const url = editingServer ? `${API}/servers/${editingServer.id}` : `${API}/servers`;
    const method = editingServer ? 'PUT' : 'POST';
    await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(form) });
    showServerDialog = false;
    await loadData();
  }

  function confirmDelete(server) {
    deletingServer = server;
    showDeleteConfirm = true;
  }

  async function doDelete() {
    if (!deletingServer) return;
    await fetch(`${API}/servers/${deletingServer.id}`, { method: 'DELETE' });
    showDeleteConfirm = false;
    deletingServer = null;
    await loadData();
  }

  // ── Protocol change ────────────────────────────────────────────────────

  function onProtocolChange() {
    if (form.port === 22 && form.protocol === 'RDP') form.port = 3389;
    else if (form.port === 3389 && form.protocol === 'SSH') form.port = 22;
  }

  // ── Ping ─────────────────────────────────────────────────────────────────

  async function pingServer(serverId) {
    pingStates[serverId] = { alive: false, ms: 0, loading: true };
    pingStates = pingStates;
    try {
      const res = await fetch(`${API}/ping/${serverId}`, { method: 'POST' });
      const data = await res.json();
      pingStates[serverId] = { alive: data.alive, ms: data.latency_ms, loading: false };
    } catch(e) {
      pingStates[serverId] = { alive: false, ms: 0, loading: false };
    }
    pingStates = pingStates;
  }

  async function pingAll() {
    const ids = filteredServers.map(s => s.id);
    for (const id of ids) {
      pingStates[id] = { alive: false, ms: 0, loading: true };
    }
    pingStates = pingStates;
    try {
      const res = await fetch(`${API}/ping`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ server_ids: ids }),
      });
      const results = await res.json();
      for (const r of results) {
        pingStates[r.server_id] = { alive: r.alive, ms: r.latency_ms, loading: false };
      }
    } catch(e) {
      for (const id of ids) {
        pingStates[id] = { alive: false, ms: 0, loading: false };
      }
    }
    pingStates = pingStates;
  }

  // ── Connect (SSH integrated / RDP integrated or external) ──────────────────

  function connectServer(server) {
    if (server.protocol === 'SSH') {
      openSSHSession(server);
    } else {
      // RDP: prompt for password then launch mstsc natively
      rdpPasswordServer = server;
      rdpPassword = '';
      showRdpPasswordDialog = true;
    }
  }

  async function connectRDPWithPassword() {
    if (!rdpPasswordServer) return;
    showRdpPasswordDialog = false;
    await launchRDP(rdpPasswordServer, rdpPassword);
    rdpPasswordServer = null;
    rdpPassword = '';
  }

  async function launchRDP(server, password) {
    try {
      const res = await fetch(`${API}/rdp-launch/${server.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password }),
      });
      const data = await res.json();
      if (!data.ok) throw new Error(data.detail || 'Erreur');
    } catch(e) {
      alert(`Erreur lancement RDP: ${e.message}`);
    }
  }

  // ── RDP Setup actions ───────────────────────────────────────────────

  function openSSHSession(server) {
    // Check if already open
    const existing = sessions.findIndex(s => s.id === server.id);
    if (existing >= 0) {
      activeSessionIdx = existing;
      return;
    }

    const session = {
      id: server.id,
      server,
      ws: null,
      status: 'connecting',
      term: null,
      fitAddon: null,
    };
    sessions = [...sessions, session];
    activeSessionIdx = sessions.length - 1;

    // Connect WebSocket after DOM renders
    setTimeout(() => initSSHTerminal(sessions.length - 1), 100);
  }

  async function initSSHTerminal(idx) {
    const session = sessions[idx];
    if (!session) return;

    // Dynamic import xterm.js
    const { Terminal } = await import('@xterm/xterm');
    const { FitAddon } = await import('@xterm/addon-fit');

    const termEl = document.getElementById(`terminal-${session.id}`);
    if (!termEl) return;

    const term = new Terminal({
      cursorBlink: true,
      fontSize: 14,
      fontFamily: "'Cascadia Code','Fira Code','Consolas',monospace",
      theme: {
        background: '#0D1117',
        foreground: '#C9D1D9',
        cursor: '#58A6FF',
        selectionBackground: '#264F78',
        black: '#484F58',
        red: '#FF7B72',
        green: '#3FB950',
        yellow: '#D29922',
        blue: '#58A6FF',
        magenta: '#BC8CFF',
        cyan: '#39D2E0',
        white: '#B1BAC4',
      },
    });
    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);
    term.open(termEl);
    fitAddon.fit();

    term.writeln('\x1b[90mConnexion en cours...\x1b[0m');

    // WebSocket
    const ws = new WebSocket(`${WS_BASE}/ssh/${session.id}`);

    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data);
      if (msg.type === 'data') {
        term.write(msg.data);
      } else if (msg.type === 'status') {
        if (msg.data === 'connected') {
          term.writeln('\x1b[32m\u2713 Connect\u00e9\x1b[0m\r\n');
          updateSessionStatus(session.id, 'connected');
          fitAddon.fit();
          ws.send(JSON.stringify({ type: 'resize', cols: term.cols, rows: term.rows }));
        } else if (msg.data === 'connecting') {
          updateSessionStatus(session.id, 'connecting');
        }
      } else if (msg.type === 'error') {
        term.writeln(`\r\n\x1b[31m\u2717 ${msg.data}\x1b[0m`);
        updateSessionStatus(session.id, 'error');
      }
    };

    ws.onclose = () => {
      term.writeln('\r\n\x1b[33m\u23FB D\u00e9connect\u00e9\x1b[0m');
      updateSessionStatus(session.id, 'disconnected');
    };

    ws.onerror = () => {
      updateSessionStatus(session.id, 'error');
    };

    // Terminal input -> WebSocket
    term.onData((data) => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'data', data }));
      }
    });

    // Resize observer
    const ro = new ResizeObserver(() => {
      fitAddon.fit();
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'resize', cols: term.cols, rows: term.rows }));
      }
    });
    ro.observe(termEl);

    // Update session
    sessions[idx] = { ...session, ws, term, fitAddon };
    sessions = sessions;
  }

  function updateSessionStatus(serverId, status) {
    sessions = sessions.map(s => s.id === serverId ? { ...s, status } : s);
  }

  function closeSession(idx) {
    const session = sessions[idx];
    if (session.ws) {
      try { session.ws.close(); } catch(e) {}
    }
    if (session.term) {
      try { session.term.dispose(); } catch(e) {}
    }
    sessions = sessions.filter((_, i) => i !== idx);
    if (activeSessionIdx >= sessions.length) activeSessionIdx = sessions.length - 1;
    if (sessions.length === 0) activeSessionIdx = -1;
  }

  // ── Clipboard ──────────────────────────────────────────────────────────────

  function copySSHCommand(server) {
    const port = server.port !== 22 ? ` -p ${server.port}` : '';
    const user = server.username ? `${server.username}@` : '';
    const cmd = `ssh${port} ${user}${server.hostname}`;
    navigator.clipboard.writeText(cmd);
  }

  // ── Groups dialog ─────────────────────────────────────────────────────────

  let newGroupName = '';
  let newGroupColor = '#4B8BFF';

  async function addGroup() {
    if (!newGroupName.trim()) return;
    await fetch(`${API}/groups`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: newGroupName.trim(), color_hex: newGroupColor }),
    });
    newGroupName = '';
    newGroupColor = '#4B8BFF';
    await loadData();
  }

  async function deleteGroup(id) {
    await fetch(`${API}/groups/${id}`, { method: 'DELETE' });
    await loadData();
  }

  // Refit terminal when switching tabs
  function switchTab(idx) {
    activeSessionIdx = idx;
    setTimeout(() => {
      const session = sessions[idx];
      if (session && session.fitAddon) {
        session.fitAddon.fit();
      }
    }, 50);
  }
</script>

<div class="bastion-page">
  <!-- Header -->
  <div class="page-header">
    <div class="header-left">
      <h1>{'\u{1F50C}'} Bastion</h1>
      {#if stats}
        <div class="stats-chips">
          <span class="chip">{stats.total} serveurs</span>
          <span class="chip ssh">SSH {stats.ssh_count}</span>
          <span class="chip rdp">RDP {stats.rdp_count}</span>
        </div>
      {/if}
    </div>
    <div class="header-actions">
      <span class="gateway-indicator gw-on" title="RDP via mstsc natif">
        <span class="gw-dot"></span>
        RDP Natif
      </span>
      <button class="btn-icon" on:click={pingAll} title="Ping tous les serveurs">
        {'\u{1F4E1}'} Ping All
      </button>
      <button class="btn-icon" on:click={() => showGroupDialog = true} title="G\u00e9rer les groupes">
        {'\u{1F3F7}\uFE0F'} Groupes
      </button>
      <button class="btn-primary" on:click={() => openAddServer()}>
        + Nouveau serveur
      </button>
    </div>
  </div>


  <div class="bastion-layout">
    <!-- LEFT: Server list -->
    <div class="server-panel" class:collapsed={sessions.length > 0 && activeSessionIdx >= 0}>
      <!-- Filters -->
      <div class="filters-bar">
        <input type="text" placeholder="Rechercher..." bind:value={search} class="search-input" />
        <div class="filter-chips">
          <button class="filter-chip" class:active={!selectedGroup} on:click={() => selectedGroup = ''}>Tous</button>
          {#each groups as g}
            <button class="filter-chip" class:active={selectedGroup === g.name}
              on:click={() => selectedGroup = selectedGroup === g.name ? '' : g.name}
              style="--chip-color: {g.color_hex}">
              <span class="chip-dot" style="background:{g.color_hex}"></span>
              {g.name}
              <span class="chip-count">{g.server_count}</span>
            </button>
          {/each}
        </div>
        <div class="protocol-filter">
          <button class:active={!protocolFilter} on:click={() => protocolFilter = ''}>Tous</button>
          <button class:active={protocolFilter === 'SSH'} on:click={() => protocolFilter = protocolFilter === 'SSH' ? '' : 'SSH'}>SSH</button>
          <button class:active={protocolFilter === 'RDP'} on:click={() => protocolFilter = protocolFilter === 'RDP' ? '' : 'RDP'}>RDP</button>
        </div>
      </div>

      <!-- Server list -->
      <div class="server-list">
        {#if loading}
          <div class="empty-state">Chargement...</div>
        {:else if filteredServers.length === 0}
          <div class="empty-state">
            <div class="empty-icon">{'\u{1F50C}'}</div>
            <div>Aucun serveur</div>
            <button class="btn-primary" on:click={() => openAddServer()}>+ Ajouter un serveur</button>
          </div>
        {:else}
          {#each groupedServers as group}
            <div class="group-section">
              <div class="group-header">
                <span class="group-dot" style="background:{groupColors[group.name] || '#64748B'}"></span>
                <span class="group-name">{group.name}</span>
                <span class="group-count">{group.servers.length}</span>
                <div class="group-line"></div>
                <button class="btn-add-small" on:click={() => openAddServer(group.name)} title="Ajouter dans ce groupe">+</button>
              </div>
              {#each group.servers as server}
                <div class="server-row" role="button" tabindex="0"
                  on:click={() => connectServer(server)}
                  on:keydown={(e) => e.key === 'Enter' && connectServer(server)}>
                  <!-- Ping dot -->
                  <span class="ping-dot"
                    class:alive={pingStates[server.id]?.alive}
                    class:dead={pingStates[server.id] && !pingStates[server.id]?.alive && !pingStates[server.id]?.loading}
                    class:pinging={pingStates[server.id]?.loading}
                    on:click|stopPropagation={() => pingServer(server.id)}
                    title={pingStates[server.id]?.alive ? `${pingStates[server.id].ms} ms` : 'Cliquer pour tester'}>
                    {'\u2B24'}
                  </span>
                  <!-- Protocol badge -->
                  <span class="proto-badge" class:ssh={server.protocol === 'SSH'} class:rdp={server.protocol === 'RDP'}>
                    {server.protocol}
                  </span>
                  <!-- Info -->
                  <div class="server-info">
                    <div class="server-name">{server.name}</div>
                    <div class="server-meta">{server.hostname} {'\u00B7'} {server.username || '\u2014'}</div>
                  </div>
                  <!-- Actions (on hover) -->
                  <div class="server-actions">
                    {#if server.protocol === 'SSH'}
                      <button class="action-btn" on:click|stopPropagation={() => copySSHCommand(server)} title="Copier commande SSH">
                        {'\u{1F4CB}'}
                      </button>
                    {/if}
                    <button class="action-btn" on:click|stopPropagation={() => openEditServer(server)} title="Modifier">
                      {'\u270F\uFE0F'}
                    </button>
                    <button class="action-btn danger" on:click|stopPropagation={() => confirmDelete(server)} title="Supprimer">
                      {'\u{1F5D1}\uFE0F'}
                    </button>
                    <button class="action-btn connect" on:click|stopPropagation={() => connectServer(server)} title="Connecter">
                      {'\u26A1'}
                    </button>
                  </div>
                </div>
              {/each}
            </div>
          {/each}
        {/if}
      </div>
    </div>

    <!-- RIGHT: Terminal area -->
    {#if sessions.length > 0}
      <div class="terminal-panel">
        <!-- Session tabs -->
        <div class="session-tabs">
          {#each sessions as session, idx}
            <div class="session-tab" class:active={activeSessionIdx === idx}
              role="button" tabindex="0"
              on:click={() => switchTab(idx)}
              on:keydown={(e) => e.key === 'Enter' && switchTab(idx)}>
              <span class="tab-status"
                class:connected={session.status === 'connected'}
                class:connecting={session.status === 'connecting'}
                class:error={session.status === 'error' || session.status === 'disconnected'}>
                {'\u2B24'}
              </span>
              <span class="tab-proto" class:ssh={session.server.protocol === 'SSH'} class:rdp={session.server.protocol === 'RDP'}>
                {session.server.protocol}
              </span>
              {session.server.name}
              <span class="tab-close" role="button" tabindex="0"
                on:click|stopPropagation={() => closeSession(idx)}
                on:keydown|stopPropagation={(e) => e.key === 'Enter' && closeSession(idx)}>{'\u2715'}</span>
            </div>
          {/each}
        </div>
        <!-- Terminal content -->
        <div class="terminal-content">
          {#each sessions as session, idx}
            <div class="terminal-wrapper" class:visible={activeSessionIdx === idx}>
              <div id="terminal-{session.id}" class="xterm-container"></div>
            </div>
          {/each}
        </div>
      </div>
    {/if}
  </div>
</div>

<!-- Server Dialog -->
{#if showServerDialog}
  <div class="dialog-overlay" on:click={() => showServerDialog = false} role="presentation">
    <div class="dialog" on:click|stopPropagation role="presentation">
      <h2>{editingServer ? 'Modifier le serveur' : 'Nouveau serveur'}</h2>
      <div class="form-grid">
        <label>
          <span>Nom</span>
          <input type="text" bind:value={form.name} placeholder="Serveur web prod" />
        </label>
        <label>
          <span>H{'\u00f4'}te</span>
          <input type="text" bind:value={form.hostname} placeholder="192.168.1.100" />
        </label>
        <label>
          <span>Protocole</span>
          <select bind:value={form.protocol} on:change={onProtocolChange}>
            <option value="SSH">SSH</option>
            <option value="RDP">RDP</option>
          </select>
        </label>
        <label>
          <span>Port</span>
          <input type="number" bind:value={form.port} min="1" max="65535" />
        </label>
        <label>
          <span>Utilisateur</span>
          <input type="text" bind:value={form.username} placeholder="admin" />
        </label>
        <label>
          <span>Groupe</span>
          <select bind:value={form.group_name}>
            <option value="">(aucun)</option>
            {#each groups as g}
              <option value={g.name}>{g.name}</option>
            {/each}
          </select>
        </label>
        {#if form.protocol === 'SSH'}
          <label class="full-width">
            <span>Cl{'\u00e9'} SSH (chemin)</span>
            <input type="text" bind:value={form.ssh_key_path} placeholder="C:\Users\...\.ssh\id_rsa" />
          </label>
        {/if}
        <label class="full-width">
          <span>Notes</span>
          <textarea bind:value={form.notes} rows="2" placeholder="Notes libres..."></textarea>
        </label>
      </div>
      <div class="dialog-actions">
        <button class="btn-secondary" on:click={() => showServerDialog = false}>Annuler</button>
        <button class="btn-primary" on:click={saveServer}>
          {editingServer ? 'Enregistrer' : 'Cr\u00e9er'}
        </button>
      </div>
    </div>
  </div>
{/if}

<!-- Delete Confirmation -->
{#if showDeleteConfirm}
  <div class="dialog-overlay" on:click={() => showDeleteConfirm = false} role="presentation">
    <div class="dialog dialog-small" on:click|stopPropagation role="presentation">
      <h2>Supprimer le serveur</h2>
      <p>Supprimer {'\u00ab'} {deletingServer?.name} {'\u00bb'} ?</p>
      <div class="dialog-actions">
        <button class="btn-secondary" on:click={() => showDeleteConfirm = false}>Annuler</button>
        <button class="btn-danger" on:click={doDelete}>Supprimer</button>
      </div>
    </div>
  </div>
{/if}

<!-- Groups Dialog -->
{#if showGroupDialog}
  <div class="dialog-overlay" on:click={() => showGroupDialog = false} role="presentation">
    <div class="dialog" on:click|stopPropagation role="presentation">
      <h2>G{'\u00e9'}rer les groupes</h2>
      <div class="group-list">
        {#each groups as g}
          <div class="group-item">
            <span class="group-dot" style="background:{g.color_hex}"></span>
            <span class="group-item-name">{g.name}</span>
            <span class="group-item-count">({g.server_count})</span>
            <button class="btn-delete-small" on:click={() => deleteGroup(g.id)}>{'\u2715'}</button>
          </div>
        {/each}
      </div>
      <div class="add-group-row">
        <input type="text" bind:value={newGroupName} placeholder="Nouveau groupe..." />
        <input type="color" bind:value={newGroupColor} class="color-picker" />
        <button class="btn-primary" on:click={addGroup}>Ajouter</button>
      </div>
      <div class="dialog-actions">
        <button class="btn-secondary" on:click={() => showGroupDialog = false}>Fermer</button>
      </div>
    </div>
  </div>
{/if}

<!-- RDP Password Dialog -->
{#if showRdpPasswordDialog}
  <div class="dialog-overlay" on:click={() => showRdpPasswordDialog = false} role="presentation">
    <div class="dialog dialog-small" on:click|stopPropagation role="presentation">
      <h2>{'\u{1F512}'} Connexion RDP</h2>
      <p class="rdp-dialog-server">{rdpPasswordServer?.name} ({rdpPasswordServer?.hostname})</p>
      <div class="rdp-dialog-form">
        <label>
          <span>Utilisateur</span>
          <input type="text" value={rdpPasswordServer?.username || ''} disabled class="dialog-input" />
        </label>
        <label>
          <span>Mot de passe</span>
          <input type="password" bind:value={rdpPassword} class="dialog-input"
            placeholder="Mot de passe Windows"
            on:keydown={(e) => e.key === 'Enter' && connectRDPWithPassword()} />
        </label>
      </div>
      <div class="dialog-actions">
        <button class="btn-secondary" on:click={() => showRdpPasswordDialog = false}>Annuler</button>
        <button class="btn-primary" on:click={connectRDPWithPassword}>
          {'\u{1F50C}'} Connecter
        </button>
      </div>
    </div>
  </div>
{/if}


<style>
  .bastion-page {
    display: flex;
    flex-direction: column;
    height: calc(100vh - 56px);
    gap: 12px;
  }

  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-shrink: 0;
  }

  .header-left {
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

  .stats-chips {
    display: flex;
    gap: 8px;
  }

  .chip {
    background: var(--bg-card, rgba(13,24,42,0.7));
    border: 1px solid var(--border-subtle, rgba(255,255,255,0.06));
    border-radius: 12px;
    padding: 2px 10px;
    font-size: 0.75rem;
    color: var(--text-dim, #94A3B8);
  }
  .chip.ssh { color: #58A6FF; }
  .chip.rdp { color: #BC8CFF; }

  .header-actions {
    display: flex;
    gap: 8px;
    align-items: center;
  }

  .gateway-indicator {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    border-radius: 8px;
    font-size: 0.7rem;
    font-weight: 600;
    background: rgba(239,68,68,0.1);
    border: 1px solid rgba(239,68,68,0.2);
    color: #EF4444;
    cursor: pointer;
    transition: all 0.15s;
  }
  .gateway-indicator:hover { opacity: 0.85; }
  .gateway-indicator.gw-on {
    background: rgba(16,185,129,0.1);
    border-color: rgba(16,185,129,0.2);
    color: #10B981;
    cursor: default;
  }
  .gw-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #EF4444;
  }
  .gw-on .gw-dot { background: #10B981; }
  .gw-dot.pulsing { background: #F59E0B; animation: pulse 1s infinite; }

  .btn-icon {
    background: var(--bg-card, rgba(13,24,42,0.7));
    border: 1px solid var(--border-subtle, rgba(255,255,255,0.06));
    border-radius: 8px;
    padding: 6px 12px;
    color: var(--text-dim, #94A3B8);
    cursor: pointer;
    font-size: 0.8rem;
    transition: all 0.15s;
  }
  .btn-icon:hover { background: rgba(255,255,255,0.05); color: var(--text, #E6EAF2); }

  .btn-primary {
    background: var(--accent, #06A6C9);
    border: none;
    border-radius: 8px;
    padding: 6px 16px;
    color: #fff;
    cursor: pointer;
    font-size: 0.85rem;
    font-weight: 600;
    transition: opacity 0.15s;
  }
  .btn-primary:hover { opacity: 0.85; }

  .btn-secondary {
    background: var(--bg-card, rgba(13,24,42,0.7));
    border: 1px solid var(--border-subtle, rgba(255,255,255,0.06));
    border-radius: 8px;
    padding: 6px 16px;
    color: var(--text-dim, #94A3B8);
    cursor: pointer;
    font-size: 0.85rem;
    transition: all 0.15s;
  }
  .btn-secondary:hover { background: rgba(255,255,255,0.05); }

  .btn-danger {
    background: #991B1B;
    border: none;
    border-radius: 8px;
    padding: 6px 16px;
    color: #FCA5A5;
    cursor: pointer;
    font-size: 0.85rem;
    font-weight: 600;
  }
  .btn-danger:hover { background: #B91C1C; }

  /* ── Layout ─────────────────────────────────────────── */

  .bastion-layout {
    display: flex;
    flex: 1;
    gap: 0;
    min-height: 0;
    overflow: hidden;
  }

  .server-panel {
    width: 360px;
    min-width: 360px;
    display: flex;
    flex-direction: column;
    background: var(--bg-card, rgba(13,24,42,0.7));
    border: 1px solid var(--border-subtle, rgba(255,255,255,0.06));
    border-radius: 12px;
    overflow: hidden;
    transition: width 0.2s;
  }
  .server-panel.collapsed {
    width: 300px;
    min-width: 300px;
  }

  .terminal-panel {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;
    margin-left: 8px;
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid var(--border-subtle, rgba(255,255,255,0.06));
  }

  /* ── Filters ─────────────────────────────────────────── */

  .filters-bar {
    padding: 10px 12px;
    border-bottom: 1px solid var(--border-subtle, rgba(255,255,255,0.06));
    display: flex;
    flex-direction: column;
    gap: 8px;
    flex-shrink: 0;
  }

  .search-input {
    width: 100%;
    background: rgba(0,0,0,0.2);
    border: 1px solid var(--border-subtle, rgba(255,255,255,0.06));
    border-radius: 8px;
    padding: 6px 10px;
    color: var(--text, #E6EAF2);
    font-size: 0.8rem;
    outline: none;
  }
  .search-input:focus { border-color: var(--accent, #06A6C9); }

  .filter-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
  }

  .filter-chip {
    background: transparent;
    border: 1px solid var(--border-subtle, rgba(255,255,255,0.06));
    border-radius: 12px;
    padding: 2px 8px;
    color: var(--text-dim, #94A3B8);
    cursor: pointer;
    font-size: 0.7rem;
    display: flex;
    align-items: center;
    gap: 4px;
    transition: all 0.15s;
  }
  .filter-chip:hover { background: rgba(255,255,255,0.03); }
  .filter-chip.active {
    background: rgba(255,255,255,0.06);
    border-color: var(--chip-color, var(--accent, #06A6C9));
    color: var(--text, #E6EAF2);
  }

  .chip-dot {
    width: 6px; height: 6px;
    border-radius: 50%;
    display: inline-block;
  }
  .chip-count {
    opacity: 0.6;
    font-size: 0.65rem;
  }

  .protocol-filter {
    display: flex;
    gap: 4px;
  }
  .protocol-filter button {
    background: transparent;
    border: 1px solid var(--border-subtle, rgba(255,255,255,0.06));
    border-radius: 6px;
    padding: 2px 10px;
    color: var(--text-dim, #94A3B8);
    cursor: pointer;
    font-size: 0.7rem;
    transition: all 0.15s;
  }
  .protocol-filter button.active {
    background: rgba(255,255,255,0.06);
    color: var(--text, #E6EAF2);
  }

  /* ── Server list ─────────────────────────────────────── */

  .server-list {
    flex: 1;
    overflow-y: auto;
    padding: 8px;
  }

  .empty-state {
    text-align: center;
    padding: 40px 20px;
    color: var(--text-dim, #94A3B8);
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
  }
  .empty-icon { font-size: 2.5rem; }

  .group-section { margin-bottom: 12px; }

  .group-header {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 4px 6px;
    margin-bottom: 4px;
  }
  .group-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }
  .group-name {
    color: var(--text-dim, #94A3B8);
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  .group-count {
    color: var(--text-dim, #94A3B8);
    font-size: 0.65rem;
    opacity: 0.5;
  }
  .group-line {
    flex: 1;
    height: 1px;
    background: var(--border-subtle, rgba(255,255,255,0.06));
  }
  .btn-add-small {
    width: 18px; height: 18px;
    border-radius: 4px;
    border: 1px solid var(--border-subtle, rgba(255,255,255,0.06));
    background: transparent;
    color: var(--text-dim, #94A3B8);
    cursor: pointer;
    font-size: 0.7rem;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    transition: all 0.15s;
  }
  .btn-add-small:hover { background: rgba(255,255,255,0.05); color: var(--text, #E6EAF2); }

  .server-row {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 10px;
    border-radius: 8px;
    cursor: pointer;
    transition: background 0.15s;
    position: relative;
  }
  .server-row:hover { background: rgba(255,255,255,0.03); }
  .server-row:hover .server-actions { opacity: 1; }

  .ping-dot {
    font-size: 8px;
    color: #374151;
    flex-shrink: 0;
    cursor: pointer;
    width: 14px;
    text-align: center;
  }
  .ping-dot.alive { color: #10B981; }
  .ping-dot.dead { color: #EF4444; }
  .ping-dot.pinging { color: #F59E0B; animation: pulse 1s infinite; }

  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
  }

  .proto-badge {
    font-size: 0.6rem;
    font-weight: 700;
    padding: 1px 6px;
    border-radius: 3px;
    flex-shrink: 0;
  }
  .proto-badge.ssh { background: #1D4ED8; color: #fff; }
  .proto-badge.rdp { background: #7C3AED; color: #fff; }

  .server-info {
    flex: 1;
    min-width: 0;
  }
  .server-name {
    color: var(--text, #E6EAF2);
    font-size: 0.85rem;
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .server-meta {
    color: var(--text-dim, #64748B);
    font-size: 0.7rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .server-actions {
    display: flex;
    gap: 2px;
    opacity: 0;
    transition: opacity 0.15s;
    flex-shrink: 0;
  }
  .action-btn {
    background: transparent;
    border: none;
    border-radius: 4px;
    width: 26px; height: 26px;
    cursor: pointer;
    font-size: 0.8rem;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background 0.15s;
  }
  .action-btn:hover { background: rgba(255,255,255,0.08); }
  .action-btn.danger:hover { background: rgba(239,68,68,0.15); }
  .action-btn.connect:hover { background: rgba(6,166,201,0.15); }

  /* ── Session tabs ─────────────────────────────────────── */

  .session-tabs {
    display: flex;
    background: #0B1424;
    border-bottom: 1px solid var(--border-subtle, rgba(255,255,255,0.06));
    overflow-x: auto;
    flex-shrink: 0;
  }
  .session-tab {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 14px;
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    color: var(--text-dim, #94A3B8);
    cursor: pointer;
    font-size: 0.8rem;
    white-space: nowrap;
    transition: all 0.15s;
  }
  .session-tab:hover { background: rgba(255,255,255,0.03); }
  .session-tab.active {
    color: var(--text, #E6EAF2);
    border-bottom-color: var(--accent, #06A6C9);
    background: rgba(255,255,255,0.03);
  }

  .tab-status {
    font-size: 6px;
  }
  .tab-status.connected { color: #10B981; }
  .tab-status.connecting { color: #F59E0B; animation: pulse 1s infinite; }
  .tab-status.error { color: #EF4444; }

  .tab-proto {
    font-size: 0.55rem;
    font-weight: 700;
    padding: 0px 4px;
    border-radius: 2px;
  }
  .tab-proto.ssh { background: #1D4ED8; color: #fff; }
  .tab-proto.rdp { background: #7C3AED; color: #fff; }

  .tab-close {
    background: transparent;
    border: none;
    color: var(--text-dim, #64748B);
    cursor: pointer;
    font-size: 0.7rem;
    padding: 0 2px;
    margin-left: 4px;
    border-radius: 3px;
  }
  .tab-close:hover { background: rgba(239,68,68,0.2); color: #EF4444; }

  /* ── Terminal content ────────────────────────────────── */

  .terminal-content {
    flex: 1;
    position: relative;
    background: #0D1117;
    min-height: 0;
  }

  .terminal-wrapper {
    position: absolute;
    inset: 0;
    display: none;
  }
  .terminal-wrapper.visible { display: flex; }

  .xterm-container {
    flex: 1;
    width: 100%;
    height: 100%;
  }

  :global(.xterm-container .xterm) {
    height: 100%;
    padding: 4px;
  }

  /* ── RDP external card ───────────────────────────────── */

  .rdp-external-card {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    gap: 12px;
    color: var(--text-dim, #94A3B8);
  }


  .rdp-dialog-server {
    color: var(--text-dim, #94A3B8);
    font-size: 0.85rem;
    margin: 0 0 12px 0;
  }
  .rdp-dialog-form {
    display: flex;
    flex-direction: column;
    gap: 10px;
    margin-bottom: 16px;
  }
  .rdp-dialog-form label {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .rdp-dialog-form span {
    color: var(--text-dim, #94A3B8);
    font-size: 0.75rem;
    font-weight: 600;
  }
  .dialog-input {
    background: rgba(0,0,0,0.3);
    border: 1px solid var(--border-subtle, rgba(255,255,255,0.06));
    border-radius: 8px;
    padding: 8px 12px;
    color: var(--text, #E6EAF2);
    font-size: 0.85rem;
    outline: none;
  }
  .dialog-input:focus { border-color: var(--accent, #06A6C9); }
  .dialog-input:disabled { opacity: 0.5; }

  /* ── Dialogs ─────────────────────────────────────────── */

  .dialog-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.6);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
    backdrop-filter: blur(4px);
  }

  .dialog {
    background: var(--bg-dialog, #0D1826);
    border: 1px solid var(--border-subtle, rgba(255,255,255,0.1));
    border-radius: 16px;
    padding: 24px;
    max-width: 480px;
    width: 90%;
    max-height: 85vh;
    overflow-y: auto;
  }
  .dialog-small { max-width: 360px; }

  .dialog h2 {
    color: var(--text, #E6EAF2);
    font-size: 1.1rem;
    margin: 0 0 16px 0;
  }
  .dialog p {
    color: var(--text-dim, #94A3B8);
    margin: 0 0 16px 0;
  }

  .form-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
  }
  .form-grid label {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .form-grid label span {
    color: var(--text-dim, #94A3B8);
    font-size: 0.75rem;
    font-weight: 600;
  }
  .form-grid label.full-width { grid-column: 1 / -1; }

  .form-grid input, .form-grid select, .form-grid textarea {
    background: rgba(0,0,0,0.3);
    border: 1px solid var(--border-subtle, rgba(255,255,255,0.06));
    border-radius: 8px;
    padding: 8px 10px;
    color: var(--text, #E6EAF2);
    font-size: 0.85rem;
    outline: none;
  }
  .form-grid input:focus, .form-grid select:focus, .form-grid textarea:focus {
    border-color: var(--accent, #06A6C9);
  }
  .form-grid textarea { resize: vertical; font-family: inherit; }

  .dialog-actions {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    margin-top: 16px;
  }

  /* ── Groups dialog ───────────────────────────────────── */

  .group-list {
    display: flex;
    flex-direction: column;
    gap: 6px;
    margin-bottom: 12px;
    max-height: 250px;
    overflow-y: auto;
  }
  .group-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 10px;
    background: rgba(0,0,0,0.2);
    border-radius: 8px;
  }
  .group-item-name {
    flex: 1;
    color: var(--text, #E6EAF2);
    font-size: 0.85rem;
  }
  .group-item-count {
    color: var(--text-dim, #64748B);
    font-size: 0.75rem;
  }
  .btn-delete-small {
    background: transparent;
    border: none;
    color: #64748B;
    cursor: pointer;
    font-size: 0.8rem;
    padding: 2px 6px;
    border-radius: 4px;
  }
  .btn-delete-small:hover { color: #EF4444; background: rgba(239,68,68,0.1); }

  .add-group-row {
    display: flex;
    gap: 8px;
    align-items: center;
  }
  .add-group-row input[type="text"] {
    flex: 1;
    background: rgba(0,0,0,0.3);
    border: 1px solid var(--border-subtle, rgba(255,255,255,0.06));
    border-radius: 8px;
    padding: 6px 10px;
    color: var(--text, #E6EAF2);
    font-size: 0.85rem;
    outline: none;
  }
  .color-picker {
    width: 32px; height: 32px;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    background: transparent;
  }
</style>
