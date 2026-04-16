<script>
  import { createEventDispatcher, onMount, onDestroy } from 'svelte';

  export let sidebarOpen = false;
  const dispatch = createEventDispatcher();

  const navItems = [
    { href: '/', label: 'Dashboard', icon: '📊' },
    { href: '/products', label: 'Products', icon: '📦' },
    { href: '/pos', label: 'Point of Sale', icon: '🛒' },
    { href: '/sales', label: 'Sales', icon: '💰' },
    { href: '/insights', label: 'Insights', icon: '📈' },
    { href: '/expenses', label: 'Expenses', icon: '💸' },
    { href: '/alerts', label: 'Alerts', icon: '⚠️' },
  ];

  let currentPath = window.location.pathname;

  function updateCurrentPath() {
    currentPath = window.location.pathname;
  }

  onMount(() => {
    window.addEventListener('popstate', updateCurrentPath);
    return () => window.removeEventListener('popstate', updateCurrentPath);
  });

  function navigate(href) {
    if (window.navigate) {
      window.navigate(href);
    } else {
      window.location.href = href;
    }
    currentPath = href;
    // Auto‑close on mobile after navigation
    if (window.innerWidth <= 768) {
      dispatch('close');
    }
  }

  function closeSidebar() {
    dispatch('close');
  }

  function handleKeydown(e) {
    if (e.key === 'Escape' && sidebarOpen) {
      closeSidebar();
    }
  }

  onMount(() => {
    window.addEventListener('keydown', handleKeydown);
    return () => window.removeEventListener('keydown', handleKeydown);
  });
</script>

{#if sidebarOpen}
  <div class="backdrop" on:click={closeSidebar}></div>
{/if}

<aside class="sidebar" class:open={sidebarOpen}>
  <div class="sidebar-header">
    <h2>PHINDU</h2>
    <button class="close-btn" on:click={closeSidebar} aria-label="Close menu">✕</button>
  </div>
  <nav>
    {#each navItems as item}
      <button
        class="nav-item"
        class:active={currentPath === item.href}
        on:click={() => navigate(item.href)}
      >
        <span class="icon">{item.icon}</span>
        <span class="label">{item.label}</span>
      </button>
    {/each}
  </nav>
</aside>

<style>
  .backdrop {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.4);
    z-index: 90;
    display: none;
  }

  .sidebar {
    position: fixed;
    left: 0;
    top: 0;
    bottom: 0;
    width: var(--sidebar-width);
    background: var(--surface);
    border-right: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    padding: 1.5rem 0.75rem;
    z-index: 100;
    transition: transform 0.3s ease;
    overflow-y: auto;
  }

  .sidebar-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 0.5rem 1.5rem;
  }

  .sidebar-header h2 {
    font-weight: 700;
    font-size: 1.8rem;
    color: var(--primary);
  }

  .close-btn {
    display: none;
    background: none;
    border: none;
    font-size: 2rem;
    cursor: pointer;
    color: var(--text-light);
    padding: 0.25rem 0.5rem;
  }

  .nav-item {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.9rem 1rem;
    margin: 0.25rem 0;
    border-radius: var(--radius);
    color: var(--text-light);
    width: 100%;
    background: none;
    border: none;
    cursor: pointer;
    text-align: left;
    transition: all 0.2s;
    white-space: nowrap;
  }

  .nav-item:hover {
    background: var(--background);
    color: var(--text);
  }

  .nav-item.active {
    background: var(--primary);
    color: white;
  }

  .icon {
    font-size: 1.4rem;
  }

  .label {
    font-size: 1rem;
  }

  /* Mobile styles */
  @media (max-width: 768px) {
    .backdrop {
      display: block;
    }

    .sidebar {
      transform: translateX(-100%);
      width: 280px;               /* fixed width for mobile */
      max-width: 85vw;
    }

    .sidebar.open {
      transform: translateX(0);
      box-shadow: var(--shadow-lg);
    }

    .close-btn {
      display: block;
    }

    .nav-item {
      padding: 1rem 1rem;
    }
  }

  /* Desktop: sidebar always visible */
  @media (min-width: 769px) {
    .sidebar {
      transform: translateX(0) !important;
    }
  }
</style>