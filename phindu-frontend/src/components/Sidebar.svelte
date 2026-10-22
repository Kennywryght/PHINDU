<script>
  import { createEventDispatcher, onMount } from "svelte";
  import {
    LayoutDashboard,
    Package,
    ShoppingCart,
    DollarSign,
    TrendingUp,
    Receipt,
    AlertTriangle,
    Clock,
    CreditCard,
    LogOut,
    User as UserIcon,
    X,
  } from "lucide-svelte";

  export let sidebarOpen = false;
  const dispatch = createEventDispatcher();

  const navItems = [
    { href: "/", label: "Dashboard", icon: LayoutDashboard },
    { href: "/products", label: "Products", icon: Package },
    { href: "/pos", label: "Point of Sale", icon: ShoppingCart },
    { href: "/sales", label: "Sales", icon: DollarSign },
    { href: "/insights", label: "Insights", icon: TrendingUp },
    { href: "/expenses", label: "Expenses", icon: Receipt },
    { href: "/alerts", label: "Alerts", icon: AlertTriangle },
    { href: "/sessions", label: "Sessions", icon: Clock },
    { href: "/credit", label: "Credit / Loans", icon: CreditCard },
  ];

  let currentPath = typeof window !== "undefined" ? window.location.pathname : "/";

  function updateCurrentPath() {
    currentPath = window.location.pathname;
  }

  function navigate(href) {
    if (typeof window !== "undefined" && window.navigate) {
      window.navigate(href);
    } else {
      window.location.href = href;
    }
    currentPath = href;
    if (window.innerWidth <= 768) {
      dispatch("close");
    }
  }

  function closeSidebar() {
    dispatch("close");
  }

  function handleLogout() {
    import("../stores/auth.js").then((module) => module.logout());
  }

  function handleKeydown(e) {
    if (e.key === "Escape" && sidebarOpen) {
      closeSidebar();
    }
  }

  onMount(() => {
    window.addEventListener("popstate", updateCurrentPath);
    window.addEventListener("keydown", handleKeydown);
    return () => {
      window.removeEventListener("popstate", updateCurrentPath);
      window.removeEventListener("keydown", handleKeydown);
    };
  });
</script>

{#if sidebarOpen}
  <div
    class="backdrop"
    role="button"
    tabindex="0"
    aria-label="Close menu"
    on:click={closeSidebar}
    on:keydown={(e) => e.key === "Enter" && closeSidebar()}
  ></div>
{/if}

<aside class="sidebar" class:open={sidebarOpen}>
  <div class="sidebar-header">
    <h2>PHINDU</h2>
    <button class="close-btn" on:click={closeSidebar} aria-label="Close menu" type="button">
      <X size={22} />
    </button>
  </div>

  <nav>
    {#each navItems as item}
      {@const Icon = item.icon}
      <button
        class="nav-item"
        class:active={currentPath === item.href}
        on:click={() => navigate(item.href)}
        type="button"
      >
        <span class="icon">
          <Icon size={20} strokeWidth={1.75} />
        </span>
        <span class="label">{item.label}</span>
      </button>
    {/each}
  </nav>

  <div class="sidebar-footer">
    <div class="user-info">
      <span class="user-avatar">
        <UserIcon size={18} strokeWidth={1.75} />
      </span>
      <span class="user-label">Account</span>
    </div>
    <button class="nav-item logout-btn" on:click={handleLogout} type="button">
      <span class="icon">
        <LogOut size={20} strokeWidth={1.75} />
      </span>
      <span class="label">Logout</span>
    </button>
  </div>
</aside>

<style>
  .backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.45);
    z-index: 90;
    display: none;
  }

  .sidebar {
    position: fixed;
    left: 0;
    top: 0;
    bottom: 0;
    width: var(--sidebar-width, 240px);
    background: var(--surface, #ffffff);
    border-right: 1px solid var(--border, #e5e7eb);
    display: flex;
    flex-direction: column;
    padding: 1.25rem 0.75rem;
    z-index: 100;
    transition: transform 0.3s ease;
    overflow-y: auto;
    overscroll-behavior: contain;
  }

  .sidebar-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 0.5rem 1.5rem;
  }

  .sidebar-header h2 {
    font-weight: 700;
    font-size: 1.5rem;
    color: var(--primary, #0f6b3e);
    letter-spacing: 0.5px;
  }

  .close-btn {
    display: none;
    background: none;
    border: none;
    cursor: pointer;
    color: var(--text-light, #6b7280);
    padding: 0.4rem;
    border-radius: 8px;
    line-height: 0;
    transition: background 0.15s;
  }

  .close-btn:hover {
    background: var(--background, #f9fafb);
  }

  nav {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    flex: 1;
  }

  .nav-item {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem 0.9rem;
    border-radius: 10px;
    color: var(--text-light, #6b7280);
    background: none;
    border: none;
    cursor: pointer;
    text-align: left;
    width: 100%;
    font-size: 0.92rem;
    font-weight: 500;
    transition:
      background 0.15s,
      color 0.15s;
    white-space: nowrap;
  }

  .nav-item:hover {
    background: var(--background, #f9fafb);
    color: var(--text, #111827);
  }

  .nav-item.active {
    background: var(--primary, #0f6b3e);
    color: #ffffff;
  }

  .nav-item.active .icon {
    color: #ffffff;
  }

  .icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    color: inherit;
  }

  .label {
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .sidebar-footer {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
    padding-top: 0.75rem;
    margin-top: 0.75rem;
    border-top: 1px solid var(--border, #e5e7eb);
    flex-shrink: 0;
  }

  .user-info {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.6rem 0.9rem;
    font-size: 0.88rem;
    color: var(--text-light, #6b7280);
    font-weight: 500;
  }

  .user-avatar {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    border-radius: 50%;
    background: var(--primary-light, #d1fae5);
    color: var(--primary-dark, #065f46);
    flex-shrink: 0;
  }

  .logout-btn:hover {
    background: #fef2f2;
    color: var(--danger, #dc2626);
  }

  @media (max-width: 768px) {
    .backdrop {
      display: block;
    }

    .sidebar {
      transform: translateX(-100%);
      width: 280px;
      max-width: 85vw;
    }

    .sidebar.open {
      transform: translateX(0);
      box-shadow:
        0 20px 25px -5px rgba(0, 0, 0, 0.15),
        0 10px 10px -5px rgba(0, 0, 0, 0.1);
    }

    .close-btn {
      display: inline-flex;
    }
  }

  @media (min-width: 769px) {
    .sidebar {
      transform: translateX(0) !important;
    }
  }
</style>
