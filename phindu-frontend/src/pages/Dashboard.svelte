<script>
  import { onMount } from 'svelte';
  import { RefreshCw, TrendingUp, Calendar } from 'lucide-svelte';
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
    session_id: null,
    stock_value_cost: 0,
    stock_value_selling: 0,
  };
  let loading = true;
  let error = null;
  let chartData = [];
  let currentSession = null;

  onMount(loadDashboard);

  async function loadDashboard() {
    loading = true;
    error = null;
    try {
      const sessionRes = await API.get('/sessions/current');
      if (sessionRes.data.id) {
        currentSession = sessionRes.data;
      }

      const sessionParam = currentSession ? `?session_id=${currentSession.id}` : '';
      const [dashRes, trendRes] = await Promise.all([
        API.get(`/dashboard/${sessionParam}`),
        API.get('/analytics/revenue-trend'),
      ]);

      data = Array.isArray(dashRes.data) ? dashRes.data[0] : dashRes.data;
      chartData = trendRes.data;
    } catch (err) {
      error = 'Failed to load dashboard data';
      console.error(err);
    } finally {
      loading = false;
    }
  }

  function formatDate(isoString) {
    const d = new Date(isoString);
    return d.toLocaleDateString(undefined, { weekday: 'short' });
  }

  // Guard against division by zero and produce a sane max for chart scaling
  $: maxRevenue = chartData.length > 0
    ? Math.max(...chartData.map((d) => d.revenue), 1)
    : 1;
</script>

<Layout title="Dashboard">
  {#if loading}
    <div class="state-box">
      <div class="spinner"></div>
      <p>Loading dashboard...</p>
    </div>
  {:else if error}
    <div class="state-box error">
      <p>{error}</p>
      <button class="btn btn-primary" on:click={loadDashboard} type="button">
        <RefreshCw size={16} strokeWidth={2} /> Retry
      </button>
    </div>
  {:else}
    <div class="dashboard">
      {#if currentSession}
        <div class="session-info">
          <Calendar size={16} strokeWidth={1.75} />
          <span>
            Showing data for session opened
            <strong>{new Date(currentSession.opened_at).toLocaleString()}</strong>
          </span>
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
        <MetricCard title="Stock (Cost)" value={data.stock_value_cost || 0} prefix="MWK" />
        <MetricCard title="Stock (Selling)" value={data.stock_value_selling || 0} prefix="MWK" />
      </div>

      <div class="chart-card">
        <div class="chart-header">
          <h3>
            <TrendingUp size={18} strokeWidth={2} />
            Revenue Trend (Last 6 Days)
          </h3>
        </div>
        {#if chartData.length === 0}
          <p class="no-data">No sales data yet.</p>
        {:else}
          <div class="chart-wrapper">
            <div class="chart">
              {#each chartData as item}
                <div class="bar-container">
                  <div
                    class="bar"
                    style="height: {Math.max(3, (item.revenue / maxRevenue) * 100)}%"
                  >
                    {#if item.revenue > 0}
                      <span class="bar-value">{item.revenue.toFixed(0)}</span>
                    {/if}
                  </div>
                  <span class="bar-label">{formatDate(item.date)}</span>
                </div>
              {/each}
            </div>
          </div>
        {/if}
      </div>
    </div>
  {/if}
</Layout>

<style>
  /* ============================================================
     CONTAINER — overflow protection from the very top
     ============================================================ */
  .dashboard {
    width: 100%;
    max-width: 100%;
    box-sizing: border-box;
    overflow-x: hidden; /* 🔧 Critical: no horizontal scroll ever */
  }

  /* ============================================================
     LOADING / ERROR STATE
     ============================================================ */
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
    to { transform: rotate(360deg); }
  }

  .btn {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.55rem 1rem;
    background: var(--primary, #0f6b3e);
    color: white;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    font-weight: 500;
  }

  /* ============================================================
     SESSION BANNER
     ============================================================ */
  .session-info {
    display: flex;
    align-items: flex-start;
    gap: 0.5rem;
    background: var(--primary-light, #d1fae5);
    padding: 0.65rem 0.9rem;
    border-radius: 10px;
    font-size: 0.85rem;
    color: var(--primary-dark, #065f46);
    margin-bottom: 1.25rem;
    border-left: 3px solid var(--primary, #0f6b3e);
    line-height: 1.4;
  }

  .session-info svg {
    flex-shrink: 0;
    margin-top: 2px;
  }

  .session-info strong {
    font-weight: 600;
    word-break: break-word;
  }

  /* ============================================================
     METRICS GRID — the heart of the mobile fix
     
     Desktop: as many columns as fit (auto-fit, 180px min)
     Tablet:  2 columns
     Mobile:  2 columns (small cards fit 2 across on 320px+)
     ============================================================ */
  .metrics-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 0.9rem;
    width: 100%;
    box-sizing: border-box;
  }

  /* ============================================================
     CHART CARD — bars always fit width, no scroll
     ============================================================ */
  .chart-card {
    background: var(--surface, #fff);
    border-radius: 12px;
    padding: 1.25rem;
    margin-top: 1.5rem;
    border: 1px solid var(--border, #e5e7eb);
    box-sizing: border-box;
    width: 100%;
    overflow: hidden; /* 🔧 prevent any inner overflow from pushing page */
  }

  .chart-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
  }

  .chart-header h3 {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin: 0;
    font-size: 1.05rem;
    font-weight: 600;
    color: var(--text, #111827);
  }

  .no-data {
    text-align: center;
    color: var(--text-light, #6b7280);
    padding: 2rem 1rem;
    font-size: 0.9rem;
  }

  /* 🔧 Key change: chart-wrapper does NOT scroll horizontally. Chart fits. */
  .chart-wrapper {
    width: 100%;
    overflow: hidden;
  }

  /* Bars use `flex: 1 1 0` so they SHRINK to fit any width.
     No `min-width` on containers → no overflow. */
  .chart {
    display: flex;
    align-items: flex-end;
    gap: 0.4rem;
    height: 200px;
    width: 100%;
    box-sizing: border-box;
  }

  .bar-container {
    flex: 1 1 0; /* 🔧 both grow and shrink — fits any width */
    min-width: 0; /* 🔧 allow shrinking below content size */
    display: flex;
    flex-direction: column;
    align-items: center;
    height: 100%;
    justify-content: flex-end;
  }

  .bar {
    width: 100%;
    max-width: 56px;
    background: var(--primary, #0f6b3e);
    border-radius: 6px 6px 0 0;
    min-height: 3px;
    transition: height 0.3s ease;
    display: flex;
    justify-content: center;
    align-items: flex-start;
    padding-top: 0.35rem;
    box-sizing: border-box;
    position: relative;
    overflow: hidden;
  }

  .bar-value {
    color: white;
    font-size: 0.65rem;
    font-weight: 600;
    white-space: nowrap;
    writing-mode: vertical-rl;
    text-orientation: upright;
    padding: 0.1rem;
    overflow: hidden;
  }

  .bar-label {
    margin-top: 0.5rem;
    font-size: 0.72rem;
    color: var(--text-light, #6b7280);
    text-align: center;
    white-space: nowrap;
    font-weight: 500;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 100%;
  }

  /* ============================================================
     TABLET (≤768px)
     ============================================================ */
  @media (max-width: 768px) {
    .metrics-grid {
      grid-template-columns: repeat(2, 1fr);
      gap: 0.65rem;
    }

    .chart-card {
      padding: 1rem;
    }

    .chart {
      height: 170px;
      gap: 0.35rem;
    }

    .bar-value {
      font-size: 0.6rem;
    }

    .bar-label {
      font-size: 0.68rem;
    }
  }

  /* ============================================================
     MOBILE (≤480px) — the actual fix
     Everything shrinks. Nothing overflows. Nothing scrolls sideways.
     ============================================================ */
  @media (max-width: 480px) {
    .dashboard {
      overflow-x: hidden;
    }

    .session-info {
      font-size: 0.78rem;
      padding: 0.55rem 0.75rem;
      margin-bottom: 1rem;
    }

    .metrics-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr)); /* 🔧 minmax(0, 1fr) fixes overflow */
      gap: 0.5rem;
    }

    .chart-card {
      padding: 0.75rem;
      margin-top: 1rem;
      border-radius: 10px;
    }

    .chart-header h3 {
      font-size: 0.9rem;
    }

    .chart {
      height: 140px;
      gap: 0.25rem;
    }

    /* 🔧 Hide bar values on mobile — the tall rotated numbers are the main
       source of visual clutter and take space. Users can still see the
       bar heights, and the trend is what matters on a phone. */
    .bar-value {
      display: none;
    }

    .bar-label {
      font-size: 0.65rem;
      margin-top: 0.35rem;
    }
  }

  /* ============================================================
     VERY SMALL (≤360px) — iPhone SE / Galaxy A-series
     ============================================================ */
  @media (max-width: 360px) {
    .metrics-grid {
      gap: 0.4rem;
    }

    .chart {
      height: 120px;
      gap: 0.2rem;
    }

    .bar-label {
      font-size: 0.6rem;
    }
  }
</style>