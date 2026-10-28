<script>
  import {
    Sparkles,
    Package,
    TrendingUp,
    Wallet,
    PiggyBank,
    AlertCircle,
  } from "lucide-svelte";

  export let goodNews = [];
  export let willRunOut = [];
  export let profitByCategory = [];
  export let inventoryValue = null;
  export let expenseBreakdown = null;

  // Helper: format a percentage so tiny values (<1%) keep 2 decimals
  // (e.g. 0.42% stays "0.42%", 13.4% stays "13.4%", 100% stays "100%").
  function fmtPct(value) {
    const n = Number(value);
    if (!isFinite(n)) return "—";
    if (n === 0) return "0%";
    const abs = Math.abs(n);
    if (abs < 1) return n.toFixed(2) + "%";
    if (abs < 10) return n.toFixed(1) + "%";
    return n.toFixed(1) + "%";
  }

  // Compute a category's share-of-profit % from the current array, used
  // as a fallback if the API didn't include share_percent.
  $: profitTotal = profitByCategory.reduce(
    (s, c) => s + Number(c.profit || 0),
    0
  );

  // Compute expense share from expenseBreakdown.total as a fallback.
  $: expenseTotal = expenseBreakdown?.total ?? 0;

  function profitSharePct(c) {
    if (c.share_percent != null) return Number(c.share_percent);
    if (profitTotal > 0) return (Number(c.profit || 0) / profitTotal) * 100;
    return 0;
  }

  function expenseSharePct(c) {
    if (c.percent != null) return Number(c.percent);
    if (c.share_pct != null) return Number(c.share_pct);
    if (expenseTotal > 0) return (Number(c.total || 0) / expenseTotal) * 100;
    return 0;
  }

  function fmtMoney(n) {
    const num = Number(n || 0);
    if (!isFinite(num)) return "0";
    return num.toLocaleString(undefined, { maximumFractionDigits: 0 });
  }
</script>

<div class="info-cards-grid">
  <!-- ── Good news ── -->
  {#if goodNews && goodNews.length > 0}
    <div class="info-card good-news">
      <h4><Sparkles size={16} strokeWidth={2} /> Good news</h4>
      <ul>
        {#each goodNews as g}
          <li>{g.text || g}</li>
        {/each}
      </ul>
    </div>
  {/if}

  <!-- ── Will run out (Restock Planner) ── -->
  {#if willRunOut && willRunOut.length > 0}
    <div class="info-card will-run-out">
      <h4><AlertCircle size={16} strokeWidth={2} /> Will run out soon</h4>
      <ul>
        {#each willRunOut as p}
          <li>
            <div class="wro-main">
              <strong>{p.name}</strong>
              <span class="wro-meta">
                ~{p.days_left} day{p.days_left === 1 ? "" : "s"} left
                {#if p.recommended_order_qty != null}
                  · Order ~{p.recommended_order_qty}
                {:else if p.suggested_reorder != null}
                  · Order ~{p.suggested_reorder}
                {/if}
              </span>
            </div>
          </li>
        {/each}
      </ul>
    </div>
  {/if}

  <!-- ── Profit by category ── -->
  {#if profitByCategory && profitByCategory.length > 0}
    <div class="info-card profit-by-cat">
      <h4><TrendingUp size={16} strokeWidth={2} /> Profit by category (30d)</h4>
      <ul>
        {#each profitByCategory as c}
          <li class="pbc-row">
            <span class="pbc-name">{c.category}</span>
            <span class="pbc-val">
              MWK {fmtMoney(c.profit)}
            </span>
            <span class="pbc-pct" title="Share of total profit">
              {fmtPct(profitSharePct(c))}
            </span>
          </li>
        {/each}
      </ul>
    </div>
  {/if}

  <!-- ── Inventory value ── -->
  {#if inventoryValue}
    <div class="info-card inventory">
      <h4><Package size={16} strokeWidth={2} /> Inventory value</h4>

      <div class="inv-stats">
        <div class="inv-stat" title="Number of distinct products currently in stock (variants counted separately)">
          <span class="inv-label">SKUs</span>
          <strong class="inv-value">{inventoryValue.sku_count ?? 0}</strong>
        </div>
        <div class="inv-stat" title="Total money you paid for the stock you currently hold (buying cost)">
          <span class="inv-label">Stock at cost</span>
          <strong class="inv-value">MWK {fmtMoney(inventoryValue.value_at_cost)}</strong>
        </div>
        <div class="inv-stat" title="Money you would make if you sold ALL stock at today's prices (revenue − cost)">
          <span class="inv-label">Potential profit</span>
          <strong class="inv-value">MWK {fmtMoney(inventoryValue.potential_margin)}</strong>
        </div>
        <div class="inv-stat" title="Average number of times your stock sells out and is refilled per year. Higher = faster money turn-around">
          <span class="inv-label">Turnover</span>
          <strong class="inv-value">
            {Number(inventoryValue.turnover ?? inventoryValue.turnover_annual ?? 0).toFixed(1)}×
          </strong>
        </div>
      </div>

      <div class="inv-explainer">
        <p>
          <strong>SKUs</strong> = how many different products you stock.<br />
          <strong>Potential profit</strong> = what you'd earn if all current stock sold at
          today's prices. It's not money in the bank yet — it's the value sitting on
          your shelves.<br />
          <strong>Turnover</strong> = how many times per year your average stock gets
          sold and replaced. A turnover of <em>2×</em> means you cycle through your
          stock twice a year. Higher is better — it means cash isn't stuck on shelves.
        </p>
      </div>
    </div>
  {/if}

  <!-- ── Expense breakdown ── -->
  {#if expenseBreakdown && expenseBreakdown.categories && expenseBreakdown.categories.length > 0}
    <div class="info-card expenses">
      <h4><Wallet size={16} strokeWidth={2} /> Expense breakdown (30d)</h4>
      <ul>
        {#each expenseBreakdown.categories.slice(0, 5) as c}
          <li class="pbc-row">
            <span class="pbc-name">{c.category}</span>
            <span class="pbc-val">MWK {fmtMoney(c.total)}</span>
            <span class="pbc-pct" title="Share of total expenses">
              {fmtPct(expenseSharePct(c))}
            </span>
          </li>
        {/each}
      </ul>
      {#if expenseBreakdown.total != null}
        <p class="exp-total">
          <PiggyBank size={12} /> Total: MWK {fmtMoney(expenseBreakdown.total)}
        </p>
      {/if}
    </div>
  {/if}
</div>

<style>
  .info-cards-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 0.75rem;
    width: 100%;
    box-sizing: border-box;
  }

  .info-card {
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 12px;
    padding: 0.85rem 0.95rem;
    box-sizing: border-box;
    min-width: 0;
  }
  .info-card h4 {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    margin: 0 0 0.55rem;
    font-size: 0.88rem;
    font-weight: 700;
    color: var(--text, #111827);
  }
  .info-card.good-news {
    border-color: #86efac;
    background: linear-gradient(135deg, rgba(34, 197, 94, 0.05), var(--surface, #fff) 70%);
  }
  .info-card.good-news h4 { color: #166534; }
  .info-card.will-run-out {
    border-color: #fca5a5;
    background: linear-gradient(135deg, rgba(239, 68, 68, 0.05), var(--surface, #fff) 70%);
  }
  .info-card.will-run-out h4 { color: #991b1b; }

  .info-card ul {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
  }
  .info-card li {
    font-size: 0.8rem;
    color: var(--text, #111827);
    line-height: 1.35;
  }
  .wro-main { display: flex; flex-direction: column; gap: 0.1rem; }
  .wro-main strong {
    font-size: 0.82rem;
    color: var(--text, #111827);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .wro-meta { font-size: 0.72rem; color: var(--text-light, #6b7280); }

  .pbc-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto auto;
    align-items: baseline;
    gap: 0.5rem;
  }
  .pbc-name {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: var(--text, #111827);
  }
  .pbc-val {
    font-weight: 600;
    color: var(--text, #111827);
    white-space: nowrap;
  }
  .pbc-pct {
    font-size: 0.72rem;
    font-weight: 600;
    color: var(--primary, #0f6b3e);
    background: #f0fdf4;
    border: 1px solid #86efac;
    padding: 0.05rem 0.4rem;
    border-radius: 20px;
    min-width: 42px;
    text-align: right;
    white-space: nowrap;
  }
  .info-card.expenses .pbc-pct {
    color: #b45309;
    background: #fffbeb;
    border-color: #fde68a;
  }

  .inv-stats {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 0.5rem;
    margin-bottom: 0.6rem;
  }
  .inv-stat {
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
    padding: 0.5rem 0.6rem;
    background: var(--background, #f9fafb);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 8px;
    cursor: help;
  }
  .inv-label {
    font-size: 0.65rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    color: var(--text-light, #6b7280);
  }
  .inv-value {
    font-size: 0.9rem;
    font-weight: 700;
    color: var(--text, #111827);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .inv-explainer {
    font-size: 0.72rem;
    color: var(--text-light, #6b7280);
    line-height: 1.45;
    border-top: 1px dashed var(--border, #e5e7eb);
    padding-top: 0.5rem;
  }
  .inv-explainer p { margin: 0; }
  .inv-explainer strong { color: var(--text, #111827); }

  .exp-total {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    margin: 0.5rem 0 0;
    font-size: 0.72rem;
    color: var(--text-light, #6b7280);
    border-top: 1px dashed var(--border, #e5e7eb);
    padding-top: 0.4rem;
    width: 100%;
  }

  @media (max-width: 480px) {
    .inv-stats { grid-template-columns: 1fr 1fr; }
    .inv-value { font-size: 0.85rem; }
    .pbc-pct { min-width: 38px; font-size: 0.68rem; }
  }
</style>