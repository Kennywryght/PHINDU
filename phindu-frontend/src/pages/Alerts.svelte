<script>
  import { onMount } from 'svelte';
  import Layout from '../components/Layout.svelte';
  import API from '../api/api';

  let lowStock = [];
  let loading = true;
  let error = null;

  onMount(async () => {
    try {
      const res = await API.get('/alerts/low-stock');
      lowStock = res.data;
    } catch (err) {
      error = 'Could not fetch low stock alerts.';
      console.error(err);
    } finally {
      loading = false;
    }
  });
</script>

<Layout title="Alerts">
  <div class="alerts-page">
    <div class="page-header">
      <h2>⚠️ Low Stock Alerts</h2>
      <p class="subtitle">Products that need restocking soon</p>
    </div>

    {#if loading}
      <div class="loading">Checking inventory...</div>
    {:else if error}
      <div class="error">{error}</div>
    {:else if lowStock.length === 0}
      <div class="card success-card">
        <span class="success-icon">✅</span>
        <h3>All products are well stocked</h3>
        <p>No low stock alerts at this time.</p>
      </div>
    {:else}
      <div class="alert-grid">
        {#each lowStock as product}
          <div class="alert-card">
            <div class="alert-badge">LOW STOCK</div>
            <h3>{product.name}</h3>
            <div class="details">
              <div class="detail-item">
                <span>Current Stock</span>
                <strong class="stock-value">{product.stock_qty}</strong>
              </div>
              <div class="detail-item">
                <span>Category</span>
                <strong>{product.category || '—'}</strong>
              </div>
              <div class="detail-item">
                <span>Selling Price</span>
                <strong>MWK {product.selling_price}</strong>
              </div>
            </div>
            <div class="card-actions">
              <button class="btn btn-secondary" on:click={() => window.location.href = '/products'}>
                Manage Product
              </button>
            </div>
          </div>
        {/each}
      </div>
    {/if}
  </div>
</Layout>

<style>
  .alerts-page {
    max-width: 1200px;
    margin: 0 auto;
  }

  .page-header {
    margin-bottom: 2rem;
  }

  .subtitle {
    color: var(--text-light);
    margin-top: 0.25rem;
  }

  .loading,
  .error {
    text-align: center;
    padding: 3rem;
    color: var(--text-light);
  }

  .error {
    color: var(--danger);
  }

  .success-card {
    text-align: center;
    padding: 3rem 2rem;
  }

  .success-icon {
    font-size: 3rem;
    display: block;
    margin-bottom: 1rem;
  }

  .alert-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 1.5rem;
  }

  .alert-card {
    background: var(--surface);
    border: 2px solid var(--danger);
    border-radius: var(--radius);
    padding: 1.5rem;
    position: relative;
    box-shadow: var(--shadow);
    transition: transform 0.2s;
  }

  .alert-card:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-lg);
  }

  .alert-badge {
    position: absolute;
    top: -10px;
    right: 16px;
    background: var(--danger);
    color: white;
    font-size: 0.7rem;
    font-weight: 700;
    padding: 0.25rem 0.75rem;
    border-radius: 20px;
    letter-spacing: 0.5px;
  }

  h3 {
    margin-bottom: 1.25rem;
    font-size: 1.25rem;
    color: var(--text);
  }

  .details {
    margin-bottom: 1.5rem;
  }

  .detail-item {
    display: flex;
    justify-content: space-between;
    padding: 0.5rem 0;
    border-bottom: 1px dashed var(--border);
  }

  .detail-item:last-child {
    border-bottom: none;
  }

  .detail-item span {
    color: var(--text-light);
    font-size: 0.9rem;
  }

  .stock-value {
    color: var(--danger);
    font-size: 1.25rem;
  }

  .card-actions {
    display: flex;
    justify-content: flex-end;
  }

  .card-actions .btn {
    width: 100%;
    justify-content: center;
  }

  @media (max-width: 640px) {
    .alert-grid {
      grid-template-columns: 1fr;
    }
  }
</style>