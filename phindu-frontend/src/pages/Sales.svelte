<script>
  import { onMount } from 'svelte';
  import Layout from '../components/Layout.svelte';
  import API from '../api/api';

  let sales = [];
  let products = [];
  let showForm = false;
  let saleItems = [{ product_id: '', quantity: 1 }];
  let loading = false;

  onMount(async () => {
    await Promise.all([fetchSales(), fetchProducts()]);
  });

  async function fetchSales() {
    const res = await API.get('/sales/');
    sales = res.data;
  }

  async function fetchProducts() {
    const res = await API.get('/products/');
    products = res.data.filter(p => !p.archived);
  }

  function addItem() {
    saleItems = [...saleItems, { product_id: '', quantity: 1 }];
  }

  function removeItem(index) {
    saleItems = saleItems.filter((_, i) => i !== index);
  }

  async function submitSale() {
    const items = saleItems.filter(i => i.product_id);
    if (items.length === 0) return;
    loading = true;
    try {
      await API.post('/sales/', { items });
      alert('Sale recorded');
      saleItems = [{ product_id: '', quantity: 1 }];
      showForm = false;
      fetchSales();
    } catch (err) {
      alert('Failed to create sale');
    } finally {
      loading = false;
    }
  }
</script>

<Layout title="Sales">
  <div class="sales-header">
    <h2>Recent Sales</h2>
    <button class="btn btn-primary" on:click={() => showForm = !showForm}>
      {showForm ? 'Cancel' : '+ New Sale'}
    </button>
  </div>

  {#if showForm}
    <div class="card sale-form">
      <h3>Create Sale</h3>
      {#each saleItems as item, i}
        <div class="sale-item-row">
          <select bind:value={item.product_id}>
            <option value="">Select product</option>
            {#each products as p}
              <option value={p.id}>{p.name} (MWK {p.selling_price})</option>
            {/each}
          </select>
          <input type="number" min="1" bind:value={item.quantity} placeholder="Qty" />
          <button class="btn-icon" on:click={() => removeItem(i)}>✖</button>
        </div>
      {/each}
      <button class="btn btn-secondary" on:click={addItem}>+ Add Item</button>
      <div class="form-actions">
        <button class="btn btn-primary" on:click={submitSale} disabled={loading}>
          {loading ? 'Saving...' : 'Record Sale'}
        </button>
      </div>
    </div>
  {/if}

  <div class="sales-list">
    {#if sales.length === 0}
      <p>No sales recorded yet.</p>
    {:else}
      <table class="sales-table">
        <thead>
          <tr><th>Products</th><th>Total</th><th>Date</th></tr>
        </thead>
        <tbody>
          {#each sales as sale}
            <tr>
              <td>{sale.products.join(', ') || '-'}</td>
              <td>MWK {sale.total_amount}</td>
              <td>{new Date(sale.created_at).toLocaleString()}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    {/if}
  </div>
</Layout>

<style>
  .sales-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1.5rem;
  }

  .sale-form {
    margin-bottom: 2rem;
  }

  .sale-item-row {
    display: grid;
    grid-template-columns: 1fr 100px 40px;
    gap: 0.5rem;
    margin-bottom: 0.75rem;
  }

  .btn-icon {
    background: none;
    border: 1px solid var(--border);
    border-radius: 4px;
    font-size: 1.2rem;
    color: var(--danger);
  }

  .form-actions {
    margin-top: 1rem;
    display: flex;
    justify-content: flex-end;
  }

  .sales-table {
    width: 100%;
    background: var(--surface);
    border-radius: var(--radius);
    border: 1px solid var(--border);
  }

  .sales-table th,
  .sales-table td {
    padding: 1rem;
    text-align: left;
  }

  @media (max-width: 640px) {
    .sales-table {
      display: block;
      overflow-x: auto;
    }
  }
</style>