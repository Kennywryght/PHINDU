<script>
  import { createEventDispatcher } from "svelte";
  import { X, Loader2, AlertCircle, KeyRound } from "lucide-svelte";
  import API from "../api/api";

  const dispatch = createEventDispatcher();

  let current = "";
  let next = "";
  let confirm = "";
  let showCurrent = false;
  let showNext = false;
  let saving = false;
  let error = null;

  async function submit() {
    error = null;
    if (!current || !next) {
      error = "All fields are required";
      return;
    }
    if (next !== confirm) {
      error = "Passwords do not match";
      return;
    }
    if (next.length < 6) {
      error = "Password must be at least 6 characters";
      return;
    }
    saving = true;
    try {
      await API.post("/auth/change-password", {
        current_password: current,
        new_password: next,
      });
      dispatch("saved");
    } catch (err) {
      error = err.response?.data?.detail || "Failed to change password";
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
      <h3><KeyRound size={18} strokeWidth={2} /> Change Password</h3>
      <button class="close-btn" on:click={close} type="button" aria-label="Close">
        <X size={20} strokeWidth={2} />
      </button>
    </div>

    <div class="form-group">
      <label for="cp-current">Current password</label>
      <input id="cp-current" type={showCurrent ? "text" : "password"} bind:value={current} disabled={saving} autocomplete="current-password" />
    </div>
    <div class="form-group">
      <label for="cp-next">New password</label>
      <input id="cp-next" type={showNext ? "text" : "password"} bind:value={next} disabled={saving} autocomplete="new-password" />
      <p class="hint">At least 6 characters</p>
    </div>
    <div class="form-group">
      <label for="cp-confirm">Confirm new password</label>
      <input id="cp-confirm" type={showNext ? "text" : "password"} bind:value={confirm} disabled={saving} autocomplete="new-password" />
    </div>

    {#if error}
      <div class="error-box"><AlertCircle size={14} /> {error}</div>
    {/if}

    <div class="modal-actions">
      <button class="btn btn-secondary" on:click={close} type="button" disabled={saving}>Cancel</button>
      <button class="btn btn-primary" on:click={submit} type="button" disabled={saving}>
        {#if saving}
          <Loader2 size={14} class="spin" /> Saving…
        {:else}
          Change Password
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
    display: flex;
    align-items: center;
    gap: 0.4rem;
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
  label {
    display: block;
    margin-bottom: 0.3rem;
    font-weight: 500;
    font-size: 0.88rem;
    color: var(--text, #111827);
  }
  .hint {
    font-size: 0.75rem;
    color: var(--text-light, #6b7280);
    margin: 0.25rem 0 0;
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