<script>
  import { createEventDispatcher } from "svelte";
  import { X, Loader2, AlertCircle, Wallet } from "lucide-svelte";
  import API from "../api/api";

  export let customer = null; // { id, name, total_credit, phone }
  const dispatch = createEventDispatcher();

  let amount = customer?.total_credit || 0;
  let method = "cash";
  let note = "";
  let saving = false;
  let error = null;

  const METHODS = [
    { value: "cash", label: "Cash" },
    { value: "airtel_money", label: "Airtel Money" },
    { value: "tnm_mpamba", label: "TNM Mpamba" },
    { value: "bank", label: "Bank" },
    { value: "other", label: "Other" },
  ];

  async function submit() {
    error = null;
    if (!amount || amount <= 0) {
      error = "Amount must be greater than 0";
      return;
    }
    saving = true;
    try {
      await API.post(`/customers/${customer.id}/record-payment`, {
        amount: Number(amount),
        method,
        note: note.trim() || null,
      });
      dispatch("saved");
    } catch (err) {
      error = err.response?.data?.detail || "Failed to record payment";
    } finally {
      saving = false;
    }
  }

  function close() {
    dispatch("close");
  }

  function handleKeydown(e) {
    if (e.key === "Escape" && !saving) close();
  }

  function fmt(n) {
    return Number(n || 0).toLocaleString(undefined, {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  }

  function quickFill(pct) {
    amount = Math.round(Number(customer.total_credit || 0) * pct * 100) / 100;
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
        <h3><Wallet size={18} strokeWidth={2} /> Record Payment</h3>
        <p class="subtitle">{customer?.name}</p>
      </div>
      <button class="close-btn" on:click={close} type="button" aria-label="Close">
        <X size={20} strokeWidth={2} />
      </button>
    </div>

    <div class="current-info">
      <span>Currently owes:</span>
      <strong>MWK {fmt(customer?.total_credit)}</strong>
    </div>

    <div class="form-group">
      <label for="pm-amount">Amount (MWK)</label>
      <input
        id="pm-amount"
        type="number"
        min="0.01"
        step="0.01"
        bind:value={amount}
        disabled={saving}
      />
      <div class="quick-fills">
        <button type="button" on:click={() => quickFill(0.25)} disabled={saving}>25%</button>
        <button type="button" on:click={() => quickFill(0.5)} disabled={saving}>50%</button>
        <button type="button" on:click={() => quickFill(1)} disabled={saving}>Full</button>
      </div>
    </div>

    <div class="form-group">
      <label for="pm-method">Method</label>
      <select id="pm-method" bind:value={method} disabled={saving}>
        {#each METHODS as m}
          <option value={m.value}>{m.label}</option>
        {/each}
      </select>
    </div>

    <div class="form-group">
      <label for="pm-note">Note (optional)</label>
      <input id="pm-note" type="text" bind:value={note} placeholder="e.g. Received via Airtel" disabled={saving} />
    </div>

    {#if error}
      <div class="error-box">
        <AlertCircle size={14} strokeWidth={2} /> {error}
      </div>
    {/if}

    <div class="modal-actions">
      <button class="btn btn-secondary" on:click={close} type="button" disabled={saving}>
        Cancel
      </button>
      <button class="btn btn-primary" on:click={submit} type="button" disabled={saving}>
        {#if saving}
          <Loader2 size={14} class="spin" /> Saving…
        {:else}
          Record Payment
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
    margin-bottom: 1rem;
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
    flex-shrink: 0;
  }
  .close-btn:hover {
    background: var(--background, #f9fafb);
  }
  .current-info {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.6rem 0.85rem;
    background: var(--background, #f9fafb);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 8px;
    margin-bottom: 1rem;
    font-size: 0.85rem;
    color: var(--text-light, #6b7280);
  }
  .current-info strong {
    color: #b91c1c;
    font-size: 1.05rem;
    font-weight: 700;
  }
  .form-group {
    margin-bottom: 0.85rem;
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
  .quick-fills {
    display: flex;
    gap: 0.35rem;
    margin-top: 0.35rem;
  }
  .quick-fills button {
    flex: 1;
    padding: 0.35rem;
    border: 1px solid var(--border, #e5e7eb);
    background: var(--surface, #fff);
    border-radius: 6px;
    font-size: 0.78rem;
    font-weight: 600;
    color: var(--primary, #0f6b3e);
    cursor: pointer;
  }
  .quick-fills button:hover:not(:disabled) {
    background: #f0fdf4;
    border-color: var(--primary, #0f6b3e);
  }
  .quick-fills button:disabled {
    opacity: 0.55;
    cursor: not-allowed;
  }
  .error-box {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    background: #fee2e2;
    color: #991b1b;
    padding: 0.55rem 0.75rem;
    border-radius: 8px;
    font-size: 0.85rem;
    margin-bottom: 0.75rem;
  }
  .modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: 0.5rem;
    margin-top: 1rem;
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
  .spin {
    animation: spin 1s linear infinite;
  }
  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
</style>