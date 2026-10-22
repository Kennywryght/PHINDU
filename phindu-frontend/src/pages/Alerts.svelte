<script>
  import { onMount } from "svelte";
  import { AlertTriangle, CheckCircle2, Package } from "lucide-svelte";
  import Layout from "../components/Layout.svelte";
  import API from "../api/api";

  let lowStock = [];
  let loading = true;
  let error = null;

  onMount(async () => {
    try {
      const res = await API.get("/alerts/low-stock");
      lowStock = res.data;
    } catch {
      error = "Could not fetch low stock alerts.";
      console.error(err);
    } finally {
      loading = false;
    }
  });
</script>

<Layout title="Alerts">
  <div class="alerts-page">
    <div class="page-header">
      <h2>
        <AlertTriangle size={22} strokeWidth={2} />
        Low Stock Alerts
      </h2>
      <p class="subtitle">Products that need restocking soon</p>
    </div>

    {#if loading}
      <div class="state-box">Checking inventory...</div>
    {:else if error}
      <div class="state-box error">{error}</div>
    {:else if lowStock.length === 0}
      <div class="card success-card">
        <CheckCircle2 size={48} strokeWidth={1.5} class="success-icon" />
        <h3>All products are well stocked</h3>
        <p>No low stock alerts at this time.</p>
      </div>
    {:else}
      <div class="alert-grid">
        {#each lowStock as product}
          <div class="alert-card">
            <div class="alert-badge">LOW STOCK</div>
            <h3>
              <Package size={18} strokeWidth={2} />
              {product.name}
            </h3>
            <div class="details">
              <div class="detail-item">
                <span>Current Stock</span>
                <strong class="stock-value">{product.stock_qty}</strong>
              </div>
              <div class="detail-item">
                <span>Category</span>
                <strong>{product.category || "—"}</strong>
              </div>
              <div class="detail-item">
                <span>Selling Price</span>
                <strong>MWK {product.selling_price?.toLocaleString()}</strong>
              </div>
            </div>
            <div class="card-actions">
              <button
                class="btn btn-primary"
                on:click={() => (window.location.href = "/products")}
                type="button"
              >
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
    margin-bottom: 1.5rem;
  }
  .page-header h2 {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin: 0;
    font-size: 1.2rem;
    font-weight: 600;
    color: var(--text, #111827);
  }
  .subtitle {
    color: var(--text-light, #6b7280);
    margin-top: 0.25rem;
    font-size: 0.88rem;
  }
  .state-box {
    text-align: center;
    padding: 2rem;
    color: var(--text-light, #6b7280);
    font-size: 0.9rem;
  }
  .state-box.error {
    color: var(--danger, #dc2626);
  }
  .card {
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 12px;
    padding: 1.25rem;
  }
  .success-card {
    text-align: center;
    padding: 2.5rem 1.5rem;
  }
  .success-card h3 {
    margin: 0 0 0.5rem;
    font-size: 1.05rem;
    font-weight: 600;
    color: var(--text, #111827);
  }
  .success-card p {
    color: var(--text-light, #6b7280);
    margin: 0;
    font-size: 0.9rem;
  }
  .alert-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 1rem;
  }
  .alert-card {
    background: var(--surface, #fff);
    border: 2px solid var(--danger, #dc2626);
    border-radius: 12px;
    padding: 1.25rem;
    position: relative;
    transition: transform 0.2s;
  }
  .alert-card:hover {
    transform: translateY(-2px);
  }
  .alert-badge {
    position: absolute;
    top: -9px;
    right: 1rem;
    background: var(--danger, #dc2626);
    color: white;
    font-size: 0.65rem;
    font-weight: 700;
    padding: 0.2rem 0.6rem;
    border-radius: 20px;
    letter-spacing: 0.5px;
  }
  .alert-card h3 {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    margin: 0.5rem 0 1rem;
    font-size: 1rem;
    font-weight: 600;
    color: var(--text, #111827);
  }
  .details {
    margin-bottom: 1rem;
  }
  .detail-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.5rem 0;
    border-bottom: 1px dashed var(--border, #e5e7eb);
    gap: 0.5rem;
  }
  .detail-item:last-child {
    border-bottom: none;
  }
  .detail-item span {
    color: var(--text-light, #6b7280);
    font-size: 0.85rem;
  }
  .detail-item strong {
    color: var(--text, #111827);
    font-size: 0.9rem;
  }
  .stock-value {
    color: var(--danger, #dc2626) !important;
    font-size: 1.1rem !important;
  }
  .btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.4rem;
    padding: 0.55rem 1rem;
    border-radius: 8px;
    border: none;
    cursor: pointer;
    font-weight: 500;
    font-size: 0.9rem;
    width: 100%;
    background: var(--primary, #0f6b3e);
    color: white;
    transition: background 0.15s;
  }
  .btn:hover {
    background: var(--primary-dark, #0a4f2e);
  }

  @media (max-width: 640px) {
    .alert-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
