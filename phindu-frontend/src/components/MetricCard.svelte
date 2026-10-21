<script>
  export let title = '';
  export let value = 0;
  export let prefix = '';
  export let suffix = '';
  export let highlight = false;

  $: formattedValue =
    typeof value === 'number'
      ? value.toLocaleString(undefined, { maximumFractionDigits: 2 })
      : value;
</script>

<div class="metric-card" class:highlight>
  <h4>{title}</h4>
  <div class="value">
    {#if prefix}<span class="prefix">{prefix}</span>{/if}
    <span class="number">{formattedValue}</span>{#if suffix}<span class="suffix">{suffix}</span>{/if}
  </div>
</div>

<style>
  .metric-card {
    background: var(--surface, #fff);
    border-radius: 12px;
    padding: 1rem 0.85rem;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
    border: 1px solid var(--border, #e5e7eb);
    min-width: 0;
    overflow: hidden;
    box-sizing: border-box;
  }

  h4 {
    font-size: 0.78rem;
    font-weight: 500;
    color: var(--text-light, #6b7280);
    margin: 0 0 0.4rem;
    line-height: 1.2;
    text-transform: uppercase;
    letter-spacing: 0.3px;
  }

  .value {
    display: flex;
    align-items: baseline;
    flex-wrap: nowrap;
    gap: 0.15rem;
    color: var(--text, #111827);
    font-weight: 700;
    min-width: 0;
    overflow: hidden;
  }

  .prefix {
    font-size: 0.68rem;
    font-weight: 600;
    color: var(--text-light, #6b7280);
    flex-shrink: 0;
    letter-spacing: 0.3px;
  }

  .number {
    font-size: clamp(0.95rem, 4vw, 1.5rem);
    line-height: 1.1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    flex: 1 1 auto;
    min-width: 0;
  }

  .suffix {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--text-light, #6b7280);
    flex-shrink: 0;
  }

  .highlight .number {
    color: var(--success, #16a34a);
  }

  /* ============ TABLET ============ */
  @media (max-width: 768px) {
    .metric-card {
      padding: 0.85rem 0.7rem;
    }

    h4 {
      font-size: 0.72rem;
    }

    .number {
      font-size: clamp(0.9rem, 4.2vw, 1.35rem);
    }
  }

  /* ============ MOBILE ============ */
  @media (max-width: 480px) {
    .metric-card {
      padding: 0.7rem 0.55rem;
    }

    h4 {
      font-size: 0.68rem;
      margin-bottom: 0.3rem;
      line-height: 1.15;
      /* allow 2 lines for long titles like "Avg Sale Value" */
      min-height: 1.5em;
    }

    .prefix {
      font-size: 0.58rem;
    }

    .number {
      /* Key fix: shrink further so "3,500" / "125,000" fits.
         On a 320px phone → 2 col → each ~140px inner → 0.85rem font
         fits ~10 chars + prefix. Clean. */
      font-size: clamp(0.82rem, 3.9vw, 1.1rem);
    }

    .suffix {
      font-size: 0.65rem;
    }
  }

  /* ============ VERY SMALL ============ */
  @media (max-width: 360px) {
    .metric-card {
      padding: 0.6rem 0.5rem;
    }

    h4 {
      font-size: 0.63rem;
    }

    .number {
      font-size: clamp(0.78rem, 3.8vw, 1rem);
    }

    .prefix {
      font-size: 0.55rem;
    }
  }
</style>