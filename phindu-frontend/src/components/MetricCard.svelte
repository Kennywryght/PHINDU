<script>
  export let title = "";
  export let value = 0;
  export let prefix = "";
  export let suffix = "";
  export let highlight = false;
  export let delta = null; // ← NEW: percentage number or null

  $: formattedValue =
    typeof value === "number"
      ? value.toLocaleString(undefined, { maximumFractionDigits: 2 })
      : value;

  $: deltaClass =
    delta === null || delta === undefined
      ? null
      : delta > 0
      ? "positive"
      : delta < 0
      ? "negative"
      : "flat";

  $: deltaText =
    delta === null || delta === undefined
      ? ""
      : `${delta > 0 ? "↑" : delta < 0 ? "↓" : "—"} ${Math.abs(delta)}%`;
</script>

<div class="metric-card" class:highlight>
  <h4>{title}</h4>
  <div class="value">
    {#if prefix}<span class="prefix">{prefix}</span>{/if}
    <span class="number">{formattedValue}</span>{#if suffix}<span class="suffix">{suffix}</span
      >{/if}
  </div>
  {#if deltaClass}
    <span class="delta {deltaClass}" title="vs yesterday">
      {deltaText}
    </span>
  {/if}
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

  /* ─── Delta pill ─── */
  .delta {
    display: inline-flex;
    align-items: center;
    margin-top: 0.4rem;
    padding: 0.1rem 0.4rem;
    font-size: 0.68rem;
    font-weight: 600;
    border-radius: 6px;
    line-height: 1.4;
    white-space: nowrap;
  }

  .delta.positive {
    background: #dcfce7;
    color: #15803d;
  }

  .delta.negative {
    background: #fee2e2;
    color: #b91c1c;
  }

  .delta.flat {
    background: #f3f4f6;
    color: #6b7280;
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

    .delta {
      font-size: 0.64rem;
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
      min-height: 1.5em;
    }

    .prefix {
      font-size: 0.58rem;
    }

    .number {
      font-size: clamp(0.82rem, 3.9vw, 1.1rem);
    }

    .suffix {
      font-size: 0.65rem;
    }

    .delta {
      font-size: 0.6rem;
      padding: 0.08rem 0.35rem;
      margin-top: 0.3rem;
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