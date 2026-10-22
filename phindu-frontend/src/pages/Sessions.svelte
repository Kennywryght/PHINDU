<script>
  import { onMount } from "svelte";
  import { Calendar, Plus, CheckCircle } from "lucide-svelte";
  import Layout from "../components/Layout.svelte";
  import API from "../api/api";

  let sessions = [];
  let currentSession = null;
  let loading = true;
  let showOpenModal = false;
  let showCloseModal = false;
  let openingBalance = 0;
  let closingBalance = 0;
  let closeNotes = "";

  onMount(async () => {
    await Promise.all([fetchSessions(), fetchCurrentSession()]);
    loading = false;
  });

  async function fetchSessions() {
    try {
      const res = await API.get("/sessions/");
      sessions = res.data;
    } catch (err) {
      console.error("Failed to fetch sessions", err);
    }
  }

  async function fetchCurrentSession() {
    try {
      const res = await API.get("/sessions/current");
      currentSession = res.data.id ? res.data : null;
    } catch {
      currentSession = null;
    }
  }

  async function openSession() {
    try {
      await API.post("/sessions/open", null, {
        params: { opening_balance: openingBalance },
      });
      await fetchCurrentSession();
      await fetchSessions();
      showOpenModal = false;
      openingBalance = 0;
    } catch (err) {
      alert("Failed to open session: " + (err.response?.data?.detail || "Unknown error"));
    }
  }

  async function closeSession() {
    try {
      await API.post("/sessions/close", null, {
        params: { closing_balance: closingBalance, notes: closeNotes },
      });
      await fetchCurrentSession();
      await fetchSessions();
      showCloseModal = false;
      closingBalance = 0;
      closeNotes = "";
    } catch (err) {
      alert("Failed to close session: " + (err.response?.data?.detail || "Unknown error"));
    }
  }

  function formatDateTime(isoString) {
    if (!isoString) return "—";
    return new Date(isoString).toLocaleString();
  }

  function formatDate(isoString) {
    if (!isoString) return "—";
    return new Date(isoString).toLocaleDateString();
  }
</script>

<Layout title="Daily Sessions">
  <div class="sessions-page">
    <div class="card current-session">
      <h2>
        <Calendar size={20} strokeWidth={2} />
        Current Session
      </h2>
      {#if currentSession}
        <div class="session-details">
          <div class="detail-row">
            <span>Opened:</span>
            <strong>{formatDateTime(currentSession.opened_at)}</strong>
          </div>
          <div class="detail-row">
            <span>Opening Balance:</span>
            <strong>MWK {currentSession.opening_balance?.toLocaleString()}</strong>
          </div>
          <div class="detail-row">
            <span>Sales so far:</span>
            <strong>MWK {currentSession.total_sales?.toLocaleString()}</strong>
          </div>
          <div class="detail-row">
            <span>Expenses so far:</span>
            <strong>MWK {currentSession.total_expenses?.toLocaleString()}</strong>
          </div>
        </div>
        <button
          class="btn btn-primary btn-block"
          on:click={() => (showCloseModal = true)}
          type="button"
        >
          Close Day
        </button>
      {:else}
        <p class="no-session">No active session.</p>
        <button
          class="btn btn-primary btn-block"
          on:click={() => (showOpenModal = true)}
          type="button"
        >
          <Plus size={16} strokeWidth={2} /> Open New Session
        </button>
      {/if}
    </div>

    <div class="card past-sessions">
      <h2>Past Sessions</h2>
      {#if loading}
        <p class="loading-text">Loading...</p>
      {:else if sessions.length === 0}
        <p class="empty-text">No past sessions recorded.</p>
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
                    <td>MWK {s.total_sales?.toLocaleString()}</td>
                    <td>MWK {s.total_expenses?.toLocaleString()}</td>
                    <td>
                      <strong>
                        MWK {(s.total_sales || 0 - s.total_expenses || 0).toLocaleString()}
                      </strong>
                    </td>
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

  {#if showOpenModal}
    <div
      class="modal-overlay"
      role="dialog"
      aria-modal="true"
      tabindex="-1"
      on:click|self={() => (showOpenModal = false)}
      on:keydown={(e) => e.key === "Escape" && (showOpenModal = false)}
    >
      <div class="modal">
        <h3>
          <Calendar size={18} strokeWidth={2} /> Open New Session
        </h3>
        <div class="form-group">
          <label for="opening">Opening Cash Balance (MWK)</label>
          <input id="opening" type="number" min="0" step="0.01" bind:value={openingBalance} />
        </div>
        <div class="modal-actions">
          <button class="btn btn-secondary" on:click={() => (showOpenModal = false)} type="button">
            Cancel
          </button>
          <button class="btn btn-primary" on:click={openSession} type="button">Open</button>
        </div>
      </div>
    </div>
  {/if}

  {#if showCloseModal}
    <div
      class="modal-overlay"
      role="dialog"
      aria-modal="true"
      tabindex="-1"
      on:click|self={() => (showCloseModal = false)}
      on:keydown={(e) => e.key === "Escape" && (showCloseModal = false)}
    >
      <div class="modal">
        <h3>
          <CheckCircle size={18} strokeWidth={2} /> Close Session
        </h3>
        <div class="form-group">
          <label for="closing">Closing Cash Balance (MWK)</label>
          <input id="closing" type="number" min="0" step="0.01" bind:value={closingBalance} />
        </div>
        <div class="form-group">
          <label for="notes">Notes (optional)</label>
          <textarea id="notes" bind:value={closeNotes} rows="3"></textarea>
        </div>
        <div class="modal-actions">
          <button class="btn btn-secondary" on:click={() => (showCloseModal = false)} type="button">
            Cancel
          </button>
          <button class="btn btn-primary" on:click={closeSession} type="button">Close Day</button>
        </div>
      </div>
    </div>
  {/if}
</Layout>

<style>
  .sessions-page {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    max-width: 900px;
    margin: 0 auto;
  }
  .card {
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 12px;
    padding: 1.25rem;
  }
  .card h2 {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-top: 0;
    margin-bottom: 1rem;
    font-size: 1.1rem;
    font-weight: 600;
    color: var(--text, #111827);
  }
  .session-details {
    margin: 1rem 0 1.25rem;
  }
  .detail-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.55rem 0;
    border-bottom: 1px solid var(--border, #e5e7eb);
    font-size: 0.9rem;
    gap: 0.5rem;
  }
  .detail-row:last-child {
    border-bottom: none;
  }
  .detail-row span {
    color: var(--text-light, #6b7280);
  }
  .detail-row strong {
    color: var(--text, #111827);
    text-align: right;
    word-break: break-word;
  }
  .no-session {
    color: var(--text-light, #6b7280);
    margin: 1rem 0;
    font-size: 0.9rem;
  }
  .loading-text,
  .empty-text {
    text-align: center;
    padding: 1.5rem;
    color: var(--text-light, #6b7280);
    font-size: 0.9rem;
  }
  .table-wrapper {
    overflow-x: auto;
    border-radius: 8px;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.88rem;
  }
  th,
  td {
    padding: 0.6rem 0.5rem;
    text-align: left;
    border-bottom: 1px solid var(--border, #e5e7eb);
    white-space: nowrap;
  }
  th {
    background: var(--background, #f9fafb);
    font-weight: 600;
    color: var(--text-light, #6b7280);
    font-size: 0.78rem;
    text-transform: uppercase;
  }
  .btn {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.55rem 1rem;
    border-radius: 8px;
    border: none;
    cursor: pointer;
    font-weight: 500;
    font-size: 0.9rem;
  }
  .btn-primary {
    background: var(--primary, #0f6b3e);
    color: white;
  }
  .btn-primary:hover {
    background: var(--primary-dark, #0a4f2e);
  }
  .btn-secondary {
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    color: var(--text, #111827);
  }
  .btn-block {
    width: 100%;
    justify-content: center;
    padding: 0.7rem;
  }
  .modal-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
    padding: 1rem;
  }
  .modal {
    background: var(--surface, #fff);
    border-radius: 12px;
    padding: 1.5rem;
    max-width: 420px;
    width: 100%;
    max-height: 90vh;
    overflow-y: auto;
  }
  .modal h3 {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-top: 0;
    margin-bottom: 1rem;
    font-size: 1.05rem;
    color: var(--text, #111827);
  }
  .form-group {
    margin-bottom: 0.85rem;
  }
  label {
    display: block;
    margin-bottom: 0.3rem;
    font-weight: 500;
    font-size: 0.88rem;
    color: var(--text, #111827);
  }
  input,
  textarea {
    width: 100%;
    padding: 0.6rem;
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 8px;
    font-size: 0.9rem;
    background: var(--surface, #fff);
    color: var(--text, #111827);
    box-sizing: border-box;
    font-family: inherit;
  }
  textarea {
    resize: vertical;
  }
  input:focus,
  textarea:focus {
    outline: none;
    border-color: var(--primary, #0f6b3e);
    box-shadow: 0 0 0 3px rgba(15, 107, 62, 0.1);
  }
  .modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: 0.6rem;
    margin-top: 1.25rem;
  }

  @media (max-width: 480px) {
    .detail-row {
      flex-direction: column;
      align-items: flex-start;
      gap: 0.2rem;
    }
    .detail-row strong {
      text-align: left;
    }
    th,
    td {
      padding: 0.45rem 0.35rem;
      font-size: 0.78rem;
    }
    .card {
      padding: 1rem;
    }
  }
</style>
