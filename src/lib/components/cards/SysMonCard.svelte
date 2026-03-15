<script>
  import { onMount, onDestroy } from 'svelte';
  import { api } from '../../api/client.js';
  import GlassCard from '../GlassCard.svelte';

  let cpu = 0;
  let ram = 0;
  let disk = 0;
  let ramFree = '0';
  let diskFree = '0';
  let interval;

  export function refresh() {
    fetchData();
  }

  onMount(() => {
    fetchData();
    interval = setInterval(fetchData, 2000);
  });

  onDestroy(() => {
    if (interval) clearInterval(interval);
  });

  async function fetchData() {
    try {
      const data = await api.get('/api/dashboard/sysmon');
      cpu = data.cpu_percent || 0;
      ram = data.ram_percent || 0;
      disk = data.disk_percent || 0;
      ramFree = data.ram_free_gb || '0';
      diskFree = data.disk_free_gb || '0';
    } catch (e) {
      // keep last values
    }
  }

  function barColor(val) {
    if (val > 85) return 'var(--danger)';
    if (val > 65) return 'var(--warning)';
    return null; // use default
  }

  function statusColor(val) {
    if (val > 85) return 'var(--danger)';
    if (val > 65) return 'var(--warning)';
    return 'var(--success)';
  }
</script>

<GlassCard padding="0">
  <div class="card-inner">
    <div class="card-header">
      <h3>{'\u{1F4BB}'} Syst&egrave;me</h3>
      <span class="status-dot" style="background: {statusColor(Math.max(cpu, ram, disk))}"></span>
    </div>

    <div class="bars">
      <div class="bar-row">
        <span class="bar-label">CPU</span>
        <div class="bar-track">
          <div
            class="bar-fill bar-cpu"
            style="width: {cpu}%; {barColor(cpu) ? `background: ${barColor(cpu)};` : ''}"
          ></div>
        </div>
        <span class="bar-value">{Math.round(cpu)}%</span>
      </div>

      <div class="bar-row">
        <span class="bar-label">RAM</span>
        <div class="bar-track">
          <div
            class="bar-fill bar-ram"
            style="width: {ram}%; {barColor(ram) ? `background: ${barColor(ram)};` : ''}"
          ></div>
        </div>
        <span class="bar-value">{Math.round(ram)}%</span>
      </div>

      <div class="bar-row">
        <span class="bar-label">Disque</span>
        <div class="bar-track">
          <div
            class="bar-fill bar-disk"
            style="width: {disk}%; {barColor(disk) ? `background: ${barColor(disk)};` : ''}"
          ></div>
        </div>
        <span class="bar-value">{Math.round(disk)}%</span>
      </div>
    </div>

    <div class="info-line">
      RAM libre: {ramFree} Go / Disque libre: {diskFree} Go
    </div>
  </div>
</GlassCard>

<style>
  .card-inner {
    display: flex;
    flex-direction: column;
  }

  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 20px 12px;
    border-bottom: 1px solid var(--border-subtle);
  }

  .card-header h3 {
    font-size: 14px;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0;
  }

  .status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
    animation: pulse-glow 2s infinite;
  }

  .bars {
    padding: 16px 20px;
    display: flex;
    flex-direction: column;
    gap: 14px;
  }

  .bar-row {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .bar-label {
    font-size: 12px;
    font-weight: 500;
    color: var(--text-secondary);
    width: 44px;
    flex-shrink: 0;
  }

  .bar-track {
    flex: 1;
    height: 8px;
    background: rgba(255, 255, 255, 0.06);
    border-radius: 4px;
    overflow: hidden;
  }

  .bar-fill {
    height: 100%;
    border-radius: 4px;
    transition: width 0.5s ease, background 0.3s ease;
  }

  .bar-cpu {
    background: var(--info);
  }

  .bar-ram {
    background: #14B8A6;
  }

  .bar-disk {
    background: #8B5CF6;
  }

  .bar-value {
    font-size: 12px;
    font-weight: 600;
    color: var(--text-primary);
    width: 36px;
    text-align: right;
    flex-shrink: 0;
  }

  .info-line {
    padding: 10px 20px 14px;
    font-size: 11.5px;
    color: var(--text-muted);
    border-top: 1px solid var(--border-subtle);
  }
</style>
