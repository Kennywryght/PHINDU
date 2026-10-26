<script>
  import { createEventDispatcher, onMount } from "svelte";
  import {
    X,
    Pencil,
    PackagePlus,
    Archive,
    RotateCcw,
    Trash2,
    TrendingUp,
    Clock,
    Package,
    DollarSign,
    Activity,
    Loader2,
  } from "lucide-svelte";
  import API from "../api/api";

  export let product = null;
  const dispatch = createEventDispatcher();

  let loading = true;
  let error = null;

  let priceHistory = null;
  let restocks = null;
  let sellSpeed = null;
  let prediction = null;

  onMount(async () => {
    if (!product?.id) {
      loading = false;
      return;
    }
    try {
      const [phRes, rsRes, ssRes, prRes] = await Promise.all([
        API.get(`/products/${product.id}/price-history`),
        API.get(`/products/${product.id}/restocks`),
        API.get(`/products/${product.id}/sell-speed`),
        API.get(`/products/${product.id}/restock-prediction`),
      ]);
      priceHistory = phRes.data;
      restocks = rsRes.data;
      sellSpeed = ssRes.data;
      prediction = prRes.data;
    } catch (err) {
      error = err.response?.data?.detail || "Failed to load product details";
      console.error(err);
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

  function onEdit() {
    dispatch("edit", product);
  }
  function onRestock() {
    dispatch("restock", product);
  }
  function onArchive() {
    dispatch("archive", product);
  }
  function onUnarchive() {
    dispatch("unarchive", product);
  }
  function onSoftDelete() {
    dispatch("softdelete", product);
  }

  function formatMoney(n) {
    return Number(n || 0).toLocaleString(undefined, { maximumFractionDigits: 2 });
  }

  function formatDate(iso) {
    if (!iso) return "—";
    return new Date(iso).toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  }

  function formatDateTime(iso) {
    if (!iso) return "—";
    return new Date(iso).toLocaleString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  function predClass(pred) {
    if (!pred || pred.days_until_restock === null) return "";
    const d = pred.days_until_restock;
    if (d <= 3) return "critical";
    if (d <= 7) return "soon";
    return "ok";
  }

  function predText(pred) {
    if (!pred) return "";
    if (pred.days_until_restock === null) return "Not enough data yet";
    const d = pred.days_until_restock;
    if (d < 0) return `Overdue by ${Math.abs(d)} days`;
    if (d === 0) return "Restock today";
    if (d === 1) return "Restock tomorrow";
    return `Restock in ~${d} days`;
  }
</script>

<svelte:window on:keydown={handleKeydown} />

<div
  class="drawer-overlay"
  role="presentation"
  on:click|self={close}
></div>

<aside class="drawer" role="dialog" aria-modal="true" aria-label="Product details">
  <header class="drawer-header">
    <div>
      <h2>{product?.name || "Product"}</h2>
      <p class="subtitle">
        {#if product?.category}{product.category} · {/if}
        {product?.unit || "unit"}
        {#if product?.parent_id}<span class="chip">variant</span>{/if}
      </p>
    </div>
    <button class="close-btn" on:click={close} type="button" aria-label="Close">
      <X size={20} strokeWidth={2} />
    </button>
  </header>

  {#if loading}
    <div class="loading-state">
      <Loader2 size={22} class="spin" />
      <p>Loading details…</p>
    </div>
  {:else if error}
    <div class="error-box">{error}</div>
  {:else}
    <div class="drawer-body">
      <!-- Overview -->
      <section class="section">
        <h3><DollarSign size={16} /> Overview</h3>
        <div class="kv-grid">
          <div><span>Selling price</span><strong>MWK {formatMoney(product.selling_price)}</strong></div>
          <div><span>Purchase price</span><strong>MWK {formatMoney(product.purchase_price)}</strong></div>
          <div><span>Current stock</span><strong>{product.stock_qty} {product.unit || ""}</strong></div>
          <div><span>Low-stock alert</span><strong>at {product.low_stock_threshold}</strong></div>
          {#if priceHistory?.product?.current_margin_percent != null}
            <div>
              <span>Current margin</span>
              <strong>{priceHistory.product.current_margin_percent.toFixed(1)}%</strong>
            </div>
          {/if}
        </div>
      </section>

      <!-- Prediction -->
      {#if prediction && prediction.method !== "no_data"}
        <section class="section">
          <h3><Clock size={16} /> Restock prediction</h3>
          <div class="prediction-card {predClass(prediction)}">
            <strong>{predText(prediction)}</strong>
            <div class="pred-meta">
              Method: {prediction.method === "batch_life" ? "Batch lifecycle" : "Sales velocity"}
              · Confidence: {prediction.confidence}
            </div>
          </div>
        </section>
      {/if}

      <!-- Sell speed -->
      {#if sellSpeed}
        <section class="section">
          <h3><Activity size={16} /> Sell speed</h3>
          {#if sellSpeed.batches_analyzed > 0}
            <div class="kv-grid">
              <div><span>Avg days to sell</span><strong>{sellSpeed.avg_days_to_sell ?? "—"}</strong></div>
              <div><span>Avg units / day</span><strong>{sellSpeed.avg_units_per_day ?? "—"}</strong></div>
              <div><span>Batches analyzed</span><strong>{sellSpeed.batches_analyzed}</strong></div>
            </div>
          {:else}
            <p class="muted">No finished batches yet. Sell through this product once to populate.</p>
          {/if}
        </section>
      {/if}

      <!-- Price history -->
      {#if priceHistory}
        <section class="section">
          <h3><TrendingUp size={16} /> Price history</h3>
          {#if priceHistory.history.length === 0}
            <p class="muted">No price changes recorded yet.</p>
          {:else}
            <ul class="history-list">
              {#each priceHistory.history.slice(0, 10) as h}
                <li class="history-row">
                  <span class="price-type type-{h.price_type}">
                    {h.price_type === "purchase" ? "Cost" : "Price"}
                  </span>
                  <span class="price-change">
                    MWK {formatMoney(h.old_price)} → <strong>MWK {formatMoney(h.new_price)}</strong>
                  </span>
                  {#if h.change_percent != null}
                    <span class="pct {h.change_percent > 0 ? 'up' : 'down'}">
                      {h.change_percent > 0 ? "+" : ""}{h.change_percent}%
                    </span>
                  {/if}
                  <span class="when">{formatDate(h.changed_at)}</span>
                </li>
              {/each}
            </ul>
          {/if}
        </section>
      {/if}

      <!-- Restock history -->
      {#if restocks}
        <section class="section">
          <h3><Package size={16} /> Restock history</h3>
          {#if restocks.batches.length === 0}
            <p class="muted">No restocks recorded yet.</p>
          {:else}
            <ul class="history-list">
              {#each restocks.batches.slice(0, 10) as b}
                <li class="history-row restock-row">
                  <span class="restock-qty">+{b.quantity_added}</span>
                  <span class="restock-detail">
                    {formatDateTime(b.date_added)}
                    {#if b.is_active}
                      <span class="badge active">active</span>
                    {:else if b.days_to_sell != null}
                      <span class="badge done">sold in {b.days_to_sell}d</span>
                    {/if}
                  </span>
                  {#if b.cost_per_unit != null}
                    <span class="restock-cost">@ MWK {formatMoney(b.cost_per_unit)}</span>
                  {/if}
                  {#if b.notes}
                    <span class="restock-notes">{b.notes}</span>
                  {/if}
                </li>
              {/each}
            </ul>
          {/if}
        </section>
      {/if}
    </div>

    <!-- Action bar -->
    <footer class="drawer-actions">
      {#if product?.archived}
        <button class="action-btn" on:click={onUnarchive} type="button">
          <RotateCcw size={16} /> Unarchive
        </button>
      {:else}
        <button class="action-btn" on:click={onArchive} type="button">
          <Archive size={16} /> Archive
        </button>
      {/if}
      {#if !product?.is_deleted && !product?.is_variant_parent}
        <button class="action-btn restock" on:click={onRestock} type="button">
          <PackagePlus size={16} /> Restock
        </button>
      {/if}
      <button class="action-btn" on:click={onEdit} type="button">
        <Pencil size={16} /> Edit
      </button>
      <button class="action-btn danger" on:click={onSoftDelete} type="button">
        <Trash2 size={16} /> Soft delete
      </button>
    </footer>
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
    from { opacity: 0; }
    to { opacity: 1; }
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
    max-width: 100%;
  }

  @keyframes slideIn {
    from { transform: translateX(100%); }
    to { transform: translateX(0); }
  }

  .drawer-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    padding: 1.1rem 1.25rem;
    border-bottom: 1px solid var(--border, #e5e7eb);
    flex-shrink: 0;
    gap: 0.5rem;
  }
  .drawer-header h2 {
    margin: 0;
    font-size: 1.15rem;
    font-weight: 700;
    color: var(--text, #111827);
    word-break: break-word;
  }
  .subtitle {
    margin: 0.15rem 0 0;
    font-size: 0.82rem;
    color: var(--text-light, #6b7280);
    display: flex;
    align-items: center;
    gap: 0.35rem;
    flex-wrap: wrap;
  }
  .chip {
    background: #dbeafe;
    color: #1e40af;
    font-size: 0.68rem;
    font-weight: 600;
    padding: 0.05rem 0.4rem;
    border-radius: 20px;
    text-transform: uppercase;
    letter-spacing: 0.03em;
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
  .spin { animation: spin 1s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }

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

  .section {
    margin-top: 0.9rem;
  }
  .section:first-child {
    margin-top: 0.4rem;
  }
  .section h3 {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    margin: 0 0 0.6rem;
    font-size: 0.82rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--text-light, #6b7280);
  }

  .kv-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.5rem 0.85rem;
  }
  .kv-grid div {
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
    padding: 0.5rem 0.6rem;
    background: var(--background, #f9fafb);
    border-radius: 8px;
  }
  .kv-grid span {
    font-size: 0.7rem;
    color: var(--text-light, #6b7280);
    text-transform: uppercase;
    letter-spacing: 0.03em;
    font-weight: 600;
  }
  .kv-grid strong {
    font-size: 0.92rem;
    color: var(--text, #111827);
    font-weight: 700;
    word-break: break-word;
  }

  .prediction-card {
    padding: 0.7rem 0.85rem;
    border-radius: 9px;
    border-left: 3px solid transparent;
    background: var(--background, #f9fafb);
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    font-size: 0.88rem;
  }
  .prediction-card.critical {
    background: #fee2e2;
    border-left-color: #dc2626;
    color: #991b1b;
  }
  .prediction-card.soon {
    background: #fef3c7;
    border-left-color: #ea580c;
    color: #92400e;
  }
  .prediction-card.ok {
    background: #dcfce7;
    border-left-color: #16a34a;
    color: #166534;
  }
  .pred-meta {
    font-size: 0.72rem;
    opacity: 0.8;
    text-transform: capitalize;
  }

  .muted {
    color: var(--text-light, #6b7280);
    font-size: 0.82rem;
    padding: 0.4rem 0;
  }

  .history-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
  }
  .history-row {
    display: flex;
    align-items: center;
    gap: 0.55rem;
    padding: 0.5rem 0.6rem;
    background: var(--background, #f9fafb);
    border-radius: 8px;
    font-size: 0.82rem;
    flex-wrap: wrap;
  }
  .price-type {
    font-weight: 600;
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    padding: 0.1rem 0.4rem;
    border-radius: 20px;
  }
  .type-selling {
    background: #dbeafe;
    color: #1e40af;
  }
  .type-purchase {
    background: #fce7f3;
    color: #9d174d;
  }
  .price-change {
    color: var(--text, #111827);
    font-size: 0.82rem;
  }
  .pct {
    font-weight: 600;
    font-size: 0.75rem;
  }
  .pct.up { color: #15803d; }
  .pct.down { color: #b91c1c; }
  .when {
    margin-left: auto;
    color: var(--text-light, #6b7280);
    font-size: 0.75rem;
  }

  .restock-row {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.15rem;
  }
  .restock-qty {
    font-weight: 700;
    color: var(--primary, #0f6b3e);
    font-size: 0.9rem;
  }
  .restock-detail {
    font-size: 0.78rem;
    color: var(--text-light, #6b7280);
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    flex-wrap: wrap;
  }
  .badge {
    font-size: 0.65rem;
    font-weight: 600;
    padding: 0.05rem 0.4rem;
    border-radius: 20px;
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }
  .badge.active {
    background: #dcfce7;
    color: #166534;
  }
  .badge.done {
    background: #e5e7eb;
    color: #4b5563;
  }
  .restock-cost {
    font-size: 0.78rem;
    color: var(--text, #111827);
  }
  .restock-notes {
    font-size: 0.75rem;
    color: var(--text-light, #6b7280);
    font-style: italic;
  }

  .drawer-actions {
    display: flex;
    gap: 0.4rem;
    flex-wrap: wrap;
    padding: 0.75rem 1.25rem;
    border-top: 1px solid var(--border, #e5e7eb);
    background: var(--surface, #fff);
    flex-shrink: 0;
  }
  .action-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.5rem 0.75rem;
    border-radius: 8px;
    border: 1px solid var(--border, #e5e7eb);
    background: transparent;
    cursor: pointer;
    font-size: 0.82rem;
    font-weight: 500;
    color: var(--text, #111827);
    transition: all 0.15s;
  }
  .action-btn:hover {
    background: var(--background, #f9fafb);
    border-color: var(--primary, #0f6b3e);
    color: var(--primary, #0f6b3e);
  }
  .action-btn.restock {
    background: var(--primary, #0f6b3e);
    color: white;
    border-color: var(--primary, #0f6b3e);
  }
  .action-btn.restock:hover {
    background: var(--primary-dark, #0a4f2e);
    color: white;
  }
  .action-btn.danger {
    color: #b91c1c;
    border-color: #fecaca;
  }
  .action-btn.danger:hover {
    background: #dc2626;
    color: white;
    border-color: #dc2626;
  }

  @media (max-width: 768px) {
    .drawer {
      width: 100vw;
    }
    .kv-grid {
      grid-template-columns: 1fr;
    }
    .drawer-actions .action-btn {
      flex: 1;
      justify-content: center;
    }
  }
</style>