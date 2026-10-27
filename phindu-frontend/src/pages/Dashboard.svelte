<script>
  import { onMount, onDestroy } from "svelte";
  import {
    RefreshCw,
    TrendingUp,
    Calendar,
    Activity,
    AlertTriangle,
    AlertCircle,
    CheckCircle2,
    Info,
    ArrowUpRight,
    ArrowDownRight,
    Minus,
    Target,
    Wallet,
    Coins,
    Package,
    Users,
    Store,
  } from "lucide-svelte";
  import Layout from "../components/Layout.svelte";
  import MetricCard from "../components/MetricCard.svelte";
  import InfoCards from "../components/InfoCards.svelte";
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
  let sessionSummary = null;

  let today = null;
  let health = null;
  let focus = [];
  let deltas = null;
  let topProducts = [];

  let alerts = [];
  let topCustomers = [];
  let debtAgeing = null;
  let slowMovers = [];

  let heatmap = null;
  const HEATMAP_OPTIONS = [14, 30, 90];
  let heatmapDays = 30;
  let heatmapLoading = false;

  const TREND_OPTIONS = [7, 14, 30];
  let trendDays = 7;
  let trendLoading = false;

  // Sessions & Sales trend (replaces old cash-flow card)
  let sessionsTrend = [];
  let sessionsTrendTotals = null;
  let sessionsLoading = false;
  let sessionsDays = 7;
  const SESSION_OPTIONS = [7, 14, 30];

  // New informational cards
  let willRunOut = [];
  let profitByCategory = [];
  let customerHealth = null;
  let inventoryValue = null;
  let expenseBreakdown = null;
  let goodNews = [];

  let pollId = null;

  onMount(() => {
    loadDashboard();
    const onVis = () => {
      if (document.visibilityState === "visible") loadDashboard();
    };
    document.addEventListener("visibilitychange", onVis);
    return () => document.removeEventListener("visibilitychange", onVis);
  });

  onDestroy(() => {
    if (pollId) clearInterval(pollId);
  });

  $: {
    if (pollId) { clearInterval(pollId); pollId = null; }
    if (currentSession) {
      pollId = setInterval(() => {
        if (document.visibilityState === "visible") loadDashboard();
      }, 60000);
    }
  }

  async function loadDashboard() {
    loading = loading && !data.session_id;
    error = null;
    try {
      const [
        sessionRes,
        trendRes,
        todayRes,
        healthRes,
        focusRes,
        deltaRes,
        sessRes,
        topRes,
        alertsRes,
        topCustRes,
        debtRes,
        slowRes,
        heatmapRes,
        runOutRes,
        catRes,
        custHealthRes,
        invRes,
        expRes,
        goodNewsRes,
      ] = await Promise.all([
        API.get("/sessions/current").catch(() => ({ data: {} })),
        API.get(`/analytics/revenue-trend?days=${trendDays}`),
        API.get("/dashboard/today"),
        API.get("/dashboard/health-score"),
        API.get("/dashboard/focus"),
        API.get("/dashboard/metric-deltas"),
        API.get(`/dashboard/sessions-trend?days=${sessionsDays}`).catch(() => ({
          data: { items: [], totals: null },
        })),
        API.get("/dashboard/top-products-trend?days=7&limit=3"),
        API.get("/dashboard/alerts").catch(() => ({ data: { alerts: [] } })),
        API.get("/dashboard/top-customers?days=7&limit=5").catch(() => ({ data: { customers: [] } })),
        API.get("/dashboard/debt-ageing").catch(() => ({ data: null })),
        API.get("/dashboard/slow-movers?days=30&limit=5").catch(() => ({ data: { products: [] } })),
        API.get(`/dashboard/heatmap?days=${heatmapDays}`).catch(() => ({ data: null })),
        API.get("/dashboard/will-run-out?days=14&limit=5").catch(() => ({ data: { products: [] } })),
        API.get("/dashboard/profit-by-category?days=30").catch(() => ({ data: { categories: [] } })),
        API.get("/dashboard/customer-health?days=7").catch(() => ({ data: null })),
        API.get("/dashboard/inventory-value").catch(() => ({ data: null })),
        API.get("/dashboard/expense-breakdown?days=30").catch(() => ({ data: null })),
        API.get("/dashboard/good-news").catch(() => ({ data: { items: [] } })),
      ]);

      currentSession = sessionRes.data?.id ? sessionRes.data : null;

      const [dashRes, summaryRes] = await Promise.all([
        API.get(
          currentSession
            ? `/dashboard/?session_id=${currentSession.id}`
            : `/dashboard/`
        ),
        currentSession
          ? API.get(`/sessions/${currentSession.id}/summary`).catch(() => ({ data: null }))
          : Promise.resolve({ data: null }),
      ]);

      data = Array.isArray(dashRes.data) ? dashRes.data[0] : dashRes.data;
      chartData = trendRes.data;
      today = todayRes.data;
      health = healthRes.data;
      focus = focusRes.data?.items || [];
      deltas = deltaRes.data;
      topProducts = topRes.data?.products || [];
      sessionSummary = summaryRes.data;

      sessionsTrend = sessRes.data?.items || [];
      sessionsTrendTotals = sessRes.data?.totals || null;

      alerts = alertsRes.data?.alerts || [];
      topCustomers = topCustRes.data?.customers || [];
      debtAgeing = debtRes.data;
      slowMovers = slowRes.data?.products || [];
      heatmap = heatmapRes.data;

      willRunOut = runOutRes.data?.products || [];
      profitByCategory = catRes.data?.categories || [];
      customerHealth = custHealthRes.data;
      inventoryValue = invRes.data;
      expenseBreakdown = expRes.data;
      goodNews = goodNewsRes.data?.items || [];
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

  async function fetchHeatmap() {
    heatmapLoading = true;
    try {
      const res = await API.get(`/dashboard/heatmap?days=${heatmapDays}`);
      heatmap = res.data;
    } catch (e) {
      console.error(e);
    } finally {
      heatmapLoading = false;
    }
  }

  function setHeatmapDays(n) {
    if (heatmapDays === n) return;
    heatmapDays = n;
    fetchHeatmap();
  }

  async function loadSessionsTrend() {
    sessionsLoading = true;
    try {
      const res = await API.get(`/dashboard/sessions-trend?days=${sessionsDays}`);
      sessionsTrend = res.data?.items || [];
      sessionsTrendTotals = res.data?.totals || null;
    } catch (e) {
      console.error(e);
    } finally {
      sessionsLoading = false;
    }
  }

  function setSessionsDays(n) {
    if (sessionsDays === n) return;
    sessionsDays = n;
    loadSessionsTrend();
  }

  function heatmapIntensity(value, max) {
    if (!max || !value) return 0;
    return Math.min(1, Math.sqrt(value / max));
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

  $: heatmapMax = heatmap?.max ?? 0;
  $: heatmapTotal = heatmap
    ? heatmap.grid.flat().reduce((s, v) => s + v, 0)
    : 0;

  // ── Sessions chart derived values ──
  $: maxDayValue = sessionsTrend.length
    ? Math.max(...sessionsTrend.map((d) => Math.max(d.sessions, d.sales)), 1)
    : 1;

  $: activeDays = sessionsTrend.filter((d) => d.sessions > 0).length;

  $: avgSessionsPerActiveDay = activeDays
    ? (sessionsTrend.reduce((s, d) => s + d.sessions, 0) / activeDays).toFixed(1)
    : "0";

  $: sessionsByWeekday = (() => {
    const groups = {};
    const order = [];
    for (const d of sessionsTrend) {
      const wd = new Date(d.date).toLocaleDateString(undefined, { weekday: "short" });
      if (!groups[wd]) {
        groups[wd] = { sessions: 0, sales: 0 };
        order.push(wd);
      }
      groups[wd].sessions += d.sessions;
      groups[wd].sales += d.sales;
    }
    return order.map((wd) => [wd, groups[wd]]);
  })();

  $: healthComponents = (() => {
    const c = health?.components;
    if (!c) return [];
    return [
      {
        label: "Profit margin",
        points: c.profit_margin_points ?? 0,
        max: 40,
        hint: `Margin ${c.profit_margin_pct ?? 0}% — 40 pts at ≥30%, 25 at ≥15%, 10 at >0%`,
      },
      {
        label: "Cash flow",
        points: c.cash_flow_points ?? 0,
        max: 30,
        hint: `Profit stays positive as share of revenue (${Math.round((c.cash_flow_ratio ?? 0) * 100)}%)`,
      },
      {
        label: "Stock health",
        points: c.stock_points ?? 0,
        max: 20,
        hint: `${c.healthy_products ?? 0} of ${c.total_products ?? 0} products healthy · ${c.low_stock ?? 0} low`,
      },
      {
        label: "Debt collection",
        points: c.debt_points ?? 0,
        max: 10,
        hint: `${Math.round((c.collection_ratio ?? 1) * 100)}% of 7-day credit sales collected`,
      },
    ];
  })();

  function healthBarPercent(points, max) {
    if (!max) return 0;
    return Math.max(0, Math.min(100, (points / max) * 100));
  }
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
      <!-- ── Alerts strip ── -->
      {#if alerts.length > 0}
        <div class="alerts-strip">
          {#each alerts as a (a.id)}
            {#if a.link}
              <a class="alert-chip sev-{a.severity}" href={a.link}>
                {#if a.severity === "high"}
                  <AlertCircle size={14} strokeWidth={2.5} />
                {:else if a.severity === "medium"}
                  <AlertTriangle size={14} strokeWidth={2.5} />
                {:else if a.severity === "low"}
                  <CheckCircle2 size={14} strokeWidth={2.5} />
                {:else}
                  <Info size={14} strokeWidth={2.5} />
                {/if}
                <span class="alert-title">{a.title}</span>
                {#if a.cta}
                  <span class="alert-cta">{a.cta} →</span>
                {/if}
              </a>
            {:else}
              <span class="alert-chip sev-{a.severity} no-link">
                {#if a.severity === "high"}
                  <AlertCircle size={14} strokeWidth={2.5} />
                {:else if a.severity === "medium"}
                  <AlertTriangle size={14} strokeWidth={2.5} />
                {:else if a.severity === "low"}
                  <CheckCircle2 size={14} strokeWidth={2.5} />
                {:else}
                  <Info size={14} strokeWidth={2.5} />
                {/if}
                <span class="alert-title">{a.title}</span>
              </span>
            {/if}
          {/each}
        </div>
      {/if}

      <!-- ── Good news + analytical cards ── -->
      <InfoCards
        goodNews={goodNews}
        willRunOut={willRunOut}
        profitByCategory={profitByCategory}
        customerHealth={customerHealth}
        inventoryValue={inventoryValue}
        expenseBreakdown={expenseBreakdown}
      />

      {#if currentSession}
        <div class="session-info">
          <Calendar size={16} strokeWidth={1.75} />
          <span>
            Showing data for session opened
            <strong>{new Date(currentSession.opened_at).toLocaleString()}</strong>
          </span>
        </div>
      {/if}

      <!-- ── Session summary card ── -->
      {#if sessionSummary}
        <div class="session-summary-card">
          <div class="ss-header">
            <div class="ss-title-wrap">
              <Wallet size={18} strokeWidth={2} />
              <span>{sessionSummary.is_active ? "Current session" : "Last session summary"}</span>
            </div>
            {#if sessionSummary.opened_at}
              <span class="ss-time">
                Opened {new Date(sessionSummary.opened_at).toLocaleTimeString()}
                {#if sessionSummary.closed_at}
                  · Closed {new Date(sessionSummary.closed_at).toLocaleTimeString()}
                {/if}
              </span>
            {/if}
          </div>
          <div class="ss-grid">
            <div class="ss-cell">
              <span class="ss-label">Sales</span>
              <span class="ss-value">{sessionSummary.sales.total_count}</span>
            </div>
            <div class="ss-cell">
              <span class="ss-label">Revenue</span>
              <span class="ss-value">MWK {formatMoney(sessionSummary.sales.total_sales)}</span>
            </div>
            <div class="ss-cell">
              <span class="ss-label">Cash sales</span>
              <span class="ss-value">MWK {formatMoney(sessionSummary.sales.cash_sales)}</span>
            </div>
            <div class="ss-cell">
              <span class="ss-label">Expenses</span>
              <span class="ss-value">MWK {formatMoney(sessionSummary.expenses.total)}</span>
            </div>
            <div class="ss-cell highlight">
              <span class="ss-label">Expected in drawer</span>
              <span class="ss-value">
                MWK {formatMoney(sessionSummary.cash_drawer.expected_in_drawer)}
              </span>
            </div>
          </div>
        </div>
      {/if}

      <!-- ── Business Health hero card ── -->
      {#if health}
        <div class="health-card tone-{healthTone}" role="status">
          <div class="health-top-row">
            <div class="health-icon-wrap">
              <Activity size={22} strokeWidth={2} />
            </div>
            <div class="health-content">
              <div class="health-title-row">
                <span class="health-title">Business Health</span>
                <span class="health-score">
                  {health.score}<span class="health-max">/100</span>
                </span>
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

          <div class="health-bar">
            <div class="health-bar-fill" style="width: {health.score}%"></div>
          </div>

          {#if healthComponents.length > 0}
            <div class="health-components">
              {#each healthComponents as c}
                <div class="hc-chip" title={c.hint}>
                  <div class="hc-chip-head">
                    <span class="hc-chip-label">{c.label}</span>
                    <span class="hc-chip-points">{c.points}<span class="hc-chip-max">/{c.max}</span></span>
                  </div>
                  <div class="hc-bar">
                    <div class="hc-bar-fill" style="width: {healthBarPercent(c.points, c.max)}%"></div>
                  </div>
                </div>
              {/each}
            </div>
            <p class="health-explainer">
              Score = sum of the four components. Hover a chip for the rule.
            </p>
          {/if}
        </div>
      {/if}

      <!-- ── Today at a glance ── -->
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
          <div class="today-cell" class:warning={today.low_stock_count > 0}>
            <span class="today-label">Low Stock</span>
            <span class="today-value">
              {#if today.low_stock_count > 0}
                <AlertTriangle size={14} strokeWidth={2} /> {today.low_stock_count}
              {:else}
                0
              {/if}
            </span>
          </div>
        </div>
      {/if}

      <!-- ── Today's Focus ── -->
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

      <!-- ── MONEY ── -->
      <h3 class="section-title">
        <Coins size={16} strokeWidth={2} /> Money
        <span class="section-hint">vs yesterday</span>
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

      <!-- ── VOLUME ── -->
      <h3 class="section-title">
        <Package size={16} strokeWidth={2} /> Volume
        <span class="section-hint">vs yesterday</span>
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

      <!-- ── Sessions & Sales Trend (replaces old Cash Flow card) ── -->
      <div class="sessions-card">
        <div class="sess-header-row">
          <h3 class="sess-header">
            <Store size={18} strokeWidth={2} />
            Sessions &amp; Sales (Last {sessionsDays} Days)
          </h3>
          <div class="period-tabs" role="tablist" aria-label="Sessions period">
            {#each SESSION_OPTIONS as n}
              <button
                type="button"
                class="period-tab"
                class:active={sessionsDays === n}
                on:click={() => setSessionsDays(n)}
                aria-pressed={sessionsDays === n}
                disabled={sessionsLoading}
              >
                {n}d
              </button>
            {/each}
          </div>
        </div>

        {#if sessionsLoading}
          <p class="no-data">Loading…</p>
        {:else if sessionsTrend.length === 0}
          <p class="no-data">No sessions recorded in this period.</p>
        {:else}
          <!-- KPI row -->
          <div class="sess-kpis">
            <div class="sess-kpi">
              <span class="sk-label">Sessions</span>
              <span class="sk-value">{sessionsTrendTotals?.sessions ?? 0}</span>
            </div>
            <div class="sess-kpi">
              <span class="sk-label">Active days</span>
              <span class="sk-value">{activeDays}/{sessionsTrend.length}</span>
            </div>
            <div class="sess-kpi">
              <span class="sk-label">Avg sessions / active day</span>
              <span class="sk-value">{avgSessionsPerActiveDay}</span>
            </div>
            <div class="sess-kpi">
              <span class="sk-label">Total sales</span>
              <span class="sk-value">{sessionsTrendTotals?.sales ?? 0}</span>
            </div>
          </div>

          <!-- Dual bar chart: sessions (green) + sales (blue) -->
          <div class="sess-chart">
            {#each sessionsTrend as d (d.date)}
              {@const sessH = (d.sessions / maxDayValue) * 100}
              {@const saleH = (d.sales / maxDayValue) * 100}
              <div
                class="sess-day"
                class:empty={d.sessions === 0}
                title="{new Date(d.date).toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })}
— {d.sessions} session{d.sessions === 1 ? '' : 's'}
— {d.sales} sale{d.sales === 1 ? '' : 's'}
— MWK {formatMoney(d.revenue)}"
              >
                <div class="sess-bars">
                  <div class="sess-bar sessions-bar" style="height: {Math.max(2, sessH)}%"></div>
                  <div class="sess-bar sales-bar" style="height: {Math.max(2, saleH)}%"></div>
                </div>
                {#if sessionsDays <= 14}
                  <span class="sess-count">{d.sessions}</span>
                {/if}
                <span class="sess-day-label">
                  {sessionsDays <= 7
                    ? new Date(d.date).toLocaleDateString(undefined, { weekday: "short" })
                    : new Date(d.date).toLocaleDateString(undefined, { day: "numeric" })}
                </span>
              </div>
            {/each}
          </div>

          <div class="sess-legend">
            <span class="legend-item"><span class="legend-dot sessions-dot"></span> Sessions</span>
            <span class="legend-item"><span class="legend-dot sales-dot"></span> Sales</span>
            {#if activeDays < sessionsTrend.length}
              <span class="legend-note">
                {sessionsTrend.length - activeDays} day{sessionsTrend.length - activeDays === 1 ? "" : "s"} had no activity
              </span>
            {/if}
          </div>

          <!-- Per-weekday summary -->
          {#if sessionsByWeekday.length > 1}
            <div class="sess-weekday-grid">
              {#each sessionsByWeekday as [wd, v]}
                <div class="wd-chip">
                  <span class="wd-name">{wd}</span>
                  <span class="wd-main">{v.sessions}<small> sess</small></span>
                  <span class="wd-sub">{v.sales} sales</span>
                </div>
              {/each}
            </div>
          {/if}
        {/if}
      </div>

      <!-- ── Debt Ageing ── -->
      {#if debtAgeing && debtAgeing.total > 0}
        <div class="debt-card">
          <h3 class="debt-header">
            <AlertTriangle size={18} strokeWidth={2} />
            Outstanding Credit — Ageing
          </h3>
          <div class="debt-buckets">
            {#each [
              ["current", "Current (<7d)", "#16a34a"],
              ["days_7_14", "7–14 days", "#eab308"],
              ["days_15_30", "15–30 days", "#f97316"],
              ["over_30", "Over 30 days", "#dc2626"],
            ] as [key, label, color]}
              {@const b = debtAgeing.buckets[key]}
              <div class="debt-bucket">
                <div class="db-bar-wrap">
                  <div
                    class="db-bar"
                    style="height: {debtAgeing.total > 0 ? Math.max(4, (b.total / debtAgeing.total) * 100) : 0}%; background: {color};"
                  ></div>
                </div>
                <div class="db-info">
                  <span class="db-label">{label}</span>
                  <strong class="db-total">MWK {formatMoney(b.total)}</strong>
                  <span class="db-count">{b.count} customer{b.count === 1 ? "" : "s"}</span>
                </div>
              </div>
            {/each}
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

      <!-- ── Revenue Heatmap ── -->
      {#if heatmap && heatmapTotal > 0}
        <div class="heatmap-card">
          <div class="heatmap-header">
            <h3>
              <Activity size={18} strokeWidth={2} />
              Sales Heatmap (Last {heatmapDays} Days)
            </h3>
            <div class="period-tabs" role="tablist" aria-label="Heatmap period">
              {#each HEATMAP_OPTIONS as n}
                <button
                  type="button"
                  class="period-tab"
                  class:active={heatmapDays === n}
                  on:click={() => setHeatmapDays(n)}
                  aria-pressed={heatmapDays === n}
                  disabled={heatmapLoading}
                >
                  {n}d
                </button>
              {/each}
            </div>
          </div>

          {#if heatmapLoading}
            <p class="no-data">Loading…</p>
          {:else}
            <div class="heatmap-legend">
              <span class="legend-label">Fewer sales</span>
              <div class="legend-scale">
                {#each [0, 0.25, 0.5, 0.75, 1] as i}
                  <span
                    class="legend-cell"
                    style="background: rgba(15, 107, 62, {i === 0 ? 0.06 : 0.15 + i * 0.85});"
                  ></span>
                {/each}
              </div>
              <span class="legend-label">More sales</span>
            </div>

            <div class="heatmap-wrapper">
              <div class="heatmap">
                <div class="heatmap-corner"></div>
                {#each Array(24) as _, h}
                  <div class="heatmap-hour-label">
                    {#if h % 3 === 0}{h}{/if}
                  </div>
                {/each}

                {#each heatmap.grid as row, dayIdx}
                  <div class="heatmap-day-label">
                    {heatmap.weekday_labels[dayIdx]}
                  </div>
                  {#each row as count, hourIdx}
                    {@const intensity = heatmapIntensity(count, heatmapMax)}
                    <div
                      class="heatmap-cell"
                      class:peak={count === heatmapMax && count > 0}
                      style="background: {count === 0
                        ? 'rgba(15, 107, 62, 0.06)'
                        : `rgba(15, 107, 62, ${0.15 + intensity * 0.85})`};"
                      title="{heatmap.weekday_labels[dayIdx]} {hourIdx}:00 — {count} sale{count === 1 ? '' : 's'}"
                    ></div>
                  {/each}
                {/each}
              </div>
            </div>

            <p class="heatmap-hint">
              Darker = more sales. Hover a cell for details.
              {#if heatmapMax > 0}
                Busiest slot: <strong>{heatmapMax} sale{heatmapMax === 1 ? "" : "s"}</strong>.
              {/if}
            </p>
          {/if}
        </div>
      {/if}

      <!-- ── Top Products ── -->
      {#if topProducts.length > 0}
        <div class="topprod-card">
          <h3 class="tp-header">
            <TrendingUp size={18} strokeWidth={2} />
            Top Products (Last 7 Days)
          </h3>
          <ul class="tp-list">
            {#each topProducts as p, i}
              {@const maxSpar = Math.max(...p.sparkline, 1)}
              <li class="tp-row">
                <span class="tp-rank">{i + 1}</span>
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

      <!-- ── Top Customers ── -->
      {#if topCustomers.length > 0}
        <div class="topcust-card">
          <h3 class="tc-header">
            <Users size={18} strokeWidth={2} />
            Top Customers (Last 7 Days)
          </h3>
          <ul class="tc-list">
            {#each topCustomers as c, i}
              <li class="tc-row">
                <span class="tc-rank">{i + 1}</span>
                <div class="tc-main">
                  <span class="tc-name">{c.name}</span>
                  <span class="tc-meta">
                    {c.purchase_count} purchase{c.purchase_count === 1 ? "" : "s"}
                    {#if c.credit_outstanding > 0}
                      · owes MWK {formatMoney(c.credit_outstanding)}
                    {/if}
                  </span>
                </div>
                <span class="tc-rev">MWK {formatMoney(c.revenue)}</span>
              </li>
            {/each}
          </ul>
        </div>
      {/if}

      <!-- ── Slow Movers ── -->
      {#if slowMovers.length > 0}
        <div class="slow-card">
          <h3 class="sm-header">
            <Package size={18} strokeWidth={2} />
            Slow Movers (Last 30 Days)
            <span class="sm-sub">Cash tied up in idle stock</span>
          </h3>
          <ul class="sm-list">
            {#each slowMovers as p}
              <li class="sm-row">
                <div class="sm-main">
                  <span class="sm-name">{p.name}</span>
                  <span class="sm-meta">
                    {p.sold} sold · {p.stock_qty} {p.unit || "units"} in stock
                  </span>
                </div>
                <span class="sm-value">MWK {formatMoney(p.idle_value)}</span>
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
    display: flex;
    flex-direction: column;
    gap: 0.85rem;
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

  /* ── Alerts strip ── */
  .alerts-strip {
    display: flex;
    gap: 0.5rem;
    overflow-x: auto;
    padding-bottom: 0.25rem;
    scrollbar-width: thin;
  }
  .alert-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.55rem 0.8rem;
    border-radius: 10px;
    border: 1px solid var(--border, #e5e7eb);
    background: var(--surface, #fff);
    text-decoration: none;
    color: var(--text, #111827);
    font-size: 0.82rem;
    white-space: nowrap;
    flex-shrink: 0;
    transition: all 0.15s;
  }
  .alert-chip:hover { transform: translateY(-1px); box-shadow: 0 2px 6px rgba(0,0,0,0.06); }
  .alert-chip.no-link { cursor: default; }
  .alert-chip.no-link:hover { transform: none; box-shadow: none; }
  .alert-chip.sev-high { background: #fef2f2; border-color: #fecaca; color: #991b1b; }
  .alert-chip.sev-medium { background: #fffbeb; border-color: #fde68a; color: #92400e; }
  .alert-chip.sev-low { background: #f0fdf4; border-color: #86efac; color: #166534; }
  .alert-chip.sev-info { background: #eff6ff; border-color: #bfdbfe; color: #1e40af; }
  .alert-title { font-weight: 600; }
  .alert-cta { font-size: 0.75rem; font-weight: 700; opacity: 0.85; }

  /* ── Session summary ── */
  .session-summary-card {
    background: linear-gradient(135deg, rgba(59, 130, 246, 0.05) 0%, var(--surface, #fff) 70%);
    border: 1px solid #bfdbfe;
    border-radius: 12px;
    padding: 1rem 1.1rem;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }
  .ss-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.5rem;
  }
  .ss-title-wrap {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-weight: 600;
    color: var(--text, #111827);
    font-size: 0.95rem;
  }
  .ss-title-wrap svg { color: #1e40af; }
  .ss-time { font-size: 0.75rem; color: var(--text-light, #6b7280); }
  .ss-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 0.5rem; }
  .ss-cell {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
    padding: 0.55rem 0.6rem;
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 9px;
    min-width: 0;
  }
  .ss-cell.highlight { background: #eff6ff; border-color: #bfdbfe; }
  .ss-label {
    font-size: 0.65rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    color: var(--text-light, #6b7280);
  }
  .ss-value {
    font-size: 0.88rem;
    font-weight: 700;
    color: var(--text, #111827);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .ss-cell.highlight .ss-value { color: #1e40af; }

  /* ── Session info ── */
  .session-info {
    display: flex;
    align-items: flex-start;
    gap: 0.5rem;
    background: rgba(15, 107, 62, 0.08);
    padding: 0.65rem 0.9rem;
    border-radius: 10px;
    font-size: 0.85rem;
    color: var(--primary, #0f6b3e);
    border-left: 3px solid var(--primary, #0f6b3e);
    line-height: 1.4;
  }
  .session-info strong { font-weight: 600; word-break: break-word; }

  /* ── Health card ── */
  .health-card {
    padding: 1.1rem 1.25rem;
    border-radius: 14px;
    border: 1px solid var(--border, #e5e7eb);
    background: var(--surface, #fff);
    box-sizing: border-box;
    width: 100%;
    display: flex;
    flex-direction: column;
    gap: 0.85rem;
    transition: all 0.2s;
  }
  .health-card.tone-good { border-color: #86efac; background: linear-gradient(135deg, rgba(34, 197, 94, 0.05) 0%, var(--surface, #fff) 70%); }
  .health-card.tone-warn { border-color: #fcd34d; background: linear-gradient(135deg, rgba(245, 158, 11, 0.05) 0%, var(--surface, #fff) 70%); }
  .health-card.tone-bad { border-color: #fca5a5; background: linear-gradient(135deg, rgba(220, 38, 38, 0.05) 0%, var(--surface, #fff) 70%); }
  .health-top-row { display: flex; align-items: flex-start; gap: 0.9rem; }
  .health-icon-wrap {
    flex-shrink: 0; width: 44px; height: 44px; border-radius: 12px;
    display: flex; align-items: center; justify-content: center;
    background: var(--background, #f3f4f6); color: var(--text, #374151);
  }
  .tone-good .health-icon-wrap { background: rgba(34, 197, 94, 0.15); color: #15803d; }
  .tone-warn .health-icon-wrap { background: rgba(245, 158, 11, 0.15); color: #b45309; }
  .tone-bad .health-icon-wrap { background: rgba(220, 38, 38, 0.15); color: #b91c1c; }
  .health-content { flex: 1; min-width: 0; }
  .health-title-row { display: flex; justify-content: space-between; align-items: baseline; gap: 0.5rem; }
  .health-title { font-size: 0.82rem; font-weight: 700; color: var(--text-light, #6b7280); text-transform: uppercase; letter-spacing: 0.04em; }
  .health-score { font-size: 1.75rem; font-weight: 800; color: var(--text, #111827); line-height: 1; }
  .health-max { font-size: 0.9rem; font-weight: 500; color: var(--text-light, #6b7280); margin-left: 2px; }
  .health-sub { display: flex; align-items: center; flex-wrap: wrap; gap: 0.4rem; margin-top: 0.3rem; font-size: 0.8rem; color: var(--text-light, #6b7280); }
  .health-delta { display: inline-flex; align-items: center; gap: 0.15rem; font-weight: 600; }
  .tone-good .health-delta { color: #15803d; }
  .tone-warn .health-delta { color: #b45309; }
  .tone-bad .health-delta { color: #b91c1c; }
  .health-sep { color: var(--border, #d1d5db); }
  .health-label { font-weight: 600; color: var(--text, #111827); }
  .health-message { margin: 0.4rem 0 0; font-size: 0.82rem; color: var(--text, #111827); line-height: 1.35; }
  .health-bar { width: 100%; height: 10px; background: var(--background, #f3f4f6); border-radius: 6px; overflow: hidden; }
  .health-bar-fill { height: 100%; border-radius: 6px; transition: width 0.4s ease; }
  .tone-good .health-bar-fill { background: #16a34a; }
  .tone-warn .health-bar-fill { background: #f59e0b; }
  .tone-bad .health-bar-fill { background: #dc2626; }
  .health-components { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 0.5rem; padding-top: 0.5rem; border-top: 1px dashed var(--border, #e5e7eb); }
  .hc-chip { display: flex; flex-direction: column; gap: 0.35rem; padding: 0.55rem 0.65rem; background: var(--background, #f9fafb); border-radius: 9px; border: 1px solid var(--border, #e5e7eb); cursor: help; transition: all 0.15s; }
  .hc-chip:hover { border-color: var(--primary, #0f6b3e); }
  .hc-chip-head { display: flex; justify-content: space-between; align-items: baseline; gap: 0.4rem; }
  .hc-chip-label { font-size: 0.72rem; font-weight: 600; color: var(--text-light, #6b7280); text-transform: uppercase; letter-spacing: 0.03em; }
  .hc-chip-points { font-size: 0.85rem; font-weight: 700; color: var(--text, #111827); }
  .hc-chip-max { font-size: 0.7rem; color: var(--text-light, #6b7280); font-weight: 500; }
  .hc-bar { width: 100%; height: 5px; background: var(--surface, #fff); border-radius: 3px; overflow: hidden; border: 1px solid var(--border, #e5e7eb); }
  .hc-bar-fill { height: 100%; background: var(--primary, #0f6b3e); border-radius: 3px; transition: width 0.4s ease; }
  .health-explainer { margin: 0; font-size: 0.72rem; color: var(--text-light, #6b7280); font-style: italic; }

  .today-strip {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 0.5rem;
    padding: 0.75rem 0.85rem;
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 12px;
    box-sizing: border-box;
    width: 100%;
  }
  .today-cell { display: flex; flex-direction: column; gap: 0.15rem; min-width: 0; padding: 0.35rem 0.4rem; border-radius: 8px; transition: background 0.15s; }
  .today-cell.warning { background: rgba(245, 158, 11, 0.08); }
  .today-label { font-size: 0.7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.03em; color: var(--text-light, #6b7280); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .today-value { font-size: 0.95rem; font-weight: 700; color: var(--text, #111827); display: inline-flex; align-items: center; gap: 0.2rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .today-cell.warning .today-value { color: #b45309; }

  .focus-card { background: var(--surface, #fff); border: 1px solid var(--border, #e5e7eb); border-radius: 12px; padding: 1rem 1.1rem; box-sizing: border-box; width: 100%; }
  .focus-header { display: flex; align-items: center; gap: 0.5rem; margin: 0 0 0.75rem; font-size: 1rem; font-weight: 600; color: var(--text, #111827); }
  .focus-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 0.55rem; }
  .focus-item { display: flex; gap: 0.75rem; padding: 0.65rem 0.75rem; border-radius: 9px; background: var(--background, #f9fafb); border-left: 3px solid var(--text-light, #9ca3af); box-sizing: border-box; }
  .focus-item.sev-high { border-left-color: #dc2626; background: rgba(220, 38, 38, 0.04); }
  .focus-item.sev-medium { border-left-color: #d97706; background: rgba(245, 158, 11, 0.04); }
  .focus-item.sev-low { border-left-color: #059669; background: rgba(22, 163, 74, 0.04); }
  .focus-number { flex-shrink: 0; width: 24px; height: 24px; border-radius: 50%; background: var(--surface, #fff); border: 1px solid var(--border, #e5e7eb); display: inline-flex; align-items: center; justify-content: center; font-size: 0.75rem; font-weight: 700; color: var(--text, #111827); }
  .focus-body { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 0.15rem; }
  .focus-title { font-size: 0.9rem; font-weight: 600; color: var(--text, #111827); text-decoration: none; line-height: 1.3; word-break: break-word; }
  .focus-title:hover { text-decoration: underline; }
  .focus-detail { font-size: 0.8rem; color: var(--text-light, #6b7280); line-height: 1.35; }
  .focus-hint { font-size: 0.78rem; font-weight: 600; color: var(--primary, #0f6b3e); }

  .section-title { display: flex; align-items: center; gap: 0.4rem; margin: 0.4rem 0 0; font-size: 0.78rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: var(--text-light, #6b7280); }
  .section-hint { font-size: 0.68rem; font-weight: 500; text-transform: none; letter-spacing: 0; color: var(--text-light, #6b7280); margin-left: 0.25rem; opacity: 0.8; }

  .metrics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 0.9rem; width: 100%; box-sizing: border-box; }

  /* ── Sessions & Sales Trend ── */
  .sessions-card {
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 12px;
    padding: 1rem 1.1rem;
    box-sizing: border-box;
    width: 100%;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }
  .sess-header-row {
    display: flex; justify-content: space-between; align-items: center;
    gap: 0.5rem; flex-wrap: wrap;
  }
  .sess-header {
    display: flex; align-items: center; gap: 0.5rem;
    margin: 0; font-size: 1rem; font-weight: 600; color: var(--text, #111827);
  }
  .sess-kpis {
    display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.5rem;
  }
  .sess-kpi {
    display: flex; flex-direction: column; gap: 0.1rem;
    padding: 0.55rem 0.7rem;
    background: var(--background, #f9fafb);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 9px;
    min-width: 0;
  }
  .sk-label {
    font-size: 0.65rem; font-weight: 600; text-transform: uppercase;
    letter-spacing: 0.03em; color: var(--text-light, #6b7280);
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }
  .sk-value {
    font-size: 1.05rem; font-weight: 800; color: var(--text, #111827);
  }

  .sess-chart {
    display: flex; align-items: flex-end; gap: 0.5rem;
    height: 190px; padding-top: 0.5rem;
    border-bottom: 1px solid var(--border, #e5e7eb);
    overflow-x: auto; overflow-y: hidden;
  }
  .sess-day {
    flex: 1 1 0; min-width: 20px;
    display: flex; flex-direction: column; align-items: center;
    height: 100%; justify-content: flex-end;
    position: relative;
  }
  .sess-day.empty .sess-bar { opacity: 0.25; }
  .sess-bars {
    flex: 1; width: 100%;
    display: flex; align-items: flex-end; justify-content: center;
    gap: 2px; min-height: 2px;
  }
  .sess-bar {
    width: 45%; max-width: 22px;
    border-radius: 4px 4px 0 0;
    transition: height 0.3s ease;
  }
  .sessions-bar { background: var(--primary, #0f6b3e); }
  .sales-bar    { background: #3b82f6; }
  .sess-count {
    font-size: 0.62rem; font-weight: 700; color: var(--text, #111827);
    margin-top: 2px;
  }
  .sess-day-label {
    margin-top: 0.35rem; font-size: 0.7rem; font-weight: 500;
    color: var(--text-light, #6b7280); white-space: nowrap;
  }

  .sess-legend {
    display: flex; align-items: center; gap: 0.9rem;
    font-size: 0.75rem; color: var(--text-light, #6b7280);
    flex-wrap: wrap;
  }
  .legend-item { display: inline-flex; align-items: center; gap: 0.3rem; }
  .legend-dot { width: 10px; height: 10px; border-radius: 3px; }
  .sessions-dot { background: var(--primary, #0f6b3e); }
  .sales-dot    { background: #3b82f6; }
  .legend-note { margin-left: auto; font-style: italic; opacity: 0.8; }

  .sess-weekday-grid {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(90px, 1fr));
    gap: 0.4rem; padding-top: 0.5rem;
    border-top: 1px dashed var(--border, #e5e7eb);
  }
  .wd-chip {
    display: flex; flex-direction: column; gap: 0.05rem;
    padding: 0.45rem 0.55rem;
    background: var(--background, #f9fafb);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 8px; text-align: center;
  }
  .wd-name {
    font-size: 0.65rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.04em; color: var(--text-light, #6b7280);
  }
  .wd-main {
    font-size: 1rem; font-weight: 800; color: var(--text, #111827);
  }
  .wd-main small { font-size: 0.65rem; font-weight: 500; color: var(--text-light, #6b7280); }
  .wd-sub { font-size: 0.68rem; color: var(--text-light, #6b7280); }

  /* Debt Ageing */
  .debt-card { background: var(--surface, #fff); border: 1px solid var(--border, #e5e7eb); border-radius: 12px; padding: 1rem 1.1rem; box-sizing: border-box; width: 100%; }
  .debt-header { display: flex; align-items: center; gap: 0.5rem; margin: 0 0 0.85rem; font-size: 1rem; font-weight: 600; color: var(--text, #111827); }
  .debt-buckets { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.6rem; align-items: end; }
  .debt-bucket { display: flex; flex-direction: column; gap: 0.35rem; align-items: stretch; }
  .db-bar-wrap { height: 60px; background: var(--background, #f3f4f6); border-radius: 6px; display: flex; align-items: flex-end; overflow: hidden; }
  .db-bar { width: 100%; border-radius: 6px 6px 0 0; transition: height 0.4s; }
  .db-info { display: flex; flex-direction: column; gap: 0.1rem; }
  .db-label { font-size: 0.68rem; font-weight: 600; color: var(--text-light, #6b7280); text-transform: uppercase; letter-spacing: 0.03em; }
  .db-total { font-size: 0.85rem; font-weight: 700; color: var(--text, #111827); }
  .db-count { font-size: 0.7rem; color: var(--text-light, #6b7280); }

  /* Chart */
  .chart-card { background: var(--surface, #fff); border-radius: 12px; padding: 1.25rem; border: 1px solid var(--border, #e5e7eb); box-sizing: border-box; width: 100%; overflow: hidden; }
  .chart-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; gap: 0.75rem; flex-wrap: wrap; }
  .chart-header h3 { display: flex; align-items: center; gap: 0.5rem; margin: 0; font-size: 1.05rem; font-weight: 600; color: var(--text, #111827); }
  .period-tabs { display: inline-flex; gap: 0.25rem; background: var(--background, #f3f4f6); padding: 0.2rem; border-radius: 10px; border: 1px solid var(--border, #e5e7eb); }
  .period-tab { border: none; background: transparent; padding: 0.35rem 0.7rem; border-radius: 7px; font-size: 0.8rem; font-weight: 600; color: var(--text-light, #6b7280); cursor: pointer; transition: all 0.15s; line-height: 1; }
  .period-tab:hover:not(:disabled) { color: var(--text, #111827); }
  .period-tab.active { background: var(--surface, #ffffff); color: var(--primary, #0f6b3e); box-shadow: 0 1px 2px rgba(0, 0, 0, 0.08); }
  .period-tab:disabled { opacity: 0.6; cursor: not-allowed; }
  .no-data { text-align: center; color: var(--text-light, #6b7280); padding: 2rem 1rem; font-size: 0.9rem; }
  .chart-wrapper { width: 100%; overflow: hidden; }
  .chart-wrapper.compact .bar-label { font-size: 0.6rem; }
  .chart { display: flex; align-items: flex-end; gap: 0.4rem; height: 200px; width: 100%; box-sizing: border-box; padding-bottom: 1px; border-bottom: 1px solid var(--border, #e5e7eb); }
  .bar-container { flex: 1 1 0; min-width: 0; display: flex; flex-direction: column; align-items: center; height: 100%; justify-content: flex-end; }
  .bar { width: 100%; max-width: 56px; background: var(--primary, #0f6b3e); border-radius: 6px 6px 0 0; min-height: 3px; transition: height 0.3s ease; display: flex; justify-content: center; align-items: flex-start; padding-top: 0.35rem; box-sizing: border-box; position: relative; overflow: hidden; }
  .bar-value { color: white; font-size: 0.65rem; font-weight: 600; white-space: nowrap; writing-mode: vertical-rl; text-orientation: upright; padding: 0.1rem; overflow: hidden; }
  .bar-label { margin-top: 0.5rem; font-size: 0.72rem; color: var(--text-light, #6b7280); text-align: center; white-space: nowrap; font-weight: 500; overflow: hidden; text-overflow: ellipsis; max-width: 100%; }

  /* ── Heatmap ── */
  .heatmap-card { background: var(--surface, #fff); border: 1px solid var(--border, #e5e7eb); border-radius: 12px; padding: 1rem 1.1rem; box-sizing: border-box; width: 100%; }
  .heatmap-header { display: flex; justify-content: space-between; align-items: center; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 0.75rem; }
  .heatmap-header h3 { display: flex; align-items: center; gap: 0.5rem; margin: 0; font-size: 1rem; font-weight: 600; color: var(--text, #111827); }
  .heatmap-legend { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.6rem; font-size: 0.72rem; color: var(--text-light, #6b7280); }
  .legend-scale { display: flex; gap: 2px; }
  .legend-cell { width: 14px; height: 10px; border-radius: 2px; }
  .heatmap-wrapper { overflow-x: auto; padding-bottom: 0.25rem; }
  .heatmap { display: grid; grid-template-columns: 36px repeat(24, minmax(16px, 1fr)); gap: 2px; min-width: 560px; }
  .heatmap-corner { height: 14px; }
  .heatmap-hour-label { font-size: 0.6rem; color: var(--text-light, #9ca3af); text-align: center; height: 14px; line-height: 14px; user-select: none; }
  .heatmap-day-label { font-size: 0.65rem; font-weight: 600; color: var(--text-light, #6b7280); height: 22px; display: flex; align-items: center; padding-right: 0.4rem; user-select: none; }
  .heatmap-cell { height: 22px; border-radius: 3px; transition: transform 0.1s, box-shadow 0.1s; cursor: pointer; }
  .heatmap-cell:hover { transform: scale(1.15); box-shadow: 0 0 0 1px var(--primary, #0f6b3e); z-index: 2; position: relative; }
  .heatmap-cell.peak { box-shadow: 0 0 0 1px #166534; }
  .heatmap-hint { margin: 0.6rem 0 0; font-size: 0.75rem; color: var(--text-light, #6b7280); text-align: center; }
  .heatmap-hint strong { color: var(--text, #111827); }

  /* Top products */
  .topprod-card { background: var(--surface, #fff); border: 1px solid var(--border, #e5e7eb); border-radius: 12px; padding: 1rem 1.1rem; box-sizing: border-box; width: 100%; }
  .tp-header { display: flex; align-items: center; gap: 0.5rem; margin: 0 0 0.75rem; font-size: 1rem; font-weight: 600; color: var(--text, #111827); }
  .tp-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 0.5rem; }
  .tp-row { display: flex; align-items: center; gap: 0.65rem; padding: 0.55rem 0.7rem; border-radius: 9px; background: var(--background, #f9fafb); min-width: 0; }
  .tp-rank { flex-shrink: 0; width: 24px; height: 24px; border-radius: 50%; background: var(--primary, #0f6b3e); color: white; font-size: 0.72rem; font-weight: 700; display: inline-flex; align-items: center; justify-content: center; }
  .tp-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 0.15rem; }
  .tp-name { font-weight: 600; font-size: 0.88rem; color: var(--text, #111827); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .tp-meta { font-size: 0.75rem; color: var(--text-light, #6b7280); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .tp-spark { display: flex; align-items: flex-end; gap: 2px; height: 28px; width: 78px; flex-shrink: 0; }
  .spark-bar { flex: 1 1 0; min-width: 0; background: var(--primary, #0f6b3e); border-radius: 2px 2px 0 0; opacity: 0.8; }

  /* Top customers */
  .topcust-card { background: var(--surface, #fff); border: 1px solid var(--border, #e5e7eb); border-radius: 12px; padding: 1rem 1.1rem; box-sizing: border-box; width: 100%; }
  .tc-header { display: flex; align-items: center; gap: 0.5rem; margin: 0 0 0.75rem; font-size: 1rem; font-weight: 600; color: var(--text, #111827); }
  .tc-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 0.5rem; }
  .tc-row { display: flex; align-items: center; gap: 0.65rem; padding: 0.55rem 0.7rem; border-radius: 9px; background: var(--background, #f9fafb); min-width: 0; }
  .tc-rank { flex-shrink: 0; width: 24px; height: 24px; border-radius: 50%; background: #3b82f6; color: white; font-size: 0.72rem; font-weight: 700; display: inline-flex; align-items: center; justify-content: center; }
  .tc-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 0.15rem; }
  .tc-name { font-weight: 600; font-size: 0.88rem; color: var(--text, #111827); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .tc-meta { font-size: 0.75rem; color: var(--text-light, #6b7280); }
  .tc-rev { font-weight: 700; font-size: 0.9rem; color: #1e40af; flex-shrink: 0; }

  /* Slow movers */
  .slow-card { background: var(--surface, #fff); border: 1px solid #fed7aa; border-radius: 12px; padding: 1rem 1.1rem; box-sizing: border-box; width: 100%; background: linear-gradient(135deg, rgba(251, 146, 60, 0.04) 0%, var(--surface, #fff) 70%); }
  .sm-header { display: flex; align-items: center; gap: 0.5rem; margin: 0 0 0.75rem; font-size: 1rem; font-weight: 600; color: var(--text, #111827); flex-wrap: wrap; }
  .sm-sub { font-size: 0.75rem; font-weight: 500; color: #c2410c; text-transform: none; letter-spacing: 0; }
  .sm-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 0.4rem; }
  .sm-row { display: flex; justify-content: space-between; align-items: center; gap: 0.5rem; padding: 0.55rem 0.7rem; border-radius: 9px; background: #fff7ed; border: 1px solid #fed7aa; }
  .sm-main { display: flex; flex-direction: column; gap: 0.1rem; min-width: 0; flex: 1; }
  .sm-name { font-weight: 600; font-size: 0.88rem; color: var(--text, #111827); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .sm-meta { font-size: 0.75rem; color: var(--text-light, #6b7280); }
  .sm-value { font-weight: 700; font-size: 0.9rem; color: #c2410c; flex-shrink: 0; }

  /* Responsive */
  @media (max-width: 768px) {
    .metrics-grid { grid-template-columns: repeat(2, 1fr); gap: 0.65rem; }
    .chart-card { padding: 1rem; }
    .chart { height: 170px; gap: 0.35rem; }
    .bar-value { font-size: 0.6rem; }
    .bar-label { font-size: 0.68rem; }
    .today-strip { grid-template-columns: repeat(2, 1fr); row-gap: 0.6rem; }
    .ss-grid { grid-template-columns: repeat(2, 1fr); }
    .debt-buckets { grid-template-columns: repeat(2, 1fr); }
    .sess-kpis { grid-template-columns: repeat(2, 1fr); }
    .sess-chart { height: 160px; gap: 0.35rem; }
  }

  @media (max-width: 480px) {
    .session-info { font-size: 0.78rem; padding: 0.55rem 0.75rem; }
    .health-card { padding: 0.9rem 1rem; }
    .health-icon-wrap { width: 38px; height: 38px; }
    .health-score { font-size: 1.5rem; }
    .health-message { font-size: 0.78rem; }
    .health-components { grid-template-columns: 1fr 1fr; }
    .hc-chip { padding: 0.45rem 0.55rem; }
    .hc-chip-label { font-size: 0.65rem; }
    .today-strip { padding: 0.6rem 0.7rem; gap: 0.4rem 0.5rem; }
    .today-value { font-size: 0.85rem; }
    .today-label { font-size: 0.65rem; }
    .focus-card { padding: 0.85rem 0.9rem; }
    .focus-title { font-size: 0.85rem; }
    .focus-detail, .focus-hint { font-size: 0.75rem; }
    .metrics-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0.5rem; }
    .chart-card { padding: 0.75rem; border-radius: 10px; }
    .chart-header { margin-bottom: 0.75rem; }
    .chart-header h3 { font-size: 0.9rem; }
    .period-tab { padding: 0.3rem 0.55rem; font-size: 0.72rem; }
    .chart { height: 140px; gap: 0.25rem; }
    .bar-value { display: none; }
    .bar-label { font-size: 0.65rem; margin-top: 0.35rem; }
    .chart-wrapper.compact .bar-label { font-size: 0.55rem; }
    .topprod-card { padding: 0.85rem 0.9rem; }
    .tp-spark { width: 60px; height: 24px; }
    .tp-rank { width: 22px; height: 22px; font-size: 0.68rem; }
    .alerts-strip { gap: 0.35rem; }
    .alert-chip { font-size: 0.75rem; padding: 0.45rem 0.65rem; }
    .ss-grid { grid-template-columns: 1fr 1fr; }
    .debt-buckets { grid-template-columns: 1fr 1fr; }
    .heatmap { grid-template-columns: 28px repeat(24, minmax(13px, 1fr)); gap: 1.5px; }
    .heatmap-cell { height: 18px; border-radius: 2px; }
    .heatmap-day-label { height: 18px; font-size: 0.6rem; }
    .heatmap-hour-label { font-size: 0.55rem; }
    .sessions-card { padding: 0.85rem 0.9rem; }
    .sess-chart { height: 130px; gap: 0.25rem; }
    .sess-count { display: none; }
    .sess-day-label { font-size: 0.6rem; }
    .sess-weekday-grid { grid-template-columns: repeat(2, 1fr); }
  }

  @media (max-width: 360px) {
    .metrics-grid { gap: 0.4rem; }
    .chart { height: 120px; gap: 0.2rem; }
    .bar-label { font-size: 0.6rem; }
    .health-components { grid-template-columns: 1fr; }
    .ss-grid { grid-template-columns: 1fr; }
  }
</style>