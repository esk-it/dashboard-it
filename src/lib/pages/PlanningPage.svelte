<script>
  import { onMount, onDestroy } from 'svelte';
  import { api } from '../api/client.js';
  import { currentPage } from '../stores/navigation.js';

  // ---------------------------------------------------------------------------
  // Constants
  // ---------------------------------------------------------------------------
  const JOURS_COURTS = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'];
  const MOIS_NOMS = [
    'janvier','février','mars','avril','mai','juin',
    'juillet','août','septembre','octobre','novembre','décembre',
  ];

  const EVENT_TYPES = {
    meeting:      { emoji: '🤝', label: 'Réunion',      color: '#4B8BFF' },
    intervention: { emoji: '🔧', label: 'Intervention',  color: '#F59E0B' },
    maintenance:  { emoji: '⚙️',  label: 'Maintenance',   color: '#8B5CF6' },
    leave:        { emoji: '🏖️',  label: 'Congé',        color: '#22C55E' },
    milestone:    { emoji: '🏁', label: 'Jalon',         color: '#EC4899' },
    other:        { emoji: '📌', label: 'Autre',         color: '#64748B' },
  };

  const HOURS = Array.from({ length: 24 }, (_, i) => i);

  // ---------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------
  let view = 'month'; // 'month' | 'week' | 'day'
  let refDate = new Date();     // anchor date for navigation
  let events = [];
  let calendarTasks = [];
  let loading = false;

  // Dialog
  let showDialog = false;
  let editingEvent = null; // null = create, object = edit
  let form = defaultForm();

  // Current time line
  let nowMinutes = 0;
  let clockTimer;

  // Open tasks for linking
  let openTasks = [];

  // ---------------------------------------------------------------------------
  // Derived
  // ---------------------------------------------------------------------------
  $: today = toDateStr(new Date());
  $: viewMonth = refDate.getMonth();
  $: viewYear = refDate.getFullYear();
  $: monthLabel = `${MOIS_NOMS[viewMonth].charAt(0).toUpperCase() + MOIS_NOMS[viewMonth].slice(1)} ${viewYear}`;
  $: dayLabel = refDate.toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });

  // Compute week range (Mon-Sun around refDate)
  $: weekStart = getWeekStart(refDate);
  $: weekDays = Array.from({ length: 7 }, (_, i) => {
    const d = new Date(weekStart);
    d.setDate(d.getDate() + i);
    return d;
  });

  // Compute month grid
  $: monthGrid = buildMonthGrid(viewYear, viewMonth);

  // Fetch range based on view
  $: fetchRange = computeFetchRange(view, viewYear, viewMonth, weekStart);
  $: if (fetchRange) fetchEvents();

  // Group events by date for month view
  $: eventsByDate = groupEventsByDate(events, calendarTasks);

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  function defaultForm() {
    return {
      title: '',
      event_type: 'other',
      date_start: toDateStr(new Date()),
      date_end: toDateStr(new Date()),
      all_day: true,
      time_start: '09:00',
      time_end: '10:00',
      person: '',
      notes: '',
      task_id: null,
    };
  }

  function toDateStr(d) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const dd = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${dd}`;
  }

  function parseDate(str) {
    const [y, m, d] = str.split('-').map(Number);
    return new Date(y, m - 1, d);
  }

  function getWeekStart(d) {
    const copy = new Date(d);
    const day = copy.getDay();
    const diff = day === 0 ? -6 : 1 - day; // Monday
    copy.setDate(copy.getDate() + diff);
    copy.setHours(0, 0, 0, 0);
    return copy;
  }

  function buildMonthGrid(year, month) {
    const first = new Date(year, month, 1);
    let startDay = first.getDay(); // 0=Sun
    startDay = startDay === 0 ? 6 : startDay - 1; // shift to Mon=0

    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const cells = [];

    // Previous month fill
    const prevMonthDays = new Date(year, month, 0).getDate();
    for (let i = startDay - 1; i >= 0; i--) {
      const d = new Date(year, month - 1, prevMonthDays - i);
      cells.push({ date: d, dateStr: toDateStr(d), currentMonth: false });
    }

    // Current month
    for (let i = 1; i <= daysInMonth; i++) {
      const d = new Date(year, month, i);
      cells.push({ date: d, dateStr: toDateStr(d), currentMonth: true });
    }

    // Next month fill to complete rows of 7
    while (cells.length % 7 !== 0) {
      const d = new Date(year, month + 1, cells.length - startDay - daysInMonth + 1);
      cells.push({ date: d, dateStr: toDateStr(d), currentMonth: false });
    }

    return cells;
  }

  function computeFetchRange(v, year, month, ws) {
    if (v === 'month') {
      const start = new Date(year, month - 1, 1);
      const end = new Date(year, month + 2, 0);
      return { start: toDateStr(start), end: toDateStr(end) };
    } else if (v === 'day') {
      const ds = toDateStr(refDate);
      return { start: ds, end: ds };
    } else {
      const end = new Date(ws);
      end.setDate(end.getDate() + 6);
      return { start: toDateStr(ws), end: toDateStr(end) };
    }
  }

  function groupEventsByDate(evts, tasks) {
    const map = {};
    for (const evt of evts) {
      const s = parseDate(evt.date_start);
      const e = parseDate(evt.date_end);
      for (let d = new Date(s); d <= e; d.setDate(d.getDate() + 1)) {
        const ds = toDateStr(d);
        if (!map[ds]) map[ds] = [];
        map[ds].push({ ...evt, _type: 'event' });
      }
    }
    for (const t of tasks) {
      const ds = t.due_date;
      if (!map[ds]) map[ds] = [];
      map[ds].push({ ...t, _type: 'task' });
    }
    return map;
  }

  function getEventsForDate(dateStr) {
    return eventsByDate[dateStr] || [];
  }

  function getEventColor(evt) {
    if (evt._type === 'task') return '#4B8BFF';
    return EVENT_TYPES[evt.event_type]?.color || '#64748B';
  }

  function getEventLabel(evt) {
    if (evt._type === 'task') return `✅ ${evt.title}`;
    const t = EVENT_TYPES[evt.event_type];
    return t ? `${t.emoji} ${evt.title}` : evt.title;
  }

  function timeToMinutes(t) {
    if (!t) return 0;
    const [h, m] = t.split(':').map(Number);
    return h * 60 + m;
  }

  function minutesToPx(m) {
    return (m / 60) * 56; // 56px per hour
  }

  // Events that overlap a specific day for week view
  function getWeekDayEvents(dateStr) {
    const items = getEventsForDate(dateStr);
    const allDay = items.filter(e => e._type === 'task' || (e._type === 'event' && e.all_day));
    const timed = items.filter(e => e._type === 'event' && !e.all_day && e.time_start);
    return { allDay, timed };
  }

  function isWeekend(dateStr) {
    const d = parseDate(dateStr);
    const day = d.getDay();
    return day === 0 || day === 6;
  }

  function updateNow() {
    const n = new Date();
    nowMinutes = n.getHours() * 60 + n.getMinutes();
  }

  // ---------------------------------------------------------------------------
  // API
  // ---------------------------------------------------------------------------
  async function fetchEvents() {
    if (!fetchRange) return;
    loading = true;
    try {
      const [evts, tasks] = await Promise.all([
        api.get(`/api/planning/events?start=${fetchRange.start}&end=${fetchRange.end}`),
        api.get(`/api/planning/tasks-for-calendar?start=${fetchRange.start}&end=${fetchRange.end}`),
      ]);
      events = evts;
      calendarTasks = tasks;
    } catch (e) {
      console.error('Failed to fetch planning data', e);
    } finally {
      loading = false;
    }
  }

  async function fetchOpenTasks() {
    try {
      openTasks = await api.get('/api/tasks?status=open');
    } catch {
      openTasks = [];
    }
  }

  async function saveEvent() {
    const payload = { ...form };
    if (payload.all_day) {
      payload.time_start = null;
      payload.time_end = null;
    }
    if (!payload.task_id) payload.task_id = null;

    try {
      if (editingEvent) {
        await api.put(`/api/planning/events/${editingEvent.id}`, payload);
      } else {
        await api.post('/api/planning/events', payload);
      }
      showDialog = false;
      await fetchEvents();
    } catch (e) {
      console.error('Failed to save event', e);
    }
  }

  async function deleteEvent() {
    if (!editingEvent) return;
    try {
      await api.delete(`/api/planning/events/${editingEvent.id}`);
      showDialog = false;
      await fetchEvents();
    } catch (e) {
      console.error('Failed to delete event', e);
    }
  }

  // ---------------------------------------------------------------------------
  // Navigation
  // ---------------------------------------------------------------------------
  function prev() {
    const d = new Date(refDate);
    if (view === 'month') d.setMonth(d.getMonth() - 1);
    else if (view === 'day') d.setDate(d.getDate() - 1);
    else d.setDate(d.getDate() - 7);
    refDate = d;
  }

  function next() {
    const d = new Date(refDate);
    if (view === 'month') d.setMonth(d.getMonth() + 1);
    else if (view === 'day') d.setDate(d.getDate() + 1);
    else d.setDate(d.getDate() + 7);
    refDate = d;
  }

  function goToday() {
    refDate = new Date();
  }

  // ---------------------------------------------------------------------------
  // Dialog open helpers
  // ---------------------------------------------------------------------------
  function openNewEvent(dateStr, timeStr = null) {
    editingEvent = null;
    form = defaultForm();
    form.date_start = dateStr;
    form.date_end = dateStr;
    if (timeStr) {
      form.all_day = false;
      form.time_start = timeStr;
      const [h, m] = timeStr.split(':').map(Number);
      form.time_end = `${String(h + 1).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
    }
    fetchOpenTasks();
    showDialog = true;
  }

  function openEditEvent(evt) {
    if (evt._type === 'task') {
      currentPage.set('/tasks');
      return;
    }
    editingEvent = evt;
    form = {
      title: evt.title,
      event_type: evt.event_type || 'other',
      date_start: evt.date_start,
      date_end: evt.date_end,
      all_day: evt.all_day,
      time_start: evt.time_start || '09:00',
      time_end: evt.time_end || '10:00',
      person: evt.person || '',
      notes: evt.notes || '',
      task_id: evt.task_id || null,
    };
    fetchOpenTasks();
    showDialog = true;
  }

  function handleDayCellClick(e, dateStr) {
    // Only open new event if clicking directly on the cell (not on an event chip)
    if (e.target.closest('.event-chip')) return;
    openNewEvent(dateStr);
  }

  function handleTimeSlotClick(dateStr, hour) {
    const timeStr = `${String(hour).padStart(2, '0')}:00`;
    openNewEvent(dateStr, timeStr);
  }

  // ---------------------------------------------------------------------------
  // Lifecycle
  // ---------------------------------------------------------------------------
  onMount(() => {
    updateNow();
    clockTimer = setInterval(updateNow, 60000);
  });

  onDestroy(() => {
    if (clockTimer) clearInterval(clockTimer);
  });
</script>

<div class="planning-page">
  <!-- Top bar -->
  <header class="planning-header">
    <div class="nav-controls">
      <button class="nav-btn" on:click={prev}>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
      </button>
      <button class="nav-btn" on:click={next}>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
      </button>
      <button class="today-btn" on:click={goToday}>Aujourd'hui</button>
      <h2 class="month-label">
        {#if view === 'day'}{dayLabel}{:else}{monthLabel}{/if}
      </h2>
    </div>
    <div class="view-controls">
      <div class="legend">
        {#each Object.entries(EVENT_TYPES) as [key, t]}
          <span class="legend-item">
            <span class="legend-dot" style="background:{t.color}"></span>
            <span class="legend-emoji">{t.emoji}</span>
            {t.label}
          </span>
        {/each}
        <span class="legend-item">
          <span class="legend-dot task-dot"></span>
          <span class="legend-emoji">✅</span>
          Tâche
        </span>
      </div>
      <div class="segmented">
        <button class="seg-btn" class:active={view === 'month'} on:click={() => view = 'month'}>Mois</button>
        <button class="seg-btn" class:active={view === 'week'} on:click={() => view = 'week'}>Semaine</button>
        <button class="seg-btn" class:active={view === 'day'} on:click={() => view = 'day'}>Jour</button>
      </div>
    </div>
  </header>

  <!-- Calendar container -->
  <div class="calendar-card">
    {#if view === 'month'}
      <!-- MONTH VIEW -->
      <div class="month-grid">
        {#each JOURS_COURTS as day, i}
          <div class="day-header" class:weekend-header={i >= 5}>{day}</div>
        {/each}

        {#each monthGrid as cell}
          {@const cellEvents = getEventsForDate(cell.dateStr)}
          <div
            class="day-cell"
            class:other-month={!cell.currentMonth}
            class:weekend-cell={isWeekend(cell.dateStr)}
            class:today-cell={cell.dateStr === today}
            on:click={(e) => handleDayCellClick(e, cell.dateStr)}
          >
            <span
              class="day-number"
              class:today-circle={cell.dateStr === today}
            >{cell.date.getDate()}</span>

            <div class="events-container">
              {#each cellEvents.slice(0, 3) as evt}
                <button
                  class="event-chip"
                  class:task-chip={evt._type === 'task'}
                  style="--chip-color:{getEventColor(evt)}"
                  on:click|stopPropagation={() => openEditEvent(evt)}
                  title={getEventLabel(evt)}
                >
                  <span class="chip-text">{getEventLabel(evt)}</span>
                </button>
              {/each}

              {#if cellEvents.length > 3}
                <span class="more-events">+{cellEvents.length - 3} de plus</span>
              {/if}
            </div>
          </div>
        {/each}
      </div>

    {:else if view === 'week'}
      <!-- WEEK VIEW -->
      <div class="week-view">
        <!-- Header row -->
        <div class="week-header">
          <div class="time-gutter-header"></div>
          {#each weekDays as wd}
            <div
              class="week-day-header"
              class:today-col={toDateStr(wd) === today}
            >
              <span class="wd-name">{JOURS_COURTS[wd.getDay() === 0 ? 6 : wd.getDay() - 1]}</span>
              <span
                class="wd-num"
                class:today-circle={toDateStr(wd) === today}
              >{wd.getDate()}</span>
            </div>
          {/each}
        </div>

        <!-- All-day strip -->
        <div class="all-day-strip">
          <div class="time-gutter all-day-label">Journée</div>
          {#each weekDays as wd}
            {@const items = getWeekDayEvents(toDateStr(wd)).allDay}
            <div class="all-day-cell" class:today-allday-col={toDateStr(wd) === today}>
              {#each items as evt}
                <button
                  class="event-chip small"
                  class:task-chip={evt._type === 'task'}
                  style="--chip-color:{getEventColor(evt)}"
                  on:click={() => openEditEvent(evt)}
                  title={getEventLabel(evt)}
                >
                  <span class="chip-text">{getEventLabel(evt)}</span>
                </button>
              {/each}
            </div>
          {/each}
        </div>

        <!-- Time grid -->
        <div class="time-grid-scroll">
          <div class="time-grid">
            <!-- Hour lines -->
            {#each HOURS as hour}
              <div class="hour-row" style="top:{hour * 56}px">
                <div class="time-gutter time-label">{String(hour).padStart(2,'0')}:00</div>
                <div class="hour-line"></div>
              </div>
              <div class="half-hour-line" style="top:{hour * 56 + 28}px"></div>
            {/each}

            <!-- Day columns -->
            <div class="day-columns">
              {#each weekDays as wd, i}
                {@const dateStr = toDateStr(wd)}
                {@const timedEvents = getWeekDayEvents(dateStr).timed}
                <div
                  class="day-column"
                  class:today-col-bg={dateStr === today}
                  class:weekend-col={isWeekend(dateStr)}
                >
                  <!-- Click targets per hour -->
                  {#each HOURS as hour}
                    <div
                      class="hour-slot"
                      style="top:{hour * 56}px; height:56px"
                      on:click={() => handleTimeSlotClick(dateStr, hour)}
                    ></div>
                  {/each}

                  <!-- Timed events -->
                  {#each timedEvents as evt}
                    {@const topPx = minutesToPx(timeToMinutes(evt.time_start))}
                    {@const endM = evt.time_end ? timeToMinutes(evt.time_end) : timeToMinutes(evt.time_start) + 60}
                    {@const heightPx = Math.max(minutesToPx(endM - timeToMinutes(evt.time_start)), 24)}
                    <button
                      class="timed-event"
                      style="
                        top:{topPx}px;
                        height:{heightPx}px;
                        --evt-color:{getEventColor(evt)};
                      "
                      on:click|stopPropagation={() => openEditEvent(evt)}
                    >
                      <span class="timed-title">{getEventLabel(evt)}</span>
                      <span class="timed-time">{evt.time_start} – {evt.time_end || ''}</span>
                    </button>
                  {/each}

                  <!-- Current time line -->
                  {#if dateStr === today}
                    <div class="now-line" style="top:{minutesToPx(nowMinutes)}px">
                      <div class="now-dot"></div>
                    </div>
                  {/if}
                </div>
              {/each}
            </div>
          </div>
        </div>
      </div>

    {:else}
      <!-- DAY VIEW -->
      {@const dayStr = toDateStr(refDate)}
      {@const dayEvents = getWeekDayEvents(dayStr)}
      <div class="day-view">
        <!-- All-day events -->
        {#if dayEvents.allDay.length > 0}
          <div class="day-allday-section">
            <div class="day-section-label">Journ{'\u00e9'}e enti{'\u00e8'}re</div>
            <div class="day-allday-list">
              {#each dayEvents.allDay as evt}
                <button
                  class="event-chip"
                  class:task-chip={evt._type === 'task'}
                  style="--chip-color:{getEventColor(evt)}"
                  on:click={() => openEditEvent(evt)}
                >
                  <span class="chip-text">{getEventLabel(evt)}</span>
                </button>
              {/each}
            </div>
          </div>
        {/if}

        <!-- Time grid (single column) -->
        <div class="day-time-grid-scroll">
          <div class="day-time-grid">
            {#each HOURS as hour}
              <div class="day-hour-row">
                <div class="day-time-label">{String(hour).padStart(2,'0')}:00</div>
                <!-- svelte-ignore a11y_click_events_have_key_events -->
                <!-- svelte-ignore a11y_no_static_element_interactions -->
                <div class="day-hour-slot" on:click={() => handleTimeSlotClick(dayStr, hour)}>
                  {#each dayEvents.timed.filter(e => {
                    const startH = timeToMinutes(e.time_start) / 60;
                    return Math.floor(startH) === hour;
                  }) as evt}
                    {@const topPx = (timeToMinutes(evt.time_start) % 60) / 60 * 64}
                    {@const endM = evt.time_end ? timeToMinutes(evt.time_end) : timeToMinutes(evt.time_start) + 60}
                    {@const heightPx = Math.max((endM - timeToMinutes(evt.time_start)) / 60 * 64, 28)}
                    <button
                      class="day-timed-event"
                      style="top:{topPx}px;height:{heightPx}px;--evt-color:{getEventColor(evt)}"
                      on:click|stopPropagation={() => openEditEvent(evt)}
                    >
                      <div class="day-evt-time">{evt.time_start} - {evt.time_end || ''}</div>
                      <div class="day-evt-title">{getEventLabel(evt)}</div>
                      {#if evt.person}<div class="day-evt-person">{'\u{1F464}'} {evt.person}</div>{/if}
                    </button>
                  {/each}
                </div>
              </div>
              <!-- Half-hour line -->
              <div class="day-hour-row day-half-row">
                <div class="day-time-label half-label">
                  {String(hour).padStart(2,'0')}:30
                </div>
                <div class="day-hour-half-line"></div>
              </div>
            {/each}

            <!-- Current time indicator -->
            {#if dayStr === today}
              <div class="day-now-indicator" style="top:{(nowMinutes / 60) * 128}px">
                <div class="day-now-dot"></div>
                <div class="day-now-line"></div>
              </div>
            {/if}
          </div>
        </div>
      </div>
    {/if}
  </div>
</div>

<!-- Event dialog -->
{#if showDialog}
  <div class="dialog-overlay" on:click|self={() => showDialog = false}>
    <div class="dialog">
      <div class="dialog-header">
        <h3>{editingEvent ? 'Modifier l\'événement' : 'Nouvel événement'}</h3>
        <button class="dialog-close" on:click={() => showDialog = false}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </button>
      </div>

      <label class="field">
        <span>Titre *</span>
        <input type="text" bind:value={form.title} placeholder="Titre de l'événement" />
      </label>

      <!-- Event type selector with colored icons -->
      <div class="field">
        <span>Type</span>
        <div class="type-selector">
          {#each Object.entries(EVENT_TYPES) as [key, t]}
            <button
              class="type-option"
              class:selected={form.event_type === key}
              style="--type-color:{t.color}"
              on:click={() => form.event_type = key}
              title={t.label}
            >
              <span class="type-emoji">{t.emoji}</span>
              <span class="type-label">{t.label}</span>
            </button>
          {/each}
        </div>
      </div>

      <label class="field">
        <span>Personne</span>
        <input type="text" bind:value={form.person} placeholder="Optionnel" />
      </label>

      <div class="field-row">
        <label class="field">
          <span>Date début</span>
          <input type="date" bind:value={form.date_start} />
        </label>
        <label class="field">
          <span>Date fin</span>
          <input type="date" bind:value={form.date_end} min={form.date_start} />
        </label>
      </div>

      <label class="field checkbox-field">
        <input type="checkbox" bind:checked={form.all_day} />
        <span>Journée entière</span>
      </label>

      {#if !form.all_day}
        <div class="field-row">
          <label class="field">
            <span>Heure début</span>
            <input type="time" bind:value={form.time_start} />
          </label>
          <label class="field">
            <span>Heure fin</span>
            <input type="time" bind:value={form.time_end} />
          </label>
        </div>
      {/if}

      <label class="field">
        <span>Notes</span>
        <textarea bind:value={form.notes} rows="3" placeholder="Notes optionnelles"></textarea>
      </label>

      <label class="field">
        <span>Lier à une tâche</span>
        <select bind:value={form.task_id}>
          <option value={null}>-- Aucune --</option>
          {#each openTasks as t}
            <option value={t.id}>{t.title}</option>
          {/each}
        </select>
      </label>

      <div class="dialog-actions">
        {#if editingEvent}
          <button class="btn-delete" on:click={deleteEvent}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
            Supprimer
          </button>
        {/if}
        <div class="spacer"></div>
        <button class="btn-cancel" on:click={() => showDialog = false}>Annuler</button>
        <button class="btn-save" on:click={saveEvent} disabled={!form.title.trim()}>
          {editingEvent ? 'Enregistrer' : 'Créer'}
        </button>
      </div>
    </div>
  </div>
{/if}

<style>
  /* =========================================================================
     Planning Page – Polished Design
     ========================================================================= */
  .planning-page {
    animation: fadeIn 0.35s ease-out;
    display: flex;
    flex-direction: column;
    height: calc(100vh - 56px);
    overflow: hidden;
  }

  /* =========================================================================
     Header / Navigation
     ========================================================================= */
  .planning-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 12px;
    margin-bottom: 12px;
    flex-shrink: 0;
  }

  .nav-controls {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .nav-btn {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: 10px;
    color: var(--text-secondary);
    width: 36px;
    height: 36px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s ease;
    font-family: inherit;
    backdrop-filter: blur(12px);
  }
  .nav-btn:hover {
    background: var(--bg-hover);
    border-color: var(--border-hover);
    color: var(--text-primary);
    transform: scale(1.05);
  }
  .nav-btn:active {
    transform: scale(0.97);
  }

  .today-btn {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: 10px;
    color: var(--text-secondary);
    font-size: 13px;
    padding: 7px 16px;
    cursor: pointer;
    transition: all 0.2s ease;
    font-family: inherit;
    backdrop-filter: blur(12px);
    font-weight: 500;
  }
  .today-btn:hover {
    background: rgba(var(--accent-rgb), 0.1);
    border-color: rgba(var(--accent-rgb), 0.3);
    color: var(--accent);
  }
  .today-btn:active {
    transform: scale(0.97);
  }

  .month-label {
    font-size: 22px;
    font-weight: 700;
    color: var(--text-primary);
    margin: 0 0 0 12px;
    letter-spacing: -0.3px;
  }

  .view-controls {
    display: flex;
    align-items: center;
    gap: 16px;
    flex-wrap: wrap;
  }

  .legend {
    display: flex;
    align-items: center;
    gap: 14px;
    font-size: 11.5px;
    color: var(--text-secondary);
    flex-wrap: wrap;
  }
  .legend-item {
    display: flex;
    align-items: center;
    gap: 4px;
  }
  .legend-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }
  .legend-dot.task-dot {
    background: #4B8BFF;
    border: 1.5px dashed rgba(75, 139, 255, 0.7);
    width: 9px;
    height: 9px;
  }
  .legend-emoji {
    font-size: 12px;
    line-height: 1;
  }

  .segmented {
    display: flex;
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: 10px;
    overflow: hidden;
    backdrop-filter: blur(12px);
  }
  .seg-btn {
    background: transparent;
    border: none;
    color: var(--text-secondary);
    font-size: 13px;
    padding: 7px 18px;
    cursor: pointer;
    transition: all 0.2s ease;
    font-family: inherit;
    font-weight: 500;
  }
  .seg-btn.active {
    background: var(--accent);
    color: #fff;
    box-shadow: 0 2px 8px rgba(var(--accent-rgb), 0.3);
  }
  .seg-btn:hover:not(.active) {
    background: var(--bg-hover);
    color: var(--text-primary);
  }

  /* =========================================================================
     Calendar Card (glass)
     ========================================================================= */
  .calendar-card {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: 16px;
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    overflow: hidden;
    box-shadow: 0 4px 24px rgba(0, 0, 0, 0.15);
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
  }

  /* =========================================================================
     Month View
     ========================================================================= */
  .month-grid {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    grid-template-rows: auto repeat(6, 1fr);
    flex: 1;
    min-height: 0;
  }

  .day-header {
    padding: 10px 8px;
    font-size: 11px;
    font-weight: 700;
    color: var(--text-secondary);
    text-align: center;
    text-transform: uppercase;
    letter-spacing: 1px;
    border-bottom: 1px solid var(--border-subtle);
    background: rgba(255, 255, 255, 0.01);
  }
  .day-header.weekend-header {
    color: var(--text-muted);
  }

  .day-cell {
    min-height: 0;
    padding: 6px 7px;
    overflow: hidden;
    border-right: 1px solid var(--border-subtle);
    border-bottom: 1px solid var(--border-subtle);
    cursor: pointer;
    transition: background 0.15s ease;
    display: flex;
    flex-direction: column;
    gap: 3px;
  }
  .day-cell:nth-child(7n + 7) {
    border-right: none;
  }
  .day-cell:hover {
    background: rgba(255, 255, 255, 0.03);
  }
  .day-cell.other-month {
    opacity: 0.3;
  }
  .day-cell.weekend-cell {
    background: rgba(255, 255, 255, 0.012);
  }
  .day-cell.today-cell {
    background: rgba(var(--accent-rgb), 0.04);
  }

  .day-number {
    font-size: 13px;
    font-weight: 500;
    color: var(--text-primary);
    width: 28px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    margin-bottom: 2px;
    transition: all 0.15s ease;
  }
  .day-number.today-circle {
    background: var(--accent);
    color: #fff;
    font-weight: 700;
    box-shadow: 0 2px 8px rgba(var(--accent-rgb), 0.35);
  }

  .events-container {
    display: flex;
    flex-direction: column;
    gap: 2px;
    flex: 1;
    min-height: 0;
  }

  /* Event Chips */
  .event-chip {
    display: flex;
    align-items: center;
    width: 100%;
    padding: 2px 6px;
    border: none;
    border-left: 3px solid var(--chip-color);
    border-radius: 4px;
    font-size: 11px;
    cursor: pointer;
    text-align: left;
    font-family: inherit;
    transition: all 0.15s ease;
    overflow: hidden;
    background: color-mix(in srgb, var(--chip-color) 12%, transparent);
    opacity: 0.88;
  }
  .event-chip:hover {
    opacity: 1;
    background: color-mix(in srgb, var(--chip-color) 20%, transparent);
    transform: translateX(1px);
  }
  .event-chip.small {
    font-size: 10px;
    padding: 1px 4px;
  }

  /* Task chips: dotted border, different style */
  .event-chip.task-chip {
    border-left: 3px dashed var(--chip-color);
    border-radius: 6px;
    background: color-mix(in srgb, var(--chip-color) 8%, transparent);
  }
  .event-chip.task-chip:hover {
    background: color-mix(in srgb, var(--chip-color) 16%, transparent);
  }

  .chip-text {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    color: var(--text-primary);
    line-height: 1.4;
  }

  .more-events {
    font-size: 10px;
    color: var(--accent);
    padding: 1px 6px;
    font-weight: 600;
    cursor: pointer;
    opacity: 0.8;
    transition: opacity 0.15s;
  }
  .more-events:hover {
    opacity: 1;
  }

  /* =========================================================================
     Week View
     ========================================================================= */
  .week-view {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
  }

  .week-header {
    display: grid;
    grid-template-columns: 56px repeat(7, 1fr);
    border-bottom: 1px solid var(--border-subtle);
    background: rgba(255, 255, 255, 0.01);
  }
  .time-gutter-header {
    /* empty corner */
  }
  .week-day-header {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 10px 4px 8px;
    gap: 4px;
    transition: background 0.15s;
  }
  .week-day-header.today-col {
    background: rgba(var(--accent-rgb), 0.06);
  }
  .wd-name {
    font-size: 11px;
    font-weight: 700;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 1px;
  }
  .wd-num {
    font-size: 22px;
    font-weight: 700;
    color: var(--text-primary);
    width: 38px;
    height: 38px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    transition: all 0.2s;
  }
  .wd-num.today-circle {
    background: var(--accent);
    color: #fff;
    box-shadow: 0 2px 10px rgba(var(--accent-rgb), 0.35);
  }

  /* All-day strip */
  .all-day-strip {
    display: grid;
    grid-template-columns: 56px repeat(7, 1fr);
    border-bottom: 1px solid var(--border-subtle);
    min-height: 32px;
    background: rgba(255, 255, 255, 0.008);
  }
  .all-day-label {
    font-size: 10px;
    color: var(--text-muted);
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 600;
    letter-spacing: 0.3px;
  }
  .all-day-cell {
    display: flex;
    flex-direction: column;
    gap: 2px;
    padding: 3px;
    border-left: 1px solid var(--border-subtle);
  }
  .all-day-cell.today-allday-col {
    background: rgba(var(--accent-rgb), 0.03);
  }

  /* Time grid */
  .time-grid-scroll {
    overflow-y: auto;
    flex: 1;
    min-height: 0;
  }
  .time-grid {
    position: relative;
    height: calc(24 * 56px);
  }

  .hour-row {
    position: absolute;
    left: 0;
    right: 0;
    height: 0;
    display: flex;
    align-items: center;
  }
  .time-label {
    width: 56px;
    font-size: 10px;
    color: var(--text-muted);
    text-align: right;
    padding-right: 8px;
    transform: translateY(-50%);
    flex-shrink: 0;
    font-weight: 500;
    font-variant-numeric: tabular-nums;
  }
  .hour-line {
    flex: 1;
    border-top: 1px solid var(--border-subtle);
  }
  .half-hour-line {
    position: absolute;
    left: 56px;
    right: 0;
    border-top: 1px dashed var(--border-subtle);
    opacity: 0.3;
  }

  .day-columns {
    position: absolute;
    top: 0;
    left: 56px;
    right: 0;
    bottom: 0;
    display: grid;
    grid-template-columns: repeat(7, 1fr);
  }
  .day-column {
    position: relative;
    border-left: 1px solid var(--border-subtle);
  }
  .day-column.today-col-bg {
    background: rgba(var(--accent-rgb), 0.025);
  }
  .day-column.weekend-col {
    background: rgba(255, 255, 255, 0.01);
  }

  .hour-slot {
    position: absolute;
    left: 0;
    right: 0;
    cursor: pointer;
    transition: background 0.1s;
  }
  .hour-slot:hover {
    background: rgba(255, 255, 255, 0.03);
  }

  .timed-event {
    position: absolute;
    left: 3px;
    right: 3px;
    border-radius: 6px;
    padding: 3px 6px;
    cursor: pointer;
    overflow: hidden;
    font-family: inherit;
    border: none;
    border-left: 3px solid var(--evt-color);
    background: color-mix(in srgb, var(--evt-color) 15%, transparent);
    transition: all 0.15s ease;
    display: flex;
    flex-direction: column;
    z-index: 1;
    opacity: 0.9;
  }
  .timed-event:hover {
    opacity: 1;
    background: color-mix(in srgb, var(--evt-color) 22%, transparent);
    z-index: 2;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
    transform: scale(1.01);
  }
  .timed-title {
    font-size: 11px;
    font-weight: 600;
    color: var(--text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .timed-time {
    font-size: 9.5px;
    color: var(--text-secondary);
    font-weight: 500;
  }

  /* Current time line */
  .now-line {
    position: absolute;
    left: -1px;
    right: 0;
    z-index: 3;
    pointer-events: none;
    border-top: 2px solid #EF4444;
  }
  .now-dot {
    width: 10px;
    height: 10px;
    background: #EF4444;
    border-radius: 50%;
    position: absolute;
    left: -5px;
    top: -6px;
    box-shadow: 0 0 6px rgba(239, 68, 68, 0.5);
  }

  /* =========================================================================
     Day View
     ========================================================================= */
  .day-view {
    flex: 1; display: flex; flex-direction: column; min-height: 0;
  }
  .day-allday-section {
    padding: 10px 16px; border-bottom: 1px solid var(--border-subtle);
    background: rgba(255,255,255,0.01);
  }
  .day-section-label {
    font-size: 11px; font-weight: 600; color: var(--text-muted);
    text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px;
  }
  .day-allday-list { display: flex; gap: 6px; flex-wrap: wrap; }

  .day-time-grid-scroll {
    flex: 1; overflow-y: auto; min-height: 0;
  }
  .day-time-grid {
    position: relative;
  }
  .day-hour-row {
    display: flex; align-items: stretch;
    border-bottom: 1px solid rgba(255,255,255,0.04);
    min-height: 64px; position: relative;
  }
  .day-half-row {
    min-height: 0; border-bottom: 1px dashed rgba(255,255,255,0.03);
  }
  .day-time-label {
    width: 60px; flex-shrink: 0; font-size: 12px; font-weight: 500;
    color: var(--text-muted); text-align: right; padding: 8px 10px 0 0;
    font-variant-numeric: tabular-nums;
  }
  .half-label { font-size: 10px; color: rgba(255,255,255,0.15); padding-top: 4px; }
  .day-hour-slot {
    flex: 1; position: relative; cursor: pointer;
    transition: background 0.1s; min-height: 64px;
    border-left: 1px solid rgba(255,255,255,0.04);
  }
  .day-hour-slot:hover { background: rgba(255,255,255,0.02); }
  .day-hour-half-line {
    flex: 1; border-left: 1px solid rgba(255,255,255,0.04);
    min-height: 8px;
  }

  .day-timed-event {
    position: absolute; left: 8px; right: 8px;
    border-radius: 8px; padding: 6px 10px;
    cursor: pointer; font-family: inherit; border: none;
    border-left: 4px solid var(--evt-color);
    background: color-mix(in srgb, var(--evt-color) 12%, transparent);
    transition: all 0.15s; z-index: 1; overflow: hidden;
    display: flex; flex-direction: column; gap: 2px; text-align: left;
  }
  .day-timed-event:hover {
    background: color-mix(in srgb, var(--evt-color) 20%, transparent);
    box-shadow: 0 2px 12px rgba(0,0,0,0.15);
    z-index: 2;
  }
  .day-evt-time { font-size: 11px; font-weight: 600; color: var(--text-primary); }
  .day-evt-title { font-size: 13px; font-weight: 500; color: var(--text-primary); }
  .day-evt-person { font-size: 11px; color: var(--text-muted); }

  /* Day current time */
  .day-now-indicator {
    position: absolute; left: 60px; right: 0; z-index: 5; pointer-events: none;
    display: flex; align-items: center;
  }
  .day-now-dot {
    width: 12px; height: 12px; background: #EF4444; border-radius: 50%;
    box-shadow: 0 0 8px rgba(239,68,68,0.5); flex-shrink: 0; margin-left: -6px;
  }
  .day-now-line {
    flex: 1; height: 2px; background: #EF4444;
  }

  /* =========================================================================
     Dialog – Glass Morphism
     ========================================================================= */
  .dialog-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.55);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
    animation: fadeInOverlay 0.2s ease-out;
  }
  @keyframes fadeInOverlay {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  .dialog {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: 16px;
    padding: 24px 28px;
    width: 500px;
    max-width: 95vw;
    max-height: 90vh;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 16px;
    box-shadow: 0 24px 80px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(255, 255, 255, 0.03);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    animation: dialogSlideIn 0.25s ease-out;
  }
  @keyframes dialogSlideIn {
    from {
      opacity: 0;
      transform: translateY(12px) scale(0.97);
    }
    to {
      opacity: 1;
      transform: translateY(0) scale(1);
    }
  }

  .dialog-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .dialog-header h3 {
    margin: 0;
    font-size: 18px;
    font-weight: 700;
    color: var(--text-primary);
    letter-spacing: -0.2px;
  }
  .dialog-close {
    background: transparent;
    border: none;
    color: var(--text-secondary);
    cursor: pointer;
    padding: 4px;
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.15s;
  }
  .dialog-close:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
  }

  /* Event type selector */
  .type-selector {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 4px;
  }
  .type-option {
    display: flex;
    align-items: center;
    gap: 5px;
    padding: 6px 10px;
    border: 1px solid var(--border-subtle);
    border-radius: 8px;
    background: transparent;
    color: var(--text-secondary);
    font-size: 12px;
    font-family: inherit;
    cursor: pointer;
    transition: all 0.15s ease;
  }
  .type-option:hover {
    border-color: var(--type-color);
    background: color-mix(in srgb, var(--type-color) 8%, transparent);
    color: var(--text-primary);
  }
  .type-option.selected {
    border-color: var(--type-color);
    background: color-mix(in srgb, var(--type-color) 15%, transparent);
    color: var(--text-primary);
    box-shadow: 0 0 8px color-mix(in srgb, var(--type-color) 20%, transparent);
  }
  .type-emoji {
    font-size: 14px;
    line-height: 1;
  }
  .type-label {
    font-weight: 500;
  }

  .field {
    display: flex;
    flex-direction: column;
    gap: 5px;
  }
  .field > span {
    font-size: 12px;
    font-weight: 600;
    color: var(--text-secondary);
    letter-spacing: 0.2px;
  }
  .field input[type="text"],
  .field input[type="date"],
  .field input[type="time"],
  .field select,
  .field textarea {
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid var(--border-subtle);
    border-radius: 10px;
    color: var(--text-primary);
    font-size: 13px;
    padding: 9px 12px;
    font-family: inherit;
    outline: none;
    transition: all 0.2s ease;
  }
  .field input:focus,
  .field select:focus,
  .field textarea:focus {
    border-color: var(--accent);
    box-shadow: 0 0 0 2px rgba(var(--accent-rgb), 0.15);
  }
  .field textarea {
    resize: vertical;
  }

  .field-row {
    display: flex;
    gap: 12px;
  }
  .field-row .field {
    flex: 1;
  }

  .checkbox-field {
    flex-direction: row;
    align-items: center;
    gap: 8px;
  }
  .checkbox-field input[type="checkbox"] {
    width: 16px;
    height: 16px;
    accent-color: var(--accent);
  }

  .dialog-actions {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 6px;
    padding-top: 12px;
    border-top: 1px solid var(--border-subtle);
  }
  .spacer {
    flex: 1;
  }

  .btn-delete {
    background: transparent;
    border: 1px solid rgba(239, 68, 68, 0.4);
    border-radius: 10px;
    color: #EF4444;
    font-size: 13px;
    padding: 8px 14px;
    cursor: pointer;
    transition: all 0.15s;
    font-family: inherit;
    display: flex;
    align-items: center;
    gap: 6px;
    font-weight: 500;
  }
  .btn-delete:hover {
    background: rgba(239, 68, 68, 0.1);
    border-color: rgba(239, 68, 68, 0.6);
  }

  .btn-cancel {
    background: transparent;
    border: 1px solid var(--border-subtle);
    border-radius: 10px;
    color: var(--text-secondary);
    font-size: 13px;
    padding: 8px 16px;
    cursor: pointer;
    transition: all 0.15s;
    font-family: inherit;
    font-weight: 500;
  }
  .btn-cancel:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
    border-color: var(--border-hover);
  }

  .btn-save {
    background: var(--accent);
    border: none;
    border-radius: 10px;
    color: #fff;
    font-size: 13px;
    font-weight: 700;
    padding: 9px 22px;
    cursor: pointer;
    transition: all 0.2s ease;
    font-family: inherit;
    box-shadow: 0 2px 8px rgba(var(--accent-rgb), 0.3);
  }
  .btn-save:hover:not(:disabled) {
    filter: brightness(1.15);
    box-shadow: 0 4px 14px rgba(var(--accent-rgb), 0.4);
    transform: translateY(-1px);
  }
  .btn-save:active:not(:disabled) {
    transform: translateY(0);
  }
  .btn-save:disabled {
    opacity: 0.35;
    cursor: not-allowed;
    box-shadow: none;
  }
</style>
