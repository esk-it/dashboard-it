<script>
  import { onMount } from 'svelte';

  const API = 'http://localhost:8010/api/tools';

  // ── Tab system ────────────────────────────────────────────────────────────
  let activeTab = 'ping';
  const tabs = [
    { id: 'ping',      label: 'Ping',         icon: '\u{1F4E1}', group: 'network' },
    { id: 'dns',       label: 'DNS Lookup',    icon: '\u{1F310}', group: 'network' },
    { id: 'tcp',       label: 'Test TCP',      icon: '\u{1F50C}', group: 'network' },
    { id: 'traceroute',label: 'Traceroute',    icon: '\u{1F6E4}\uFE0F', group: 'network' },
    { id: 'password',  label: 'Mots de passe', icon: '\u{1F510}', group: 'utils' },
    { id: 'ipcalc',    label: 'IP / CIDR',     icon: '\u{1F4CA}', group: 'utils' },
    { id: 'wol',       label: 'Wake-on-LAN',   icon: '\u{1F4E1}', group: 'utils' },
    { id: 'whois',     label: 'WHOIS',         icon: '\u{1F50D}', group: 'utils' },
    { id: 'portscan',  label: 'Scan ports',    icon: '\u{1F6E1}\uFE0F', group: 'network' },
    { id: 'qrcode',    label: 'QR Code',       icon: '\u{1F4F1}', group: 'utils' },
  ];

  // ── Network tools state ───────────────────────────────────────────────────
  let host = '';
  let port = 80;
  let pingCount = 4;
  let timeout = 3;
  let running = false;
  let output = '';
  let success = null;
  let history = [];
  let commonPorts = [];
  let showPortPicker = false;

  // ── Password generator state ──────────────────────────────────────────────
  let pwLength = 16;
  let pwUppercase = true;
  let pwLowercase = true;
  let pwDigits = true;
  let pwSymbols = true;
  let pwExcludeSimilar = false;
  let pwCount = 5;
  let pwResults = [];
  let pwRunning = false;

  // ── IP/CIDR calculator state ──────────────────────────────────────────────
  let cidrInput = '';
  let cidrResult = null;
  let cidrRunning = false;

  // ── Wake-on-LAN state ─────────────────────────────────────────────────────
  let wolMac = '';
  let wolBroadcast = '255.255.255.255';
  let wolPort = 9;
  let wolResult = null;
  let wolRunning = false;
  let wolHistory = [];

  // ── WHOIS state ───────────────────────────────────────────────────────────
  let whoisQuery = '';
  let whoisResult = '';
  let whoisSuccess = null;
  let whoisRunning = false;

  // ── Port scanner state ───────────────────────────────────────────────────
  let scanHost = '';
  let scanPorts = '22,80,443,3389,8080';
  let scanTimeout = 2;
  let scanRunning = false;
  let scanResults = [];

  // ── QR Code state ────────────────────────────────────────────────────────
  let qrText = '';
  let qrSize = 256;
  let qrDataUrl = '';
  let qrType = 'text';  // text, url, wifi, email

  onMount(async () => {
    try {
      const res = await fetch(`${API}/common-ports`);
      commonPorts = await res.json();
    } catch(e) {}
  });

  // ── Network tool runner ───────────────────────────────────────────────────
  async function runTool() {
    if (!host.trim()) return;
    running = true;
    output = '';
    success = null;

    const entry = { type: activeTab, host: host.trim(), port, time: new Date().toLocaleTimeString() };
    history = [entry, ...history.slice(0, 9)];

    try {
      let res;
      if (activeTab === 'ping') {
        res = await fetch(`${API}/ping`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ host: host.trim(), count: pingCount, timeout }),
        });
        const data = await res.json();
        output = data.output;
        success = data.success;
      } else if (activeTab === 'dns') {
        res = await fetch(`${API}/dns?host=${encodeURIComponent(host.trim())}`, { method: 'POST' });
        const data = await res.json();
        output = data.output;
        success = data.success;
      } else if (activeTab === 'tcp') {
        res = await fetch(`${API}/tcp`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ host: host.trim(), port, timeout }),
        });
        const data = await res.json();
        output = data.output;
        success = data.open;
      } else if (activeTab === 'traceroute') {
        res = await fetch(`${API}/traceroute?host=${encodeURIComponent(host.trim())}`, { method: 'POST' });
        const data = await res.json();
        output = data.output;
        success = data.success;
      }
    } catch(e) {
      output = `Erreur: ${e.message}`;
      success = false;
    }
    running = false;
  }

  // ── Password generator ────────────────────────────────────────────────────
  async function generatePasswords() {
    pwRunning = true;
    try {
      const res = await fetch(`${API}/password-generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          length: pwLength,
          uppercase: pwUppercase,
          lowercase: pwLowercase,
          digits: pwDigits,
          symbols: pwSymbols,
          exclude_similar: pwExcludeSimilar,
          count: pwCount,
        }),
      });
      const data = await res.json();
      pwResults = data.passwords;
    } catch(e) {
      pwResults = [];
    }
    pwRunning = false;
  }

  function copyPassword(pw) {
    navigator.clipboard.writeText(pw);
  }

  function copyAllPasswords() {
    const text = pwResults.map(p => p.password).join('\n');
    navigator.clipboard.writeText(text);
  }

  function strengthColor(s) {
    if (s === 'Faible') return '#EF4444';
    if (s === 'Moyen') return '#F59E0B';
    if (s === 'Fort') return '#10B981';
    return '#06A6C9';
  }

  // ── IP/CIDR calculator ────────────────────────────────────────────────────
  async function calcCidr() {
    if (!cidrInput.trim()) return;
    cidrRunning = true;
    cidrResult = null;
    try {
      const res = await fetch(`${API}/ip-calc`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cidr: cidrInput.trim() }),
      });
      cidrResult = await res.json();
    } catch(e) {
      cidrResult = { success: false, error: e.message };
    }
    cidrRunning = false;
  }

  function setCidrQuick(prefix) {
    const base = cidrInput.split('/')[0] || '192.168.1.0';
    cidrInput = `${base}/${prefix}`;
  }

  // ── Wake-on-LAN ──────────────────────────────────────────────────────────
  async function sendWol() {
    if (!wolMac.trim()) return;
    wolRunning = true;
    wolResult = null;
    try {
      const res = await fetch(`${API}/wol`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mac_address: wolMac.trim(), broadcast_ip: wolBroadcast, port: wolPort }),
      });
      wolResult = await res.json();
      if (wolResult.success) {
        wolHistory = [
          { mac: wolMac.trim(), broadcast: wolBroadcast, time: new Date().toLocaleTimeString() },
          ...wolHistory.slice(0, 9)
        ];
      }
    } catch(e) {
      wolResult = { success: false, message: e.message };
    }
    wolRunning = false;
  }

  // ── WHOIS ─────────────────────────────────────────────────────────────────
  async function runWhois() {
    if (!whoisQuery.trim()) return;
    whoisRunning = true;
    whoisResult = '';
    whoisSuccess = null;
    try {
      const res = await fetch(`${API}/whois`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: whoisQuery.trim() }),
      });
      const data = await res.json();
      whoisResult = data.result;
      whoisSuccess = data.success;
    } catch(e) {
      whoisResult = `Erreur: ${e.message}`;
      whoisSuccess = false;
    }
    whoisRunning = false;
  }

  // ── Helpers ───────────────────────────────────────────────────────────────
  function selectPort(p) {
    port = p.port;
    host = host || '';
    showPortPicker = false;
  }

  function copyOutput() { navigator.clipboard.writeText(output); }
  function clearOutput() { output = ''; success = null; }

  function loadFromHistory(entry) {
    host = entry.host;
    if (entry.port) port = entry.port;
    activeTab = entry.type;
  }

  function highlightLine(line) {
    if (line.startsWith('$ ')) return 'cmd';
    if (line.includes('\u2705') || line.includes('R\u00e9ponse de') || line.includes('Reply from') || line.includes('ouvert')) return 'ok';
    if (line.includes('\u274C') || line.includes('timed out') || line.includes('ferm\u00e9') || line.includes('failed')) return 'err';
    if (line.includes('Statistiques') || line.includes('statistics') || line.includes('Hostname:') || line.includes('Addresses:')) return 'section';
    if (line.includes('Paquets') || line.includes('Packets')) {
      return line.includes('perdus = 0') || line.includes('Lost = 0') ? 'ok' : 'warn';
    }
    return '';
  }

  $: portCategories = (() => {
    const cats = {};
    for (const p of commonPorts) {
      if (!cats[p.category]) cats[p.category] = [];
      cats[p.category].push(p);
    }
    return Object.entries(cats);
  })();

  $: isNetworkTab = ['ping', 'dns', 'tcp', 'traceroute', 'portscan'].includes(activeTab);

  // ── Port Scanner ────────────────────────────────────────────────────────
  async function runPortScan() {
    if (!scanHost.trim()) return;
    scanRunning = true;
    scanResults = [];
    const ports = scanPorts.split(',').map(p => parseInt(p.trim())).filter(p => !isNaN(p) && p > 0 && p < 65536);
    const results = [];
    for (const p of ports) {
      try {
        const res = await fetch(`${API}/tcp`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ host: scanHost.trim(), port: p, timeout: scanTimeout }),
        });
        const data = await res.json();
        results.push({ port: p, open: data.open, service: data.service || '', latency: data.latency_ms || '' });
      } catch {
        results.push({ port: p, open: false, service: '', latency: '' });
      }
      scanResults = [...results]; // Update reactively after each port
    }
    scanRunning = false;
  }

  // ── QR Code Generator (client-side using canvas) ─────────────────────────
  function generateQrText() {
    if (qrType === 'wifi') {
      return `WIFI:T:WPA;S:${qrText};P:${qrText};;`;
    }
    if (qrType === 'email') {
      return `mailto:${qrText}`;
    }
    if (qrType === 'url' && qrText && !qrText.startsWith('http')) {
      return `https://${qrText}`;
    }
    return qrText;
  }

  async function generateQr() {
    if (!qrText.trim()) return;
    const text = generateQrText();
    // Use public API for QR generation (no dependency needed)
    qrDataUrl = `https://api.qrserver.com/v1/create-qr-code/?size=${qrSize}x${qrSize}&data=${encodeURIComponent(text)}&format=png&margin=8`;
  }

  function downloadQr() {
    if (!qrDataUrl) return;
    const a = document.createElement('a');
    a.href = qrDataUrl;
    a.download = `qrcode-${Date.now()}.png`;
    a.click();
  }

  function copyQrToClipboard() {
    if (!qrDataUrl) return;
    navigator.clipboard.writeText(qrDataUrl);
  }
</script>

<div class="tools-page">
  <div class="page-header">
    <h1>{'\u{1F527}'} Outils</h1>
  </div>

  <div class="tools-layout">
    <!-- Main area -->
    <div class="main-area">
      <!-- Tool tabs -->
      <div class="tool-tabs">
        <div class="tab-group">
          <span class="tab-group-label">R{'\u00e9'}seau</span>
          {#each tabs.filter(t => t.group === 'network') as tab}
            <button class="tool-tab" class:active={activeTab === tab.id} on:click={() => activeTab = tab.id}>
              {tab.icon} {tab.label}
            </button>
          {/each}
        </div>
        <div class="tab-separator"></div>
        <div class="tab-group">
          <span class="tab-group-label">Utilitaires</span>
          {#each tabs.filter(t => t.group === 'utils') as tab}
            <button class="tool-tab" class:active={activeTab === tab.id} on:click={() => activeTab = tab.id}>
              {tab.icon} {tab.label}
            </button>
          {/each}
        </div>
      </div>

      <!-- ═══════════════ NETWORK TOOLS ═══════════════ -->
      {#if isNetworkTab}
        <div class="input-area">
          <div class="input-row">
            <input type="text" bind:value={host} placeholder="Adresse IP ou nom d'h{'\u00f4'}te"
              class="host-input" on:keydown={(e) => e.key === 'Enter' && runTool()} />

            {#if activeTab === 'tcp'}
              <div class="port-group">
                <input type="number" bind:value={port} min="1" max="65535" class="port-input" placeholder="Port" />
                <button class="btn-port-picker" on:click={() => showPortPicker = !showPortPicker} title="Ports courants">
                  {'\u{1F4CB}'}
                </button>
              </div>
            {/if}

            {#if activeTab === 'ping'}
              <div class="option-group">
                <label>
                  <span>Nombre</span>
                  <input type="number" bind:value={pingCount} min="1" max="20" class="small-input" />
                </label>
              </div>
            {/if}

            <button class="btn-run" on:click={runTool} disabled={running || !host.trim()}>
              {#if running}
                {'\u23F3'} En cours...
              {:else}
                {'\u25B6'} Ex{'\u00e9'}cuter
              {/if}
            </button>
          </div>

          {#if showPortPicker && activeTab === 'tcp'}
            <div class="port-picker">
              {#each portCategories as [cat, ports]}
                <div class="port-category">
                  <div class="port-cat-name">{cat}</div>
                  <div class="port-items">
                    {#each ports as p}
                      <button class="port-item" on:click={() => selectPort(p)} class:active={port === p.port}>
                        <span class="port-num">{p.port}</span>
                        <span class="port-name">{p.name}</span>
                      </button>
                    {/each}
                  </div>
                </div>
              {/each}
            </div>
          {/if}
        </div>

        <div class="output-area">
          <div class="output-header">
            <div class="output-title">
              {#if success === true}
                <span class="status-ok">{'\u2705'} Succ{'\u00e8'}s</span>
              {:else if success === false}
                <span class="status-err">{'\u274C'} {'\u00C9'}chec</span>
              {:else}
                <span class="status-idle">R{'\u00e9'}sultat</span>
              {/if}
            </div>
            <div class="output-actions">
              <button class="btn-small" on:click={copyOutput} disabled={!output} title="Copier">{'\u{1F4CB}'} Copier</button>
              <button class="btn-small" on:click={clearOutput} disabled={!output} title="Effacer">{'\u{1F5D1}\uFE0F'} Effacer</button>
            </div>
          </div>
          <div class="output-content">
            {#if running}
              <div class="output-loading">{'\u23F3'} Ex{'\u00e9'}cution en cours...</div>
            {:else if output}
              {#each output.split('\n') as line}
                <div class="output-line {highlightLine(line)}">{line}</div>
              {/each}
            {:else}
              <div class="output-empty">
                {#if activeTab === 'ping'}
                  Entrez une adresse et lancez un ping pour tester la connectivit{'\u00e9'}.
                {:else if activeTab === 'dns'}
                  Entrez un nom de domaine pour r{'\u00e9'}soudre son adresse IP.
                {:else if activeTab === 'tcp'}
                  Entrez une adresse et un port pour tester la connexion TCP.
                {:else}
                  Entrez une adresse pour tracer l'itin{'\u00e9'}raire r{'\u00e9'}seau.
                {/if}
              </div>
            {/if}
          </div>
        </div>

      <!-- ═══════════════ PASSWORD GENERATOR ═══════════════ -->
      {:else if activeTab === 'password'}
        <div class="tool-panel">
          <div class="pw-config">
            <div class="pw-row">
              <label class="pw-label">Longueur : <strong>{pwLength}</strong></label>
              <input type="range" bind:value={pwLength} min="4" max="128" class="pw-slider" />
            </div>

            <div class="pw-options">
              <label class="pw-check">
                <input type="checkbox" bind:checked={pwUppercase} /> Majuscules (A-Z)
              </label>
              <label class="pw-check">
                <input type="checkbox" bind:checked={pwLowercase} /> Minuscules (a-z)
              </label>
              <label class="pw-check">
                <input type="checkbox" bind:checked={pwDigits} /> Chiffres (0-9)
              </label>
              <label class="pw-check">
                <input type="checkbox" bind:checked={pwSymbols} /> Symboles (!@#$...)
              </label>
              <label class="pw-check">
                <input type="checkbox" bind:checked={pwExcludeSimilar} /> Exclure similaires (I,l,1,O,0)
              </label>
            </div>

            <div class="pw-row">
              <label class="pw-label">Nombre : </label>
              <input type="number" bind:value={pwCount} min="1" max="20" class="small-input" />
              <button class="btn-run" on:click={generatePasswords} disabled={pwRunning}>
                {#if pwRunning}
                  {'\u23F3'} ...
                {:else}
                  {'\u{1F510}'} G{'\u00e9'}n{'\u00e9'}rer
                {/if}
              </button>
              {#if pwResults.length > 0}
                <button class="btn-small" on:click={copyAllPasswords}>{'\u{1F4CB}'} Copier tout</button>
              {/if}
            </div>
          </div>

          {#if pwResults.length > 0}
            <div class="pw-results">
              {#each pwResults as entry, i}
                <div class="pw-item">
                  <span class="pw-index">#{i + 1}</span>
                  <code class="pw-value">{entry.password}</code>
                  <span class="pw-strength" style="color: {strengthColor(entry.strength)}">
                    {entry.strength} ({entry.entropy} bits)
                  </span>
                  <button class="btn-copy-sm" on:click={() => copyPassword(entry.password)} title="Copier">
                    {'\u{1F4CB}'}
                  </button>
                </div>
              {/each}
            </div>
          {:else}
            <div class="output-empty">
              Configurez les options et g{'\u00e9'}n{'\u00e9'}rez des mots de passe s{'\u00e9'}curis{'\u00e9'}s.
            </div>
          {/if}
        </div>

      <!-- ═══════════════ IP/CIDR CALCULATOR ═══════════════ -->
      {:else if activeTab === 'ipcalc'}
        <div class="tool-panel">
          <div class="input-area">
            <div class="input-row">
              <input type="text" bind:value={cidrInput} placeholder="Ex: 192.168.1.0/24"
                class="host-input" on:keydown={(e) => e.key === 'Enter' && calcCidr()} />
              <button class="btn-run" on:click={calcCidr} disabled={cidrRunning || !cidrInput.trim()}>
                {#if cidrRunning}
                  {'\u23F3'} ...
                {:else}
                  {'\u{1F4CA}'} Calculer
                {/if}
              </button>
            </div>
            <div class="quick-prefixes">
              {#each [8, 16, 20, 22, 24, 25, 26, 27, 28, 29, 30] as p}
                <button class="prefix-btn" on:click={() => setCidrQuick(p)}>/{p}</button>
              {/each}
            </div>
          </div>

          {#if cidrResult}
            {#if cidrResult.success}
              <div class="cidr-grid">
                <div class="cidr-cell">
                  <span class="cidr-label">R{'\u00e9'}seau</span>
                  <span class="cidr-value">{cidrResult.network}/{cidrResult.prefix}</span>
                </div>
                <div class="cidr-cell">
                  <span class="cidr-label">Masque</span>
                  <span class="cidr-value">{cidrResult.netmask}</span>
                </div>
                <div class="cidr-cell">
                  <span class="cidr-label">Wildcard</span>
                  <span class="cidr-value">{cidrResult.wildcard}</span>
                </div>
                <div class="cidr-cell">
                  <span class="cidr-label">Broadcast</span>
                  <span class="cidr-value">{cidrResult.broadcast}</span>
                </div>
                <div class="cidr-cell">
                  <span class="cidr-label">Premier h{'\u00f4'}te</span>
                  <span class="cidr-value">{cidrResult.first_host}</span>
                </div>
                <div class="cidr-cell">
                  <span class="cidr-label">Dernier h{'\u00f4'}te</span>
                  <span class="cidr-value">{cidrResult.last_host}</span>
                </div>
                <div class="cidr-cell">
                  <span class="cidr-label">Total adresses</span>
                  <span class="cidr-value">{cidrResult.total_addresses.toLocaleString()}</span>
                </div>
                <div class="cidr-cell">
                  <span class="cidr-label">H{'\u00f4'}tes utilisables</span>
                  <span class="cidr-value">{cidrResult.usable_hosts.toLocaleString()}</span>
                </div>
                <div class="cidr-cell">
                  <span class="cidr-label">Classe</span>
                  <span class="cidr-value">{cidrResult.ip_class}</span>
                </div>
                <div class="cidr-cell">
                  <span class="cidr-label">Priv{'\u00e9'}</span>
                  <span class="cidr-value" style="color: {cidrResult.is_private ? '#10B981' : '#F59E0B'}">
                    {cidrResult.is_private ? 'Oui' : 'Non'}
                  </span>
                </div>
              </div>

              {#if cidrResult.subnets && cidrResult.subnets.length > 0}
                <div class="subnets-section">
                  <h3>Sous-r{'\u00e9'}seaux</h3>
                  <div class="subnets-list">
                    {#each cidrResult.subnets as sub}
                      <div class="subnet-item">
                        <span class="subnet-network">{sub.network}</span>
                        <span class="subnet-range">{sub.first_host} - {sub.last_host}</span>
                        <span class="subnet-hosts">{sub.hosts} h{'\u00f4'}tes</span>
                      </div>
                    {/each}
                  </div>
                </div>
              {/if}
            {:else}
              <div class="error-message">{'\u274C'} {cidrResult.error}</div>
            {/if}
          {:else}
            <div class="output-empty">
              Entrez une adresse CIDR (ex: 192.168.1.0/24) pour calculer les informations r{'\u00e9'}seau.
            </div>
          {/if}
        </div>

      <!-- ═══════════════ WAKE-ON-LAN ═══════════════ -->
      {:else if activeTab === 'wol'}
        <div class="tool-panel">
          <div class="input-area">
            <div class="wol-form">
              <div class="form-group">
                <label class="form-label">Adresse MAC</label>
                <input type="text" bind:value={wolMac} placeholder="AA:BB:CC:DD:EE:FF"
                  class="host-input" on:keydown={(e) => e.key === 'Enter' && sendWol()} />
              </div>
              <div class="form-row">
                <div class="form-group" style="flex:1">
                  <label class="form-label">IP Broadcast</label>
                  <input type="text" bind:value={wolBroadcast} class="host-input" />
                </div>
                <div class="form-group" style="width:100px">
                  <label class="form-label">Port</label>
                  <input type="number" bind:value={wolPort} min="1" max="65535" class="port-input" />
                </div>
                <button class="btn-run btn-wol" on:click={sendWol} disabled={wolRunning || !wolMac.trim()}>
                  {#if wolRunning}
                    {'\u23F3'} ...
                  {:else}
                    {'\u26A1'} Envoyer
                  {/if}
                </button>
              </div>
            </div>
          </div>

          {#if wolResult}
            <div class="wol-result" class:wol-ok={wolResult.success} class:wol-err={!wolResult.success}>
              {wolResult.success ? '\u2705' : '\u274C'} {wolResult.message}
            </div>
          {/if}

          {#if wolHistory.length > 0}
            <div class="wol-history">
              <h3>Historique d'envoi</h3>
              {#each wolHistory as entry}
                <div class="wol-hist-item">
                  <span class="wol-hist-mac">{entry.mac}</span>
                  <span class="wol-hist-bc">{entry.broadcast}</span>
                  <span class="wol-hist-time">{entry.time}</span>
                  <button class="btn-small" on:click={() => { wolMac = entry.mac; wolBroadcast = entry.broadcast; }}>
                    R{'\u00e9'}utiliser
                  </button>
                </div>
              {/each}
            </div>
          {:else if !wolResult}
            <div class="output-empty">
              Envoyez un magic packet Wake-on-LAN pour r{'\u00e9'}veiller une machine sur le r{'\u00e9'}seau.
            </div>
          {/if}
        </div>

      <!-- ═══════════════ WHOIS ═══════════════ -->
      {:else if activeTab === 'whois'}
        <div class="tool-panel">
          <div class="input-area">
            <div class="input-row">
              <input type="text" bind:value={whoisQuery} placeholder="Domaine ou adresse IP (ex: google.com)"
                class="host-input" on:keydown={(e) => e.key === 'Enter' && runWhois()} />
              <button class="btn-run" on:click={runWhois} disabled={whoisRunning || !whoisQuery.trim()}>
                {#if whoisRunning}
                  {'\u23F3'} Recherche...
                {:else}
                  {'\u{1F50D}'} WHOIS
                {/if}
              </button>
            </div>
          </div>

          <div class="output-area-inner">
            {#if whoisRunning}
              <div class="output-loading">{'\u23F3'} Recherche WHOIS en cours...</div>
            {:else if whoisResult}
              <div class="output-header">
                <div class="output-title">
                  {#if whoisSuccess}
                    <span class="status-ok">{'\u2705'} R{'\u00e9'}sultat pour {whoisQuery}</span>
                  {:else}
                    <span class="status-err">{'\u274C'} {'\u00C9'}chec</span>
                  {/if}
                </div>
                <button class="btn-small" on:click={() => navigator.clipboard.writeText(whoisResult)}>{'\u{1F4CB}'} Copier</button>
              </div>
              <pre class="whois-output">{whoisResult}</pre>
            {:else}
              <div class="output-empty">
                Entrez un nom de domaine ou une adresse IP pour effectuer une recherche WHOIS.
              </div>
            {/if}
          </div>
        </div>

      <!-- ═══════════════ PORT SCANNER ═══════════════ -->
      {:else if activeTab === 'portscan'}
        <div class="tool-panel">
          <div class="input-area">
            <div class="input-row">
              <input type="text" bind:value={scanHost} placeholder="Adresse IP ou hostname"
                class="host-input" style="flex:1" on:keydown={(e) => e.key === 'Enter' && runPortScan()} />
              <input type="text" bind:value={scanPorts} placeholder="Ports (ex: 22,80,443)"
                class="host-input" style="flex:1.5" />
              <button class="btn-run" on:click={runPortScan} disabled={scanRunning || !scanHost.trim()}>
                {#if scanRunning}
                  {'\u23F3'} Scan...
                {:else}
                  {'\u{1F6E1}\uFE0F'} Scanner
                {/if}
              </button>
            </div>
            <div class="port-presets">
              <span class="preset-label">Presets :</span>
              <button class="btn-preset" on:click={() => scanPorts = '22,80,443,3389'}>Web+SSH</button>
              <button class="btn-preset" on:click={() => scanPorts = '21,22,23,25,53,80,110,143,443,993,995,3306,3389,5432,8080,8443'}>Complet</button>
              <button class="btn-preset" on:click={() => scanPorts = '135,137,139,445,3389'}>Windows</button>
              <button class="btn-preset" on:click={() => scanPorts = '22,80,443,8080,8443,9090'}>Linux</button>
            </div>
          </div>

          <div class="output-area-inner">
            {#if scanResults.length > 0}
              <div class="scan-results-grid">
                {#each scanResults as r}
                  <div class="scan-port-card" class:port-open={r.open} class:port-closed={!r.open}>
                    <span class="port-number">{r.port}</span>
                    <span class="port-status">{r.open ? '\u2705 Ouvert' : '\u274C Ferm\u00e9'}</span>
                    {#if r.service}<span class="port-service">{r.service}</span>{/if}
                  </div>
                {/each}
              </div>
              {#if scanRunning}
                <div class="scan-progress">{'\u23F3'} Scan en cours... {scanResults.length}/{scanPorts.split(',').length} ports</div>
              {/if}
            {:else if scanRunning}
              <div class="output-loading">{'\u23F3'} D{'\u00e9'}marrage du scan...</div>
            {:else}
              <div class="output-empty">
                Entrez une adresse et des ports pour lancer un scan TCP.
              </div>
            {/if}
          </div>
        </div>

      <!-- ═══════════════ QR CODE ═══════════════ -->
      {:else if activeTab === 'qrcode'}
        <div class="tool-panel">
          <div class="input-area">
            <div class="qr-type-row">
              <button class="qr-type-btn" class:active={qrType === 'text'} on:click={() => qrType = 'text'}>{'\u{1F4DD}'} Texte</button>
              <button class="qr-type-btn" class:active={qrType === 'url'} on:click={() => qrType = 'url'}>{'\u{1F310}'} URL</button>
              <button class="qr-type-btn" class:active={qrType === 'wifi'} on:click={() => qrType = 'wifi'}>{'\u{1F4F6}'} Wi-Fi</button>
              <button class="qr-type-btn" class:active={qrType === 'email'} on:click={() => qrType = 'email'}>{'\u2709\uFE0F'} Email</button>
            </div>
            <div class="input-row">
              <input type="text" bind:value={qrText}
                placeholder={qrType === 'url' ? 'https://example.com' : qrType === 'wifi' ? 'Nom du r\u00e9seau Wi-Fi' : qrType === 'email' ? 'contact@example.com' : 'Texte \u00e0 encoder'}
                class="host-input" style="flex:1" on:keydown={(e) => e.key === 'Enter' && generateQr()} />
              <select bind:value={qrSize} class="host-input" style="width:100px">
                <option value={128}>128px</option>
                <option value={256}>256px</option>
                <option value={512}>512px</option>
              </select>
              <button class="btn-run" on:click={generateQr} disabled={!qrText.trim()}>
                {'\u{1F4F1}'} G{'\u00e9'}n{'\u00e9'}rer
              </button>
            </div>
          </div>

          <div class="output-area-inner">
            {#if qrDataUrl}
              <div class="qr-result">
                <div class="qr-preview">
                  <img src={qrDataUrl} alt="QR Code" width={qrSize} height={qrSize} />
                </div>
                <div class="qr-actions">
                  <button class="btn-small" on:click={downloadQr}>{'\u{2B07}\uFE0F'} T{'\u00e9'}l{'\u00e9'}charger PNG</button>
                  <button class="btn-small" on:click={copyQrToClipboard}>{'\u{1F4CB}'} Copier l'URL</button>
                </div>
              </div>
            {:else}
              <div class="output-empty">
                <div style="font-size:3rem;margin-bottom:12px">{'\u{1F4F1}'}</div>
                G{'\u00e9'}n{'\u00e9'}rez un QR Code pour du texte, une URL, un r{'\u00e9'}seau Wi-Fi ou un email.
              </div>
            {/if}
          </div>
        </div>
      {/if}
    </div>

    <!-- Sidebar: history (only for network tabs) -->
    {#if isNetworkTab}
      <div class="sidebar">
        <div class="sidebar-title">Historique</div>
        {#if history.length === 0}
          <div class="sidebar-empty">Aucun historique</div>
        {:else}
          {#each history as entry}
            <button class="history-item" on:click={() => loadFromHistory(entry)}>
              <span class="history-type">{entry.type.toUpperCase()}</span>
              <span class="history-host">{entry.host}{entry.type === 'tcp' ? `:${entry.port}` : ''}</span>
              <span class="history-time">{entry.time}</span>
            </button>
          {/each}
        {/if}
      </div>
    {/if}
  </div>
</div>

<style>
  .tools-page {
    display: flex;
    flex-direction: column;
    height: calc(100vh - 56px);
    gap: 12px;
  }

  .page-header h1 {
    color: var(--text, #E6EAF2);
    font-size: 1.5rem;
    font-weight: 700;
    margin: 0;
  }

  .tools-layout {
    display: flex;
    flex: 1;
    gap: 12px;
    min-height: 0;
  }

  .main-area {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 0;
    min-width: 0;
    background: var(--bg-card, rgba(13,24,42,0.7));
    border: 1px solid var(--border-subtle, rgba(255,255,255,0.06));
    border-radius: 12px;
    overflow: hidden;
  }

  /* ── Tool tabs ──────────────────────────────────────── */

  .tool-tabs {
    display: flex;
    border-bottom: 1px solid var(--border-subtle, rgba(255,255,255,0.06));
    flex-shrink: 0;
    flex-wrap: wrap;
    align-items: center;
    gap: 0;
  }
  .tab-group {
    display: flex;
    align-items: center;
    gap: 0;
  }
  .tab-group-label {
    color: var(--text-dim, #64748B);
    font-size: 0.6rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    padding: 0 8px 0 12px;
  }
  .tab-separator {
    width: 1px;
    height: 24px;
    background: var(--border-subtle, rgba(255,255,255,0.1));
    margin: 0 2px;
  }
  .tool-tab {
    padding: 10px 14px;
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    color: var(--text-dim, #94A3B8);
    cursor: pointer;
    font-size: 0.8rem;
    transition: all 0.15s;
    white-space: nowrap;
  }
  .tool-tab:hover { background: rgba(255,255,255,0.03); }
  .tool-tab.active {
    color: var(--text, #E6EAF2);
    border-bottom-color: var(--accent, #06A6C9);
  }

  /* ── Input area ─────────────────────────────────────── */

  .input-area {
    padding: 12px 16px;
    border-bottom: 1px solid var(--border-subtle, rgba(255,255,255,0.06));
    flex-shrink: 0;
  }

  .input-row {
    display: flex;
    gap: 8px;
    align-items: center;
  }

  .host-input {
    flex: 1;
    background: rgba(0,0,0,0.3);
    border: 1px solid var(--border-subtle, rgba(255,255,255,0.06));
    border-radius: 8px;
    padding: 8px 12px;
    color: var(--text, #E6EAF2);
    font-size: 0.9rem;
    font-family: 'Consolas', monospace;
    outline: none;
  }
  .host-input:focus { border-color: var(--accent, #06A6C9); }

  .port-group {
    display: flex;
    gap: 4px;
    align-items: center;
  }
  .port-input {
    width: 80px;
    background: rgba(0,0,0,0.3);
    border: 1px solid var(--border-subtle, rgba(255,255,255,0.06));
    border-radius: 8px;
    padding: 8px 10px;
    color: var(--text, #E6EAF2);
    font-size: 0.9rem;
    font-family: 'Consolas', monospace;
    outline: none;
  }
  .port-input:focus { border-color: var(--accent, #06A6C9); }

  .btn-port-picker {
    background: rgba(0,0,0,0.3);
    border: 1px solid var(--border-subtle, rgba(255,255,255,0.06));
    border-radius: 8px;
    padding: 8px;
    color: var(--text-dim, #94A3B8);
    cursor: pointer;
    font-size: 0.9rem;
  }
  .btn-port-picker:hover { background: rgba(255,255,255,0.05); }

  .option-group {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .option-group label {
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .option-group span {
    color: var(--text-dim, #94A3B8);
    font-size: 0.75rem;
  }
  .small-input {
    width: 60px;
    background: rgba(0,0,0,0.3);
    border: 1px solid var(--border-subtle, rgba(255,255,255,0.06));
    border-radius: 6px;
    padding: 6px;
    color: var(--text, #E6EAF2);
    font-size: 0.85rem;
    text-align: center;
    outline: none;
  }

  .btn-run {
    background: var(--accent, #06A6C9);
    border: none;
    border-radius: 8px;
    padding: 8px 20px;
    color: #fff;
    cursor: pointer;
    font-size: 0.85rem;
    font-weight: 600;
    white-space: nowrap;
    transition: opacity 0.15s;
  }
  .btn-run:disabled { opacity: 0.5; cursor: not-allowed; }
  .btn-run:not(:disabled):hover { opacity: 0.85; }

  /* ── Port picker ─────────────────────────────────────── */

  .port-picker {
    margin-top: 8px;
    background: rgba(0,0,0,0.3);
    border: 1px solid var(--border-subtle, rgba(255,255,255,0.06));
    border-radius: 10px;
    padding: 12px;
    max-height: 200px;
    overflow-y: auto;
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
  }
  .port-category { min-width: 180px; }
  .port-cat-name {
    color: var(--text-dim, #94A3B8);
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 4px;
  }
  .port-items { display: flex; flex-wrap: wrap; gap: 4px; }
  .port-item {
    background: transparent;
    border: 1px solid var(--border-subtle, rgba(255,255,255,0.06));
    border-radius: 6px;
    padding: 3px 8px;
    color: var(--text-dim, #94A3B8);
    cursor: pointer;
    font-size: 0.7rem;
    display: flex;
    gap: 4px;
    transition: all 0.15s;
  }
  .port-item:hover { background: rgba(255,255,255,0.05); }
  .port-item.active { border-color: var(--accent, #06A6C9); color: var(--text, #E6EAF2); }
  .port-num { font-weight: 600; color: var(--accent, #06A6C9); }

  /* ── Output area ─────────────────────────────────────── */

  .output-area {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
  }

  .output-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 16px;
    border-bottom: 1px solid var(--border-subtle, rgba(255,255,255,0.06));
    flex-shrink: 0;
  }
  .status-ok { color: #10B981; font-size: 0.85rem; }
  .status-err { color: #EF4444; font-size: 0.85rem; }
  .status-idle { color: var(--text-dim, #94A3B8); font-size: 0.85rem; }

  .output-actions { display: flex; gap: 6px; }
  .btn-small {
    background: transparent;
    border: 1px solid var(--border-subtle, rgba(255,255,255,0.06));
    border-radius: 6px;
    padding: 3px 10px;
    color: var(--text-dim, #94A3B8);
    cursor: pointer;
    font-size: 0.7rem;
    transition: all 0.15s;
  }
  .btn-small:hover:not(:disabled) { background: rgba(255,255,255,0.05); }
  .btn-small:disabled { opacity: 0.4; cursor: default; }

  .output-content {
    flex: 1;
    overflow-y: auto;
    padding: 12px 16px;
    font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
    font-size: 0.8rem;
    line-height: 1.6;
  }

  .output-line { white-space: pre-wrap; word-break: break-all; }
  .output-line.cmd { color: #60A5FA; }
  .output-line.ok { color: #22C55E; }
  .output-line.err { color: #EF4444; }
  .output-line.warn { color: #F59E0B; }
  .output-line.section { color: #93C5FD; }

  .output-loading {
    color: #F59E0B;
    text-align: center;
    padding: 40px;
  }
  .output-empty {
    color: var(--text-dim, #64748B);
    text-align: center;
    padding: 60px 20px;
    font-family: inherit;
  }

  /* ── Tool panel (non-network tabs) ──────────────────── */

  .tool-panel {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow-y: auto;
    min-height: 0;
  }

  /* ── Password generator ─────────────────────────────── */

  .pw-config {
    padding: 16px;
    border-bottom: 1px solid var(--border-subtle, rgba(255,255,255,0.06));
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .pw-row {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .pw-label {
    color: var(--text-dim, #94A3B8);
    font-size: 0.85rem;
    min-width: 120px;
  }
  .pw-label strong {
    color: var(--text, #E6EAF2);
  }
  .pw-slider {
    flex: 1;
    accent-color: var(--accent, #06A6C9);
    max-width: 300px;
  }
  .pw-options {
    display: flex;
    flex-wrap: wrap;
    gap: 8px 20px;
  }
  .pw-check {
    display: flex;
    align-items: center;
    gap: 6px;
    color: var(--text-dim, #94A3B8);
    font-size: 0.8rem;
    cursor: pointer;
  }
  .pw-check input[type="checkbox"] {
    accent-color: var(--accent, #06A6C9);
  }

  .pw-results {
    padding: 12px 16px;
    display: flex;
    flex-direction: column;
    gap: 6px;
    overflow-y: auto;
  }
  .pw-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 12px;
    background: rgba(0,0,0,0.2);
    border: 1px solid var(--border-subtle, rgba(255,255,255,0.06));
    border-radius: 8px;
  }
  .pw-index {
    color: var(--text-dim, #64748B);
    font-size: 0.7rem;
    font-weight: 600;
    min-width: 24px;
  }
  .pw-value {
    flex: 1;
    font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
    font-size: 0.85rem;
    color: var(--text, #E6EAF2);
    word-break: break-all;
  }
  .pw-strength {
    font-size: 0.7rem;
    font-weight: 600;
    white-space: nowrap;
  }
  .btn-copy-sm {
    background: transparent;
    border: 1px solid var(--border-subtle, rgba(255,255,255,0.06));
    border-radius: 6px;
    padding: 3px 8px;
    color: var(--text-dim, #94A3B8);
    cursor: pointer;
    font-size: 0.75rem;
  }
  .btn-copy-sm:hover { background: rgba(255,255,255,0.05); }

  /* ── IP/CIDR Calculator ─────────────────────────────── */

  .quick-prefixes {
    display: flex;
    gap: 4px;
    margin-top: 8px;
    flex-wrap: wrap;
  }
  .prefix-btn {
    background: rgba(0,0,0,0.3);
    border: 1px solid var(--border-subtle, rgba(255,255,255,0.06));
    border-radius: 6px;
    padding: 4px 10px;
    color: var(--accent, #06A6C9);
    cursor: pointer;
    font-size: 0.75rem;
    font-weight: 600;
    font-family: 'Consolas', monospace;
    transition: all 0.15s;
  }
  .prefix-btn:hover { background: rgba(6,166,201,0.15); }

  .cidr-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 8px;
    padding: 16px;
  }
  .cidr-cell {
    background: rgba(0,0,0,0.2);
    border: 1px solid var(--border-subtle, rgba(255,255,255,0.06));
    border-radius: 8px;
    padding: 10px 14px;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  .cidr-label {
    color: var(--text-dim, #64748B);
    font-size: 0.65rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  .cidr-value {
    color: var(--text, #E6EAF2);
    font-family: 'Cascadia Code', 'Consolas', monospace;
    font-size: 0.9rem;
  }

  .subnets-section {
    padding: 0 16px 16px;
  }
  .subnets-section h3 {
    color: var(--text-dim, #94A3B8);
    font-size: 0.8rem;
    font-weight: 600;
    margin: 0 0 8px;
  }
  .subnets-list {
    display: flex;
    flex-direction: column;
    gap: 4px;
    max-height: 200px;
    overflow-y: auto;
  }
  .subnet-item {
    display: flex;
    gap: 12px;
    padding: 6px 10px;
    background: rgba(0,0,0,0.15);
    border-radius: 6px;
    font-size: 0.75rem;
    font-family: 'Consolas', monospace;
  }
  .subnet-network { color: var(--accent, #06A6C9); font-weight: 600; min-width: 160px; }
  .subnet-range { color: var(--text-dim, #94A3B8); flex: 1; }
  .subnet-hosts { color: #10B981; white-space: nowrap; }

  .error-message {
    color: #EF4444;
    padding: 20px;
    text-align: center;
    font-size: 0.9rem;
  }

  /* ── Wake-on-LAN ────────────────────────────────────── */

  .wol-form {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .form-group {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .form-label {
    color: var(--text-dim, #94A3B8);
    font-size: 0.75rem;
    font-weight: 600;
  }
  .form-row {
    display: flex;
    gap: 8px;
    align-items: flex-end;
  }
  .btn-wol {
    height: 38px;
  }

  .wol-result {
    margin: 12px 16px;
    padding: 12px 16px;
    border-radius: 8px;
    font-size: 0.85rem;
  }
  .wol-ok {
    background: rgba(16,185,129,0.1);
    border: 1px solid rgba(16,185,129,0.3);
    color: #10B981;
  }
  .wol-err {
    background: rgba(239,68,68,0.1);
    border: 1px solid rgba(239,68,68,0.3);
    color: #EF4444;
  }

  .wol-history {
    padding: 0 16px 16px;
  }
  .wol-history h3 {
    color: var(--text-dim, #94A3B8);
    font-size: 0.8rem;
    font-weight: 600;
    margin: 0 0 8px;
  }
  .wol-hist-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 6px 10px;
    background: rgba(0,0,0,0.15);
    border-radius: 6px;
    margin-bottom: 4px;
    font-size: 0.75rem;
  }
  .wol-hist-mac {
    color: var(--text, #E6EAF2);
    font-family: 'Consolas', monospace;
    font-weight: 600;
  }
  .wol-hist-bc { color: var(--text-dim, #94A3B8); }
  .wol-hist-time { color: var(--text-dim, #64748B); margin-left: auto; }

  /* ── WHOIS ──────────────────────────────────────────── */

  .output-area-inner {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
    overflow: hidden;
  }
  .whois-output {
    flex: 1;
    overflow-y: auto;
    padding: 12px 16px;
    font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
    font-size: 0.75rem;
    line-height: 1.5;
    color: var(--text, #E6EAF2);
    white-space: pre-wrap;
    word-break: break-all;
    margin: 0;
    background: rgba(0,0,0,0.15);
  }

  /* ── Sidebar ─────────────────────────────────────────── */

  .sidebar {
    width: 220px;
    background: var(--bg-card, rgba(13,24,42,0.7));
    border: 1px solid var(--border-subtle, rgba(255,255,255,0.06));
    border-radius: 12px;
    padding: 12px;
    display: flex;
    flex-direction: column;
    gap: 6px;
    overflow-y: auto;
    flex-shrink: 0;
  }
  .sidebar-title {
    color: var(--text-dim, #94A3B8);
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    padding: 0 4px 4px;
  }
  .sidebar-empty {
    color: var(--text-dim, #64748B);
    font-size: 0.75rem;
    padding: 8px;
    text-align: center;
  }

  .history-item {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    padding: 6px 8px;
    background: transparent;
    border: 1px solid transparent;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.15s;
    text-align: left;
  }
  .history-item:hover { background: rgba(255,255,255,0.03); border-color: var(--border-subtle, rgba(255,255,255,0.06)); }

  .history-type {
    font-size: 0.55rem;
    font-weight: 700;
    background: rgba(6,166,201,0.15);
    color: var(--accent, #06A6C9);
    padding: 1px 5px;
    border-radius: 3px;
  }
  .history-host {
    font-size: 0.75rem;
    color: var(--text, #E6EAF2);
    font-family: 'Consolas', monospace;
    flex: 1;
  }
  .history-time {
    font-size: 0.6rem;
    color: var(--text-dim, #64748B);
    width: 100%;
  }

  /* ── Port Scanner ─────────────────────────────────────── */
  .port-presets {
    display: flex; align-items: center; gap: 6px; margin-top: 8px; flex-wrap: wrap;
  }
  .preset-label { font-size: 0.75rem; color: rgba(255,255,255,0.4); }
  .btn-preset {
    background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.1);
    border-radius: 6px; padding: 3px 10px; font-size: 0.72rem; color: rgba(255,255,255,0.6);
    cursor: pointer; font-family: inherit; transition: all 0.15s;
  }
  .btn-preset:hover { background: rgba(108,99,255,0.15); border-color: rgba(108,99,255,0.3); color: #fff; }
  .scan-results-grid {
    display: grid; grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); gap: 8px;
    padding: 16px;
  }
  .scan-port-card {
    display: flex; flex-direction: column; align-items: center; gap: 4px;
    padding: 12px 8px; border-radius: 10px; text-align: center;
    border: 1px solid rgba(255,255,255,0.06);
    background: rgba(255,255,255,0.03); transition: all 0.15s;
  }
  .scan-port-card.port-open {
    border-color: rgba(34,197,94,0.3); background: rgba(34,197,94,0.08);
  }
  .scan-port-card.port-closed {
    border-color: rgba(239,68,68,0.2); background: rgba(239,68,68,0.04);
  }
  .port-number { font-size: 1.1rem; font-weight: 700; color: #fff; font-family: 'Consolas', monospace; }
  .port-status { font-size: 0.72rem; }
  .port-service { font-size: 0.68rem; color: rgba(255,255,255,0.4); }
  .scan-progress { text-align: center; padding: 12px; font-size: 0.82rem; color: rgba(255,255,255,0.5); }

  /* ── QR Code ──────────────────────────────────────────── */
  .qr-type-row {
    display: flex; gap: 6px; margin-bottom: 8px;
  }
  .qr-type-btn {
    background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.1);
    border-radius: 8px; padding: 7px 14px; font-size: 0.8rem; color: rgba(255,255,255,0.6);
    cursor: pointer; font-family: inherit; transition: all 0.15s;
  }
  .qr-type-btn:hover { background: rgba(255,255,255,0.1); color: #fff; }
  .qr-type-btn.active {
    background: rgba(108,99,255,0.15); border-color: var(--accent, #6C63FF);
    color: #fff; font-weight: 600;
  }
  .qr-result {
    display: flex; flex-direction: column; align-items: center; gap: 16px; padding: 32px;
  }
  .qr-preview {
    background: #fff; border-radius: 12px; padding: 16px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.2);
  }
  .qr-preview img { display: block; border-radius: 4px; }
  .qr-actions { display: flex; gap: 8px; }
</style>
