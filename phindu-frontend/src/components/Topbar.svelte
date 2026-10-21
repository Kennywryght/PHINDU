<script>
  import { createEventDispatcher, onMount } from 'svelte';
  import { locale } from 'svelte-i18n';
  import {
    Menu,
    Moon,
    Sun,
    Globe,
    LogOut,
    User as UserIcon,
    Circle,
  } from 'lucide-svelte';
  import API from '../api/api';

  export let title = '';
  const dispatch = createEventDispatcher();

  // Session state
  let session = null;
  let showSessionModal = false;
  let openingBalance = 0;

  // Theme state
  let theme = typeof window !== 'undefined'
    ? localStorage.getItem('theme') || 'light'
    : 'light';

  if (typeof document !== 'undefined') {
    document.documentElement.setAttribute('data-theme', theme);
  }

  // Language state
  let currentLocale = typeof window !== 'undefined'
    ? localStorage.getItem('locale') || 'en'
    : 'en';
  locale.set(currentLocale);

  onMount(() => {
    fetchCurrentSession();
    const interval = setInterval(fetchCurrentSession, 60000);
    return () => clearInterval(interval);
  });

  async function fetchCurrentSession() {
    try {
      const res = await API.get('/sessions/current');
      session = res.data.id ? res.data : null;
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
      await API.post('/sessions/open', null, {
        params: { opening_balance: openingBalance },
      });
      await fetchCurrentSession();
      showSessionModal = false;
      openingBalance = 0;
    } catch (err) {
      alert(
        'Failed to open session: ' +
          (err.response?.data?.detail || 'Unknown error')
      );
    }
  }

  function toggleTheme() {
    theme = theme === 'light' ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }

  function toggleLocale() {
    currentLocale = currentLocale === 'en' ? 'ny' : 'en';
    locale.set(currentLocale);
    localStorage.setItem('locale', currentLocale);
  }

  function handleLogout() {
    import('../stores/auth.js').then((module) => module.logout());
  }
</script>

<header class="topbar">
  <div class="left-group">
    <button
      class="menu-btn"
      on:click={() => dispatch('toggle')}
      aria-label="Open menu"
      type="button"
    >
      <Menu size={24} strokeWidth={1.75} />
    </button>

    <div class="brand">
      <img src="/logo-192.png" alt="PHINDU" class="logo-img" />
      <span class="logo-text">PHINDU</span>
    </div>
  </div>

  <h1 class="page-title">{title}</h1>

  <div class="spacer"></div>

  <div class="session-widget">
    {#if session}
      <span
        class="session-badge"
        title="Session active since {new Date(session.opened_at).toLocaleString()}"
      >
        <Circle size={8} fill="currentColor" strokeWidth={0} />
        <span>Session Open</span>
      </span>
    {:else}
      <button
        class="btn btn-sm btn-outline"
        on:click={() => (showSessionModal = true)}
        type="button"
      >
        Open Day
      </button>
    {/if}
  </div>

  <div class="user-controls">
    <button
      on:click={toggleTheme}
      title="Toggle theme"
      class="icon-btn"
      aria-label="Toggle theme"
      type="button"
    >
      {#if theme === 'light'}
        <Moon size={20} strokeWidth={1.75} />
      {:else}
        <Sun size={20} strokeWidth={1.75} />
      {/if}
    </button>

    <button
      on:click={toggleLocale}
      title="Change language"
      class="icon-btn"
      aria-label="Change language"
      type="button"
    >
      <Globe size={20} strokeWidth={1.75} />
      <span class="lang-tag">{currentLocale.toUpperCase()}</span>
    </button>

    <button
      on:click={handleLogout}
      title="Logout"
      class="icon-btn"
      aria-label="Logout"
      type="button"
    >
      <LogOut size={20} strokeWidth={1.75} />
    </button>

    <span class="user-avatar" aria-label="User">
      <UserIcon size={20} strokeWidth={1.75} />
    </span>
  </div>
</header>

{#if showSessionModal}
  <div
    class="modal-overlay"
    role="dialog"
    aria-modal="true"
    on:click|self={() => (showSessionModal = false)}
    on:keydown={(e) => e.key === 'Escape' && (showSessionModal = false)}
  >
    <div class="modal">
      <h3>Open New Session</h3>
      <div class="form-group">
        <label for="openingBalance">Opening Cash Balance (MWK)</label>
        <input
          id="openingBalance"
          type="number"
          min="0"
          step="0.01"
          bind:value={openingBalance}
        />
      </div>
      <div class="modal-actions">
        <button
          class="btn btn-secondary"
          on:click={() => (showSessionModal = false)}
          type="button"
        >
          Cancel
        </button>
        <button class="btn btn-primary" on:click={openSession} type="button">
          Open Session
        </button>
      </div>
    </div>
  </div>
{/if}

<style>
  .topbar {
    height: var(--topbar-height, 64px);
    background: var(--surface, #ffffff);
    border-bottom: 1px solid var(--border, #e5e7eb);
    display: flex;
    align-items: center;
    padding: 0 1.25rem;
    position: sticky;
    top: 0;
    z-index: 50;
    width: 100%;
    box-sizing: border-box;
    gap: 0.5rem;
  }

  .left-group {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    flex-shrink: 0;
  }

  .menu-btn {
    display: none;
    background: none;
    border: none;
    cursor: pointer;
    color: var(--text, #111827);
    padding: 0.4rem;
    border-radius: 8px;
    line-height: 0;
    transition: background 0.15s;
  }

  .menu-btn:hover {
    background: var(--background, #f9fafb);
  }

  .brand {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-shrink: 0;
  }

  .logo-img {
    height: 40px;
    width: auto;
  }

  .logo-text {
    font-weight: 600;
    font-size: 1.15rem;
    color: var(--primary, #0f6b3e);
    white-space: nowrap;
  }

  .page-title {
    font-size: 1.05rem;
    font-weight: 500;
    color: var(--text-light, #6b7280);
    margin-left: 0.75rem;
    white-space: nowrap;
    flex-shrink: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    min-width: 0;
  }

  .spacer {
    flex: 1 1 auto;
    min-width: 0.5rem;
  }

  .session-widget {
    flex-shrink: 0;
  }

  .session-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    background: var(--primary-light, #d1fae5);
    color: var(--primary-dark, #065f46);
    padding: 0.35rem 0.75rem;
    border-radius: 20px;
    font-size: 0.82rem;
    font-weight: 500;
    line-height: 1;
  }

  .btn-sm {
    padding: 0.35rem 0.8rem;
    font-size: 0.82rem;
  }

  .btn-outline {
    background: transparent;
    border: 1px solid var(--primary, #0f6b3e);
    color: var(--primary, #0f6b3e);
    border-radius: 20px;
    cursor: pointer;
    transition: all 0.15s;
  }

  .btn-outline:hover {
    background: var(--primary, #0f6b3e);
    color: white;
  }

  .user-controls {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    flex-shrink: 0;
  }

  .icon-btn {
    background: none;
    border: none;
    cursor: pointer;
    padding: 0.45rem;
    border-radius: 8px;
    color: var(--text, #111827);
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    line-height: 0;
    transition: background 0.15s;
  }

  .icon-btn:hover {
    background: var(--background, #f9fafb);
  }

  .lang-tag {
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.5px;
    line-height: 1;
  }

  .user-avatar {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 34px;
    height: 34px;
    border-radius: 50%;
    background: var(--primary-light, #d1fae5);
    color: var(--primary-dark, #065f46);
    margin-left: 0.25rem;
    flex-shrink: 0;
  }

  /* ============ MODAL ============ */
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
    background: var(--surface, #ffffff);
    border-radius: 12px;
    padding: 1.5rem;
    max-width: 400px;
    width: 100%;
    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.15);
  }

  .modal h3 {
    margin-top: 0;
    margin-bottom: 1rem;
    color: var(--text, #111827);
  }

  .form-group {
    margin-bottom: 1rem;
  }

  label {
    display: block;
    margin-bottom: 0.4rem;
    font-weight: 500;
    color: var(--text, #111827);
    font-size: 0.9rem;
  }

  input {
    width: 100%;
    padding: 0.6rem;
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 8px;
    background: var(--surface, #ffffff);
    color: var(--text, #111827);
    font-size: 0.95rem;
    box-sizing: border-box;
  }

  input:focus {
    outline: none;
    border-color: var(--primary, #0f6b3e);
    box-shadow: 0 0 0 3px rgba(15, 107, 62, 0.1);
  }

  .modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: 0.75rem;
    margin-top: 1.5rem;
  }

  .btn {
    padding: 0.55rem 1rem;
    border-radius: 8px;
    border: none;
    cursor: pointer;
    font-size: 0.9rem;
    font-weight: 500;
    transition: all 0.15s;
  }

  .btn-primary {
    background: var(--primary, #0f6b3e);
    color: white;
  }

  .btn-primary:hover {
    background: var(--primary-dark, #0a4f2e);
  }

  .btn-secondary {
    background: var(--surface, #ffffff);
    border: 1px solid var(--border, #e5e7eb);
    color: var(--text, #111827);
  }

  .btn-secondary:hover {
    background: var(--background, #f9fafb);
  }

  /* ============ MOBILE ============ */
  @media (max-width: 768px) {
    .topbar {
      padding: 0 0.75rem;
      gap: 0.35rem;
    }

    .menu-btn {
      display: inline-flex;
    }

    .logo-img {
      height: 32px;
    }

    .logo-text {
      font-size: 1rem;
    }

    .page-title {
      font-size: 0.95rem;
      margin-left: 0.5rem;
    }

    .icon-btn {
      padding: 0.4rem;
    }

    .user-avatar {
      width: 30px;
      height: 30px;
    }

    .session-badge {
      padding: 0.3rem 0.6rem;
      font-size: 0.75rem;
    }

    .session-badge span {
      display: none; /* show only the dot on mobile */
    }
  }

  @media (max-width: 480px) {
    .logo-text {
      display: none;
    }

    .page-title {
      font-size: 0.9rem;
    }

    .lang-tag {
      display: none;
    }
  }
</style>