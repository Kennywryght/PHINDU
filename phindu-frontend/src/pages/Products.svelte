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
    Trash,
    AlertTriangle,
    Search,
    X,
    ArrowUp,
    ArrowDown,
    ArrowUpDown,
    TrendingDown,
    Wallet,
    Sparkles,
    Upload,
    Wand2,
    Package,
    Coins,
  } from "lucide-svelte";
  import Layout from "../components/Layout.svelte";
  import ProductModal from "../components/ProductModal.svelte";
  import RestockModal from "../components/RestockModal.svelte";
  import ProductDrawer from "../components/ProductDrawer.svelte";
  import BatchRestockModal from "../components/BatchRestockModal.svelte";
  import VariantWizard from "../components/VariantWizard.svelte";
  import API from "../api/api";

  let products = [];
  let grouped = [];
  let expanded = {};
  let predictions = {};
  let loading = true;
  let showModal = false;
  let editingProduct = null;
  let filter = "all";

  let showRestockModal = false;
  let restockingProduct = null;

  let showDrawer = false;
  let drawerProduct = null;

  let showBatchRestock = false;
  let showWizard = false;

  let serverCategories = [];

  let search = "";
  let selectedCategory = "";
  let sortKey = "name";
  let sortDir = 1;

  // ── Selection ──
  let selectedIds = new Set();
  let bulkWorking = false;

  // ── Attention banner ──
  let lowStockAlerts = [];
  let slowMoverAlerts = [];
  let attentionDismissedToday = false;
  let reviewMode = false;
  const ATTENTION_DAYS = 30;

  function todayKey() {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(
      d.getDate()
    ).padStart(2, "0")}`;
  }

  const ATTENTION_STORAGE_KEY = "phindu:products:attentionDismissed";

  function checkDismissedToday() {
    if (typeof window === "undefined") return false;
    const stored = window.localStorage.getItem(ATTENTION_STORAGE_KEY);
    return stored === todayKey();
  }

  function dismissAttentionForToday() {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(ATTENTION_STORAGE_KEY, todayKey());
    }
    attentionDismissedToday = true;
  }

  let prevFilter = filter;

  onMount(async () => {
    attentionDismissedToday = checkDismissedToday();
    await Promise.all([fetchProducts(), fetchCategories(), fetchAttentionAlerts()]);
  });

  async function fetchCategories() {
    try {
      const res = await API.get("/products/categories");
      serverCategories = (res.data || []).map((c) => c.name);
    } catch (err) {
      console.error("Failed to load categories", err);
      serverCategories = [];
    }
  }

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
      const visible = new Set(products.map((p) => p.id));
      selectedIds = new Set([...selectedIds].filter((id) => visible.has(id)));

      buildGroups();
      fetchPredictions();
    } catch (err) {
      console.error("Failed to fetch products", err);
    } finally {
      loading = false;
    }
  }

  async function fetchPredictions() {
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
          /* ignore */
        }
      })
    );
    predictions = results;
  }

  async function fetchAttentionAlerts() {
    try {
      const [lowRes, slowRes] = await Promise.all([
        API.get("/alerts/low-stock"),
        API.get(`/alerts/slow-movers?days=${ATTENTION_DAYS}`),
      ]);
      lowStockAlerts = Array.isArray(lowRes.data) ? lowRes.data : [];
      slowMoverAlerts = Array.isArray(slowRes.data) ? slowRes.data : [];
    } catch (err) {
      console.error("Failed to fetch attention alerts", err);
    }
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

    const sortedTops = [...tops].sort(compareFn);
    Object.keys(byParent).forEach((pid) => {
      byParent[pid].sort((a, b) =>
        (a.name || "").localeCompare(b.name || "", undefined, { sensitivity: "base" })
      );
    });

    grouped = sortedTops.map((p) => ({
      parent: p,
      variants: byParent[p.id] || [],
    }));
  }

  function compareFn(a, b) {
    const key = sortKey;
    if (key === "name") {
      const av = (a.name || "").toLowerCase();
      const bv = (b.name || "").toLowerCase();
      return av < bv ? -1 * sortDir : av > bv ? 1 * sortDir : 0;
    }
    if (key === "category") {
      const av = (a.category || "").toLowerCase();
      const bv = (b.category || "").toLowerCase();
      return av < bv ? -1 * sortDir : av > bv ? 1 * sortDir : 0;
    }
    const av = Number(a[key] || 0);
    const bv = Number(b[key] || 0);
    return (av - bv) * sortDir;
  }

  function handleSort(key) {
    if (sortKey === key) {
      sortDir = -sortDir;
    } else {
      sortKey = key;
      sortDir = 1;
    }
    buildGroups();
  }

  function sortIcon(key) {
    if (sortKey !== key) return ArrowUpDown;
    return sortDir === 1 ? ArrowUp : ArrowDown;
  }

  function toggleExpand(id) {
    expanded = { ...expanded, [id]: !expanded[id] };
  }

  $: if (filter !== prevFilter) {
    prevFilter = filter;
    fetchProducts();
  }

  function matchesCurrentFilters(p) {
    if (reviewMode) {
      const id = p.id;
      const parentId = p.parent_id;
      const matchesAlert =
        lowStockAlerts.some((a) => a.id === id || a.id === parentId) ||
        slowMoverAlerts.some((a) => a.id === id || a.id === parentId);
      if (!matchesAlert) return false;
    }
    if (selectedCategory) {
      if ((p.category || "") !== selectedCategory) return false;
    }
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      const name = (p.name || "").toLowerCase();
      const cat = (p.category || "").toLowerCase();
      if (!name.includes(q) && !cat.includes(q)) return false;
    }
    return true;
  }

  // Auto-expand parents whose variants match when the parent itself doesn't.
  // This ensures a search that only matches variants actually reveals them.
  $: if (search.trim() || selectedCategory || reviewMode) {
    grouped.forEach((g) => {
      if (g.variants.length === 0) return;
      const parentMatches = matchesCurrentFilters(g.parent);
      if (parentMatches) return;
      const matching = g.variants.filter(matchesCurrentFilters);
      if (matching.length > 0 && !expanded[g.parent.id]) {
        expanded = { ...expanded, [g.parent.id]: true };
      }
    });
  }

  $: filteredGroups = grouped
    .map((g) => {
      const parentMatches = matchesCurrentFilters(g.parent);
      const matchingVariants = g.variants.filter(matchesCurrentFilters);
      if (parentMatches) {
        return { parent: g.parent, variants: g.variants };
      }
      if (matchingVariants.length > 0) {
        return { parent: g.parent, variants: matchingVariants };
      }
      return null;
    })
    .filter(Boolean);

  $: categories = (() => {
    const set = new Set(serverCategories);
    products.forEach((p) => {
      if (p.category && p.category.trim()) set.add(p.category.trim());
    });
    return Array.from(set).sort((a, b) => a.localeCompare(b));
  })();

  // ── Summary — LEAF PRODUCTS ONLY, no archived/deleted, no parents-with-children ──
  $: summary = (() => {
    let count = 0;
    let valueSell = 0;
    let valueCost = 0;
    let lowCount = 0;

    filteredGroups.forEach((g) => {
      const isParentWithVariants = g.variants.length > 0;
      const leafList = isParentWithVariants ? g.variants : [g.parent];

      leafList.forEach((p) => {
        if (p.is_deleted || p.archived) return;
        count += 1;
        valueSell += (Number(p.selling_price) || 0) * (Number(p.stock_qty) || 0);
        valueCost += (Number(p.purchase_price) || 0) * (Number(p.stock_qty) || 0);
        const threshold = Number(p.low_stock_threshold ?? 5);
        const stock = Number(p.stock_qty ?? 0);
        if (stock <= threshold) lowCount += 1;
      });
    });

    return { count, valueSell, valueCost, lowCount };
  })();

  $: hasAttentionItems =
    (lowStockAlerts.length > 0 || slowMoverAlerts.length > 0) &&
    !attentionDismissedToday &&
    filter !== "deleted" &&
    filter !== "archived";

  $: criticalLowCount = lowStockAlerts.filter(
    (a) => a.severity === "critical" || a.severity === "out_of_stock"
  ).length;

  function reviewAlerts() {
    reviewMode = true;
    filter = "active";
    search = "";
    selectedCategory = "";
    buildGroups();
  }

  function exitReview() {
    reviewMode = false;
  }

  // ── Selection ──
  function toggleSelect(id) {
    if (selectedIds.has(id)) {
      selectedIds.delete(id);
    } else {
      selectedIds.add(id);
    }
    selectedIds = selectedIds;
  }

  function isSelected(id) {
    return selectedIds.has(id);
  }

  $: visibleIds = (() => {
    const ids = [];
    filteredGroups.forEach((g) => {
      ids.push(g.parent.id);
      g.variants.forEach((v) => ids.push(v.id));
    });
    return ids;
  })();

  $: allVisibleSelected =
    visibleIds.length > 0 && visibleIds.every((id) => selectedIds.has(id));

  $: someVisibleSelected =
    visibleIds.some((id) => selectedIds.has(id)) && !allVisibleSelected;

  function toggleSelectAll() {
    if (allVisibleSelected) {
      const next = new Set(selectedIds);
      visibleIds.forEach((id) => next.delete(id));
      selectedIds = next;
    } else {
      const next = new Set(selectedIds);
      visibleIds.forEach((id) => next.add(id));
      selectedIds = next;
    }
  }

  function clearSelection() {
    selectedIds = new Set();
  }

  async function runBulk(endpoint, extraBody = {}) {
    if (selectedIds.size === 0) return;
    bulkWorking = true;
    try {
      await API.post(endpoint, {
        product_ids: [...selectedIds],
        ...extraBody,
      });
      clearSelection();
      await fetchProducts();
      await fetchAttentionAlerts();
    } catch (err) {
      alert(
        "Bulk action failed: " + (err.response?.data?.detail || "Unknown error")
      );
    } finally {
      bulkWorking = false;
    }
  }

  async function bulkArchive() {
    if (!confirm(`Archive ${selectedIds.size} product(s)?`)) return;
    await runBulk("/products/bulk-archive");
  }

  async function bulkUnarchive() {
    if (!confirm(`Unarchive ${selectedIds.size} product(s)?`)) return;
    await runBulk("/products/bulk-unarchive");
  }

  async function bulkSoftDelete() {
    if (
      !confirm(
        `Move ${selectedIds.size} product(s) to Deleted?\n\n` +
          `They can be restored later from the Deleted tab.`
      )
    )
      return;
    await runBulk("/products/bulk-soft-delete");
  }

  async function bulkRestore() {
    if (!confirm(`Restore ${selectedIds.size} product(s)?`)) return;
    await runBulk("/products/bulk-restore");
  }

  // ── Handlers ──
  async function handleSave(productData) {
    try {
      if (editingProduct) {
        await API.put(`/products/${editingProduct.id}`, productData);
      } else {
        await API.post("/products/", productData);
      }
      await fetchProducts();
      await fetchCategories();
      closeModal();
    } catch (err) {
      alert("Failed to save product: " + (err.response?.data?.detail || "Unknown error"));
    }
  }

  async function handleSoftDelete(product) {
    const ok = confirm(
      `Move "${product.name}" to Deleted?\n\n` +
        `It will disappear from the Active list and can be restored ` +
        `later from the Deleted tab.`
    );
    if (!ok) return;
    try {
      await API.put(`/products/soft-delete/${product.id}`);
      fetchProducts();
      fetchAttentionAlerts();
    } catch (err) {
      alert("Soft delete failed: " + (err.response?.data?.detail || "Unknown error"));
    }
  }

  async function handlePermanentDelete(product) {
    const ok = confirm(
      `Permanently delete "${product.name}"?\n\n` +
        `This cannot be undone. Products with sales history will be moved ` +
        `to the Deleted tab instead of being removed.`
    );
    if (!ok) return;
    try {
      const res = await API.delete(`/products/${product.id}`);
      if (res.data?.soft_deleted) alert(res.data.message);
      fetchProducts();
      fetchAttentionAlerts();
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
      fetchAttentionAlerts();
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
    fetchAttentionAlerts();
  }

  function openDrawer(product) {
    drawerProduct = product;
    showDrawer = true;
  }

  function closeDrawer() {
    showDrawer = false;
    drawerProduct = null;
  }

  function handleDrawerEdit(product) {
    closeDrawer();
    openModal(product);
  }

  function handleDrawerRestock(product) {
    closeDrawer();
    openRestockModal(product);
  }

  async function handleDrawerArchive(product) {
    await handleArchive(product.id);
    closeDrawer();
  }

  async function handleDrawerUnarchive(product) {
    await handleUnarchive(product.id);
    closeDrawer();
  }

  async function handleDrawerSoftDelete(product) {
    await handleSoftDelete(product);
    closeDrawer();
  }

  function openBatchRestock() {
    showBatchRestock = true;
  }

  function closeBatchRestock() {
    showBatchRestock = false;
  }

  function handleBatchRestockSaved() {
    fetchProducts();
    fetchCategories();
    fetchAttentionAlerts();
  }

  function openWizard() {
    showWizard = true;
  }
  function closeWizard() {
    showWizard = false;
  }
  async function handleWizardSaved() {
    showWizard = false;
    await fetchProducts();
    await fetchCategories();
    await fetchAttentionAlerts();
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

  function isLowStock(p) {
    const threshold = Number(p.low_stock_threshold ?? 5);
    const stock = Number(p.stock_qty ?? 0);
    return !p.is_deleted && !p.archived && stock <= threshold;
  }

  function formatMoney(n) {
    const v = Number(n || 0);
    return v.toLocaleString(undefined, { maximumFractionDigits: 0 });
  }

  $: emptyCopy = (() => {
    if (reviewMode) return "No products match the current alerts.";
    if (search.trim() || selectedCategory) return "No products match your filters.";
    if (filter === "active") return "No active products. Add one to get started.";
    if (filter === "archived") return "No archived products. Nice and clean!";
    if (filter === "deleted") return "No deleted products.";
    return "No products yet. Add your first product to get started.";
  })();
</script>

<Layout title="Products">
  <div class="products-page">
    <div class="products-header">
      <div class="filter-tabs">
        <button type="button" class:active={filter === "all"} on:click={() => (filter = "all")}>
          All
        </button>
        <button type="button" class:active={filter === "active"} on:click={() => (filter = "active")}>
          Active
        </button>
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
      <div class="header-actions">
        <button class="btn btn-secondary" on:click={openWizard} type="button">
          <Wand2 size={16} strokeWidth={2} />
          <span>Add with variants</span>
        </button>
        <button class="btn btn-secondary" on:click={openBatchRestock} type="button">
          <Upload size={16} strokeWidth={2} />
          <span>Batch Restock</span>
        </button>
        <button class="btn btn-primary" on:click={() => openModal()} type="button">
          <Plus size={18} strokeWidth={2} />
          <span>Add Product</span>
        </button>
      </div>
    </div>

    {#if hasAttentionItems}
      <div class="attention-banner">
        <div class="att-icon">
          <AlertTriangle size={22} strokeWidth={2} />
        </div>
        <div class="att-body">
          {#if lowStockAlerts.length > 0}
            <div class="att-line">
              <strong>{lowStockAlerts.length}</strong>
              product{lowStockAlerts.length === 1 ? "" : "s"} need{lowStockAlerts.length === 1
                ? "s"
                : ""} restocking
              {#if criticalLowCount > 0}
                <span class="att-critical">({criticalLowCount} critical)</span>
              {/if}
            </div>
          {/if}
          {#if slowMoverAlerts.length > 0}
            <div class="att-line">
              <TrendingDown size={14} strokeWidth={2} class="att-inline-icon" />
              <strong>{slowMoverAlerts.length}</strong>
              product{slowMoverAlerts.length === 1 ? "" : "s"} haven't sold in {ATTENTION_DAYS}+ days
            </div>
          {/if}
        </div>
        <div class="att-actions">
          <button type="button" class="att-btn primary" on:click={reviewAlerts}>
            Review →
          </button>
          <button type="button" class="att-btn ghost" on:click={dismissAttentionForToday}>
            Dismiss for today
          </button>
        </div>
      </div>
    {/if}

    {#if reviewMode}
      <div class="review-strip">
        <span class="review-label">
          <Sparkles size={14} strokeWidth={2} />
          Showing products from alerts only
        </span>
        <button type="button" class="review-exit" on:click={exitReview}>
          <X size={14} strokeWidth={2} /> Clear review
        </button>
      </div>
    {/if}

    <div class="toolbar">
      <div class="search-wrap">
        <Search size={16} strokeWidth={2} class="search-icon" />
        <input
          type="text"
          placeholder="Search by name or category…"
          bind:value={search}
          class="search-input"
        />
        {#if search}
          <button class="search-clear" on:click={() => (search = "")} type="button" aria-label="Clear">
            <X size={14} strokeWidth={2} />
          </button>
        {/if}
      </div>

      <select class="category-select" bind:value={selectedCategory}>
        <option value="">All categories</option>
        {#each categories as c}
          <option value={c}>{c}</option>
        {/each}
      </select>
    </div>

    <!-- Summary strip — clear, only leaf products, no archived/deleted -->
    {#if !loading && filteredGroups.length > 0}
      <div class="summary-strip">
        <div class="sum-cell">
          <Package size={14} strokeWidth={2} class="sum-icon" />
          <div class="sum-body">
            <span class="sum-label">Products</span>
            <strong>{summary.count}</strong>
          </div>
        </div>
        <div class="sum-cell">
          <Wallet size={14} strokeWidth={2} class="sum-icon" />
          <div class="sum-body">
            <span class="sum-label">Stock value (selling)</span>
            <strong>MWK {formatMoney(summary.valueSell)}</strong>
          </div>
        </div>
        <div class="sum-cell">
          <Coins size={14} strokeWidth={2} class="sum-icon" />
          <div class="sum-body">
            <span class="sum-label">At cost</span>
            <strong>MWK {formatMoney(summary.valueCost)}</strong>
          </div>
        </div>
        {#if summary.lowCount > 0}
          <div class="sum-cell warn">
            <AlertTriangle size={14} strokeWidth={2} class="sum-icon" />
            <div class="sum-body">
              <span class="sum-label">Low stock</span>
              <strong>{summary.lowCount}</strong>
            </div>
          </div>
        {/if}
      </div>
    {/if}

    {#if loading}
      <p class="loading-text">Loading products...</p>
    {:else if filteredGroups.length === 0}
      <div class="empty-state">
        <PackageX size={48} strokeWidth={1.25} />
        <p>{emptyCopy}</p>
        {#if !reviewMode && !search && !selectedCategory && filter !== "deleted" && filter !== "archived"}
          <button class="btn btn-primary" on:click={() => openModal()} type="button">
            <Plus size={16} strokeWidth={2} /> Add your first product
          </button>
        {/if}
      </div>
    {:else}
      <div class="products-container">
        <div class="table-wrapper">
          <table class="products-table">
            <thead>
              <tr>
                <th class="checkbox-col">
                  <input
                    type="checkbox"
                    checked={allVisibleSelected}
                    indeterminate={someVisibleSelected}
                    on:change={toggleSelectAll}
                    aria-label="Select all"
                  />
                </th>
                <th>
                  <button type="button" class="sort-btn" on:click={() => handleSort("name")}>
                    Name
                    <svelte:component this={sortIcon("name")} size={13} strokeWidth={2} />
                  </button>
                </th>
                <th>
                  <button type="button" class="sort-btn" on:click={() => handleSort("category")}>
                    Category
                    <svelte:component this={sortIcon("category")} size={13} strokeWidth={2} />
                  </button>
                </th>
                <th>
                  <button type="button" class="sort-btn" on:click={() => handleSort("selling_price")}>
                    Price
                    <svelte:component this={sortIcon("selling_price")} size={13} strokeWidth={2} />
                  </button>
                </th>
                <th>
                  <button type="button" class="sort-btn" on:click={() => handleSort("stock_qty")}>
                    Stock
                    <svelte:component this={sortIcon("stock_qty")} size={13} strokeWidth={2} />
                  </button>
                </th>
                <th>Status</th>
                <th class="actions-col">Actions</th>
              </tr>
            </thead>
            <tbody>
              {#each filteredGroups as group}
                {@const pred = predictions[group.parent.id]}
                {@const parentLow = isLowStock(group.parent)}
                <tr class:parent-row={group.variants.length > 0} class:row-selected={isSelected(group.parent.id)}>
                  <td class="checkbox-col">
                    <input
                      type="checkbox"
                      checked={isSelected(group.parent.id)}
                      on:change={() => toggleSelect(group.parent.id)}
                      aria-label={`Select ${group.parent.name}`}
                    />
                  </td>
                  <td data-label="Name">
                    <div class="name-cell name-clickable" on:click={() => openDrawer(group.parent)} on:keydown={(e) => e.key === "Enter" && openDrawer(group.parent)} role="button" tabindex="0">
                      {#if group.variants.length > 0}
                        <button
                          class="expand-btn"
                          on:click|stopPropagation={() => toggleExpand(group.parent.id)}
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
                        <span class:low-stock-num={parentLow}>{group.parent.stock_qty}</span>
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
                        <button class="action-btn" on:click={() => handleRestore(group.parent.id)} title="Restore" type="button">
                          <RotateCcw size={16} strokeWidth={2} />
                        </button>
                        <button class="action-btn danger" on:click={() => handlePermanentDelete(group.parent)} title="Permanently delete" type="button">
                          <Trash size={16} strokeWidth={2} />
                        </button>
                      {:else}
                        {#if group.variants.length === 0}
                          <button
                            class="action-btn restock-pill"
                            class:critical={parentLow}
                            on:click={() => openRestockModal(group.parent)}
                            title={parentLow ? "Low stock — restock now" : "Restock"}
                            type="button"
                          >
                            <PackagePlus size={14} strokeWidth={2} />
                            {#if parentLow}<span class="pill-label">Restock</span>{/if}
                          </button>
                        {/if}
                        <button class="action-btn" on:click={() => openModal(group.parent)} title="Edit" type="button">
                          <Pencil size={16} strokeWidth={2} />
                        </button>
                        {#if group.parent.archived}
                          <button class="action-btn" on:click={() => handleUnarchive(group.parent.id)} title="Unarchive" type="button">
                            <RotateCcw size={16} strokeWidth={2} />
                          </button>
                        {:else}
                          <button class="action-btn" on:click={() => handleArchive(group.parent.id)} title="Archive" type="button">
                            <Archive size={16} strokeWidth={2} />
                          </button>
                        {/if}
                        <button class="action-btn danger-outline" on:click={() => handleSoftDelete(group.parent)} title="Soft delete" type="button">
                          <Trash2 size={16} strokeWidth={2} />
                        </button>
                      {/if}
                    </div>
                  </td>
                </tr>

                {#if expanded[group.parent.id]}
                  {#each group.variants as variant}
                    {@const vpred = predictions[variant.id]}
                    {@const vLow = isLowStock(variant)}
                    <tr class="variant-row" class:row-selected={isSelected(variant.id)}>
                      <td class="checkbox-col">
                        <input
                          type="checkbox"
                          checked={isSelected(variant.id)}
                          on:change={() => toggleSelect(variant.id)}
                          aria-label={`Select ${variant.name}`}
                        />
                      </td>
                      <td data-label="Name">
                        <div class="name-cell variant-name name-clickable" on:click={() => openDrawer(variant)} on:keydown={(e) => e.key === "Enter" && openDrawer(variant)} role="button" tabindex="0">
                          <span class="variant-indent">↳</span>
                          {variant.name}
                        </div>
                      </td>
                      <td data-label="Category">{variant.category || "—"}</td>
                      <td data-label="Price">MWK {variant.selling_price?.toLocaleString()}</td>
                      <td data-label="Stock">
                        <div class="stock-cell">
                          <span class:low-stock-num={vLow}>{variant.stock_qty}</span>
                          {#if vpred && vpred.method !== "no_data"}
                            <span class="prediction-tag {predictionClass(vpred)}">
                              <Clock size={10} strokeWidth={2} />
                              {predictionText(vpred)}
                            </span>
                          {/if}
                        </div>
                      </td>
                      <td data-label="Status">
                        <span class="status" class:archived={variant.archived} class:deleted={variant.is_deleted}>
                          {#if variant.is_deleted}Deleted{:else if variant.archived}Archived{:else}Active{/if}
                        </span>
                      </td>
                      <td data-label="Actions">
                        <div class="actions">
                          {#if variant.is_deleted}
                            <button class="action-btn" on:click={() => handleRestore(variant.id)} title="Restore" type="button">
                              <RotateCcw size={16} strokeWidth={2} />
                            </button>
                            <button class="action-btn danger" on:click={() => handlePermanentDelete(variant)} title="Permanently delete" type="button">
                              <Trash size={16} strokeWidth={2} />
                            </button>
                          {:else}
                            <button
                              class="action-btn restock-pill"
                              class:critical={vLow}
                              on:click={() => openRestockModal(variant)}
                              title={vLow ? "Low stock — restock now" : "Restock"}
                              type="button"
                            >
                              <PackagePlus size={14} strokeWidth={2} />
                              {#if vLow}<span class="pill-label">Restock</span>{/if}
                            </button>
                            <button class="action-btn" on:click={() => openModal(variant)} title="Edit" type="button">
                              <Pencil size={16} strokeWidth={2} />
                            </button>
                            <button class="action-btn danger-outline" on:click={() => handleSoftDelete(variant)} title="Soft delete" type="button">
                              <Trash2 size={16} strokeWidth={2} />
                            </button>
                          {/if}
                        </div>
                      </td>
                    </tr>
                  {/each}
                {/if}
              {/each}
            </tbody>
          </table>
        </div>

        <div class="mobile-cards">
          {#each filteredGroups as group}
            {@const pred = predictions[group.parent.id]}
            {@const parentLow = isLowStock(group.parent)}
            <div class="product-card" class:low={parentLow}>
              <div class="card-header">
                <input
                  type="checkbox"
                  class="card-checkbox"
                  checked={isSelected(group.parent.id)}
                  on:change={() => toggleSelect(group.parent.id)}
                  aria-label={`Select ${group.parent.name}`}
                />
                <div
                  class="name-cell"
                  on:click={() => openDrawer(group.parent)}
                  on:keydown={(e) => e.key === "Enter" && openDrawer(group.parent)}
                  role="button"
                  tabindex="0"
                >
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
                    <strong class:low-stock-num={parentLow}>
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
                <button class="expand-mobile-btn" on:click={() => toggleExpand(group.parent.id)} type="button">
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
                      {@const vLow = isLowStock(variant)}
                      <div class="variant-item">
                        <input
                          type="checkbox"
                          checked={isSelected(variant.id)}
                          on:change={() => toggleSelect(variant.id)}
                          aria-label={`Select ${variant.name}`}
                        />
                        <div class="variant-text">
                          <div class="variant-name">{variant.name}</div>
                          <div class="variant-meta">
                            MWK {variant.selling_price?.toLocaleString()} · Stock
                            <span class:low-stock-num={vLow}>{variant.stock_qty}</span>
                            {#if vpred && vpred.method !== "no_data"}
                              · <span class="{predictionClass(vpred)}">{predictionText(vpred)}</span>
                            {/if}
                          </div>
                        </div>
                        <div class="variant-actions">
                          {#if variant.is_deleted}
                            <button class="icon-btn" on:click={() => handleRestore(variant.id)} type="button" aria-label="Restore">
                              <RotateCcw size={14} />
                            </button>
                            <button class="icon-btn danger" on:click={() => handlePermanentDelete(variant)} type="button" aria-label="Permanently delete">
                              <Trash size={14} />
                            </button>
                          {:else}
                            <button class="icon-btn" class:critical={vLow} on:click={() => openRestockModal(variant)} type="button" aria-label="Restock">
                              <PackagePlus size={14} />
                            </button>
                            <button class="icon-btn" on:click={() => openModal(variant)} type="button" aria-label="Edit">
                              <Pencil size={14} />
                            </button>
                            <button class="icon-btn danger" on:click={() => handleSoftDelete(variant)} type="button" aria-label="Soft delete">
                              <Trash2 size={14} />
                            </button>
                          {/if}
                        </div>
                      </div>
                    {/each}
                  </div>
                {/if}
              {/if}

              <div class="card-actions">
                {#if group.parent.is_deleted}
                  <button class="action-btn full" on:click={() => handleRestore(group.parent.id)} type="button">
                    <RotateCcw size={16} strokeWidth={2} /> Restore
                  </button>
                  <button class="action-btn full danger-outline" on:click={() => handlePermanentDelete(group.parent)} type="button">
                    <Trash size={16} strokeWidth={2} /> Permanently Delete
                  </button>
                {:else}
                  {#if group.variants.length === 0}
                    <button class="action-btn full" class:critical={parentLow} on:click={() => openRestockModal(group.parent)} type="button">
                      <PackagePlus size={16} strokeWidth={2} />
                      {parentLow ? "Restock Now" : "Restock"}
                    </button>
                  {/if}
                  <button class="action-btn full" on:click={() => openModal(group.parent)} type="button">
                    <Pencil size={16} strokeWidth={2} /> Edit
                  </button>
                  {#if group.parent.archived}
                    <button class="action-btn full" on:click={() => handleUnarchive(group.parent.id)} type="button">
                      <RotateCcw size={16} strokeWidth={2} /> Unarchive
                    </button>
                  {:else}
                    <button class="action-btn full" on:click={() => handleArchive(group.parent.id)} type="button">
                      <Archive size={16} strokeWidth={2} /> Archive
                    </button>
                  {/if}
                  <button class="action-btn full danger-outline" on:click={() => handleSoftDelete(group.parent)} type="button">
                    <Trash2 size={16} strokeWidth={2} /> Soft Delete
                  </button>
                {/if}
              </div>
            </div>
          {/each}
        </div>
      </div>
    {/if}
  </div>

  {#if selectedIds.size > 0}
    <div class="bulk-bar" role="region" aria-label="Bulk actions">
      <span class="bulk-count">{selectedIds.size} selected</span>
      <div class="bulk-actions">
        {#if filter === "archived"}
          <button type="button" class="bulk-btn" on:click={bulkUnarchive} disabled={bulkWorking}>
            <RotateCcw size={14} /> Unarchive
          </button>
        {:else if filter === "deleted"}
          <button type="button" class="bulk-btn" on:click={bulkRestore} disabled={bulkWorking}>
            <RotateCcw size={14} /> Restore
          </button>
        {:else}
          <button type="button" class="bulk-btn" on:click={bulkArchive} disabled={bulkWorking}>
            <Archive size={14} /> Archive
          </button>
        {/if}
        {#if filter !== "deleted"}
          <button type="button" class="bulk-btn danger" on:click={bulkSoftDelete} disabled={bulkWorking}>
            <Trash2 size={14} /> Soft delete
          </button>
        {/if}
        <button type="button" class="bulk-btn ghost" on:click={clearSelection} disabled={bulkWorking}>
          <X size={14} /> Clear
        </button>
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

  {#if showDrawer && drawerProduct}
    <ProductDrawer
      product={drawerProduct}
      on:close={closeDrawer}
      on:edit={(e) => handleDrawerEdit(e.detail)}
      on:restock={(e) => handleDrawerRestock(e.detail)}
      on:archive={(e) => handleDrawerArchive(e.detail)}
      on:unarchive={(e) => handleDrawerUnarchive(e.detail)}
      on:softdelete={(e) => handleDrawerSoftDelete(e.detail)}
    />
  {/if}

  {#if showBatchRestock}
    <BatchRestockModal
      on:close={closeBatchRestock}
      on:saved={handleBatchRestockSaved}
    />
  {/if}

  {#if showWizard}
    <VariantWizard on:close={closeWizard} on:saved={handleWizardSaved} />
  {/if}
</Layout>

<style>
  .products-page {
    display: flex;
    flex-direction: column;
    gap: 0.9rem;
  }

  /* ── Header ── */
  .products-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.75rem;
  }
  .filter-tabs {
    display: flex;
    gap: 0.35rem;
    flex-wrap: wrap;
    background: var(--background, #f9fafb);
    padding: 0.25rem;
    border-radius: 10px;
    border: 1px solid var(--border, #e5e7eb);
  }
  .filter-tabs button {
    padding: 0.45rem 0.9rem;
    border-radius: 7px;
    background: transparent;
    border: none;
    cursor: pointer;
    font-size: 0.85rem;
    font-weight: 500;
    color: var(--text-light, #6b7280);
    transition: all 0.15s;
  }
  .filter-tabs button:hover {
    color: var(--text, #111827);
  }
  .filter-tabs button.active {
    background: var(--surface, #fff);
    color: var(--primary, #0f6b3e);
    font-weight: 600;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
  }
  .header-actions {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
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
    font-size: 0.88rem;
    transition: all 0.15s;
  }
  .btn-primary {
    background: var(--primary, #0f6b3e);
    color: white;
    box-shadow: 0 4px 12px -3px rgba(15, 107, 62, 0.4);
  }
  .btn-primary:hover {
    background: var(--primary-dark, #0a4f2e);
  }
  .btn-secondary {
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    color: var(--text, #111827);
  }
  .btn-secondary:hover {
    border-color: var(--primary, #0f6b3e);
    color: var(--primary, #0f6b3e);
  }

  /* ── Attention banner ── */
  .attention-banner {
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
    background: linear-gradient(135deg, #fffbeb 0%, #ffffff 100%);
    border: 1px solid #fcd34d;
    border-left: 4px solid #d97706;
    border-radius: 10px;
    padding: 0.85rem 1rem;
    flex-wrap: wrap;
  }
  .att-icon {
    color: #b45309;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    padding-top: 2px;
  }
  .att-body {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
  }
  .att-line {
    font-size: 0.9rem;
    color: #111827;
    display: flex;
    align-items: center;
    gap: 0.3rem;
    flex-wrap: wrap;
  }
  .att-critical {
    color: #b91c1c;
    font-weight: 600;
  }
  .att-inline-icon {
    color: #7c3aed;
  }
  .att-actions {
    display: flex;
    gap: 0.5rem;
    flex-shrink: 0;
    flex-wrap: wrap;
  }
  .att-btn {
    border: none;
    background: transparent;
    cursor: pointer;
    font-size: 0.82rem;
    font-weight: 600;
    border-radius: 7px;
    padding: 0.4rem 0.7rem;
    transition: all 0.15s;
    white-space: nowrap;
  }
  .att-btn.primary {
    background: #d97706;
    color: white;
  }
  .att-btn.primary:hover {
    background: #b45309;
  }
  .att-btn.ghost {
    color: #6b7280;
    border: 1px solid #e5e7eb;
    background: white;
  }
  .att-btn.ghost:hover {
    color: #111827;
    border-color: #9ca3af;
  }

  /* ── Review strip ── */
  .review-strip {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: #eef2ff;
    border: 1px solid #c7d2fe;
    border-radius: 8px;
    padding: 0.5rem 0.85rem;
    gap: 0.5rem;
    flex-wrap: wrap;
  }
  .review-label {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    font-size: 0.85rem;
    color: #3730a3;
    font-weight: 500;
  }
  .review-exit {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    border: none;
    background: white;
    border-radius: 6px;
    color: #4f46e5;
    font-size: 0.78rem;
    font-weight: 600;
    padding: 0.35rem 0.6rem;
    cursor: pointer;
  }
  .review-exit:hover {
    background: #e0e7ff;
  }

  /* ── Toolbar ── */
  .toolbar {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
  }
  .search-wrap {
    position: relative;
    flex: 1 1 280px;
    min-width: 0;
  }
  .search-icon {
    position: absolute;
    left: 0.9rem;
    top: 50%;
    transform: translateY(-50%);
    color: #94a3b8;
    pointer-events: none;
    z-index: 1;
  }
  .search-input {
    width: 100%;
    padding: 0.65rem 2.4rem 0.65rem 2.5rem;
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 10px;
    background: var(--surface, #fff);
    color: var(--text, #111827);
    font-size: 0.9rem;
    box-sizing: border-box;
    transition: all 0.15s;
  }
  .search-input:focus {
    outline: none;
    border-color: var(--primary, #0f6b3e);
    box-shadow: 0 0 0 3px rgba(15, 107, 62, 0.12);
  }
  .search-clear {
    position: absolute;
    right: 0.6rem;
    top: 50%;
    transform: translateY(-50%);
    border: none;
    background: var(--background, #f3f4f6);
    cursor: pointer;
    color: #64748b;
    padding: 0.25rem;
    border-radius: 50%;
    line-height: 0;
    transition: all 0.15s;
  }
  .search-clear:hover {
    color: #111827;
    background: #e5e7eb;
  }
  .category-select {
    padding: 0.65rem 0.9rem;
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 10px;
    background: var(--surface, #fff);
    color: var(--text, #111827);
    font-size: 0.9rem;
    cursor: pointer;
    min-width: 180px;
    flex: 0 1 220px;
    transition: all 0.15s;
  }
  .category-select:focus {
    outline: none;
    border-color: var(--primary, #0f6b3e);
    box-shadow: 0 0 0 3px rgba(15, 107, 62, 0.12);
  }

  /* ── Summary strip ── */
  .summary-strip {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 0.5rem;
  }
  .sum-cell {
    display: flex;
    align-items: center;
    gap: 0.65rem;
    padding: 0.75rem 0.85rem;
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 10px;
    min-width: 0;
    transition: all 0.15s;
  }
  .sum-cell:hover {
    border-color: var(--primary, #0f6b3e);
    box-shadow: 0 2px 6px rgba(15, 107, 62, 0.06);
  }
  .sum-icon {
    flex-shrink: 0;
    color: var(--primary, #0f6b3e);
    padding: 0.4rem;
    background: rgba(15, 107, 62, 0.1);
    border-radius: 8px;
    box-sizing: content-box;
  }
  .sum-body {
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
    min-width: 0;
  }
  .sum-label {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    font-weight: 600;
    color: var(--text-light, #6b7280);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .sum-body strong {
    font-size: 1rem;
    font-weight: 700;
    color: var(--text, #111827);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .sum-cell.warn {
    border-color: #fde68a;
    background: #fffbeb;
  }
  .sum-cell.warn .sum-icon {
    color: #b45309;
    background: rgba(217, 119, 6, 0.12);
  }
  .sum-cell.warn .sum-label {
    color: #92400e;
  }
  .sum-cell.warn .sum-body strong {
    color: #b45309;
  }

  /* ── Table ── */
  .table-wrapper {
    overflow-x: auto;
    background: var(--surface, #fff);
    border-radius: 12px;
    border: 1px solid var(--border, #e5e7eb);
  }
  .products-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.9rem;
  }
  .products-table th {
    text-align: left;
    padding: 0.75rem 1rem;
    background: var(--background, #f9fafb);
    font-weight: 600;
    color: var(--text-light, #6b7280);
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.4px;
    white-space: nowrap;
  }
  .products-table td {
    padding: 0.85rem 1rem;
    border-top: 1px solid var(--border, #e5e7eb);
    color: var(--text, #111827);
    vertical-align: middle;
  }
  .products-table tbody tr:hover {
    background: rgba(15, 107, 62, 0.02);
  }

  .sort-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    border: none;
    background: transparent;
    cursor: pointer;
    font: inherit;
    color: inherit;
    text-transform: inherit;
    letter-spacing: inherit;
    padding: 0;
  }
  .sort-btn:hover {
    color: var(--primary, #0f6b3e);
  }

  .checkbox-col {
    width: 40px;
    text-align: center;
    padding-left: 0.75rem !important;
    padding-right: 0.25rem !important;
  }
  .checkbox-col input {
    width: auto;
    cursor: pointer;
    accent-color: var(--primary, #0f6b3e);
  }
  .row-selected {
    background: #f0fdf4 !important;
  }

  .parent-row {
    background: var(--surface, #fff);
  }
  .variant-row {
    background: var(--background, #f9fafb);
    font-size: 0.88rem;
  }
  .variant-row td {
    padding-top: 0.6rem;
    padding-bottom: 0.6rem;
  }

  .name-cell {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  .name-clickable {
    cursor: pointer;
  }
  .name-clickable:hover strong {
    color: var(--primary, #0f6b3e);
    text-decoration: underline;
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
  .low-stock-num {
    color: #b91c1c;
    font-weight: 700;
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
    width: 220px;
  }
  .status {
    display: inline-block;
    padding: 0.2rem 0.55rem;
    border-radius: 20px;
    background: #dcfce7;
    color: #166534;
    font-size: 0.72rem;
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
    flex-wrap: wrap;
    align-items: center;
  }
  .action-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.3rem;
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
  .action-btn.danger-outline {
    color: #b91c1c;
    border-color: #fecaca;
  }
  .action-btn.danger-outline:hover {
    border-color: #dc2626;
    color: #ffffff;
    background: #dc2626;
  }
  .action-btn.full {
    flex: 1;
    padding: 0.55rem;
  }
  .action-btn.restock-pill {
    padding: 0.4rem 0.55rem;
  }
  .action-btn.restock-pill.critical {
    background: #dc2626;
    border-color: #dc2626;
    color: #ffffff;
    font-weight: 600;
  }
  .action-btn.restock-pill.critical:hover {
    background: #b91c1c;
    border-color: #b91c1c;
    color: #ffffff;
  }
  .pill-label {
    font-size: 0.75rem;
    font-weight: 600;
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

  /* ── Mobile cards ── */
  .mobile-cards {
    display: none;
    flex-direction: column;
    gap: 0.75rem;
  }
  .product-card {
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 12px;
    padding: 1rem;
    transition: all 0.15s;
  }
  .product-card:hover {
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  }
  .product-card.low {
    border-left: 3px solid #dc2626;
  }
  .card-header {
    display: flex;
    justify-content: flex-start;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.75rem;
  }
  .card-header .name-cell {
    flex: 1;
    min-width: 0;
    cursor: pointer;
  }
  .card-header .status {
    flex-shrink: 0;
  }
  .card-header h3 {
    font-size: 1rem;
    font-weight: 600;
    margin: 0;
    color: var(--text, #111827);
  }
  .card-checkbox {
    width: auto;
    margin-right: 0;
    cursor: pointer;
    accent-color: var(--primary, #0f6b3e);
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
    gap: 0.5rem;
  }
  .variant-item:last-child {
    border-bottom: none;
  }
  .variant-item input[type="checkbox"] {
    width: auto;
    cursor: pointer;
    accent-color: var(--primary, #0f6b3e);
    flex-shrink: 0;
  }
  .variant-text {
    flex: 1;
    min-width: 0;
  }
  .variant-meta {
    font-size: 0.78rem;
    color: var(--text-light, #6b7280);
    margin-top: 0.15rem;
  }
  .variant-actions {
    display: flex;
    gap: 0.25rem;
    flex-shrink: 0;
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
  .icon-btn.critical {
    background: #dc2626;
    border-color: #dc2626;
    color: white;
  }
  .icon-btn.danger {
    color: var(--danger, #dc2626);
  }
  .card-actions {
    display: flex;
    gap: 0.4rem;
    flex-wrap: wrap;
  }

  /* ── Bulk bar ── */
  .bulk-bar {
    position: fixed;
    bottom: 1rem;
    left: 50%;
    transform: translateX(-50%);
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 12px;
    padding: 0.55rem 0.75rem;
    display: flex;
    align-items: center;
    gap: 0.75rem;
    box-shadow: 0 10px 25px -8px rgba(0, 0, 0, 0.25);
    z-index: 900;
    max-width: 95vw;
    flex-wrap: wrap;
  }
  .bulk-count {
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--text, #111827);
    padding-left: 0.3rem;
  }
  .bulk-actions {
    display: flex;
    gap: 0.35rem;
    flex-wrap: wrap;
  }
  .bulk-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    border: 1px solid var(--border, #e5e7eb);
    background: var(--surface, #fff);
    color: var(--text, #111827);
    border-radius: 8px;
    padding: 0.4rem 0.75rem;
    font-size: 0.82rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.15s;
  }
  .bulk-btn:hover:not(:disabled) {
    border-color: var(--primary, #0f6b3e);
    color: var(--primary, #0f6b3e);
  }
  .bulk-btn.danger {
    color: #b91c1c;
    border-color: #fecaca;
  }
  .bulk-btn.danger:hover:not(:disabled) {
    background: #dc2626;
    border-color: #dc2626;
    color: #fff;
  }
  .bulk-btn.ghost {
    color: var(--text-light, #6b7280);
  }
  .bulk-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  /* ── Responsive ── */
  @media (max-width: 768px) {
    .products-header {
      flex-direction: column;
      align-items: stretch;
    }
    .header-actions {
      flex-direction: column;
    }
    .btn {
      justify-content: center;
      padding: 0.65rem;
    }
    .table-wrapper {
      display: none;
    }
    .mobile-cards {
      display: flex;
    }
    .att-actions {
      width: 100%;
    }
    .att-btn {
      flex: 1;
      justify-content: center;
      text-align: center;
    }
    .category-select {
      flex: 1 1 100%;
    }
    .bulk-bar {
      left: 0.5rem;
      right: 0.5rem;
      transform: none;
      bottom: 0.5rem;
    }
    .summary-strip {
      grid-template-columns: repeat(2, 1fr);
    }
  }

  @media (max-width: 480px) {
    .att-body {
      font-size: 0.82rem;
    }
    .sum-cell {
      padding: 0.6rem 0.7rem;
    }
    .sum-body strong {
      font-size: 0.92rem;
    }
    .filter-tabs {
      overflow-x: auto;
      flex-wrap: nowrap;
    }
  }
</style>