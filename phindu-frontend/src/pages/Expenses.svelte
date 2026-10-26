<script>
  import { onMount } from "svelte";
  import {
    Receipt,
    CheckCircle2,
    AlertCircle,
    Search,
    X,
    Pencil,
    Trash2,
    ChevronLeft,
    ChevronRight,
    Loader2,
    Plus,
    Wallet,
    CalendarDays,
    TrendingUp,
  } from "lucide-svelte";
  import { user as userStore } from "../stores/auth";
  import Layout from "../components/Layout.svelte";
  import ExpenseEditModal from "../components/ExpenseEditModal.svelte";
  import API from "../api/api";

  // Form
  let name = "";
  let amount = "";
  let category = "";
  let useNewCategory = false;
  let newCategoryName = "";
  let loading = false;
  let message = "";
  let messageType = "";

  // List state
  let expenses = [];
  let totalExpenses = 0;
  let hasMore = false;
  let loadingList = false;
  const PAGE_SIZE = 20;
  let listOffset = 0;

  // Filters
  let searchQ = "";
  let selectedCategory = "";
  let dateRange = "all"; // all | today | 7d | 30d

  // Categories (from server)
  let categories = [];
  let loadingCategories = true;

  // Summary
  let summary = null;

  // Edit modal
  let editingExpense = null;

  // Role
  let currentUser = null;
  const unsub = userStore.subscribe((v) => (currentUser = v));
  $: canEdit = currentUser?.role === "manager" || currentUser?.role === "owner";

  // Cleanup store sub
  import { onDestroy } from "svelte";
  onDestroy(unsub);

  // Quick add presets
  const QUICK_ADD = [
    { name: "Rent", category: "Rent" },
    { name: "Transport", category: "Transport" },
    { name: "Supplies", category: "Supplies" },
    { name: "Utilities", category: "Utilities" },
    { name: "Salary", category: "Salary" },
  ];

  onMount(async () => {
    await Promise.all([fetchCategories(), fetchSummary(), fetchExpenses(true)]);
  });

  async function fetchCategories() {
    try {
      const res = await API.get("/expenses/categories");
      categories = res.data || [];
    } catch (err) {
      console.error("Failed to load categories", err);
      categories = [];
    } finally {
      loadingCategories = false;
    }
  }

  async function fetchSummary() {
    try {
      const res = await API.get("/expenses/summary");
      summary = res.data;
    } catch (err) {
      console.error("Failed to load summary", err);
    }
  }

  async function fetchExpenses(reset = false) {
    if (loadingList) return;
    loadingList = true;
    try {
      if (reset) listOffset = 0;
      const params = {
        limit: PAGE_SIZE,
        offset: reset ? 0 : listOffset,
      };
      if (searchQ.trim()) params.q = searchQ.trim();
      if (selectedCategory) params.category = selectedCategory;
      if (dateRange === "today") params.days = 1;
      else if (dateRange === "7d") params.days = 7;
      else if (dateRange === "30d") params.days = 30;

      const res = await API.get("/expenses/", { params });
      const data = res.data;
      const page = Array.isArray(data) ? data : data.items || [];
      expenses = reset ? page : [...expenses, ...page];
      totalExpenses = Array.isArray(data) ? page.length : data.total || page.length;
      hasMore = Array.isArray(data) ? false : !!data.has_more;
      listOffset = expenses.length;
    } catch (err) {
      console.error("Failed to fetch expenses", err);
    } finally {
      loadingList = false;
    }
  }

  function applyFilter(fn) {
    fn();
    fetchExpenses(true);
  }

  function setDateRange(r) {
    if (dateRange === r) return;
    dateRange = r;
    fetchExpenses(true);
  }

  function onCategoryFilterChange(e) {
    selectedCategory = e.target.value;
    fetchExpenses(true);
  }

  function onNewCategorySelect(e) {
    const v = e.target.value;
    if (v === "__new__") {
      useNewCategory = true;
      category = "";
    } else {
      useNewCategory = false;
      category = v;
    }
  }

  function quickAddPreset(preset) {
    name = preset.name;
    category = preset.category;
    useNewCategory = false;
    // Focus amount input
    const el = document.getElementById("amount");
    if (el) el.focus();
  }

  async function handleSubmit() {
    if (!name.trim() || !amount) {
      message = "Name and amount are required.";
      messageType = "error";
      return;
    }

    const finalCategory = useNewCategory
      ? newCategoryName.trim() || "Uncategorized"
      : category.trim() || "Uncategorized";

    loading = true;
    message = "";

    try {
      await API.post("/expenses/", {
        name: name.trim(),
        amount: parseFloat(amount),
        category: finalCategory,
      });
      message = "Expense recorded successfully!";
      messageType = "success";
      name = "";
      amount = "";
      category = "";
      newCategoryName = "";
      useNewCategory = false;
      await Promise.all([
        fetchExpenses(true),
        fetchSummary(),
        fetchCategories(),
      ]);
    } catch (err) {
      message =
        err.response?.data?.detail || "Failed to record expense. Please try again.";
      messageType = "error";
    } finally {
      loading = false;
    }
  }

  function openEdit(exp) {
    editingExpense = exp;
  }
  function closeEdit() {
    editingExpense = null;
  }
  async function handleEdited() {
    editingExpense = null;
    await Promise.all([fetchExpenses(true), fetchSummary(), fetchCategories()]);
  }

  function fmt(n) {
    return Number(n || 0).toLocaleString(undefined, {
      maximumFractionDigits: 2,
    });
  }

  function fmtDate(iso) {
    if (!iso) return "—";
    return new Date(iso).toLocaleString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  function fmtShortDate(iso) {
    if (!iso) return "—";
    return new Date(iso).toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
    });
  }
</script>

<Layout title="Expenses">
  <div class="page-wrapper">
    <!-- ── Summary strip ── -->
    {#if summary}
      <div class="summary-strip">
        <div class="sum-cell">
          <span class="sum-label">Total expenses</span>
          <strong>MWK {fmt(summary.total)}</strong>
        </div>
        <div class="sum-cell">
          <span class="sum-label">Today</span>
          <strong>MWK {fmt(summary.today)}</strong>
        </div>
        <div class="sum-cell">
          <span class="sum-label">This week</span>
          <strong>MWK {fmt(summary.this_week)}</strong>
        </div>
        <div class="sum-cell">
          <span class="sum-label">Records</span>
          <strong>{summary.count}</strong>
        </div>
      </div>

      {#if summary.top_categories && summary.top_categories.length > 0}
        <div class="top-cats-card">
          <div class="tc-header">
            <TrendingUp size={16} strokeWidth={2} />
            <span>Top spending categories</span>
          </div>
          <div class="tc-list">
            {#each summary.top_categories as cat}
              <div class="tc-row">
                <span class="tc-name">{cat.category}</span>
                <span class="tc-amount">MWK {fmt(cat.total)}</span>
              </div>
            {/each}
          </div>
        </div>
      {/if}
    {/if}

    <!-- ── Add expense card ── -->
    <div class="card expense-card">
      <h2>
        <Receipt size={20} strokeWidth={2} />
        Record New Expense
      </h2>

      <!-- Quick add chips -->
      <div class="quick-add-row">
        <span class="qa-label">Quick add:</span>
        {#each QUICK_ADD as p}
          <button
            class="qa-chip"
            type="button"
            on:click={() => quickAddPreset(p)}
            disabled={loading}
          >
            <Plus size={12} /> {p.name}
          </button>
        {/each}
      </div>

      <form on:submit|preventDefault={handleSubmit}>
        <div class="form-group">
          <label for="name">Expense Name</label>
          <input
            id="name"
            type="text"
            bind:value={name}
            placeholder="e.g., Rent, Supplies, Utilities"
            disabled={loading}
          />
        </div>

        <div class="form-row">
          <div class="form-group">
            <label for="amount">Amount (MWK)</label>
            <input
              id="amount"
              type="number"
              min="0"
              step="0.01"
              bind:value={amount}
              placeholder="0.00"
              disabled={loading}
            />
          </div>

          <div class="form-group">
            <label for="category">Category</label>
            {#if loadingCategories}
              <p class="hint">Loading categories...</p>
            {:else if !useNewCategory}
              <select
                id="category"
                value={category}
                on:change={onNewCategorySelect}
                disabled={loading}
              >
                <option value="">— Choose —</option>
                {#each categories as cat}
                  <option value={cat.name}>{cat.name} ({cat.count})</option>
                {/each}
                <option value="__new__">＋ New category…</option>
              </select>
            {:else}
              <div class="new-cat-row">
                <input
                  type="text"
                  bind:value={newCategoryName}
                  placeholder="New category name"
                  disabled={loading}
                  autofocus
                />
                <button
                  type="button"
                  class="btn-cancel-new"
                  on:click={() => {
                    useNewCategory = false;
                    newCategoryName = "";
                  }}
                  disabled={loading}
                >
                  Cancel
                </button>
              </div>
            {/if}
          </div>
        </div>

        {#if message}
          <div class="message" class:error={messageType === "error"}>
            {#if messageType === "error"}
              <AlertCircle size={16} strokeWidth={2} />
            {:else}
              <CheckCircle2 size={16} strokeWidth={2} />
            {/if}
            <span>{message}</span>
          </div>
        {/if}

        <button type="submit" class="btn btn-primary btn-block" disabled={loading}>
          {#if loading}
            <span class="spinner"></span> Saving...
          {:else}
            Save Expense
          {/if}
        </button>
      </form>
    </div>

    <!-- ── Expenses list ── -->
    <div class="card expenses-list">
      <div class="list-header">
        <h3>Expenses</h3>
        {#if !loadingList}
          <span class="list-count">{totalExpenses} record{totalExpenses === 1 ? "" : "s"}</span>
        {/if}
      </div>

      <!-- Filters -->
      <div class="filter-bar">
        <div class="search-wrap">
          <Search size={14} strokeWidth={2} class="search-icon" />
          <input
            type="text"
            placeholder="Search name or category…"
            bind:value={searchQ}
            on:input={() => applyFilter(() => {})}
            class="search-input"
          />
          {#if searchQ}
            <button
              class="search-clear"
              on:click={() => applyFilter(() => (searchQ = ""))}
              type="button"
              aria-label="Clear"
            >
              <X size={12} />
            </button>
          {/if}
        </div>

        <select
          class="category-filter"
          bind:value={selectedCategory}
          on:change={() => fetchExpenses(true)}
        >
          <option value="">All categories</option>
          {#each categories as cat}
            <option value={cat.name}>{cat.name}</option>
          {/each}
        </select>
      </div>

      <div class="date-pills">
        <button
          type="button"
          class:active={dateRange === "all"}
          on:click={() => setDateRange("all")}
        >
          All
        </button>
        <button
          type="button"
          class:active={dateRange === "today"}
          on:click={() => setDateRange("today")}
        >
          Today
        </button>
        <button
          type="button"
          class:active={dateRange === "7d"}
          on:click={() => setDateRange("7d")}
        >
          7d
        </button>
        <button
          type="button"
          class:active={dateRange === "30d"}
          on:click={() => setDateRange("30d")}
        >
          30d
        </button>
      </div>

      {#if loadingList && expenses.length === 0}
        <div class="list-loading">
          <Loader2 size={20} class="spin" />
          <span>Loading expenses…</span>
        </div>
      {:else if expenses.length === 0}
        <p class="empty-text">
          {#if searchQ || selectedCategory || dateRange !== "all"}
            No expenses match your filters.
          {:else}
            No expenses recorded yet.
          {/if}
        </p>
      {:else}
        <div class="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Amount</th>
                <th>Category</th>
                <th>Date</th>
                {#if canEdit}<th class="actions-col"></th>{/if}
              </tr>
            </thead>
            <tbody>
              {#each expenses as exp}
                <tr>
                  <td class="name-cell">{exp.name}</td>
                  <td><strong>MWK {fmt(exp.amount)}</strong></td>
                  <td>
                    <span class="cat-pill">{exp.category || "Uncategorized"}</span>
                  </td>
                  <td class="date-cell">{fmtDate(exp.created_at)}</td>
                  {#if canEdit}
                    <td class="actions-col">
                      <button
                        class="row-btn"
                        on:click={() => openEdit(exp)}
                        title="Edit"
                        type="button"
                      >
                        <Pencil size={14} strokeWidth={2} />
                      </button>
                    </td>
                  {/if}
                </tr>
              {/each}
            </tbody>
          </table>
        </div>

        <!-- Mobile cards -->
        <div class="expense-cards">
          {#each expenses as exp}
            <div class="expense-card-mobile">
              <div class="ecm-header">
                <strong>{exp.name}</strong>
                <span class="ecm-amount">MWK {fmt(exp.amount)}</span>
              </div>
              <div class="ecm-meta">
                <span class="cat-pill">{exp.category || "Uncategorized"}</span>
                <span class="ecm-date">{fmtShortDate(exp.created_at)}</span>
              </div>
              {#if canEdit}
                <div class="ecm-actions">
                  <button
                    class="row-btn"
                    on:click={() => openEdit(exp)}
                    type="button"
                  >
                    <Pencil size={14} strokeWidth={2} /> Edit
                  </button>
                </div>
              {/if}
            </div>
          {/each}
        </div>

        {#if hasMore}
          <div class="load-more-row">
            <button
              class="btn btn-secondary"
              on:click={() => fetchExpenses(false)}
              disabled={loadingList}
              type="button"
            >
              {loadingList ? "Loading…" : "Load more"}
            </button>
          </div>
        {/if}
      {/if}
    </div>
  </div>

  {#if editingExpense}
    <ExpenseEditModal
      expense={editingExpense}
      on:close={closeEdit}
      on:saved={handleEdited}
      on:deleted={handleEdited}
    />
  {/if}
</Layout>

<style>
  .page-wrapper {
    max-width: 800px;
    margin: 0 auto;
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  /* Summary strip */
  .summary-strip {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 0.5rem;
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 12px;
    padding: 0.85rem;
  }
  .sum-cell {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
    min-width: 0;
  }
  .sum-label {
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    font-weight: 600;
    color: var(--text-light, #6b7280);
  }
  .sum-cell strong {
    font-size: 1.05rem;
    font-weight: 700;
    color: var(--text, #111827);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .top-cats-card {
    background: linear-gradient(135deg, #fef2f2 0%, #ffffff 100%);
    border: 1px solid #fecaca;
    border-radius: 12px;
    padding: 0.85rem 1rem;
  }
  .tc-header {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: #991b1b;
    margin-bottom: 0.5rem;
  }
  .tc-list {
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
  }
  .tc-row {
    display: flex;
    justify-content: space-between;
    font-size: 0.85rem;
  }
  .tc-name {
    color: var(--text, #111827);
    font-weight: 500;
  }
  .tc-amount {
    color: #991b1b;
    font-weight: 600;
  }

  .card {
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 12px;
    padding: 1.25rem;
  }
  .expense-card h2 {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-top: 0;
    margin-bottom: 1rem;
    font-size: 1.1rem;
    font-weight: 600;
    color: var(--text, #111827);
  }

  .quick-add-row {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    flex-wrap: wrap;
    margin-bottom: 1rem;
    padding-bottom: 0.85rem;
    border-bottom: 1px dashed var(--border, #e5e7eb);
  }
  .qa-label {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--text-light, #6b7280);
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }
  .qa-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.2rem;
    padding: 0.35rem 0.7rem;
    border: 1px solid var(--border, #e5e7eb);
    background: var(--surface, #fff);
    border-radius: 20px;
    font-size: 0.78rem;
    font-weight: 500;
    color: var(--text, #111827);
    cursor: pointer;
    transition: all 0.15s;
  }
  .qa-chip:hover {
    border-color: var(--primary, #0f6b3e);
    color: var(--primary, #0f6b3e);
    background: #f0fdf4;
  }

  .form-group {
    margin-bottom: 1rem;
  }
  label {
    display: block;
    margin-bottom: 0.4rem;
    font-weight: 500;
    font-size: 0.9rem;
    color: var(--text, #111827);
  }
  input,
  select {
    width: 100%;
    padding: 0.65rem 0.85rem;
    font-size: 0.95rem;
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 8px;
    background: var(--surface, #fff);
    color: var(--text, #111827);
    box-sizing: border-box;
  }
  input:focus,
  select:focus {
    outline: none;
    border-color: var(--primary, #0f6b3e);
    box-shadow: 0 0 0 3px rgba(15, 107, 62, 0.1);
  }
  .form-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.75rem;
  }
  .hint {
    font-size: 0.8rem;
    color: var(--text-light, #6b7280);
    margin: 0.3rem 0 0;
  }
  .new-cat-row {
    display: flex;
    gap: 0.4rem;
  }
  .new-cat-row input {
    flex: 1;
  }
  .btn-cancel-new {
    border: 1px solid var(--border, #e5e7eb);
    background: var(--surface, #fff);
    border-radius: 8px;
    padding: 0 0.65rem;
    font-size: 0.78rem;
    color: var(--text-light, #6b7280);
    cursor: pointer;
    white-space: nowrap;
  }

  .message {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin: 1rem 0;
    padding: 0.65rem 0.85rem;
    border-radius: 8px;
    background: #dcfce7;
    color: #166534;
    font-size: 0.88rem;
  }
  .message.error {
    background: #fee2e2;
    color: #991b1b;
  }

  .btn {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.6rem 1rem;
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
    opacity: 0.55;
    cursor: not-allowed;
  }
  .btn-secondary {
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    color: var(--text, #111827);
  }
  .btn-secondary:hover:not(:disabled) {
    border-color: var(--primary, #0f6b3e);
    color: var(--primary, #0f6b3e);
  }
  .btn-block {
    width: 100%;
    justify-content: center;
    padding: 0.75rem;
  }
  .spinner {
    width: 14px;
    height: 14px;
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
  .spin {
    animation: spin 1s linear infinite;
  }

  .expenses-list h3 {
    margin: 0;
    font-size: 1rem;
    font-weight: 600;
  }
  .list-header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 0.5rem;
    margin-bottom: 1rem;
  }
  .list-count {
    font-size: 0.75rem;
    color: var(--text-light, #6b7280);
  }

  .filter-bar {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 0.6rem;
    flex-wrap: wrap;
  }
  .search-wrap {
    position: relative;
    flex: 1 1 200px;
    min-width: 0;
  }
  .search-icon {
    position: absolute;
    left: 0.7rem;
    top: 50%;
    transform: translateY(-50%);
    color: var(--text-light, #6b7280);
    pointer-events: none;
  }
  .search-input {
    padding-left: 2rem !important;
    font-size: 0.85rem !important;
    padding-top: 0.5rem !important;
    padding-bottom: 0.5rem !important;
  }
  .search-clear {
    position: absolute;
    right: 0.5rem;
    top: 50%;
    transform: translateY(-50%);
    border: none;
    background: transparent;
    color: var(--text-light, #6b7280);
    cursor: pointer;
    padding: 0.2rem;
    border-radius: 4px;
    line-height: 0;
  }
  .search-clear:hover {
    background: var(--background, #f9fafb);
    color: var(--text, #111827);
  }
  .category-filter {
    flex: 0 1 180px;
    padding: 0.5rem 0.65rem !important;
    font-size: 0.85rem !important;
  }

  .date-pills {
    display: flex;
    gap: 0.3rem;
    flex-wrap: wrap;
    margin-bottom: 0.9rem;
  }
  .date-pills button {
    padding: 0.35rem 0.75rem;
    border-radius: 7px;
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    cursor: pointer;
    font-size: 0.78rem;
    font-weight: 500;
    color: var(--text, #111827);
    transition: all 0.15s;
  }
  .date-pills button:hover {
    border-color: var(--primary, #0f6b3e);
    color: var(--primary, #0f6b3e);
  }
  .date-pills button.active {
    background: var(--primary, #0f6b3e);
    color: white;
    border-color: var(--primary, #0f6b3e);
  }

  .list-loading {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    padding: 2rem 1rem;
    color: var(--text-light, #6b7280);
    font-size: 0.9rem;
  }
  .empty-text {
    text-align: center;
    padding: 1.5rem;
    color: var(--text-light, #6b7280);
    font-size: 0.9rem;
  }

  .table-wrapper {
    overflow-x: auto;
    border-radius: 8px;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.9rem;
  }
  th,
  td {
    text-align: left;
    padding: 0.6rem 0.5rem;
    border-bottom: 1px solid var(--border, #e5e7eb);
  }
  th {
    background: var(--background, #f9fafb);
    font-weight: 600;
    color: var(--text-light, #6b7280);
    font-size: 0.78rem;
    text-transform: uppercase;
  }
  .actions-col {
    width: 32px;
    text-align: right;
  }
  .name-cell {
    max-width: 220px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .date-cell {
    font-size: 0.8rem;
    color: var(--text-light, #6b7280);
    white-space: nowrap;
  }
  .cat-pill {
    display: inline-block;
    padding: 0.15rem 0.5rem;
    border-radius: 20px;
    background: var(--background, #f9fafb);
    border: 1px solid var(--border, #e5e7eb);
    font-size: 0.72rem;
    font-weight: 500;
    color: var(--text, #111827);
  }
  .row-btn {
    background: transparent;
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 6px;
    padding: 0.3rem 0.45rem;
    cursor: pointer;
    color: var(--text-light, #6b7280);
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    font-size: 0.75rem;
  }
  .row-btn:hover {
    border-color: var(--primary, #0f6b3e);
    color: var(--primary, #0f6b3e);
  }

  .expense-cards {
    display: none;
    flex-direction: column;
    gap: 0.5rem;
  }
  .expense-card-mobile {
    background: var(--background, #f9fafb);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 8px;
    padding: 0.65rem 0.75rem;
  }
  .ecm-header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 0.5rem;
    margin-bottom: 0.35rem;
  }
  .ecm-header strong {
    font-size: 0.9rem;
    color: var(--text, #111827);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    min-width: 0;
  }
  .ecm-amount {
    font-weight: 700;
    color: var(--text, #111827);
    font-size: 0.88rem;
    white-space: nowrap;
  }
  .ecm-meta {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.4rem;
  }
  .ecm-date {
    font-size: 0.72rem;
    color: var(--text-light, #6b7280);
  }
  .ecm-actions {
    display: flex;
    justify-content: flex-end;
  }

  .load-more-row {
    display: flex;
    justify-content: center;
    padding-top: 1rem;
  }

  @media (max-width: 640px) {
    .summary-strip {
      grid-template-columns: repeat(2, 1fr);
    }
    .form-row {
      grid-template-columns: 1fr;
      gap: 0;
    }
    .card {
      padding: 1rem;
    }
    .table-wrapper {
      display: none;
    }
    .expense-cards {
      display: flex;
    }
  }

  @media (max-width: 480px) {
    .sum-cell strong {
      font-size: 0.95rem;
    }
    .filter-bar {
      flex-direction: column;
    }
    .category-filter {
      flex: 1 1 auto;
    }
  }
</style>