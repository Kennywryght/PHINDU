<script>
  import { onMount } from 'svelte';
  import Layout from '../components/Layout.svelte';
  import ProductModal from '../components/ProductModal.svelte';
  import API from '../api/api';

  let products = [];
  let loading = true;
  let showModal = false;
  let editingProduct = null;
  let filter = 'all'; // all, active, archived

  onMount(fetchProducts);

  async function fetchProducts() {
    try {
      const res = await API.get('/products/');
      products = res.data;
    } catch (err) {
      console.error(err);
    } finally {
      loading = false;
    }
  }

  async function handleSave(productData) {
    try {
      if (editingProduct) {
        await API.put(`/products/${editingProduct.id}`, productData);
      } else {
        await API.post('/products/', productData);
      }
      await fetchProducts();
      closeModal();
    } catch (err) {
      alert('Failed to save product');
    }
  }

  async function handleDelete(id) {
    if (!confirm('Delete this product?')) return;
    try {
      await API.delete(`/products/${id}`);
      fetchProducts();
    } catch (err) {
      alert('Delete failed');
    }
  }

  async function handleArchive(id) {
    try {
      await API.put(`/products/archive/${id}`);
      fetchProducts();
    } catch (err) {
      alert('Archive failed');
    }
  }

  async function handleUnarchive(id) {
    try {
      await API.put(`/products/unarchive/${id}`);
      fetchProducts();
    } catch (err) {
      alert('Unarchive failed');
    }
  }

  function openModal(product = null) {
    editingProduct = product;
    showModal = true;
  }

  function closeModal() {
    showModal = false;
    editingProduct = null;
  }

  $: filteredProducts = products.filter(p => {
    if (filter === 'archived') return p.archived;
    if (filter === 'active') return !p.archived;
    return true;
  });
</script>

<Layout title="Products">
  <div class="products-header">
    <div class="filter-tabs">
      <button class:active={filter === 'all'} on:click={() => filter = 'all'}>All</button>
      <button class:active={filter === 'active'} on:click={() => filter = 'active'}>Active</button>
      <button class:active={filter === 'archived'} on:click={() => filter = 'archived'}>Archived</button>
    </div>
    <button class="btn btn-primary" on:click={() => openModal()}>+ Add Product</button>
  </div>

  {#if loading}
    <p>Loading products...</p>
  {:else}
    <div class="products-container">
      <!-- Desktop Table -->
      <div class="table-wrapper">
        <table class="products-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Category</th>
              <th>Price</th>
              <th>Stock</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {#each filteredProducts as product}
              <tr>
                <td>{product.name}</td>
                <td>{product.category}</td>
                <td>MWK {product.selling_price}</td>
                <td>{product.stock_qty}</td>
                <td>
                  <span class="status" class:archived={product.archived}>
                    {product.archived ? 'Archived' : 'Active'}
                  </span>
                </td>
                <td class="actions">
                  <button on:click={() => openModal(product)}>✏️</button>
                  {#if product.archived}
                    <button on:click={() => handleUnarchive(product.id)}>↩️</button>
                  {:else}
                    <button on:click={() => handleArchive(product.id)}>📦</button>
                  {/if}
                  <button class="danger" on:click={() => handleDelete(product.id)}>🗑️</button>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>

      <!-- Mobile Cards (hidden on desktop) -->
      <div class="mobile-cards">
        {#each filteredProducts as product}
          <div class="product-card">
            <div class="card-header">
              <h3>{product.name}</h3>
              <span class="status" class:archived={product.archived}>
                {product.archived ? 'Archived' : 'Active'}
              </span>
            </div>
            <div class="details">
              <div><span>Category:</span> {product.category}</div>
              <div><span>Price:</span> MWK {product.selling_price}</div>
              <div><span>Stock:</span> {product.stock_qty}</div>
            </div>
            <div class="card-actions">
              <button on:click={() => openModal(product)}>Edit</button>
              {#if product.archived}
                <button on:click={() => handleUnarchive(product.id)}>Unarchive</button>
              {:else}
                <button on:click={() => handleArchive(product.id)}>Archive</button>
              {/if}
              <button class="danger" on:click={() => handleDelete(product.id)}>Delete</button>
            </div>
          </div>
        {/each}
      </div>
    </div>
  {/if}

  {#if showModal}
    <ProductModal
      product={editingProduct}
      on:save={e => handleSave(e.detail)}
      on:close={closeModal}
    />
  {/if}
</Layout>

<style>
  .products-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1.5rem;
    flex-wrap: wrap;
    gap: 1rem;
  }

  .filter-tabs {
    display: flex;
    gap: 0.5rem;
  }

  .filter-tabs button {
    padding: 0.5rem 1rem;
    border-radius: var(--radius);
    background: var(--surface);
    border: 1px solid var(--border);
  }

  .filter-tabs button.active {
    background: var(--primary);
    color: white;
    border-color: var(--primary);
  }

  .table-wrapper {
    overflow-x: auto;
    background: var(--surface);
    border-radius: var(--radius);
    border: 1px solid var(--border);
  }

  .products-table {
    width: 100%;
    border-collapse: collapse;
  }

  .products-table th {
    text-align: left;
    padding: 1rem;
    background: var(--background);
    font-weight: 600;
  }

  .products-table td {
    padding: 1rem;
    border-top: 1px solid var(--border);
  }

  .status {
    padding: 0.25rem 0.5rem;
    border-radius: 20px;
    background: #dcfce7;
    color: #166534;
    font-size: 0.8rem;
  }

  .status.archived {
    background: #fee2e2;
    color: #991b1b;
  }

  .actions {
    display: flex;
    gap: 0.5rem;
  }

  .actions button {
    padding: 0.25rem 0.5rem;
  }

  .danger {
    color: var(--danger);
  }

  .mobile-cards {
    display: none;
    flex-direction: column;
    gap: 1rem;
  }

  .product-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1rem;
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.75rem;
  }

  .details div {
    display: flex;
    justify-content: space-between;
    margin-bottom: 0.5rem;
  }

  .details span {
    color: var(--text-light);
  }

  .card-actions {
    display: flex;
    gap: 0.5rem;
    margin-top: 1rem;
  }

  .card-actions button {
    flex: 1;
    padding: 0.5rem;
    border: 1px solid var(--border);
    border-radius: var(--radius);
  }

  @media (max-width: 768px) {
    .table-wrapper {
      display: none;
    }
    .mobile-cards {
      display: flex;
    }
  }
</style>