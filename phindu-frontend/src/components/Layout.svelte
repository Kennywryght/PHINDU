<script>
  import Sidebar from './Sidebar.svelte';
  import Topbar from './Topbar.svelte';

  export let title = 'Dashboard';
  let sidebarOpen = false;

  function toggleSidebar() {
    sidebarOpen = !sidebarOpen;
  }
</script>

<div class="layout">
  <Sidebar {sidebarOpen} on:close={() => sidebarOpen = false} />
  <div class="main">
    <Topbar {title} on:toggle={toggleSidebar} />
    <main class="content">
      <slot />
    </main>
  </div>
</div>

<style>
  .layout {
    display: flex;
    min-height: 100vh;
  }

  .main {
    flex: 1;
    display: flex;
    flex-direction: column;
    margin-left: var(--sidebar-width);
    transition: margin-left 0.3s ease;
  }

  .content {
    padding: 1.5rem;
    flex: 1;
  }

  @media (max-width: 768px) {
    .main {
      margin-left: 0;
    }
  }
</style>