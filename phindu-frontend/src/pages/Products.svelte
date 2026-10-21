<script>
  import { onMount } from 'svelte';
  import { Plus, Pencil, Trash2, Archive, RotateCcw, PackageX } from 'lucide-svelte';
  import Layout from '../components/Layout.svelte';
  import ProductModal from '../components/ProductModal.svelte';
  import API from '../api/api';

  let products = [];
  let loading = true;
  let showModal = false;
  let editingProduct = null;
  let filter = 'all'; // all, active, archived, deleted

  onMount(fetchProducts);

  async function fetchProducts() {
    loading = true;
    try {
      let url = '/products/';
      if (filter === 'deleted') {
        url += '?include_deleted=true';
      }
      const res = await API.get(url);
      let filtered = res.data;
      if (filter === 'active') {
        filtered = filtered.filter((p) => !p.archived && !p.is_deleted);
      } else if (filter === 'archived') {
        filtered = filtered.filter((p) => p.archived && !p.is_deleted);
      } else if (filter === 'deleted') {
        filtered = filtered.filter((p) => p.is_deleted);
      } else {
        filtered = filtered.filter((p) => !p.is_deleted);
      }
      products = filtered;
    } catch (err) {
      console.error('Failed to fetch products', err);
    } finally {
      loading = false;
    }
  }

  $: filter, fetchProducts();

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

  async function handleRestore(id) {
    try {
      await API.put(`/products/restore/${id}`);
      fetchProducts();
    } catch (err) {
      alert('Restore failed');
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
</script>

<Layout title="Products">
  <div class="products-header">
    <div class="filter-tabs">
      <button type="button" class:active={filter === 'all'} on:click={() => (filter = 'all')}>All</button>
      <button type="button" class:active={filter === 'active'} on:click={() => (filter = 'active')}>Active</button>
      <button type="button" class:active={filter === 'archived'} on:click={() => (filter = 'archived')}>Archived</button>
      <button type="button" class:active={filter === 'deleted'} on:click={() => (filter = 'deleted')}>Deleted</button>
    </div>
    <button class="btn btn-primary add-btn" on:click={() => openModal()} type="button">
      <Plus size={18} strokeWidth={2} />
      <span>Add Product</span>
    </button>
  </div>

  {#if loading}
    <p class="loading-text">Loading products...</p>
  {:else if products.length === 0}
    <div class="empty-state">
      <PackageX size={48} strokeWidth={1.25} />
      <p>No products in this category</p>
      <button class="btn btn-primary" on:click={() => openModal()} type="button">
        <Plus size={16} strokeWidth={2} /> Add your first product
      </button>
    </div>
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
              <th class="actions-col">Actions</th>
            </tr>
          </thead>
          <tbody>
            {#each products as product}
              <tr>
                <td data-label="Name"><strong>{product.name}</strong></td>
                <td data-label="Category">{product.category || '—'}</td>
                <td data-label="Price">MWK {product.selling_price?.toLocaleString()}</td>
                <td data-label="Stock">{product.stock_qty}</td>
                <td data-label="Status">
                  <span class="status" class:archived={product.archived} class:deleted={product.is_deleted}>
                    {#if product.is_deleted}Deleted{:else if product.archived}Archived{:else}Active{/if}
                  </span>
                </td>
                <td data-label="Actions">
                  <div class="actions">
                    {#if product.is_deleted}
                      <button class="action-btn" on:click={() => handleRestore(product.id)} title="Restore" type="button">
                        <RotateCcw size={16} strokeWidth={2} />
                      </button>
                    {:else}
                      <button class="action-btn" on:click={() => openModal(product)} title="Edit" type="button">
                        <Pencil size={16} strokeWidth={2} />
                      </button>
                      {#if product.archived}
                        <button class="action-btn" on:click={() => handleUnarchive(product.id)} title="Unarchive" type="button">
                          <RotateCcw size={16} strokeWidth={2} />
                        </button>
                      {:else}
                        <button class="action-btn" on:click={() => handleArchive(product.id)} title="Archive" type="button">
                          <Archive size={16} strokeWidth={2} />
                        </button>
                      {/if}
                      <button class="action-btn danger" on:click={() => handleDelete(product.id)} title="Delete" type="button">
                        <Trash2 size={16} strokeWidth={2} />
                      </button>
                    {/if}
                  </div>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>

      <!-- Mobile Cards -->
      <div class="mobile-cards">
        {#each products as product}
          <div class="product-card">
            <div class="card-header">
              <h3>{product.name}</h3>
              <span class="status" class:archived={product.archived} class:deleted={product.is_deleted}>
                {#if product.is_deleted}Deleted{:else if product.archived}Archived{:else}Active{/if}
              </span>
            </div>
            <div class="details">
              <div><span>Category</span><strong>{product.category || '—'}</strong></div>
              <div><span>Price</span><strong>MWK {product.selling_price?.toLocaleString()}</strong></div>
              <div><span>Stock</span><strong>{product.stock_qty}</strong></div>
            </div>
            <div class="card-actions">
              {#if product.is_deleted}
                <button class="action-btn full" on:click={() => handleRestore(product.id)} type="button">
                  <RotateCcw size={16} strokeWidth={2} /> Restore
                </button>
              {:else}
                <button class="action-btn full" on:click={() => openModal(product)} type="button">
                  <Pencil size={16} strokeWidth={2} /> Edit
                </button>
                {#if product.archived}
                  <button class="action-btn full" on:click={() => handleUnarchive(product.id)} type="button">
                    <RotateCcw size={16} strokeWidth={2} /> Unarchive
                  </button>
                {:else}
                  <button class="action-btn full" on:click={() => handleArchive(product.id)} type="button">
                    <Archive size={16} strokeWidth={2} /> Archive
                  </button>
                {/if}
                <button class="action-btn full danger" on:click={() => handleDelete(product.id)} type="button">
                  <Trash2 size={16} strokeWidth={2} /> Delete
                </button>
              {/if}
            </div>
          </div>
        {/each}
      </div>
    </div>
  {/if}

  {#if showModal}
    <ProductModal
      product={editingProduct}
      on:save={(e) => handleSave(e.detail)}
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
    gap: 0.75rem;
  }

  .filter-tabs {
    display: flex;
    gap: 0.35rem;
    flex-wrap: wrap;
  }

  .filter-tabs button {
    padding: 0.45rem 0.9rem;
    border-radius: 8px;
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    cursor: pointer;
    font-size: 0.85rem;
    font-weight: 500;
    color: var(--text, #111827);
    transition: all 0.15s;
  }

  .filter-tabs button:hover {
    border-color: var(--primary, #0f6b3e);
    color: var(--primary, #0f6b3e);
  }

  .filter-tabs button.active {
    background: var(--primary, #0f6b3e);
    color: white;
    border-color: var(--primary, #0f6b3e);
  }

  .add-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.55rem 1rem;
    border-radius: 8px;
    background: var(--primary, #0f6b3e);
    color: white;
    border: none;
    cursor: pointer;
    font-weight: 500;
    font-size: 0.9rem;
    transition: background 0.15s;
  }

  .add-btn:hover {
    background: var(--primary-dark, #0a4f2e);
  }

  .table-wrapper {
    overflow-x: auto;
    background: var(--surface, #fff);
    border-radius: 10px;
    border: 1px solid var(--border, #e5e7eb);
  }

  .products-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.9rem;
  }

  .products-table th {
    text-align: left;
    padding: 0.85rem 1rem;
    background: var(--background, #f9fafb);
    font-weight: 600;
    color: var(--text-light, #6b7280);
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.4px;
    white-space: nowrap;
  }

  .products-table td {
    padding: 0.9rem 1rem;
    border-top: 1px solid var(--border, #e5e7eb);
    color: var(--text, #111827);
  }

  .actions-col {
    width: 140px;
  }

  .status {
    display: inline-block;
    padding: 0.2rem 0.55rem;
    border-radius: 20px;
    background: #dcfce7;
    color: #166534;
    font-size: 0.75rem;
    font-weight: 600;
  }

  .status.archived {
    background: #fef3c7;
    color: #92400e;
  }

  .status.deleted {
    background: #fee2e2;
    color: #991b1b;
  }

  .actions {
    display: flex;
    gap: 0.25rem;
  }

  .action-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.35rem;
    padding: 0.4rem 0.5rem;
    background: transparent;
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 6px;
    cursor: pointer;
    color: var(--text, #111827);
    transition: all 0.15s;
    font-size: 0.85rem;
    font-weight: 500;
  }

  .action-btn:hover {
    background: var(--background, #f9fafb);
    border-color: var(--primary, #0f6b3e);
    color: var(--primary, #0f6b3e);
  }

  .action-btn.danger:hover {
    border-color: #dc2626;
    color: #dc2626;
    background: #fef2f2;
  }

  .action-btn.full {
    flex: 1;
    padding: 0.55rem;
  }

  .loading-text {
    text-align: center;
    padding: 2rem;
    color: var(--text-light, #6b7280);
  }

  .empty-state {
    text-align: center;
    padding: 3rem 1rem;
    color: var(--text-light, #6b7280);
  }

  .empty-state p {
    margin: 1rem 0;
    font-size: 1rem;
  }

  .mobile-cards {
    display: none;
    flex-direction: column;
    gap: 0.75rem;
  }

  .product-card {
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 10px;
    padding: 1rem;
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 0.5rem;
    margin-bottom: 0.75rem;
  }

  .card-header h3 {
    font-size: 1rem;
    font-weight: 600;
    margin: 0;
    color: var(--text, #111827);
  }

  .details {
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
    margin-bottom: 1rem;
  }

  .details div {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 0.9rem;
  }

  .details span {
    color: var(--text-light, #6b7280);
  }

  .details strong {
    color: var(--text, #111827);
    font-weight: 600;
  }

  .card-actions {
    display: flex;
    gap: 0.4rem;
    flex-wrap: wrap;
  }

  /* ============ MOBILE ============ */
  @media (max-width: 768px) {
    .products-header {
      flex-direction: column;
      align-items: stretch;
    }

    .add-btn {
      justify-content: center;
      padding: 0.65rem;
    }

    .table-wrapper {
      display: none;
    }

    .mobile-cards {
      display: flex;
    }
  }
</style>