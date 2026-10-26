<script>
  import { createEventDispatcher, onMount } from "svelte";
  import { X, Loader2, Wallet } from "lucide-svelte";
  import API from "../api/api";

  export let customer = null; // { id, name, total_credit }
  const dispatch = createEventDispatcher();

  let payments = [];
  let loading = true;
  let error = null;

  onMount(async () => {
    try {
      const res = await API.get(`/customers/${customer.id}/payments`);
      payments = res.data || [];
    } catch (err) {
      error = err.response?.data?.detail || "Failed to load payments";
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
</script>

<svelte:window on:keydown={handleKeydown} />

<div class="modal-overlay" role="dialog" aria-modal="true" tabindex="-1" on:click|self={close}>
  <div class="modal">
    <div class="modal-header">
      <div>
        <h3><Wallet size={18} strokeWidth={2} /> Payment History</h3>
        <p class="subtitle">{customer?.name}</p>
      </div>
      <button class="close-btn" on:click={close} type="button" aria-label="Close">
        <X size={20} strokeWidth={2} />
      </button>
    </div>

    {#if loading}
      <div class="loading-row"><Loader2 size={18} class="spin" /> Loading…</div>
    {:else if error}
      <div class="error-box">{error}</div>
    {:else if payments.length === 0}
      <p class="empty-text">No payments recorded yet.</p>
    {:else}
      <div class="pay-list">
        {#each payments as p}
          <div class="pay-row">
            <div class="pay-main">
              <strong>MWK {fmt(p.amount)}</strong>
              <span class="pay-method">{p.method}</span>
            </div>
            <div class="pay-meta">
              <span>{fmtDate(p.created_at)}</span>
              {#if p.note}
                <span class="pay-note">{p.note}</span>
              {/if}
            </div>
          </div>
        {/each}
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
    max-width: 440px;
    width: 100%;
    max-height: 90vh;
    overflow-y: auto;
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
    margin: 0.15rem 0 0;
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
  }
  .close-btn:hover {
    background: var(--background, #f9fafb);
  }
  .loading-row {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    padding: 2rem 1rem;
    color: var(--text-light, #6b7280);
    font-size: 0.88rem;
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
    padding: 0.6rem 0.8rem;
    border-radius: 8px;
    font-size: 0.85rem;
  }
  .empty-text {
    text-align: center;
    padding: 1.5rem 1rem;
    color: var(--text-light, #6b7280);
    font-size: 0.88rem;
  }
  .pay-list {
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
    max-height: 380px;
    overflow-y: auto;
  }
  .pay-row {
    padding: 0.6rem 0.75rem;
    background: var(--background, #f9fafb);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 8px;
  }
  .pay-main {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 0.5rem;
    margin-bottom: 0.15rem;
  }
  .pay-main strong {
    font-size: 0.92rem;
    color: var(--text, #111827);
  }
  .pay-method {
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    font-weight: 700;
    color: var(--primary, #0f6b3e);
    background: rgba(15, 107, 62, 0.1);
    padding: 0.1rem 0.4rem;
    border-radius: 4px;
  }
  .pay-meta {
    display: flex;
    justify-content: space-between;
    gap: 0.5rem;
    font-size: 0.72rem;
    color: var(--text-light, #6b7280);
    flex-wrap: wrap;
  }
  .pay-note {
    font-style: italic;
  }
  .modal-actions {
    display: flex;
    justify-content: flex-end;
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
</style>