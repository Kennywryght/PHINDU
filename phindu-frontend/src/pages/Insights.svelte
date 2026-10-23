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
  } from "lucide-svelte";
  import Layout from "../components/Layout.svelte";
  import API from "../api/api";
  import * as XLSX from "xlsx";

  let period = "day";
  let loading = true;
  let error = null;

  // Single summary data object
  let summary = null;

  async function fetchSummary() {
    loading = true;
    error = null;
    try {
      const res = await API.get(`/analytics/summary?period=${period}`);
      summary = res.data;
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
    const res = await API.get("/sales/");
    const data = res.data.map((s) => ({
      Products: s.products.join(", "),
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
    return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });
  }

  $: maxPeak = summary?.peak_hours?.length > 0 ? Math.max(...summary.peak_hours, 1) : 1;
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

    <div class="period-selector">
      <label for="period">Show top products for:</label>
      <select id="period" bind:value={period}>
        <option value="day">Today</option>
        <option value="week">This Week</option>
        <option value="month">This Month</option>
      </select>
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
      <!-- Recent Price Changes -->
      <div class="card">
        <h3>
          <Bell size={18} strokeWidth={2} />
          Recent Price Changes (Last 30 Days)
        </h3>
        {#if summary.recent_price_changes.length === 0}
          <p class="empty-text">No price changes in the last 30 days.</p>
        {:else}
          <div class="price-changes-list">
            {#each summary.recent_price_changes as entry}
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
                  {#each entry.changes as change}
                    <div class="change-line">
                      <span class="change-type {change.price_type}">
                        {change.price_type === "purchase" ? "COST" : "SELL"}
                      </span>
                      <span class="change-values">
                        {#if change.old_price === null || change.old_price === 0}
                          Set to MWK {change.new_price?.toLocaleString()}
                        {:else}
                          MWK {change.old_price?.toLocaleString()} →
                          MWK {change.new_price?.toLocaleString()}
                        {/if}
                      </span>
                      {#if change.change_percent !== null}
                        {#if change.change_percent > 0}
                          <span class="pct up">
                            <TrendingUp size={11} /> +{change.change_percent}%
                          </span>
                        {:else if change.change_percent < 0}
                          <span class="pct down">
                            <TrendingDown size={11} /> {change.change_percent}%
                          </span>
                        {:else}
                          <span class="pct flat"><Minus size={11} /> 0%</span>
                        {/if}
                      {/if}
                      <span class="change-date">{formatDate(change.changed_at)}</span>
                    </div>
                  {/each}
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </div>

      <!-- Top Products -->
      <div class="card">
        <h3>
          <Trophy size={18} strokeWidth={2} />
          Top Selling Products
        </h3>
        {#if summary.top_products.length === 0}
          <p class="empty-text">No sales data for this period.</p>
        {:else}
          <div class="table-wrapper">
            <table>
              <thead>
                <tr><th>Product</th><th>Quantity Sold</th></tr>
              </thead>
              <tbody>
                {#each summary.top_products as product}
                  <tr>
                    <td>{product.name}</td>
                    <td><strong>{product.quantity}</strong></td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        {/if}
      </div>

      <!-- Profit Margins -->
      <div class="card">
        <h3>
          <PiggyBank size={18} strokeWidth={2} />
          Profit Margin by Product
        </h3>
        {#if summary.profit_margins.length === 0}
          <p class="empty-text">No sales data available.</p>
        {:else}
          <div class="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Product</th>
                  <th>Revenue</th>
                  <th>Cost</th>
                  <th>Profit</th>
                  <th>Margin %</th>
                </tr>
              </thead>
              <tbody>
                {#each summary.profit_margins as item}
                  <tr>
                    <td>{item.name}</td>
                    <td>MWK {item.revenue?.toFixed(2)}</td>
                    <td>MWK {item.cost?.toFixed(2)}</td>
                    <td>MWK {item.profit?.toFixed(2)}</td>
                    <td class="margin-value">{item.margin_percent}%</td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        {/if}
      </div>

      <!-- Peak Hours -->
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
                  {#if count > 0}
                    <span class="peak-value">{count}</span>
                  {/if}
                </div>
                <span class="peak-label">{hour}</span>
              </div>
            {/each}
          </div>
        </div>
        <p class="chart-hint">Bars show sales count per hour (0–23)</p>
      </div>

      <!-- Expense Breakdown -->
      <div class="card">
        <h3>
          <Receipt size={18} strokeWidth={2} />
          Expenses by Category
        </h3>
        {#if summary.expense_breakdown.length === 0}
          <p class="empty-text">No expenses recorded.</p>
        {:else}
          <div class="table-wrapper">
            <table>
              <thead>
                <tr><th>Category</th><th>Amount</th></tr>
              </thead>
              <tbody>
                {#each summary.expense_breakdown as item}
                  <tr>
                    <td>{item.category}</td>
                    <td>MWK {item.total?.toFixed(2)}</td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        {/if}
      </div>

      <!-- Overview -->
      <div class="card">
        <h3>
          <BarChart3 size={18} strokeWidth={2} />
          Overview
        </h3>
        <ul class="overview-list">
          <li>
            <span>Total Products:</span>
            <strong>{summary.counts.total_products}</strong>
          </li>
          <li>
            <span>Total Sales:</span>
            <strong>{summary.counts.total_sales}</strong>
          </li>
        </ul>
      </div>

      <!-- Exports -->
      <div class="export-actions">
        <button class="btn btn-secondary" on:click={exportSales} type="button">
          <FileSpreadsheet size={16} strokeWidth={2} /> Export Sales
        </button>
        <button class="btn btn-secondary" on:click={exportProducts} type="button">
          <Package size={16} strokeWidth={2} /> Export Products
        </button>
      </div>
    {/if}
  </div>
</Layout>

<style>
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

  .state-box.error {
    color: var(--danger, #dc2626);
  }

  .spinner {
    width: 28px;
    height: 28px;
    border: 3px solid var(--border, #e5e7eb);
    border-top-color: var(--primary, #0f6b3e);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  .period-selector {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    background: var(--surface, #fff);
    padding: 0.85rem;
    border-radius: 10px;
    border: 1px solid var(--border, #e5e7eb);
    flex-wrap: wrap;
  }
  .period-selector label {
    font-size: 0.9rem;
    color: var(--text, #111827);
  }
  .period-selector select {
    padding: 0.45rem 0.7rem;
    border-radius: 8px;
    border: 1px solid var(--border, #e5e7eb);
    background: var(--surface, #fff);
    color: var(--text, #111827);
    font-size: 0.9rem;
  }
  .card {
    background: var(--surface, #fff);
    border-radius: 12px;
    padding: 1.25rem;
    border: 1px solid var(--border, #e5e7eb);
    overflow: hidden;
  }
  .card h3 {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-top: 0;
    margin-bottom: 1rem;
    font-size: 1rem;
    font-weight: 600;
    color: var(--text, #111827);
  }
  .table-wrapper {
    overflow-x: auto;
    border-radius: 8px;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.9rem;
  }
  th,
  td {
    text-align: left;
    padding: 0.6rem 0.5rem;
    border-bottom: 1px solid var(--border, #e5e7eb);
  }
  th {
    background: var(--background, #f9fafb);
    font-weight: 600;
    color: var(--text-light, #6b7280);
    font-size: 0.78rem;
    text-transform: uppercase;
  }
  .margin-value {
    font-weight: 600;
    color: var(--success, #16a34a);
  }
  .loading-text,
  .empty-text {
    text-align: center;
    padding: 1.5rem;
    color: var(--text-light, #6b7280);
    font-size: 0.9rem;
  }
  .overview-list {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }
  .overview-list li {
    display: flex;
    justify-content: space-between;
    padding: 0.5rem 0;
    border-bottom: 1px dashed var(--border, #e5e7eb);
    font-size: 0.9rem;
  }
  .overview-list li:last-child {
    border-bottom: none;
  }
  .overview-list span {
    color: var(--text-light, #6b7280);
  }

  .price-changes-list {
    display: flex;
    flex-direction: column;
    gap: 0.65rem;
  }

  .price-change-item {
    padding: 0.75rem;
    background: var(--background, #f9fafb);
    border-radius: 8px;
    border: 1px solid var(--border, #e5e7eb);
  }

  .product-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.5rem;
    gap: 0.5rem;
    flex-wrap: wrap;
  }

  .product-header strong {
    font-size: 0.95rem;
    color: var(--text, #111827);
  }

  .current-margin {
    font-size: 0.78rem;
    color: var(--text-light, #6b7280);
  }

  .changes-list {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
  }

  .change-line {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-wrap: wrap;
    font-size: 0.82rem;
  }

  .change-type {
    font-size: 0.62rem;
    font-weight: 700;
    padding: 0.1rem 0.35rem;
    border-radius: 3px;
    letter-spacing: 0.3px;
  }

  .change-type.selling {
    background: #dbeafe;
    color: #1e40af;
  }

  .change-type.purchase {
    background: #fef3c7;
    color: #92400e;
  }

  .change-values {
    color: var(--text, #111827);
    font-weight: 500;
  }

  .pct {
    display: inline-flex;
    align-items: center;
    gap: 0.1rem;
    font-size: 0.72rem;
    font-weight: 600;
    padding: 0.1rem 0.35rem;
    border-radius: 20px;
  }

  .pct.up {
    background: #dcfce7;
    color: #166534;
  }

  .pct.down {
    background: #fee2e2;
    color: #991b1b;
  }

  .pct.flat {
    background: var(--surface, #fff);
    color: var(--text-light, #6b7280);
  }

  .change-date {
    margin-left: auto;
    font-size: 0.72rem;
    color: var(--text-light, #6b7280);
  }

  .peak-chart-wrapper {
    width: 100%;
    overflow: hidden;
  }
  .peak-chart {
    display: flex;
    align-items: flex-end;
    gap: 0.15rem;
    height: 140px;
    width: 100%;
    box-sizing: border-box;
  }
  .peak-bar-container {
    flex: 1 1 0;
    min-width: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    height: 100%;
    justify-content: flex-end;
  }
  .peak-bar {
    width: 100%;
    background: var(--primary, #0f6b3e);
    border-radius: 2px 2px 0 0;
    min-height: 3px;
    position: relative;
    transition: height 0.3s;
    display: flex;
    justify-content: center;
    align-items: flex-start;
    padding-top: 0.15rem;
    box-sizing: border-box;
    overflow: hidden;
  }
  .peak-value {
    color: white;
    font-size: 0.55rem;
    font-weight: 700;
    line-height: 1;
  }
  .peak-label {
    margin-top: 0.25rem;
    font-size: 0.58rem;
    color: var(--text-light, #6b7280);
    text-align: center;
  }
  .chart-hint {
    text-align: center;
    font-size: 0.75rem;
    color: var(--text-light, #6b7280);
    margin-top: 0.5rem;
    margin-bottom: 0;
  }

  .export-actions {
    display: flex;
    gap: 0.6rem;
    flex-wrap: wrap;
    margin-top: 0.5rem;
  }
  .btn {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.55rem 1rem;
    border-radius: 8px;
    border: 1px solid var(--border, #e5e7eb);
    background: var(--surface, #fff);
    color: var(--text, #111827);
    cursor: pointer;
    font-weight: 500;
    font-size: 0.9rem;
    transition: all 0.15s;
  }
  .btn:hover {
    border-color: var(--primary, #0f6b3e);
    color: var(--primary, #0f6b3e);
  }

  @media (max-width: 768px) {
    .card {
      padding: 1rem;
    }
    .period-selector {
      flex-direction: column;
      align-items: stretch;
    }
    .period-selector select {
      width: 100%;
    }
    .peak-chart {
      height: 110px;
    }
    .peak-value {
      display: none;
    }
    .peak-label {
      font-size: 0.5rem;
    }
    .export-actions {
      flex-direction: column;
    }
    .export-actions .btn {
      justify-content: center;
      width: 100%;
    }
  }

  @media (max-width: 480px) {
    th,
    td {
      padding: 0.45rem 0.35rem;
      font-size: 0.82rem;
    }
    .peak-chart {
      height: 90px;
    }
  }
</style>