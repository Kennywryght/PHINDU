<script>
  import { createEventDispatcher } from 'svelte';

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
    parent_id: ''
  };

  if (product) {
    form = { ...product };
  }

function handleSubmit() {
  const payload = { ...form };
  // Remove parent_id if it's empty or only whitespace
  if (!payload.parent_id || payload.parent_id.trim() === '') {
    delete payload.parent_id;
  }
  dispatch('save', payload);
}
</script>

<div class="modal-overlay" on:click|self={() => dispatch('close')}>
  <div class="modal">
    <h2>{product ? 'Edit Product' : 'Add Product'}</h2>
    <form on:submit|preventDefault={handleSubmit}>
      <div class="form-group">
        <label>Name</label>
        <input bind:value={form.name} required />
      </div>
      <div class="form-group">
        <label>Category</label>
        <input bind:value={form.category} />
      </div>
      <div class="form-group">
        <label>Type</label>
        <select bind:value={form.type}>
          <option value="variant">Variant</option>
          <option value="simple">Simple</option>
        </select>
      </div>
      <div class="form-group">
        <label>Unit</label>
        <input bind:value={form.unit} placeholder="e.g., capsules, kg" />
      </div>
      <div class="form-row">
        <div class="form-group">
          <label>Selling Price</label>
          <input type="number" step="0.01" bind:value={form.selling_price} />
        </div>
        <div class="form-group">
          <label>Purchase Price</label>
          <input type="number" step="0.01" bind:value={form.purchase_price} />
        </div>
      </div>
      <div class="form-group">
        <label>Stock Quantity</label>
        <input type="number" bind:value={form.stock_qty} />
      </div>
      <div class="form-group">
        <label>Parent ID (optional)</label>
        <input bind:value={form.parent_id} />
      </div>
      <div class="modal-actions">
        <button type="button" class="btn btn-secondary" on:click={() => dispatch('close')}>
          Cancel
        </button>
        <button type="submit" class="btn btn-primary">Save</button>
      </div>
    </form>
  </div>
</div>

<style>
  .modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
    padding: 1rem;
  }

  .modal {
    background: white;
    border-radius: var(--radius);
    padding: 1.5rem;
    max-width: 500px;
    width: 100%;
    max-height: 90vh;
    overflow-y: auto;
  }

  h2 {
    margin-bottom: 1.5rem;
  }

  .form-group {
    margin-bottom: 1rem;
  }

  label {
    display: block;
    margin-bottom: 0.25rem;
    font-weight: 500;
  }

  input,
  select {
    width: 100%;
  }

  .form-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
  }

  .modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: 0.75rem;
    margin-top: 1.5rem;
  }

  .btn {
    padding: 0.5rem 1rem;
    border-radius: var(--radius);
    font-weight: 500;
    cursor: pointer;
    border: none;
  }

  .btn-primary {
    background: var(--primary);
    color: white;
  }

  .btn-secondary {
    background: white;
    border: 1px solid var(--border);
    color: var(--text);
  }
</style>