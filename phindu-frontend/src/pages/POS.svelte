<script>
  import { onMount } from 'svelte';
  import { Search, Plus, UserPlus, ShoppingCart, PackageX, CheckCircle2 } from 'lucide-svelte';
  import Layout from '../components/Layout.svelte';
  import CartItem from '../components/CartItem.svelte';
  import API from '../api/api';

  let products = [];
  let customers = [];
  let cart = [];
  let searchTerm = '';
  let loading = false;

  let isCreditSale = false;
  let selectedCustomerId = null;
  let showNewCustomerModal = false;
  let newCustomer = { name: '', phone: '', email: '', address: '' };

  let checkoutSuccess = false;

  onMount(async () => {
    const [productsRes, customersRes] = await Promise.all([
      API.get('/products/'),
      API.get('/customers/'),
    ]);
    products = productsRes.data.filter((p) => !p.archived && p.stock_qty > 0);
    customers = customersRes.data;
  });

  $: filteredProducts = products.filter((p) =>
    p.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  function addToCart(product) {
    const existing = cart.find((item) => item.id === product.id);
    if (existing) {
      existing.qty += 1;
      cart = [...cart];
    } else {
      cart = [...cart, { ...product, qty: 1 }];
    }
  }

  function updateQty(id, qty) {
    cart = cart.map((item) => (item.id === id ? { ...item, qty } : item));
  }

  function removeFromCart(id) {
    cart = cart.filter((item) => item.id !== id);
  }

  $: total = cart.reduce((sum, item) => sum + item.selling_price * item.qty, 0);

  async function checkout() {
    if (cart.length === 0) return;
    if (isCreditSale && !selectedCustomerId) {
      alert('Please select a customer for credit sale');
      return;
    }
    loading = true;
    try {
      const payload = {
        items: cart.map((item) => ({ id: item.id, qty: item.qty })),
        customer_id: isCreditSale ? selectedCustomerId : null,
        payment_status: isCreditSale ? 'unpaid' : 'paid',
        amount_paid: isCreditSale ? 0 : total,
      };
      await API.post('/sales/bulk', payload);

      checkoutSuccess = true;
      setTimeout(() => (checkoutSuccess = false), 2000);

      cart = [];
      isCreditSale = false;
      selectedCustomerId = null;
    } catch (err) {
      alert('Checkout failed: ' + (err.response?.data?.detail || 'Unknown error'));
    } finally {
      loading = false;
    }
  }

  async function createCustomer() {
    if (!newCustomer.name) return;
    try {
      const res = await API.post('/customers/', newCustomer);
      customers = [...customers, res.data];
      selectedCustomerId = res.data.id;
      showNewCustomerModal = false;
      newCustomer = { name: '', phone: '', email: '', address: '' };
    } catch (err) {
      alert('Failed to create customer');
    }
  }

  function closeCustomerModal() {
    showNewCustomerModal = false;
  }
</script>

<Layout title="Point of Sale">
  <div class="pos-container">
    <!-- PRODUCTS -->
    <div class="product-section">
      <div class="search-bar">
        <Search size={18} strokeWidth={2} class="search-icon" />
        <input type="text" placeholder="Search products..." bind:value={searchTerm} />
      </div>

      {#if filteredProducts.length === 0}
        <div class="empty-products">
          <PackageX size={44} strokeWidth={1.25} />
          <p>No products found</p>
        </div>
      {:else}
        <div class="product-grid">
          {#each filteredProducts as product}
            <button class="product-card" on:click={() => addToCart(product)} type="button">
              <div class="product-name">{product.name}</div>
              <div class="product-price">MWK {product.selling_price?.toLocaleString()}</div>
              <div class="product-stock">Stock: {product.stock_qty}</div>
            </button>
          {/each}
        </div>
      {/if}
    </div>

    <!-- CART -->
    <div class="cart-section">
      <div class="cart-header">
        <h2>
          <ShoppingCart size={18} strokeWidth={2} />
          Current Sale
        </h2>
      </div>

      {#if cart.length === 0}
        <div class="empty-cart">
          <ShoppingCart size={40} strokeWidth={1.25} />
          <p>Cart is empty</p>
        </div>
      {:else}
        <div class="cart-items">
          {#each cart as item (item.id)}
            <CartItem
              {item}
              on:update={(e) => updateQty(item.id, e.detail.qty)}
              on:remove={() => removeFromCart(item.id)}
            />
          {/each}
        </div>
        <div class="cart-total">
          <span>Total:</span>
          <strong>MWK {total.toLocaleString()}</strong>
        </div>
      {/if}

      <div class="credit-section">
        <label class="credit-toggle">
          <input type="checkbox" bind:checked={isCreditSale} />
          <span>Credit Sale (Loan)</span>
        </label>

        {#if isCreditSale}
          <div class="customer-selector">
            <select bind:value={selectedCustomerId}>
              <option value={null}>-- Select customer --</option>
              {#each customers as c}
                <option value={c.id}>{c.name}{c.phone ? ` (${c.phone})` : ''}</option>
              {/each}
            </select>
            <button class="btn btn-sm btn-outline" on:click={() => (showNewCustomerModal = true)} type="button">
              <UserPlus size={14} strokeWidth={2} />
              <span>New</span>
            </button>
          </div>
        {/if}
      </div>

      <button
        class="checkout-btn"
        class:success={checkoutSuccess}
        on:click={checkout}
        disabled={loading || cart.length === 0}
        type="button"
      >
        {#if checkoutSuccess}
          <CheckCircle2 size={18} strokeWidth={2} /> Sale completed!
        {:else if loading}
          <span class="spinner"></span> Processing...
        {:else}
          <ShoppingCart size={18} strokeWidth={2} /> Complete Sale — MWK {total.toLocaleString()}
        {/if}
      </button>
    </div>
  </div>

  <!-- NEW CUSTOMER MODAL -->
  {#if showNewCustomerModal}
    <div class="modal-overlay" role="dialog" aria-modal="true" tabindex="-1" on:click|self={closeCustomerModal}>
      <div class="modal">
        <h3>Add New Customer</h3>
        <div class="form-group">
          <label for="cust-name">Name *</label>
          <input id="cust-name" type="text" bind:value={newCustomer.name} required />
        </div>
        <div class="form-group">
          <label for="cust-phone">Phone</label>
          <input id="cust-phone" type="text" bind:value={newCustomer.phone} />
        </div>
        <div class="form-group">
          <label for="cust-email">Email</label>
          <input id="cust-email" type="email" bind:value={newCustomer.email} />
        </div>
        <div class="form-group">
          <label for="cust-address">Address</label>
          <input id="cust-address" type="text" bind:value={newCustomer.address} />
        </div>
        <div class="modal-actions">
          <button class="btn btn-secondary" on:click={closeCustomerModal} type="button">Cancel</button>
          <button class="btn btn-primary" on:click={createCustomer} disabled={!newCustomer.name} type="button">
            Save
          </button>
        </div>
      </div>
    </div>
  {/if}
</Layout>

<style>
  .pos-container {
    display: grid;
    grid-template-columns: 1fr 380px;
    gap: 1.25rem;
    height: calc(100vh - var(--topbar-height, 64px) - 3rem);
    min-height: 500px;
  }

  /* ============ PRODUCTS ============ */
  .product-section {
    display: flex;
    flex-direction: column;
    overflow: hidden;
    min-width: 0;
  }

  .search-bar {
    position: relative;
    margin-bottom: 1rem;
    flex-shrink: 0;
  }

  .search-icon {
    position: absolute;
    left: 1rem;
    top: 50%;
    transform: translateY(-50%);
    color: var(--text-light, #6b7280);
    pointer-events: none;
  }

  .search-bar input {
    width: 100%;
    padding: 0.75rem 1rem 0.75rem 2.75rem;
    font-size: 0.95rem;
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 10px;
    background: var(--surface, #fff);
    box-sizing: border-box;
    color: var(--text, #111827);
  }

  .search-bar input:focus {
    outline: none;
    border-color: var(--primary, #0f6b3e);
    box-shadow: 0 0 0 3px rgba(15, 107, 62, 0.1);
  }

  .product-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
    gap: 0.75rem;
    overflow-y: auto;
    padding-right: 0.35rem;
    overscroll-behavior: contain;
  }

  .product-card {
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 10px;
    padding: 0.85rem;
    text-align: left;
    transition: all 0.15s;
    width: 100%;
    cursor: pointer;
    min-height: 96px;
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
  }

  .product-card:hover {
    border-color: var(--primary, #0f6b3e);
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.06);
    transform: translateY(-1px);
  }

  .product-card:active {
    transform: translateY(0);
  }

  .product-name {
    font-weight: 600;
    font-size: 0.88rem;
    color: var(--text, #111827);
    line-height: 1.3;
    overflow: hidden;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
  }

  .product-price {
    color: var(--primary, #0f6b3e);
    font-weight: 700;
    font-size: 0.9rem;
    margin-top: auto;
  }

  .product-stock {
    font-size: 0.72rem;
    color: var(--text-light, #6b7280);
  }

  .empty-products {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 3rem 1rem;
    color: var(--text-light, #6b7280);
    gap: 0.75rem;
  }

  /* ============ CART ============ */
  .cart-section {
    display: flex;
    flex-direction: column;
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 12px;
    padding: 1rem;
    overflow: hidden;
    min-width: 0;
  }

  .cart-header {
    flex-shrink: 0;
    margin-bottom: 0.5rem;
  }

  .cart-header h2 {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 1.05rem;
    font-weight: 600;
    margin: 0;
    color: var(--text, #111827);
  }

  .cart-items {
    flex: 1;
    overflow-y: auto;
    margin: 0.75rem 0;
    padding-right: 0.25rem;
    overscroll-behavior: contain;
  }

  .empty-cart {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    flex: 1;
    color: var(--text-light, #6b7280);
    gap: 0.75rem;
    padding: 2rem 1rem;
  }

  .cart-total {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.85rem 0;
    border-top: 2px solid var(--border, #e5e7eb);
    font-size: 1.1rem;
    flex-shrink: 0;
  }

  .cart-total strong {
    color: var(--primary, #0f6b3e);
    font-size: 1.3rem;
  }

  .credit-section {
    margin: 0.75rem 0;
    padding: 0.75rem;
    background: var(--background, #f9fafb);
    border-radius: 10px;
    flex-shrink: 0;
  }

  .credit-toggle {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    cursor: pointer;
    font-size: 0.9rem;
    font-weight: 500;
    color: var(--text, #111827);
  }

  .credit-toggle input {
    width: auto;
    cursor: pointer;
  }

  .customer-selector {
    display: flex;
    gap: 0.4rem;
    margin-top: 0.6rem;
  }

  .customer-selector select {
    flex: 1;
    padding: 0.5rem;
    border-radius: 8px;
    border: 1px solid var(--border, #e5e7eb);
    background: var(--surface, #fff);
    color: var(--text, #111827);
    font-size: 0.85rem;
    min-width: 0;
  }

  .checkout-btn {
    width: 100%;
    padding: 0.85rem;
    font-size: 1rem;
    font-weight: 600;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    background: var(--primary, #0f6b3e);
    color: white;
    border: none;
    border-radius: 10px;
    cursor: pointer;
    transition: all 0.15s;
    flex-shrink: 0;
  }

  .checkout-btn:hover:not(:disabled) {
    background: var(--primary-dark, #0a4f2e);
  }

  .checkout-btn:disabled {
    opacity: 0.55;
    cursor: not-allowed;
  }

  .checkout-btn.success {
    background: #16a34a;
  }

  .spinner {
    width: 16px;
    height: 16px;
    border: 2px solid rgba(255, 255, 255, 0.4);
    border-top-color: white;
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  /* ============ MODAL ============ */
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
    padding: 1.5rem;
    max-width: 400px;
    width: 100%;
    max-height: 90vh;
    overflow-y: auto;
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
    font-size: 0.9rem;
    box-sizing: border-box;
    background: var(--surface, #fff);
    color: var(--text, #111827);
  }

  input:focus {
    outline: none;
    border-color: var(--primary, #0f6b3e);
    box-shadow: 0 0 0 3px rgba(15, 107, 62, 0.1);
  }

  .modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: 0.6rem;
    margin-top: 1.25rem;
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

  .btn-primary {
    background: var(--primary, #0f6b3e);
    color: white;
  }

  .btn-primary:hover:not(:disabled) {
    background: var(--primary-dark, #0a4f2e);
  }

  .btn-primary:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .btn-secondary {
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    color: var(--text, #111827);
  }

  .btn-outline {
    background: transparent;
    border: 1px solid var(--border, #e5e7eb);
    color: var(--text, #111827);
  }

  .btn-outline:hover {
    border-color: var(--primary, #0f6b3e);
    color: var(--primary, #0f6b3e);
  }

  .btn-sm {
    padding: 0.45rem 0.75rem;
    font-size: 0.85rem;
  }

  /* ============ TABLET ============ */
  @media (max-width: 1024px) {
    .pos-container {
      grid-template-columns: 1fr 320px;
    }
  }

  /* ============ MOBILE ============ */
  @media (max-width: 768px) {
    .pos-container {
      grid-template-columns: 1fr;
      height: auto;
      gap: 1rem;
    }

    .product-grid {
      max-height: 300px;
    }

    .cart-section {
      min-height: 320px;
      max-height: 80vh;
    }

    .cart-items {
      max-height: 260px;
    }
  }

  /* ============ SMALL MOBILE ============ */
  @media (max-width: 480px) {
    .product-grid {
      grid-template-columns: repeat(2, 1fr);
      gap: 0.5rem;
      max-height: 260px;
    }

    .product-card {
      padding: 0.65rem;
      min-height: 84px;
    }

    .product-name {
      font-size: 0.8rem;
    }

    .product-price {
      font-size: 0.82rem;
    }

    .cart-total strong {
      font-size: 1.15rem;
    }
  }
</style>