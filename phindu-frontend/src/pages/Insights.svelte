<script>
  import { onMount, onDestroy } from "svelte";
  import { fade } from "svelte/transition";
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
    ChevronLeft,
    ChevronRight,
    ChevronDown,
    Sparkles,
    Tags,
    Layers,
    AlertTriangle,
    Loader2,
    ShoppingBasket,
    ArrowRight,
    Target,
    Wallet,
    Users,
    Zap,
    Rocket,
    Lightbulb,
  } from "lucide-svelte";
  import Layout from "../components/Layout.svelte";
  import API from "../api/api";
  import ExpenseDrilldownModal from "../components/ExpenseDrilldownModal.svelte";
  import Delta from "../components/Delta.svelte";
  import * as XLSX from "xlsx";

  // ── State ──
  let period = "week";
  let loading = true;
  let error = null;
  let summary = null;

  let priceChangeRange = "30";
  let priceChanges = [];
  let priceChangesLoading = false;

  let marketBasket = null;
  let marketBasketLoading = false;
  let marketBasketError = null;
  let mbPeriod = "month";
  let mbMinSupport = 3;

  const PAGE_SIZE = 10;
  let marginPage = 0;
  let expensePage = 0;
  let drilldownCategory = null;

  // section expand/collapse (defaults tuned for the new order)
  let openSections = {
    margins: false,
    price: false,
    top: false,
    marketBasket: true,
    peak: true,
    expenses: true,
  };
  function toggle(section) {
    openSections = { ...openSections, [section]: !openSections[section] };
  }

  // ── Fetchers ──
  async function fetchSummary() {
    loading = true;
    error = null;
    try {
      const res = await API.get(`/analytics/summary?period=${period}`);
      summary = res.data;
      marginPage = 0;
      expensePage = 0;
    } catch (err) {
      error = "Failed to load insights";
      console.error(err);
    } finally {
      loading = false;
    }
  }

  function normalizePriceChanges(raw) {
    if (Array.isArray(raw?.recent_price_changes_v2)) {
      return raw.recent_price_changes_v2;
    }
    if (Array.isArray(raw?.recent_price_changes)) {
      return raw.recent_price_changes.map((entry) => {
        const costCh = entry.changes.find((c) => c.price_type === "purchase") || null;
        const sellCh = entry.changes.find((c) => c.price_type === "selling") || null;
        return {
          product: entry.product,
          last_cost_change: costCh,
          last_sell_change: sellCh,
          changes: entry.changes,
        };
      });
    }
    return [];
  }

  async function fetchPriceChanges() {
    priceChangesLoading = true;
    try {
      let items;
      try {
        const params = {};
        if (priceChangeRange !== "all") params.days = Number(priceChangeRange);
        const res = await API.get("/analytics/price-changes", { params });
        items = res.data || [];
      } catch (e) {
        if (summary) {
          items = normalizePriceChanges(summary);
        } else {
          const res = await API.get(`/analytics/summary?period=${period}`);
          items = normalizePriceChanges(res.data);
        }
      }

      if (priceChangeRange !== "all") {
        const cutoff = Date.now() - Number(priceChangeRange) * 24 * 60 * 60 * 1000;
        items = items.filter((entry) => {
          const ts =
            entry.last_cost_change?.changed_at ||
            entry.last_sell_change?.changed_at ||
            entry.changes?.[0]?.changed_at;
          return ts ? new Date(ts).getTime() >= cutoff : true;
        });
      }
      priceChanges = items;
    } catch (e) {
      console.error("Price changes fetch failed:", e);
      priceChanges = [];
    } finally {
      priceChangesLoading = false;
    }
  }

  async function fetchMarketBasket() {
    marketBasketLoading = true;
    marketBasketError = null;
    try {
      const res = await API.get("/analytics/market-basket", {
        params: { period: mbPeriod, min_support: mbMinSupport, limit: 10 },
      });
      marketBasket = res.data;
    } catch (e) {
      if (summary?.market_basket) {
        marketBasket = summary.market_basket;
      } else {
        marketBasketError = "Could not load market basket analysis";
        marketBasket = null;
      }
    } finally {
      marketBasketLoading = false;
    }
  }

  async function refreshAll() {
    await Promise.all([fetchSummary(), fetchPriceChanges(), fetchMarketBasket()]);
  }

  // ── Lifecycle ──
  let pollId = null;
  function handleVisibility() {
    if (document.visibilityState === "visible") refreshAll();
  }
  onMount(() => {
    refreshAll();
    document.addEventListener("visibilitychange", handleVisibility);
    pollId = setInterval(() => {
      if (document.visibilityState === "visible") {
        fetchPriceChanges();
        fetchMarketBasket();
      }
    }, 60000);
    return () => {
      document.removeEventListener("visibilitychange", handleVisibility);
      if (pollId) clearInterval(pollId);
    };
  });
  onDestroy(() => {
    if (pollId) clearInterval(pollId);
  });

  $: if (period) fetchSummary();

  // ── Exports ──
  async function exportSales() {
    const res = await API.get("/sales/?limit=200");
    const raw = res.data;
    const salesArr = Array.isArray(raw) ? raw : raw.sales || [];
    const data = salesArr.map((s) => ({
      Products: (s.products || []).join(", "),
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

  // ── Helpers ──
  function formatDate(iso) {
    if (!iso) return "—";
    return new Date(iso).toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
    });
  }
  function fmt(n) {
    return Number(n || 0).toLocaleString(undefined, { maximumFractionDigits: 0 });
  }
  function fmtShort(n) {
    const num = Number(n || 0);
    if (Math.abs(num) >= 1_000_000) return (num / 1_000_000).toFixed(1) + "M";
    if (Math.abs(num) >= 1_000) return (num / 1_000).toFixed(0) + "k";
    return num.toFixed(0);
  }
  function openDrilldown(category) {
    drilldownCategory = category || "Uncategorized";
  }
  function closeDrilldown() {
    drilldownCategory = null;
  }

  // ── Derived ──
  $: wg = summary?.week_glance;
  $: margins = summary?.profit_margins || [];
  $: marginPageCount = Math.max(1, Math.ceil(margins.length / PAGE_SIZE));
  $: pagedMargins = margins.slice(marginPage * PAGE_SIZE, (marginPage + 1) * PAGE_SIZE);

  $: expenses = summary?.expense_breakdown || [];
  $: expensePageCount = Math.max(1, Math.ceil(expenses.length / PAGE_SIZE));
  $: pagedExpenses = expenses.slice(expensePage * PAGE_SIZE, (expensePage + 1) * PAGE_SIZE);

  $: categoryPerf = summary?.category_performance || [];
  $: topDetailed = summary?.top_products_detailed || [];
  $: lowStock = summary?.low_stock || [];

  $: netWeek =
    (wg?.revenue?.current || 0) - (summary?.week_expenses || 0);

  // ── Heatmap: prefer server grid, fall back to client-side from peak_hours ──
  const WEEKDAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

  $: peakGrid = (() => {
    if (Array.isArray(summary?.peak_grid) && summary.peak_grid.length === 7) {
      return summary.peak_grid;
    }
    // fallback: derive from old peak_hours only (all rows same)
    const ph = summary?.peak_hours;
    if (!Array.isArray(ph) || ph.length === 0) return null;
    const grid = Array.from({ length: 7 }, () => Array(24).fill(0));
    // we can't know weekday split client-side from peak_hours; show as "All days"
    return null;
  })();

  $: peakHoursOnly = Array.isArray(summary?.peak_hours) ? summary.peak_hours : null;

  // Determine the active hours range to render (trim dead space)
  $: activeHourRange = (() => {
    const src = peakGrid
      ? peakGrid.flat()
      : peakHoursOnly || [];
    if (src.length === 0) return { start: 6, end: 20 };
    let first = 24, last = -1;
    for (let h = 0; h < 24; h++) {
      const v = peakGrid
        ? peakGrid.reduce((s, row) => s + row[h], 0)
        : (peakHoursOnly?.[h] ?? 0);
      if (v > 0) {
        if (h < first) first = h;
        if (h > last) last = h;
      }
    }
    if (first === 24) return { start: 6, end: 20 };
    return { start: Math.max(0, first - 1), end: Math.min(23, last + 1) };
  })();

  $: peakMax = (() => {
    const flat = peakGrid ? peakGrid.flat() : peakHoursOnly || [];
    return Math.max(1, ...flat);
  })();

  $: peakTotalsByDay = (() => {
    if (!peakGrid) return null;
    return peakGrid.map((row) => row.reduce((s, v) => s + v, 0));
  })();

  $: bestDay = (() => {
    if (!peakTotalsByDay) return null;
    let idx = 0;
    for (let i = 1; i < 7; i++) if (peakTotalsByDay[i] > peakTotalsByDay[idx]) idx = i;
    if (peakTotalsByDay[idx] === 0) return null;
    return { label: WEEKDAY_LABELS[idx], count: peakTotalsByDay[idx] };
  })();

  $: peakSlot = (() => {
    if (!peakGrid) return null;
    let best = { v: 0, day: 0, hour: 0 };
    for (let d = 0; d < 7; d++) {
      for (let h = 0; h < 24; h++) {
        if (peakGrid[d][h] > best.v) best = { v: peakGrid[d][h], day: d, hour: h };
      }
    }
    if (best.v === 0) return null;
    return {
      label: `${WEEKDAY_LABELS[best.day]} ${best.hour}:00–${best.hour + 1}:00`,
      count: best.v,
    };
  })();

  $: deadSlots = (() => {
    if (!peakGrid) return [];
    // find weekday×hour slots with 0 sales that are between the first and last active hour of that weekday
    const dead = [];
    for (let d = 0; d < 7; d++) {
      const row = peakGrid[d];
      let first = -1, last = -1;
      for (let h = 0; h < 24; h++) {
        if (row[h] > 0) {
          if (first === -1) first = h;
          last = h;
        }
      }
      if (first === -1) continue;
      for (let h = first + 1; h < last; h++) {
        if (row[h] === 0) dead.push({ day: WEEKDAY_LABELS[d], hour: h });
      }
    }
    return dead.slice(0, 3);
  })();

  // ── Best / worst margins ──
  $: bestWorst = (() => {
    if (margins.length === 0) return null;
    return {
      best: margins[0],
      worst: margins[margins.length - 1],
      count: margins.length,
    };
  })();

  // ── Cost-shock detector: join price changes to current margins ──
  $: costShocks = (() => {
    if (priceChanges.length === 0 || margins.length === 0) return [];
    const marginByName = {};
    margins.forEach((m) => (marginByName[m.name] = m));
    const hits = [];
    priceChanges.forEach((entry) => {
      const c = entry.last_cost_change;
      if (!c || !c.change_percent || c.change_percent <= 0) return;
      const name = entry.product?.name;
      const m = marginByName[name];
      if (!m) return;
      hits.push({
        name,
        costUpPct: c.change_percent,
        marginNow: m.margin_percent,
        marginAtRisk: Math.max(0, m.margin_percent - c.change_percent * 0.5),
      });
    });
    hits.sort((a, b) => b.costUpPct - a.costUpPct);
    return hits.slice(0, 3);
  })();

  // ── Action list ──
  $: actions = (() => {
    const out = [];
    // 1. restock
    if (lowStock.length > 0) {
      out.push({
        kind: "restock",
        severity: lowStock.length >= 3 ? "high" : "medium",
        title: `Restock ${lowStock.length} product${lowStock.length === 1 ? "" : "s"}`,
        detail: lowStock.slice(0, 3).map((p) => p.name).join(", "),
        cta: "Open Products",
        link: "/products?filter=low_stock",
      });
    }
    // 2. cost shock
    if (costShocks.length > 0) {
      const top = costShocks[0];
      out.push({
        kind: "margin",
        severity: "high",
        title: `${top.name} cost up ${top.costUpPct.toFixed(0)}%`,
        detail: `Margin now ${top.marginNow.toFixed(1)}% — consider raising price`,
        cta: "View price changes",
        action: () => toggle("price"),
      });
    }
    // 3. revenue down
    if ((wg?.revenue?.percent ?? 0) <= -10) {
      out.push({
        kind: "revenue",
        severity: "medium",
        title: `Revenue down ${Math.abs(wg.revenue.percent).toFixed(0)}% vs last period`,
        detail: `MWK ${fmt(wg.revenue.current)} vs MWK ${fmt(wg.revenue.previous)}`,
        cta: "See categories",
        action: () => scrollToSection("category-perf"),
      });
    }
    // 4. best margin product to push
    if (bestWorst && bestWorst.count > 1 && bestWorst.best.margin_percent > 20) {
      out.push({
        kind: "growth",
        severity: "low",
        title: `Push ${bestWorst.best.name}`,
        detail: `Highest margin at ${bestWorst.best.margin_percent.toFixed(1)}% — good upsell candidate`,
        cta: "See margin",
        action: () => toggle("margins"),
      });
    }
    // 5. pairing opportunity
    if (marketBasket?.pairs?.length > 0) {
      const top = marketBasket.pairs[0];
      out.push({
        kind: "basket",
        severity: "low",
        title: `Bundle ${top.product_a.name} + ${top.product_b.name}`,
        detail: `Bought together ${top.co_count}× — try a combo price`,
        cta: "See basket",
        action: () => scrollToSection("basket"),
      });
    }
    return out;
  })();

  function scrollToSection(id) {
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  // ── Projection ──
  $: projection = (() => {
    const current = wg?.revenue?.current;
    const previous = wg?.revenue?.previous;
    if (current == null) return null;
    const days = period === "day" ? 1 : period === "week" ? 7 : 30;
    const dailyAvg = current / days;
    const monthlyProjected = dailyAvg * 30;
    const trendPct = previous != null && previous > 0
      ? ((current - previous) / previous) * 100
      : null;
    return { dailyAvg, monthlyProjected, trendPct };
  })();

  function prevMargin() { if (marginPage > 0) marginPage -= 1; }
  function nextMargin() { if (marginPage < marginPageCount - 1) marginPage += 1; }
  function prevExpense() { if (expensePage > 0) expensePage -= 1; }
  function nextExpense() { if (expensePage < expensePageCount - 1) expensePage += 1; }

  function heatColor(count) {
    if (!count || peakMax === 0) return "rgba(15, 107, 62, 0.04)";
    const i = Math.sqrt(count / peakMax);
    return `rgba(15, 107, 62, ${0.1 + i * 0.85})`;
  }
</script>

<Layout title="Insights">
  <div class="insights-page">
    <!-- ── Header ── -->
    <div class="page-header">
      <div class="header-title">
        <h2>
          <BarChart3 size={22} strokeWidth={2} />
          Business Insights
        </h2>
        {#if summary}
          <span class="timestamp">
            Updated {new Date(summary.generated_at).toLocaleTimeString()}
          </span>
        {/if}
      </div>
      <div class="header-actions">
        <div class="segmented" role="group" aria-label="Period">
          {#each [["day", "Today"], ["week", "This Week"], ["month", "This Month"]] as [val, label]}
            <button
              type="button"
              class:active={period === val}
              on:click={() => (period = val)}
            >
              {label}
            </button>
          {/each}
        </div>
        <button
          class="icon-btn"
          on:click={refreshAll}
          title="Refresh"
          aria-label="Refresh insights"
          type="button"
        >
          <RefreshCw size={16} class={loading ? "spin" : ""} />
        </button>
      </div>
    </div>

    {#if loading && !summary}
      <div class="state-box">
        <div class="spinner"></div>
        <p>Loading insights...</p>
      </div>
    {:else if error && !summary}
      <div class="state-box error">
        <p>{error}</p>
        <button class="btn btn-primary" on:click={refreshAll} type="button">
          <RefreshCw size={16} strokeWidth={2} /> Retry
        </button>
      </div>
    {:else if summary}
      <!-- ══════════════════════════════════════════════════════════ -->
      <!-- 1. WHERE AM I — KPI strip with WoW change                 -->
      <!-- ══════════════════════════════════════════════════════════ -->
      {#if wg}
        <div class="kpi-grid">
          <div class="kpi-card">
            <div class="kpi-head">
              <Wallet size={16} strokeWidth={2} />
              <span>Revenue</span>
            </div>
            <strong class="kpi-big">MWK {fmtShort(wg.revenue.current)}</strong>
            <div class="kpi-foot">
              <Delta pct={wg.revenue.percent} />
              <span class="kpi-compare">vs {fmtShort(wg.revenue.previous)}</span>
            </div>
          </div>

          <div class="kpi-card">
            <div class="kpi-head">
              <PiggyBank size={16} strokeWidth={2} />
              <span>Profit</span>
            </div>
            <strong class="kpi-big">MWK {fmtShort(wg.profit.current)}</strong>
            <div class="kpi-foot">
              <Delta pct={wg.profit.percent} />
              <span class="kpi-compare">vs {fmtShort(wg.profit.previous)}</span>
            </div>
          </div>

          <div class="kpi-card">
            <div class="kpi-head">
              <Receipt size={16} strokeWidth={2} />
              <span>Sales</span>
            </div>
            <strong class="kpi-big">{wg.sales_count.current}</strong>
            <div class="kpi-foot">
              <Delta pct={wg.sales_count.percent} />
              <span class="kpi-compare">vs {wg.sales_count.previous}</span>
            </div>
          </div>

          <div class="kpi-card">
            <div class="kpi-head">
              <Target size={16} strokeWidth={2} />
              <span>Avg Sale</span>
            </div>
            <strong class="kpi-big">MWK {fmtShort(wg.avg_sale.current)}</strong>
            <div class="kpi-foot">
              <Delta pct={wg.avg_sale.percent} />
              <span class="kpi-compare">vs {fmtShort(wg.avg_sale.previous)}</span>
            </div>
          </div>
        </div>

        <!-- Cash line -->
        <div class="cash-line">
          <div class="cash-item income">
            <span>Money in</span>
            <strong>MWK {fmt(netWeek + (summary.week_expenses || 0))}</strong>
          </div>
          <div class="cash-item expense">
            <span>Money out</span>
            <strong>MWK {fmt(summary.week_expenses || 0)}</strong>
          </div>
          <div class="cash-item net" class:negative={netWeek < 0}>
            <span>Left over</span>
            <strong>MWK {fmt(netWeek)}</strong>
          </div>
          {#if projection}
            <div class="cash-item projection">
              <span>Next 30 days</span>
              <strong>≈ MWK {fmtShort(projection.monthlyProjected)}</strong>
            </div>
          {/if}
        </div>
      {/if}

      <!-- ══════════════════════════════════════════════════════════ -->
      <!-- 2. WHAT TO DO — action list                              -->
      <!-- ══════════════════════════════════════════════════════════ -->
      {#if actions.length > 0}
        <section class="action-section">
          <h3 class="section-title">
            <Zap size={18} strokeWidth={2} />
            What to do
          </h3>
          <div class="action-list">
            {#each actions as a}
              <div class="action-row tone-{a.severity}">
                <div class="action-icon">
                  {#if a.kind === "restock"}
                    <Package size={18} strokeWidth={2} />
                  {:else if a.kind === "margin"}
                    <PiggyBank size={18} strokeWidth={2} />
                  {:else if a.kind === "revenue"}
                    <TrendingDown size={18} strokeWidth={2} />
                  {:else if a.kind === "growth"}
                    <Rocket size={18} strokeWidth={2} />
                  {:else}
                    <ShoppingBasket size={18} strokeWidth={2} />
                  {/if}
                </div>
                <div class="action-main">
                  <strong class="action-title">{a.title}</strong>
                  <span class="action-detail">{a.detail}</span>
                </div>
                {#if a.link}
                  <a class="action-cta" href={a.link}>
                    {a.cta} <ArrowRight size={14} />
                  </a>
                {:else if a.action}
                  <button class="action-cta" on:click={a.action} type="button">
                    {a.cta} <ArrowRight size={14} />
                  </button>
                {/if}
              </div>
            {/each}
          </div>
        </section>
      {/if}

      <!-- ══════════════════════════════════════════════════════════ -->
      <!-- 3. HOW DID I GET HERE — categories + busiest slots        -->
      <!-- ══════════════════════════════════════════════════════════ -->

      <!-- Category performance -->
      <section class="card" id="category-perf">
        <div class="card-header">
          <h3>
            <Tags size={18} strokeWidth={2} />
            Where revenue comes from
          </h3>
        </div>
        {#if categoryPerf.length === 0}
          <p class="empty-text">No category sales in this period.</p>
        {:else}
          <div class="cat-perf-list">
            {#each categoryPerf as cat}
              <div class="cp-row">
                <div class="cp-top">
                  <strong class="cp-name">{cat.category}</strong>
                  <span class="cp-rev">MWK {fmt(cat.revenue)}</span>
                </div>
                <div class="cp-bar-wrap">
                  <div
                    class="cp-bar"
                    style="width: {Math.min(100, cat.revenue_percent || 0)}%"
                  ></div>
                </div>
                <div class="cp-meta">
                  <span>{cat.revenue_percent}% of revenue</span>
                  <span>{cat.quantity} units · {cat.sale_count} sale{cat.sale_count === 1 ? "" : "s"}</span>
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </section>

      <!-- Busiest slots: day × hour heatmap -->
      <section class="card" id="busiest">
        <div class="card-header">
          <h3>
            <Clock size={18} strokeWidth={2} />
            When you're busiest
          </h3>
          <button
            class="icon-btn small"
            on:click={() => toggle("peak")}
            aria-label="Toggle busiest slots section"
            type="button"
          >
            <ChevronDown size={14} class={!openSections.peak ? "rotated" : ""} />
          </button>
        </div>

        {#if openSections.peak}
          {#if peakGrid}
            <div class="peak-hints">
              {#if bestDay}
                <div class="peak-hint-chip">
                  <Trophy size={12} /> Busiest day: <strong>{bestDay.label}</strong>
                  <span>({bestDay.count} sales)</span>
                </div>
              {/if}
              {#if peakSlot}
                <div class="peak-hint-chip">
                  <Zap size={12} /> Peak slot: <strong>{peakSlot.label}</strong>
                  <span>({peakSlot.count} sales)</span>
                </div>
              {/if}
              {#if deadSlots.length > 0}
                <div class="peak-hint-chip warn">
                  <AlertTriangle size={12} /> Dead slots:
                  {#each deadSlots as d, i}
                    {d.day} {d.hour}:00{#if i < deadSlots.length - 1}, {/if}
                  {/each}
                </div>
              {/if}
            </div>

            <div class="heatmap-wrapper">
              <div class="heatmap-grid" style="--hours: {activeHourRange.end - activeHourRange.start + 1}">
                <!-- hour header -->
                <div class="heat-corner"></div>
                {#each Array(activeHourRange.end - activeHourRange.start + 1) as _, i}
                  {@const h = activeHourRange.start + i}
                  <div class="heat-hour">{h}</div>
                {/each}

                <!-- rows -->
                {#each peakGrid as row, dayIdx}
                  <div class="heat-day">{WEEKDAY_LABELS[dayIdx]}</div>
                  {#each Array(activeHourRange.end - activeHourRange.start + 1) as _, i}
                    {@const h = activeHourRange.start + i}
                    {@const count = row[h]}
                    <div
                      class="heat-cell"
                      class:peak={count === peakMax && count > 0}
                      style="background: {heatColor(count)};"
                      title="{WEEKDAY_LABELS[dayIdx]} {h}:00 — {count} sale{count === 1 ? '' : 's'}"
                    ></div>
                  {/each}
                {/each}
              </div>
            </div>
            <p class="chart-hint">
              Darker = more sales. Only active hours shown ({activeHourRange.start}:00–{activeHourRange.end + 1}:00).
            </p>
          {:else if peakHoursOnly}
            <!-- fallback: old single-row bar chart if server doesn't send peak_grid -->
            <div class="legacy-hours">
              {#each peakHoursOnly as count, hour}
                <div class="peak-bar-container">
                  <div class="peak-bar" style="height: {Math.max(3, (count / peakMax) * 100)}%">
                    {#if count > 0}<span class="peak-value">{count}</span>{/if}
                  </div>
                  <span class="peak-label">{hour}</span>
                </div>
              {/each}
            </div>
            <p class="chart-hint">
              Bars show sales count per hour. To see the weekday breakdown, enable <code>peak_grid</code> in the analytics endpoint.
            </p>
          {:else}
            <p class="empty-text">No sales data for this period.</p>
          {/if}
        {/if}
      </section>

      <!-- ══════════════════════════════════════════════════════════ -->
      <!-- 4. WHAT'S NEXT — margin risk, basket, top products       -->
      <!-- ══════════════════════════════════════════════════════════ -->

      <!-- Margin risk / cost shocks -->
      {#if costShocks.length > 0}
        <section class="card risk-card">
          <div class="card-header">
            <h3>
              <AlertTriangle size={18} strokeWidth={2} />
              Margin at risk
            </h3>
          </div>
          <p class="risk-hint">
            Recent cost increases are eating into your margin. Consider raising prices.
          </p>
          <div class="risk-list">
            {#each costShocks as s}
              <div class="risk-row">
                <div class="risk-main">
                  <strong>{s.name}</strong>
                  <span class="risk-meta">
                    Cost up <strong class="risk-cost">+{s.costUpPct.toFixed(1)}%</strong>
                    · margin now <strong>{s.marginNow.toFixed(1)}%</strong>
                  </span>
                </div>
                <span class="risk-badge">Check price</span>
              </div>
            {/each}
          </div>
        </section>
      {/if}

      <!-- Market basket — simplified -->
      <section class="card" id="basket" class:collapsed={!openSections.marketBasket}>
        <div class="card-header">
          <h3>
            <ShoppingBasket size={18} strokeWidth={2} />
            What sells together
          </h3>
          <div class="card-actions">
            <select bind:value={mbPeriod} on:change={fetchMarketBasket} class="small-select">
              <option value="week">This Week</option>
              <option value="month">This Month</option>
              <option value="all">All Time</option>
            </select>
            <button
              class="icon-btn small"
              on:click={() => toggle("marketBasket")}
              aria-label="Toggle market basket section"
              type="button"
            >
              <ChevronDown size={14} class={!openSections.marketBasket ? "rotated" : ""} />
            </button>
          </div>
        </div>

        {#if openSections.marketBasket}
          {#if marketBasketLoading && !marketBasket}
            <div class="state-inline">
              <Loader2 size={16} class="spin" /> Analysing baskets…
            </div>
          {:else if marketBasketError}
            <p class="empty-text">{marketBasketError}</p>
          {:else if !marketBasket || marketBasket.pairs.length === 0}
            <p class="empty-text">
              Not enough multi-item transactions in this period yet.
            </p>
          {:else}
            <p class="basket-hint">
              <Lightbulb size={14} /> Display these together or bundle them — customers already buy them as a pair.
            </p>
            <div class="mb-list">
              {#each marketBasket.pairs.slice(0, 5) as pair, i}
                <div class="mb-row" class:top={i === 0}>
                  <div class="mb-pair">
                    <span class="mb-product" title={pair.product_a.name}>
                      {pair.product_a.name}
                    </span>
                    <span class="mb-plus">+</span>
                    <span class="mb-product" title={pair.product_b.name}>
                      {pair.product_b.name}
                    </span>
                  </div>
                  <div class="mb-stats">
                    <span class="mb-stat">
                      <strong>{pair.co_count}×</strong> together
                    </span>
                  </div>
                </div>
              {/each}
            </div>
          {/if}
        {/if}
      </section>

      <!-- Top 5 products -->
      <section class="card" class:collapsed={!openSections.top}>
        <div class="card-header">
          <h3>
            <Trophy size={18} strokeWidth={2} />
            What's selling
          </h3>
          <button
            class="icon-btn small"
            on:click={() => toggle("top")}
            aria-label="Toggle top products section"
            type="button"
          >
            <ChevronDown size={14} class={!openSections.top ? "rotated" : ""} />
          </button>
        </div>
        {#if openSections.top}
          {#if topDetailed.length === 0}
            <p class="empty-text">No sales data for this period.</p>
          {:else}
            <div class="top-list">
              {#each topDetailed as product, i}
                <div class="top-row">
                  <span class="top-rank">{i + 1}</span>
                  <div class="top-main">
                    <div class="top-name-line">
                      <strong>{product.name}</strong>
                      {#if product.is_variant && product.parent_name}
                        <span class="parent-tag">
                          <Layers size={11} strokeWidth={2} /> {product.parent_name}
                        </span>
                      {/if}
                    </div>
                    {#if product.category}
                      <div class="top-meta">
                        <span class="cat-chip">{product.category}</span>
                      </div>
                    {/if}
                  </div>
                  <div class="top-qty">
                    <strong>{product.quantity}</strong>
                    <span>units</span>
                  </div>
                </div>
              {/each}
            </div>
          {/if}
        {/if}
      </section>

      <!-- ══════════════════════════════════════════════════════════ -->
      <!-- 5. DRILL-DOWN DETAILS (collapsed by default)             -->
      <!-- ══════════════════════════════════════════════════════════ -->

      <!-- Profit margins -->
      <section class="card" class:collapsed={!openSections.margins}>
        <div class="card-header">
          <h3>
            <PiggyBank size={18} strokeWidth={2} />
            Profit margin by product
          </h3>
          <button
            class="icon-btn small"
            on:click={() => toggle("margins")}
            aria-label="Toggle profit margins section"
            type="button"
          >
            <ChevronDown size={14} class={!openSections.margins ? "rotated" : ""} />
          </button>
        </div>
        {#if openSections.margins}
          {#if bestWorst && bestWorst.count > 1}
            <div class="best-worst-row">
              <div class="bw-cell best">
                <span>Best margin</span>
                <strong>{bestWorst.best.name}</strong>
                <span class="bw-pct">{bestWorst.best.margin_percent.toFixed(1)}%</span>
              </div>
              <div class="bw-cell worst">
                <span>Worst margin</span>
                <strong>{bestWorst.worst.name}</strong>
                <span class="bw-pct">{bestWorst.worst.margin_percent.toFixed(1)}%</span>
              </div>
            </div>
          {/if}

          {#if margins.length === 0}
            <p class="empty-text">No sales data available.</p>
          {:else}
            <div class="table-wrapper margin-table-wrap">
              <table class="margin-table">
                <thead>
                  <tr>
                    <th>Product</th>
                    <th class="num">Revenue</th>
                    <th class="num">Cost</th>
                    <th class="num">Profit</th>
                    <th class="num">Margin</th>
                  </tr>
                </thead>
                <tbody>
                  {#each pagedMargins as item}
                    <tr>
                      <td class="name-cell">{item.name}</td>
                      <td class="num">{fmt(item.revenue)}</td>
                      <td class="num">{fmt(item.cost)}</td>
                      <td class="num">{fmt(item.profit)}</td>
                      <td class="num margin-value">{item.margin_percent}%</td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>

            <div class="margin-cards">
              {#each pagedMargins as item}
                <div class="margin-card">
                  <div class="mc-header">
                    <strong>{item.name}</strong>
                    <span class="mc-margin">{item.margin_percent}%</span>
                  </div>
                  <div class="mc-row"><span>Revenue</span><span>MWK {fmt(item.revenue)}</span></div>
                  <div class="mc-row"><span>Cost</span><span>MWK {fmt(item.cost)}</span></div>
                  <div class="mc-row"><span>Profit</span><span class="mc-profit">MWK {fmt(item.profit)}</span></div>
                </div>
              {/each}
            </div>

            {#if marginPageCount > 1}
              <div class="pagination">
                <button class="page-btn" on:click={prevMargin} disabled={marginPage === 0} type="button" aria-label="Previous page">
                  <ChevronLeft size={16} />
                </button>
                <span class="page-info">
                  {marginPage * PAGE_SIZE + 1}–{Math.min((marginPage + 1) * PAGE_SIZE, margins.length)}
                  of {margins.length}
                </span>
                <button class="page-btn" on:click={nextMargin} disabled={marginPage >= marginPageCount - 1} type="button" aria-label="Next page">
                  <ChevronRight size={16} />
                </button>
              </div>
            {/if}
          {/if}
        {/if}
      </section>

      <!-- Price changes -->
      <section class="card" class:collapsed={!openSections.price}>
        <div class="card-header">
          <h3>
            <Bell size={18} strokeWidth={2} />
            Price changes
          </h3>
          <div class="card-actions">
            <select
              bind:value={priceChangeRange}
              on:change={fetchPriceChanges}
              class="small-select"
            >
              <option value="7">Last 7 days</option>
              <option value="30">Last 30 days</option>
              <option value="90">Last 90 days</option>
              <option value="all">All time</option>
            </select>
            <button
              class="icon-btn small"
              on:click={() => toggle("price")}
              title="Toggle section"
              aria-label="Toggle price changes section"
              type="button"
            >
              <ChevronDown size={14} class={!openSections.price ? "rotated" : ""} />
            </button>
          </div>
        </div>

        {#if openSections.price}
          {#if priceChangesLoading}
            <div class="state-inline">
              <Loader2 size={16} class="spin" /> Loading…
            </div>
          {:else if priceChanges.length === 0}
            <p class="empty-text">No price changes in this period.</p>
          {:else}
            <div class="price-changes-list">
              {#each priceChanges as entry}
                <div class="price-change-item">
                  <div class="product-header">
                    <strong>{entry.product?.name || "Unknown product"}</strong>
                    <span class="current-margin">
                      Current margin:
                      {entry.product?.current_margin_percent != null
                        ? `${entry.product.current_margin_percent.toFixed(1)}%`
                        : "—"}
                    </span>
                  </div>
                  <div class="changes-list">
                    {#if entry.last_cost_change}
                      {@const c = entry.last_cost_change}
                      <div class="change-line">
                        <span class="change-type purchase">COST</span>
                        <span class="change-values">
                          {#if c.old_price === null || c.old_price === 0}
                            Set to MWK {c.new_price?.toLocaleString()}
                          {:else}
                            MWK {c.old_price?.toLocaleString()} →
                            MWK {c.new_price?.toLocaleString()}
                          {/if}
                        </span>
                        {#if c.change_percent !== null && c.change_percent !== undefined}
                          {#if c.change_percent > 0}
                            <span class="pct up"><TrendingUp size={11} /> +{c.change_percent}%</span>
                          {:else if c.change_percent < 0}
                            <span class="pct down"><TrendingDown size={11} /> {c.change_percent}%</span>
                          {:else}
                            <span class="pct flat"><Minus size={11} /> 0%</span>
                          {/if}
                        {/if}
                        <span class="change-date">{formatDate(c.changed_at)}</span>
                      </div>
                    {:else}
                      <div class="change-line muted">
                        <span class="change-type purchase off">COST</span>
                        <span class="change-values muted">No change</span>
                      </div>
                    {/if}

                    {#if entry.last_sell_change}
                      {@const s = entry.last_sell_change}
                      <div class="change-line">
                        <span class="change-type selling">SELL</span>
                        <span class="change-values">
                          {#if s.old_price === null || s.old_price === 0}
                            Set to MWK {s.new_price?.toLocaleString()}
                          {:else}
                            MWK {s.old_price?.toLocaleString()} →
                            MWK {s.new_price?.toLocaleString()}
                          {/if}
                        </span>
                        {#if s.change_percent !== null && s.change_percent !== undefined}
                          {#if s.change_percent > 0}
                            <span class="pct up"><TrendingUp size={11} /> +{s.change_percent}%</span>
                          {:else if s.change_percent < 0}
                            <span class="pct down"><TrendingDown size={11} /> {s.change_percent}%</span>
                          {:else}
                            <span class="pct flat"><Minus size={11} /> 0%</span>
                          {/if}
                        {/if}
                        <span class="change-date">{formatDate(s.changed_at)}</span>
                      </div>
                    {:else}
                      <div class="change-line muted">
                        <span class="change-type selling off">SELL</span>
                        <span class="change-values muted">No change</span>
                      </div>
                    {/if}
                  </div>
                </div>
              {/each}
            </div>
          {/if}
        {/if}
      </section>

      <!-- Expenses -->
      <section class="card" class:collapsed={!openSections.expenses}>
        <div class="card-header">
          <h3>
            <Receipt size={18} strokeWidth={2} />
            Where money goes
          </h3>
          <button
            class="icon-btn small"
            on:click={() => toggle("expenses")}
            aria-label="Toggle expenses section"
            type="button"
          >
            <ChevronDown size={14} class={!openSections.expenses ? "rotated" : ""} />
          </button>
        </div>
        {#if openSections.expenses}
          {#if expenses.length === 0}
            <p class="empty-text">No expenses recorded.</p>
          {:else}
            <div class="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Category</th>
                    <th class="num">Amount</th>
                    <th class="action-col"></th>
                  </tr>
                </thead>
                <tbody>
                  {#each pagedExpenses as item}
                    <tr
                      class="clickable-row"
                      on:click={() => openDrilldown(item.category)}
                      on:keydown={(e) => e.key === "Enter" && openDrilldown(item.category)}
                      role="button"
                      tabindex="0"
                    >
                      <td>{item.category || "Uncategorized"}</td>
                      <td class="num">MWK {Number(item.total || 0).toFixed(2)}</td>
                      <td class="action-col"><ChevronRight size={16} strokeWidth={2} class="chev-icon" /></td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>

            {#if expensePageCount > 1}
              <div class="pagination">
                <button class="page-btn" on:click={prevExpense} disabled={expensePage === 0} type="button" aria-label="Previous page">
                  <ChevronLeft size={16} />
                </button>
                <span class="page-info">
                  {expensePage * PAGE_SIZE + 1}–{Math.min((expensePage + 1) * PAGE_SIZE, expenses.length)}
                  of {expenses.length}
                </span>
                <button class="page-btn" on:click={nextExpense} disabled={expensePage >= expensePageCount - 1} type="button" aria-label="Next page">
                  <ChevronRight size={16} />
                </button>
              </div>
            {/if}
          {/if}
        {/if}
      </section>

      <!-- Exports -->
      <div class="export-actions">
        <button class="btn" on:click={exportSales} type="button">
          <FileSpreadsheet size={16} strokeWidth={2} /> Export Sales
        </button>
        <button class="btn" on:click={exportProducts} type="button">
          <Package size={16} strokeWidth={2} /> Export Products
        </button>
      </div>
    {/if}
  </div>

  {#if drilldownCategory}
    {#key drilldownCategory}
      <div transition:fade={{ duration: 120 }}>
        <ExpenseDrilldownModal
          category={drilldownCategory}
          on:close={closeDrilldown}
        />
      </div>
    {/key}
  {/if}
</Layout>

<style>
  .insights-page {
    max-width: 960px;
    margin: 0 auto;
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
    overflow-x: hidden;
  }

  /* ── Header ── */
  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    flex-wrap: wrap;
    gap: 0.75rem;
  }
  .header-title {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
    min-width: 0;
  }
  .page-header h2 {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin: 0;
    font-size: 1.25rem;
    font-weight: 700;
    color: var(--text, #111827);
  }
  .timestamp {
    font-size: 0.75rem;
    color: var(--text-light, #6b7280);
    padding-left: 2rem;
  }
  .header-actions {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-wrap: wrap;
  }
  .icon-btn {
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 6px;
    padding: 0.35rem;
    cursor: pointer;
    color: var(--text-light, #6b7280);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    line-height: 0;
    transition: all 0.15s;
  }
  .icon-btn:hover {
    border-color: var(--primary, #0f6b3e);
    color: var(--primary, #0f6b3e);
  }
  .icon-btn.small { padding: 0.25rem; }
  .spin { animation: spin 0.9s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }

  .segmented {
    display: inline-flex;
    background: var(--background, #f3f4f6);
    border-radius: 8px;
    padding: 0.2rem;
    gap: 0.15rem;
    border: 1px solid var(--border, #e5e7eb);
  }
  .segmented button {
    background: transparent;
    border: none;
    padding: 0.4rem 0.8rem;
    border-radius: 6px;
    font-size: 0.82rem;
    font-weight: 600;
    cursor: pointer;
    color: var(--text-light, #6b7280);
    transition: all 0.15s;
    line-height: 1;
  }
  .segmented button.active {
    background: var(--surface, #fff);
    color: var(--primary, #0f6b3e);
    box-shadow: 0 1px 2px rgba(0,0,0,0.08);
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
  .state-inline {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.4rem;
    padding: 1.5rem 1rem;
    color: var(--text-light, #6b7280);
    font-size: 0.85rem;
  }
  .spinner {
    width: 28px;
    height: 28px;
    border: 3px solid var(--border, #e5e7eb);
    border-top-color: var(--primary, #0f6b3e);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  /* ── 1. KPI grid ── */
  .kpi-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 0.65rem;
  }
  .kpi-card {
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 12px;
    padding: 0.9rem 1rem;
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
    min-width: 0;
  }
  .kpi-head {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--text-light, #6b7280);
  }
  .kpi-head svg { color: var(--primary, #0f6b3e); }
  .kpi-big {
    font-size: 1.35rem;
    font-weight: 800;
    color: var(--text, #111827);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    line-height: 1.15;
  }
  .kpi-foot {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    flex-wrap: wrap;
  }
  .kpi-compare {
    font-size: 0.72rem;
    color: var(--text-light, #6b7280);
  }

  /* ── Cash line ── */
  .cash-line {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 0.55rem;
    padding: 0.75rem 0.9rem;
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 12px;
  }
  .cash-item {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
    padding: 0.55rem 0.7rem;
    border-radius: 9px;
    background: var(--background, #f9fafb);
    border: 1px solid var(--border, #e5e7eb);
  }
  .cash-item span {
    font-size: 0.68rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--text-light, #6b7280);
  }
  .cash-item strong {
    font-size: 1rem;
    font-weight: 700;
    color: var(--text, #111827);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .cash-item.income { background: #f0fdf4; border-color: #86efac; }
  .cash-item.income strong { color: #166534; }
  .cash-item.expense { background: #fef2f2; border-color: #fecaca; }
  .cash-item.expense strong { color: #991b1b; }
  .cash-item.net { background: #eef2ff; border-color: #c7d2fe; }
  .cash-item.net strong { color: #3730a3; }
  .cash-item.net.negative strong { color: #991b1b; }
  .cash-item.projection { background: #fefce8; border-color: #fde047; }
  .cash-item.projection strong { color: #854d0e; }

  /* ── 2. Action list ── */
  .action-section {
    display: flex;
    flex-direction: column;
    gap: 0.6rem;
  }
  .section-title {
    display: flex;
    align-items: center;
    gap: 0.45rem;
    margin: 0;
    font-size: 0.88rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-light, #6b7280);
  }
  .section-title svg { color: var(--primary, #0f6b3e); }
  .action-list {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }
  .action-row {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem 0.95rem;
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 10px;
    border-left: 4px solid var(--text-light, #9ca3af);
    flex-wrap: wrap;
  }
  .action-row.tone-high {
    border-left-color: #dc2626;
    background: linear-gradient(90deg, #fef2f2 0%, var(--surface, #fff) 40%);
  }
  .action-row.tone-medium {
    border-left-color: #f59e0b;
    background: linear-gradient(90deg, #fffbeb 0%, var(--surface, #fff) 40%);
  }
  .action-row.tone-low {
    border-left-color: #16a34a;
    background: linear-gradient(90deg, #f0fdf4 0%, var(--surface, #fff) 40%);
  }
  .action-icon {
    flex-shrink: 0;
    width: 36px;
    height: 36px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(15, 107, 62, 0.08);
    color: var(--primary, #0f6b3e);
  }
  .tone-high .action-icon { background: #fee2e2; color: #b91c1c; }
  .tone-medium .action-icon { background: #fef3c7; color: #b45309; }
  .tone-low .action-icon { background: #dcfce7; color: #15803d; }
  .action-main {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
  }
  .action-title {
    font-size: 0.9rem;
    font-weight: 600;
    color: var(--text, #111827);
    line-height: 1.3;
  }
  .action-detail {
    font-size: 0.78rem;
    color: var(--text-light, #6b7280);
    line-height: 1.35;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .action-cta {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    padding: 0.45rem 0.8rem;
    background: transparent;
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 7px;
    font-size: 0.78rem;
    font-weight: 600;
    color: var(--text, #111827);
    text-decoration: none;
    cursor: pointer;
    flex-shrink: 0;
    transition: all 0.15s;
  }
  .action-cta:hover {
    border-color: var(--primary, #0f6b3e);
    color: var(--primary, #0f6b3e);
  }

  /* ── Cards ── */
  .card {
    background: var(--surface, #fff);
    border-radius: 12px;
    padding: 1.15rem 1.25rem;
    border: 1px solid var(--border, #e5e7eb);
    overflow: hidden;
  }
  .card.collapsed { padding-bottom: 1rem; }
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.85rem;
    flex-wrap: wrap;
  }
  .card-header h3 {
    display: flex;
    align-items: center;
    gap: 0.45rem;
    margin: 0;
    font-size: 1rem;
    font-weight: 600;
    color: var(--text, #111827);
  }
  .card-header h3 svg { color: var(--primary, #0f6b3e); }
  .card-actions {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    flex-wrap: wrap;
  }
  .small-select {
    padding: 0.3rem 0.55rem;
    border-radius: 6px;
    border: 1px solid var(--border, #e5e7eb);
    background: var(--surface, #fff);
    color: var(--text, #111827);
    font-size: 0.78rem;
  }
  .rotated { transform: rotate(-90deg); }

  /* ── Category performance ── */
  .cat-perf-list { display: flex; flex-direction: column; gap: 0.7rem; }
  .cp-row { display: flex; flex-direction: column; gap: 0.3rem; }
  .cp-top { display: flex; justify-content: space-between; align-items: baseline; gap: 0.5rem; }
  .cp-name { font-size: 0.9rem; font-weight: 600; color: var(--text, #111827); }
  .cp-rev { font-size: 0.85rem; font-weight: 700; color: var(--primary, #0f6b3e); }
  .cp-bar-wrap {
    width: 100%;
    height: 7px;
    background: var(--background, #f3f4f6);
    border-radius: 4px;
    overflow: hidden;
  }
  .cp-bar {
    height: 100%;
    background: var(--primary, #0f6b3e);
    border-radius: 4px;
    transition: width 0.3s;
  }
  .cp-meta {
    display: flex;
    justify-content: space-between;
    font-size: 0.72rem;
    color: var(--text-light, #6b7280);
  }

  /* ── Heatmap ── */
  .peak-hints {
    display: flex;
    gap: 0.4rem;
    flex-wrap: wrap;
    margin-bottom: 0.75rem;
  }
  .peak-hint-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.35rem 0.6rem;
    background: #f0fdf4;
    border: 1px solid #86efac;
    border-radius: 20px;
    font-size: 0.75rem;
    color: #166534;
    font-weight: 500;
  }
  .peak-hint-chip strong { font-weight: 700; }
  .peak-hint-chip span { opacity: 0.75; }
  .peak-hint-chip.warn {
    background: #fffbeb;
    border-color: #fde68a;
    color: #92400e;
  }

  .heatmap-wrapper {
    overflow-x: auto;
    padding-bottom: 0.35rem;
  }
  .heatmap-grid {
    display: grid;
    grid-template-columns: 40px repeat(var(--hours), minmax(20px, 1fr));
    gap: 2px;
    min-width: 520px;
  }
  .heat-corner { height: 16px; }
  .heat-hour {
    font-size: 0.62rem;
    color: var(--text-light, #9ca3af);
    text-align: center;
    height: 16px;
    line-height: 16px;
    font-weight: 600;
    user-select: none;
  }
  .heat-day {
    font-size: 0.7rem;
    font-weight: 700;
    color: var(--text-light, #6b7280);
    height: 22px;
    display: flex;
    align-items: center;
    padding-right: 0.4rem;
    user-select: none;
  }
  .heat-cell {
    height: 22px;
    border-radius: 3px;
    transition: transform 0.1s, box-shadow 0.1s;
    cursor: pointer;
  }
  .heat-cell:hover {
    transform: scale(1.15);
    box-shadow: 0 0 0 1px var(--primary, #0f6b3e);
    position: relative;
    z-index: 2;
  }
  .heat-cell.peak { box-shadow: 0 0 0 1px #166534; }
  .chart-hint {
    text-align: center;
    font-size: 0.72rem;
    color: var(--text-light, #6b7280);
    margin: 0.6rem 0 0;
  }

  /* Legacy fallback */
  .legacy-hours {
    display: flex;
    align-items: flex-end;
    gap: 0.15rem;
    height: 140px;
  }
  .peak-bar-container {
    flex: 1 1 0;
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
    display: flex;
    justify-content: center;
    align-items: flex-start;
    padding-top: 0.15rem;
    box-sizing: border-box;
    overflow: hidden;
  }
  .peak-value { color: white; font-size: 0.55rem; font-weight: 700; }
  .peak-label {
    margin-top: 0.25rem;
    font-size: 0.58rem;
    color: var(--text-light, #6b7280);
  }

  /* ── Risk card ── */
  .risk-card {
    border-color: #fcd34d;
    background: linear-gradient(135deg, #fffbeb 0%, var(--surface, #fff) 60%);
  }
  .risk-card h3 svg { color: #b45309; }
  .risk-hint {
    font-size: 0.82rem;
    color: var(--text-light, #6b7280);
    margin: 0 0 0.75rem;
  }
  .risk-list {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }
  .risk-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 0.5rem;
    padding: 0.65rem 0.75rem;
    background: #fff;
    border: 1px solid #fde68a;
    border-radius: 9px;
    flex-wrap: wrap;
  }
  .risk-main {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
    min-width: 0;
    flex: 1;
  }
  .risk-main strong { font-size: 0.88rem; color: var(--text, #111827); }
  .risk-meta {
    font-size: 0.75rem;
    color: var(--text-light, #6b7280);
  }
  .risk-cost { color: #b91c1c; }
  .risk-badge {
    padding: 0.25rem 0.55rem;
    background: #fef3c7;
    color: #92400e;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 700;
    flex-shrink: 0;
  }

  /* ── Basket ── */
  .basket-hint {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    font-size: 0.8rem;
    color: var(--text-light, #6b7280);
    margin: 0 0 0.75rem;
    padding: 0.55rem 0.75rem;
    background: #fefce8;
    border-left: 3px solid #facc15;
    border-radius: 6px;
  }
  .basket-hint svg { color: #ca8a04; flex-shrink: 0; }
  .mb-list { display: flex; flex-direction: column; gap: 0.5rem; }
  .mb-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 0.5rem;
    padding: 0.65rem 0.85rem;
    background: var(--background, #f9fafb);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 9px;
    flex-wrap: wrap;
  }
  .mb-row.top {
    background: linear-gradient(90deg, #f0fdf4 0%, var(--surface, #fff) 100%);
    border-color: #86efac;
  }
  .mb-pair {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    min-width: 0;
    flex: 1;
  }
  .mb-product {
    font-size: 0.88rem;
    font-weight: 600;
    color: var(--text, #111827);
    max-width: 180px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .mb-plus {
    font-size: 1rem;
    font-weight: 700;
    color: #4f46e5;
  }
  .mb-stats { flex-shrink: 0; }
  .mb-stat {
    font-size: 0.78rem;
    color: var(--text-light, #6b7280);
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    padding: 0.25rem 0.6rem;
    border-radius: 20px;
    white-space: nowrap;
  }
  .mb-stat strong { color: var(--primary, #0f6b3e); font-weight: 700; }

  /* ── Top products ── */
  .top-list { display: flex; flex-direction: column; gap: 0.45rem; }
  .top-row {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    padding: 0.55rem 0.75rem;
    background: var(--background, #f9fafb);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 9px;
  }
  .top-rank {
    width: 26px;
    height: 26px;
    flex-shrink: 0;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: var(--primary, #0f6b3e);
    color: white;
    border-radius: 50%;
    font-size: 0.75rem;
    font-weight: 700;
  }
  .top-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 0.1rem; }
  .top-name-line { display: flex; align-items: center; gap: 0.35rem; flex-wrap: wrap; }
  .top-name-line strong { font-size: 0.88rem; color: var(--text, #111827); font-weight: 600; }
  .parent-tag {
    display: inline-flex;
    align-items: center;
    gap: 0.15rem;
    font-size: 0.68rem;
    font-weight: 500;
    background: #dbeafe;
    color: #1e40af;
    padding: 0.1rem 0.4rem;
    border-radius: 20px;
  }
  .top-meta { display: flex; align-items: center; gap: 0.3rem; }
  .cat-chip {
    display: inline-block;
    font-size: 0.68rem;
    font-weight: 500;
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    color: var(--text-light, #6b7280);
    padding: 0.05rem 0.4rem;
    border-radius: 20px;
  }
  .top-qty { display: flex; flex-direction: column; align-items: flex-end; flex-shrink: 0; }
  .top-qty strong { font-size: 1rem; font-weight: 700; color: var(--primary, #0f6b3e); }
  .top-qty span { font-size: 0.68rem; color: var(--text-light, #6b7280); }

  /* ── Tables ── */
  .table-wrapper { overflow-x: auto; border-radius: 8px; }
  table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
  th, td {
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
  th.num, td.num { text-align: right; white-space: nowrap; }
  .margin-value { font-weight: 600; color: #16a34a; }
  .name-cell {
    max-width: 220px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .empty-text {
    text-align: center;
    padding: 1.5rem;
    color: var(--text-light, #6b7280);
    font-size: 0.9rem;
  }

  /* Best/worst */
  .best-worst-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.6rem;
    margin-bottom: 1rem;
  }
  .bw-cell {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
    padding: 0.65rem 0.8rem;
    border-radius: 9px;
    font-size: 0.82rem;
    min-width: 0;
  }
  .bw-cell span:first-child {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    font-weight: 600;
    color: var(--text-light, #6b7280);
  }
  .bw-cell strong {
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--text, #111827);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .bw-cell .bw-pct {
    font-size: 0.8rem;
    font-weight: 700;
    text-transform: none;
    letter-spacing: 0;
  }
  .bw-cell.best { background: #f0fdf4; border: 1px solid #86efac; }
  .bw-cell.best .bw-pct { color: #166534; }
  .bw-cell.worst { background: #fef2f2; border: 1px solid #fecaca; }
  .bw-cell.worst .bw-pct { color: #991b1b; }

  /* Margin cards (mobile) */
  .margin-cards { display: none; flex-direction: column; gap: 0.5rem; }
  .margin-card {
    background: var(--background, #f9fafb);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 9px;
    padding: 0.65rem 0.75rem;
  }
  .mc-header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 0.5rem;
    margin-bottom: 0.35rem;
  }
  .mc-header strong {
    font-size: 0.9rem;
    color: var(--text, #111827);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    min-width: 0;
  }
  .mc-margin { font-weight: 700; color: #166534; font-size: 0.88rem; flex-shrink: 0; }
  .mc-row {
    display: flex;
    justify-content: space-between;
    font-size: 0.78rem;
    color: var(--text-light, #6b7280);
    padding: 0.1rem 0;
  }
  .mc-row .mc-profit { color: var(--text, #111827); font-weight: 600; }

  .pagination {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.6rem;
    padding: 0.75rem 0 0;
    margin-top: 0.5rem;
    border-top: 1px solid var(--border, #e5e7eb);
  }
  .page-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    border-radius: 6px;
    border: 1px solid var(--border, #e5e7eb);
    background: var(--surface, #fff);
    color: var(--text, #111827);
    cursor: pointer;
    transition: all 0.15s;
  }
  .page-btn:hover:not(:disabled) {
    border-color: var(--primary, #0f6b3e);
    color: var(--primary, #0f6b3e);
  }
  .page-btn:disabled { opacity: 0.4; cursor: not-allowed; }
  .page-info {
    font-size: 0.8rem;
    color: var(--text-light, #6b7280);
    font-weight: 500;
  }

  .clickable-row { cursor: pointer; transition: background 0.15s; }
  .clickable-row:hover { background: #f0fdf4; }
  .action-col { width: 24px; text-align: right; }
  .chev-icon { color: var(--text-light, #6b7280); }

  /* Price changes */
  .price-changes-list { display: flex; flex-direction: column; gap: 0.65rem; }
  .price-change-item {
    padding: 0.75rem;
    background: var(--background, #f9fafb);
    border-radius: 9px;
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
  .product-header strong { font-size: 0.95rem; color: var(--text, #111827); }
  .current-margin { font-size: 0.78rem; color: var(--text-light, #6b7280); }
  .changes-list { display: flex; flex-direction: column; gap: 0.35rem; }
  .change-line {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-wrap: wrap;
    font-size: 0.82rem;
  }
  .change-line.muted { opacity: 0.6; }
  .change-type {
    font-size: 0.62rem;
    font-weight: 700;
    padding: 0.1rem 0.35rem;
    border-radius: 3px;
    letter-spacing: 0.3px;
  }
  .change-type.selling { background: #dbeafe; color: #1e40af; }
  .change-type.purchase { background: #fef3c7; color: #92400e; }
  .change-type.off { background: #e5e7eb; color: #9ca3af; }
  .change-values { color: var(--text, #111827); font-weight: 500; }
  .change-values.muted { color: var(--text-light, #6b7280); font-style: italic; font-weight: 400; }
  .pct {
    display: inline-flex;
    align-items: center;
    gap: 0.1rem;
    font-size: 0.72rem;
    font-weight: 600;
    padding: 0.1rem 0.35rem;
    border-radius: 20px;
  }
  .pct.up { background: #dcfce7; color: #166534; }
  .pct.down { background: #fee2e2; color: #991b1b; }
  .pct.flat { background: var(--surface, #fff); color: var(--text-light, #6b7280); }
  .change-date {
    margin-left: auto;
    font-size: 0.72rem;
    color: var(--text-light, #6b7280);
  }

  /* Exports */
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
  .btn:hover { border-color: var(--primary, #0f6b3e); color: var(--primary, #0f6b3e); }
  .btn-primary {
    background: var(--primary, #0f6b3e);
    color: white;
    border-color: var(--primary, #0f6b3e);
  }

  /* ── Responsive ── */
  @media (max-width: 768px) {
    .kpi-grid { grid-template-columns: repeat(2, 1fr); }
    .cash-line { grid-template-columns: repeat(2, 1fr); }
    .card { padding: 1rem; }
    .action-row { flex-wrap: wrap; }
    .action-cta { margin-left: auto; }
  }

  @media (max-width: 480px) {
    .insights-page { gap: 1rem; }
    .kpi-big { font-size: 1.15rem; }
    .cash-line { padding: 0.6rem; gap: 0.4rem; }
    .cash-item { padding: 0.45rem 0.55rem; }
    .cash-item strong { font-size: 0.88rem; }
    .margin-table-wrap { display: none; }
    .margin-cards { display: flex; }
    .best-worst-row { grid-template-columns: 1fr; gap: 0.45rem; }
    th, td { padding: 0.45rem 0.35rem; font-size: 0.82rem; }
    .heatmap-grid {
      grid-template-columns: 32px repeat(var(--hours), minmax(16px, 1fr));
      gap: 1.5px;
      min-width: 460px;
    }
    .heat-cell { height: 18px; }
    .heat-day { font-size: 0.65rem; height: 18px; }
    .heat-hour { font-size: 0.55rem; }
    .mb-pair { gap: 0.3rem; }
    .mb-product { max-width: 120px; }
    .action-row { padding: 0.65rem 0.75rem; }
    .action-title { font-size: 0.85rem; }
    .action-detail { white-space: normal; }
    .export-actions { flex-direction: column; }
    .export-actions .btn { justify-content: center; width: 100%; }
  }
</style>