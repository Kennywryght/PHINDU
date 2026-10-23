<script>
  import { onMount } from "svelte";
  import {
    Plus,
    Pencil,
    Trash2,
    Archive,
    RotateCcw,
    PackageX,
    ChevronDown,
    ChevronRight,
    Layers,
    PackagePlus,
    Clock,
  } from "lucide-svelte";
  import Layout from "../components/Layout.svelte";
  import ProductModal from "../components/ProductModal.svelte";
  import RestockModal from "../components/RestockModal.svelte";
  import API from "../api/api";

  let products = [];
  let grouped = [];
  let expanded = {};
  let predictions = {}; // { product_id: prediction_data }
  let loading = true;
  let showModal = false;
  let editingProduct = null;
  let filter = "all";

  let showRestockModal = false;
  let restockingProduct = null;

  onMount(fetchProducts);

  async function fetchProducts() {
    loading = true;
    try {
      let url = "/products/";
      if (filter === "deleted") {
        url += "?include_deleted=true";
      }
      const res = await API.get(url);
      let filtered = res.data;

      if (filter === "active") {
        filtered = filtered.filter((p) => !p.archived && !p.is_deleted);
      } else if (filter === "archived") {
        filtered = filtered.filter((p) => p.archived && !p.is_deleted);
      } else if (filter === "deleted") {
        filtered = filtered.filter((p) => p.is_deleted);
      } else {
        filtered = filtered.filter((p) => !p.is_deleted);
      }

      products = filtered;
      buildGroups();

      // Fetch predictions in parallel (fire and forget, don't block render)
      fetchPredictions();
    } catch (err) {
      console.error("Failed to fetch products", err);
    } finally {
      loading = false;
    }
  }

  async function fetchPredictions() {
    // Only fetch for sellable products (not parents, not deleted)
    const sellable = products.filter(
      (p) => !p.is_deleted && !p.archived && (p.parent_id || !isParentOfVariants(p.id))
    );

    const results = {};
    await Promise.all(
      sellable.map(async (p) => {
        try {
          const res = await API.get(`/products/${p.id}/restock-prediction`);
          results[p.id] = res.data;
        } catch {
          // Ignore individual failures
        }
      })
    );
    predictions = results;
  }

  function isParentOfVariants(productId) {
    return products.some((p) => p.parent_id === productId);
  }

  function buildGroups() {
    const byId = {};
    products.forEach((p) => (byId[p.id] = p));

    const byParent = {};
    const tops = [];
    products.forEach((p) => {
      if (p.parent_id && byId[p.parent_id]) {
        if (!byParent[p.parent_id]) byParent[p.parent_id] = [];
        byParent[p.parent_id].push(p);
      } else {
        tops.push(p);
      }
    });

    grouped = tops.map((p) => ({
      parent: p,
      variants: byParent[p.id] || [],
    }));
  }

  function toggleExpand(id) {
    expanded[id] = !expanded[id];
  }

  $: filter, fetchProducts();

  async function handleSave(productData) {
    try {
      if (editingProduct) {
        await API.put(`/products/${editingProduct.id}`, productData);
      } else {
        await API.post("/products/", productData);
      }
      await fetchProducts();
      closeModal();
    } catch (err) {
      alert("Failed to save product: " + (err.response?.data?.detail || "Unknown error"));
    }
  }

  async function handleDelete(id) {
    if (!confirm("Delete this product?")) return;
    try {
      await API.delete(`/products/${id}`);
      fetchProducts();
    } catch (err) {
      alert("Delete failed: " + (err.response?.data?.detail || "Unknown error"));
    }
  }

  async function handleArchive(id) {
    try {
      await API.put(`/products/archive/${id}`);
      fetchProducts();
    } catch {
      alert("Archive failed");
    }
  }

  async function handleUnarchive(id) {
    try {
      await API.put(`/products/unarchive/${id}`);
      fetchProducts();
    } catch {
      alert("Unarchive failed");
    }
  }

  async function handleRestore(id) {
    try {
      await API.put(`/products/restore/${id}`);
      fetchProducts();
    } catch {
      alert("Restore failed");
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

  function openRestockModal(product) {
    restockingProduct = product;
    showRestockModal = true;
  }

  function closeRestockModal() {
    showRestockModal = false;
    restockingProduct = null;
  }

  function handleRestockSaved() {
    closeRestockModal();
    fetchProducts();
  }

  function predictionClass(pred) {
    if (!pred || pred.days_until_restock === null) return "";
    const d = pred.days_until_restock;
    if (d <= 3) return "pred-critical";
    if (d <= 7) return "pred-soon";
    return "pred-ok";
  }

  function predictionText(pred) {
    if (!pred) return null;
    if (pred.method === "no_data") return "No prediction yet";
    if (pred.days_until_restock === null) return "—";
    const d = pred.days_until_restock;
    if (d < 0) return `Overdue ${Math.abs(d)}d`;
    if (d === 0) return "Restock today";
    return `~${d}d left`;
  }
</script>

<Layout title="Products">
  <div class="products-header">
    <div class="filter-tabs">
      <button type="button" class:active={filter === "all"} on:click={() => (filter = "all")}
        >All</button
      >
      <button type="button" class:active={filter === "active"} on:click={() => (filter = "active")}
        >Active</button
      >
      <button
        type="button"
        class:active={filter === "archived"}
        on:click={() => (filter = "archived")}>Archived</button
      >
      <button
        type="button"
        class:active={filter === "deleted"}
        on:click={() => (filter = "deleted")}>Deleted</button
      >
    </div>
    <button class="btn btn-primary add-btn" on:click={() => openModal()} type="button">
      <Plus size={18} strokeWidth={2} />
      <span>Add Product</span>
    </button>
  </div>

  {#if loading}
    <p class="loading-text">Loading products...</p>
  {:else if grouped.length === 0}
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
            {#each grouped as group}
              {@const pred = predictions[group.parent.id]}
              <tr class:parent-row={group.variants.length > 0}>
                <td data-label="Name">
                  <div class="name-cell">
                    {#if group.variants.length > 0}
                      <button
                        class="expand-btn"
                        on:click={() => toggleExpand(group.parent.id)}
                        type="button"
                        aria-label="Toggle variants"
                      >
                        {#if expanded[group.parent.id]}
                          <ChevronDown size={16} />
                        {:else}
                          <ChevronRight size={16} />
                        {/if}
                      </button>
                    {/if}
                    <strong>{group.parent.name}</strong>
                    {#if group.variants.length > 0}
                      <span class="variant-badge">
                        <Layers size={11} strokeWidth={2} />
                        {group.variants.length}
                      </span>
                    {/if}
                  </div>
                </td>
                <td data-label="Category">{group.parent.category || "—"}</td>
                <td data-label="Price">
                  {#if group.variants.length > 0}
                    <span class="muted">—</span>
                  {:else}
                    MWK {group.parent.selling_price?.toLocaleString()}
                  {/if}
                </td>
                <td data-label="Stock">
                  {#if group.variants.length > 0}
                    <span class="muted">—</span>
                  {:else}
                    <div class="stock-cell">
                      <span>{group.parent.stock_qty}</span>
                      {#if pred && pred.method !== "no_data"}
                        <span class="prediction-tag {predictionClass(pred)}">
                          <Clock size={10} strokeWidth={2} />
                          {predictionText(pred)}
                        </span>
                      {/if}
                    </div>
                  {/if}
                </td>
                <td data-label="Status">
                  <span
                    class="status"
                    class:archived={group.parent.archived}
                    class:deleted={group.parent.is_deleted}
                  >
                    {#if group.parent.is_deleted}Deleted{:else if group.parent.archived}Archived{:else}Active{/if}
                  </span>
                </td>
                <td data-label="Actions">
                  <div class="actions">
                    {#if group.parent.is_deleted}
                      <button
                        class="action-btn"
                        on:click={() => handleRestore(group.parent.id)}
                        title="Restore"
                        type="button"
                      >
                        <RotateCcw size={16} strokeWidth={2} />
                      </button>
                    {:else}
                      {#if group.variants.length === 0}
                        <button
                          class="action-btn"
                          on:click={() => openRestockModal(group.parent)}
                          title="Restock"
                          type="button"
                        >
                          <PackagePlus size={16} strokeWidth={2} />
                        </button>
                      {/if}
                      <button
                        class="action-btn"
                        on:click={() => openModal(group.parent)}
                        title="Edit"
                        type="button"
                      >
                        <Pencil size={16} strokeWidth={2} />
                      </button>
                      {#if group.parent.archived}
                        <button
                          class="action-btn"
                          on:click={() => handleUnarchive(group.parent.id)}
                          title="Unarchive"
                          type="button"
                        >
                          <RotateCcw size={16} strokeWidth={2} />
                        </button>
                      {:else}
                        <button
                          class="action-btn"
                          on:click={() => handleArchive(group.parent.id)}
                          title="Archive"
                          type="button"
                        >
                          <Archive size={16} strokeWidth={2} />
                        </button>
                      {/if}
                      <button
                        class="action-btn danger"
                        on:click={() => handleDelete(group.parent.id)}
                        title="Delete"
                        type="button"
                      >
                        <Trash2 size={16} strokeWidth={2} />
                      </button>
                    {/if}
                  </div>
                </td>
              </tr>

              {#if expanded[group.parent.id]}
                {#each group.variants as variant}
                  {@const vpred = predictions[variant.id]}
                  <tr class="variant-row">
                    <td data-label="Name">
                      <div class="name-cell variant-name">
                        <span class="variant-indent">↳</span>
                        {variant.name}
                      </div>
                    </td>
                    <td data-label="Category">{variant.category || "—"}</td>
                    <td data-label="Price">MWK {variant.selling_price?.toLocaleString()}</td>
                    <td data-label="Stock">
                      <div class="stock-cell">
                        <span>{variant.stock_qty}</span>
                        {#if vpred && vpred.method !== "no_data"}
                          <span class="prediction-tag {predictionClass(vpred)}">
                            <Clock size={10} strokeWidth={2} />
                            {predictionText(vpred)}
                          </span>
                        {/if}
                      </div>
                    </td>
                    <td data-label="Status">
                      <span
                        class="status"
                        class:archived={variant.archived}
                        class:deleted={variant.is_deleted}
                      >
                        {#if variant.is_deleted}Deleted{:else if variant.archived}Archived{:else}Active{/if}
                      </span>
                    </td>
                    <td data-label="Actions">
                      <div class="actions">
                        <button
                          class="action-btn"
                          on:click={() => openRestockModal(variant)}
                          title="Restock"
                          type="button"
                        >
                          <PackagePlus size={16} strokeWidth={2} />
                        </button>
                        <button
                          class="action-btn"
                          on:click={() => openModal(variant)}
                          title="Edit"
                          type="button"
                        >
                          <Pencil size={16} strokeWidth={2} />
                        </button>
                        <button
                          class="action-btn danger"
                          on:click={() => handleDelete(variant.id)}
                          title="Delete"
                          type="button"
                        >
                          <Trash2 size={16} strokeWidth={2} />
                        </button>
                      </div>
                    </td>
                  </tr>
                {/each}
              {/if}
            {/each}
          </tbody>
        </table>
      </div>

      <!-- Mobile Cards -->
      <div class="mobile-cards">
        {#each grouped as group}
          {@const pred = predictions[group.parent.id]}
          <div class="product-card">
            <div class="card-header">
              <div class="name-cell">
                <h3>{group.parent.name}</h3>
                {#if group.variants.length > 0}
                  <span class="variant-badge">
                    <Layers size={11} strokeWidth={2} />
                    {group.variants.length}
                  </span>
                {/if}
              </div>
              <span
                class="status"
                class:archived={group.parent.archived}
                class:deleted={group.parent.is_deleted}
              >
                {#if group.parent.is_deleted}Deleted{:else if group.parent.archived}Archived{:else}Active{/if}
              </span>
            </div>
            <div class="details">
              <div><span>Category</span><strong>{group.parent.category || "—"}</strong></div>
              {#if group.variants.length === 0}
                <div>
                  <span>Price</span><strong>MWK {group.parent.selling_price?.toLocaleString()}</strong>
                </div>
                <div>
                  <span>Stock</span>
                  <strong>
                    {group.parent.stock_qty}
                    {#if pred && pred.method !== "no_data"}
                      <span class="prediction-tag {predictionClass(pred)}">
                        <Clock size={10} strokeWidth={2} />
                        {predictionText(pred)}
                      </span>
                    {/if}
                  </strong>
                </div>
              {/if}
            </div>

            {#if group.variants.length > 0}
              <button
                class="expand-mobile-btn"
                on:click={() => toggleExpand(group.parent.id)}
                type="button"
              >
                {#if expanded[group.parent.id]}
                  Hide {group.variants.length} variants
                {:else}
                  Show {group.variants.length} variants
                {/if}
              </button>

              {#if expanded[group.parent.id]}
                <div class="variant-list">
                  {#each group.variants as variant}
                    {@const vpred = predictions[variant.id]}
                    <div class="variant-item">
                      <div>
                        <div class="variant-name">{variant.name}</div>
                        <div class="variant-meta">
                          MWK {variant.selling_price?.toLocaleString()} · Stock {variant.stock_qty}
                          {#if vpred && vpred.method !== "no_data"}
                            · <span class="{predictionClass(vpred)}">{predictionText(vpred)}</span>
                          {/if}
                        </div>
                      </div>
                      <div class="variant-actions">
                        <button
                          class="icon-btn"
                          on:click={() => openRestockModal(variant)}
                          type="button"
                          aria-label="Restock"
                        >
                          <PackagePlus size={14} />
                        </button>
                        <button
                          class="icon-btn"
                          on:click={() => openModal(variant)}
                          type="button"
                          aria-label="Edit"
                        >
                          <Pencil size={14} />
                        </button>
                        <button
                          class="icon-btn danger"
                          on:click={() => handleDelete(variant.id)}
                          type="button"
                          aria-label="Delete"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>
                  {/each}
                </div>
              {/if}
            {/if}

            <div class="card-actions">
              {#if group.parent.is_deleted}
                <button
                  class="action-btn full"
                  on:click={() => handleRestore(group.parent.id)}
                  type="button"
                >
                  <RotateCcw size={16} strokeWidth={2} /> Restore
                </button>
              {:else}
                {#if group.variants.length === 0}
                  <button
                    class="action-btn full"
                    on:click={() => openRestockModal(group.parent)}
                    type="button"
                  >
                    <PackagePlus size={16} strokeWidth={2} /> Restock
                  </button>
                {/if}
                <button class="action-btn full" on:click={() => openModal(group.parent)} type="button">
                  <Pencil size={16} strokeWidth={2} /> Edit
                </button>
                {#if group.parent.archived}
                  <button
                    class="action-btn full"
                    on:click={() => handleUnarchive(group.parent.id)}
                    type="button"
                  >
                    <RotateCcw size={16} strokeWidth={2} /> Unarchive
                  </button>
                {:else}
                  <button
                    class="action-btn full"
                    on:click={() => handleArchive(group.parent.id)}
                    type="button"
                  >
                    <Archive size={16} strokeWidth={2} /> Archive
                  </button>
                {/if}
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
      on:restocked={() => fetchProducts()}
    />
  {/if}

  {#if showRestockModal && restockingProduct}
    <RestockModal
      product={restockingProduct}
      on:saved={handleRestockSaved}
      on:close={closeRestockModal}
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

  .parent-row {
    background: var(--surface, #fff);
  }

  .variant-row {
    background: var(--background, #f9fafb);
    font-size: 0.88rem;
  }

  .variant-row td {
    padding-top: 0.65rem;
    padding-bottom: 0.65rem;
  }

  .name-cell {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .variant-name {
    padding-left: 1.5rem;
  }

  .variant-indent {
    color: var(--text-light, #6b7280);
    font-weight: 400;
  }

  .expand-btn {
    background: none;
    border: none;
    cursor: pointer;
    padding: 0.15rem;
    color: var(--text-light, #6b7280);
    display: inline-flex;
    align-items: center;
    line-height: 0;
    border-radius: 4px;
  }

  .expand-btn:hover {
    background: var(--background, #f9fafb);
    color: var(--text, #111827);
  }

  .variant-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.2rem;
    background: #dbeafe;
    color: #1e40af;
    font-size: 0.7rem;
    font-weight: 600;
    padding: 0.15rem 0.45rem;
    border-radius: 20px;
  }

  .muted {
    color: var(--text-light, #6b7280);
    font-size: 0.85rem;
  }

  .stock-cell {
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
  }

  .prediction-tag {
    display: inline-flex;
    align-items: center;
    gap: 0.2rem;
    font-size: 0.7rem;
    font-weight: 600;
    padding: 0.1rem 0.4rem;
    border-radius: 20px;
    white-space: nowrap;
  }

  .pred-critical {
    background: #fee2e2;
    color: #991b1b;
  }

  .pred-soon {
    background: #fef3c7;
    color: #92400e;
  }

  .pred-ok {
    background: #dcfce7;
    color: #166534;
  }

  .actions-col {
    width: 160px;
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

  .expand-mobile-btn {
    width: 100%;
    padding: 0.55rem;
    background: var(--background, #f9fafb);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 8px;
    cursor: pointer;
    font-size: 0.85rem;
    font-weight: 500;
    color: var(--text, #111827);
    margin-bottom: 0.5rem;
  }

  .variant-list {
    margin-bottom: 0.75rem;
  }

  .variant-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.55rem 0;
    border-bottom: 1px solid var(--border, #e5e7eb);
  }

  .variant-item:last-child {
    border-bottom: none;
  }

  .variant-meta {
    font-size: 0.78rem;
    color: var(--text-light, #6b7280);
    margin-top: 0.15rem;
  }

  .variant-actions {
    display: flex;
    gap: 0.25rem;
  }

  .icon-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 30px;
    height: 30px;
    border: 1px solid var(--border, #e5e7eb);
    background: transparent;
    border-radius: 6px;
    cursor: pointer;
    color: var(--text, #111827);
    padding: 0;
  }

  .icon-btn.danger {
    color: var(--danger, #dc2626);
  }

  .card-actions {
    display: flex;
    gap: 0.4rem;
    flex-wrap: wrap;
  }

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