<script>
  import { onMount } from "svelte";
  import {
    AlertTriangle,
    CheckCircle2,
    Package,
    Users,
    Clock,
    PackageX,
    AlertCircle,
    TrendingDown,
    DollarSign,
    Phone,
    ShoppingCart,
    RefreshCw,
  } from "lucide-svelte";
  import Layout from "../components/Layout.svelte";
  import RestockModal from "../components/RestockModal.svelte";
  import API from "../api/api";

  let activeTab = "low-stock";

  // Data
  let lowStock = [];
  let debtors = [];
  let slowMovers = [];
  let reorder = { critical: [], soon: [], ok: [], no_data: [] };
  let summary = {
    low_stock: 0,
    debtors: 0,
    slow_movers: 0,
    reorder: 0,
    total: 0,
  };

  // State
  let loading = true;
  let error = null;

  // Restock modal
  let showRestockModal = false;
  let restockingProduct = null;

  onMount(async () => {
    await Promise.all([
      fetchLowStock(),
      fetchDebtors(),
      fetchSlowMovers(),
      fetchReorder(),
      fetchSummary(),
    ]);
    loading = false;
  });

  async function fetchLowStock() {
    try {
      const res = await API.get("/alerts/low-stock");
      lowStock = res.data;
    } catch (err) {
      console.error("Failed to fetch low stock", err);
      error = "Could not fetch low stock alerts.";
    }
  }

  async function fetchDebtors() {
    try {
      const res = await API.get("/alerts/debtors?days=14");
      debtors = res.data;
    } catch (err) {
      console.error("Failed to fetch debtors", err);
    }
  }

  async function fetchSlowMovers() {
    try {
      const res = await API.get("/alerts/slow-movers?days=30");
      slowMovers = res.data;
    } catch (err) {
      console.error("Failed to fetch slow movers", err);
    }
  }

  async function fetchReorder() {
    try {
      const res = await API.get("/alerts/reorder-suggestions?lookback_days=30&target_days=7");
      reorder = res.data;
    } catch (err) {
      console.error("Failed to fetch reorder suggestions", err);
    }
  }

  async function fetchSummary() {
    try {
      const res = await API.get("/alerts/summary");
      summary = res.data;
    } catch (err) {
      console.error("Failed to fetch summary", err);
    }
  }

  async function refreshAll() {
    loading = true;
    await Promise.all([
      fetchLowStock(),
      fetchDebtors(),
      fetchSlowMovers(),
      fetchReorder(),
      fetchSummary(),
    ]);
    loading = false;
  }

  function severityLabel(severity) {
    if (severity === "out_of_stock") return "OUT OF STOCK";
    if (severity === "critical") return "CRITICAL";
    return "LOW";
  }

  function severityClass(severity) {
    if (severity === "out_of_stock") return "out-of-stock";
    if (severity === "critical") return "critical";
    return "low";
  }

  function formatDate(isoString) {
    if (!isoString) return "—";
    return new Date(isoString).toLocaleDateString();
  }

  function goToProducts() {
    window.location.href = "/products";
  }

  function goToCredit() {
    window.location.href = "/credit";
  }

  // Open restock modal for a product suggestion
  function openRestock(product) {
    // Build minimal product object expected by RestockModal
    restockingProduct = {
      id: product.product_id,
      name: product.name,
      stock_qty: product.stock_qty,
      unit: product.unit,
      purchase_price: product.purchase_price || 0,
    };
    showRestockModal = true;
  }

  function closeRestock() {
    showRestockModal = false;
    restockingProduct = null;
  }

  async function handleRestockSaved() {
    closeRestock();
    // Refresh all data (stock changed, reorder suggestions changed)
    await refreshAll();
  }
</script>

<Layout title="Alerts">
  <div class="alerts-page">
    <div class="page-header">
      <div>
        <h2>
          <AlertTriangle size={22} strokeWidth={2} />
          Alerts
        </h2>
        <p class="subtitle">What needs your attention today</p>
      </div>
      <button class="refresh-btn" on:click={refreshAll} disabled={loading} type="button">
        <RefreshCw size={16} strokeWidth={2} />
        Refresh
      </button>
    </div>

    {#if loading}
      <div class="state-box">Checking your business...</div>
    {:else}
      <!-- Tabs -->
      <div class="tabs">
        <button
          type="button"
          class="tab"
          class:active={activeTab === "reorder"}
          on:click={() => (activeTab = "reorder")}
        >
          <ShoppingCart size={16} strokeWidth={2} />
          <span>Reorder</span>
          {#if summary.reorder > 0}
            <span class="badge reorder-badge">{summary.reorder}</span>
          {/if}
        </button>

        <button
          type="button"
          class="tab"
          class:active={activeTab === "low-stock"}
          on:click={() => (activeTab = "low-stock")}
        >
          <Package size={16} strokeWidth={2} />
          <span>Low Stock</span>
          {#if summary.low_stock > 0}
            <span class="badge">{summary.low_stock}</span>
          {/if}
        </button>

        <button
          type="button"
          class="tab"
          class:active={activeTab === "debtors"}
          on:click={() => (activeTab = "debtors")}
        >
          <Users size={16} strokeWidth={2} />
          <span>Debtors</span>
          {#if summary.debtors > 0}
            <span class="badge">{summary.debtors}</span>
          {/if}
        </button>

        <button
          type="button"
          class="tab"
          class:active={activeTab === "slow-movers"}
          on:click={() => (activeTab = "slow-movers")}
        >
          <TrendingDown size={16} strokeWidth={2} />
          <span>Slow Movers</span>
          {#if summary.slow_movers > 0}
            <span class="badge">{summary.slow_movers}</span>
          {/if}
        </button>
      </div>

      <!-- TAB CONTENT: REORDER -->
      {#if activeTab === "reorder"}
        {#if reorder.critical.length === 0 &&
          reorder.soon.length === 0 &&
          reorder.ok.length === 0 &&
          reorder.no_data.length === 0}
          <div class="card success-card">
            <CheckCircle2 size={48} strokeWidth={1.5} class="success-icon" />
            <h3>No reorder data yet</h3>
            <p>Add products and make sales to see smart reorder suggestions.</p>
          </div>
        {:else}
          <!-- Critical -->
          {#if reorder.critical.length > 0}
            <div class="reorder-group">
              <div class="group-header critical-header">
                <AlertCircle size={18} strokeWidth={2} />
                <span>Critical — Reorder Now</span>
                <span class="group-count">{reorder.critical.length}</span>
              </div>
              <div class="reorder-list">
                {#each reorder.critical as item}
                  <div class="reorder-card critical-card">
                    <div class="reorder-info">
                      <h3>{item.name}</h3>
                      <div class="reorder-meta">
                        <span>
                          <strong>{item.stock_qty}</strong> {item.unit} left
                        </span>
                        <span>
                          Selling <strong>{item.avg_daily_sales}</strong>/day
                        </span>
                        <span class="urgency-text">
                          {item.days_remaining !== null
                            ? `${item.days_remaining} days left`
                            : "OUT"}
                        </span>
                        <span class="confidence confidence-{item.confidence}">
                          {item.confidence} confidence
                        </span>
                      </div>
                      <div class="suggestion">
                        <strong>Order {item.suggested_order_qty} {item.unit}</strong>
                        {#if item.purchase_price}
                          <span class="cost">
                            (≈ MWK {(item.suggested_order_qty * item.purchase_price).toLocaleString()})
                          </span>
                        {/if}
                      </div>
                    </div>
                    <button class="btn-action primary" on:click={() => openRestock(item)} type="button">
                      Restock Now
                    </button>
                  </div>
                {/each}
              </div>
            </div>
          {/if}

          <!-- Soon -->
          {#if reorder.soon.length > 0}
            <div class="reorder-group">
              <div class="group-header soon-header">
                <Clock size={18} strokeWidth={2} />
                <span>Soon — Order This Week</span>
                <span class="group-count">{reorder.soon.length}</span>
              </div>
              <div class="reorder-list">
                {#each reorder.soon as item}
                  <div class="reorder-card soon-card">
                    <div class="reorder-info">
                      <h3>{item.name}</h3>
                      <div class="reorder-meta">
                        <span>
                          <strong>{item.stock_qty}</strong> {item.unit} left
                        </span>
                        <span>
                          Selling <strong>{item.avg_daily_sales}</strong>/day
                        </span>
                        <span class="urgency-text">
                          {item.days_remaining !== null
                            ? `${item.days_remaining} days left`
                            : "—"}
                        </span>
                        <span class="confidence confidence-{item.confidence}">
                          {item.confidence} confidence
                        </span>
                      </div>
                      <div class="suggestion">
                        <strong>Suggest ordering {item.suggested_order_qty} {item.unit}</strong>
                      </div>
                    </div>
                    <button class="btn-action" on:click={() => openRestock(item)} type="button">
                      Restock
                    </button>
                  </div>
                {/each}
              </div>
            </div>
          {/if}

          <!-- OK -->
          {#if reorder.ok.length > 0}
            <div class="reorder-group">
              <div class="group-header ok-header">
                <CheckCircle2 size={18} strokeWidth={2} />
                <span>OK — Well Stocked</span>
                <span class="group-count">{reorder.ok.length}</span>
              </div>
              <div class="reorder-list">
                {#each reorder.ok as item}
                  <div class="reorder-card ok-card">
                    <div class="reorder-info">
                      <h3>{item.name}</h3>
                      <div class="reorder-meta">
                        <span>
                          <strong>{item.stock_qty}</strong> {item.unit} left
                        </span>
                        <span>
                          Selling <strong>{item.avg_daily_sales}</strong>/day
                        </span>
                        <span class="urgency-text">
                          {item.days_remaining !== null
                            ? `${item.days_remaining} days left`
                            : "—"}
                        </span>
                      </div>
                    </div>
                  </div>
                {/each}
              </div>
            </div>
          {/if}

          <!-- No Data -->
          {#if reorder.no_data.length > 0}
            <div class="reorder-group">
              <div class="group-header no-data-header">
                <AlertTriangle size={18} strokeWidth={2} />
                <span>Not Enough Sales History</span>
                <span class="group-count">{reorder.no_data.length}</span>
              </div>
              <div class="reorder-list">
                {#each reorder.no_data as item}
                  <div class="reorder-card no-data-card">
                    <div class="reorder-info">
                      <h3>{item.name}</h3>
                      <div class="reorder-meta">
                        <span>
                          <strong>{item.stock_qty}</strong> {item.unit} in stock
                        </span>
                        <span class="muted">No sales in last 30 days</span>
                      </div>
                    </div>
                  </div>
                {/each}
              </div>
            </div>
          {/if}
        {/if}
      {/if}

      <!-- TAB CONTENT: LOW STOCK -->
      {#if activeTab === "low-stock"}
        {#if lowStock.length === 0}
          <div class="card success-card">
            <CheckCircle2 size={48} strokeWidth={1.5} class="success-icon" />
            <h3>All products are well stocked</h3>
            <p>No low stock alerts at this time.</p>
          </div>
        {:else}
          <div class="alert-list">
            {#each lowStock as product}
              <div class="alert-item severity-{severityClass(product.severity)}">
                <div class="alert-severity">
                  {#if product.severity === "out_of_stock"}
                    <PackageX size={20} strokeWidth={2} />
                  {:else if product.severity === "critical"}
                    <AlertCircle size={20} strokeWidth={2} />
                  {:else}
                    <AlertTriangle size={20} strokeWidth={2} />
                  {/if}
                  <span class="severity-label">{severityLabel(product.severity)}</span>
                </div>
                <div class="alert-content">
                  <h3>{product.name}</h3>
                  <div class="alert-meta">
                    <span>Stock: <strong>{product.stock_qty}</strong> {product.unit}</span>
                    <span>Threshold: {product.low_stock_threshold}</span>
                    <span>MWK {product.selling_price?.toLocaleString()}</span>
                  </div>
                </div>
                <button class="btn-action" on:click={goToProducts} type="button">
                  Manage
                </button>
              </div>
            {/each}
          </div>
        {/if}
      {/if}

      <!-- TAB CONTENT: DEBTORS -->
      {#if activeTab === "debtors"}
        {#if debtors.length === 0}
          <div class="card success-card">
            <CheckCircle2 size={48} strokeWidth={1.5} class="success-icon" />
            <h3>No aging debtors</h3>
            <p>All customers are up to date on payments.</p>
          </div>
        {:else}
          <div class="alert-list">
            {#each debtors as debtor}
              <div class="alert-item severity-debtor">
                <div class="alert-severity">
                  <Clock size={20} strokeWidth={2} />
                  <span class="severity-label">
                    {#if debtor.never_paid}
                      NEVER PAID
                    {:else}
                      {debtor.days_since_last_payment}d AGO
                    {/if}
                  </span>
                </div>
                <div class="alert-content">
                  <h3>{debtor.name}</h3>
                  <div class="alert-meta">
                    <span class="amount">Owes MWK {debtor.total_credit?.toLocaleString()}</span>
                    {#if debtor.phone}
                      <span><Phone size={12} /> {debtor.phone}</span>
                    {/if}
                    {#if debtor.last_payment_date}
                      <span>Last paid: {formatDate(debtor.last_payment_date)}</span>
                    {:else}
                      <span class="warning">No payments on record</span>
                    {/if}
                  </div>
                </div>
                <button class="btn-action" on:click={goToCredit} type="button">
                  <DollarSign size={14} strokeWidth={2} />
                  Payment
                </button>
              </div>
            {/each}
          </div>
        {/if}
      {/if}

      <!-- TAB CONTENT: SLOW MOVERS -->
      {#if activeTab === "slow-movers"}
        {#if slowMovers.length === 0}
          <div class="card success-card">
            <CheckCircle2 size={48} strokeWidth={1.5} class="success-icon" />
            <h3>All products are moving</h3>
            <p>Every in-stock product has sold recently.</p>
          </div>
        {:else}
          <div class="alert-list">
            {#each slowMovers as product}
              <div class="alert-item severity-slow">
                <div class="alert-severity">
                  <TrendingDown size={20} strokeWidth={2} />
                  <span class="severity-label">
                    {#if product.never_sold}
                      NEVER SOLD
                    {:else}
                      {product.days_since_last_sale}d
                    {/if}
                  </span>
                </div>
                <div class="alert-content">
                  <h3>{product.name}</h3>
                  <div class="alert-meta">
                    <span>In stock: <strong>{product.stock_qty}</strong> {product.unit}</span>
                    <span>MWK {product.selling_price?.toLocaleString()}</span>
                    {#if product.last_sale_date}
                      <span>Last sale: {formatDate(product.last_sale_date)}</span>
                    {:else}
                      <span class="warning">Never sold</span>
                    {/if}
                  </div>
                </div>
                <button class="btn-action" on:click={goToProducts} type="button">
                  View
                </button>
              </div>
            {/each}
          </div>
        {/if}
      {/if}
    {/if}
  </div>
</Layout>

{#if showRestockModal && restockingProduct}
  <RestockModal
    product={restockingProduct}
    on:saved={handleRestockSaved}
    on:close={closeRestock}
  />
{/if}

<style>
  .alerts-page {
    max-width: 900px;
    margin: 0 auto;
  }

  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 1.5rem;
    gap: 1rem;
    flex-wrap: wrap;
  }

  .page-header h2 {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin: 0;
    font-size: 1.2rem;
    font-weight: 600;
    color: var(--text, #111827);
  }

  .subtitle {
    color: var(--text-light, #6b7280);
    margin-top: 0.25rem;
    font-size: 0.88rem;
  }

  .refresh-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.45rem 0.85rem;
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 8px;
    cursor: pointer;
    font-size: 0.85rem;
    font-weight: 500;
    color: var(--text, #111827);
    transition: all 0.15s;
    flex-shrink: 0;
  }

  .refresh-btn:hover:not(:disabled) {
    border-color: var(--primary, #0f6b3e);
    color: var(--primary, #0f6b3e);
  }

  .refresh-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .state-box {
    text-align: center;
    padding: 2rem;
    color: var(--text-light, #6b7280);
    font-size: 0.9rem;
  }

  /* ============ TABS ============ */
  .tabs {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 1.25rem;
    border-bottom: 1px solid var(--border, #e5e7eb);
    overflow-x: auto;
    padding-bottom: 0.5rem;
  }

  .tab {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.6rem 1rem;
    background: transparent;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    font-weight: 500;
    font-size: 0.9rem;
    color: var(--text-light, #6b7280);
    transition: all 0.15s;
    white-space: nowrap;
  }

  .tab:hover {
    background: var(--background, #f9fafb);
    color: var(--text, #111827);
  }

  .tab.active {
    background: var(--primary, #0f6b3e);
    color: white;
  }

  .tab .badge {
    background: rgba(255, 255, 255, 0.25);
    color: inherit;
    font-size: 0.7rem;
    font-weight: 700;
    padding: 0.1rem 0.4rem;
    border-radius: 10px;
    min-width: 18px;
    text-align: center;
  }

  .tab:not(.active) .badge {
    background: var(--danger, #dc2626);
    color: white;
  }

  .tab:not(.active) .badge.reorder-badge {
    background: #ea580c;
  }

  /* ============ REORDER GROUPS ============ */
  .reorder-group {
    margin-bottom: 1.5rem;
  }

  .group-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.85rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.4px;
    margin-bottom: 0.6rem;
    padding: 0.5rem 0.75rem;
    border-radius: 8px;
  }

  .group-header.critical-header {
    background: #fee2e2;
    color: #991b1b;
  }

  .group-header.soon-header {
    background: #ffedd5;
    color: #9a3412;
  }

  .group-header.ok-header {
    background: #dcfce7;
    color: #166534;
  }

  .group-header.no-data-header {
    background: var(--background, #f9fafb);
    color: var(--text-light, #6b7280);
  }

  .group-count {
    margin-left: auto;
    background: rgba(0, 0, 0, 0.1);
    padding: 0.1rem 0.5rem;
    border-radius: 20px;
    font-size: 0.75rem;
  }

  .reorder-list {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .reorder-card {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 0.9rem 1rem;
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    border-left: 4px solid var(--border, #e5e7eb);
    border-radius: 10px;
  }

  .critical-card {
    border-left-color: #dc2626;
    background: #fef2f2;
  }

  .soon-card {
    border-left-color: #ea580c;
    background: #fff7ed;
  }

  .ok-card {
    border-left-color: #16a34a;
    background: #f0fdf4;
  }

  .no-data-card {
    border-left-color: var(--border, #e5e7eb);
    background: var(--background, #f9fafb);
    opacity: 0.85;
  }

  .reorder-info {
    flex: 1;
    min-width: 0;
  }

  .reorder-info h3 {
    margin: 0 0 0.35rem;
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--text, #111827);
  }

  .reorder-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem 0.9rem;
    font-size: 0.78rem;
    color: var(--text-light, #6b7280);
    margin-bottom: 0.4rem;
    align-items: center;
  }

  .reorder-meta strong {
    color: var(--text, #111827);
    font-weight: 600;
  }

  .urgency-text {
    color: #dc2626;
    font-weight: 600;
  }

  .soon-card .urgency-text {
    color: #ea580c;
  }

  .ok-card .urgency-text {
    color: #16a34a;
  }

  .confidence {
    font-size: 0.68rem;
    padding: 0.1rem 0.4rem;
    border-radius: 4px;
    font-weight: 600;
    text-transform: uppercase;
  }

  .confidence-high {
    background: #dcfce7;
    color: #166534;
  }

  .confidence-medium {
    background: #fef3c7;
    color: #92400e;
  }

  .confidence-low {
    background: #fee2e2;
    color: #991b1b;
  }

  .suggestion {
    font-size: 0.85rem;
    color: var(--text, #111827);
  }

  .suggestion strong {
    font-weight: 700;
    color: var(--primary, #0f6b3e);
  }

  .suggestion .cost {
    font-size: 0.78rem;
    color: var(--text-light, #6b7280);
    margin-left: 0.4rem;
  }

  .muted {
    color: var(--text-light, #6b7280);
    font-style: italic;
  }

  /* ============ ALERT LIST (existing tabs) ============ */
  .alert-list {
    display: flex;
    flex-direction: column;
    gap: 0.65rem;
  }

  .alert-item {
    display: flex;
    align-items: center;
    gap: 1rem;
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    border-left: 4px solid var(--border, #e5e7eb);
    border-radius: 10px;
    padding: 1rem;
    transition: all 0.15s;
  }

  .alert-item:hover {
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  }

  .alert-item.severity-out-of-stock {
    border-left-color: #dc2626;
    background: #fef2f2;
  }

  .alert-item.severity-critical {
    border-left-color: #ea580c;
    background: #fff7ed;
  }

  .alert-item.severity-low {
    border-left-color: #eab308;
    background: #fefce8;
  }

  .alert-item.severity-debtor {
    border-left-color: #7c3aed;
    background: #f5f3ff;
  }

  .alert-item.severity-slow {
    border-left-color: #0891b2;
    background: #ecfeff;
  }

  .alert-severity {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.25rem;
    min-width: 70px;
    flex-shrink: 0;
  }

  .alert-severity svg {
    color: inherit;
  }

  .severity-out-of-stock .alert-severity {
    color: #dc2626;
  }

  .severity-critical .alert-severity {
    color: #ea580c;
  }

  .severity-low .alert-severity {
    color: #ca8a04;
  }

  .severity-debtor .alert-severity {
    color: #7c3aed;
  }

  .severity-slow .alert-severity {
    color: #0891b2;
  }

  .severity-label {
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.4px;
    text-transform: uppercase;
    text-align: center;
  }

  .alert-content {
    flex: 1;
    min-width: 0;
  }

  .alert-content h3 {
    margin: 0 0 0.35rem;
    font-size: 1rem;
    font-weight: 600;
    color: var(--text, #111827);
  }

  .alert-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
    font-size: 0.82rem;
    color: var(--text-light, #6b7280);
    align-items: center;
  }

  .alert-meta span {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
  }

  .alert-meta .amount {
    color: #dc2626;
    font-weight: 700;
    font-size: 0.9rem;
  }

  .alert-meta .warning {
    color: #ea580c;
    font-weight: 600;
  }

  .btn-action {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.5rem 1rem;
    background: var(--primary, #0f6b3e);
    color: white;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    font-weight: 500;
    font-size: 0.85rem;
    flex-shrink: 0;
    transition: background 0.15s;
  }

  .btn-action.primary {
    background: #dc2626;
  }

  .btn-action.primary:hover {
    background: #991b1b;
  }

  .btn-action:hover {
    background: var(--primary-dark, #0a4f2e);
  }

  /* ============ SUCCESS CARD ============ */
  .card {
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 12px;
    padding: 1.25rem;
  }

  .success-card {
    text-align: center;
    padding: 3rem 1.5rem;
  }

  .success-icon {
    color: var(--success, #16a34a);
    margin-bottom: 1rem;
  }

  .success-card h3 {
    margin: 0 0 0.5rem;
    font-size: 1.05rem;
    font-weight: 600;
    color: var(--text, #111827);
  }

  .success-card p {
    color: var(--text-light, #6b7280);
    margin: 0;
    font-size: 0.9rem;
  }

  /* ============ MOBILE ============ */
  @media (max-width: 640px) {
    .alert-item,
    .reorder-card {
      flex-direction: column;
      align-items: stretch;
      gap: 0.75rem;
    }

    .alert-severity {
      flex-direction: row;
      justify-content: flex-start;
      min-width: 0;
    }

    .severity-label {
      text-align: left;
    }

    .btn-action {
      width: 100%;
      justify-content: center;
    }

    .group-header {
      font-size: 0.78rem;
    }
  }
</style>