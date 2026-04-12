<script>
  import { createEventDispatcher } from 'svelte';

  export let item;
  const dispatch = createEventDispatcher();

  function increment() {
    dispatch('update', { qty: item.qty + 1 });
  }

  function decrement() {
    if (item.qty > 1) {
      dispatch('update', { qty: item.qty - 1 });
    } else {
      dispatch('remove');
    }
  }
</script>

<div class="cart-item">
  <div class="item-info">
    <span class="name">{item.name}</span>
    <span class="price">MWK {item.selling_price}</span>
  </div>
  <div class="item-controls">
    <button on:click={decrement}>−</button>
    <span>{item.qty}</span>
    <button on:click={increment}>+</button>
    <button class="remove" on:click={() => dispatch('remove')}>🗑️</button>
  </div>
</div>

<style>
  .cart-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.75rem 0;
    border-bottom: 1px solid var(--border);
  }

  .item-info {
    display: flex;
    flex-direction: column;
  }

  .name {
    font-weight: 500;
  }

  .price {
    font-size: 0.9rem;
    color: var(--text-light);
  }

  .item-controls {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .item-controls button {
    width: 28px;
    height: 28px;
    border-radius: 4px;
    border: 1px solid var(--border);
    background: white;
    cursor: pointer;
  }

  .remove {
    color: var(--danger);
    border-color: var(--danger) !important;
  }
</style>