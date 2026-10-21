<script>
  import { createEventDispatcher } from 'svelte';
  import { X } from 'lucide-svelte';

  export let product = null;
  const dispatch = createEventDispatcher();

  let form = {
    name: '',
    category: '',
    type: 'variant',
    unit: '',
    selling_price: 0,
    purchase_price: 0,
    stock_qty: 0,
    parent_id: '',
  };

  if (product) {
    form = { ...product };
  }

  function handleSubmit() {
    const payload = { ...form };
    if (!payload.parent_id || payload.parent_id.trim() === '') {
      delete payload.parent_id;
    }
    dispatch('save', payload);
  }

  function close() {
    dispatch('close');
  }

  function handleKeydown(e) {
    if (e.key === 'Escape') close();
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
      <h2>{product ? 'Edit Product' : 'Add Product'}</h2>
      <button class="close-btn" on:click={close} type="button" aria-label="Close">
        <X size={20} strokeWidth={2} />
      </button>
    </div>

    <form on:submit|preventDefault={handleSubmit}>
      <div class="form-group">
        <label for="p-name">Name</label>
        <input id="p-name" bind:value={form.name} required />
      </div>

      <div class="form-group">
        <label for="p-category">Category</label>
        <input id="p-category" bind:value={form.category} />
      </div>

      <div class="form-row">
        <div class="form-group">
          <label for="p-type">Type</label>
          <select id="p-type" bind:value={form.type}>
            <option value="variant">Variant</option>
            <option value="simple">Simple</option>
            <option value="bulk">Bulk (weight)</option>
          </select>
        </div>

        <div class="form-group">
          <label for="p-unit">Unit</label>
          <input id="p-unit" bind:value={form.unit} placeholder="e.g., piece, kg" />
        </div>
      </div>

      <div class="form-row">
        <div class="form-group">
          <label for="p-selling">Selling Price</label>
          <input id="p-selling" type="number" step="0.01" min="0" bind:value={form.selling_price} />
        </div>

        <div class="form-group">
          <label for="p-purchase">Purchase Price</label>
          <input id="p-purchase" type="number" step="0.01" min="0" bind:value={form.purchase_price} />
        </div>
      </div>

      <div class="form-group">
        <label for="p-stock">Stock Quantity</label>
        <input id="p-stock" type="number" min="0" bind:value={form.stock_qty} />
      </div>

      <div class="form-group">
        <label for="p-parent">Parent ID (optional)</label>
        <input id="p-parent" bind:value={form.parent_id} placeholder="Leave blank for standalone product" />
      </div>

      <div class="modal-actions">
        <button type="button" class="btn btn-secondary" on:click={close}>Cancel</button>
        <button type="submit" class="btn btn-primary">Save</button>
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
    z-index: 1000;
    padding: 1rem;
  }

  .modal {
    background: var(--surface, #fff);
    border-radius: 12px;
    padding: 1.5rem;
    max-width: 500px;
    width: 100%;
    max-height: 90vh;
    overflow-y: auto;
    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.15);
  }

  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1.25rem;
    gap: 0.5rem;
  }

  .modal-header h2 {
    margin: 0;
    font-size: 1.15rem;
    font-weight: 600;
    color: var(--text, #111827);
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
    transition: background 0.15s;
  }

  .close-btn:hover {
    background: var(--background, #f9fafb);
  }

  .form-group {
    margin-bottom: 0.85rem;
  }

  .form-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.75rem;
  }

  label {
    display: block;
    margin-bottom: 0.3rem;
    font-weight: 500;
    font-size: 0.88rem;
    color: var(--text, #111827);
  }

  input,
  select {
    width: 100%;
    padding: 0.6rem;
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 8px;
    font-size: 0.9rem;
    background: var(--surface, #fff);
    color: var(--text, #111827);
    box-sizing: border-box;
  }

  input:focus,
  select:focus {
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

  .btn {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.55rem 1rem;
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

  .btn-primary:hover {
    background: var(--primary-dark, #0a4f2e);
  }

  .btn-secondary {
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    color: var(--text, #111827);
  }

  .btn-secondary:hover {
    background: var(--background, #f9fafb);
  }

  /* ============ MOBILE ============ */
  @media (max-width: 480px) {
    .modal-overlay {
      padding: 0.75rem;
    }

    .modal {
      padding: 1.15rem;
      border-radius: 10px;
    }

    .form-row {
      grid-template-columns: 1fr;
      gap: 0;
    }

    .modal-actions {
      flex-direction: column-reverse;
    }

    .modal-actions .btn {
      width: 100%;
      justify-content: center;
      padding: 0.7rem;
    }
  }
</style>