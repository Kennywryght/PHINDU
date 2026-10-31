<script>
  export let icon = null;
  export let title = "";
  export let message = "";
  export let primaryLabel = "";
  export let primaryAction = null;
  export let secondaryLabel = "";
  export let secondaryAction = null;
</script>

<div class="empty-state">
  {#if icon}
    <div class="es-icon">
      <svelte:component this={icon} size={32} strokeWidth={1.75} />
    </div>
  {/if}

  {#if title}<h2 class="es-title">{title}</h2>{/if}
  {#if message}<p class="es-message">{message}</p>{/if}

  {#if (primaryLabel && primaryAction) || (secondaryLabel && secondaryAction)}
    <div class="es-actions">
      {#if primaryLabel && primaryAction}
        <button type="button" class="es-btn primary" on:click={primaryAction}>
          {primaryLabel}
        </button>
      {/if}
      {#if secondaryLabel && secondaryAction}
        <button type="button" class="es-btn secondary" on:click={secondaryAction}>
          {secondaryLabel}
        </button>
      {/if}
    </div>
  {/if}
</div>

<style>
  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    gap: 0.75rem;
    padding: 3rem 1.25rem;
    max-width: 420px;
    margin: 0 auto;
    box-sizing: border-box;
  }
  .es-icon {
    width: 68px;
    height: 68px;
    border-radius: 18px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(15, 107, 62, 0.1);
    color: var(--primary, #0f6b3e);
  }
  .es-title {
    margin: 0.25rem 0 0;
    font-size: 1.2rem;
    font-weight: 700;
    color: var(--text, #111827);
  }
  .es-message {
    margin: 0;
    font-size: 0.9rem;
    line-height: 1.5;
    color: var(--text-light, #6b7280);
  }
  .es-actions {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 0.6rem;
    margin-top: 0.5rem;
  }
  .es-btn {
    padding: 0.6rem 1.1rem;
    border-radius: 8px;
    font-size: 0.88rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s;
  }
  .es-btn.primary {
    background: var(--primary, #0f6b3e);
    color: #fff;
    border: 1px solid var(--primary, #0f6b3e);
  }
  .es-btn.primary:hover { filter: brightness(1.08); }
  .es-btn.secondary {
    background: var(--surface, #fff);
    color: var(--text, #111827);
    border: 1px solid var(--border, #e5e7eb);
  }
  .es-btn.secondary:hover {
    border-color: var(--primary, #0f6b3e);
    color: var(--primary, #0f6b3e);
  }
</style>
