<script>
  import { onMount } from 'svelte';
  import Layout from '../components/Layout.svelte';
  import CartItem from '../components/CartItem.svelte';
  import API from '../api/api';

  let products = [];
  let cart = [];
  let searchTerm = '';
  let loading = false;

  onMount(async () => {
    const res = await API.get('/products/');
    products = res.data.filter(p => !p.archived && p.stock_qty > 0);
  });

  $: filteredProducts = products.filter(p =>
    p.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  function addToCart(product) {
    const existing = cart.find(item => item.id === product.id);
    if (existing) {
      existing.qty += 1;
    } else {
      cart = [...cart, { ...product, qty: 1 }];
    }
  }

  function updateQty(id, qty) {
    cart = cart.map(item => item.id === id ? { ...item, qty } : item);
  }

  function removeFromCart(id) {
    cart = cart.filter(item => item.id !== id);
  }

  $: total = cart.reduce((sum, item) => sum + item.selling_price * item.qty, 0);

  async function checkout() {
    if (cart.length === 0) return;
    loading = true;
    try {
      const payload = {
        items: cart.map(item => ({ id: item.id, qty: item.qty }))
      };
      await API.post('/sales/bulk', payload);
      alert('Sale completed!');
      cart = [];
    } catch (err) {
      alert('Checkout failed');
    } finally {
      loading = false;
    }
  }
</script>

<Layout title="Point of Sale">
  <div class="pos-container">
    <div class="product-section">
      <div class="search-bar">
        <input type="text" placeholder="Search products..." bind:value={searchTerm} />
      </div>
      <div class="product-grid">
        {#each filteredProducts as product}
          <button class="product-card" on:click={() => addToCart(product)}>
            <div class="product-name">{product.name}</div>
            <div class="product-price">MWK {product.selling_price}</div>
            <div class="product-stock">Stock: {product.stock_qty}</div>
          </button>
        {/each}
      </div>
    </div>

    <div class="cart-section card">
      <h2>Current Sale</h2>
      {#if cart.length === 0}
        <p class="empty-cart">No items in cart</p>
      {:else}
        <div class="cart-items">
          {#each cart as item (item.id)}
            <CartItem
              {item}
              on:update={e => updateQty(item.id, e.detail.qty)}
              on:remove={() => removeFromCart(item.id)}
            />
          {/each}
        </div>
        <div class="cart-total">
          <span>Total:</span>
          <strong>MWK {total.toFixed(2)}</strong>
        </div>
        <button class="btn btn-primary checkout-btn" on:click={checkout} disabled={loading}>
          {loading ? 'Processing...' : 'Complete Sale'}
        </button>
      {/if}
    </div>
  </div>
</Layout>

<style>
  .pos-container {
    display: grid;
    grid-template-columns: 1fr 360px;
    gap: 1.5rem;
    height: calc(100vh - var(--topbar-height) - 3rem);
    min-height: 600px;
  }

  .product-section {
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .search-bar {
    margin-bottom: 1rem;
  }

  .search-bar input {
    width: 100%;
    padding: 0.75rem 1rem;
    font-size: 1rem;
  }

  .product-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
    gap: 1rem;
    overflow-y: auto;
    padding-right: 0.5rem;
  }

  .product-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1rem;
    text-align: left;
    transition: all 0.2s;
    width: 100%;
    cursor: pointer;
  }

  .product-card:hover {
    border-color: var(--primary);
    box-shadow: var(--shadow);
  }

  .product-name {
    font-weight: 600;
    margin-bottom: 0.25rem;
  }

  .product-price {
    color: var(--primary);
    font-weight: 700;
  }

  .product-stock {
    font-size: 0.8rem;
    color: var(--text-light);
    margin-top: 0.5rem;
  }

  .cart-section {
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .cart-items {
    flex: 1;
    overflow-y: auto;
    margin: 1rem 0;
  }

  .cart-total {
    display: flex;
    justify-content: space-between;
    padding: 1rem 0;
    border-top: 2px solid var(--border);
    font-size: 1.2rem;
  }

  .checkout-btn {
    width: 100%;
    padding: 0.75rem;
    font-size: 1.1rem;
  }

  .empty-cart {
    text-align: center;
    color: var(--text-light);
    margin: 2rem 0;
  }

  @media (max-width: 768px) {
    .pos-container {
      grid-template-columns: 1fr;
      height: auto;
    }
    .product-grid {
      max-height: 300px;
    }
  }
</style>