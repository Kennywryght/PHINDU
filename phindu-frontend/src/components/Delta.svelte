<script>
  import { ArrowUpRight, ArrowDownRight, Minus } from "lucide-svelte";
  export let pct = null;
</script>

{#if pct !== null && pct !== undefined}
  <span class="delta" class:up={pct > 0} class:down={pct < 0} class:flat={pct === 0}>
    {#if pct > 0}
      <ArrowUpRight size={11} />+{pct}%
    {:else if pct < 0}
      <ArrowDownRight size={11} />{pct}%
    {:else}
      <Minus size={11} />0%
    {/if}
  </span>
{/if}

<style>
  .delta {
    display: inline-flex;
    align-items: center;
    gap: 0.1rem;
    font-size: 0.7rem;
    font-weight: 600;
  }
  .delta.up { color: #166534; }
  .delta.down { color: #991b1b; }
  .delta.flat { color: var(--text-light, #6b7280); }
</style>