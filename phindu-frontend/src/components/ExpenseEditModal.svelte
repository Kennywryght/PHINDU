<script>
  import { createEventDispatcher, onMount } from "svelte";
  import { X, Loader2, Trash2 } from "lucide-svelte";
  import API from "../api/api";

  export let expense = null; // { id, name, amount, category }
  const dispatch = createEventDispatcher();

  let name = expense?.name || "";
  let amount = expense?.amount || 0;
  let category = expense?.category || "";

  let saving = false;
  let deleting = false;
  let error = null;
  let categories = [];
  let loadingCategories = true;
  let useNewCategory = false;
  let newCategoryName = "";

  onMount(async () => {
    try {
      const res = await API.get("/expenses/categories");
      categories = res.data || [];
    } catch {
      categories = [];
    } finally {
      loadingCategories = false;
    }
  });

  function onCategoryChange(e) {
    const v = e.target.value;
    if (v === "__new__") {
      useNewCategory = true;
      category = "";
    } else {
      useNewCategory = false;
      category = v;
    }
  }

  async function save() {
    error = null;
    const trimmedName = name.trim();
    const trimmedCat = (
      useNewCategory ? newCategoryName.trim() : category.trim()
    );
    if (!trimmedName) {
      error = "Name is required";
      return;
    }
    if (!amount || amount <= 0) {
      error = "Amount must be greater than 0";
      return;
    }
    if (!trimmedCat) {
      error = "Category is required";
      return;
    }

    saving = true;
    try {
      await API.put(`/expenses/${expense.id}`, {
        name: trimmedName,
        amount: Number(amount),
        category: trimmedCat,
      });
      dispatch("saved");
    } catch (err) {
      error = err.response?.data?.detail || "Failed to update expense";
    } finally {
      saving = false;
    }
  }

  async function del() {
    if (!confirm(`Delete expense "${expense.name}"? This cannot be undone.`)) return;
    deleting = true;
    try {
      await API.delete(`/expenses/${expense.id}`);
      dispatch("deleted");
    } catch (err) {
      error = err.response?.data?.detail || "Failed to delete";
      deleting = false;
    }
  }

  function close() {
    dispatch("close");
  }

  function handleKeydown(e) {
    if (e.key === "Escape" && !saving && !deleting) close();
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
      <h3>Edit Expense</h3>
      <button class="close-btn" on:click={close} type="button" aria-label="Close">
        <X size={20} strokeWidth={2} />
      </button>
    </div>

    <div class="form-group">
      <label for="ee-name">Name</label>
      <input id="ee-name" type="text" bind:value={name} disabled={saving || deleting} />
    </div>

    <div class="form-row">
      <div class="form-group">
        <label for="ee-amount">Amount (MWK)</label>
        <input
          id="ee-amount"
          type="number"
          min="0.01"
          step="0.01"
          bind:value={amount}
          disabled={saving || deleting}
        />
      </div>
      <div class="form-group">
        <label for="ee-category">Category</label>
        {#if loadingCategories}
          <p class="hint">Loading categories...</p>
        {:else if !useNewCategory}
          <select id="ee-category" value={category} on:change={onCategoryChange} disabled={saving || deleting}>
            <option value="">— Choose —</option>
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
              placeholder="New category"
              disabled={saving || deleting}
            />
            <button
              type="button"
              class="btn-cancel-new"
              on:click={() => {
                useNewCategory = false;
                newCategoryName = "";
              }}
              disabled={saving || deleting}
            >
              Cancel
            </button>
          </div>
        {/if}
      </div>
    </div>

    {#if error}
      <div class="error-box">{error}</div>
    {/if}

    <div class="modal-actions">
      <button class="btn btn-danger" on:click={del} disabled={saving || deleting} type="button">
        {#if deleting}
          <Loader2 size={14} class="spin" /> Deleting…
        {:else}
          <Trash2 size={14} strokeWidth={2} /> Delete
        {/if}
      </button>
      <div class="right">
        <button class="btn btn-secondary" on:click={close} disabled={saving || deleting} type="button">
          Cancel
        </button>
        <button class="btn btn-primary" on:click={save} disabled={saving || deleting} type="button">
          {#if saving}
            <Loader2 size={14} class="spin" /> Saving…
          {:else}
            Save
          {/if}
        </button>
      </div>
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
    z-index: 1000;
    padding: 1rem;
  }
  .modal {
    background: var(--surface, #fff);
    border-radius: 12px;
    padding: 1.25rem;
    max-width: 440px;
    width: 100%;
    max-height: 90vh;
    overflow-y: auto;
  }
  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 1rem;
  }
  .modal-header h3 {
    margin: 0;
    font-size: 1.05rem;
    font-weight: 600;
    color: var(--text, #111827);
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
  .form-group {
    margin-bottom: 0.85rem;
  }
  .form-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.6rem;
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
    margin: 0.3rem 0 0;
  }
  input,
  select {
    width: 100%;
    padding: 0.6rem;
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 8px;
    background: var(--surface, #fff);
    color: var(--text, #111827);
    font-size: 0.9rem;
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
    gap: 0.4rem;
  }
  .new-cat-row input {
    flex: 1;
  }
  .btn-cancel-new {
    border: 1px solid var(--border, #e5e7eb);
    background: var(--surface, #fff);
    border-radius: 8px;
    padding: 0 0.6rem;
    font-size: 0.78rem;
    color: var(--text-light, #6b7280);
    cursor: pointer;
    white-space: nowrap;
  }
  .error-box {
    background: #fee2e2;
    color: #991b1b;
    padding: 0.55rem 0.75rem;
    border-radius: 8px;
    font-size: 0.85rem;
    margin-bottom: 0.75rem;
  }
  .modal-actions {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 0.5rem;
    margin-top: 1rem;
  }
  .modal-actions .right {
    display: flex;
    gap: 0.5rem;
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
  .btn:disabled {
    opacity: 0.55;
    cursor: not-allowed;
  }
  .btn-primary {
    background: var(--primary, #0f6b3e);
    color: white;
  }
  .btn-primary:hover:not(:disabled) {
    background: var(--primary-dark, #0a4f2e);
  }
  .btn-secondary {
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    color: var(--text, #111827);
  }
  .btn-secondary:hover:not(:disabled) {
    background: var(--background, #f9fafb);
  }
  .btn-danger {
    background: transparent;
    border: 1px solid #fecaca;
    color: #b91c1c;
  }
  .btn-danger:hover:not(:disabled) {
    background: #dc2626;
    color: white;
    border-color: #dc2626;
  }
  .spin {
    animation: spin 1s linear infinite;
  }
  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
  @media (max-width: 480px) {
    .form-row {
      grid-template-columns: 1fr;
    }
  }
</style>