<script>
  import { createEventDispatcher } from 'svelte';
  export let title = '';
  const dispatch = createEventDispatcher();
</script>

<header class="topbar">
  <button class="menu-btn" on:click={() => dispatch('toggle')}>
    <span>☰</span>
  </button>
  <h1>{title}</h1>
  <div class="spacer"></div>
  <div class="user">
    <span>👤</span>
  </div>
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

  .menu-btn {
    display: none;
    font-size: 1.5rem;
    margin-right: 1rem;
  }

  h1 {
    font-size: 1.5rem;
    font-weight: 600;
  }

  .spacer {
    flex: 1;
  }

  @media (max-width: 768px) {
    .menu-btn {
      display: block;
    }
  }
</style>