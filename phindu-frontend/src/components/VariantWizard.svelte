<script>
  import { createEventDispatcher, onMount } from "svelte";
  import { X, Plus, Trash2, Package, Loader2, AlertCircle } from "lucide-svelte";
  import API from "../api/api";

  const dispatch = createEventDispatcher();

  let mode = "variants"; // "variants" | "standalone"

  let form = {
    name: "",
    category: "",
    unit: "piece",
    low_stock_threshold: 5,
    // standalone
    selling_price: 0,
    purchase_price: 0,
    stock_qty: 0,
  };

  let variants = [
    { name: "", selling_price: 0, purchase_price: 0, stock_qty: 0, low_stock_threshold: 5 },
  ];

  // Categories
  let categories = [];
  let loadingCategories = true;
  let useNewCategory = false;
  let newCategoryName = "";

  let submitting = false;
  let error = null;

  let nameInput;
  function focusOnMount(node) {
    setTimeout(() => node?.focus(), 50);
  }

  onMount(async () => {
    try {
      const res = await API.get("/products/categories");
      categories = res.data || [];
    } catch {
      categories = [];
    } finally {
      loadingCategories = false;
    }
  });

  function addVariant() {
    variants = [
      ...variants,
      { name: "", selling_price: 0, purchase_price: 0, stock_qty: 0, low_stock_threshold: 5 },
    ];
  }

  function removeVariant(i) {
    if (variants.length <= 1) return;
    variants = variants.filter((_, idx) => idx !== i);
  }

  function onCategorySelect(e) {
    const val = e.target.value;
    if (val === "__new__") {
      useNewCategory = true;
      form.category = "";
    } else {
      useNewCategory = false;
      form.category = val;
    }
  }

  async function handleSubmit() {
    error = null;

    const trimmedName = form.name.trim();
    if (!trimmedName) {
      error = "Product name is required";
      return;
    }

    let finalCategory = form.category;
    if (useNewCategory) {
      const nc = newCategoryName.trim();
      if (!nc) {
        error = "Please enter a category name, or choose an existing category";
        return;
      }
      finalCategory = nc;
    }

    if (mode === "standalone") {
      if (!form.selling_price || form.selling_price <= 0) {
        error = "Selling price must be greater than 0";
        return;
      }
    } else {
      if (variants.length === 0) {
        error = "Add at least one variant";
        return;
      }
      const names = new Set();
      for (let i = 0; i < variants.length; i++) {
        const v = variants[i];
        const n = v.name.trim();
        if (!n) {
          error = `Variant ${i + 1}: name is required`;
          return;
        }
        if (names.has(n.toLowerCase())) {
          error = `Duplicate variant name: ${n}`;
          return;
        }
        names.add(n.toLowerCase());
        if (!v.selling_price || v.selling_price <= 0) {
          error = `Variant ${i + 1}: selling price must be > 0`;
          return;
        }
      }
    }

    const payload = {
      name: trimmedName,
      category: finalCategory || null,
      type: "variant",
      unit: form.unit || "piece",
      low_stock_threshold: form.low_stock_threshold || 5,
      has_variants: mode === "variants",
    };

    if (mode === "standalone") {
      payload.selling_price = Number(form.selling_price) || 0;
      payload.purchase_price = Number(form.purchase_price) || 0;
      payload.stock_qty = Number(form.stock_qty) || 0;
      payload.variants = [];
    } else {
      payload.variants = variants.map((v) => ({
        name: v.name.trim(),
        selling_price: Number(v.selling_price) || 0,
        purchase_price: Number(v.purchase_price) || 0,
        stock_qty: Number(v.stock_qty) || 0,
        low_stock_threshold: Number(v.low_stock_threshold) || 5,
      }));
    }

    submitting = true;
    try {
      const res = await API.post("/products/bulk", payload);
      dispatch("saved", res.data);
    } catch (err) {
      error = err.response?.data?.detail || "Failed to create product";
    } finally {
      submitting = false;
    }
  }

  function close() {
    dispatch("close");
  }

  function handleKeydown(e) {
    if (e.key === "Escape" && !submitting) close();
  }
</script>

<svelte:window on:keydown={handleKeydown} />

<div class="modal-overlay" role="dialog" aria-modal="true" tabindex="-1">
  <div class="modal">
    <div class="modal-header">
      <div>
        <h2>Add Product with Variants</h2>
        <p class="subtitle">Name the parent, add variants inline, save in one go</p>
      </div>
      <button class="close-btn" on:click={close} type="button" aria-label="Close">
        <X size={20} strokeWidth={2} />
      </button>
    </div>

    <div class="mode-toggle">
      <button
        type="button"
        class:active={mode === "variants"}
        on:click={() => (mode = "variants")}
      >
        <Package size={14} strokeWidth={2} /> Has variants
      </button>
      <button
        type="button"
        class:active={mode === "standalone"}
        on:click={() => (mode = "standalone")}
      >
        Standalone product
      </button>
    </div>

    <div class="form-group">
      <label for="vw-name">Product Name *</label>
      <input
        id="vw-name"
        bind:value={form.name}
        use:focusOnMount
        bind:this={nameInput}
        placeholder="e.g., Sugar, Rice, Cooking Oil"
      />
    </div>

    <div class="form-row">
      <div class="form-group">
        <label for="vw-category">Category</label>
        {#if loadingCategories}
          <p class="hint">Loading categories...</p>
        {:else if !useNewCategory}
          <select id="vw-category" value={form.category || ""} on:change={onCategorySelect}>
            <option value="">— No category —</option>
            {#each categories as cat}
              <option value={cat.name}>{cat.name} ({cat.count})</option>
            {/each}
            <option value="__new__">＋ New category…</option>
          </select>
        {:else}
          <div class="new-cat-row">
            <input
              type="text"
              bind:value={newCategoryName}
              placeholder="New category name"
              autofocus
            />
            <button
              type="button"
              class="btn-cancel-new"
              on:click={() => {
                useNewCategory = false;
                newCategoryName = "";
              }}
            >
              Cancel
            </button>
          </div>
        {/if}
      </div>

      <div class="form-group">
        <label for="vw-unit">Unit</label>
        <input id="vw-unit" bind:value={form.unit} placeholder="piece / kg / g" />
      </div>
    </div>

    <div class="form-group">
      <label for="vw-threshold">Low-stock alert at</label>
      <input
        id="vw-threshold"
        type="number"
        min="0"
        bind:value={form.low_stock_threshold}
      />
    </div>

    {#if mode === "standalone"}
      <div class="form-row">
        <div class="form-group">
          <label for="vw-selling">Selling Price *</label>
          <input
            id="vw-selling"
            type="number"
            step="0.01"
            min="0"
            bind:value={form.selling_price}
          />
        </div>
        <div class="form-group">
          <label for="vw-purchase">Purchase Price</label>
          <input
            id="vw-purchase"
            type="number"
            step="0.01"
            min="0"
            bind:value={form.purchase_price}
          />
        </div>
      </div>
      <div class="form-group">
        <label for="vw-stock">Stock Quantity</label>
        <input id="vw-stock" type="number" min="0" bind:value={form.stock_qty} />
      </div>
    {:else}
      <div class="variants-section">
        <div class="variants-header">
          <h3>Variants</h3>
          <button type="button" class="add-variant-btn" on:click={addVariant}>
            <Plus size={14} strokeWidth={2} /> Add variant
          </button>
        </div>

        <div class="variant-head">
          <span>Name</span>
          <span>Sell</span>
          <span>Cost</span>
          <span>Stock</span>
          <span></span>
        </div>

        {#each variants as v, i}
          <div class="variant-row">
            <input type="text" bind:value={v.name} placeholder="e.g., 1kg" />
            <input type="number" step="0.01" min="0" bind:value={v.selling_price} />
            <input type="number" step="0.01" min="0" bind:value={v.purchase_price} />
            <input type="number" min="0" bind:value={v.stock_qty} />
            <button
              type="button"
              class="remove-btn"
              on:click={() => removeVariant(i)}
              disabled={variants.length <= 1}
              aria-label="Remove variant"
            >
              <Trash2 size={14} strokeWidth={2} />
            </button>
          </div>
        {/each}
      </div>
    {/if}

    {#if error}
      <div class="error-box">
        <AlertCircle size={14} />
        {error}
      </div>
    {/if}

    <div class="modal-actions">
      <button type="button" class="btn btn-secondary" on:click={close} disabled={submitting}>
        Cancel
      </button>
      <button type="button" class="btn btn-primary" on:click={handleSubmit} disabled={submitting}>
        {#if submitting}
          <Loader2 size={14} class="spin" /> Creating…
        {:else}
          Create {mode === "variants" ? "Product + Variants" : "Product"}
        {/if}
      </button>
    </div>
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
    z-index: 1400;
    padding: 1rem;
  }

  .modal {
    background: var(--surface, #fff);
    border-radius: 12px;
    padding: 1.5rem;
    max-width: 720px;
    width: 100%;
    max-height: 92vh;
    overflow-y: auto;
    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.2);
  }

  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 1rem;
    gap: 0.5rem;
  }
  .modal-header h2 {
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

  .mode-toggle {
    display: inline-flex;
    gap: 0.25rem;
    background: var(--background, #f9fafb);
    padding: 0.2rem;
    border-radius: 8px;
    margin-bottom: 1rem;
    border: 1px solid var(--border, #e5e7eb);
  }
  .mode-toggle button {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.4rem 0.85rem;
    border: none;
    background: transparent;
    border-radius: 6px;
    font-size: 0.82rem;
    font-weight: 500;
    color: var(--text-light, #6b7280);
    cursor: pointer;
    transition: all 0.15s;
  }
  .mode-toggle button.active {
    background: var(--surface, #fff);
    color: var(--primary, #0f6b3e);
    font-weight: 600;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
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
  .hint {
    font-size: 0.8rem;
    color: var(--text-light, #6b7280);
    margin: 0.4rem 0 0;
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

  .new-cat-row {
    display: flex;
    gap: 0.5rem;
  }
  .new-cat-row input {
    flex: 1;
  }
  .btn-cancel-new {
    border: 1px solid var(--border, #e5e7eb);
    background: var(--surface, #fff);
    border-radius: 8px;
    padding: 0 0.75rem;
    font-size: 0.82rem;
    color: var(--text-light, #6b7280);
    cursor: pointer;
    white-space: nowrap;
  }
  .btn-cancel-new:hover {
    color: var(--text, #111827);
    border-color: var(--text-light, #6b7280);
  }

  .variants-section {
    margin-top: 0.5rem;
    padding: 0.85rem;
    background: var(--background, #f9fafb);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 10px;
  }
  .variants-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 0.6rem;
  }
  .variants-header h3 {
    margin: 0;
    font-size: 0.9rem;
    font-weight: 700;
    color: var(--text, #111827);
  }
  .add-variant-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    padding: 0.35rem 0.7rem;
    border-radius: 6px;
    font-size: 0.78rem;
    font-weight: 600;
    color: var(--primary, #0f6b3e);
    cursor: pointer;
  }
  .add-variant-btn:hover {
    background: #f0fdf4;
    border-color: var(--primary, #0f6b3e);
  }

  .variant-head {
    display: grid;
    grid-template-columns: 2fr 1fr 1fr 1fr 32px;
    gap: 0.4rem;
    padding: 0 0 0.35rem;
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--text-light, #6b7280);
    margin-bottom: 0.3rem;
  }
  .variant-row {
    display: grid;
    grid-template-columns: 2fr 1fr 1fr 1fr 32px;
    gap: 0.4rem;
    margin-bottom: 0.35rem;
    align-items: center;
  }
  .variant-row input {
    padding: 0.5rem 0.55rem;
    font-size: 0.85rem;
  }
  .remove-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    border: 1px solid var(--border, #e5e7eb);
    background: var(--surface, #fff);
    border-radius: 6px;
    color: #b91c1c;
    cursor: pointer;
  }
  .remove-btn:hover:not(:disabled) {
    background: #fef2f2;
    border-color: #dc2626;
  }
  .remove-btn:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  .error-box {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    background: #fee2e2;
    color: #991b1b;
    padding: 0.6rem 0.85rem;
    border-radius: 8px;
    font-size: 0.85rem;
    margin-top: 0.6rem;
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

  .spin {
    animation: spin 1s linear infinite;
  }
  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  @media (max-width: 640px) {
    .modal {
      padding: 1rem;
      max-height: 95vh;
    }
    .form-row {
      grid-template-columns: 1fr;
      gap: 0;
    }
    .variant-head,
    .variant-row {
      grid-template-columns: 1fr 1fr 32px;
    }
    .variant-head span:nth-child(3),
    .variant-head span:nth-child(4),
    .variant-row input:nth-child(3),
    .variant-row input:nth-child(4) {
      display: none;
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