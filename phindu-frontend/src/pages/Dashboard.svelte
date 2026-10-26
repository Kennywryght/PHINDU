<script>
  import { onMount } from "svelte";
  import {
    RefreshCw,
    TrendingUp,
    Calendar,
    Activity,
    AlertTriangle,
    ArrowUpRight,
    ArrowDownRight,
    Minus,
    Target,
    Wallet,
    Coins,
    Package,
  } from "lucide-svelte";
  import Layout from "../components/Layout.svelte";
  import MetricCard from "../components/MetricCard.svelte";
  import API from "../api/api";

  let data = {
    total_revenue: 0,
    total_cost: 0,
    profit: 0,
    total_items_sold: 0,
    profit_margin: 0,
    avg_sale_value: 0,
    total_expenses: 0,
    session_id: null,
  };
  let loading = true;
  let error = null;
  let chartData = [];
  let currentSession = null;

  let today = null;
  let health = null;
  let focus = [];
  let deltas = null;
  let cashFlow = null;
  let topProducts = [];

  const TREND_OPTIONS = [7, 14, 30];
  let trendDays = 7;
  let trendLoading = false;

  onMount(loadDashboard);

  async function loadDashboard() {
    loading = true;
    error = null;
    try {
      const sessionRes = await API.get("/sessions/current");
      if (sessionRes.data.id) currentSession = sessionRes.data;

      const sessionParam = currentSession ? `?session_id=${currentSession.id}` : "";

      const [dashRes, trendRes, todayRes, healthRes, focusRes, deltaRes, cfRes, topRes] =
        await Promise.all([
          API.get(`/dashboard/${sessionParam}`),
          API.get(`/analytics/revenue-trend?days=${trendDays}`),
          API.get("/dashboard/today"),
          API.get("/dashboard/health-score"),
          API.get("/dashboard/focus"),
          API.get("/dashboard/metric-deltas"),
          API.get("/dashboard/cash-flow?days=7"),
          API.get("/dashboard/top-products-trend?days=7&limit=3"),
        ]);

      data = Array.isArray(dashRes.data) ? dashRes.data[0] : dashRes.data;
      chartData = trendRes.data;
      today = todayRes.data;
      health = healthRes.data;
      focus = focusRes.data?.items || [];
      deltas = deltaRes.data;
      cashFlow = cfRes.data;
      topProducts = topRes.data?.products || [];
    } catch (err) {
      error = "Failed to load dashboard data";
      console.error(err);
    } finally {
      loading = false;
    }
  }

  async function loadTrend() {
    trendLoading = true;
    try {
      const res = await API.get(`/analytics/revenue-trend?days=${trendDays}`);
      chartData = res.data;
    } catch (err) {
      console.error(err);
    } finally {
      trendLoading = false;
    }
  }

  function setTrendDays(n) {
    if (trendDays === n) return;
    trendDays = n;
    loadTrend();
  }

  function formatDate(isoString) {
    const d = new Date(isoString);
    if (trendDays <= 7) return d.toLocaleDateString(undefined, { weekday: "short" });
    return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
  }

  function formatMoney(n) {
    if (n == null) return "0";
    const num = Number(n);
    if (!isFinite(num)) return "0";
    return num.toLocaleString(undefined, { maximumFractionDigits: 0 });
  }

  function fmtDelta(d) {
    if (!d) return null;
    if (d.percent === null) return null;
    return d.percent;
  }

  $: maxRevenue = chartData.length > 0 ? Math.max(...chartData.map((d) => d.revenue), 1) : 1;
  $: healthTone = health?.tone || "warn";
  $: healthDelta = health?.delta ?? 0;
  $: healthIcon = healthDelta > 0 ? ArrowUpRight : healthDelta < 0 ? ArrowDownRight : Minus;
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

      {#if health}
        <div class="health-card tone-{healthTone}" role="status">
          <div class="health-icon-wrap">
            <Activity size={22} strokeWidth={2} />
          </div>
          <div class="health-content">
            <div class="health-title-row">
              <span class="health-title">Business Health</span>
              <span class="health-score">{health.score}<span class="health-max">/100</span></span>
            </div>
            <div class="health-sub">
              <span class="health-delta">
                <svelte:component this={healthIcon} size={14} strokeWidth={2.5} />
                {#if healthDelta > 0}+{healthDelta}{:else if healthDelta < 0}{healthDelta}{:else}0{/if}
                vs last week
              </span>
              <span class="health-sep">·</span>
              <span class="health-label">{health.label}</span>
            </div>
            <p class="health-message">{health.message}</p>
          </div>
        </div>
      {/if}

      {#if today}
        <div class="today-strip">
          <div class="today-cell">
            <span class="today-label">Today Revenue</span>
            <span class="today-value">MWK {formatMoney(today.revenue)}</span>
          </div>
          <div class="today-cell">
            <span class="today-label">Sales</span>
            <span class="today-value">{today.sales_count}</span>
          </div>
          <div class="today-cell">
            <span class="today-label">Profit</span>
            <span class="today-value">MWK {formatMoney(today.profit)}</span>
          </div>
          <div class="today-cell">
            <span class="today-label">Low Stock</span>
            <span class="today-value" class:warning={today.low_stock_count > 0}>
              {#if today.low_stock_count > 0}
                <AlertTriangle size={14} strokeWidth={2} /> {today.low_stock_count}
              {:else}
                0
              {/if}
            </span>
          </div>
        </div>
      {/if}

      {#if focus.length > 0}
        <div class="focus-card">
          <h3 class="focus-header">
            <Target size={18} strokeWidth={2} />
            Today's Focus
          </h3>
          <ul class="focus-list">
            {#each focus as item, i}
              <li class="focus-item sev-{item.severity}">
                <span class="focus-number">{i + 1}</span>
                <div class="focus-body">
                  <a class="focus-title" href={item.link}>{item.title}</a>
                  <span class="focus-detail">{item.detail}</span>
                  <span class="focus-hint">→ {item.hint}</span>
                </div>
              </li>
            {/each}
          </ul>
        </div>
      {/if}

      <!-- ── MONEY section ── -->
      <h3 class="section-title">
        <Coins size={16} strokeWidth={2} /> Money
      </h3>
      <div class="metrics-grid">
        <MetricCard
          title="Total Revenue"
          value={data.total_revenue}
          prefix="MWK"
          delta={fmtDelta(deltas?.revenue)}
        />
        <MetricCard title="Total Cost" value={data.total_cost} prefix="MWK" />
        <MetricCard
          title="Expenses"
          value={data.total_expenses || 0}
          prefix="MWK"
          delta={fmtDelta(deltas?.expenses)}
        />
        <MetricCard
          title="Profit"
          value={data.profit}
          prefix="MWK"
          highlight
          delta={fmtDelta(deltas?.profit)}
        />
      </div>

      <!-- ── VOLUME section ── -->
      <h3 class="section-title">
        <Package size={16} strokeWidth={2} /> Volume
      </h3>
      <div class="metrics-grid">
        <MetricCard
          title="Items Sold"
          value={data.total_items_sold}
          delta={fmtDelta(deltas?.items_sold)}
        />
        <MetricCard title="Profit Margin" value={data.profit_margin} suffix="%" />
        <MetricCard title="Avg Sale Value" value={data.avg_sale_value} prefix="MWK" />
      </div>

      <!-- ── Cash Flow ── -->
      {#if cashFlow}
        <div class="cashflow-card">
          <h3 class="cf-header">
            <Wallet size={18} strokeWidth={2} />
            Cash Flow (Last {cashFlow.window_days} Days)
          </h3>
          <div class="cf-grid">
            <div class="cf-cell in">
              <span class="cf-label">Cash In</span>
              <span class="cf-value">+MWK {formatMoney(cashFlow.cash_in)}</span>
            </div>
            <div class="cf-cell out">
              <span class="cf-label">Cash Out</span>
              <span class="cf-value">−MWK {formatMoney(cashFlow.cash_out)}</span>
            </div>
            <div class="cf-cell net" class:negative={cashFlow.net < 0}>
              <span class="cf-label">Net</span>
              <span class="cf-value">
                {cashFlow.net >= 0 ? "+" : "−"}MWK {formatMoney(Math.abs(cashFlow.net))}
              </span>
            </div>
            <div class="cf-cell drawer">
              <span class="cf-label">In Drawer</span>
              <span class="cf-value">
                {#if cashFlow.drawer === null}
                  —
                {:else}
                  MWK {formatMoney(cashFlow.drawer)}
                {/if}
              </span>
            </div>
          </div>
        </div>
      {/if}

      <!-- ── Revenue Trend ── -->
      <div class="chart-card">
        <div class="chart-header">
          <h3>
            <TrendingUp size={18} strokeWidth={2} />
            Revenue Trend (Last {trendDays} Days)
          </h3>
          <div class="period-tabs" role="tablist" aria-label="Revenue trend period">
            {#each TREND_OPTIONS as n}
              <button
                type="button"
                class="period-tab"
                class:active={trendDays === n}
                on:click={() => setTrendDays(n)}
                aria-pressed={trendDays === n}
                disabled={trendLoading}
              >
                {n}d
              </button>
            {/each}
          </div>
        </div>
        {#if trendLoading}
          <p class="no-data">Loading…</p>
        {:else if chartData.length === 0}
          <p class="no-data">No sales data yet.</p>
        {:else}
          <div class="chart-wrapper" class:compact={trendDays > 7}>
            <div class="chart">
              {#each chartData as item}
                <div class="bar-container">
                  <div
                    class="bar"
                    style="height: {Math.max(3, (item.revenue / maxRevenue) * 100)}%"
                  >
                    {#if item.revenue > 0 && trendDays <= 14}
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

      <!-- ── Top Products with sparklines ── -->
      {#if topProducts.length > 0}
        <div class="topprod-card">
          <h3 class="tp-header">
            <TrendingUp size={18} strokeWidth={2} />
            Top Products (Last 7 Days)
          </h3>
          <ul class="tp-list">
            {#each topProducts as p}
              {@const maxSpar = Math.max(...p.sparkline, 1)}
              <li class="tp-row">
                <div class="tp-main">
                  <span class="tp-name">{p.name}</span>
                  <span class="tp-meta">
                    {Math.round(p.quantity)} sold · MWK {formatMoney(p.revenue)}
                  </span>
                </div>
                <div class="tp-spark" aria-hidden="true">
                  {#each p.sparkline as v}
                    <span
                      class="spark-bar"
                      style="height: {Math.max(8, (v / maxSpar) * 100)}%"
                    ></span>
                  {/each}
                </div>
              </li>
            {/each}
          </ul>
        </div>
      {/if}
    </div>
  {/if}
</Layout>

<style>
  .dashboard {
    width: 100%;
    max-width: 100%;
    box-sizing: border-box;
    overflow-x: hidden;
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
  .session-info strong {
    font-weight: 600;
    word-break: break-word;
  }

  /* Health card */
  .health-card {
    display: flex;
    align-items: flex-start;
    gap: 0.9rem;
    padding: 1rem 1.1rem;
    border-radius: 12px;
    border: 1px solid var(--border, #e5e7eb);
    background: var(--surface, #fff);
    margin-bottom: 1rem;
    box-sizing: border-box;
    width: 100%;
  }
  .health-card.tone-good {
    border-color: #86efac;
    background: linear-gradient(135deg, #f0fdf4 0%, #ffffff 100%);
  }
  .health-card.tone-warn {
    border-color: #fcd34d;
    background: linear-gradient(135deg, #fffbeb 0%, #ffffff 100%);
  }
  .health-card.tone-bad {
    border-color: #fca5a5;
    background: linear-gradient(135deg, #fef2f2 0%, #ffffff 100%);
  }
  .health-icon-wrap {
    flex-shrink: 0;
    width: 40px;
    height: 40px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #f3f4f6;
    color: #374151;
  }
  .tone-good .health-icon-wrap {
    background: #dcfce7;
    color: #15803d;
  }
  .tone-warn .health-icon-wrap {
    background: #fef3c7;
    color: #b45309;
  }
  .tone-bad .health-icon-wrap {
    background: #fee2e2;
    color: #b91c1c;
  }
  .health-content {
    flex: 1;
    min-width: 0;
  }
  .health-title-row {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 0.5rem;
  }
  .health-title {
    font-size: 0.82rem;
    font-weight: 600;
    color: var(--text-light, #6b7280);
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }
  .health-score {
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--text, #111827);
    line-height: 1;
  }
  .health-max {
    font-size: 0.85rem;
    font-weight: 500;
    color: var(--text-light, #6b7280);
    margin-left: 1px;
  }
  .health-sub {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.4rem;
    margin-top: 0.3rem;
    font-size: 0.8rem;
    color: var(--text-light, #6b7280);
  }
  .health-delta {
    display: inline-flex;
    align-items: center;
    gap: 0.15rem;
    font-weight: 600;
  }
  .tone-good .health-delta {
    color: #15803d;
  }
  .tone-warn .health-delta {
    color: #b45309;
  }
  .tone-bad .health-delta {
    color: #b91c1c;
  }
  .health-sep {
    color: #d1d5db;
  }
  .health-label {
    font-weight: 600;
    color: var(--text, #111827);
  }
  .health-message {
    margin: 0.4rem 0 0;
    font-size: 0.82rem;
    color: var(--text, #111827);
    line-height: 1.35;
  }

  /* Today strip */
  .today-strip {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 0.5rem;
    margin-bottom: 1rem;
    padding: 0.75rem;
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 12px;
    box-sizing: border-box;
    width: 100%;
  }
  .today-cell {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
    min-width: 0;
  }
  .today-label {
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    color: var(--text-light, #6b7280);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .today-value {
    font-size: 0.95rem;
    font-weight: 700;
    color: var(--text, #111827);
    display: inline-flex;
    align-items: center;
    gap: 0.2rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .today-value.warning {
    color: #b45309;
  }

  /* Focus */
  .focus-card {
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 12px;
    padding: 1rem 1.1rem;
    margin-bottom: 1.25rem;
    box-sizing: border-box;
    width: 100%;
  }
  .focus-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin: 0 0 0.75rem;
    font-size: 1rem;
    font-weight: 600;
    color: var(--text, #111827);
  }
  .focus-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 0.55rem;
  }
  .focus-item {
    display: flex;
    gap: 0.75rem;
    padding: 0.6rem 0.7rem;
    border-radius: 9px;
    background: #f9fafb;
    border-left: 3px solid #9ca3af;
    box-sizing: border-box;
  }
  .focus-item.sev-high {
    border-left-color: #dc2626;
    background: #fef2f2;
  }
  .focus-item.sev-medium {
    border-left-color: #d97706;
    background: #fffbeb;
  }
  .focus-item.sev-low {
    border-left-color: #059669;
    background: #f0fdf4;
  }
  .focus-number {
    flex-shrink: 0;
    width: 22px;
    height: 22px;
    border-radius: 50%;
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 0.75rem;
    font-weight: 700;
    color: var(--text, #111827);
  }
  .focus-body {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
  }
  .focus-title {
    font-size: 0.9rem;
    font-weight: 600;
    color: var(--text, #111827);
    text-decoration: none;
    line-height: 1.3;
    word-break: break-word;
  }
  .focus-title:hover {
    text-decoration: underline;
  }
  .focus-detail {
    font-size: 0.8rem;
    color: var(--text-light, #6b7280);
    line-height: 1.35;
  }
  .focus-hint {
    font-size: 0.78rem;
    font-weight: 600;
    color: var(--primary, #0f6b3e);
  }

  /* Section heading */
  .section-title {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    margin: 1.1rem 0 0.6rem;
    font-size: 0.78rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-light, #6b7280);
  }
  .section-title:first-of-type {
    margin-top: 0;
  }

  /* Metrics */
  .metrics-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 0.9rem;
    width: 100%;
    box-sizing: border-box;
  }

  /* Cash flow card */
  .cashflow-card {
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 12px;
    padding: 1rem 1.1rem;
    margin-top: 1.25rem;
    box-sizing: border-box;
    width: 100%;
  }
  .cf-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin: 0 0 0.75rem;
    font-size: 1rem;
    font-weight: 600;
    color: var(--text, #111827);
  }
  .cf-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 0.5rem;
  }
  .cf-cell {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
    padding: 0.55rem 0.65rem;
    border-radius: 8px;
    background: #f9fafb;
    min-width: 0;
  }
  .cf-cell.in {
    background: #f0fdf4;
  }
  .cf-cell.out {
    background: #fef2f2;
  }
  .cf-cell.net {
    background: #eff6ff;
  }
  .cf-cell.net.negative {
    background: #fef2f2;
  }
  .cf-cell.drawer {
    background: #faf5ff;
  }
  .cf-label {
    font-size: 0.68rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    color: var(--text-light, #6b7280);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .cf-value {
    font-size: 0.9rem;
    font-weight: 700;
    color: var(--text, #111827);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  /* Chart */
  .chart-card {
    background: var(--surface, #fff);
    border-radius: 12px;
    padding: 1.25rem;
    margin-top: 1.5rem;
    border: 1px solid var(--border, #e5e7eb);
    box-sizing: border-box;
    width: 100%;
    overflow: hidden;
  }
  .chart-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
    gap: 0.75rem;
    flex-wrap: wrap;
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
  .period-tabs {
    display: inline-flex;
    gap: 0.25rem;
    background: var(--background, #f3f4f6);
    padding: 0.2rem;
    border-radius: 10px;
    border: 1px solid var(--border, #e5e7eb);
  }
  .period-tab {
    border: none;
    background: transparent;
    padding: 0.35rem 0.7rem;
    border-radius: 7px;
    font-size: 0.8rem;
    font-weight: 600;
    color: var(--text-light, #6b7280);
    cursor: pointer;
    transition: all 0.15s;
    line-height: 1;
  }
  .period-tab:hover:not(:disabled) {
    color: var(--text, #111827);
  }
  .period-tab.active {
    background: var(--surface, #ffffff);
    color: var(--primary, #0f6b3e);
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.08);
  }
  .period-tab:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
  .no-data {
    text-align: center;
    color: var(--text-light, #6b7280);
    padding: 2rem 1rem;
    font-size: 0.9rem;
  }
  .chart-wrapper {
    width: 100%;
    overflow: hidden;
  }
  .chart-wrapper.compact .bar-label {
    font-size: 0.6rem;
  }
  .chart {
    display: flex;
    align-items: flex-end;
    gap: 0.4rem;
    height: 200px;
    width: 100%;
    box-sizing: border-box;
  }
  .bar-container {
    flex: 1 1 0;
    min-width: 0;
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

  /* Top products */
  .topprod-card {
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 12px;
    padding: 1rem 1.1rem;
    margin-top: 1.25rem;
    box-sizing: border-box;
    width: 100%;
  }
  .tp-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin: 0 0 0.75rem;
    font-size: 1rem;
    font-weight: 600;
    color: var(--text, #111827);
  }
  .tp-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }
  .tp-row {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.5rem 0.6rem;
    border-radius: 8px;
    background: #f9fafb;
    min-width: 0;
  }
  .tp-main {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
  }
  .tp-name {
    font-weight: 600;
    font-size: 0.88rem;
    color: var(--text, #111827);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .tp-meta {
    font-size: 0.75rem;
    color: var(--text-light, #6b7280);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .tp-spark {
    display: flex;
    align-items: flex-end;
    gap: 2px;
    height: 28px;
    width: 78px;
    flex-shrink: 0;
  }
  .spark-bar {
    flex: 1 1 0;
    min-width: 0;
    background: var(--primary, #0f6b3e);
    border-radius: 2px 2px 0 0;
    opacity: 0.8;
  }

  /* ============ Responsive ============ */
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
    .today-strip {
      grid-template-columns: repeat(2, 1fr);
      row-gap: 0.6rem;
    }
    .cf-grid {
      grid-template-columns: repeat(2, 1fr);
    }
  }

  @media (max-width: 480px) {
    .dashboard {
      overflow-x: hidden;
    }
    .session-info {
      font-size: 0.78rem;
      padding: 0.55rem 0.75rem;
      margin-bottom: 1rem;
    }
    .health-card {
      padding: 0.8rem 0.9rem;
      gap: 0.7rem;
    }
    .health-icon-wrap {
      width: 34px;
      height: 34px;
    }
    .health-score {
      font-size: 1.3rem;
    }
    .health-message {
      font-size: 0.78rem;
    }
    .today-strip {
      padding: 0.6rem 0.7rem;
      gap: 0.4rem 0.5rem;
    }
    .today-value {
      font-size: 0.85rem;
    }
    .today-label {
      font-size: 0.65rem;
    }
    .focus-card {
      padding: 0.85rem 0.9rem;
    }
    .focus-title {
      font-size: 0.85rem;
    }
    .focus-detail,
    .focus-hint {
      font-size: 0.75rem;
    }
    .metrics-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 0.5rem;
    }
    .cashflow-card {
      padding: 0.85rem 0.9rem;
    }
    .cf-grid {
      gap: 0.4rem;
    }
    .cf-value {
      font-size: 0.82rem;
    }
    .chart-card {
      padding: 0.75rem;
      margin-top: 1rem;
      border-radius: 10px;
    }
    .chart-header {
      margin-bottom: 0.75rem;
    }
    .chart-header h3 {
      font-size: 0.9rem;
    }
    .period-tab {
      padding: 0.3rem 0.55rem;
      font-size: 0.72rem;
    }
    .chart {
      height: 140px;
      gap: 0.25rem;
    }
    .bar-value {
      display: none;
    }
    .bar-label {
      font-size: 0.65rem;
      margin-top: 0.35rem;
    }
    .chart-wrapper.compact .bar-label {
      font-size: 0.55rem;
    }
    .topprod-card {
      padding: 0.85rem 0.9rem;
    }
    .tp-spark {
      width: 60px;
      height: 24px;
    }
  }

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