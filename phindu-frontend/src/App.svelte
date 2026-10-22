<script>
  // i18n initialization
  import { init, register, locale } from "svelte-i18n";

  init({
    fallbackLocale: "en",
    initialLocale: localStorage.getItem("locale") || "en",
  });

  register("en", () => import("./i18n/en.json"));
  register("ny", () => import("./i18n/ny.json"));

  let currentLocale = localStorage.getItem("locale") || "en";
  locale.set(currentLocale);

  // Routing and authentication
  import { onMount, onDestroy } from "svelte";
  import { routes } from "./routes";
  import { token } from "./stores/auth.js";
  import Login from "./pages/Login.svelte";

  let currentPath = window.location.pathname;
  let CurrentPage = routes[currentPath] || routes["/"];

  function updateRoute() {
    currentPath = window.location.pathname;
    CurrentPage = routes[currentPath] || routes["/"];
  }

  function navigate(path) {
    window.history.pushState({}, "", path);
    updateRoute();
  }

  onMount(() => {
    window.addEventListener("popstate", updateRoute);
    window.navigate = navigate;
    updateRoute();
  });

  onDestroy(() => {
    window.removeEventListener("popstate", updateRoute);
  });

  $: isPublicRoute = currentPath === "/login" || currentPath === "/register";
</script>

<main>
  {#if !$token && !isPublicRoute}
    <Login />
  {:else}
    <svelte:component this={CurrentPage} />
  {/if}
</main>

<style global>
  @import "./app.css";
</style>
