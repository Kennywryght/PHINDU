<script>
  import { onMount } from 'svelte';
  import Layout from '../components/Layout.svelte';
  import API from '../api/api';

  let sessions = [];
  let currentSession = null;
  let loading = true;
  let showOpenModal = false;
  let showCloseModal = false;
  let openingBalance = 0;
  let closingBalance = 0;
  let closeNotes = '';

  onMount(async () => {
    await Promise.all([fetchSessions(), fetchCurrentSession()]);
    loading = false;
  });

  async function fetchSessions() {
    try {
      const res = await API.get('/sessions/');
      sessions = res.data;
    } catch (err) {
      console.error('Failed to fetch sessions', err);
    }
  }

  async function fetchCurrentSession() {
    try {
      const res = await API.get('/sessions/current');
      if (res.data.id) currentSession = res.data;
      else currentSession = null;
    } catch {
      currentSession = null;
    }
  }

  async function openSession() {
    try {
      await API.post('/sessions/open', null, { params: { opening_balance: openingBalance } });
      await fetchCurrentSession();
      await fetchSessions();
      showOpenModal = false;
      openingBalance = 0;
    } catch (err) {
      alert('Failed to open session: ' + (err.response?.data?.detail || 'Unknown error'));
    }
  }

  async function closeSession() {
    try {
      await API.post('/sessions/close', null, {
        params: { closing_balance: closingBalance, notes: closeNotes }
      });
      await fetchCurrentSession();
      await fetchSessions();
      showCloseModal = false;
      closingBalance = 0;
      closeNotes = '';
    } catch (err) {
      alert('Failed to close session: ' + (err.response?.data?.detail || 'Unknown error'));
    }
  }

  function formatDateTime(isoString) {
    if (!isoString) return '—';
    const d = new Date(isoString);
    return d.toLocaleString();
  }

  function formatDate(isoString) {
    if (!isoString) return '—';
    return new Date(isoString).toLocaleDateString();
  }
</script>

<Layout title="Daily Sessions">
  <div class="sessions-page">
    <!-- Current Session Card -->
    <div class="card current-session">
      <h2>Current Session</h2>
      {#if currentSession}
        <div class="session-details">
          <div class="detail-row">
            <span>Opened:</span>
            <strong>{formatDateTime(currentSession.opened_at)}</strong>
          </div>
          <div class="detail-row">
            <span>Opening Balance:</span>
            <strong>MWK {currentSession.opening_balance.toFixed(2)}</strong>
          </div>
          <div class="detail-row">
            <span>Sales so far:</span>
            <strong>MWK {currentSession.total_sales.toFixed(2)}</strong>
          </div>
          <div class="detail-row">
            <span>Expenses so far:</span>
            <strong>MWK {currentSession.total_expenses.toFixed(2)}</strong>
          </div>
        </div>
        <button class="btn btn-primary" on:click={() => showCloseModal = true}>
          Close Day
        </button>
      {:else}
        <p class="no-session">No active session.</p>
        <button class="btn btn-primary" on:click={() => showOpenModal = true}>
          Open New Session
        </button>
      {/if}
    </div>

    <!-- Past Sessions Table -->
    <div class="card past-sessions">
      <h2>Past Sessions</h2>
      {#if loading}
        <p>Loading...</p>
      {:else if sessions.length === 0}
        <p>No past sessions recorded.</p>
      {:else}
        <div class="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Sales</th>
                <th>Expenses</th>
                <th>Net</th>
                <th>Closed</th>
              </tr>
            </thead>
            <tbody>
              {#each sessions as s}
                {#if !s.is_active}
                  <tr>
                    <td>{formatDate(s.opened_at)}</td>
                    <td>MWK {s.total_sales.toFixed(2)}</td>
                    <td>MWK {s.total_expenses.toFixed(2)}</td>
                    <td>MWK {(s.total_sales - s.total_expenses).toFixed(2)}</td>
                    <td>{formatDateTime(s.closed_at)}</td>
                  </tr>
                {/if}
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    </div>
  </div>

  <!-- Open Session Modal -->
  {#if showOpenModal}
    <div class="modal-overlay" on:click|self={() => showOpenModal = false}>
      <div class="modal">
        <h3>Open New Session</h3>
        <div class="form-group">
          <label for="opening">Opening Cash Balance (MWK)</label>
          <input id="opening" type="number" min="0" step="0.01" bind:value={openingBalance} />
        </div>
        <div class="modal-actions">
          <button class="btn btn-secondary" on:click={() => showOpenModal = false}>Cancel</button>
          <button class="btn btn-primary" on:click={openSession}>Open</button>
        </div>
      </div>
    </div>
  {/if}

  <!-- Close Session Modal -->
  {#if showCloseModal}
    <div class="modal-overlay" on:click|self={() => showCloseModal = false}>
      <div class="modal">
        <h3>Close Session</h3>
        <div class="form-group">
          <label for="closing">Closing Cash Balance (MWK)</label>
          <input id="closing" type="number" min="0" step="0.01" bind:value={closingBalance} />
        </div>
        <div class="form-group">
          <label for="notes">Notes (optional)</label>
          <textarea id="notes" bind:value={closeNotes} rows="3"></textarea>
        </div>
        <div class="modal-actions">
          <button class="btn btn-secondary" on:click={() => showCloseModal = false}>Cancel</button>
          <button class="btn btn-primary" on:click={closeSession}>Close Day</button>
        </div>
      </div>
    </div>
  {/if}
</Layout>

<style>
  .sessions-page {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
    max-width: 900px;
    margin: 0 auto;
  }

  .current-session {
    padding: 1.5rem;
  }

  .session-details {
    margin: 1.5rem 0;
  }

  .detail-row {
    display: flex;
    justify-content: space-between;
    padding: 0.5rem 0;
    border-bottom: 1px solid var(--border);
  }

  .detail-row:last-child {
    border-bottom: none;
  }

  .no-session {
    color: var(--text-light);
    margin: 1rem 0;
  }

  .past-sessions {
    padding: 1.5rem;
  }

  .table-wrapper {
    overflow-x: auto;
    margin-top: 1rem;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.9rem;
  }

  th, td {
    padding: 0.75rem 0.5rem;
    text-align: left;
    border-bottom: 1px solid var(--border);
  }

  th {
    background: var(--background);
    font-weight: 600;
  }

  .modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0,0,0,0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
    padding: 1rem;
  }

  .modal {
    background: white;
    border-radius: var(--radius);
    padding: 1.5rem;
    max-width: 400px;
    width: 100%;
  }

  .form-group {
    margin-bottom: 1rem;
  }

  label {
    display: block;
    margin-bottom: 0.25rem;
    font-weight: 500;
  }

  input, textarea {
    width: 100%;
    padding: 0.5rem;
    border: 1px solid var(--border);
    border-radius: var(--radius);
  }

  .modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: 0.75rem;
    margin-top: 1.5rem;
  }

  .btn {
    padding: 0.5rem 1rem;
    border-radius: var(--radius);
    border: none;
    cursor: pointer;
  }

  .btn-primary {
    background: var(--primary);
    color: white;
  }

  .btn-secondary {
    background: var(--surface);
    border: 1px solid var(--border);
  }

  @media (max-width: 480px) {
    .detail-row {
      flex-direction: column;
      align-items: flex-start;
      gap: 0.25rem;
    }
    th, td {
      padding: 0.5rem 0.25rem;
      font-size: 0.8rem;
    }
  }
</style>