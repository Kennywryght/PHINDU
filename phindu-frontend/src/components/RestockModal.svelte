<script>
  import { createEventDispatcher } from "svelte";
  import { X, PackagePlus } from "lucide-svelte";
  import API from "../api/api";

  export let product;
  const dispatch = createEventDispatcher();

  let quantity = 0;
  let costPerUnit = product.purchase_price || 0;
  let notes = "";
  let submitting = false;
  let error = null;

  async function handleSubmit() {
    if (quantity <= 0) {
      error = "Quantity must be greater than 0";
      return;
    }
    submitting = true;
    error = null;
    try {
      const res = await API.post(`/products/${product.id}/restock`, {
        quantity: parseFloat(quantity),
        cost_per_unit: costPerUnit > 0 ? parseFloat(costPerUnit) : null,
        notes: notes.trim() || null,
      });
      dispatch("saved", res.data);
    } catch (err) {
      error = err.response?.data?.detail || "Failed to restock";
      submitting = false;
    }
  }

  function close() {
    dispatch("close");
  }

  function handleKeydown(e) {
    if (e.key === "Escape") close();
  }
</script>

<svelte:window on:keydown={handleKeydown} />

<div class="modal-overlay" role="dialog" aria-modal="true" tabindex="-1">
  <div class="modal">
    <div class="modal-header">
      <div>
        <h2>
          <PackagePlus size={18} strokeWidth={2} />
          Restock Product
        </h2>
        <p class="product-name">{product.name}</p>
      </div>
      <button class="close-btn" on:click={close} type="button" aria-label="Close">
        <X size={20} strokeWidth={2} />
      </button>
    </div>

    <div class="current-info">
      Current stock: <strong>{product.stock_qty} {product.unit || "units"}</strong>
    </div>

    <form on:submit|preventDefault={handleSubmit}>
      <div class="form-group">
        <label for="r-qty">Quantity to Add *</label>
        <div class="input-with-unit">
          <input
            id="r-qty"
            type="number"
            min="0.01"
            step="0.01"
            bind:value={quantity}
            required
            autofocus
          />
          <span class="unit-label">{product.unit || "units"}</span>
        </div>
      </div>

      <div class="form-group">
        <label for="r-cost">Cost per {product.unit || "unit"} (MWK)</label>
        <input
          id="r-cost"
          type="number"
          min="0"
          step="0.01"
          bind:value={costPerUnit}
          placeholder="Optional"
        />
        <p class="hint">Tracks cost basis for margin calculations</p>
      </div>

      <div class="form-group">
        <label for="r-notes">Notes</label>
        <textarea
          id="r-notes"
          bind:value={notes}
          rows="2"
          placeholder="e.g., Bought from ABC supplier"
        ></textarea>
      </div>

      {#if error}
        <div class="error-box">{error}</div>
      {/if}

      <div class="modal-actions">
        <button type="button" class="btn btn-secondary" on:click={close} disabled={submitting}>
          Cancel
        </button>
        <button type="submit" class="btn btn-primary" disabled={submitting || quantity <= 0}>
          {submitting ? "Adding..." : `Add ${quantity || 0} ${product.unit || "units"}`}
        </button>
      </div>
    </form>
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
    max-width: 450px;
    width: 100%;
    max-height: 90vh;
    overflow-y: auto;
    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.15);
  }

  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 1rem;
    gap: 0.5rem;
  }

  .modal-header h2 {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    margin: 0;
    font-size: 1.1rem;
    font-weight: 600;
    color: var(--text, #111827);
  }

  .product-name {
    margin: 0.25rem 0 0;
    font-size: 0.85rem;
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
  }

  .close-btn:hover {
    background: var(--background, #f9fafb);
  }

  .current-info {
    background: var(--background, #f9fafb);
    padding: 0.6rem 0.85rem;
    border-radius: 8px;
    margin-bottom: 1rem;
    font-size: 0.85rem;
    color: var(--text, #111827);
  }

  .form-group {
    margin-bottom: 0.9rem;
  }

  label {
    display: block;
    margin-bottom: 0.3rem;
    font-weight: 500;
    font-size: 0.88rem;
    color: var(--text, #111827);
  }

  .input-with-unit {
    position: relative;
    display: flex;
    align-items: center;
  }

  .input-with-unit input {
    padding-right: 3.5rem;
  }

  .unit-label {
    position: absolute;
    right: 0.75rem;
    font-size: 0.8rem;
    color: var(--text-light, #6b7280);
    pointer-events: none;
  }

  input,
  textarea {
    width: 100%;
    padding: 0.6rem;
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 8px;
    font-size: 0.9rem;
    background: var(--surface, #fff);
    color: var(--text, #111827);
    box-sizing: border-box;
    font-family: inherit;
  }

  textarea {
    resize: vertical;
  }

  input:focus,
  textarea:focus {
    outline: none;
    border-color: var(--primary, #0f6b3e);
    box-shadow: 0 0 0 3px rgba(15, 107, 62, 0.1);
  }

  .hint {
    margin: 0.35rem 0 0;
    font-size: 0.75rem;
    color: var(--text-light, #6b7280);
  }

  .error-box {
    background: #fee2e2;
    color: #991b1b;
    padding: 0.6rem 0.85rem;
    border-radius: 8px;
    font-size: 0.85rem;
    margin-bottom: 0.75rem;
  }

  .modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: 0.6rem;
    margin-top: 1rem;
  }

  .btn {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.6rem 1rem;
    border-radius: 8px;
    border: none;
    cursor: pointer;
    font-weight: 500;
    font-size: 0.9rem;
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

  .btn-secondary:hover:not(:disabled) {
    background: var(--background, #f9fafb);
  }

  @media (max-width: 480px) {
    .modal-overlay {
      padding: 0.75rem;
    }
    .modal {
      padding: 1.15rem;
    }
    .modal-actions {
      flex-direction: column-reverse;
    }
    .modal-actions .btn {
      width: 100%;
      justify-content: center;
    }
  }
</style>