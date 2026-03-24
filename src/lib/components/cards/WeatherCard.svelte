<script>
  import { onMount } from 'svelte';
  import GlassCard from '../GlassCard.svelte';

  let weather = null;
  let loading = true;

  export async function refresh() { await loadWeather(); }

  onMount(loadWeather);

  async function loadWeather() {
    loading = true;
    try {
      const res = await fetch('http://localhost:8010/api/dashboard/weather');
      weather = await res.json();
    } catch { weather = null; }
    loading = false;
  }
</script>

<GlassCard padding="0">
  <div class="card-inner">
    <div class="card-header">
      <h3>{'\u{1F326}\uFE0F'} M{'\u00e9'}t{'\u00e9'}o</h3>
      {#if weather?.city}
        <span class="city">{weather.city}</span>
      {/if}
    </div>

    {#if loading}
      <div class="weather-loading">Chargement...</div>
    {:else if weather?.temperature != null}
      <div class="weather-current">
        <span class="weather-emoji">{weather.emoji}</span>
        <div class="weather-info">
          <span class="weather-temp">{Math.round(weather.temperature)}{'\u00b0'}C</span>
          <span class="weather-desc">{weather.description}</span>
        </div>
        <div class="weather-details">
          <span>{'\u{1F4A7}'} {weather.humidity}%</span>
          <span>{'\u{1F32C}\uFE0F'} {Math.round(weather.wind_speed)} km/h</span>
        </div>
      </div>

      {#if weather.forecast?.length > 0}
        <div class="forecast">
          {#each weather.forecast as day}
            <div class="forecast-day">
              <span class="fc-date">{new Date(day.date + 'T00:00').toLocaleDateString('fr-FR', { weekday: 'short' })}</span>
              <span class="fc-emoji">{day.emoji}</span>
              <span class="fc-temps">
                <span class="fc-max">{Math.round(day.temp_max)}{'\u00b0'}</span>
                <span class="fc-min">{Math.round(day.temp_min)}{'\u00b0'}</span>
              </span>
            </div>
          {/each}
        </div>
      {/if}
    {:else}
      <div class="weather-loading">M{'\u00e9'}t{'\u00e9'}o indisponible</div>
    {/if}
  </div>
</GlassCard>

<style>
  .card-inner { display: flex; flex-direction: column; flex: 1; }
  .card-header {
    padding: 16px 20px 12px;
    border-bottom: 1px solid var(--border-subtle);
    display: flex; justify-content: space-between; align-items: center;
  }
  .card-header h3 { font-size: 14px; font-weight: 600; color: var(--text-primary); margin: 0; }
  .city { font-size: 12px; color: var(--text-muted); }

  .weather-loading {
    padding: 24px; text-align: center; color: var(--text-muted); font-size: 13px;
  }

  .weather-current {
    display: flex; align-items: center; gap: 14px;
    padding: 16px 20px;
  }
  .weather-emoji { font-size: 36px; line-height: 1; }
  .weather-info { display: flex; flex-direction: column; }
  .weather-temp { font-size: 28px; font-weight: 700; color: var(--text-primary); line-height: 1; }
  .weather-desc { font-size: 12px; color: var(--text-secondary); margin-top: 2px; }
  .weather-details {
    margin-left: auto;
    display: flex; flex-direction: column; gap: 4px;
    font-size: 11px; color: var(--text-muted); text-align: right;
  }

  .forecast {
    display: flex; justify-content: space-around;
    padding: 10px 16px 14px;
    border-top: 1px solid var(--border-subtle);
  }
  .forecast-day {
    display: flex; flex-direction: column; align-items: center; gap: 4px;
  }
  .fc-date { font-size: 11px; font-weight: 600; color: var(--text-secondary); text-transform: capitalize; }
  .fc-emoji { font-size: 18px; }
  .fc-temps { display: flex; gap: 6px; font-size: 12px; }
  .fc-max { color: var(--text-primary); font-weight: 600; }
  .fc-min { color: var(--text-muted); }
</style>
