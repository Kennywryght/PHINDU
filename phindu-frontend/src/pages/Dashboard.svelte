<script>
  import { onMount } from 'svelte';
  import Layout from '../components/Layout.svelte';
  import MetricCard from '../components/MetricCard.svelte';
  import API from '../api/api';

  let data = {
    total_revenue: 0,
    total_cost: 0,
    profit: 0,
    total_items_sold: 0,
    profit_margin: 0,
    avg_sale_value: 0
  };
  let loading = true;
  let error = null;

onMount(async () => {
  console.log('Dashboard mounted, calling API...');
  try {
    const res = await API.get('/dashboard/');
    console.log('Dashboard API response:', res.data);
    data = Array.isArray(res.data) ? res.data[0] : res.data;
  } catch (err) {
    console.error('Dashboard API failed:', err);
    error = 'Failed to load dashboard data';
  } finally {
    loading = false;
  }
});

  // For chart (top products could be used, but we'll show revenue trend placeholder)
  const chartData = [65, 45, 75, 55, 80, 70];
</script>

<Layout title="Dashboard">
  {#if loading}
    <p>Loading...</p>
  {:else if error}
    <p class="error">{error}</p>
  {:else}
    <div class="dashboard">
      <div class="metrics-grid">
        <MetricCard title="Total Revenue" value={data.total_revenue} prefix="MWK" />
        <MetricCard title="Total Cost" value={data.total_cost} prefix="MWK" />
        <MetricCard title="Profit" value={data.profit} prefix="MWK" highlight />
        <MetricCard title="Items Sold" value={data.total_items_sold} />
        <MetricCard title="Profit Margin" value={data.profit_margin} suffix="%" />
        <MetricCard title="Avg Sale Value" value={data.avg_sale_value} prefix="MWK" />
      </div>

      <div class="card chart-card">
        <h3>Revenue Trend (Last 6 Days)</h3>
        <div class="chart">
          {#each chartData as value, i}
            <div class="bar-container">
              <div class="bar" style="height: {value}%">
                <span class="bar-value">{value}</span>
              </div>
              <span class="bar-label">Day {i+1}</span>
            </div>
          {/each}
        </div>
      </div>
    </div>
  {/if}
</Layout>

<style>
  .dashboard {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
  }

  .metrics-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 1rem;
  }

  .chart-card {
    padding: 1.5rem;
  }

  .chart {
    display: flex;
    align-items: flex-end;
    gap: 1rem;
    height: 200px;
    margin-top: 1rem;
  }

  .bar-container {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    height: 100%;
  }

  .bar {
    width: 100%;
    max-width: 50px;
    background: var(--primary);
    border-radius: 4px 4px 0 0;
    min-height: 4px;
    transition: height 0.3s;
    display: flex;
    justify-content: center;
    align-items: flex-start;
    padding-top: 4px;
  }

  .bar-value {
    color: white;
    font-size: 0.8rem;
  }

  .bar-label {
    margin-top: 0.5rem;
    font-size: 0.8rem;
    color: var(--text-light);
  }

  @media (max-width: 480px) {
    .metrics-grid {
      grid-template-columns: 1fr 1fr;
    }
  }
</style>