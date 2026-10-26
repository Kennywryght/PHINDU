<script>
  import { onMount } from "svelte";
  import {
    BarChart3,
    Trophy,
    PiggyBank,
    Clock,
    Receipt,
    FileSpreadsheet,
    Package,
    TrendingUp,
    TrendingDown,
    Minus,
    Bell,
    RefreshCw,
    ChevronLeft,
    ChevronRight,
    ArrowUpRight,
    ArrowDownRight,
    Sparkles,
    Tags,
    Layers,
  } from "lucide-svelte";
  import Layout from "../components/Layout.svelte";
  import API from "../api/api";
  import ExpenseDrilldownModal from "../components/ExpenseDrilldownModal.svelte";
  import * as XLSX from "xlsx";

  let period = "day";
  let loading = true;
  let error = null;
  let summary = null;

  const PAGE_SIZE = 10;
  let marginPage = 0;
  let expensePage = 0;
  let drilldownCategory = null;

  async function fetchSummary() {
    loading = true;
    error = null;
    try {
      const res = await API.get(`/analytics/summary?period=${period}`);
      summary = res.data;
      marginPage = 0;
      expensePage = 0;
    } catch (err) {
      error = "Failed to load insights";
      console.error(err);
    } finally {
      loading = false;
    }
  }

  onMount(fetchSummary);
  $: period, fetchSummary();

  async function exportSales() {
    const res = await API.get("/sales/?limit=200");
    const raw = res.data;
    const salesArr = Array.isArray(raw) ? raw : raw.sales || [];
    const data = salesArr.map((s) => ({
      Products: (s.products || []).join(", "),
      Total: s.total_amount,
      Date: new Date(s.created_at).toLocaleString(),
    }));
    const ws = XLSX.utils.json_to_sheet(data);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Sales");
    XLSX.writeFile(wb, `phindu_sales_${new Date().toISOString().split("T")[0]}.xlsx`);
  }

  async function exportProducts() {
    const res = await API.get("/products/");
    const data = res.data.map((p) => ({
      Name: p.name,
      Category: p.category,
      "Selling Price": p.selling_price,
      "Purchase Price": p.purchase_price,
      Stock: p.stock_qty,
      Status: p.archived ? "Archived" : p.is_deleted ? "Deleted" : "Active",
    }));
    const ws = XLSX.utils.json_to_sheet(data);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Products");
    XLSX.writeFile(wb, `phindu_products_${new Date().toISOString().split("T")[0]}.xlsx`);
  }

  function formatDate(iso) {
    if (!iso) return "—";
    return new Date(iso).toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
    });
  }

  function fmt(n) {
    return Number(n || 0).toLocaleString(undefined, { maximumFractionDigits: 0 });
  }

  function openDrilldown(category) {
    drilldownCategory = category;
  }
  function closeDrilldown() {
    drilldownCategory = null;
  }

  $: maxPeak =
    summary?.peak_hours?.length > 0 ? Math.max(...summary.peak_hours, 1) : 1;

  $: priceChanges = (() => {
    if (!summary) return [];
    if (Array.isArray(summary.recent_price_changes_v2)) {
      return summary.recent_price_changes_v2;
    }
    return (summary.recent_price_changes || []).map((entry) => {
      const costCh = entry.changes.find((c) => c.price_type === "purchase") || null;
      const sellCh = entry.changes.find((c) => c.price_type === "selling") || null;
      return {
        product: entry.product,
        last_cost_change: costCh,
        last_sell_change: sellCh,
        changes: entry.changes,
      };
    });
  })();

  $: bestWorst = (() => {
    const margins = summary?.profit_margins || [];
    if (margins.length === 0) return null;
    return { best: margins[0], worst: margins[margins.length - 1], count: margins.length };
  })();

  $: margins = summary?.profit_margins || [];
  $: marginPageCount = Math.max(1, Math.ceil(margins.length / PAGE_SIZE));
  $: pagedMargins = margins.slice(marginPage * PAGE_SIZE, (marginPage + 1) * PAGE_SIZE);

  $: expenses = summary?.expense_breakdown || [];
  $: expensePageCount = Math.max(1, Math.ceil(expenses.length / PAGE_SIZE));
  $: pagedExpenses = expenses.slice(expensePage * PAGE_SIZE, (expensePage + 1) * PAGE_SIZE);

  // NEW: category performance + top-5 detailed
  $: categoryPerf = summary?.category_performance || [];
  $: topDetailed = summary?.top_products_detailed || [];

  function prevMargin() {
    if (marginPage > 0) marginPage -= 1;
  }
  function nextMargin() {
    if (marginPage < marginPageCount - 1) marginPage += 1;
  }
  function prevExpense() {
    if (expensePage > 0) expensePage -= 1;
  }
  function nextExpense() {
    if (expensePage < expensePageCount - 1) expensePage += 1;
  }
</script>

<Layout title="Insights">
  <div class="insights-page">
    <div class="page-header">
      <h2>
        <BarChart3 size={22} strokeWidth={2} />
        Business Insights
      </h2>
      {#if summary}
        <p class="timestamp">
          Updated {new Date(summary.generated_at).toLocaleTimeString()}
        </p>
      {/if}
    </div>

    {#if loading}
      <div class="state-box">
        <div class="spinner"></div>
        <p>Loading insights...</p>
      </div>
    {:else if error}
      <div class="state-box error">
        <p>{error}</p>
        <button class="btn btn-primary" on:click={fetchSummary} type="button">
          <RefreshCw size={16} strokeWidth={2} /> Retry
        </button>
      </div>
    {:else if summary}
      <!-- ── Week at a glance ── -->
      {#if summary.week_glance}
        {@const wg = summary.week_glance}
        <div class="glance-card">
          <div class="glance-header">
            <Sparkles size={16} strokeWidth={2} />
            <span>This week at a glance</span>
          </div>
          <div class="glance-grid">
            <div class="glance-cell">
              <span class="gl-label">Revenue</span>
              <strong class="gl-value">MWK {fmt(wg.revenue.current)}</strong>
              {#if wg.revenue.percent !== null}
                <span class="gl-delta" class:up={wg.revenue.percent > 0} class:down={wg.revenue.percent < 0}>
                  {#if wg.revenue.percent > 0}<ArrowUpRight size={12} /> +{wg.revenue.percent}%
                  {:else if wg.revenue.percent < 0}<ArrowDownRight size={12} /> {wg.revenue.percent}%
                  {:else}<Minus size={12} /> 0%{/if}
                  vs last week
                </span>
              {/if}
            </div>
            <div class="glance-cell">
              <span class="gl-label">Profit</span>
              <strong class="gl-value">MWK {fmt(wg.profit.current)}</strong>
              {#if wg.profit.percent !== null}
                <span class="gl-delta" class:up={wg.profit.percent > 0} class:down={wg.profit.percent < 0}>
                  {#if wg.profit.percent > 0}<ArrowUpRight size={12} /> +{wg.profit.percent}%
                  {:else if wg.profit.percent < 0}<ArrowDownRight size={12} /> {wg.profit.percent}%
                  {:else}<Minus size={12} /> 0%{/if}
                  vs last week
                </span>
              {/if}
            </div>
            <div class="glance-cell">
              <span class="gl-label">Sales</span>
              <strong class="gl-value">{wg.sales_count.current}</strong>
              {#if wg.sales_count.percent !== null}
                <span class="gl-delta" class:up={wg.sales_count.percent > 0} class:down={wg.sales_count.percent < 0}>
                  {#if wg.sales_count.percent > 0}<ArrowUpRight size={12} /> +{wg.sales_count.percent}%
                  {:else if wg.sales_count.percent < 0}<ArrowDownRight size={12} /> {wg.sales_count.percent}%
                  {:else}<Minus size={12} /> 0%{/if}
                </span>
              {/if}
            </div>
            <div class="glance-cell">
              <span class="gl-label">Avg sale</span>
              <strong class="gl-value">MWK {fmt(wg.avg_sale.current)}</strong>
              {#if wg.avg_sale.percent !== null}
                <span class="gl-delta" class:up={wg.avg_sale.percent > 0} class:down={wg.avg_sale.percent < 0}>
                  {#if wg.avg_sale.percent > 0}<ArrowUpRight size={12} /> +{wg.avg_sale.percent}%
                  {:else if wg.avg_sale.percent < 0}<ArrowDownRight size={12} /> {wg.avg_sale.percent}%
                  {:else}<Minus size={12} /> 0%{/if}
                </span>
              {/if}
            </div>
          </div>
        </div>
      {/if}

      <div class="period-selector">
        <label for="period">Show top products for:</label>
        <select id="period" bind:value={period}>
          <option value="day">Today</option>
          <option value="week">This Week</option>
          <option value="month">This Month</option>
        </select>
      </div>

      <!-- ── Recent Price Changes ── -->
      <div class="card">
        <h3>
          <Bell size={18} strokeWidth={2} />
          Recent Price Changes (Last 30 Days)
        </h3>
        {#if priceChanges.length === 0}
          <p class="empty-text">No price changes in the last 30 days.</p>
        {:else}
          <div class="price-changes-list">
            {#each priceChanges as entry}
              <div class="price-change-item">
                <div class="product-header">
                  <strong>{entry.product.name}</strong>
                  <span class="current-margin">
                    Current margin:
                    {entry.product.current_margin_percent != null
                      ? `${entry.product.current_margin_percent.toFixed(1)}%`
                      : "—"}
                  </span>
                </div>
                <div class="changes-list">
                  {#if entry.last_cost_change}
                    {@const c = entry.last_cost_change}
                    <div class="change-line">
                      <span class="change-type purchase">COST</span>
                      <span class="change-values">
                        {#if c.old_price === null || c.old_price === 0}
                          Set to MWK {c.new_price?.toLocaleString()}
                        {:else}
                          MWK {c.old_price?.toLocaleString()} →
                          MWK {c.new_price?.toLocaleString()}
                        {/if}
                      </span>
                      {#if c.change_percent !== null}
                        {#if c.change_percent > 0}<span class="pct up"><TrendingUp size={11} /> +{c.change_percent}%</span>
                        {:else if c.change_percent < 0}<span class="pct down"><TrendingDown size={11} /> {c.change_percent}%</span>
                        {:else}<span class="pct flat"><Minus size={11} /> 0%</span>{/if}
                      {/if}
                      <span class="change-date">{formatDate(c.changed_at)}</span>
                    </div>
                  {:else}
                    <div class="change-line muted">
                      <span class="change-type purchase off">COST</span>
                      <span class="change-values muted">No change</span>
                    </div>
                  {/if}

                  {#if entry.last_sell_change}
                    {@const s = entry.last_sell_change}
                    <div class="change-line">
                      <span class="change-type selling">SELL</span>
                      <span class="change-values">
                        {#if s.old_price === null || s.old_price === 0}
                          Set to MWK {s.new_price?.toLocaleString()}
                        {:else}
                          MWK {s.old_price?.toLocaleString()} →
                          MWK {s.new_price?.toLocaleString()}
                        {/if}
                      </span>
                      {#if s.change_percent !== null}
                        {#if s.change_percent > 0}<span class="pct up"><TrendingUp size={11} /> +{s.change_percent}%</span>
                        {:else if s.change_percent < 0}<span class="pct down"><TrendingDown size={11} /> {s.change_percent}%</span>
                        {:else}<span class="pct flat"><Minus size={11} /> 0%</span>{/if}
                      {/if}
                      <span class="change-date">{formatDate(s.changed_at)}</span>
                    </div>
                  {:else}
                    <div class="change-line muted">
                      <span class="change-type selling off">SELL</span>
                      <span class="change-values muted">No change</span>
                    </div>
                  {/if}
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </div>

      <!-- ── Top Products (NEW: with parent + category) ── -->
      <div class="card">
        <h3>
          <Trophy size={18} strokeWidth={2} />
          Top 5 Products
        </h3>
        {#if topDetailed.length === 0}
          <p class="empty-text">No sales data for this period.</p>
        {:else}
          <div class="top-list">
            {#each topDetailed as product, i}
              <div class="top-row">
                <span class="top-rank">{i + 1}</span>
                <div class="top-main">
                  <div class="top-name-line">
                    <strong>{product.name}</strong>
                    {#if product.is_variant && product.parent_name}
                      <span class="parent-tag">
                        <Layers size={11} strokeWidth={2} /> {product.parent_name}
                      </span>
                    {/if}
                  </div>
                  <div class="top-meta">
                    {#if product.category}
                      <span class="cat-chip">{product.category}</span>
                    {/if}
                  </div>
                </div>
                <div class="top-qty">
                  <strong>{product.quantity}</strong>
                  <span>units</span>
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </div>

      <!-- ── NEW: Category Performance ── -->
      <div class="card">
        <h3>
          <Tags size={18} strokeWidth={2} />
          Category Performance
        </h3>
        {#if categoryPerf.length === 0}
          <p class="empty-text">No category sales in this period.</p>
        {:else}
          <div class="cat-perf-list">
            {#each categoryPerf as cat}
              <div class="cp-row">
                <div class="cp-top">
                  <strong class="cp-name">{cat.category}</strong>
                  <span class="cp-rev">MWK {fmt(cat.revenue)}</span>
                </div>
                <div class="cp-bar-wrap">
                  <div
                    class="cp-bar"
                    style="width: {Math.min(100, cat.revenue_percent || 0)}%"
                  ></div>
                </div>
                <div class="cp-meta">
                  <span>{cat.revenue_percent}% of revenue</span>
                  <span>{cat.quantity} units · {cat.sale_count} sale{cat.sale_count === 1 ? "" : "s"}</span>
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </div>

      <!-- ── Profit Margins ── -->
      <div class="card">
        <h3>
          <PiggyBank size={18} strokeWidth={2} />
          Profit Margin by Product
        </h3>

        {#if bestWorst && bestWorst.count > 1}
          <div class="best-worst-row">
            <div class="bw-cell best">
              <span>Best margin</span>
              <strong>{bestWorst.best.name}</strong>
              <span class="bw-pct">{bestWorst.best.margin_percent.toFixed(1)}%</span>
            </div>
            <div class="bw-cell worst">
              <span>Worst margin</span>
              <strong>{bestWorst.worst.name}</strong>
              <span class="bw-pct">{bestWorst.worst.margin_percent.toFixed(1)}%</span>
            </div>
          </div>
        {/if}

        {#if margins.length === 0}
          <p class="empty-text">No sales data available.</p>
        {:else}
          <div class="table-wrapper margin-table-wrap">
            <table class="margin-table">
              <thead>
                <tr>
                  <th>Product</th>
                  <th class="num">Revenue</th>
                  <th class="num">Cost</th>
                  <th class="num">Profit</th>
                  <th class="num">Margin</th>
                </tr>
              </thead>
              <tbody>
                {#each pagedMargins as item}
                  <tr>
                    <td class="name-cell">{item.name}</td>
                    <td class="num">{fmt(item.revenue)}</td>
                    <td class="num">{fmt(item.cost)}</td>
                    <td class="num">{fmt(item.profit)}</td>
                    <td class="num margin-value">{item.margin_percent}%</td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>

          <div class="margin-cards">
            {#each pagedMargins as item}
              <div class="margin-card">
                <div class="mc-header">
                  <strong>{item.name}</strong>
                  <span class="mc-margin">{item.margin_percent}%</span>
                </div>
                <div class="mc-row"><span>Revenue</span><span>MWK {fmt(item.revenue)}</span></div>
                <div class="mc-row"><span>Cost</span><span>MWK {fmt(item.cost)}</span></div>
                <div class="mc-row"><span>Profit</span><span class="mc-profit">MWK {fmt(item.profit)}</span></div>
              </div>
            {/each}
          </div>

          {#if marginPageCount > 1}
            <div class="pagination">
              <button class="page-btn" on:click={prevMargin} disabled={marginPage === 0} type="button" aria-label="Previous">
                <ChevronLeft size={16} />
              </button>
              <span class="page-info">
                {marginPage * PAGE_SIZE + 1}–{Math.min((marginPage + 1) * PAGE_SIZE, margins.length)}
                of {margins.length}
              </span>
              <button class="page-btn" on:click={nextMargin} disabled={marginPage >= marginPageCount - 1} type="button" aria-label="Next">
                <ChevronRight size={16} />
              </button>
            </div>
          {/if}
        {/if}
      </div>

      <!-- ── Peak Hours ── -->
      <div class="card">
        <h3>
          <Clock size={18} strokeWidth={2} />
          Busiest Hours
        </h3>
        <div class="peak-chart-wrapper">
          <div class="peak-chart">
            {#each summary.peak_hours as count, hour}
              <div class="peak-bar-container">
                <div class="peak-bar" style="height: {Math.max(3, (count / maxPeak) * 100)}%">
                  {#if count > 0}<span class="peak-value">{count}</span>{/if}
                </div>
                <span class="peak-label">{hour}</span>
              </div>
            {/each}
          </div>
        </div>
        <p class="chart-hint">Bars show sales count per hour (0–23)</p>
      </div>

      <!-- ── Expense Breakdown ── -->
      <div class="card">
        <h3>
          <Receipt size={18} strokeWidth={2} />
          Expenses by Category
        </h3>
        {#if expenses.length === 0}
          <p class="empty-text">No expenses recorded.</p>
        {:else}
          <div class="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Category</th>
                  <th class="num">Amount</th>
                  <th class="action-col"></th>
                </tr>
              </thead>
              <tbody>
                {#each pagedExpenses as item}
                  <tr class="clickable-row" on:click={() => openDrilldown(item.category)} on:keydown={(e) => e.key === "Enter" && openDrilldown(item.category)} role="button" tabindex="0">
                    <td>{item.category}</td>
                    <td class="num">MWK {item.total?.toFixed(2)}</td>
                    <td class="action-col"><ChevronRight size={16} strokeWidth={2} class="chev-icon" /></td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>

          {#if expensePageCount > 1}
            <div class="pagination">
              <button class="page-btn" on:click={prevExpense} disabled={expensePage === 0} type="button" aria-label="Previous">
                <ChevronLeft size={16} />
              </button>
              <span class="page-info">
                {expensePage * PAGE_SIZE + 1}–{Math.min((expensePage + 1) * PAGE_SIZE, expenses.length)}
                of {expenses.length}
              </span>
              <button class="page-btn" on:click={nextExpense} disabled={expensePage >= expensePageCount - 1} type="button" aria-label="Next">
                <ChevronRight size={16} />
              </button>
            </div>
          {/if}
        {/if}
      </div>

      <!-- ── Overview ── -->
      <div class="card">
        <h3>
          <BarChart3 size={18} strokeWidth={2} />
          Overview
        </h3>
        <ul class="overview-list">
          <li><span>Total Products:</span><strong>{summary.counts.total_products}</strong></li>
          <li><span>Total Sales:</span><strong>{summary.counts.total_sales}</strong></li>
        </ul>
      </div>

      <!-- Exports -->
      <div class="export-actions">
        <button class="btn" on:click={exportSales} type="button">
          <FileSpreadsheet size={16} strokeWidth={2} /> Export Sales
        </button>
        <button class="btn" on:click={exportProducts} type="button">
          <Package size={16} strokeWidth={2} /> Export Products
        </button>
      </div>
    {/if}
  </div>

  {#if drilldownCategory !== null}
    <ExpenseDrilldownModal category={drilldownCategory} on:close={closeDrilldown} />
  {/if}
</Layout>

<style>
  /* Same styles as before, plus the new ones below */

  .insights-page {
    max-width: 900px;
    margin: 0 auto;
    display: flex;
    flex-direction: column;
    gap: 1rem;
    overflow-x: hidden;
  }
  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.5rem;
  }
  .page-header h2 {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin: 0;
    font-size: 1.2rem;
    font-weight: 600;
    color: var(--text, #111827);
  }
  .timestamp {
    font-size: 0.75rem;
    color: var(--text-light, #6b7280);
    margin: 0;
  }
  .state-box {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1rem;
    padding: 3rem 1rem;
    color: var(--text-light, #6b7280);
    text-align: center;
  }
  .state-box.error { color: var(--danger, #dc2626); }
  .spinner {
    width: 28px;
    height: 28px;
    border: 3px solid var(--border, #e5e7eb);
    border-top-color: var(--primary, #0f6b3e);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  .glance-card {
    background: linear-gradient(135deg, #eef2ff 0%, #ffffff 100%);
    border: 1px solid #c7d2fe;
    border-radius: 12px;
    padding: 0.9rem 1rem;
  }
  .glance-header {
    display: flex; align-items: center; gap: 0.4rem;
    font-size: 0.78rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.04em; color: #3730a3; margin-bottom: 0.6rem;
  }
  .glance-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.55rem; }
  .glance-cell { display: flex; flex-direction: column; gap: 0.15rem; min-width: 0; }
  .gl-label {
    font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.04em;
    color: var(--text-light, #6b7280); font-weight: 600;
  }
  .gl-value {
    font-size: 1.05rem; font-weight: 700; color: var(--text, #111827);
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }
  .gl-delta {
    display: inline-flex; align-items: center; gap: 0.15rem;
    font-size: 0.7rem; font-weight: 600; color: var(--text-light, #6b7280);
  }
  .gl-delta.up { color: #166534; }
  .gl-delta.down { color: #991b1b; }

  .period-selector {
    display: flex; align-items: center; gap: 0.75rem;
    background: var(--surface, #fff); padding: 0.85rem;
    border-radius: 10px; border: 1px solid var(--border, #e5e7eb);
    flex-wrap: wrap;
  }
  .period-selector label { font-size: 0.9rem; color: var(--text, #111827); }
  .period-selector select {
    padding: 0.45rem 0.7rem; border-radius: 8px;
    border: 1px solid var(--border, #e5e7eb);
    background: var(--surface, #fff); color: var(--text, #111827);
    font-size: 0.9rem;
  }
  .card {
    background: var(--surface, #fff); border-radius: 12px;
    padding: 1.25rem; border: 1px solid var(--border, #e5e7eb);
    overflow: hidden;
  }
  .card h3 {
    display: flex; align-items: center; gap: 0.5rem;
    margin-top: 0; margin-bottom: 1rem;
    font-size: 1rem; font-weight: 600; color: var(--text, #111827);
  }
  .table-wrapper { overflow-x: auto; border-radius: 8px; }
  table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
  th, td {
    text-align: left; padding: 0.6rem 0.5rem;
    border-bottom: 1px solid var(--border, #e5e7eb);
  }
  th {
    background: var(--background, #f9fafb); font-weight: 600;
    color: var(--text-light, #6b7280); font-size: 0.78rem;
    text-transform: uppercase;
  }
  th.num, td.num { text-align: right; white-space: nowrap; }
  .margin-value { font-weight: 600; color: var(--success, #16a34a); }
  .name-cell { max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .empty-text {
    text-align: center; padding: 1.5rem;
    color: var(--text-light, #6b7280); font-size: 0.9rem;
  }

  /* NEW: Top 5 list */
  .top-list { display: flex; flex-direction: column; gap: 0.4rem; }
  .top-row {
    display: flex; align-items: center; gap: 0.6rem;
    padding: 0.55rem 0.7rem;
    background: var(--background, #f9fafb);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 8px;
  }
  .top-rank {
    width: 24px; height: 24px; flex-shrink: 0;
    display: inline-flex; align-items: center; justify-content: center;
    background: var(--primary, #0f6b3e); color: white;
    border-radius: 50%; font-size: 0.75rem; font-weight: 700;
  }
  .top-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 0.1rem; }
  .top-name-line { display: flex; align-items: center; gap: 0.35rem; flex-wrap: wrap; }
  .top-name-line strong {
    font-size: 0.88rem; color: var(--text, #111827); font-weight: 600;
  }
  .parent-tag {
    display: inline-flex; align-items: center; gap: 0.15rem;
    font-size: 0.68rem; font-weight: 500;
    background: #dbeafe; color: #1e40af;
    padding: 0.1rem 0.4rem; border-radius: 20px;
  }
  .top-meta { display: flex; align-items: center; gap: 0.3rem; }
  .cat-chip {
    display: inline-block; font-size: 0.68rem; font-weight: 500;
    background: var(--background, #f9fafb);
    border: 1px solid var(--border, #e5e7eb);
    color: var(--text-light, #6b7280);
    padding: 0.05rem 0.4rem; border-radius: 20px;
  }
  .top-qty { display: flex; flex-direction: column; align-items: flex-end; flex-shrink: 0; }
  .top-qty strong {
    font-size: 1rem; font-weight: 700; color: var(--primary, #0f6b3e);
  }
  .top-qty span { font-size: 0.68rem; color: var(--text-light, #6b7280); }

  /* NEW: Category performance */
  .cat-perf-list { display: flex; flex-direction: column; gap: 0.65rem; }
  .cp-row { display: flex; flex-direction: column; gap: 0.3rem; }
  .cp-top { display: flex; justify-content: space-between; align-items: baseline; gap: 0.5rem; }
  .cp-name { font-size: 0.9rem; font-weight: 600; color: var(--text, #111827); }
  .cp-rev { font-size: 0.85rem; font-weight: 700; color: var(--primary, #0f6b3e); }
  .cp-bar-wrap {
    width: 100%; height: 6px; background: var(--background, #f3f4f6);
    border-radius: 4px; overflow: hidden;
  }
  .cp-bar {
    height: 100%; background: var(--primary, #0f6b3e);
    border-radius: 4px; transition: width 0.3s;
  }
  .cp-meta {
    display: flex; justify-content: space-between;
    font-size: 0.72rem; color: var(--text-light, #6b7280);
  }

  .overview-list {
    list-style: none; padding: 0; margin: 0;
    display: flex; flex-direction: column; gap: 0.5rem;
  }
  .overview-list li {
    display: flex; justify-content: space-between;
    padding: 0.5rem 0; border-bottom: 1px dashed var(--border, #e5e7eb);
    font-size: 0.9rem;
  }
  .overview-list li:last-child { border-bottom: none; }
  .overview-list span { color: var(--text-light, #6b7280); }

  /* Price changes */
  .price-changes-list { display: flex; flex-direction: column; gap: 0.65rem; }
  .price-change-item {
    padding: 0.75rem; background: var(--background, #f9fafb);
    border-radius: 8px; border: 1px solid var(--border, #e5e7eb);
  }
  .product-header {
    display: flex; justify-content: space-between; align-items: center;
    margin-bottom: 0.5rem; gap: 0.5rem; flex-wrap: wrap;
  }
  .product-header strong { font-size: 0.95rem; color: var(--text, #111827); }
  .current-margin { font-size: 0.78rem; color: var(--text-light, #6b7280); }
  .changes-list { display: flex; flex-direction: column; gap: 0.35rem; }
  .change-line {
    display: flex; align-items: center; gap: 0.5rem;
    flex-wrap: wrap; font-size: 0.82rem;
  }
  .change-line.muted { opacity: 0.6; }
  .change-type {
    font-size: 0.62rem; font-weight: 700;
    padding: 0.1rem 0.35rem; border-radius: 3px;
    letter-spacing: 0.3px;
  }
  .change-type.selling { background: #dbeafe; color: #1e40af; }
  .change-type.purchase { background: #fef3c7; color: #92400e; }
  .change-type.off { background: #e5e7eb; color: #9ca3af; }
  .change-values { color: var(--text, #111827); font-weight: 500; }
  .change-values.muted { color: var(--text-light, #6b7280); font-style: italic; font-weight: 400; }
  .pct {
    display: inline-flex; align-items: center; gap: 0.1rem;
    font-size: 0.72rem; font-weight: 600;
    padding: 0.1rem 0.35rem; border-radius: 20px;
  }
  .pct.up { background: #dcfce7; color: #166534; }
  .pct.down { background: #fee2e2; color: #991b1b; }
  .pct.flat { background: var(--surface, #fff); color: var(--text-light, #6b7280); }
  .change-date {
    margin-left: auto; font-size: 0.72rem; color: var(--text-light, #6b7280);
  }

  .best-worst-row {
    display: grid; grid-template-columns: 1fr 1fr;
    gap: 0.6rem; margin-bottom: 1rem;
  }
  .bw-cell {
    display: flex; flex-direction: column; gap: 0.15rem;
    padding: 0.6rem 0.75rem; border-radius: 8px;
    font-size: 0.82rem; min-width: 0;
  }
  .bw-cell span:first-child {
    font-size: 0.7rem; text-transform: uppercase;
    letter-spacing: 0.04em; font-weight: 600;
    color: var(--text-light, #6b7280);
  }
  .bw-cell strong {
    font-size: 0.95rem; font-weight: 600;
    color: var(--text, #111827);
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }
  .bw-cell .bw-pct {
    font-size: 0.8rem; font-weight: 700;
    text-transform: none; letter-spacing: 0;
  }
  .bw-cell.best { background: #f0fdf4; border: 1px solid #86efac; }
  .bw-cell.best .bw-pct { color: #166534; }
  .bw-cell.worst { background: #fef2f2; border: 1px solid #fecaca; }
  .bw-cell.worst .bw-pct { color: #991b1b; }

  .margin-cards { display: none; flex-direction: column; gap: 0.5rem; }
  .margin-card {
    background: var(--background, #f9fafb);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 8px; padding: 0.65rem 0.75rem;
  }
  .mc-header {
    display: flex; justify-content: space-between;
    align-items: baseline; gap: 0.5rem; margin-bottom: 0.35rem;
  }
  .mc-header strong {
    font-size: 0.9rem; color: var(--text, #111827);
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0;
  }
  .mc-margin { font-weight: 700; color: #166534; font-size: 0.88rem; flex-shrink: 0; }
  .mc-row {
    display: flex; justify-content: space-between;
    font-size: 0.78rem; color: var(--text-light, #6b7280); padding: 0.1rem 0;
  }
  .mc-row .mc-profit { color: var(--text, #111827); font-weight: 600; }

  .pagination {
    display: flex; align-items: center; justify-content: center;
    gap: 0.6rem; padding: 0.75rem 0 0;
    margin-top: 0.5rem; border-top: 1px solid var(--border, #e5e7eb);
  }
  .page-btn {
    display: inline-flex; align-items: center; justify-content: center;
    width: 32px; height: 32px; border-radius: 6px;
    border: 1px solid var(--border, #e5e7eb);
    background: var(--surface, #fff); color: var(--text, #111827);
    cursor: pointer; transition: all 0.15s;
  }
  .page-btn:hover:not(:disabled) {
    border-color: var(--primary, #0f6b3e); color: var(--primary, #0f6b3e);
  }
  .page-btn:disabled { opacity: 0.4; cursor: not-allowed; }
  .page-info {
    font-size: 0.8rem; color: var(--text-light, #6b7280); font-weight: 500;
  }

  .clickable-row { cursor: pointer; transition: background 0.15s; }
  .clickable-row:hover { background: #f0fdf4; }
  .action-col { width: 24px; text-align: right; }
  .chev-icon { color: var(--text-light, #6b7280); }

  .peak-chart-wrapper { width: 100%; overflow: hidden; }
  .peak-chart {
    display: flex; align-items: flex-end; gap: 0.15rem;
    height: 140px; width: 100%; box-sizing: border-box;
  }
  .peak-bar-container {
    flex: 1 1 0; min-width: 0; display: flex;
    flex-direction: column; align-items: center;
    height: 100%; justify-content: flex-end;
  }
  .peak-bar {
    width: 100%; background: var(--primary, #0f6b3e);
    border-radius: 2px 2px 0 0; min-height: 3px;
    position: relative; transition: height 0.3s;
    display: flex; justify-content: center; align-items: flex-start;
    padding-top: 0.15rem; box-sizing: border-box; overflow: hidden;
  }
  .peak-value { color: white; font-size: 0.55rem; font-weight: 700; line-height: 1; }
  .peak-label {
    margin-top: 0.25rem; font-size: 0.58rem;
    color: var(--text-light, #6b7280); text-align: center;
  }
  .chart-hint {
    text-align: center; font-size: 0.75rem;
    color: var(--text-light, #6b7280);
    margin-top: 0.5rem; margin-bottom: 0;
  }

  .export-actions {
    display: flex; gap: 0.6rem; flex-wrap: wrap; margin-top: 0.5rem;
  }
  .btn {
    display: inline-flex; align-items: center; gap: 0.4rem;
    padding: 0.55rem 1rem; border-radius: 8px;
    border: 1px solid var(--border, #e5e7eb);
    background: var(--surface, #fff); color: var(--text, #111827);
    cursor: pointer; font-weight: 500; font-size: 0.9rem;
    transition: all 0.15s;
  }
  .btn:hover { border-color: var(--primary, #0f6b3e); color: var(--primary, #0f6b3e); }
  .btn-primary { background: var(--primary, #0f6b3e); color: white; border-color: var(--primary, #0f6b3e); }

  @media (max-width: 768px) {
    .card { padding: 1rem; }
    .glance-grid { grid-template-columns: repeat(2, 1fr); gap: 0.55rem 0.75rem; }
    .period-selector { flex-direction: column; align-items: stretch; }
    .period-selector select { width: 100%; }
    .peak-chart { height: 110px; }
    .peak-value { display: none; }
    .peak-label { font-size: 0.5rem; }
    .export-actions { flex-direction: column; }
    .export-actions .btn { justify-content: center; width: 100%; }
  }

  @media (max-width: 480px) {
    .margin-table-wrap { display: none; }
    .margin-cards { display: flex; }
    .best-worst-row { grid-template-columns: 1fr; gap: 0.45rem; }
    th, td { padding: 0.45rem 0.35rem; font-size: 0.82rem; }
    .peak-chart { height: 90px; }
    .gl-value { font-size: 0.95rem; }
  }
</style>