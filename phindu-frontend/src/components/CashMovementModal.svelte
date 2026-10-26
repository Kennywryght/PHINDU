<script>
  import { createEventDispatcher } from "svelte";
  import { X, Loader2, AlertCircle, ArrowDownCircle, ArrowUpCircle } from "lucide-svelte";
  import API from "../api/api";

  export let direction = "out"; // "out" (cash-out) | "in" (cash-in)
  const dispatch = createEventDispatcher();

  let amount = 0;
  let reason = "";
  let saving = false;
  let error = null;

  async function submit() {
    error = null;
    if (!amount || amount <= 0) {
      error = "Amount must be greater than 0";
      return;
    }
    saving = true;
    try {
      const url = direction === "out" ? "/sessions/current/cash-out" : "/sessions/current/cash-in";
      await API.post(url, { amount: Number(amount), reason: reason.trim() || null });
      dispatch("saved");
    } catch (err) {
      error = err.response?.data?.detail || "Failed to record cash movement";
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
</script>

<svelte:window on:keydown={handleKeydown} />

<div class="modal-overlay" role="dialog" aria-modal="true" tabindex="-1" on:click|self={close}>
  <div class="modal">
    <div class="modal-header">
      <div class="mh-title">
        {#if direction === "out"}
          <ArrowDownCircle size={20} strokeWidth={2} />
          <h3>Cash Out</h3>
        {:else}
          <ArrowUpCircle size={20} strokeWidth={2} />
          <h3>Cash In</h3>
        {/if}
      </div>
      <button class="close-btn" on:click={close} type="button" aria-label="Close">
        <X size={20} strokeWidth={2} />
      </button>
    </div>

    <p class="hint">
      {#if direction === "out"}
        Record cash leaving the drawer — e.g. bank deposit, owner withdrawal.
      {:else}
        Record cash entering the drawer outside of a sale — e.g. emergency float.
      {/if}
    </p>

    <div class="form-group">
      <label for="cm-amount">Amount (MWK)</label>
      <input id="cm-amount" type="number" min="0.01" step="0.01" bind:value={amount} disabled={saving} />
    </div>
    <div class="form-group">
      <label for="cm-reason">Reason</label>
      <input id="cm-reason" type="text" bind:value={reason} placeholder="e.g. Deposit to bank" disabled={saving} />
    </div>

    {#if error}
      <div class="error-box">
        <AlertCircle size={14} /> {error}
      </div>
    {/if}

    <div class="modal-actions">
      <button class="btn btn-secondary" on:click={close} type="button" disabled={saving}>Cancel</button>
      <button class="btn btn-primary" on:click={submit} type="button" disabled={saving}>
        {#if saving}
          <Loader2 size={14} class="spin" /> Saving…
        {:else}
          Confirm {direction === "out" ? "Cash Out" : "Cash In"}
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
    max-width: 420px;
    width: 100%;
  }
  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.5rem;
  }
  .mh-title {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    color: var(--text, #111827);
  }
  .mh-title h3 {
    margin: 0;
    font-size: 1.05rem;
    font-weight: 600;
  }
  .hint {
    font-size: 0.82rem;
    color: var(--text-light, #6b7280);
    margin: 0 0 1rem;
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
  label {
    display: block;
    margin-bottom: 0.3rem;
    font-weight: 500;
    font-size: 0.88rem;
    color: var(--text, #111827);
  }
  input {
    width: 100%;
    padding: 0.6rem;
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 8px;
    background: var(--surface, #fff);
    color: var(--text, #111827);
    font-size: 0.9rem;
    box-sizing: border-box;
  }
  input:focus {
    outline: none;
    border-color: var(--primary, #0f6b3e);
    box-shadow: 0 0 0 3px rgba(15, 107, 62, 0.1);
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
  .spin {
    animation: spin 1s linear infinite;
  }
  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
</style>