<script>
  import { onMount } from 'svelte';
  import Layout from '../components/Layout.svelte';
  import API from '../api/api';

  let insights = null;
  let dashboard = null;
  let loading = true;
  let error = null;

  onMount(async () => {
    try {
      // Primary endpoint may fail
      const res = await API.get('/analytics/insights');
      insights = res.data;
    } catch (err) {
      console.warn('Insights endpoint returned error, falling back to dashboard');
      try {
        const dashRes = await API.get('/dashboard/');
        dashboard = dashRes.data;
      } catch (fallbackErr) {
        error = 'Unable to load insights or dashboard data.';
      }
    } finally {
      loading = false;
    }
  });
</script>

<Layout title="Insights">
  <div class="insights-container">
    {#if loading}
      <div class="loading-state">Loading insights...</div>
    {:else if error}
      <div class="error-state">{error}</div>
    {:else if insights}
      <div class="card">
        <h3>📈 AI‑Generated Insights</h3>
        <div class="insights-content">
          {#if typeof insights === 'string'}
            <p>{insights}</p>
          {:else}
            <!-- Render structured insights if object -->
            {#each Object.entries(insights) as [key, value]}
              <div class="insight-item">
                <span class="key">{key.replace(/_/g, ' ')}</span>
                <span class="value">{value}</span>
              </div>
            {/each}
          {/if}
        </div>
      </div>
    {:else if dashboard}
      <div class="card fallback">
        <h3>📊 Dashboard Overview (Fallback)</h3>
        <p class="note">Detailed insights unavailable – showing basic metrics instead.</p>
        <div class="metrics">
          <div class="metric">
            <span>Total Revenue</span>
            <strong>MWK {dashboard.total_revenue.toLocaleString()}</strong>
          </div>
          <div class="metric">
            <span>Profit</span>
            <strong>MWK {dashboard.profit.toLocaleString()}</strong>
          </div>
          <div class="metric">
            <span>Profit Margin</span>
            <strong>{dashboard.profit_margin}%</strong>
          </div>
          <div class="metric">
            <span>Items Sold</span>
            <strong>{dashboard.total_items_sold}</strong>
          </div>
          <div class="metric">
            <span>Avg Sale Value</span>
            <strong>MWK {dashboard.avg_sale_value.toFixed(2)}</strong>
          </div>
        </div>
      </div>
    {/if}
  </div>
</Layout>

<style>
  .insights-container {
    max-width: 900px;
    margin: 0 auto;
  }

  .loading-state,
  .error-state {
    text-align: center;
    padding: 3rem;
    color: var(--text-light);
  }

  .error-state {
    color: var(--danger);
  }

  .card {
    padding: 2rem;
  }

  h3 {
    margin-bottom: 1.5rem;
    color: var(--text);
  }

  .insights-content p {
    white-space: pre-wrap;
    line-height: 1.6;
  }

  .insight-item {
    display: flex;
    justify-content: space-between;
    padding: 0.75rem 0;
    border-bottom: 1px solid var(--border);
  }

  .insight-item:last-child {
    border-bottom: none;
  }

  .key {
    text-transform: capitalize;
    color: var(--text-light);
  }

  .value {
    font-weight: 600;
    color: var(--text);
  }

  .fallback .note {
    background: #fff3cd;
    color: #856404;
    padding: 0.75rem 1rem;
    border-radius: var(--radius);
    margin-bottom: 1.5rem;
  }

  .metrics {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1.5rem;
  }

  .metric {
    display: flex;
    flex-direction: column;
  }

  .metric span {
    font-size: 0.9rem;
    color: var(--text-light);
    margin-bottom: 0.25rem;
  }

  .metric strong {
    font-size: 1.5rem;
    color: var(--text);
  }
</style>