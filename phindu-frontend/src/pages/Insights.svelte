<script>
  import { onMount } from 'svelte';
  import Layout from '../components/Layout.svelte';
  import API from '../api/api';

  let period = 'day';
  let topProducts = [];
  let loading = false;
  let error = null;
  let insights = null;
  let dashboard = null;

  onMount(async () => {
    await fetchInsights();
    fetchTopProducts();
  });

  async function fetchInsights() {
    try {
      const res = await API.get('/analytics/insights');
      insights = res.data;
    } catch (err) {
      console.warn('Insights failed, using dashboard fallback');
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
      console.error(err);
    } finally {
      loading = false;
    }
  }

  // Refetch when period changes
  $: period, fetchTopProducts();

let profitMargins = [];
let marginsLoading = false;
let marginsError = null;

async function fetchProfitMargins() {
  marginsLoading = true;
  marginsError = null;
  try {
    const res = await API.get('/analytics/profit-margins');
    profitMargins = res.data;
  } catch (err) {
    marginsError = 'Failed to load profit margins';
    console.error(err);
  } finally {
    marginsLoading = false;
  }
}

// Call it on mount
onMount(() => {
  fetchInsights();
  fetchTopProducts();
  fetchProfitMargins();
});  
</script>

<Layout title="Insights">
  <div class="insights-page">
    <h2>📊 Business Insights</h2>

    <!-- Period Selector -->
    <div class="period-selector">
      <label for="period">Show top products for:</label>
      <select id="period" bind:value={period}>
        <option value="day">Today</option>
        <option value="week">This Week</option>
        <option value="month">This Month</option>
      </select>
    </div>

    <!-- Top Products Card -->
    <div class="card">
      <h3>🏆 Top Selling Products</h3>
      {#if loading}
        <p>Loading...</p>
      {:else if error}
        <p class="error">{error}</p>
      {:else if topProducts.length === 0}
        <p>No sales data for this period.</p>
      {:else}
        <table class="top-products-table">
          <thead>
            <tr>
              <th>Product</th>
              <th>Quantity Sold</th>
            </tr>
          </thead>
          <tbody>
            {#each topProducts as product}
              <tr>
                <td>{product.name}</td>
                <td>{product.quantity}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      {/if}
    </div>
    <!-- Profit Margins Card -->
    <div class="card">
      <h3>💰 Profit Margin by Product</h3>
      {#if marginsLoading}
        <p>Loading...</p>
      {:else if marginsError}
        <p class="error">{marginsError}</p>
      {:else if profitMargins.length === 0}
        <p>No sales data available.</p>
      {:else}
      <div class="table-wrapper">
          <table class="margins-table">
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
              <td>MWK {item.revenue.toFixed(2)}</td>
              <td>MWK {item.cost.toFixed(2)}</td>
              <td>MWK {item.profit.toFixed(2)}</td>
              <td class="margin-value">{item.margin_percent}%</td>
            </tr>
          {/each}
        </tbody>
        </table>
      </div>
      {/if}
    </div>
    <!-- Existing Insights / Fallback -->
    <div class="card">
      <h3>📈 Overview</h3>
      {#if insights}
        <p>{insights.message}</p>
        <ul>
          <li>Total Products: {insights.total_products}</li>
          <li>Total Sales: {insights.total_sales}</li>
        </ul>
      {:else if dashboard}
        <p>Dashboard fallback:</p>
        <ul>
          <li>Revenue: MWK {dashboard.total_revenue}</li>
          <li>Profit: MWK {dashboard.profit}</li>
        </ul>
      {/if}
    </div>
  </div>
</Layout>

<style>
  .insights-page {
    max-width: 800px;
    margin: 0 auto;
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
  }
  .period-selector {
    display: flex;
    align-items: center;
    gap: 1rem;
    background: var(--surface);
    padding: 1rem;
    border-radius: var(--radius);
    border: 1px solid var(--border);
  }
  select {
    padding: 0.5rem 1rem;
    border-radius: var(--radius);
    border: 1px solid var(--border);
    background: white;
  }
  .card {
    background: var(--surface);
    border-radius: var(--radius);
    padding: 1.5rem;
    border: 1px solid var(--border);
  }
  .top-products-table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 1rem;
  }
  .top-products-table th,
  .top-products-table td {
    text-align: left;
    padding: 0.75rem 0.5rem;
    border-bottom: 1px solid var(--border);
  }
  .error {
    color: var(--danger);
  }
  ul {
    padding-left: 1.5rem;
  }
  .margins-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 1rem;
}
.margins-table th,
.margins-table td {
  text-align: left;
  padding: 0.5rem;
  border-bottom: 1px solid var(--border);
}
.margin-value {
  font-weight: 600;
  color: var(--success);
}
.table-wrapper {
  overflow-x: auto;
}
</style>