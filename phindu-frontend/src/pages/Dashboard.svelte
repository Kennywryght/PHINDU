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
    avg_sale_value: 0,
    total_expenses: 0,
    session_id: null
  };
  let loading = true;
  let error = null;
  let chartData = [];
  let currentSession = null;

  onMount(async () => {
    try {
      // 1. Get current session (if any)
      const sessionRes = await API.get('/sessions/current');
      if (sessionRes.data.id) {
        currentSession = sessionRes.data;
      }

      // 2. Fetch dashboard data (pass session_id if available)
      const sessionParam = currentSession ? `?session_id=${currentSession.id}` : '';
      const [dashRes, trendRes] = await Promise.all([
        API.get(`/dashboard/${sessionParam}`),
        API.get('/analytics/revenue-trend')
      ]);

      data = Array.isArray(dashRes.data) ? dashRes.data[0] : dashRes.data;
      chartData = trendRes.data;
    } catch (err) {
      error = 'Failed to load dashboard data';
      console.error(err);
    } finally {
      loading = false;
    }
  });

  function formatDate(isoString) {
    const d = new Date(isoString);
    return d.toLocaleDateString(undefined, { weekday: 'short' });
  }
</script>

<Layout title="Dashboard">
  {#if loading}
    <p>Loading...</p>
  {:else if error}
    <p class="error">{error}</p>
  {:else}
    <div class="dashboard">
      {#if currentSession}
        <div class="session-info">
          📅 Showing data for session opened {new Date(currentSession.opened_at).toLocaleString()}
        </div>
      {/if}

      <div class="metrics-grid">
        <MetricCard title="Total Revenue" value={data.total_revenue} prefix="MWK" />
        <MetricCard title="Total Cost" value={data.total_cost} prefix="MWK" />
        <MetricCard title="Expenses" value={data.total_expenses || 0} prefix="MWK" />
        <MetricCard title="Profit" value={data.profit} prefix="MWK" highlight />
        <MetricCard title="Items Sold" value={data.total_items_sold} />
        <MetricCard title="Profit Margin" value={data.profit_margin} suffix="%" />
        <MetricCard title="Avg Sale Value" value={data.avg_sale_value} prefix="MWK" />
      </div>

      <div class="card chart-card">
        <h3>Revenue Trend (Last 6 Days)</h3>
        {#if chartData.length === 0}
          <p>No sales data yet.</p>
        {:else}
          <div class="chart">
            {#each chartData as item}
              <div class="bar-container">
                <div class="bar" style="height: {Math.max(5, (item.revenue / 1000) * 100)}%">
                  <span class="bar-value">{item.revenue.toFixed(0)}</span>
                </div>
                <span class="bar-label">{formatDate(item.date)}</span>
              </div>
            {/each}
          </div>
        {/if}
      </div>
    </div>
  {/if}
</Layout>

<style>
  .dashboard {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    width: 100%;
  }

  .session-info {
    background: var(--background);
    padding: 0.5rem 1rem;
    border-radius: var(--radius);
    font-size: 0.9rem;
    color: var(--text-light);
  }

  .metrics-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
    gap: 0.75rem;
  }

  .chart-card {
    padding: 1rem;
  }

  .chart {
    display: flex;
    align-items: flex-end;
    gap: 0.5rem;
    height: 180px;
    margin-top: 1rem;
    overflow-x: auto;
    padding-bottom: 0.5rem;
  }

  .bar-container {
    flex: 1;
    min-width: 45px;
    display: flex;
    flex-direction: column;
    align-items: center;
    height: 100%;
  }

  .bar {
    width: 100%;
    max-width: 40px;
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
    font-size: 0.7rem;
    writing-mode: vertical-rl;
    text-orientation: upright;
  }

  .bar-label {
    margin-top: 0.5rem;
    font-size: 0.75rem;
    color: var(--text-light);
    text-align: center;
  }

  /* Mobile optimizations */
  @media (max-width: 600px) {
    .metrics-grid {
      grid-template-columns: repeat(2, 1fr);
      gap: 0.5rem;
    }
    .chart {
      height: 150px;
      gap: 0.25rem;
    }
    .bar-container {
      min-width: 35px;
    }
    .bar-label {
      font-size: 0.65rem;
    }
  }

  @media (max-width: 380px) {
    .metrics-grid {
      grid-template-columns: 1fr 1fr;
    }
  }
</style>