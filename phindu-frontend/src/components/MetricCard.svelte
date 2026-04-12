<script>
  export let title = '';
  export let value = 0;
  export let prefix = '';
  export let suffix = '';
  export let highlight = false;

  $: formattedValue = typeof value === 'number' 
    ? value.toLocaleString(undefined, { maximumFractionDigits: 2 }) 
    : value;
</script>

<div class="metric-card" class:highlight>
  <h4>{title}</h4>
  <div class="value">{prefix}{formattedValue}{suffix}</div>
</div>

<style>
  .metric-card {
    background: var(--surface);
    border-radius: var(--radius);
    padding: 1.25rem;
    box-shadow: var(--shadow);
    border: 1px solid var(--border);
  }

  h4 {
    font-size: 0.9rem;
    font-weight: 500;
    color: var(--text-light);
    margin-bottom: 0.5rem;
  }

  .value {
    font-size: 1.8rem;
    font-weight: 700;
    color: var(--text);
  }

  .highlight .value {
    color: var(--success);
  }
</style>