<script>
  import { onMount } from 'svelte';
  import {
    BarChart3,
    Trophy,
    PiggyBank,
    Clock,
    Receipt,
    FileSpreadsheet,
    Package,
  } from 'lucide-svelte';
  import Layout from '../components/Layout.svelte';
  import API from '../api/api';
  import * as XLSX from 'xlsx';

  let period = 'day';
  let topProducts = [];
  let loading = false;
  let error = null;
  let insights = null;
  let dashboard = null;

  let profitMargins = [];
  let marginsLoading = false;
  let marginsError = null;

  let peakHours = [];
  let peakLoading = false;

  let expenseBreakdown = [];
  let breakdownLoading = false;

  onMount(async () => {
    await Promise.all([
      fetchInsights(),
      fetchTopProducts(),
      fetchProfitMargins(),
      fetchPeakHours(),
      fetchExpenseBreakdown(),
    ]);
  });

  async function fetchInsights() {
    try {
      const res = await API.get('/analytics/insights');
      insights = res.data;
    } catch (err) {
      try {
        const dashRes = await API.get('/dashboard/');
        dashboard = dashRes.data;
      } catch (e) {
        error = 'Unable to load insights data';
      }
    }
  }

  async function fetchTopProducts() {
    loading = true;
    error = null;
    try {
      const res = await API.get(`/analytics/top-products?period=${period}`);
      topProducts = res.data;
    } catch (err) {
      error = 'Failed to load top products';
    } finally {
      loading = false;
    }
  }

  async function fetchProfitMargins() {
    marginsLoading = true;
    try {
      const res = await API.get('/analytics/profit-margins');
      profitMargins = res.data;
    } catch (err) {
      marginsError = 'Failed to load profit margins';
    } finally {
      marginsLoading = false;
    }
  }

  async function fetchPeakHours() {
    peakLoading = true;
    try {
      const res = await API.get('/analytics/peak-hours');
      peakHours = res.data.hours;
    } catch (err) {
      console.error('Peak hours failed', err);
    } finally {
      peakLoading = false;
    }
  }

  async function fetchExpenseBreakdown() {
    breakdownLoading = true;
    try {
      const res = await API.get('/analytics/expense-breakdown');
      expenseBreakdown = res.data;
    } catch (err) {
      console.error('Expense breakdown failed', err);
    } finally {
      breakdownLoading = false;
    }
  }

  async function exportSales() {
    const res = await API.get('/sales/');
    const data = res.data.map((s) => ({
      Products: s.products.join(', '),
      Total: s.total_amount,
      Date: new Date(s.created_at).toLocaleString(),
    }));
    const ws = XLSX.utils.json_to_sheet(data);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Sales');
    XLSX.writeFile(wb, `phindu_sales_${new Date().toISOString().split('T')[0]}.xlsx`);
  }

  async function exportProducts() {
    const res = await API.get('/products/');
    const data = res.data.map((p) => ({
      Name: p.name,
      Category: p.category,
      'Selling Price': p.selling_price,
      'Purchase Price': p.purchase_price,
      Stock: p.stock_qty,
      Status: p.archived ? 'Archived' : p.is_deleted ? 'Deleted' : 'Active',
    }));
    const ws = XLSX.utils.json_to_sheet(data);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Products');
    XLSX.writeFile(wb, `phindu_products_${new Date().toISOString().split('T')[0]}.xlsx`);
  }

  $: period, fetchTopProducts();
  $: maxPeak = peakHours.length > 0 ? Math.max(...peakHours, 1) : 1;
</script>

<Layout title="Insights">
  <div class="insights-page">
    <div class="page-header">
      <h2>
        <BarChart3 size={22} strokeWidth={2} />
        Business Insights
      </h2>
    </div>

    <div class="period-selector">
      <label for="period">Show top products for:</label>
      <select id="period" bind:value={period}>
        <option value="day">Today</option>
        <option value="week">This Week</option>
        <option value="month">This Month</option>
      </select>
    </div>

    <!-- Top Products -->
    <div class="card">
      <h3>
        <Trophy size={18} strokeWidth={2} />
        Top Selling Products
      </h3>
      {#if loading}
        <p class="loading-text">Loading...</p>
      {:else if error}
        <p class="error">{error}</p>
      {:else if topProducts.length === 0}
        <p class="empty-text">No sales data for this period.</p>
      {:else}
        <div class="table-wrapper">
          <table>
            <thead>
              <tr><th>Product</th><th>Quantity Sold</th></tr>
            </thead>
            <tbody>
              {#each topProducts as product}
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
      {#if marginsLoading}
        <p class="loading-text">Loading...</p>
      {:else if marginsError}
        <p class="error">{marginsError}</p>
      {:else if profitMargins.length === 0}
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
              {#each profitMargins as item}
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
      {#if peakLoading}
        <p class="loading-text">Loading...</p>
      {:else}
        <div class="peak-chart-wrapper">
          <div class="peak-chart">
            {#each peakHours as count, hour}
              <div class="peak-bar-container">
                <div
                  class="peak-bar"
                  style="height: {Math.max(3, (count / maxPeak) * 100)}%"
                >
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
      {/if}
    </div>

    <!-- Expense Breakdown -->
    <div class="card">
      <h3>
        <Receipt size={18} strokeWidth={2} />
        Expenses by Category
      </h3>
      {#if breakdownLoading}
        <p class="loading-text">Loading...</p>
      {:else if expenseBreakdown.length === 0}
        <p class="empty-text">No expenses recorded.</p>
      {:else}
        <div class="table-wrapper">
          <table>
            <thead>
              <tr><th>Category</th><th>Amount</th></tr>
            </thead>
            <tbody>
              {#each expenseBreakdown as item}
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
      {#if insights}
        <ul class="overview-list">
          <li><span>Total Products:</span> <strong>{insights.total_products}</strong></li>
          <li><span>Total Sales:</span> <strong>{insights.total_sales}</strong></li>
        </ul>
      {:else if dashboard}
        <ul class="overview-list">
          <li><span>Revenue:</span> <strong>MWK {dashboard.total_revenue?.toLocaleString()}</strong></li>
          <li><span>Profit:</span> <strong>MWK {dashboard.profit?.toLocaleString()}</strong></li>
        </ul>
      {/if}
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
  .page-header h2 {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin: 0;
    font-size: 1.2rem;
    font-weight: 600;
    color: var(--text, #111827);
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
  .error {
    color: var(--danger, #dc2626);
    text-align: center;
    padding: 1rem;
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

  /* ====== PEAK CHART — no horizontal scroll ====== */
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

  /* ====== EXPORTS ====== */
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

  /* ====== MOBILE ====== */
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