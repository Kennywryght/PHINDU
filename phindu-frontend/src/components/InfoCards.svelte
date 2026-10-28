<script>
  import {
    Sparkles,
    Package,
    TrendingUp,
    Users,
    Wallet,
    PiggyBank,
    AlertCircle,
  } from "lucide-svelte";

  export let goodNews = [];
  export let willRunOut = [];
  export let profitByCategory = [];
  export let inventoryValue = null;
  export let expenseBreakdown = null;
  // NOTE: customerHealth was removed — the parent no longer passes it.
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
                {#if p.recommended_order_qty}
                  · Order ~{p.recommended_order_qty}
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
              MWK {Number(c.profit || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}
            </span>
            <span class="pbc-pct">{Number(c.margin_percent || 0).toFixed(1)}%</span>
          </li>
        {/each}
      </ul>
    </div>
  {/if}

  <!-- ── Inventory value (with plain-English explanation) ── -->
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
          <strong class="inv-value">MWK {Number(inventoryValue.cost_value || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}</strong>
        </div>
        <div class="inv-stat" title="Money you would make if you sold ALL stock at today's prices (revenue − cost)">
          <span class="inv-label">Potential profit</span>
          <strong class="inv-value">MWK {Number(inventoryValue.potential_margin || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}</strong>
        </div>
        <div class="inv-stat" title="Average number of times your stock sells out and is refilled per month. Higher = faster money turn-around">
          <span class="inv-label">Turnover</span>
          <strong class="inv-value">{Number(inventoryValue.turnover || 0).toFixed(1)}×</strong>
        </div>
      </div>

      <div class="inv-explainer">
        <p>
          <strong>SKUs</strong> = how many different products you stock.<br />
          <strong>Potential profit</strong> = what you'd earn if all current stock sold at
          today's prices. It's not money in the bank yet — it's the value sitting on
          your shelves.<br />
          <strong>Turnover</strong> = how many times per month your average stock gets
          sold and replaced. A turnover of <em>2×</em> means you cycle through your
          stock twice a month. Higher is better — it means cash isn't stuck on shelves.
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
            <span class="pbc-val">
              MWK {Number(c.total || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}
            </span>
            <span class="pbc-pct">{Number(c.percent || 0).toFixed(0)}%</span>
          </li>
        {/each}
      </ul>
      {#if expenseBreakdown.total != null}
        <p class="exp-total">
          <PiggyBank size={12} /> Total: MWK
          {Number(expenseBreakdown.total || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}
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
    grid-template-columns: 1fr auto auto;
    align-items: baseline;
    gap: 0.5rem;
  }
  .pbc-name {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: var(--text, #111827);
  }
  .pbc-val { font-weight: 600; color: var(--text, #111827); }
  .pbc-pct {
    font-size: 0.7rem;
    color: var(--text-light, #6b7280);
    min-width: 34px;
    text-align: right;
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
  }
</style>