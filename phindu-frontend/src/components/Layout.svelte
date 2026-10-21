<script>
  import { onMount } from 'svelte';
  import { Download, X } from 'lucide-svelte';
  import Sidebar from './Sidebar.svelte';
  import Topbar from './Topbar.svelte';

  export let title = 'Dashboard';
  let sidebarOpen = false;

  // PWA install prompt
  let deferredPrompt = null;
  let showInstall = false;

  onMount(() => {
    const handleBeforeInstall = (e) => {
      e.preventDefault();
      deferredPrompt = e;
      showInstall = true;
    };
    window.addEventListener('beforeinstallprompt', handleBeforeInstall);
    return () => {
      window.removeEventListener('beforeinstallprompt', handleBeforeInstall);
    };
  });

  async function installApp() {
    if (!deferredPrompt) return;
    deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    if (outcome === 'accepted') {
      deferredPrompt = null;
      showInstall = false;
    }
  }

  function dismissInstall() {
    showInstall = false;
  }

  function toggleSidebar() {
    sidebarOpen = !sidebarOpen;
  }

  function closeSidebar() {
    sidebarOpen = false;
  }
</script>

<div class="layout">
  <Sidebar {sidebarOpen} on:close={closeSidebar} />
  <div class="main">
    <Topbar {title} on:toggle={toggleSidebar} />
    <main class="content">
      <div class="page-card">
        <slot />
      </div>
    </main>
  </div>
</div>

{#if showInstall}
  <div class="install-banner" role="region" aria-label="Install app">
    <span class="install-text">
      <Download size={18} strokeWidth={1.75} />
      <span>Install PHINDU for offline use</span>
    </span>
    <button
      class="install-btn"
      on:click={installApp}
      type="button"
    >
      Install
    </button>
    <button
      class="close-banner"
      on:click={dismissInstall}
      type="button"
      aria-label="Dismiss install prompt"
    >
      <X size={18} strokeWidth={1.75} />
    </button>
  </div>
{/if}

<style>
  .layout {
    display: flex;
    min-height: 100vh;
    width: 100%;
    background: var(--background, #f9fafb);
  }

  .main {
    flex: 1;
    display: flex;
    flex-direction: column;
    margin-left: var(--sidebar-width, 240px);
    transition: margin-left 0.3s ease;
    min-width: 0;
    width: 100%;
  }

  .content {
    padding: 1.5rem;
    flex: 1;
    width: 100%;
    box-sizing: border-box;
  }

  .page-card {
    background: var(--surface, #ffffff);
    border-radius: var(--radius, 12px);
    box-shadow: var(--shadow, 0 1px 3px rgba(0, 0, 0, 0.08));
    border: 1px solid var(--border, #e5e7eb);
    padding: 1.5rem;
    width: 100%;
    box-sizing: border-box;
  }

  /* ============ INSTALL BANNER ============ */
  .install-banner {
    position: fixed;
    bottom: 1rem;
    left: 1rem;
    right: 1rem;
    background: var(--surface, #ffffff);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: var(--radius, 12px);
    padding: 0.75rem 1rem;
    display: flex;
    align-items: center;
    gap: 0.75rem;
    box-shadow: var(--shadow-lg, 0 10px 15px -3px rgba(0, 0, 0, 0.1));
    z-index: 200;
    flex-wrap: nowrap;
  }

  .install-text {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    flex: 1;
    font-size: 0.9rem;
    color: var(--text, #111827);
    min-width: 0;
  }

  .install-text span {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .install-btn {
    padding: 0.5rem 1rem;
    background: var(--primary, #0f6b3e);
    color: white;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    font-weight: 500;
    font-size: 0.9rem;
    flex-shrink: 0;
    transition: background 0.15s;
  }

  .install-btn:hover {
    background: var(--primary-dark, #0a4f2e);
  }

  .close-banner {
    background: none;
    border: none;
    cursor: pointer;
    padding: 0.35rem;
    color: var(--text-light, #6b7280);
    line-height: 0;
    border-radius: 6px;
    flex-shrink: 0;
    transition: background 0.15s;
  }

  .close-banner:hover {
    background: var(--background, #f9fafb);
  }

  /* ============ TABLET ============ */
  @media (max-width: 768px) {
    .main {
      margin-left: 0;
      width: 100%;
    }

    .content {
      padding: 0.75rem;
    }

    .page-card {
      padding: 1rem;
      border-radius: 10px;
    }

    .install-banner {
      padding: 0.6rem 0.75rem;
      gap: 0.5rem;
      font-size: 0.85rem;
    }

    .install-text {
      font-size: 0.85rem;
    }

    .install-btn {
      padding: 0.4rem 0.8rem;
      font-size: 0.85rem;
    }
  }

  /* ============ DESKTOP — floating banner ============ */
  @media (min-width: 769px) {
    .install-banner {
      left: auto;
      width: 380px;
    }
  }

  /* ============ VERY NARROW ============ */
  @media (max-width: 380px) {
    .install-text span {
      display: none; /* show only the download icon on very small screens */
    }

    .install-banner {
      justify-content: flex-end;
    }
  }
</style>