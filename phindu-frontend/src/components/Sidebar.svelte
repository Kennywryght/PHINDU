<script>
  import { createEventDispatcher } from 'svelte';

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

  // Update active state on navigation
  function navigate(href) {
    if (window.navigate) {
      window.navigate(href);
    } else {
      window.location.href = href;
    }
  }

  // Keep currentPath in sync with popstate (handled by App.svelte)
  // We'll listen to a custom event or just rely on re-render.
  // Simple approach: update on click.
</script>

<aside class="sidebar" class:open={sidebarOpen}>
  <div class="logo">
    <h2>PHINDU</h2>
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
  }

  .logo {
    padding: 0 1rem 2rem;
    font-weight: 700;
    font-size: 1.5rem;
    color: var(--primary);
  }

  .nav-item {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem 1rem;
    margin: 0.25rem 0;
    border-radius: var(--radius);
    color: var(--text-light);
    width: 100%;
    transition: all 0.2s;
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
    font-size: 1.25rem;
  }

  @media (max-width: 768px) {
    .sidebar {
      transform: translateX(-100%);
    }
    .sidebar.open {
      transform: translateX(0);
    }
  }
</style>