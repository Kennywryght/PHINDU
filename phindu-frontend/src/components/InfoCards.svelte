<script>
  import {
    TrendingUp, Users, Package, Wallet, PieChart, Sparkles,
    AlertCircle, CheckCircle2, Phone,
  } from "lucide-svelte";

  export let willRunOut = [];
  export let profitByCategory = [];
  export let customerHealth = null;
  export let inventoryValue = null;
  export let expenseBreakdown = null;
  export let goodNews = [];

  function formatMoney(n) {
    if (n == null) return "0";
    const num = Number(n);
    if (!isFinite(num)) return "0";
    return num.toLocaleString(undefined, { maximumFractionDigits: 0 });
  }

  function marginTone(pct) {
    if (pct >= 30) return "good";
    if (pct >= 15) return "warn";
    return "bad";
  }

  function turnoverTone(t) {
    if (t >= 4) return "good";
    if (t >= 2) return "warn";
    return "bad";
  }

  $: categoryTotalRevenue = profitByCategory.reduce((s, c) => s + c.revenue, 0);
</script>

<!-- ── Good news strip ── -->
{#if goodNews.length > 0}
  <div class="goodnews-strip">
    <Sparkles size={16} strokeWidth={2.25} class="gn-icon" />
    <div class="gn-items">
      {#each goodNews as item}
        <span class="gn-chip">
          {#if item.icon === "users"}<Users size={12} />{/if}
          {#if item.icon === "trending-up"}<TrendingUp size={12} />{/if}
          {#if item.icon === "check-circle"}<CheckCircle2 size={12} />{/if}
          {item.text}
        </span>
      {/each}
    </div>
  </div>
{/if}

<!-- ── Will run out ── -->
{#if willRunOut.length > 0}
  <div class="rn-card">
    <h3 class="rn-header">
      <AlertCircle size={18} strokeWidth={2} />
      Will run out soon
      <span class="rn-sub">Based on last 30 days of sales</span>
    </h3>
    <ul class="rn-list">
      {#each willRunOut as p}
        <li class="rn-row">
          <div class="rn-main">
            <a class="rn-name" href="/products/{p.id}">{p.name}</a>
            <span class="rn-meta">
              {p.stock_qty} {p.unit || "units"} left · sells ~{p.avg_daily_sales}/day
            </span>
          </div>
          <div class="rn-right">
            <div class="rn-days-bar">
              <div
                class="rn-days-fill tone-{p.days_left < 3 ? 'bad' : p.days_left < 7 ? 'warn' : 'ok'}"
                style="width: {Math.min(100, (p.days_left / 14) * 100)}%"
              ></div>
            </div>
            <span class="rn-days tone-{p.days_left < 3 ? 'bad' : p.days_left < 7 ? 'warn' : 'ok'}">
              {p.days_left}d
            </span>
            <span class="rn-reorder">order ~{p.suggested_reorder}</span>
          </div>
        </li>
      {/each}
    </ul>
  </div>
{/if}

<div class="info-grid">
  <!-- ── Profit by category ── -->
  {#if profitByCategory.length > 0}
    <div class="info-card">
      <h3 class="info-header">
        <PieChart size={16} strokeWidth={2} /> Profit by category
        <span class="info-sub">last 30 days</span>
      </h3>
      <ul class="cat-list">
        {#each profitByCategory as c}
          {@const width = categoryTotalRevenue > 0 ? (c.revenue / categoryTotalRevenue) * 100 : 0}
          <li class="cat-row">
            <div class="cat-top">
              <span class="cat-name">{c.category}</span>
              <span class="cat-margin tone-{marginTone(c.margin_pct)}">{c.margin_pct}%</span>
            </div>
            <div class="cat-bar">
              <div
                class="cat-bar-fill tone-{marginTone(c.margin_pct)}"
                style="width: {width}%"
              ></div>
            </div>
            <div class="cat-bottom">
              <span>MWK {formatMoney(c.revenue)}</span>
              <span class="cat-profit">+MWK {formatMoney(c.profit)} profit</span>
            </div>
          </li>
        {/each}
      </ul>
    </div>
  {/if}

  <!-- ── Customer health ── -->
  {#if customerHealth}
    <div class="info-card">
      <h3 class="info-header">
        <Users size={16} strokeWidth={2} /> Customer health
        <span class="info-sub">last 7 days</span>
      </h3>
      <div class="ch-grid">
        <div class="ch-cell">
          <span class="ch-label">Repeat rate</span>
          <span class="ch-value">{customerHealth.repeat_rate}%</span>
          <span class="ch-hint">{customerHealth.repeat_sales} of {customerHealth.total_window_sales} sales</span>
        </div>
        <div class="ch-cell">
          <span class="ch-label">New customers</span>
          <span class="ch-value">{customerHealth.new_customers}</span>
          <span class="ch-hint">first purchase this week</span>
        </div>
      </div>
      {#if customerHealth.at_risk.length > 0}
        <div class="ch-risk">
          <span class="ch-risk-title">
            <AlertCircle size={12} /> At-risk customers
          </span>
          <ul class="ch-risk-list">
            {#each customerHealth.at_risk as c}
              <li>
                <span>{c.name}</span>
                {#if c.phone}
                  <a class="ch-phone" href="tel:{c.phone}" title={c.phone}>
                    <Phone size={11} />
                  </a>
                {/if}
              </li>
            {/each}
          </ul>
        </div>
      {/if}
    </div>
  {/if}

  <!-- ── Inventory value ── -->
  {#if inventoryValue}
    <div class="info-card">
      <h3 class="info-header">
        <Package size={16} strokeWidth={2} /> Inventory value
      </h3>
      <div class="inv-block">
        <span class="inv-label">Cash tied in stock</span>
        <span class="inv-value">MWK {formatMoney(inventoryValue.value_at_cost)}</span>
        <span class="inv-hint">retail value MWK {formatMoney(inventoryValue.value_at_retail)}</span>
      </div>
      <div class="inv-row">
        <div class="inv-cell">
          <span class="inv-cell-label">SKUs</span>
          <span class="inv-cell-value">{inventoryValue.sku_count}</span>
        </div>
        <div class="inv-cell">
          <span class="inv-cell-label">Potential margin</span>
          <span class="inv-cell-value">MWK {formatMoney(inventoryValue.potential_margin)}</span>
        </div>
        <div class="inv-cell">
          <span class="inv-cell-label">Turnover</span>
          <span class="inv-cell-value tone-{turnoverTone(inventoryValue.turnover_annual)}">
            {inventoryValue.turnover_annual}×/yr
          </span>
        </div>
      </div>
    </div>
  {/if}

  <!-- ── Expense breakdown ── -->
  {#if expenseBreakdown && expenseBreakdown.categories.length > 0}
    <div class="info-card">
      <h3 class="info-header">
        <Wallet size={16} strokeWidth={2} /> Expenses breakdown
        <span class="info-sub">last 30 days</span>
      </h3>
      <div class="exp-total">
        <span class="exp-total-label">Total</span>
        <span class="exp-total-value">MWK {formatMoney(expenseBreakdown.total)}</span>
      </div>
      <ul class="exp-list">
        {#each expenseBreakdown.categories as c}
          <li class="exp-row">
            <div class="exp-top">
              <span class="exp-name">{c.category}</span>
              <span class="exp-pct">{c.share_pct}%</span>
            </div>
            <div class="exp-bar">
              <div class="exp-bar-fill" style="width: {c.share_pct}%"></div>
            </div>
            <div class="exp-bottom">
              <span>MWK {formatMoney(c.total)}</span>
              <span class="exp-count">{c.count} entries</span>
            </div>
          </li>
        {/each}
      </ul>
    </div>
  {/if}
</div>

<style>
  /* ── Good news ── */
  .goodnews-strip {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    padding: 0.65rem 0.9rem;
    border-radius: 10px;
    background: linear-gradient(135deg, rgba(34, 197, 94, 0.08), rgba(59, 130, 246, 0.05));
    border: 1px solid rgba(34, 197, 94, 0.25);
  }
  .gn-icon { color: #16a34a; flex-shrink: 0; }
  .gn-items { display: flex; flex-wrap: wrap; gap: 0.4rem 1rem; min-width: 0; }
  .gn-chip {
    display: inline-flex; align-items: center; gap: 0.3rem;
    font-size: 0.82rem; font-weight: 500; color: #166534;
  }
  .gn-chip svg { color: #16a34a; }

  /* ── Will run out ── */
  .rn-card {
    background: linear-gradient(135deg, rgba(220, 38, 38, 0.04), var(--surface, #fff) 60%);
    border: 1px solid #fecaca;
    border-radius: 12px;
    padding: 1rem 1.1rem;
    box-sizing: border-box;
    width: 100%;
  }
  .rn-header {
    display: flex; align-items: center; gap: 0.5rem;
    margin: 0 0 0.75rem; font-size: 1rem; font-weight: 600;
    color: var(--text, #111827); flex-wrap: wrap;
  }
  .rn-header svg { color: #dc2626; }
  .rn-sub {
    font-size: 0.72rem; font-weight: 500; color: var(--text-light, #6b7280);
    text-transform: none; letter-spacing: 0;
  }
  .rn-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 0.45rem; }
  .rn-row {
    display: flex; justify-content: space-between; align-items: center;
    gap: 0.65rem; padding: 0.55rem 0.7rem;
    background: #fff; border: 1px solid #fee2e2; border-radius: 9px;
  }
  .rn-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 0.1rem; }
  .rn-name {
    font-weight: 600; font-size: 0.88rem; color: var(--text, #111827);
    text-decoration: none; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }
  .rn-name:hover { text-decoration: underline; }
  .rn-meta { font-size: 0.75rem; color: var(--text-light, #6b7280); }
  .rn-right { display: flex; align-items: center; gap: 0.5rem; flex-shrink: 0; }
  .rn-days-bar {
    width: 50px; height: 6px;
    background: #f3f4f6; border-radius: 3px; overflow: hidden;
  }
  .rn-days-fill { height: 100%; border-radius: 3px; }
  .rn-days-fill.tone-bad { background: #dc2626; }
  .rn-days-fill.tone-warn { background: #f59e0b; }
  .rn-days-fill.tone-ok { background: #16a34a; }
  .rn-days { font-size: 0.8rem; font-weight: 700; min-width: 30px; text-align: right; }
  .rn-days.tone-bad { color: #b91c1c; }
  .rn-days.tone-warn { color: #b45309; }
  .rn-days.tone-ok { color: #15803d; }
  .rn-reorder { font-size: 0.72rem; color: var(--text-light, #6b7280); }

  /* ── Info grid ── */
  .info-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 0.85rem;
    width: 100%;
    box-sizing: border-box;
  }
  .info-card {
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 12px;
    padding: 1rem 1.1rem;
    box-sizing: border-box;
    display: flex;
    flex-direction: column;
    gap: 0.6rem;
  }
  .info-header {
    display: flex; align-items: center; gap: 0.45rem;
    margin: 0; font-size: 0.95rem; font-weight: 600;
    color: var(--text, #111827); flex-wrap: wrap;
  }
  .info-sub {
    font-size: 0.7rem; font-weight: 500; color: var(--text-light, #6b7280);
    text-transform: none; letter-spacing: 0;
  }

  /* ── Profit by category ── */
  .cat-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 0.55rem; }
  .cat-row { display: flex; flex-direction: column; gap: 0.25rem; }
  .cat-top { display: flex; justify-content: space-between; align-items: baseline; gap: 0.5rem; }
  .cat-name {
    font-size: 0.85rem; font-weight: 600; color: var(--text, #111827);
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }
  .cat-margin { font-size: 0.82rem; font-weight: 700; }
  .cat-margin.tone-good { color: #15803d; }
  .cat-margin.tone-warn { color: #b45309; }
  .cat-margin.tone-bad  { color: #b91c1c; }
  .cat-bar {
    width: 100%; height: 6px;
    background: var(--background, #f3f4f6); border-radius: 3px; overflow: hidden;
  }
  .cat-bar-fill { height: 100%; border-radius: 3px; transition: width 0.4s; }
  .cat-bar-fill.tone-good { background: #16a34a; }
  .cat-bar-fill.tone-warn { background: #f59e0b; }
  .cat-bar-fill.tone-bad  { background: #dc2626; }
  .cat-bottom { display: flex; justify-content: space-between; font-size: 0.72rem; color: var(--text-light, #6b7280); }
  .cat-profit { color: #15803d; font-weight: 600; }

  /* ── Customer health ── */
  .ch-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; }
  .ch-cell {
    display: flex; flex-direction: column; gap: 0.1rem;
    padding: 0.55rem 0.65rem;
    background: var(--background, #f9fafb);
    border-radius: 9px;
    border: 1px solid var(--border, #e5e7eb);
  }
  .ch-label { font-size: 0.65rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.03em; color: var(--text-light, #6b7280); }
  .ch-value { font-size: 1.2rem; font-weight: 800; color: var(--text, #111827); }
  .ch-hint { font-size: 0.7rem; color: var(--text-light, #6b7280); }
  .ch-risk {
    padding: 0.55rem 0.7rem;
    background: #fffbeb; border: 1px solid #fde68a;
    border-radius: 9px;
  }
  .ch-risk-title {
    display: inline-flex; align-items: center; gap: 0.3rem;
    font-size: 0.75rem; font-weight: 700; color: #92400e;
    text-transform: uppercase; letter-spacing: 0.03em;
  }
  .ch-risk-list { list-style: none; margin: 0.4rem 0 0; padding: 0; display: flex; flex-direction: column; gap: 0.2rem; }
  .ch-risk-list li {
    display: flex; justify-content: space-between; align-items: center;
    font-size: 0.82rem; color: var(--text, #111827);
  }
  .ch-phone {
    display: inline-flex; align-items: center; justify-content: center;
    width: 22px; height: 22px; border-radius: 50%;
    background: #fef3c7; color: #92400e; text-decoration: none;
  }

  /* ── Inventory ── */
  .inv-block { display: flex; flex-direction: column; gap: 0.1rem; }
  .inv-label { font-size: 0.68rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.03em; color: var(--text-light, #6b7280); }
  .inv-value { font-size: 1.4rem; font-weight: 800; color: var(--text, #111827); }
  .inv-hint { font-size: 0.72rem; color: var(--text-light, #6b7280); }
  .inv-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.4rem; }
  .inv-cell {
    display: flex; flex-direction: column; gap: 0.1rem;
    padding: 0.45rem 0.55rem;
    background: var(--background, #f9fafb);
    border-radius: 8px; border: 1px solid var(--border, #e5e7eb);
  }
  .inv-cell-label { font-size: 0.62rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.03em; color: var(--text-light, #6b7280); }
  .inv-cell-value { font-size: 0.85rem; font-weight: 700; color: var(--text, #111827); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .inv-cell-value.tone-good { color: #15803d; }
  .inv-cell-value.tone-warn { color: #b45309; }
  .inv-cell-value.tone-bad  { color: #b91c1c; }

  /* ── Expenses ── */
  .exp-total {
    display: flex; justify-content: space-between; align-items: baseline;
    padding-bottom: 0.5rem; border-bottom: 1px dashed var(--border, #e5e7eb);
  }
  .exp-total-label { font-size: 0.72rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.03em; color: var(--text-light, #6b7280); }
  .exp-total-value { font-size: 1.1rem; font-weight: 800; color: var(--text, #111827); }
  .exp-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 0.5rem; }
  .exp-row { display: flex; flex-direction: column; gap: 0.2rem; }
  .exp-top { display: flex; justify-content: space-between; font-size: 0.82rem; }
  .exp-name { font-weight: 600; color: var(--text, #111827); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .exp-pct { font-weight: 700; color: #dc2626; }
  .exp-bar {
    width: 100%; height: 5px;
    background: var(--background, #f3f4f6); border-radius: 3px; overflow: hidden;
  }
  .exp-bar-fill { height: 100%; background: #dc2626; border-radius: 3px; }
  .exp-bottom { display: flex; justify-content: space-between; font-size: 0.72rem; color: var(--text-light, #6b7280); }
  .exp-count { opacity: 0.85; }

  @media (max-width: 480px) {
    .info-grid { grid-template-columns: 1fr; }
    .rn-row { flex-direction: column; align-items: stretch; }
    .rn-right { justify-content: space-between; }
    .ch-grid { grid-template-columns: 1fr; }
    .inv-row { grid-template-columns: 1fr 1fr; }
    .inv-row > :last-child { grid-column: 1 / -1; }
  }
</style>