<script>
  import { onMount, createEventDispatcher } from "svelte";
  import { X, Package, TrendingUp, AlertCircle } from "lucide-svelte";
  import API from "../api/api";

  export let productId;
  const dispatch = createEventDispatcher();

  let loading = true;
  let error = null;
  let data = null;

  onMount(async () => {
    try {
      const res = await API.get(`/products/${productId}/restocks`);
      data = res.data;
    } catch (err) {
      error = "Failed to load restock history";
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
    });
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
        <h2>Restock History</h2>
        {#if data?.product}
          <p class="product-name">
            {data.product.name} {data.product.unit ? `(${data.product.unit})` : ""}
          </p>
        {/if}
      </div>
      <button class="close-btn" on:click={close} type="button" aria-label="Close">
        <X size={20} strokeWidth={2} />
      </button>
    </div>

    {#if loading}
      <p class="state-text">Loading restock history...</p>
    {:else if error}
      <p class="state-text error">{error}</p>
    {:else if data}
      <!-- Summary -->
      <div class="summary-grid">
        <div class="stat">
          <span class="stat-label">Current Stock</span>
          <strong class="stat-value">
            {data.product.current_stock}
            {data.product.unit || ""}
          </strong>
        </div>
        <div class="stat">
          <span class="stat-label">Total Restocks</span>
          <strong class="stat-value">{data.summary.total_restocks}</strong>
        </div>
        <div class="stat">
          <span class="stat-label">Avg Days to Sell</span>
          <strong class="stat-value">
            {#if data.summary.avg_days_to_sell != null}
              {data.summary.avg_days_to_sell} days
            {:else}
              —
            {/if}
          </strong>
        </div>
      </div>

      {#if data.summary.last_restock_date}
        <p class="last-restock">
          Last restock: {formatDate(data.summary.last_restock_date)}
        </p>
      {/if}

      <!-- Batch timeline -->
      {#if data.batches.length === 0}
        <p class="state-text">No restocks recorded yet.</p>
      {:else}
        <h3 class="section-title">Timeline</h3>
        <div class="batch-list">
          {#each data.batches as batch}
            <div class="batch-card" class:active={batch.is_active}>
              <div class="batch-header">
                <div class="batch-quantity">
                  <Package size={16} strokeWidth={2} />
                  <strong>{batch.quantity_added}</strong>
                  {data.product.unit || "units"}
                </div>
                <div class="batch-date">{formatDate(batch.date_added)}</div>
              </div>

              {#if batch.cost_per_unit}
                <div class="batch-cost">
                  Cost: MWK {batch.cost_per_unit?.toLocaleString()}/{data.product.unit || "unit"}
                  {#if batch.total_cost}
                    · Total: MWK {batch.total_cost?.toLocaleString()}
                  {/if}
                </div>
              {/if}

              {#if batch.notes}
                <div class="batch-notes">{batch.notes}</div>
              {/if}

              <div class="batch-status">
                {#if batch.is_active}
                  <span class="status-badge active">
                    <AlertCircle size={12} />
                    Active — {data.product.current_stock} {data.product.unit || "units"} remaining
                  </span>
                {:else}
                  <span class="status-badge sold">
                    <TrendingUp size={12} />
                    Sold out after {batch.days_to_sell} days
                  </span>
                {/if}
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

  .summary-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 0.75rem;
    background: var(--background, #f9fafb);
    border-radius: 10px;
    padding: 1rem;
    margin-bottom: 1rem;
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

  .last-restock {
    font-size: 0.82rem;
    color: var(--text-light, #6b7280);
    margin: 0 0 1rem;
    text-align: center;
  }

  .section-title {
    margin: 1rem 0 0.75rem;
    font-size: 0.88rem;
    font-weight: 600;
    color: var(--text, #111827);
    text-transform: uppercase;
    letter-spacing: 0.3px;
  }

  .batch-list {
    display: flex;
    flex-direction: column;
    gap: 0.6rem;
  }

  .batch-card {
    padding: 0.85rem;
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    border-left: 4px solid var(--border, #e5e7eb);
    border-radius: 8px;
  }

  .batch-card.active {
    border-left-color: var(--primary, #0f6b3e);
    background: #f0fdf4;
  }

  .batch-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.4rem;
    gap: 0.5rem;
    flex-wrap: wrap;
  }

  .batch-quantity {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    font-size: 0.92rem;
    color: var(--text, #111827);
  }

  .batch-quantity strong {
    font-weight: 700;
  }

  .batch-date {
    font-size: 0.78rem;
    color: var(--text-light, #6b7280);
  }

  .batch-cost {
    font-size: 0.82rem;
    color: var(--text, #111827);
    margin-bottom: 0.25rem;
  }

  .batch-notes {
    font-size: 0.78rem;
    color: var(--text-light, #6b7280);
    font-style: italic;
    margin-bottom: 0.4rem;
  }

  .batch-status {
    margin-top: 0.5rem;
  }

  .status-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    font-size: 0.75rem;
    font-weight: 600;
    padding: 0.2rem 0.55rem;
    border-radius: 20px;
  }

  .status-badge.active {
    background: #dcfce7;
    color: #166534;
  }

  .status-badge.sold {
    background: var(--background, #f9fafb);
    color: var(--text-light, #6b7280);
  }

  @media (max-width: 480px) {
    .modal-overlay {
      padding: 0.75rem;
    }

    .modal {
      padding: 1.15rem;
      border-radius: 10px;
    }

    .summary-grid {
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