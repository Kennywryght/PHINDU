<script>
  import { onMount, onDestroy } from 'svelte';
  import { routes } from './routes';

  let currentPath = window.location.pathname;
  let CurrentPage = routes[currentPath] || routes['/'];

  function updateRoute() {
    currentPath = window.location.pathname;
    CurrentPage = routes[currentPath] || routes['/'];
  }

  function navigate(path) {
    window.history.pushState({}, '', path);
    updateRoute();
  }

  onMount(() => {
    window.addEventListener('popstate', updateRoute);
    window.navigate = navigate;
    updateRoute();
  });

  onDestroy(() => {
    window.removeEventListener('popstate', updateRoute);
  });
</script>

<main>
  <svelte:component this={CurrentPage} />
</main>

<style global>
  @import './app.css';
</style>