<script>
  import { onMount, onDestroy } from "svelte";
  import {
    Plus,
    X,
    Trash2,
    AlertTriangle,
    UserPlus,
    Eye,
    ChevronDown,
    ChevronUp,
    Loader2,
    ShoppingBag,
    Sparkles,
    TrendingUp,
  } from "lucide-svelte";
  import { user as userStore } from "../stores/auth";
  import Layout from "../components/Layout.svelte";
  import Receipt from "../components/Receipt.svelte";
  import API from "../api/api";

  let sales = [];
  let products = [];
  let customers = [];

  let totalSales = 0;
  let hasMore = false;
  let loadingSales = false;
  const PAGE_SIZE = 50;

  // Filters
  let filterStatus = "all";
  let dateRange = "all";
  let searchQuery = "";

  // New sale form
  let showForm = false;
  let saleItems = [{ product_id: "", quantity: 1 }];
  let loading = false;
  let isCreditSale = false;
  let selectedCustomerId = null;
  let showNewCustomerModal = false;
  let newCustomer = { name: "", phone: "", email: "", address: "" };

  // Void modal
  let voidModalOpen = false;
  let selectedSale = null;
  let voidReason = "";
  const VOID_QUICK_REASONS = ["Wrong item", "Customer cancelled", "Duplicate", "Other"];

  // Receipt
  let showReceipt = false;
  let receiptSale = null;
  let receiptItems = [];

  // Expanded sale rows (desktop)
  let expandedSales = {};

  // Market basket analysis (collapsible)
  let basketOpen = false;

  // Role
  let currentUser = null;
  const unsub = userStore.subscribe((v) => (currentUser = v));
  $: isManagerOrOwner =
    currentUser?.role === "manager" || currentUser?.role === "owner";

  onMount(async () => {
    await Promise.all([fetchSales(true), fetchProducts(), fetchCustomers()]);
  });

  onDestroy(unsub);

  function dateParams() {
    if (dateRange === "today") return { days: 1 };
    if (dateRange === "7d") return { days: 7 };
    if (dateRange === "30d") return { days: 30 };
    return {};
  }

  async function fetchSales(reset = false) {
    if (loadingSales) return;
    loadingSales = true;
    try {
      const offset = reset ? 0 : sales.length;
      const params = { limit: PAGE_SIZE, offset, ...dateParams() };
      if (filterStatus !== "all") params.status = filterStatus;
      const res = await API.get("/sales/", { params });
      const data = res.data;
      const page = Array.isArray(data) ? data : data.sales || [];
      sales = reset ? page : [...sales, ...page];
      totalSales = Array.isArray(data) ? sales.length : data.total || sales.length;
      hasMore = Array.isArray(data) ? false : !!data.has_more;
      await maybeAutoLoadForSearch();
    } catch (err) {
      console.error("Failed to load sales", err);
    } finally {
      loadingSales = false;
    }
  }

  let autoSearchDepth = 0;
  async function maybeAutoLoadForSearch() {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return;
    if (!hasMore) return;
    if (autoSearchDepth >= 5) return;

    const anyMatch = sales.some((s) => {
      const inItems = (s.items || []).some((it) =>
        (it.name || "").toLowerCase().includes(q)
      );
      const inCustomer = (s.customer_name || "").toLowerCase().includes(q);
      const inProducts = (s.products || []).some((p) =>
        (p || "").toLowerCase().includes(q)
      );
      return inItems || inCustomer || inProducts;
    });
    if (anyMatch) return;

    autoSearchDepth += 1;
    try {
      const params = { limit: PAGE_SIZE, offset: sales.length, ...dateParams() };
      if (filterStatus !== "all") params.status = filterStatus;
      const res = await API.get("/sales/", { params });
      const data = res.data;
      const page = Array.isArray(data) ? data : data.sales || [];
      sales = [...sales, ...page];
      hasMore = Array.isArray(data) ? false : !!data.has_more;
    } catch (err) {
      console.error("Auto-load for search failed", err);
    }
  }

  $: if (searchQuery) {
    autoSearchDepth = 0;
    maybeAutoLoadForSearch();
  }

  async function fetchProducts() {
    try {
      const res = await API.get("/products/?leaf_only=true");
      products = (res.data || []).filter((p) => !p.archived && !p.is_deleted);
    } catch {
      try {
        const res = await API.get("/products/");
        products = (res.data || []).filter(
          (p) => !p.archived && !p.is_deleted && !(p.is_parent && p.parent_id === null)
        );
      } catch (err) {
        console.error("Failed to load products", err);
      }
    }
  }

  async function fetchCustomers() {
    try {
      const res = await API.get("/customers/");
      customers = res.data || [];
    } catch (err) {
      console.error("Failed to load customers", err);
    }
  }

  function setFilter(s) {
    if (filterStatus === s) return;
    filterStatus = s;
    fetchSales(true);
  }

  function setDateRange(r) {
    if (dateRange === r) return;
    dateRange = r;
    fetchSales(true);
  }

  $: filteredSales = (() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return sales;
    return sales.filter((s) => {
      const inItems = (s.items || []).some((it) =>
        (it.name || "").toLowerCase().includes(q)
      );
      const inCustomer = (s.customer_name || "").toLowerCase().includes(q);
      const inProducts = (s.products || []).some((p) =>
        (p || "").toLowerCase().includes(q)
      );
      return inItems || inCustomer || inProducts;
    });
  })();

  // Customer lookup by id — for real balance display on credit rows
  $: customerById = (() => {
    const map = {};
    customers.forEach((c) => (map[c.id] = c));
    return map;
  })();

  $: summary = (() => {
    let count = 0;
    let total = 0;
    let paid = 0;
    let credit = 0;
    let voided = 0;
    filteredSales.forEach((s) => {
      count += 1;
      if (s.is_voided) {
        voided += 1;
      } else {
        total += Number(s.total_amount || 0);
        paid += Number(s.amount_paid || 0);
        credit += Math.max(
          0,
          Number(s.total_amount || 0) - Number(s.amount_paid || 0)
        );
      }
    });
    return { count, total, paid, credit, voided };
  })();

  $: lastSaleAgo = (() => {
    const nonVoided = filteredSales.find((s) => !s.is_voided);
    if (!nonVoided) return null;
    const diffMs = Date.now() - new Date(nonVoided.created_at).getTime();
    const mins = Math.floor(diffMs / 60000);
    if (mins < 1) return "just now";
    if (mins < 60) return `${mins} min ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs} hr ago`;
    const days = Math.floor(hrs / 24);
    return `${days} d ago`;
  })();

  // ── Market basket analysis (client-side) ──
  $: basketPairs = (() => {
    const eligible = filteredSales.filter((s) => !s.is_voided);
    if (eligible.length < 3) return [];

    const soloCount = {}; // product name → # sales containing it
    const pairCount = {}; // "A|||B" → # sales containing both

    eligible.forEach((s) => {
      const names = new Set(
        (s.items || []).map((it) => it.name).filter(Boolean)
      );
      const arr = Array.from(names);
      arr.forEach((n) => (soloCount[n] = (soloCount[n] || 0) + 1));
      for (let i = 0; i < arr.length; i++) {
        for (let j = i + 1; j < arr.length; j++) {
          const key =
            arr[i] < arr[j] ? `${arr[i]}|||${arr[j]}` : `${arr[j]}|||${arr[i]}`;
          pairCount[key] = (pairCount[key] || 0) + 1;
        }
      }
    });

    const totalSales = eligible.length;
    const pairs = [];
    Object.entries(pairCount).forEach(([key, count]) => {
      if (count < 2) return;
      const [a, b] = key.split("|||");
      const soloA = soloCount[a] || 1;
      const soloB = soloCount[b] || 1;
      const support = count / totalSales;
      const lift = (count * totalSales) / (soloA * soloB);
      pairs.push({ a, b, count, support, lift });
    });

    pairs.sort((x, y) => {
      if (y.count !== x.count) return y.count - x.count;
      return y.lift - x.lift;
    });

    return pairs.slice(0, 8);
  })();

  function addItem() {
    saleItems = [...saleItems, { product_id: "", quantity: 1 }];
  }

  function removeItem(index) {
    saleItems = saleItems.filter((_, i) => i !== index);
  }

  $: formTotal = saleItems.reduce((sum, i) => {
    const p = products.find((pr) => pr.id === i.product_id);
    return sum + (p ? Number(p.selling_price || 0) * Number(i.quantity || 0) : 0);
  }, 0);

  // ── New Sale button → jump to Products page & auto-open Add modal ──
  function goToAddProduct() {
    window.location.href = "/products?add=1";
  }

  async function submitSale() {
    const items = saleItems.filter((i) => i.product_id && i.quantity > 0);
    if (items.length === 0) return;
    loading = true;
    try {
      const payload = {
        items: items.map((i) => ({
          product_id: i.product_id,
          quantity: Number(i.quantity),
        })),
        customer_id: isCreditSale ? selectedCustomerId : null,
        payment_status: isCreditSale ? "unpaid" : "paid",
        amount_paid: isCreditSale ? 0 : formTotal,
      };
      await API.post("/sales/", payload);
      resetForm();
      await fetchSales(true);
    } catch (err) {
      alert(
        "Failed to create sale: " + (err.response?.data?.detail || "Unknown error")
      );
    } finally {
      loading = false;
    }
  }

  function resetForm() {
    saleItems = [{ product_id: "", quantity: 1 }];
    isCreditSale = false;
    selectedCustomerId = null;
    showForm = false;
  }

  async function createCustomer() {
    try {
      const res = await API.post("/customers/", newCustomer);
      customers = [...customers, res.data];
      selectedCustomerId = res.data.id;
      showNewCustomerModal = false;
      newCustomer = { name: "", phone: "", email: "", address: "" };
    } catch {
      alert("Failed to create customer");
    }
  }

  // ── Void ──
  function openVoidModal(sale) {
    selectedSale = sale;
    voidReason = "";
    voidModalOpen = true;
  }
  function closeVoidModal() {
    voidModalOpen = false;
    selectedSale = null;
    voidReason = "";
  }
  function applyQuickReason(r) {
    voidReason = voidReason === r ? "" : r;
  }
  async function voidSale() {
    if (!selectedSale) return;
    try {
      await API.post(`/sales/${selectedSale.id}/void`, null, {
        params: { reason: voidReason || undefined },
      });
      await fetchSales(true);
      closeVoidModal();
    } catch (err) {
      alert(
        "Failed to void sale: " + (err.response?.data?.detail || "Unknown error")
      );
    }
  }

  // ── Receipt ──
  function openReceipt(sale) {
    receiptSale = sale;
    receiptItems = (sale.items || []).map((it) => ({
      name: it.name,
      qty: it.quantity,
      selling_price: it.unit_price,
    }));
    showReceipt = true;
  }
  function closeReceipt() {
    showReceipt = false;
    receiptSale = null;
    receiptItems = [];
  }
  function handleReceiptVoid(sale) {
    closeReceipt();
    openVoidModal(sale);
  }

  function toggleExpand(saleId) {
    expandedSales = { ...expandedSales, [saleId]: !expandedSales[saleId] };
  }

  function fmt(n) {
    return Number(n || 0).toLocaleString(undefined, {
      maximumFractionDigits: 2,
    });
  }

  function fmtDate(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    return d.toLocaleString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  function itemCount(sale) {
    return (sale.items || []).reduce((n, it) => n + (it.quantity || 0), 0);
  }

  // ── Credit display helpers ──
  // For a credit sale, show what's still owed on the whole customer account
  // if we don't have a reliable per-sale paid amount.
  function salePaidFor(sale) {
    if (sale.is_voided) return 0;
    if (sale.payment_status === "paid") return Number(sale.total_amount || 0);
    return Number(sale.amount_paid || 0);
  }
  function customerBalanceFor(sale) {
    if (!sale.customer_id) return null;
    const c = customerById[sale.customer_id];
    if (!c) return null;
    return Number(c.total_credit || 0);
  }
  function creditLabel(sale) {
    const paid = salePaidFor(sale);
    const total = Number(sale.total_amount || 0);
    if (paid >= total - 0.01) return "Fully paid";
    if (paid > 0) return `Partial · MWK ${fmt(paid)} paid`;
    return "Unpaid";
  }
</script>

<Layout title="Sales">
  <div class="sales-header">
    <div class="sales-header-text">
      <h2>Recent Sales</h2>
      {#if lastSaleAgo && filterStatus !== "voided"}
        <p class="last-sale">Last sale: {lastSaleAgo}</p>
      {/if}
    </div>
    <button class="btn btn-primary" on:click={goToAddProduct} type="button">
      <Plus size={16} strokeWidth={2} /> New Sale
    </button>
  </div>

  <!-- Filters -->
  <div class="filter-bar">
    <div class="filter-pills">
      <button type="button" class:active={filterStatus === "all"} on:click={() => setFilter("all")}>
        All
      </button>
      <button type="button" class:active={filterStatus === "paid"} on:click={() => setFilter("paid")}>
        Paid
      </button>
      <button type="button" class:active={filterStatus === "unpaid"} on:click={() => setFilter("unpaid")}>
        Credit
      </button>
      <button type="button" class:active={filterStatus === "voided"} on:click={() => setFilter("voided")}>
        Voided
      </button>
    </div>
    <div class="filter-pills date-pills">
      <button type="button" class:active={dateRange === "all"} on:click={() => setDateRange("all")}>
        All time
      </button>
      <button type="button" class:active={dateRange === "today"} on:click={() => setDateRange("today")}>
        Today
      </button>
      <button type="button" class:active={dateRange === "7d"} on:click={() => setDateRange("7d")}>
        7d
      </button>
      <button type="button" class:active={dateRange === "30d"} on:click={() => setDateRange("30d")}>
        30d
      </button>
    </div>
    <input
      class="search-input"
      type="text"
      placeholder="Search product or customer…"
      bind:value={searchQuery}
    />
  </div>

  {#if !loadingSales && filteredSales.length > 0}
    <div class="summary-bar">
      <span><strong>{summary.count}</strong> sale{summary.count === 1 ? "" : "s"}</span>
      {#if filterStatus !== "voided"}
        <span class="sum-sep">·</span>
        <span>Total: <strong>MWK {fmt(summary.total)}</strong></span>
        {#if summary.credit > 0}
          <span class="sum-sep">·</span>
          <span class="sum-credit">
            Credit outstanding: <strong>MWK {fmt(summary.credit)}</strong>
          </span>
        {/if}
      {/if}
      {#if summary.voided > 0}
        <span class="sum-sep">·</span>
        <span class="sum-voided">{summary.voided} voided</span>
      {/if}
    </div>
  {/if}

  <!-- ── Market Basket Analysis ── -->
  {#if basketPairs.length > 0}
    <div class="basket-card">
      <button
        type="button"
        class="basket-header"
        on:click={() => (basketOpen = !basketOpen)}
      >
        <div class="basket-header-left">
          <Sparkles size={16} strokeWidth={2} class="basket-icon" />
          <strong>Bought together</strong>
          <span class="basket-sub">{basketPairs.length} pair{basketPairs.length === 1 ? "" : "s"} found</span>
        </div>
        {#if basketOpen}
          <ChevronUp size={16} strokeWidth={2} />
        {:else}
          <ChevronDown size={16} strokeWidth={2} />
        {/if}
      </button>
      {#if basketOpen}
        <div class="basket-body">
          <p class="basket-hint">
            Products that appear in the same sale — the higher the count, the stronger the affinity. Consider displaying them side-by-side.
          </p>
          <ul class="basket-list">
            {#each basketPairs as p}
              <li class="basket-row">
                <span class="basket-pair">{p.a} <span class="basket-plus">+</span> {p.b}</span>
                <span class="basket-meta">
                  <strong>{p.count}×</strong>
                  <span class="basket-support">· {Math.round(p.support * 100)}% of sales</span>
                </span>
              </li>
            {/each}
          </ul>
        </div>
      {/if}
    </div>
  {/if}

  <div class="sales-list">
    {#if loadingSales && sales.length === 0}
      <div class="loading-state">
        <Loader2 size={22} class="spin" /> Loading sales…
      </div>
    {:else if filteredSales.length === 0}
      <p class="no-sales">
        {#if searchQuery || filterStatus !== "all" || dateRange !== "all"}
          No sales match your filters.
        {:else}
          No sales recorded yet.
        {/if}
      </p>
    {:else}
      <!-- Desktop table -->
      <div class="table-wrapper">
        <table class="sales-table">
          <thead>
            <tr>
              <th class="expand-col"></th>
              <th>Products</th>
              <th class="num">Total</th>
              <th>Date</th>
              <th>Status</th>
              <th class="actions-col">Actions</th>
            </tr>
          </thead>
          <tbody>
            {#each filteredSales as sale (sale.id)}
              {@const expanded = expandedSales[sale.id]}
              {@const paidAmt = salePaidFor(sale)}
              {@const custBal = customerBalanceFor(sale)}
              <tr class:voided-row={sale.is_voided}>
                <td class="expand-col">
                  <button
                    class="expand-btn"
                    on:click={() => toggleExpand(sale.id)}
                    type="button"
                    aria-label="Toggle line items"
                  >
                    {#if expanded}
                      <ChevronUp size={14} strokeWidth={2} />
                    {:else}
                      <ChevronDown size={14} strokeWidth={2} />
                    {/if}
                  </button>
                </td>
                <td>
                  <div class="sale-row-products">
                    <div class="product-names">
                      {#if sale.items && sale.items.length > 0}
                        {#each sale.items.slice(0, 2) as it}
                          <span class="product-line">
                            {it.name}
                            <span class="qty-inline">×{it.quantity}</span>
                          </span>
                        {/each}
                        {#if sale.items.length > 2}
                          <span class="more-hint">+{sale.items.length - 2} more</span>
                        {/if}
                      {:else}
                        <span class="muted">{sale.products?.join(", ") || "—"}</span>
                      {/if}
                    </div>
                    {#if sale.customer_name}
                      <span class="customer-tag">{sale.customer_name}</span>
                    {/if}
                  </div>
                </td>
                <td class="num">
                  <strong>MWK {fmt(sale.total_amount)}</strong>
                  {#if sale.payment_status !== "paid" && !sale.is_voided}
                    <div class="paid-note">
                      {#if paidAmt > 0}
                        Paid: MWK {fmt(paidAmt)} on this sale
                      {:else if custBal !== null && custBal > 0}
                        Customer owes: MWK {fmt(custBal)}
                      {:else if custBal !== null}
                        Customer settled
                      {:else}
                        Unpaid
                      {/if}
                    </div>
                  {/if}
                </td>
                <td class="date-cell">{fmtDate(sale.created_at)}</td>
                <td>
                  {#if sale.is_voided}
                    <span class="badge voided">Voided</span>
                    {#if sale.void_reason}
                      <div class="void-reason">{sale.void_reason}</div>
                    {/if}
                  {:else if sale.payment_status === "unpaid"}
                    <span class="badge credit">Credit</span>
                  {:else if sale.payment_status === "partial"}
                    <span class="badge partial">Partial</span>
                  {:else}
                    <span class="badge paid">Paid</span>
                  {/if}
                </td>
                <td>
                  <div class="row-actions">
                    <button
                      class="btn-icon"
                      on:click={() => openReceipt(sale)}
                      title="View receipt"
                      type="button"
                    >
                      <Eye size={16} strokeWidth={2} />
                    </button>
                    {#if !sale.is_voided && isManagerOrOwner}
                      <button
                        class="btn-icon danger"
                        on:click={() => openVoidModal(sale)}
                        title="Void Sale"
                        type="button"
                      >
                        <Trash2 size={16} strokeWidth={2} />
                      </button>
                    {/if}
                  </div>
                </td>
              </tr>

              {#if expanded}
                <tr class="items-detail-row">
                  <td></td>
                  <td colspan="5">
                    <div class="items-detail">
                      <table class="items-detail-table">
                        <thead>
                          <tr>
                            <th>Item</th>
                            <th class="num">Qty</th>
                            <th class="num">Price</th>
                            <th class="num">Line total</th>
                          </tr>
                        </thead>
                        <tbody>
                          {#each sale.items || [] as it}
                            <tr>
                              <td>{it.name}</td>
                              <td class="num">{it.quantity}</td>
                              <td class="num">MWK {fmt(it.unit_price)}</td>
                              <td class="num">MWK {fmt(it.total_price)}</td>
                            </tr>
                          {/each}
                        </tbody>
                      </table>
                    </div>
                  </td>
                </tr>
              {/if}
            {/each}
          </tbody>
        </table>
      </div>

      <!-- Mobile cards -->
      <div class="mobile-sales">
        {#each filteredSales as sale (sale.id)}
          {@const paidAmt = salePaidFor(sale)}
          {@const custBal = customerBalanceFor(sale)}
          <div class="sale-card" class:voided={sale.is_voided}>
            <div class="sale-card-header">
              <strong>MWK {fmt(sale.total_amount)}</strong>
              {#if sale.is_voided}
                <span class="badge voided">Voided</span>
              {:else if sale.payment_status === "unpaid"}
                <span class="badge credit">Credit</span>
              {:else if sale.payment_status === "partial"}
                <span class="badge partial">Partial</span>
              {:else}
                <span class="badge paid">Paid</span>
              {/if}
            </div>

            {#if sale.customer_name}
              <p class="sale-customer">
                <strong>{sale.customer_name}</strong>
                {#if sale.payment_status !== "paid" && !sale.is_voided}
                  {#if paidAmt > 0}
                    <span class="sale-paid-note">· MWK {fmt(paidAmt)} paid</span>
                  {:else if custBal !== null && custBal > 0}
                    <span class="sale-paid-note">· owes MWK {fmt(custBal)}</span>
                  {:else if custBal !== null}
                    <span class="sale-paid-note settled">· settled</span>
                  {/if}
                {/if}
              </p>
            {/if}

            <div class="sale-items-list">
              {#each sale.items || [] as it}
                <div class="sale-item-line">
                  <span class="item-name">{it.name}</span>
                  <span class="item-detail">{it.quantity} × {fmt(it.unit_price)}</span>
                  <strong class="item-total">MWK {fmt(it.total_price)}</strong>
                </div>
              {:else}
                <div class="sale-item-line muted">
                  {sale.products?.join(", ") || "No items"}
                </div>
              {/each}
            </div>

            {#if sale.is_voided && sale.void_reason}
              <p class="void-reason">Voided — {sale.void_reason}</p>
            {/if}

            <div class="sale-card-footer">
              <span class="sale-date">{fmtDate(sale.created_at)}</span>
              <div class="mobile-actions">
                <button
                  class="btn-icon"
                  on:click={() => openReceipt(sale)}
                  title="View receipt"
                  type="button"
                >
                  <Eye size={14} strokeWidth={2} /> Receipt
                </button>
                {#if !sale.is_voided && isManagerOrOwner}
                  <button
                    class="btn-icon danger"
                    on:click={() => openVoidModal(sale)}
                    type="button"
                  >
                    <Trash2 size={14} strokeWidth={2} /> Void
                  </button>
                {/if}
              </div>
            </div>
          </div>
        {/each}
      </div>

      {#if hasMore}
        <div class="load-more-row">
          <button
            class="btn btn-secondary"
            on:click={() => fetchSales(false)}
            disabled={loadingSales}
            type="button"
          >
            {loadingSales ? "Loading…" : "Load more"}
          </button>
        </div>
      {/if}
    {/if}
  </div>

  <!-- Void modal -->
  {#if voidModalOpen}
    <div
      class="modal-overlay"
      role="dialog"
      aria-modal="true"
      tabindex="-1"
      on:click|self={closeVoidModal}
      on:keydown={(e) => e.key === "Escape" && closeVoidModal()}
    >
      <div class="modal">
        <h3><AlertTriangle size={20} strokeWidth={2} /> Void Sale</h3>
        <p>Are you sure you want to void this sale? Stock will be restored.</p>
        {#if selectedSale}
          <div class="void-summary">
            <strong>MWK {fmt(selectedSale.total_amount)}</strong>
            <span>{itemCount(selectedSale)} item{itemCount(selectedSale) === 1 ? "" : "s"}</span>
          </div>
        {/if}
        <div class="quick-reasons">
          {#each VOID_QUICK_REASONS as r}
            <button
              type="button"
              class="reason-chip"
              class:active={voidReason === r}
              on:click={() => applyQuickReason(r)}
            >
              {r}
            </button>
          {/each}
        </div>
        <div class="form-group">
          <label for="voidReason">Reason (optional)</label>
          <input
            id="voidReason"
            type="text"
            bind:value={voidReason}
            placeholder="e.g., Customer return"
          />
        </div>
        <div class="modal-actions">
          <button class="btn btn-secondary" on:click={closeVoidModal} type="button">
            Cancel
          </button>
          <button class="btn btn-danger" on:click={voidSale} type="button">
            Confirm Void
          </button>
        </div>
      </div>
    </div>
  {/if}

  <!-- New customer modal -->
  {#if showNewCustomerModal}
    <div
      class="modal-overlay"
      role="dialog"
      aria-modal="true"
      tabindex="-1"
      on:click|self={() => (showNewCustomerModal = false)}
      on:keydown={(e) => e.key === "Escape" && (showNewCustomerModal = false)}
    >
      <div class="modal">
        <h3>Add New Customer</h3>
        <div class="form-group">
          <label for="n-name">Name *</label>
          <input id="n-name" type="text" bind:value={newCustomer.name} required />
        </div>
        <div class="form-group">
          <label for="n-phone">Phone</label>
          <input id="n-phone" type="text" bind:value={newCustomer.phone} />
        </div>
        <div class="form-group">
          <label for="n-email">Email</label>
          <input id="n-email" type="email" bind:value={newCustomer.email} />
        </div>
        <div class="form-group">
          <label for="n-address">Address</label>
          <input id="n-address" type="text" bind:value={newCustomer.address} />
        </div>
        <div class="modal-actions">
          <button
            class="btn btn-secondary"
            on:click={() => (showNewCustomerModal = false)}
            type="button"
          >
            Cancel
          </button>
          <button
            class="btn btn-primary"
            on:click={createCustomer}
            disabled={!newCustomer.name}
            type="button"
          >
            Save
          </button>
        </div>
      </div>
    </div>
  {/if}

  <!-- Receipt -->
  {#if showReceipt && receiptSale}
    <Receipt
      sale={receiptSale}
      items={receiptItems}
      customerName={receiptSale.customer_name}
      canVoid={isManagerOrOwner && !receiptSale.is_voided}
      alreadyVoided={receiptSale.is_voided}
      on:close={closeReceipt}
      on:void={(e) => handleReceiptVoid(e.detail)}
    />
  {/if}
</Layout>

<style>
  .sales-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 1rem;
    gap: 0.5rem;
    flex-wrap: wrap;
  }
  .sales-header-text h2 {
    margin: 0;
    font-size: 1.15rem;
    font-weight: 600;
  }
  .last-sale {
    margin: 0.15rem 0 0;
    font-size: 0.78rem;
    color: var(--text-light, #6b7280);
  }

  .btn {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.55rem 1rem;
    border-radius: 8px;
    border: none;
    cursor: pointer;
    font-weight: 500;
    font-size: 0.9rem;
    transition: all 0.15s;
  }
  .btn-primary {
    background: var(--primary, #0f6b3e);
    color: white;
  }
  .btn-primary:hover:not(:disabled) {
    background: var(--primary-dark, #0a4f2e);
  }
  .btn-primary:disabled {
    opacity: 0.55;
    cursor: not-allowed;
  }
  .btn-secondary {
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    color: var(--text, #111827);
  }
  .btn-secondary:hover {
    background: var(--background, #f9fafb);
  }
  .btn-danger {
    background: var(--danger, #dc2626);
    color: white;
  }

  .filter-bar {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 0.75rem;
    flex-wrap: wrap;
    align-items: center;
  }
  .filter-pills {
    display: flex;
    gap: 0.35rem;
    flex-wrap: wrap;
  }
  .filter-pills button {
    padding: 0.45rem 0.9rem;
    border-radius: 8px;
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    cursor: pointer;
    font-size: 0.82rem;
    font-weight: 500;
    color: var(--text, #111827);
    transition: all 0.15s;
  }
  .filter-pills button:hover {
    border-color: var(--primary, #0f6b3e);
    color: var(--primary, #0f6b3e);
  }
  .filter-pills button.active {
    background: var(--primary, #0f6b3e);
    color: white;
    border-color: var(--primary, #0f6b3e);
  }
  .date-pills {
    border-left: 1px solid var(--border, #e5e7eb);
    padding-left: 0.5rem;
  }
  .search-input {
    flex: 1 1 220px;
    padding: 0.55rem 0.75rem;
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 8px;
    background: var(--surface, #fff);
    color: var(--text, #111827);
    font-size: 0.85rem;
    min-width: 0;
  }
  .search-input:focus {
    outline: none;
    border-color: var(--primary, #0f6b3e);
    box-shadow: 0 0 0 3px rgba(15, 107, 62, 0.1);
  }

  .summary-bar {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.4rem 0.5rem;
    padding: 0.55rem 0.85rem;
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 8px;
    margin-bottom: 0.75rem;
    font-size: 0.82rem;
    color: var(--text-light, #6b7280);
  }
  .summary-bar strong {
    color: var(--text, #111827);
    font-weight: 600;
  }
  .sum-sep {
    color: #d1d5db;
  }
  .sum-credit {
    color: #b45309;
  }
  .sum-voided {
    color: #991b1b;
  }

  /* ── Market basket card ── */
  .basket-card {
    background: var(--surface, #fff);
    border: 1px solid #c7d2fe;
    background: linear-gradient(135deg, rgba(99, 102, 241, 0.05) 0%, var(--surface, #fff) 60%);
    border-radius: 12px;
    margin-bottom: 0.75rem;
    overflow: hidden;
  }
  .basket-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    width: 100%;
    padding: 0.75rem 1rem;
    background: transparent;
    border: none;
    cursor: pointer;
    gap: 0.5rem;
  }
  .basket-header-left {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-wrap: wrap;
    min-width: 0;
    text-align: left;
  }
  .basket-icon {
    color: #4f46e5;
    flex-shrink: 0;
  }
  .basket-header strong {
    font-size: 0.92rem;
    color: var(--text, #111827);
  }
  .basket-sub {
    font-size: 0.76rem;
    color: var(--text-light, #6b7280);
    font-weight: 500;
  }
  .basket-body {
    padding: 0 1rem 1rem;
  }
  .basket-hint {
    margin: 0 0 0.6rem;
    font-size: 0.78rem;
    color: var(--text-light, #6b7280);
    line-height: 1.4;
  }
  .basket-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
  }
  .basket-row {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 0.5rem;
    padding: 0.5rem 0.7rem;
    background: var(--background, #f9fafb);
    border-radius: 8px;
    font-size: 0.85rem;
    flex-wrap: wrap;
  }
  .basket-pair {
    font-weight: 600;
    color: var(--text, #111827);
    min-width: 0;
  }
  .basket-plus {
    color: #4f46e5;
    font-weight: 700;
  }
  .basket-meta {
    display: inline-flex;
    align-items: baseline;
    gap: 0.3rem;
    flex-shrink: 0;
  }
  .basket-meta strong {
    font-weight: 700;
    color: var(--primary, #0f6b3e);
  }
  .basket-support {
    font-size: 0.75rem;
    color: var(--text-light, #6b7280);
  }

  .no-sales {
    text-align: center;
    padding: 2rem 1rem;
    color: var(--text-light, #6b7280);
  }
  .loading-state {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    padding: 2rem;
    color: var(--text-light, #6b7280);
    font-size: 0.9rem;
  }
  .spin {
    animation: spin 1s linear infinite;
  }
  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  /* Table */
  .table-wrapper {
    overflow-x: auto;
    background: var(--surface, #fff);
    border-radius: 10px;
    border: 1px solid var(--border, #e5e7eb);
  }
  .sales-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.9rem;
  }
  .sales-table th {
    text-align: left;
    padding: 0.75rem;
    background: var(--background, #f9fafb);
    font-weight: 600;
    color: var(--text-light, #6b7280);
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.3px;
    white-space: nowrap;
  }
  .sales-table td {
    padding: 0.75rem;
    border-top: 1px solid var(--border, #e5e7eb);
    color: var(--text, #111827);
    vertical-align: top;
  }
  .sales-table th.num,
  .sales-table td.num {
    text-align: right;
  }
  .expand-col {
    width: 32px;
    padding-right: 0 !important;
  }
  .actions-col {
    width: 90px;
    text-align: right;
  }
  .expand-btn {
    background: none;
    border: none;
    cursor: pointer;
    padding: 0.25rem;
    border-radius: 4px;
    color: var(--text-light, #6b7280);
    display: inline-flex;
    align-items: center;
    line-height: 0;
  }
  .expand-btn:hover {
    background: var(--background, #f9fafb);
    color: var(--text, #111827);
  }
  .sale-row-products {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
    min-width: 0;
  }
  .product-names {
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
  }
  .product-line {
    font-weight: 500;
    color: var(--text, #111827);
    font-size: 0.88rem;
  }
  .qty-inline {
    color: var(--text-light, #6b7280);
    font-weight: 500;
    font-size: 0.8rem;
    margin-left: 0.15rem;
  }
  .more-hint {
    font-size: 0.75rem;
    color: var(--text-light, #6b7280);
    font-style: italic;
  }
  .muted {
    color: var(--text-light, #6b7280);
  }
  .customer-tag {
    display: inline-block;
    font-size: 0.72rem;
    background: #eef2ff;
    color: #3730a3;
    border-radius: 6px;
    padding: 0.1rem 0.4rem;
    font-weight: 500;
    align-self: flex-start;
  }
  .paid-note {
    font-size: 0.72rem;
    color: #b45309;
    margin-top: 0.15rem;
    font-weight: 500;
    line-height: 1.3;
  }
  .date-cell {
    white-space: nowrap;
    font-size: 0.82rem;
    color: var(--text-light, #6b7280);
  }
  .row-actions {
    display: flex;
    gap: 0.25rem;
    justify-content: flex-end;
  }
  .void-reason {
    font-size: 0.72rem;
    color: #6b7280;
    margin-top: 0.15rem;
    font-style: italic;
  }
  .voided-row {
    opacity: 0.65;
    background: #fef2f2;
  }
  .badge {
    display: inline-block;
    padding: 0.2rem 0.55rem;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 600;
  }
  .badge.paid {
    background: #dcfce7;
    color: #166534;
  }
  .badge.credit {
    background: #fef3c7;
    color: #92400e;
  }
  .badge.partial {
    background: #fef3c7;
    color: #92400e;
  }
  .badge.voided {
    background: #fee2e2;
    color: #991b1b;
  }
  .btn-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.3rem;
    background: transparent;
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 8px;
    cursor: pointer;
    color: var(--text-light, #6b7280);
    padding: 0.4rem;
    transition: all 0.15s;
    font-size: 0.82rem;
  }
  .btn-icon:hover {
    border-color: var(--primary, #0f6b3e);
    color: var(--primary, #0f6b3e);
  }
  .btn-icon.danger:hover {
    border-color: var(--danger, #dc2626);
    color: var(--danger, #dc2626);
    background: #fef2f2;
  }
  .items-detail-row td {
    background: var(--background, #f9fafb);
    padding: 0.5rem 0.75rem 0.75rem;
  }
  .items-detail {
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 8px;
    padding: 0.55rem 0.75rem;
  }
  .items-detail-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.82rem;
  }
  .items-detail-table th {
    padding: 0.35rem 0.5rem;
    font-size: 0.7rem;
    color: var(--text-light, #6b7280);
    text-transform: uppercase;
    letter-spacing: 0.04em;
    background: transparent;
    border-bottom: 1px solid var(--border, #e5e7eb);
  }
  .items-detail-table td {
    padding: 0.4rem 0.5rem;
    border-top: 1px solid #f3f4f6;
    color: var(--text, #111827);
    font-size: 0.82rem;
  }
  .items-detail-table .num {
    text-align: right;
    white-space: nowrap;
  }
  .load-more-row {
    display: flex;
    justify-content: center;
    padding: 1rem 0;
  }

  /* Mobile */
  .mobile-sales {
    display: none;
    flex-direction: column;
    gap: 0.6rem;
  }
  .sale-card {
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 10px;
    padding: 0.85rem;
  }
  .sale-card.voided {
    opacity: 0.7;
    border-left: 3px solid #dc2626;
    background: #fef2f2;
  }
  .sale-card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.4rem;
  }
  .sale-card-header strong {
    color: var(--primary, #0f6b3e);
    font-size: 1.05rem;
    font-weight: 700;
  }
  .sale-customer {
    font-size: 0.82rem;
    color: var(--text, #111827);
    margin: 0 0 0.5rem;
    display: flex;
    flex-wrap: wrap;
    gap: 0.3rem;
    align-items: baseline;
  }
  .sale-paid-note {
    color: #b45309;
    font-size: 0.75rem;
  }
  .sale-paid-note.settled {
    color: #166534;
  }
  .sale-items-list {
    border-top: 1px dashed var(--border, #e5e7eb);
    border-bottom: 1px dashed var(--border, #e5e7eb);
    padding: 0.5rem 0;
    margin-bottom: 0.5rem;
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
  }
  .sale-item-line {
    display: grid;
    grid-template-columns: 1fr auto auto;
    gap: 0.5rem;
    align-items: baseline;
    font-size: 0.82rem;
  }
  .item-name {
    color: var(--text, #111827);
    font-weight: 500;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .item-detail {
    color: var(--text-light, #6b7280);
    font-size: 0.75rem;
    white-space: nowrap;
  }
  .item-total {
    color: var(--text, #111827);
    font-weight: 600;
    white-space: nowrap;
    text-align: right;
  }
  .sale-item-line.muted {
    color: var(--text-light, #6b7280);
    font-style: italic;
  }
  .void-reason {
    font-size: 0.72rem;
    color: #991b1b;
    font-style: italic;
    margin: 0.4rem 0 0;
    padding: 0.3rem 0.5rem;
    background: #fee2e2;
    border-radius: 6px;
  }
  .sale-card-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 0.5rem;
    margin-top: 0.5rem;
  }
  .sale-date {
    font-size: 0.72rem;
    color: var(--text-light, #6b7280);
  }
  .mobile-actions {
    display: flex;
    gap: 0.3rem;
  }

  /* Modals */
  .modal-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
    padding: 1rem;
  }
  .modal {
    background: var(--surface, #fff);
    border-radius: 12px;
    padding: 1.5rem;
    max-width: 440px;
    width: 100%;
    max-height: 90vh;
    overflow-y: auto;
  }
  .modal h3 {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-top: 0;
    margin-bottom: 0.75rem;
    color: var(--text, #111827);
    font-size: 1.05rem;
  }
  .void-summary {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 0.5rem;
    padding: 0.6rem 0.75rem;
    background: #fef2f2;
    border: 1px solid #fecaca;
    border-radius: 8px;
    margin-bottom: 0.75rem;
    font-size: 0.88rem;
  }
  .void-summary strong {
    color: #991b1b;
    font-size: 1rem;
    font-weight: 700;
  }
  .quick-reasons {
    display: flex;
    gap: 0.35rem;
    flex-wrap: wrap;
    margin-bottom: 0.75rem;
  }
  .reason-chip {
    padding: 0.35rem 0.7rem;
    border: 1px solid var(--border, #e5e7eb);
    background: var(--surface, #fff);
    border-radius: 20px;
    font-size: 0.78rem;
    font-weight: 500;
    color: var(--text, #111827);
    cursor: pointer;
    transition: all 0.15s;
  }
  .reason-chip:hover {
    border-color: var(--danger, #dc2626);
    color: var(--danger, #dc2626);
  }
  .reason-chip.active {
    background: var(--danger, #dc2626);
    border-color: var(--danger, #dc2626);
    color: white;
  }
  .form-group {
    margin-bottom: 0.85rem;
  }
  .form-group label {
    display: block;
    margin-bottom: 0.3rem;
    font-weight: 500;
    font-size: 0.88rem;
    color: var(--text, #111827);
  }
  .modal input {
    width: 100%;
    padding: 0.6rem;
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 8px;
    background: var(--surface, #fff);
    color: var(--text, #111827);
    font-size: 0.9rem;
    box-sizing: border-box;
  }
  .modal input:focus {
    outline: none;
    border-color: var(--primary, #0f6b3e);
    box-shadow: 0 0 0 3px rgba(15, 107, 62, 0.1);
  }
  .modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: 0.6rem;
    margin-top: 1.25rem;
  }

  @media (max-width: 768px) {
    .table-wrapper {
      display: none;
    }
    .mobile-sales {
      display: flex;
    }
    .date-pills {
      border-left: none;
      padding-left: 0;
    }
  }

  @media (max-width: 480px) {
    .sales-header {
      flex-wrap: wrap;
    }
    .btn {
      padding: 0.5rem 0.85rem;
      font-size: 0.85rem;
    }
  }
</style>