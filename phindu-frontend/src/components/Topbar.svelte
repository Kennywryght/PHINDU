<script>
  import { createEventDispatcher } from 'svelte';
  import { onMount } from 'svelte';
  import API from'../api/api';
  export let title = '';
  let session = null;
  const dispatch = createEventDispatcher();
  async function checkSession() {
    try {
      const res = await API.get('/sessions/current');
      if (res.data.id) session = res.data;
      else session = null;
    } catch { session = null; }
  }
  onMount(checkSession);
  // Optionally poll every minute
</script>

<header class="topbar">
  <div class="left-group">
    <button class="menu-btn" on:click={() => dispatch('toggle')} aria-label="Menu">
      <span>☰</span>
    </button>
    <div class="brand">
      <!-- Replace with your actual logo path -->
      <img src="/logo.png" alt="PHINDU Logo" class="logo-img" />
      <span class="logo-text">PHINDU</span>
    </div>
    <div class="session-widget">
      {#if session}
        <span class="session-badge">🟢 Session Open</span>
      {:else}
        <button on:click={openSession} class="btn btn-sm">Open Day</button>
      {/if}
    </div>
  </div>
  <h1 class="page-title">{title}</h1>
  <div class="spacer"></div>
  <div class="user">👤</div>
</header>

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
    height: 48px;      /* Large logo image */
    width: auto;
  }

  .logo-text {
    font-weight: 600;
    font-size: 1.2rem;  /* Smaller text compared to image */
    color: var(--primary);
    letter-spacing: -0.3px;
    line-height: 1;
  }

  .page-title {
    font-size: 1.1rem;
    font-weight: 500;
    color: var(--text-light);
    margin-left: 2rem;
    text-transform: capitalize;
  }

  .spacer {
    flex: 1;
  }

  .user {
    font-size: 1.8rem;
    line-height: 1;
  }

  /* Mobile styles */
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
      font-size: 1rem;
    }
  }

  @media (max-width: 480px) {
    .page-title {
      display: none;
    }
  }
</style>