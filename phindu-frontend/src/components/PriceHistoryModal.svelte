<script>
  import { onMount, createEventDispatcher } from "svelte";
  import { X, TrendingUp, TrendingDown, Minus } from "lucide-svelte";
  import API from "../api/api";

  export let productId;
  const dispatch = createEventDispatcher();

  let loading = true;
  let error = null;
  let product = null;
  let history = [];

  onMount(async () => {
    try {
      const res = await API.get(`/products/${productId}/price-history`);
      product = res.data.product;
      history = res.data.history;
    } catch (err) {
      error = "Failed to load price history";
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

  function formatDate(iso) {
    if (!iso) return "—";
    return new Date(iso).toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  function marginClass(pct) {
    if (pct === null || pct === undefined) return "";
    if (pct > 20) return "good";
    if (pct > 10) return "okay";
    if (pct > 0) return "low";
    return "bad";
  }
</script>

<svelte:window on:keydown={handleKeydown} />

<div
  class="modal-overlay"
  role="dialog"
  aria-modal="true"
  tabindex="-1"
  on:click|self={close}
>
  <div class="modal">
    <div class="modal-header">
      <div>
        <h2>Price History</h2>
        {#if product}
          <p class="product-name">{product.name} {product.unit ? `(${product.unit})` : ""}</p>
        {/if}
      </div>
      <button class="close-btn" on:click={close} type="button" aria-label="Close">
        <X size={20} strokeWidth={2} />
      </button>
    </div>

    {#if loading}
      <p class="state-text">Loading history...</p>
    {:else if error}
      <p class="state-text error">{error}</p>
    {:else}
      <!-- Current state summary -->
      <div class="current-state">
        <div class="stat">
          <span class="stat-label">Selling Price</span>
          <strong class="stat-value">MWK {product.current_selling_price?.toLocaleString()}</strong>
        </div>
        <div class="stat">
          <span class="stat-label">Purchase Price</span>
          <strong class="stat-value">MWK {product.current_purchase_price?.toLocaleString()}</strong>
        </div>
        <div class="stat">
          <span class="stat-label">Current Margin</span>
          <strong class="stat-value margin {marginClass(product.current_margin_percent)}">
            {#if product.current_margin_percent != null}
              {product.current_margin_percent.toFixed(1)}%
            {:else}
              —
            {/if}
          </strong>
        </div>
      </div>

      {#if history.length === 0}
        <p class="state-text">No price changes recorded yet.</p>
      {:else}
        <h3 class="section-title">All Changes</h3>
        <div class="history-list">
          {#each history as entry}
            <div class="history-item">
              <div class="type-badge {entry.price_type}">
                {entry.price_type === "purchase" ? "COST" : "SELL"}
              </div>
              <div class="history-details">
                <div class="price-change">
                  {#if entry.old_price === null || entry.old_price === 0}
                    <span class="new-only">Set to MWK {entry.new_price?.toLocaleString()}</span>
                  {:else}
                    <span class="old-price">MWK {entry.old_price?.toLocaleString()}</span>
                    <span class="arrow">→</span>
                    <span class="new-price">MWK {entry.new_price?.toLocaleString()}</span>
                    {#if entry.change_percent !== null}
                      {#if entry.change_percent > 0}
                        <span class="change-pct up">
                          <TrendingUp size={12} /> +{entry.change_percent}%
                        </span>
                      {:else if entry.change_percent < 0}
                        <span class="change-pct down">
                          <TrendingDown size={12} /> {entry.change_percent}%
                        </span>
                      {:else}
                        <span class="change-pct flat">
                          <Minus size={12} /> 0%
                        </span>
                      {/if}
                    {/if}
                  {/if}
                </div>
                <div class="history-date">{formatDate(entry.changed_at)}</div>
              </div>
            </div>
          {/each}
        </div>
      {/if}
    {/if}
  </div>
</div>

<style>
  .modal-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1100;
    padding: 1rem;
  }

  .modal {
    background: var(--surface, #fff);
    border-radius: 12px;
    padding: 1.5rem;
    max-width: 600px;
    width: 100%;
    max-height: 90vh;
    overflow-y: auto;
    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.15);
  }

  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 1.25rem;
    gap: 0.5rem;
  }

  .modal-header h2 {
    margin: 0;
    font-size: 1.15rem;
    font-weight: 600;
    color: var(--text, #111827);
  }

  .product-name {
    margin: 0.25rem 0 0;
    font-size: 0.88rem;
    color: var(--text-light, #6b7280);
  }

  .close-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: none;
    border: none;
    cursor: pointer;
    padding: 0.35rem;
    border-radius: 6px;
    color: var(--text-light, #6b7280);
    line-height: 0;
  }

  .close-btn:hover {
    background: var(--background, #f9fafb);
  }

  .state-text {
    text-align: center;
    padding: 1.5rem;
    color: var(--text-light, #6b7280);
    font-size: 0.9rem;
  }

  .state-text.error {
    color: var(--danger, #dc2626);
  }

  .current-state {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 0.75rem;
    background: var(--background, #f9fafb);
    border-radius: 10px;
    padding: 1rem;
    margin-bottom: 1.25rem;
  }

  .stat {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .stat-label {
    font-size: 0.72rem;
    color: var(--text-light, #6b7280);
    text-transform: uppercase;
    letter-spacing: 0.3px;
    font-weight: 500;
  }

  .stat-value {
    font-size: 0.95rem;
    font-weight: 700;
    color: var(--text, #111827);
  }

  .stat-value.margin.good {
    color: #16a34a;
  }

  .stat-value.margin.okay {
    color: #ca8a04;
  }

  .stat-value.margin.low {
    color: #ea580c;
  }

  .stat-value.margin.bad {
    color: #dc2626;
  }

  .section-title {
    margin: 0 0 0.75rem;
    font-size: 0.88rem;
    font-weight: 600;
    color: var(--text, #111827);
    text-transform: uppercase;
    letter-spacing: 0.3px;
  }

  .history-list {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .history-item {
    display: flex;
    gap: 0.75rem;
    align-items: flex-start;
    padding: 0.7rem;
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 8px;
  }

  .type-badge {
    font-size: 0.65rem;
    font-weight: 700;
    padding: 0.2rem 0.5rem;
    border-radius: 4px;
    letter-spacing: 0.3px;
    flex-shrink: 0;
  }

  .type-badge.selling {
    background: #dbeafe;
    color: #1e40af;
  }

  .type-badge.purchase {
    background: #fef3c7;
    color: #92400e;
  }

  .history-details {
    flex: 1;
    min-width: 0;
  }

  .price-change {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    flex-wrap: wrap;
    font-size: 0.9rem;
  }

  .old-price {
    color: var(--text-light, #6b7280);
    text-decoration: line-through;
  }

  .arrow {
    color: var(--text-light, #6b7280);
    font-size: 0.8rem;
  }

  .new-price {
    font-weight: 600;
    color: var(--text, #111827);
  }

  .new-only {
    font-weight: 600;
    color: var(--text, #111827);
  }

  .change-pct {
    display: inline-flex;
    align-items: center;
    gap: 0.15rem;
    font-size: 0.78rem;
    font-weight: 600;
    padding: 0.1rem 0.4rem;
    border-radius: 20px;
  }

  .change-pct.up {
    background: #dcfce7;
    color: #166534;
  }

  .change-pct.down {
    background: #fee2e2;
    color: #991b1b;
  }

  .change-pct.flat {
    background: var(--background, #f9fafb);
    color: var(--text-light, #6b7280);
  }

  .history-date {
    font-size: 0.75rem;
    color: var(--text-light, #6b7280);
    margin-top: 0.2rem;
  }

  @media (max-width: 480px) {
    .modal-overlay {
      padding: 0.75rem;
    }

    .modal {
      padding: 1.15rem;
      border-radius: 10px;
    }

    .current-state {
      grid-template-columns: 1fr;
      gap: 0.5rem;
    }

    .stat {
      flex-direction: row;
      justify-content: space-between;
      align-items: center;
    }
  }
</style>