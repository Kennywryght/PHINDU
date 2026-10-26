<script>
  import { createEventDispatcher, onMount } from "svelte";
  import { X, Loader2, AlertCircle, CheckCircle2, AlertTriangle, Wallet } from "lucide-svelte";
  import API from "../api/api";

  const dispatch = createEventDispatcher();

  let summary = null;
  let loading = true;
  let error = null;

  let closingBalance = 0;
  let closingBalanceTouched = false;
  let notes = "";
  let discrepancyReason = "";
  let saving = false;

  onMount(async () => {
    try {
      const res = await API.get("/sessions/current/summary");
      summary = res.data;
      closingBalance = Number(res.data?.cash_drawer?.expected_in_drawer || 0);
    } catch (err) {
      error = err.response?.data?.detail || "Failed to load session summary";
    } finally {
      loading = false;
    }
  });

  $: expected = Number(summary?.cash_drawer?.expected_in_drawer || 0);
  $: physical = Number(closingBalance || 0);
  $: diff = physical - expected;
  $: status =
    Math.abs(diff) < 1 ? "balanced" : diff < 0 ? "short" : "over";
  $: needsReason = Math.abs(diff) >= 1;

  async function submit() {
    error = null;
    if (loading) return;
    if (needsReason && !discrepancyReason.trim()) {
      error = "Please explain the cash discrepancy before closing";
      return;
    }
    saving = true;
    try {
      await API.post("/sessions/close", null, {
        params: {
          closing_balance: physical,
          notes: notes.trim() || undefined,
          discrepancy_reason: discrepancyReason.trim() || undefined,
        },
      });
      dispatch("closed");
    } catch (err) {
      error = err.response?.data?.detail || "Failed to close session";
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

  function useExpected() {
    closingBalance = expected;
    closingBalanceTouched = true;
  }
</script>

<svelte:window on:keydown={handleKeydown} />

<div class="modal-overlay" role="dialog" aria-modal="true" tabindex="-1" on:click|self={close}>
  <div class="modal">
    <div class="modal-header">
      <div class="mh-title">
        <Wallet size={20} strokeWidth={2} />
        <h3>Close Session</h3>
      </div>
      <button class="close-btn" on:click={close} type="button" aria-label="Close">
        <X size={20} strokeWidth={2} />
      </button>
    </div>

    {#if loading}
      <div class="loading-row">
        <Loader2 size={20} class="spin" />
        <span>Loading session summary…</span>
      </div>
    {:else if summary}
      <!-- Drawer computation -->
      <div class="drawer-card">
        <h4>Expected cash in drawer</h4>
        <div class="drawer-row">
          <span>Opening balance</span>
          <span>MWK {fmt(summary.cash_drawer.opening_balance)}</span>
        </div>
        <div class="drawer-row">
          <span>+ Cash sales</span>
          <span>MWK {fmt(summary.cash_drawer.plus_cash_sales)}</span>
        </div>
        <div class="drawer-row">
          <span>+ Cash payments received</span>
          <span>MWK {fmt(summary.cash_drawer.plus_cash_payments_received)}</span>
        </div>
        {#if summary.cash_drawer.plus_cash_added > 0}
          <div class="drawer-row">
            <span>+ Cash added</span>
            <span>MWK {fmt(summary.cash_drawer.plus_cash_added)}</span>
          </div>
        {/if}
        <div class="drawer-row negative">
          <span>− Cash expenses</span>
          <span>MWK {fmt(summary.cash_drawer.minus_expenses)}</span>
        </div>
        {#if summary.cash_drawer.minus_cash_removed > 0}
          <div class="drawer-row negative">
            <span>− Cash removed</span>
            <span>MWK {fmt(summary.cash_drawer.minus_cash_removed)}</span>
          </div>
        {/if}
        <div class="drawer-total">
          <span>Expected in drawer</span>
          <strong>MWK {fmt(summary.cash_drawer.expected_in_drawer)}</strong>
        </div>
      </div>

      <!-- Physical count -->
      <div class="form-group">
        <div class="count-label-row">
          <label for="cs-count">Physical cash count (MWK)</label>
          <button
            type="button"
            class="use-expected-btn"
            on:click={useExpected}
            disabled={saving}
          >
            Use expected
          </button>
        </div>
        <input
          id="cs-count"
          type="number"
          min="0"
          step="0.01"
          bind:value={closingBalance}
          on:input={() => (closingBalanceTouched = true)}
          disabled={saving}
        />
      </div>

      <!-- Discrepancy band -->
      {#if closingBalanceTouched}
        <div class="status-band status-{status}">
          {#if status === "balanced"}
            <CheckCircle2 size={18} strokeWidth={2} />
            <strong>Cash is balanced</strong>
          {:else if status === "short"}
            <AlertTriangle size={18} strokeWidth={2} />
            <strong>SHORT by MWK {fmt(Math.abs(diff))}</strong>
          {:else}
            <AlertCircle size={18} strokeWidth={2} />
            <strong>OVER by MWK {fmt(diff)}</strong>
          {/if}
        </div>
      {/if}

      {#if needsReason}
        <div class="form-group">
          <label for="cs-reason">What caused the discrepancy? (required)</label>
          <input
            id="cs-reason"
            type="text"
            bind:value={discrepancyReason}
            placeholder="e.g. Cashier miscounted, missing receipt"
            disabled={saving}
          />
        </div>
      {/if}

      <div class="form-group">
        <label for="cs-notes">Additional notes (optional)</label>
        <textarea id="cs-notes" rows="2" bind:value={notes} disabled={saving}></textarea>
      </div>

      {#if error}
        <div class="error-box">
          <AlertCircle size={14} /> {error}
        </div>
      {/if}

      <div class="modal-actions">
        <button class="btn btn-secondary" on:click={close} type="button" disabled={saving}>
          Cancel
        </button>
        <button
          class="btn btn-primary"
          on:click={submit}
          type="button"
          disabled={saving || (needsReason && !discrepancyReason.trim())}
        >
          {#if saving}
            <Loader2 size={14} class="spin" /> Closing…
          {:else}
            Close Day
          {/if}
        </button>
      </div>
    {:else}
      <div class="error-box">
        <AlertCircle size={14} /> {error || "Could not load summary"}
      </div>
      <div class="modal-actions">
        <button class="btn btn-secondary" on:click={close} type="button">Close</button>
      </div>
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
    z-index: 1000;
    padding: 1rem;
  }
  .modal {
    background: var(--surface, #fff);
    border-radius: 12px;
    padding: 1.25rem;
    max-width: 480px;
    width: 100%;
    max-height: 92vh;
    overflow-y: auto;
  }
  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 1rem;
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
    gap: 0.5rem;
    padding: 1rem 0;
    color: var(--text-light, #6b7280);
    font-size: 0.9rem;
  }
  .drawer-card {
    background: var(--background, #f9fafb);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 10px;
    padding: 0.75rem 0.9rem;
    margin-bottom: 1rem;
  }
  .drawer-card h4 {
    margin: 0 0 0.6rem;
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--text-light, #6b7280);
    font-weight: 700;
  }
  .drawer-row {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    padding: 0.2rem 0;
    font-size: 0.85rem;
    color: var(--text, #111827);
  }
  .drawer-row.negative span:last-child {
    color: #b91c1c;
  }
  .drawer-total {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    padding-top: 0.5rem;
    margin-top: 0.5rem;
    border-top: 2px solid var(--border, #e5e7eb);
    font-size: 0.9rem;
  }
  .drawer-total strong {
    font-size: 1.1rem;
    font-weight: 700;
    color: var(--primary, #0f6b3e);
  }
  .form-group {
    margin-bottom: 0.85rem;
  }
  .count-label-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.3rem;
  }
  label {
    font-weight: 500;
    font-size: 0.88rem;
    color: var(--text, #111827);
  }
  .use-expected-btn {
    border: 1px solid var(--primary, #0f6b3e);
    background: transparent;
    color: var(--primary, #0f6b3e);
    border-radius: 6px;
    padding: 0.2rem 0.6rem;
    font-size: 0.72rem;
    font-weight: 600;
    cursor: pointer;
  }
  .use-expected-btn:hover:not(:disabled) {
    background: var(--primary, #0f6b3e);
    color: white;
  }
  input,
  textarea {
    width: 100%;
    padding: 0.6rem;
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 8px;
    background: var(--surface, #fff);
    color: var(--text, #111827);
    font-size: 0.9rem;
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
  .status-band {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.65rem 0.85rem;
    border-radius: 8px;
    margin-bottom: 0.85rem;
    font-size: 0.88rem;
    border: 1px solid;
  }
  .status-balanced {
    background: rgba(22, 163, 74, 0.1);
    color: #166534;
    border-color: #86efac;
  }
  .status-short {
    background: rgba(220, 38, 38, 0.1);
    color: #991b1b;
    border-color: #fecaca;
  }
  .status-over {
    background: rgba(234, 88, 12, 0.1);
    color: #9a3412;
    border-color: #fed7aa;
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