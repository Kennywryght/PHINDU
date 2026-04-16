<script>
  import { createEventDispatcher, onMount, onDestroy } from 'svelte';
  import API from '../api/api';

  export let title = '';
  const dispatch = createEventDispatcher();

  let session = null;
  let showSessionModal = false;
  let openingBalance = 0;

  onMount(fetchCurrentSession);
  const interval = setInterval(fetchCurrentSession, 60000);
  onDestroy(() => clearInterval(interval));

  async function fetchCurrentSession() {
    try {
      const res = await API.get('/sessions/current');
      if (res.data.id) session = res.data;
      else session = null;
    } catch {
      session = null;
    }
  }

  async function openSession() {
    if (!openingBalance || openingBalance < 0) {
      alert('Please enter a valid opening balance');
      return;
    }
    try {
      await API.post('/sessions/open', null, { params: { opening_balance: openingBalance } });
      await fetchCurrentSession();
      showSessionModal = false;
      openingBalance = 0;
    } catch (err) {
      alert('Failed to open session: ' + (err.response?.data?.detail || 'Unknown error'));
    }
  }
</script>

<header class="topbar">
  <div class="left-group">
    <button class="menu-btn" on:click={() => dispatch('toggle')} aria-label="Menu">
      <span>☰</span>
    </button>
    <div class="brand">
      <img src="/logo.png" alt="PHINDU Logo" class="logo-img" />
      <span class="logo-text">PHINDU</span>
    </div>
  </div>
  <h1 class="page-title">{title}</h1>
  <div class="spacer"></div>
  <div class="session-widget">
    {#if session}
      <span class="session-badge" title="Session active since {new Date(session.opened_at).toLocaleString()}">
        🟢 Session Open
      </span>
    {:else}
      <button class="btn btn-sm btn-outline" on:click={() => showSessionModal = true}>
        Open Day
      </button>
    {/if}
  </div>
  <div class="user">👤</div>
</header>

{#if showSessionModal}
  <div class="modal-overlay" on:click|self={() => showSessionModal = false}>
    <div class="modal">
      <h3>Open New Session</h3>
      <div class="form-group">
        <label for="openingBalance">Opening Cash Balance (MWK)</label>
        <input id="openingBalance" type="number" min="0" step="0.01" bind:value={openingBalance} />
      </div>
      <div class="modal-actions">
        <button class="btn btn-secondary" on:click={() => showSessionModal = false}>Cancel</button>
        <button class="btn btn-primary" on:click={openSession}>Open Session</button>
      </div>
    </div>
  </div>
{/if}

<style>
  .topbar {
    height: var(--topbar-height);
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    padding: 0 1.5rem;
    position: sticky;
    top: 0;
    z-index: 50;
    width: 100%;
    max-width: 100vw;
    box-sizing: border-box;
  }
  .left-group {
    display: flex;
    align-items: center;
    gap: 1rem;
  }
  .menu-btn {
    display: none;
    font-size: 2rem;
    line-height: 1;
    padding: 0.25rem 0.5rem;
    background: none;
    border: none;
    cursor: pointer;
    color: var(--text);
    border-radius: var(--radius);
  }
  .menu-btn:hover {
    background: var(--background);
  }
  .brand {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  .logo-img {
    height: 48px;
    width: auto;
  }
  .logo-text {
    font-weight: 600;
    font-size: 1.2rem;
    color: var(--primary);
  }
  .page-title {
    font-size: 1.1rem;
    font-weight: 500;
    color: var(--text-light);
    margin-left: 2rem;
  }
  .spacer {
    flex: 1;
  }
  .session-widget {
    margin-right: 1rem;
  }
  .session-badge {
    background: #dcfce7;
    color: #166534;
    padding: 0.3rem 0.8rem;
    border-radius: 20px;
    font-size: 0.85rem;
    font-weight: 500;
  }
  .btn-sm {
    padding: 0.3rem 0.8rem;
    font-size: 0.85rem;
  }
  .btn-outline {
    background: transparent;
    border: 1px solid var(--primary);
    color: var(--primary);
    border-radius: 20px;
  }
  .btn-outline:hover {
    background: var(--primary);
    color: white;
  }
  .user {
    font-size: 1.8rem;
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
  input {
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
  @media (max-width: 768px) {
    .topbar {
      padding: 0 1rem;
    }
    .menu-btn {
      display: block;
    }
    .logo-img {
      height: 36px;
    }
    .logo-text {
      font-size: 1rem;
    }
    .page-title {
      margin-left: 1rem;
    }
  }
  @media (max-width: 480px) {
    .page-title {
      display: none;
    }
  }
</style>