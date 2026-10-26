<script>
  import { createEventDispatcher, onMount } from "svelte";
  import { X, Loader2, ShoppingCart, Receipt, Wallet, BarChart3, CheckCircle2, AlertTriangle } from "lucide-svelte";
  import API from "../api/api";

  export let sessionId = null;
  const dispatch = createEventDispatcher();

  let loading = true;
  let error = null;
  let summary = null;
  let detail = null;
  let activeSection = "summary";

  onMount(async () => {
    try {
      const [s, d] = await Promise.all([
        API.get(`/sessions/${sessionId}/summary`),
        API.get(`/sessions/${sessionId}/detail`),
      ]);
      summary = s.data;
      detail = d.data;
    } catch (err) {
      error = err.response?.data?.detail || "Failed to load session details";
    } finally {
      loading = false;
    }
  });

  function close() {
    dispatch("close");
  }
  function handleKeydown(e) {
    if (e.key === "Escape") close();
  }
  function fmt(n) {
    return Number(n || 0).toLocaleString(undefined, {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  }
  function fmtDate(iso) {
    if (!iso) return "—";
    return new Date(iso).toLocaleString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  $: status = (() => {
    if (!summary) return "loading";
    if (summary.is_active) return "active";
    const d = summary.cash_drawer.discrepancy;
    if (d === null || d === undefined) return "not_reconciled";
    if (Math.abs(d) < 1) return "balanced";
    return d < 0 ? "short" : "over";
  })();
</script>

<svelte:window on:keydown={handleKeydown} />

<div class="drawer-overlay" role="presentation" on:click|self={close}></div>

<aside class="drawer" role="dialog" aria-modal="true" aria-label="Session details">
  <header class="drawer-header">
    <div>
      <h2>Session</h2>
      {#if summary?.opened_at}
        <p class="subtitle">{fmtDate(summary.opened_at)}</p>
      {/if}
    </div>
    <button class="close-btn" on:click={close} type="button" aria-label="Close">
      <X size={20} strokeWidth={2} />
    </button>
  </header>

  {#if loading}
    <div class="loading-state">
      <Loader2 size={22} class="spin" />
      <p>Loading session…</p>
    </div>
  {:else if error}
    <div class="error-box">{error}</div>
  {:else if summary}
    <div class="drawer-body">
      <!-- Section tabs -->
      <div class="section-tabs">
        <button type="button" class:active={activeSection === "summary"} on:click={() => (activeSection = "summary")}>
          <BarChart3 size={14} /> Summary
        </button>
        <button type="button" class:active={activeSection === "sales"} on:click={() => (activeSection = "sales")}>
          <ShoppingCart size={14} /> Sales ({detail?.sales?.length || 0})
        </button>
        <button type="button" class:active={activeSection === "expenses"} on:click={() => (activeSection = "expenses")}>
          <Receipt size={14} /> Expenses ({detail?.expenses?.length || 0})
        </button>
        <button type="button" class:active={activeSection === "payments"} on:click={() => (activeSection = "payments")}>
          <Wallet size={14} /> Payments ({detail?.payments?.length || 0})
        </button>
      </div>

      {#if activeSection === "summary"}
        <!-- Status band -->
        <div class="status-band status-{status}">
          {#if status === "active"}
            <BarChart3 size={16} /> Session in progress
          {:else if status === "balanced"}
            <CheckCircle2 size={16} /> Balanced — cash drawer correct
          {:else if status === "short"}
            <AlertTriangle size={16} /> Short by MWK {fmt(Math.abs(summary.cash_drawer.discrepancy))}
          {:else if status === "over"}
            <AlertTriangle size={16} /> Over by MWK {fmt(summary.cash_drawer.discrepancy)}
          {:else}
            Not reconciled
          {/if}
        </div>
        {#if summary.cash_drawer.discrepancy_reason}
          <p class="reason-text">Reason: {summary.cash_drawer.discrepancy_reason}</p>
        {/if}

        <!-- Drawer breakdown -->
        <div class="card">
          <h4>Cash drawer</h4>
          <div class="kv-row"><span>Opening balance</span><span>MWK {fmt(summary.cash_drawer.opening_balance)}</span></div>
          <div class="kv-row"><span>+ Cash sales</span><span>MWK {fmt(summary.cash_drawer.plus_cash_sales)}</span></div>
          <div class="kv-row"><span>+ Cash payments received</span><span>MWK {fmt(summary.cash_drawer.plus_cash_payments_received)}</span></div>
          {#if summary.cash_drawer.plus_cash_added > 0}
            <div class="kv-row"><span>+ Cash added</span><span>MWK {fmt(summary.cash_drawer.plus_cash_added)}</span></div>
          {/if}
          <div class="kv-row negative"><span>− Cash expenses</span><span>MWK {fmt(summary.cash_drawer.minus_expenses)}</span></div>
          {#if summary.cash_drawer.minus_cash_removed > 0}
            <div class="kv-row negative"><span>− Cash removed</span><span>MWK {fmt(summary.cash_drawer.minus_cash_removed)}</span></div>
          {/if}
          <div class="kv-row total"><span>Expected in drawer</span><strong>MWK {fmt(summary.cash_drawer.expected_in_drawer)}</strong></div>
          {#if summary.cash_drawer.physical_count !== null}
            <div class="kv-row"><span>Physical count</span><span>MWK {fmt(summary.cash_drawer.physical_count)}</span></div>
          {/if}
        </div>

        <!-- Sales summary -->
        <div class="card">
          <h4>Sales</h4>
          <div class="kv-row"><span>Total</span><span>MWK {fmt(summary.sales.total_sales)}</span></div>
          <div class="kv-row"><span>Cash</span><span>MWK {fmt(summary.sales.cash_sales)}</span></div>
          <div class="kv-row"><span>Credit</span><span>MWK {fmt(summary.sales.credit_sales)}</span></div>
          {#if summary.sales.voided_count > 0}
            <div class="kv-row"><span>Voided ({summary.sales.voided_count})</span><span>MWK {fmt(summary.sales.voided_amount)}</span></div>
          {/if}
        </div>

        <div class="card">
          <h4>Expenses</h4>
          <div class="kv-row"><span>Count</span><span>{summary.expenses.count}</span></div>
          <div class="kv-row total"><span>Total</span><strong>MWK {fmt(summary.expenses.total)}</strong></div>
        </div>
      {:else if activeSection === "sales"}
        {#if !detail?.sales?.length}
          <p class="empty-text">No sales in this session.</p>
        {:else}
          {#each detail.sales as s}
            <div class="item-row {s.is_voided ? 'voided' : ''}">
              <div class="item-head">
                <span class="item-title">{s.customer_name || "Walk-in"}</span>
                <span class="item-amount">MWK {fmt(s.total_amount)}</span>
              </div>
              <div class="item-sub">
                {fmtDate(s.created_at)} ·
                {s.payment_status}
                {#if s.is_voided}<span class="void-badge">VOIDED</span>{/if}
              </div>
              <div class="item-lines">
                {#each s.items as it}
                  <div class="item-line">
                    <span>{it.name}</span>
                    <span>{it.quantity} × {fmt(it.unit_price)}</span>
                    <span>MWK {fmt(it.total_price)}</span>
                  </div>
                {/each}
              </div>
            </div>
          {/each}
        {/if}
      {:else if activeSection === "expenses"}
        {#if !detail?.expenses?.length}
          <p class="empty-text">No expenses in this session.</p>
        {:else}
          {#each detail.expenses as e}
            <div class="item-row">
              <div class="item-head">
                <span class="item-title">{e.name}</span>
                <span class="item-amount">MWK {fmt(e.amount)}</span>
              </div>
              <div class="item-sub">{e.category} · {fmtDate(e.created_at)}</div>
            </div>
          {/each}
        {/if}
      {:else if activeSection === "payments"}
        {#if !detail?.payments?.length}
          <p class="empty-text">No customer payments in this session.</p>
        {:else}
          {#each detail.payments as p}
            <div class="item-row">
              <div class="item-head">
                <span class="item-title">{p.method}</span>
                <span class="item-amount">MWK {fmt(p.amount)}</span>
              </div>
              <div class="item-sub">{fmtDate(p.created_at)}</div>
            </div>
          {/each}
        {/if}
      {/if}
    </div>
  {/if}
</aside>

<style>
  .drawer-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.45);
    z-index: 1200;
    animation: fadeIn 0.15s ease-out;
  }
  @keyframes fadeIn {
    from {
      opacity: 0;
    }
    to {
      opacity: 1;
    }
  }
  .drawer {
    position: fixed;
    top: 0;
    right: 0;
    bottom: 0;
    width: min(480px, 100vw);
    background: var(--surface, #fff);
    z-index: 1201;
    display: flex;
    flex-direction: column;
    box-shadow: -8px 0 25px -8px rgba(0, 0, 0, 0.2);
    animation: slideIn 0.22s ease-out;
  }
  @keyframes slideIn {
    from {
      transform: translateX(100%);
    }
    to {
      transform: translateX(0);
    }
  }
  .drawer-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    padding: 1.1rem 1.25rem;
    border-bottom: 1px solid var(--border, #e5e7eb);
    gap: 0.5rem;
  }
  .drawer-header h2 {
    margin: 0;
    font-size: 1.15rem;
    font-weight: 700;
    color: var(--text, #111827);
  }
  .subtitle {
    margin: 0.2rem 0 0;
    font-size: 0.82rem;
    color: var(--text-light, #6b7280);
  }
  .close-btn {
    background: none;
    border: none;
    cursor: pointer;
    padding: 0.35rem;
    border-radius: 6px;
    color: var(--text-light, #6b7280);
    line-height: 0;
    flex-shrink: 0;
  }
  .close-btn:hover {
    background: var(--background, #f9fafb);
  }
  .loading-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 3rem 1rem;
    color: var(--text-light, #6b7280);
    gap: 0.6rem;
  }
  .spin {
    animation: spin 1s linear infinite;
  }
  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
  .error-box {
    background: #fee2e2;
    color: #991b1b;
    margin: 1rem;
    padding: 0.75rem 0.9rem;
    border-radius: 8px;
    font-size: 0.85rem;
  }
  .drawer-body {
    flex: 1;
    overflow-y: auto;
    padding: 0.85rem 1.25rem 1.25rem;
  }
  .section-tabs {
    display: flex;
    gap: 0.25rem;
    margin-bottom: 0.85rem;
    flex-wrap: wrap;
  }
  .section-tabs button {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.4rem 0.7rem;
    border-radius: 7px;
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    cursor: pointer;
    font-size: 0.78rem;
    font-weight: 500;
    color: var(--text-light, #6b7280);
    transition: all 0.15s;
  }
  .section-tabs button:hover {
    color: var(--text, #111827);
  }
  .section-tabs button.active {
    background: var(--primary, #0f6b3e);
    color: white;
    border-color: var(--primary, #0f6b3e);
  }
  .status-band {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.6rem 0.85rem;
    border-radius: 8px;
    margin-bottom: 0.75rem;
    font-size: 0.85rem;
    border: 1px solid;
  }
  .status-balanced {
    background: rgba(22, 163, 74, 0.1);
    color: #166534;
    border-color: #86efac;
  }
  .status-short {
    background: rgba(220, 38, 38, 0.1);
    color: #991b1b;
    border-color: #fecaca;
  }
  .status-over {
    background: rgba(234, 88, 12, 0.1);
    color: #9a3412;
    border-color: #fed7aa;
  }
  .status-active {
    background: rgba(59, 130, 246, 0.1);
    color: #1e40af;
    border-color: #bfdbfe;
  }
  .status-not_reconciled {
    background: var(--background, #f9fafb);
    color: var(--text-light, #6b7280);
    border-color: var(--border, #e5e7eb);
  }
  .reason-text {
    font-size: 0.8rem;
    color: var(--text-light, #6b7280);
    margin: 0 0 0.85rem;
    font-style: italic;
  }
  .card {
    background: var(--background, #f9fafb);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 10px;
    padding: 0.75rem 0.9rem;
    margin-bottom: 0.75rem;
  }
  .card h4 {
    margin: 0 0 0.5rem;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--text-light, #6b7280);
    font-weight: 700;
  }
  .kv-row {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    padding: 0.2rem 0;
    font-size: 0.85rem;
    color: var(--text, #111827);
    gap: 0.5rem;
  }
  .kv-row.negative span:last-child {
    color: #b91c1c;
  }
  .kv-row.total {
    border-top: 1px solid var(--border, #e5e7eb);
    padding-top: 0.5rem;
    margin-top: 0.35rem;
  }
  .kv-row.total strong {
    font-size: 1rem;
    color: var(--primary, #0f6b3e);
    font-weight: 700;
  }
  .empty-text {
    text-align: center;
    padding: 1.5rem 1rem;
    color: var(--text-light, #6b7280);
    font-size: 0.88rem;
  }
  .item-row {
    padding: 0.65rem 0.75rem;
    background: var(--background, #f9fafb);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 8px;
    margin-bottom: 0.5rem;
  }
  .item-row.voided {
    opacity: 0.6;
    border-left: 3px solid #dc2626;
  }
  .item-head {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 0.5rem;
    margin-bottom: 0.2rem;
  }
  .item-title {
    font-size: 0.9rem;
    font-weight: 600;
    color: var(--text, #111827);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    min-width: 0;
  }
  .item-amount {
    font-weight: 700;
    color: var(--text, #111827);
    font-size: 0.9rem;
    white-space: nowrap;
  }
  .item-sub {
    font-size: 0.72rem;
    color: var(--text-light, #6b7280);
    margin-bottom: 0.35rem;
  }
  .void-badge {
    background: #fee2e2;
    color: #991b1b;
    font-size: 0.62rem;
    font-weight: 700;
    padding: 0.05rem 0.35rem;
    border-radius: 4px;
    margin-left: 0.3rem;
  }
  .item-lines {
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
  }
  .item-line {
    display: grid;
    grid-template-columns: 1fr auto auto;
    gap: 0.5rem;
    align-items: baseline;
    font-size: 0.78rem;
    color: var(--text-light, #6b7280);
  }
  .item-line span:last-child {
    color: var(--text, #111827);
    font-weight: 600;
    white-space: nowrap;
  }
  @media (max-width: 640px) {
    .drawer {
      width: 100vw;
    }
  }
</style>