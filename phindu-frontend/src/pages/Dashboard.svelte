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
    HelpCircle,
    ArrowUpRight,
    ArrowDownRight,
    Minus,
    Target,
    Wallet,
    Coins,
    Package,
    Users,
    Store,
    ChevronDown,
    ChevronUp,
  } from "lucide-svelte";
  import Layout from "../components/Layout.svelte";
  import MetricCard from "../components/MetricCard.svelte";
  import InfoCards from "../components/InfoCards.svelte";
  import API from "../api/api";
  import EmptyState from "../components/EmptyState.svelte";

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

  let health = null;
  let focus = [];
  let deltas = null;
  let topProducts = [];

  let alerts = [];
  let topCustomers = [];
  let debtAgeing = null;
  let slowMovers = [];

  let willRunOut = [];

  let profitByCategory = [];
  let inventoryValue = null;
  let expenseBreakdown = null;
  let goodNews = [];

  const DELTA_OPTIONS = [
    ["day", "Day"],
    ["week", "Week"],
    ["month", "Month"],
    ["year", "Year"],
  ];
  let deltaPeriod = "day";
  let deltaLoading = false;

  const TREND_OPTIONS = [7, 14, 30];
  let trendDays = 7;
  let trendLoading = false;

  let sessionsTrend = [];
  let sessionsTrendTotals = null;
  let sessionsLoading = false;
  let sessionsDays = 7;
  const SESSION_OPTIONS = [7, 14, 30];

  let showHealthExplainer = false;

  let pollId = null;

  // ── Loading control (performance) ──
  let loadSeq = 0;            // discards stale responses
  let hasLoadedOnce = false;  // spinner only on the very first load
  let secondaryReady = false; // secondary widgets finished (avoids empty-state flash)
  let lastLoadedAt = 0;
  const STALE_MS = 30000;

  onMount(() => {
    loadDashboard();
    const onVis = () => {
      if (
        document.visibilityState === "visible" &&
        Date.now() - lastLoadedAt > STALE_MS
      ) {
        loadDashboard({ silent: true });
      }
    };
    document.addEventListener("visibilitychange", onVis);
    return () => document.removeEventListener("visibilitychange", onVis);
  });

  onDestroy(() => {
    if (pollId) clearInterval(pollId);
  });

  // Poll only while a session is open; only re-evaluates when the flag flips.
  $: hasSession = !!currentSession;
  $: syncPolling(hasSession);

  function syncPolling(active) {
    if (pollId) {
      clearInterval(pollId);
      pollId = null;
    }
    if (active) {
      pollId = setInterval(() => {
        if (document.visibilityState === "visible") refreshLive();
      }, 60000);
    }
  }

  $: deltaLabel =
    deltaPeriod === "day" ? "yesterday" :
    deltaPeriod === "week" ? "last week" :
    deltaPeriod === "month" ? "last month" :
    "last year";

  // Single source of truth for profit. Both the session card and the Money
  // card read this, so they can never disagree.
  // If the API returns profit equal to revenue while cost/expenses exist
  // (a revenue-as-profit bug), derive it: revenue - cost - expenses.
  function resolveProfit(d) {
    if (!d) return 0;
    const revenue = Number(d.total_revenue ?? 0) || 0;
    const cost = Number(d.total_cost ?? 0) || 0;
    const expenses = Number(d.total_expenses ?? 0) || 0;
    const apiProfit = Number(d.profit);

    const looksLikeRevenue =
      Number.isFinite(apiProfit) &&
      revenue > 0 &&
      apiProfit === revenue &&
      cost + expenses > 0;

    if (Number.isFinite(apiProfit) && !looksLikeRevenue) return apiProfit;
    return revenue - cost - expenses;
  }

  $: displayProfit = resolveProfit(data);
  $: sessionProfit = displayProfit;

  // Show the welcome state only when the shop has no activity or stock signals.
  $: isEmptyShop =
    !loading &&
    !error &&
    secondaryReady &&
    !currentSession &&
    (data?.total_revenue ?? 0) === 0 &&
    (data?.total_items_sold ?? 0) === 0 &&
    (data?.total_expenses ?? 0) === 0 &&
    alerts.length === 0 &&
    willRunOut.length === 0 &&
    slowMovers.length === 0 &&
    topProducts.length === 0;

  function dashboardUrl(session, period) {
    return session
      ? `/dashboard/?session_id=${session.id}&period=${period}`
      : `/dashboard/?period=${period}`;
  }

  function pickDash(res, fallback) {
    const d = Array.isArray(res?.data) ? res.data[0] : res?.data;
    return d || fallback;
  }

  async function loadDashboard(opts) {
    const silent = opts && opts.silent === true;
    const seq = ++loadSeq;
    const isStale = () => seq !== loadSeq;

    if (!hasLoadedOnce && !silent) loading = true;
    error = null;

    // Run a request and apply its result when it lands (progressive render).
    const run = (promise, apply) =>
      promise
        .then((res) => {
          if (!isStale()) apply(res);
        })
        .catch((e) => console.error(e));

    try {
      // ── Fire every independent request immediately, in parallel ──
      const sessionP = API.get("/sessions/current").catch(() => ({ data: {} }));

      const secondary = [
        run(API.get(`/analytics/revenue-trend?days=${trendDays}`), (r) => {
          chartData = r.data;
        }),
        run(API.get("/dashboard/health-score"), (r) => {
          health = r.data;
        }),
        run(API.get("/dashboard/focus"), (r) => {
          focus = r.data?.items || [];
        }),
        run(
          API.get(`/dashboard/metric-deltas?period=${deltaPeriod}`).catch(() => ({
            data: {
              revenue: { current: 0, previous: 0, absolute: 0, percent: null },
              profit: { current: 0, previous: 0, absolute: 0, percent: null },
              expenses: { current: 0, previous: 0, absolute: 0, percent: null },
              items_sold: { current: 0, previous: 0, absolute: 0, percent: null },
            },
          })),
          (r) => {
            deltas = r.data;
          }
        ),
        run(
          API.get(`/dashboard/sessions-trend?days=${sessionsDays}`).catch(() => ({
            data: { items: [], totals: null },
          })),
          (r) => {
            sessionsTrend = r.data?.items || [];
            sessionsTrendTotals = r.data?.totals || null;
          }
        ),
        run(API.get("/dashboard/top-products-trend?days=7&limit=3"), (r) => {
          topProducts = r.data?.products || [];
        }),
        run(API.get("/dashboard/alerts").catch(() => ({ data: { alerts: [] } })), (r) => {
          alerts = r.data?.alerts || [];
        }),
        run(
          API.get("/dashboard/top-customers?days=7&limit=5").catch(() => ({ data: { customers: [] } })),
          (r) => {
            topCustomers = r.data?.customers || [];
          }
        ),
        run(API.get("/dashboard/debt-ageing").catch(() => ({ data: null })), (r) => {
          debtAgeing = r.data;
        }),
        run(
          API.get("/dashboard/slow-movers?days=30&limit=5").catch(() => ({ data: { products: [] } })),
          (r) => {
            slowMovers = r.data?.products || [];
          }
        ),
        run(
          API.get("/dashboard/will-run-out?days=14&limit=5").catch(() => ({ data: { products: [] } })),
          (r) => {
            willRunOut = r.data?.products || [];
          }
        ),
        run(
          API.get("/dashboard/profit-by-category?days=30").catch(() => ({ data: { categories: [] } })),
          (r) => {
            const cats = r.data?.categories || [];
            const total = cats.reduce((s, x) => s + Number(x.profit || 0), 0);
            profitByCategory = cats.map((c) => {
              if (c.share_percent == null) {
                return {
                  ...c,
                  share_percent:
                    total > 0 ? Number(((c.profit || 0) / total) * 100).toFixed(1) : "0.0",
                };
              }
              return c;
            });
          }
        ),
        run(API.get("/dashboard/inventory-value").catch(() => ({ data: null })), (r) => {
          inventoryValue = r.data;
        }),
        run(API.get("/dashboard/expense-breakdown?days=30").catch(() => ({ data: null })), (r) => {
          if (r.data?.categories) {
            const cats = r.data.categories;
            const total = cats.reduce((s, c) => s + Number(c.total || 0), 0);
            expenseBreakdown = {
              ...r.data,
              categories: cats.map((c) => ({
                ...c,
                percent:
                  c.percent != null
                    ? c.percent
                    : total > 0
                    ? Number(((c.total || 0) / total) * 100).toFixed(2)
                    : "0.00",
              })),
            };
          } else {
            expenseBreakdown = r.data;
          }
        }),
        run(API.get("/dashboard/good-news").catch(() => ({ data: { items: [] } })), (r) => {
          goodNews = r.data?.items || [];
        }),
      ];

      // ── Core: session -> dashboard + summary (the only blocking path) ──
      const sessionRes = await sessionP;
      if (isStale()) return;
      currentSession = sessionRes.data?.id ? sessionRes.data : null;

      const [dashRes, summaryRes] = await Promise.all([
        API.get(dashboardUrl(currentSession, deltaPeriod)),
        currentSession
          ? API.get(`/sessions/${currentSession.id}/summary`).catch(() => ({ data: null }))
          : Promise.resolve({ data: null }),
      ]);
      if (isStale()) return;

      data = pickDash(dashRes, data);
      sessionSummary = summaryRes.data;

      hasLoadedOnce = true;
      lastLoadedAt = Date.now();
      loading = false; // render now; the rest streams in

      await Promise.allSettled(secondary);
      if (!isStale()) secondaryReady = true;
    } catch (err) {
      if (!hasLoadedOnce) {
        error = "Failed to load dashboard data";
      }
      console.error(err);
    } finally {
      if (!isStale()) loading = false;
    }
  }

  // Light refresh used by the 60s poll: only live session data + alerts.
  async function refreshLive() {
    try {
      const sessionRes = await API.get("/sessions/current").catch(() => ({ data: {} }));
      const sess = sessionRes.data?.id ? sessionRes.data : null;

      const [dashRes, summaryRes, alertsRes] = await Promise.all([
        API.get(dashboardUrl(sess, deltaPeriod)),
        sess
          ? API.get(`/sessions/${sess.id}/summary`).catch(() => ({ data: null }))
          : Promise.resolve({ data: null }),
        API.get("/dashboard/alerts").catch(() => ({ data: { alerts: [] } })),
      ]);

      currentSession = sess;
      data = pickDash(dashRes, data);
      sessionSummary = summaryRes.data;
      alerts = alertsRes.data?.alerts || [];
      lastLoadedAt = Date.now();
    } catch (e) {
      console.error(e);
    }
  }

  async function loadDeltas() {
    deltaLoading = true;
    try {
      const res = await API.get(`/dashboard/metric-deltas?period=${deltaPeriod}`);
      deltas = res.data;
    } catch (e) {
      console.error(e);
    } finally {
      deltaLoading = false;
    }
  }

  // Refresh headline metrics and comparison deltas from the same selected period.
  async function setDeltaPeriod(p) {
    if (deltaPeriod === p) return;

    deltaPeriod = p;
    deltaLoading = true;

    try {
      const [dashRes, deltaRes] = await Promise.all([
        API.get(dashboardUrl(currentSession, p)),
        API.get(`/dashboard/metric-deltas?period=${p}`),
      ]);

      const nextDashboardData = Array.isArray(dashRes.data)
        ? dashRes.data[0]
        : dashRes.data;

      if (nextDashboardData) {
        data = nextDashboardData;
      }
      deltas = deltaRes.data;
    } catch (e) {
      console.error("Failed to update dashboard period:", e);
    } finally {
      deltaLoading = false;
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
        key: "profit_margin",
        label: "Profit margin",
        points: c.profit_margin_points ?? 0,
        max: 40,
        value: `${c.profit_margin_pct ?? 0}%`,
        rule: "40 pts if ≥30% · 25 if ≥15% · 10 if >0% · 0 if losing money",
        explainer:
          "Of every 100 MWK you sell, how much stays as profit after paying for the goods and daily expenses. Higher is better — it means you're pricing right.",
      },
      {
        key: "cash_flow",
        label: "Cash flow",
        points: c.cash_flow_points ?? 0,
        max: 30,
        value: `${Math.round((c.cash_flow_ratio ?? 0) * 100)}%`,
        rule: "Score scales with profit as a share of revenue",
        explainer:
          "Whether money is actually flowing in vs going out. If profit stays a healthy fraction of revenue, cash flow is good. If revenue is high but profit is close to zero, this stays low even if the margin looks okay.",
      },
      {
        key: "stock_health",
        label: "Stock health",
        points: c.stock_points ?? 0,
        max: 20,
        value: `${c.healthy_products ?? 0}/${c.total_products ?? 0}`,
        rule: `Falls as more products go below their low-stock threshold (${c.low_stock ?? 0} low right now)`,
        explainer:
          "Percentage of your products that have healthy stock. If too many products are low or out of stock, you're losing sales you could have made.",
      },
      {
        key: "debt_collection",
        label: "Debt collection",
        points: c.debt_points ?? 0,
        max: 10,
        value: `${Math.round((c.collection_ratio ?? 1) * 100)}%`,
        rule: "10 pts if you collect 100% of 7-day credit sales, scaling down from there",
        explainer:
          "How much of the credit you extended in the last week has actually come back. If customers who bought on credit haven't paid, this drops — and so does your cash flow.",
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
  {:else if isEmptyShop}
    <EmptyState
      icon={Package}
      title="Welcome to your shop!"
      message="Add your first product to get started. Then open a session and make your first sale — this dashboard will fill in automatically."
      primaryLabel="Add your first product"
      primaryAction={() => (window.location.href = "/products?add=1")}
      secondaryLabel="Open a session"
      secondaryAction={() => (window.location.href = "/sessions")}
    />
  {:else}
    <div class="dashboard">
      <!-- ── Session banner (above the session card) ── -->
      {#if currentSession}
        <div class="session-info">
          <Calendar size={16} strokeWidth={1.75} />
          <span>
            Showing data for session opened
            <strong>{new Date(currentSession.opened_at).toLocaleString()}</strong>
          </span>
        </div>
      {/if}

      <!-- ── Session summary card (top of dashboard when a session exists) ── -->
      {#if sessionSummary}
        <div class="session-summary-card" class:active-session={sessionSummary.is_active}>
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
            <div class="ss-cell profit">
              <span class="ss-label">Profit</span>
              <span class="ss-value">MWK {formatMoney(sessionProfit)}</span>
            </div>
            <div class="ss-cell highlight">
              <span class="ss-label">Expected in drawer</span>
              <span class="ss-value">
                MWK {formatMoney(sessionSummary.cash_drawer.expected_in_drawer)}
   
