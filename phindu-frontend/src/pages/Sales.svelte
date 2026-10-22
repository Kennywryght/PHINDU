<script>
  import { onMount } from "svelte";
  import { Plus, X, Trash2, AlertTriangle, UserPlus } from "lucide-svelte";
  import Layout from "../components/Layout.svelte";
  import API from "../api/api";

  let sales = [];
  let products = [];
  let customers = [];
  let showForm = false;
  let saleItems = [{ product_id: "", quantity: 1 }];
  let loading = false;

  let isCreditSale = false;
  let selectedCustomerId = null;
  let showNewCustomerModal = false;
  let newCustomer = { name: "", phone: "", email: "", address: "" };

  let voidModalOpen = false;
  let selectedSale = null;
  let voidReason = "";

  onMount(async () => {
    await Promise.all([fetchSales(), fetchProducts(), fetchCustomers()]);
  });

  async function fetchSales() {
    const res = await API.get("/sales/");
    sales = res.data;
  }

  async function fetchProducts() {
    const res = await API.get("/products/");
    products = res.data.filter((p) => !p.archived);
  }

  async function fetchCustomers() {
    const res = await API.get("/customers/");
    customers = res.data;
  }

  function addItem() {
    saleItems = [...saleItems, { product_id: "", quantity: 1 }];
  }

  function removeItem(index) {
    saleItems = saleItems.filter((_, i) => i !== index);
  }

  async function submitSale() {
    const items = saleItems.filter((i) => i.product_id);
    if (items.length === 0) return;
    loading = true;
    try {
      const payload = {
        items,
        customer_id: isCreditSale ? selectedCustomerId : null,
        payment_status: isCreditSale ? "unpaid" : "paid",
        amount_paid: isCreditSale
          ? 0
          : items.reduce((sum, i) => {
              const p = products.find((pr) => pr.id === i.product_id);
              return sum + (p ? p.selling_price * i.quantity : 0);
            }, 0),
      };
      await API.post("/sales/", payload);
      resetForm();
      fetchSales();
    } catch (err) {
      alert("Failed to create sale: " + (err.response?.data?.detail || "Unknown error"));
    } finally {
      loading = false;
    }
  }

  function resetForm() {
    saleItems = [{ product_id: "", quantity: 1 }];
    isCreditSale = false;
    selectedCustomerId = null;
    showForm = false;
  }

  async function createCustomer() {
    try {
      const res = await API.post("/customers/", newCustomer);
      customers = [...customers, res.data];
      selectedCustomerId = res.data.id;
      showNewCustomerModal = false;
      newCustomer = { name: "", phone: "", email: "", address: "" };
    } catch {
      alert("Failed to create customer");
    }
  }

  async function voidSale() {
    if (!selectedSale) return;
    try {
      await API.post(`/sales/${selectedSale.id}/void`, null, {
        params: { reason: voidReason || undefined },
      });
      await fetchSales();
      closeVoidModal();
    } catch (err) {
      alert("Failed to void sale: " + (err.response?.data?.detail || "Unknown error"));
    }
  }

  function openVoidModal(sale) {
    selectedSale = sale;
    voidReason = "";
    voidModalOpen = true;
  }

  function closeVoidModal() {
    voidModalOpen = false;
    selectedSale = null;
    voidReason = "";
  }
</script>

<Layout title="Sales">
  <div class="sales-header">
    <h2>Recent Sales</h2>
    <button class="btn btn-primary" on:click={() => (showForm = !showForm)} type="button">
      {#if showForm}
        <X size={16} strokeWidth={2} /> Cancel
      {:else}
        <Plus size={16} strokeWidth={2} /> New Sale
      {/if}
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
              <option value={p.id}>{p.name} — MWK {p.selling_price?.toLocaleString()}</option>
            {/each}
          </select>
          <input type="number" min="1" bind:value={item.quantity} placeholder="Qty" />
          <button
            class="btn-icon"
            on:click={() => removeItem(i)}
            type="button"
            aria-label="Remove item"
          >
            <X size={16} strokeWidth={2} />
          </button>
        </div>
      {/each}
      <button class="btn btn-secondary" on:click={addItem} type="button">
        <Plus size={16} strokeWidth={2} /> Add Item
      </button>

      <div class="credit-section">
        <label class="credit-toggle">
          <input type="checkbox" bind:checked={isCreditSale} />
          <span>This is a credit sale (loan)</span>
        </label>

        {#if isCreditSale}
          <div class="customer-selector">
            <select id="customer" bind:value={selectedCustomerId}>
              <option value={null}>-- Select customer --</option>
              {#each customers as c}
                <option value={c.id}>{c.name}{c.phone ? ` (${c.phone})` : ""}</option>
              {/each}
            </select>
            <button
              class="btn btn-sm btn-outline"
              on:click={() => (showNewCustomerModal = true)}
              type="button"
            >
              <UserPlus size={14} strokeWidth={2} />
              <span>New</span>
            </button>
          </div>
        {/if}
      </div>

      <div class="form-actions">
        <button class="btn btn-primary" on:click={submitSale} disabled={loading} type="button">
          {loading ? "Saving..." : "Record Sale"}
        </button>
      </div>
    </div>
  {/if}

  <div class="sales-list">
    {#if sales.length === 0}
      <p class="no-sales">No sales recorded yet.</p>
    {:else}
      <!-- Desktop table -->
      <div class="table-wrapper">
        <table class="sales-table">
          <thead>
            <tr>
              <th>Products</th>
              <th>Total</th>
              <th>Date</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {#each sales as sale}
              <tr>
                <td>{sale.products?.join(", ") || "—"}</td>
                <td><strong>MWK {sale.total_amount?.toLocaleString()}</strong></td>
                <td>{new Date(sale.created_at).toLocaleString()}</td>
                <td>
                  {#if sale.is_voided}
                    <span class="badge voided">Voided</span>
                  {:else if sale.payment_status === "unpaid"}
                    <span class="badge credit">Credit</span>
                  {:else}
                    <span class="badge paid">Paid</span>
                  {/if}
                </td>
                <td>
                  {#if !sale.is_voided}
                    <button
                      class="btn-icon danger"
                      on:click={() => openVoidModal(sale)}
                      title="Void Sale"
                      type="button"
                    >
                      <Trash2 size={16} strokeWidth={2} />
                    </button>
                  {:else}
                    <span class="voided-label">Voided</span>
                  {/if}
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>

      <!-- Mobile cards -->
      <div class="mobile-sales">
        {#each sales as sale}
          <div class="sale-card">
            <div class="sale-card-header">
              <strong>MWK {sale.total_amount?.toLocaleString()}</strong>
              {#if sale.is_voided}
                <span class="badge voided">Voided</span>
              {:else if sale.payment_status === "unpaid"}
                <span class="badge credit">Credit</span>
              {:else}
                <span class="badge paid">Paid</span>
              {/if}
            </div>
            <p class="sale-products">{sale.products?.join(", ") || "No items"}</p>
            <div class="sale-card-footer">
              <span class="sale-date">{new Date(sale.created_at).toLocaleString()}</span>
              {#if !sale.is_voided}
                <button class="btn-icon danger" on:click={() => openVoidModal(sale)} type="button">
                  <Trash2 size={14} strokeWidth={2} /> Void
                </button>
              {/if}
            </div>
          </div>
        {/each}
      </div>
    {/if}
  </div>

  {#if voidModalOpen}
    <div
      class="modal-overlay"
      role="dialog"
      aria-modal="true"
      tabindex="-1"
      on:click|self={closeVoidModal}
      on:keydown={(e) => e.key === "Escape" && closeVoidModal()}
    >
      <div class="modal">
        <h3><AlertTriangle size={20} strokeWidth={2} /> Void Sale</h3>
        <p>Are you sure you want to void this sale? Stock will be restored.</p>
        <div class="form-group">
          <label for="voidReason">Reason (optional)</label>
          <input
            id="voidReason"
            type="text"
            bind:value={voidReason}
            placeholder="e.g., Customer return"
          />
        </div>
        <div class="modal-actions">
          <button class="btn btn-secondary" on:click={closeVoidModal} type="button">Cancel</button>
          <button class="btn btn-danger" on:click={voidSale} type="button">Confirm Void</button>
        </div>
      </div>
    </div>
  {/if}

  {#if showNewCustomerModal}
    <div
      class="modal-overlay"
      role="dialog"
      aria-modal="true"
      tabindex="-1"
      on:click|self={() => (showNewCustomerModal = false)}
      on:keydown={(e) => e.key === "Escape" && (showNewCustomerModal = false)}
    >
      <div class="modal">
        <h3>Add New Customer</h3>
        <div class="form-group">
          <label for="n-name">Name *</label>
          <input id="n-name" type="text" bind:value={newCustomer.name} required />
        </div>
        <div class="form-group">
          <label for="n-phone">Phone</label>
          <input id="n-phone" type="text" bind:value={newCustomer.phone} />
        </div>
        <div class="form-group">
          <label for="n-email">Email</label>
          <input id="n-email" type="email" bind:value={newCustomer.email} />
        </div>
        <div class="form-group">
          <label for="n-address">Address</label>
          <input id="n-address" type="text" bind:value={newCustomer.address} />
        </div>
        <div class="modal-actions">
          <button
            class="btn btn-secondary"
            on:click={() => (showNewCustomerModal = false)}
            type="button"
          >
            Cancel
          </button>
          <button
            class="btn btn-primary"
            on:click={createCustomer}
            disabled={!newCustomer.name}
            type="button"
          >
            Save
          </button>
        </div>
      </div>
    </div>
  {/if}
</Layout>

<style>
  .sales-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1.25rem;
    gap: 0.5rem;
  }
  .sales-header h2 {
    margin: 0;
    font-size: 1.15rem;
    font-weight: 600;
  }
  .btn {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.55rem 1rem;
    border-radius: 8px;
    border: none;
    cursor: pointer;
    font-weight: 500;
    font-size: 0.9rem;
    transition: all 0.15s;
  }
  .btn-primary {
    background: var(--primary, #0f6b3e);
    color: white;
  }
  .btn-primary:hover:not(:disabled) {
    background: var(--primary-dark, #0a4f2e);
  }
  .btn-primary:disabled {
    opacity: 0.55;
    cursor: not-allowed;
  }
  .btn-secondary {
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    color: var(--text, #111827);
  }
  .btn-secondary:hover {
    background: var(--background, #f9fafb);
  }
  .btn-danger {
    background: var(--danger, #dc2626);
    color: white;
  }
  .btn-sm {
    padding: 0.4rem 0.7rem;
    font-size: 0.82rem;
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
  .card {
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 12px;
    padding: 1.25rem;
  }
  .sale-form {
    margin-bottom: 1.5rem;
  }
  .sale-form h3 {
    margin-top: 0;
    margin-bottom: 1rem;
    font-size: 1.05rem;
  }
  .sale-item-row {
    display: grid;
    grid-template-columns: 1fr 90px 40px;
    gap: 0.5rem;
    margin-bottom: 0.6rem;
  }
  .btn-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.3rem;
    background: transparent;
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 8px;
    cursor: pointer;
    color: var(--text-light, #6b7280);
    padding: 0.4rem;
    transition: all 0.15s;
    font-size: 0.82rem;
  }
  .btn-icon.danger:hover {
    border-color: var(--danger, #dc2626);
    color: var(--danger, #dc2626);
    background: #fef2f2;
  }
  .form-actions {
    margin-top: 1.25rem;
    display: flex;
    justify-content: flex-end;
  }
  .credit-section {
    margin: 1rem 0;
    padding: 0.85rem;
    background: var(--background, #f9fafb);
    border-radius: 10px;
  }
  .credit-toggle {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    cursor: pointer;
    font-size: 0.9rem;
    font-weight: 500;
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
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 8px;
    background: var(--surface, #fff);
    color: var(--text, #111827);
    font-size: 0.85rem;
    min-width: 0;
  }
  .no-sales {
    text-align: center;
    padding: 2rem 1rem;
    color: var(--text-light, #6b7280);
  }
  .table-wrapper {
    overflow-x: auto;
    background: var(--surface, #fff);
    border-radius: 10px;
    border: 1px solid var(--border, #e5e7eb);
  }
  .sales-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.9rem;
  }
  .sales-table th {
    text-align: left;
    padding: 0.75rem;
    background: var(--background, #f9fafb);
    font-weight: 600;
    color: var(--text-light, #6b7280);
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.3px;
    white-space: nowrap;
  }
  .sales-table td {
    padding: 0.75rem;
    border-top: 1px solid var(--border, #e5e7eb);
    color: var(--text, #111827);
  }
  .badge {
    display: inline-block;
    padding: 0.2rem 0.55rem;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 600;
  }
  .badge.paid {
    background: #dcfce7;
    color: #166534;
  }
  .badge.credit {
    background: #fef3c7;
    color: #92400e;
  }
  .badge.voided {
    background: #fee2e2;
    color: #991b1b;
  }
  .voided-label {
    color: var(--text-light, #6b7280);
    font-size: 0.82rem;
  }
  .mobile-sales {
    display: none;
    flex-direction: column;
    gap: 0.6rem;
  }
  .sale-card {
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 10px;
    padding: 0.85rem;
  }
  .sale-card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.4rem;
  }
  .sale-card-header strong {
    color: var(--primary, #0f6b3e);
    font-size: 1rem;
  }
  .sale-products {
    font-size: 0.85rem;
    color: var(--text, #111827);
    margin: 0.3rem 0;
    word-break: break-word;
  }
  .sale-card-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 0.5rem;
    margin-top: 0.6rem;
    padding-top: 0.6rem;
    border-top: 1px dashed var(--border, #e5e7eb);
  }
  .sale-date {
    font-size: 0.75rem;
    color: var(--text-light, #6b7280);
  }
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
    max-width: 420px;
    width: 100%;
    max-height: 90vh;
    overflow-y: auto;
  }
  .modal h3 {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-top: 0;
    margin-bottom: 0.75rem;
    color: var(--text, #111827);
    font-size: 1.05rem;
  }
  .form-group {
    margin-bottom: 0.85rem;
  }
  .form-group label {
    display: block;
    margin-bottom: 0.3rem;
    font-weight: 500;
    font-size: 0.88rem;
    color: var(--text, #111827);
  }
  .modal input,
  .sale-form select,
  .sale-form input {
    width: 100%;
    padding: 0.6rem;
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 8px;
    background: var(--surface, #fff);
    color: var(--text, #111827);
    font-size: 0.9rem;
    box-sizing: border-box;
  }
  .modal input:focus,
  .sale-form select:focus,
  .sale-form input:focus {
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

  @media (max-width: 768px) {
    .table-wrapper {
      display: none;
    }
    .mobile-sales {
      display: flex;
    }
    .sale-item-row {
      grid-template-columns: 1fr 70px 40px;
    }
    .form-actions {
      justify-content: stretch;
    }
    .form-actions .btn {
      width: 100%;
      justify-content: center;
    }
  }

  @media (max-width: 480px) {
    .sales-header {
      flex-wrap: wrap;
    }
    .sale-item-row {
      grid-template-columns: 1fr 60px 36px;
      gap: 0.35rem;
    }
    .btn {
      padding: 0.5rem 0.85rem;
      font-size: 0.85rem;
    }
  }
</style>
