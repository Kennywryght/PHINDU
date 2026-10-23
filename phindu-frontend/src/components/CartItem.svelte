<script>
  import { createEventDispatcher } from "svelte";
  import { Minus, Plus, Trash2 } from "lucide-svelte";

  export let item;
  const dispatch = createEventDispatcher();

  function increment() {
    dispatch("update", { qty: item.qty + 1 });
  }

  function decrement() {
    if (item.qty > 1) {
      dispatch("update", { qty: item.qty - 1 });
    } else {
      dispatch("remove");
    }
  }
</script>

<div class="cart-item">
  <div class="item-info">
    <span class="name">{item.name}</span>
    <span class="price">MWK {item.selling_price?.toLocaleString()}</span>
  </div>
  <div class="item-controls">
    <button on:click={decrement} type="button" aria-label="Decrease quantity">
      <Minus size={14} strokeWidth={2.5} />
    </button>
    <span class="qty">{item.qty}</span>
    <button on:click={increment} type="button" aria-label="Increase quantity">
      <Plus size={14} strokeWidth={2.5} />
    </button>
    <button
      class="remove"
      on:click={() => dispatch("remove")}
      type="button"
      aria-label="Remove item"
    >
      <Trash2 size={14} strokeWidth={2} />
    </button>
  </div>
</div>

<style>
  .cart-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.6rem 0;
    border-bottom: 1px solid var(--border, #e5e7eb);
    gap: 0.5rem;
  }

  .item-info {
    display: flex;
    flex-direction: column;
    min-width: 0;
    flex: 1;
  }

  .name {
    font-weight: 500;
    font-size: 0.88rem;
    color: var(--text, #111827);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .price {
    font-size: 0.78rem;
    color: var(--text-light, #6b7280);
    margin-top: 0.15rem;
  }

  .item-controls {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    flex-shrink: 0;
  }

  .item-controls button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 30px;
    height: 30px;
    border-radius: 8px;
    border: 1px solid var(--border, #e5e7eb);
    background: var(--surface, #fff);
    cursor: pointer;
    color: var(--text, #111827);
    padding: 0;
    transition: all 0.15s;
  }

  .item-controls button:hover {
    border-color: var(--primary, #0f6b3e);
    color: var(--primary, #0f6b3e);
  }

  .qty {
    min-width: 24px;
    text-align: center;
    font-weight: 600;
    font-size: 0.88rem;
    color: var(--text, #111827);
  }

  .remove {
    color: var(--danger, #dc2626) !important;
    border-color: #fee2e2 !important;
  }

  .remove:hover {
    background: #fef2f2 !important;
    border-color: var(--danger, #dc2626) !important;
    color: var(--danger, #dc2626) !important;
  }

  @media (max-width: 480px) {
    .cart-item {
      padding: 0.5rem 0;
    }

    .item-controls button {
      width: 28px;
      height: 28px;
    }

    .name {
      font-size: 0.82rem;
    }

    .price {
      font-size: 0.72rem;
    }

    .qty {
      font-size: 0.82rem;
    }
  }
</style>