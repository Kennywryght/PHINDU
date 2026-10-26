<script>
  import { createEventDispatcher, onMount } from "svelte";
  import { X, Loader2, AlertCircle, Receipt } from "lucide-svelte";
  import API from "../api/api";

  export let category = "";
  const dispatch = createEventDispatcher();

  let expenses = [];
  let loading = true;
  let error = null;

  onMount(async () => {
    try {
      const res = await API.get("/expenses/", {
        params: { category, limit: 200 },
      });
      expenses = res.data || [];
    } catch (err) {
      error = err.response?.data?.detail || "Failed to load expenses";
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

  $: total = expenses.reduce((s, e) => s + Number(e.amount || 0), 0);
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
        <h3>
          <Receipt size={18} strokeWidth={2} />
          {category || "Uncategorized"} Expenses
        </h3>
        <p class="subtitle">
          {#if loading}Loading…{:else}{expenses.length} record{expenses.length === 1 ? "" : "s"}{/if}
        </p>
      </div>
      <button class="close-btn" on:click={close} type="button" aria-label="Close">
        <X size={20} strokeWidth={2} />
      </button>
    </div>

    {#if loading}
      <div class="state-box">
        <Loader2 size={22} class="spin" />
        <span>Loading…</span>
      </div>
    {:else if error}
      <div class="state-box error">
        <AlertCircle size={18} />
        <span>{error}</span>
      </div>
    {:else if expenses.length === 0}
      <div class="state-box">
        <span>No individual expenses found for this category.</span>
      </div>
    {:else}
      <div class="expense-list">
        {#each expenses as exp}
          <div class="expense-row">
            <div class="expense-main">
              <strong>{exp.name}</strong>
              <span class="expense-date">{fmtDate(exp.created_at)}</span>
            </div>
            <div class="expense-amount">MWK {fmt(exp.amount)}</div>
          </div>
        {/each}
      </div>

      <div class="expense-total-row">
        <span>Total</span>
        <strong>MWK {fmt(total)}</strong>
      </div>
    {/if}

    <div class="modal-actions">
      <button class="btn btn-secondary" on:click={close} type="button">Close</button>
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
    max-width: 480px;
    width: 100%;
    max-height: 90vh;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
  }

  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 0.5rem;
    margin-bottom: 0.85rem;
  }
  .modal-header h3 {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    margin: 0;
    font-size: 1.05rem;
    font-weight: 600;
    color: var(--text, #111827);
  }
  .subtitle {
    margin: 0.2rem 0 0;
    font-size: 0.78rem;
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

  .state-box {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    padding: 2rem 1rem;
    color: var(--text-light, #6b7280);
    font-size: 0.88rem;
    text-align: center;
  }
  .state-box.error {
    color: var(--danger, #dc2626);
  }
  .spin {
    animation: spin 1s linear infinite;
  }
  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  .expense-list {
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
    max-height: 380px;
    overflow-y: auto;
    padding-right: 0.2rem;
  }
  .expense-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 0.5rem;
    padding: 0.55rem 0.7rem;
    background: var(--background, #f9fafb);
    border-radius: 8px;
    border: 1px solid var(--border, #e5e7eb);
  }
  .expense-main {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
    min-width: 0;
  }
  .expense-main strong {
    font-size: 0.88rem;
    color: var(--text, #111827);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .expense-date {
    font-size: 0.72rem;
    color: var(--text-light, #6b7280);
  }
  .expense-amount {
    font-weight: 700;
    color: var(--text, #111827);
    font-size: 0.9rem;
    white-space: nowrap;
  }

  .expense-total-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.7rem 0.75rem;
    margin-top: 0.7rem;
    background: #f0fdf4;
    border: 1px solid #86efac;
    border-radius: 8px;
    font-size: 0.9rem;
    color: #166534;
  }
  .expense-total-row strong {
    font-size: 1.05rem;
    font-weight: 700;
  }

  .modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: 0.5rem;
    margin-top: 0.85rem;
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
  .btn-secondary {
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    color: var(--text, #111827);
  }
  .btn-secondary:hover {
    background: var(--background, #f9fafb);
  }
</style>