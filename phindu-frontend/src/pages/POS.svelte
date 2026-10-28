<script>
  import { onMount, onDestroy, tick } from "svelte";
  import {
    Search,
    UserPlus,
    ShoppingCart,
    PackageX,
    CheckCircle2,
    Layers,
    ScanBarcode,
    X,
    Wallet,
    CreditCard,
    AlertTriangle,
    ChevronUp,
  } from "lucide-svelte";
  import Layout from "../components/Layout.svelte";
  import CartItem from "../components/CartItem.svelte";
  import Receipt from "../components/Receipt.svelte";
  import API from "../api/api";

  let products = [];
  let customers = [];
  let cart = [];
  let searchTerm = "";
  let loading = false;
  let productsLoading = true;

  // Cash tender / change
  let cashGiven = 0;

  // Scan input refs
  let scanInputEl;

  // Credit mode
  let isCreditSale = false;
  let selectedCustomerId = null;
  let showNewCustomerModal = false;
  let newCustomer = { name: "", phone: "", email: "", address: "" };

  // Customer autocomplete state
  let customerSearch = "";
  let customerDropdownOpen = false;
  const AUTOCOMPLETE_THRESHOLD = 30;

  // Success + receipt
  let checkoutSuccess = false;
  let pendingReceipt = null;
  let showReceipt = false;

  // Variant picker
  let showVariantPicker = false;
  let variantParent = null;
  let variantList = [];
  let loadingVariants = false;

  // Session state
  let sessionActive = true;
  let sessionChecked = false;

  // Mobile cart drawer state
  let mobileCartOpen = false;

  // Modal stack tracking
  let modalHistoryDepth = 0;

  // Toast
  let toast = { visible: false, text: "", kind: "info" };
  let toastTimer = null;

  function showToast(text, kind = "info", ms = 2200) {
    toast = { visible: true, text, kind };
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(() => (toast = { ...toast, visible: false }), ms);
  }

  async function checkSession() {
    try {
      const res = await API.get("/sessions/current");
      sessionActive = !!(res.data && res.data.id);
    } catch {
      sessionActive = true;
    } finally {
      sessionChecked = true;
    }
  }

  function requestOpenSession() {
    window.dispatchEvent(new CustomEvent("phindu:open-session"));
  }

  function pushModalHistory() {
    if (typeof window === "undefined") return;
    window.history.pushState({ posModal: true }, "");
    modalHistoryDepth += 1;
  }

  function popModalHistory() {
    if (typeof window === "undefined") return;
    if (modalHistoryDepth > 0) {
      modalHistoryDepth -= 1;
      window.history.back();
    }
  }

  function handlePopState() {
    if (showVariantPicker) {
      showVariantPicker = false;
      variantParent = null;
      variantList = [];
      modalHistoryDepth = Math.max(0, modalHistoryDepth - 1);
      return;
    }
    if (showNewCustomerModal) {
      showNewCustomerModal = false;
      modalHistoryDepth = Math.max(0, modalHistoryDepth - 1);
      return;
    }
    if (showReceipt) {
      showReceipt = false;
      pendingReceipt = null;
      checkoutSuccess = false;
      modalHistoryDepth = Math.max(0, modalHistoryDepth - 1);
      return;
    }
    if (mobileCartOpen) {
      mobileCartOpen = false;
      modalHistoryDepth = Math.max(0, modalHistoryDepth - 1);
      return;
    }
  }

  function handleBeforeUnload(e) {
    if (cart.length > 0 && !checkoutSuccess) {
      e.preventDefault();
      e.returnValue = "";
      return "";
    }
  }

  onMount(async () => {
    await checkSession();

    // Load products in ONE call. No per-product prediction fetching.
    try {
      const [productsRes, customersRes] = await Promise.all([
        API.get("/products/?leaf_only=true"),
        API.get("/customers/"),
      ]);
      products = (productsRes.data || []).filter(
        (p) => !p.archived && !p.is_deleted
      );
      customers = customersRes.data || [];
    } catch (err) {
      console.error("Failed to load POS data — falling back", err);
      try {
        const [productsRes, customersRes] = await Promise.all([
          API.get("/products/"),
          API.get("/customers/"),
        ]);
        products = (productsRes.data || []).filter(
          (p) => !p.archived && !p.is_deleted
        );
        customers = customersRes.data || [];
      } catch (err2) {
        console.error("Fallback fetch failed too", err2);
      }
    } finally {
      productsLoading = false;
    }

    window.addEventListener("popstate", handlePopState);
    window.addEventListener("beforeunload", handleBeforeUnload);

    await tick();
    if (scanInputEl) scanInputEl.focus();
  });

  onDestroy(() => {
    if (typeof window === "undefined") return;
    window.removeEventListener("popstate", handlePopState);
    window.removeEventListener("beforeunload", handleBeforeUnload);
    if (toastTimer) clearTimeout(toastTimer);
  });

  $: filteredProducts = products.filter((p) =>
    p.name.toLowerCase().includes(searchTerm.trim().toLowerCase())
  );

  $: useCustomerAutocomplete = customers.length >= AUTOCOMPLETE_THRESHOLD;

  $: filteredCustomers = useCustomerAutocomplete
    ? customers.filter((c) => {
        const q = customerSearch.trim().toLowerCase();
        if (!q) return true;
        return (
          (c.name || "").toLowerCase().includes(q) ||
          (c.phone || "").toLowerCase().includes(q)
        );
      })
    : customers;

  $: selectedCustomer = customers.find((c) => c.id === selectedCustomerId) || null;

  function selectCustomer(c) {
    selectedCustomerId = c.id;
    customerSearch = c.name;
    customerDropdownOpen = false;
  }

  function clearCustomer() {
    selectedCustomerId = null;
    customerSearch = "";
  }

  function cartQtyFor(id) {
    return cart.find((i) => i.id === id)?.qty || 0;
  }

  function addToCart(product, qty = 1) {
    if (product.stock_qty <= 0) return;

    const existing = cart.find((item) => item.id === product.id);
    const currentQty = existing?.qty || 0;
    const newQty = currentQty + qty;

    if (newQty > product.stock_qty) {
      showToast(
        `Only ${product.stock_qty} ${product.unit || "unit"} in stock`,
        "warn"
      );
      const capped = product.stock_qty;
      if (capped > currentQty) {
        cart = cart.map((i) =>
          i.id === product.id ? { ...i, qty: capped } : i
        );
      }
      return;
    }

    if (existing) {
      cart = cart.map((i) =>
        i.id === product.id ? { ...i, qty: newQty } : i
      );
    } else {
      cart = [...cart, { ...product, qty }];
    }
    if (scanInputEl) scanInputEl.focus();
  }

  function updateQty(id, qty) {
    const product = products.find((p) => p.id === id);
    const max = product?.stock_qty ?? qty;
    const clamped = Math.max(1, Math.min(qty, max));
    cart = cart.map((item) =>
      item.id === id ? { ...item, qty: clamped } : item
    );
  }

  function removeFromCart(id) {
    cart = cart.filter((item) => item.id !== id);
  }

  async function handleProductClick(product) {
    if (product.is_parent && product.variant_count > 0) {
      openVariantPicker(product);
    } else if (product.stock_qty > 0) {
      addToCart(product);
    } else {
      showToast("Out of stock", "warn");
    }
  }

  async function openVariantPicker(parent) {
    variantParent = parent;
    showVariantPicker = true;
    pushModalHistory();
    loadingVariants = true;
    try {
      const res = await API.get(`/products/${parent.id}/variants`);
      variantList = (res.data || []).filter((v) => v.stock_qty > 0);
    } catch (err) {
      console.error("Failed to load variants", err);
      variantList = [];
    } finally {
      loadingVariants = false;
    }
  }

  function selectVariant(variant) {
    const full = products.find((p) => p.id === variant.id);
    if (full) addToCart(full);
    closeVariantPicker(true);
  }

  function closeVariantPicker(viaButton = false) {
    showVariantPicker = false;
    variantParent = null;
    variantList = [];
    if (viaButton) popModalHistory();
  }

  $: total = cart.reduce(
    (sum, item) => sum + Number(item.selling_price || 0) * item.qty,
    0
  );

  $: change = Math.max(0, Number(cashGiven || 0) - total);
  $: shortBy = Math.max(0, total - Number(cashGiven || 0));
  $: cashIsEnough = !isCreditSale && Number(cashGiven || 0) >= total;
  $: cartCount = cart.reduce((n, i) => n + i.qty, 0);

  function handleScanKeydown(e) {
    if (e.key !== "Enter") return;
    const raw = (e.target.value || "").trim();
    if (!raw) return;

    const exact = products.find(
      (p) => p.name.toLowerCase() === raw.toLowerCase()
    );
    const partial = products.filter((p) =>
      p.name.toLowerCase().includes(raw.toLowerCase())
    );

    if (exact) {
      addToCart(exact);
      e.target.value = "";
    } else if (partial.length === 1) {
      addToCart(partial[0]);
      e.target.value = "";
    } else if (partial.length > 1) {
      searchTerm = raw;
      e.target.value = "";
      showToast(`${partial.length} matches — pick one`, "info");
    } else {
      showToast(`No product for scan: "${raw}"`, "warn");
      e.target.value = "";
    }
  }

  function handleSearchEnter(e) {
    if (e.key !== "Enter") return;
    const first = filteredProducts.find(
      (p) => p.stock_qty > 0 || p.is_parent
    );
    if (first) {
      addToCart(first);
      searchTerm = "";
    }
  }

  async function checkout() {
    if (cart.length === 0) return;
    if (isCreditSale && !selectedCustomerId) {
      showToast("Please select a customer for credit sale", "warn");
      return;
    }
    loading = true;
    checkoutSuccess = false;

    const saleItems = cart.map((item) => ({ id: item.id, qty: item.qty }));
    const totalAtCheckout = total;
    const tendered = isCreditSale ? 0 : Number(cashGiven || 0);

    try {
      const payload = {
        items: saleItems,
        customer_id: isCreditSale ? selectedCustomerId : null,
        payment_status: isCreditSale ? "unpaid" : "paid",
        amount_paid: isCreditSale ? 0 : totalAtCheckout,
      };

      const res = await API.post("/sales/bulk", payload);
      const saleId = res.data?.sale_id || null;

      const receiptItems = cart.map((i) => ({
        name: i.name,
        qty: i.qty,
        selling_price: i.selling_price,
      }));

      pendingReceipt = {
        sale: {
          id: saleId,
          total_amount: totalAtCheckout,
          payment_status: isCreditSale ? "unpaid" : "paid",
        },
        items: receiptItems,
        change: isCreditSale ? 0 : Math.max(0, tendered - totalAtCheckout),
        amountTendered: isCreditSale ? null : tendered || null,
      };

      cart = [];
      isCreditSale = false;
      selectedCustomerId = null;
      customerSearch = "";
      cashGiven = 0;
      checkoutSuccess = true;
      mobileCartOpen = false;

      refreshProducts();
      checkSession();

      showReceipt = true;
      pushModalHistory();
    } catch (err) {
      showToast(
        "Checkout failed: " + (err.response?.data?.detail || "Unknown error"),
        "error",
        3500
      );
    } finally {
      loading = false;
    }
  }

  async function refreshProducts() {
    try {
      const res = await API.get("/products/?leaf_only=true");
      products = (res.data || []).filter((p) => !p.archived && !p.is_deleted);
    } catch (err) {
      console.error("Silent refresh failed", err);
    }
  }

  function closeReceipt() {
    showReceipt = false;
    pendingReceipt = null;
    checkoutSuccess = false;
    popModalHistory();
    if (scanInputEl) scanInputEl.focus();
  }

  function startNewSale() {
    checkoutSuccess = false;
    if (scanInputEl) scanInputEl.focus();
  }

  async function createCustomer() {
    if (!newCustomer.name) return;
    try {
      const res = await API.post("/customers/", newCustomer);
      customers = [...customers, res.data];
      selectedCustomerId = res.data.id;
      customerSearch = res.data.name;
      showNewCustomerModal = false;
      newCustomer = { name: "", phone: "", email: "", address: "" };
      showToast("Customer added", "success");
      popModalHistory();
    } catch {
      showToast("Failed to create customer", "error");
    }
  }

  function openCustomerModal() {
    showNewCustomerModal = true;
    pushModalHistory();
  }

  function closeCustomerModal() {
    showNewCustomerModal = false;
    popModalHistory();
  }

  function quickCash(amount) {
    cashGiven = Number(cashGiven || 0) + amount;
  }

  function exactCash() {
    cashGiven = total;
  }

  function openMobileCart() {
    mobileCartOpen = true;
    pushModalHistory();
  }

  function closeMobileCart() {
    mobileCartOpen = false;
    popModalHistory();
  }
</script>

<Layout title="Point of Sale">
  <div class="pos-container">
    <div class="product-section">
      {#if sessionChecked && !sessionActive}
        <div class="session-banner" role="alert">
          <div class="session-banner-icon">
            <AlertTriangle size={20} strokeWidth={2} />
          </div>
          <div class="session-banner-body">
            <strong>No session is open</strong>
            <span>
              Sales won't be tracked in a cash drawer until you open one.
            </span>
          </div>
          <button
            type="button"
            class="session-banner-cta"
            on:click={requestOpenSession}
          >
            Open Session →
          </button>
        </div>
      {/if}

      <input
        bind:this={scanInputEl}
        class="scan-input"
        type="text"
        placeholder=""
        on:keydown={handleScanKeydown}
        autocomplete="off"
        aria-label="Barcode scanner input"
      />

      <div class="search-bar">
        <span class="search-icon-wrap">
          <ScanBarcode size={18} strokeWidth={2} />
        </span>
        <input
          type="text"
          placeholder="Scan barcode or search… (Enter to add first match)"
          bind:value={searchTerm}
          on:keydown={handleSearchEnter}
          autocomplete="off"
        />
        {#if searchTerm}
          <button
            type="button"
            class="search-clear"
            on:click={() => (searchTerm = "")}
            aria-label="Clear search"
          >
            <X size={14} strokeWidth={2} />
          </button>
        {/if}
      </div>

      {#if productsLoading}
        <div class="product-grid-skeleton">
          {#each Array(8) as _}
            <div class="skeleton-tile"></div>
          {/each}
        </div>
      {:else if filteredProducts.length === 0}
        <div class="empty-products">
          <PackageX size={44} strokeWidth={1.25} />
          <p>No products found</p>
        </div>
      {:else}
        <div class="product-grid">
          {#each filteredProducts as product}
            {@const isParentWithVariants = product.is_parent && product.variant_count > 0}
            {@const isOutOfStock = !isParentWithVariants && product.stock_qty <= 0}
            {@const inCartQty = cartQtyFor(product.id)}
            <button
              class="product-card"
              class:parent-card={isParentWithVariants}
              class:out-of-stock={isOutOfStock}
              class:in-cart={inCartQty > 0}
              on:click={() => handleProductClick(product)}
              disabled={isOutOfStock}
              type="button"
            >
              {#if inCartQty > 0}
                <span class="in-cart-badge">{inCartQty}</span>
              {/if}
              <div class="product-name">
                {#if isParentWithVariants}
                  <Layers size={12} strokeWidth={2.5} class="layer-icon" />
                {/if}
                {product.name}
              </div>
              {#if isParentWithVariants}
                <div class="product-price">{product.variant_count} variants</div>
                <div class="product-stock">Tap to choose</div>
              {:else}
                <div class="product-price">
                  MWK {product.selling_price?.toLocaleString()}
                </div>
                <div class="product-stock">
                  {#if isOutOfStock}
                    Out of stock
                  {:else}
                    Stock: {product.stock_qty}
                  {/if}
                </div>
              {/if}
            </button>
          {/each}
        </div>
      {/if}
    </div>

    <!-- Desktop cart -->
    <div class="cart-section cart-desktop">
      <div class="cart-header">
        <h2>
          <ShoppingCart size={18} strokeWidth={2} />
          Current Sale
        </h2>
        {#if cart.length > 0}
          <span class="cart-count">{cart.length} item{cart.length === 1 ? "" : "s"}</span>
        {/if}
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
      {/if}

      <div class="cart-footer">
        <div class="cart-total">
          <span>Total</span>
          <strong>MWK {total.toLocaleString()}</strong>
        </div>

        <div class="credit-section">
          <label class="credit-toggle">
            <input type="checkbox" bind:checked={isCreditSale} />
            <span>
              <CreditCard size={14} strokeWidth={2} /> Credit sale (loan)
            </span>
          </label>

          {#if isCreditSale}
            {#if useCustomerAutocomplete}
              <div class="customer-autocomplete">
                {#if selectedCustomer}
                  <div class="selected-customer">
                    <div class="selected-customer-info">
                      <strong>{selectedCustomer.name}</strong>
                      {#if selectedCustomer.phone}
                        <span class="selected-customer-phone">{selectedCustomer.phone}</span>
                      {/if}
                    </div>
                    <button
                      type="button"
                      class="selected-customer-clear"
                      on:click={clearCustomer}
                      aria-label="Clear customer"
                    >
                      <X size={14} strokeWidth={2} />
                    </button>
                  </div>
                {:else}
                  <div class="customer-search-wrap">
                    <input
                      type="text"
                      placeholder="Search customer…"
                      bind:value={customerSearch}
                      on:focus={() => (customerDropdownOpen = true)}
                      on:blur={() => setTimeout(() => (customerDropdownOpen = false), 180)}
                      autocomplete="off"
                    />
                    {#if customerDropdownOpen}
                      <div class="customer-dropdown">
                        {#if filteredCustomers.length === 0}
                          <div class="customer-empty">No matches</div>
                        {:else}
                          {#each filteredCustomers.slice(0, 20) as c}
                            <button
                              type="button"
                              class="customer-option"
                              on:click={() => selectCustomer(c)}
                            >
                              <span class="customer-opt-name">{c.name}</span>
                              {#if c.phone}
                                <span class="customer-opt-phone">{c.phone}</span>
                              {/if}
                            </button>
                          {/each}
                        {/if}
                      </div>
                    {/if}
                  </div>
                {/if}
                <button
                  class="btn btn-sm btn-outline"
                  on:click={openCustomerModal}
                  type="button"
                >
                  <UserPlus size={14} strokeWidth={2} />
                  <span>New</span>
                </button>
              </div>
            {:else}
              <div class="customer-selector">
                <select bind:value={selectedCustomerId}>
                  <option value={null}>-- Select customer --</option>
                  {#each customers as c}
                    <option value={c.id}>
                      {c.name}{c.phone ? ` (${c.phone})` : ""}
                    </option>
                  {/each}
                </select>
                <button
                  class="btn btn-sm btn-outline"
                  on:click={openCustomerModal}
                  type="button"
                >
                  <UserPlus size={14} strokeWidth={2} />
                  <span>New</span>
                </button>
              </div>
            {/if}
          {:else}
            <div class="cash-block">
              <div class="cash-label">
                <Wallet size={14} strokeWidth={2} />
                <span>Cash given</span>
              </div>
              <div class="cash-input-row">
                <input
                  type="number"
                  min="0"
                  step="100"
                  bind:value={cashGiven}
                  placeholder="0"
                />
                <button
                  class="quick-cash-btn"
                  type="button"
                  on:click={exactCash}
                  title="Exact amount"
                >
                  Exact
                </button>
              </div>
              <div class="cash-quick-btns">
                <button type="button" on:click={() => quickCash(500)}>+500</button>
                <button type="button" on:click={() => quickCash(1000)}>+1k</button>
                <button type="button" on:click={() => quickCash(2000)}>+2k</button>
                <button type="button" on:click={() => quickCash(5000)}>+5k</button>
              </div>

              {#if Number(cashGiven) > 0}
                <div class="cash-result {cashIsEnough ? 'ok' : 'short'}">
                  {#if cashIsEnough}
                    <span>Change</span>
                    <strong>MWK {change.toLocaleString()}</strong>
                  {:else}
                    <span>Short by</span>
                    <strong>MWK {shortBy.toLocaleString()}</strong>
                  {/if}
                </div>
              {/if}
            </div>
          {/if}
        </div>

        <button
          class="checkout-btn"
          class:success={checkoutSuccess}
          on:click={checkoutSuccess ? startNewSale : checkout}
          disabled={loading ||
            (cart.length === 0 && !checkoutSuccess) ||
            (Number(cashGiven) > 0 && !cashIsEnough && !isCreditSale && cart.length > 0)}
          type="button"
        >
          {#if checkoutSuccess}
            <CheckCircle2 size={18} strokeWidth={2} /> Sale completed — New Sale
          {:else if loading}
            <span class="spinner"></span> Processing…
          {:else}
            <ShoppingCart size={18} strokeWidth={2} /> Complete Sale — MWK {total.toLocaleString()}
          {/if}
        </button>

        {#if cart.length === 0 && !checkoutSuccess}
          <p class="empty-hint">Tap a product above to start a sale.</p>
        {/if}
      </div>
    </div>
  </div>

  <!-- Mobile floating "View cart" button -->
  {#if cart.length > 0 && !mobileCartOpen}
    <button
      type="button"
      class="mobile-cart-fab"
      on:click={openMobileCart}
      aria-label="View cart"
    >
      <span class="fab-icon">
        <ShoppingCart size={20} strokeWidth={2} />
        <span class="fab-badge">{cartCount}</span>
      </span>
      <span class="fab-body">
        <span class="fab-label">{cartCount} item{cartCount === 1 ? "" : "s"}</span>
        <strong>MWK {total.toLocaleString()}</strong>
      </span>
      <ChevronUp size={18} strokeWidth={2} class="fab-chevron" />
    </button>
  {/if}

  <!-- Mobile cart sheet -->
  {#if mobileCartOpen}
    <div
      class="mobile-cart-backdrop"
      role="presentation"
      on:click={closeMobileCart}
      on:keydown={(e) => e.key === "Escape" && closeMobileCart()}
    ></div>
    <div class="mobile-cart-sheet" role="dialog" aria-modal="true">
      <div class="sheet-handle-row">
        <span class="sheet-handle"></span>
      </div>
      <div class="cart-header">
        <h2>
          <ShoppingCart size={18} strokeWidth={2} />
          Current Sale
        </h2>
        <button
          class="close-btn"
          on:click={closeMobileCart}
          type="button"
          aria-label="Close cart"
        >
          <X size={20} strokeWidth={2} />
        </button>
      </div>

      {#if cart.length === 0}
        <div class="empty-cart">
          <ShoppingCart size={40} strokeWidth={1.25} />
          <p>Cart is empty</p>
        </div>
      {:else}
        <div class="cart-items mobile-cart-items">
          {#each cart as item (item.id)}
            <CartItem
              {item}
              on:update={(e) => updateQty(item.id, e.detail.qty)}
              on:remove={() => removeFromCart(item.id)}
            />
          {/each}
        </div>
      {/if}

      <div class="cart-footer">
        <div class="cart-total">
          <span>Total</span>
          <strong>MWK {total.toLocaleString()}</strong>
        </div>

        <div class="credit-section">
          <label class="credit-toggle">
            <input type="checkbox" bind:checked={isCreditSale} />
            <span>
              <CreditCard size={14} strokeWidth={2} /> Credit sale (loan)
            </span>
          </label>

          {#if isCreditSale}
            {#if useCustomerAutocomplete}
              <div class="customer-autocomplete">
                {#if selectedCustomer}
                  <div class="selected-customer">
                    <div class="selected-customer-info">
                      <strong>{selectedCustomer.name}</strong>
                      {#if selectedCustomer.phone}
                        <span class="selected-customer-phone">{selectedCustomer.phone}</span>
                      {/if}
                    </div>
                    <button
                      type="button"
                      class="selected-customer-clear"
                      on:click={clearCustomer}
                      aria-label="Clear customer"
                    >
                      <X size={14} strokeWidth={2} />
                    </button>
                  </div>
                {:else}
                  <div class="customer-search-wrap">
                    <input
                      type="text"
                      placeholder="Search customer…"
                      bind:value={customerSearch}
                      on:focus={() => (customerDropdownOpen = true)}
                      on:blur={() => setTimeout(() => (customerDropdownOpen = false), 180)}
                      autocomplete="off"
                    />
                    {#if customerDropdownOpen}
                      <div class="customer-dropdown">
                        {#if filteredCustomers.length === 0}
                          <div class="customer-empty">No matches</div>
                        {:else}
                          {#each filteredCustomers.slice(0, 20) as c}
                            <button
                              type="button"
                              class="customer-option"
                              on:click={() => selectCustomer(c)}
                            >
                              <span class="customer-opt-name">{c.name}</span>
                              {#if c.phone}
                                <span class="customer-opt-phone">{c.phone}</span>
                              {/if}
                            </button>
                          {/each}
                        {/if}
                      </div>
                    {/if}
                  </div>
                {/if}
                <button
                  class="btn btn-sm btn-outline"
                  on:click={openCustomerModal}
                  type="button"
                >
                  <UserPlus size={14} strokeWidth={2} />
                  <span>New</span>
                </button>
              </div>
            {:else}
              <div class="customer-selector">
                <select bind:value={selectedCustomerId}>
                  <option value={null}>-- Select customer --</option>
                  {#each customers as c}
                    <option value={c.id}>
                      {c.name}{c.phone ? ` (${c.phone})` : ""}
                    </option>
                  {/each}
                </select>
                <button
                  class="btn btn-sm btn-outline"
                  on:click={openCustomerModal}
                  type="button"
                >
                  <UserPlus size={14} strokeWidth={2} />
                  <span>New</span>
                </button>
              </div>
            {/if}
          {:else}
            <div class="cash-block">
              <div class="cash-label">
                <Wallet size={14} strokeWidth={2} />
                <span>Cash given</span>
              </div>
              <div class="cash-input-row">
                <input
                  type="number"
                  min="0"
                  step="100"
                  bind:value={cashGiven}
                  placeholder="0"
                />
                <button
                  class="quick-cash-btn"
                  type="button"
                  on:click={exactCash}
                  title="Exact amount"
                >
                  Exact
                </button>
              </div>
              <div class="cash-quick-btns">
                <button type="button" on:click={() => quickCash(500)}>+500</button>
                <button type="button" on:click={() => quickCash(1000)}>+1k</button>
                <button type="button" on:click={() => quickCash(2000)}>+2k</button>
                <button type="button" on:click={() => quickCash(5000)}>+5k</button>
              </div>

              {#if Number(cashGiven) > 0}
                <div class="cash-result {cashIsEnough ? 'ok' : 'short'}">
                  {#if cashIsEnough}
                    <span>Change</span>
                    <strong>MWK {change.toLocaleString()}</strong>
                  {:else}
                    <span>Short by</span>
                    <strong>MWK {shortBy.toLocaleString()}</strong>
                  {/if}
                </div>
              {/if}
            </div>
          {/if}
        </div>

        <button
          class="checkout-btn"
          class:success={checkoutSuccess}
          on:click={checkoutSuccess ? startNewSale : checkout}
          disabled={loading ||
            (cart.length === 0 && !checkoutSuccess) ||
            (Number(cashGiven) > 0 && !cashIsEnough && !isCreditSale && cart.length > 0)}
          type="button"
        >
          {#if checkoutSuccess}
            <CheckCircle2 size={18} strokeWidth={2} /> Sale completed — New Sale
          {:else if loading}
            <span class="spinner"></span> Processing…
          {:else}
            <ShoppingCart size={18} strokeWidth={2} /> Complete Sale — MWK {total.toLocaleString()}
          {/if}
        </button>
      </div>
    </div>
  {/if}

  {#if toast.visible}
    <div class="toast toast-{toast.kind}" role="status">
      {toast.text}
    </div>
  {/if}

  {#if showVariantPicker}
    <div
      class="modal-overlay"
      role="dialog"
      aria-modal="true"
      tabindex="-1"
      on:click|self={() => closeVariantPicker(true)}
      on:keydown={(e) => e.key === "Escape" && closeVariantPicker(true)}
    >
      <div class="modal">
        <h3>
          <Layers size={18} strokeWidth={2} />
          Choose {variantParent?.name} Variant
        </h3>
        {#if loadingVariants}
          <p class="picker-hint">Loading variants…</p>
        {:else if variantList.length === 0}
          <p class="picker-hint">No variants in stock. Restock first.</p>
        {:else}
          <div class="variant-options">
            {#each variantList as variant}
              <button
                class="variant-option"
                on:click={() => selectVariant(variant)}
                type="button"
              >
                <div class="variant-info">
                  <div class="variant-name">{variant.name}</div>
                  <div class="variant-meta">
                    Stock: {variant.stock_qty} {variant.unit}
                  </div>
                </div>
                <div class="variant-price">
                  MWK {variant.selling_price?.toLocaleString()}
                </div>
              </button>
            {/each}
          </div>
        {/if}
        <div class="modal-actions">
          <button
            class="btn btn-secondary"
            on:click={() => closeVariantPicker(true)}
            type="button"
          >
            Cancel
          </button>
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
      on:click|self={closeCustomerModal}
      on:keydown={(e) => e.key === "Escape" && closeCustomerModal()}
    >
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
          <button class="btn btn-secondary" on:click={closeCustomerModal} type="button">
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

  {#if showReceipt && pendingReceipt}
    <Receipt
      sale={pendingReceipt.sale}
      items={pendingReceipt.items}
      change={pendingReceipt.change}
      amountTendered={pendingReceipt.amountTendered}
      on:close={closeReceipt}
    />
  {/if}
</Layout>

<style>
  /* ── Session banner ── */
  .session-banner {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    background: linear-gradient(135deg, #fffbeb 0%, #ffffff 100%);
    border: 1px solid #fcd34d;
    border-left: 4px solid #d97706;
    border-radius: 10px;
    padding: 0.75rem 0.95rem;
    margin-bottom: 0.9rem;
    flex-wrap: wrap;
  }
  .session-banner-icon { color: #b45309; flex-shrink: 0; display: flex; align-items: center; }
  .session-banner-body {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
    font-size: 0.85rem;
  }
  .session-banner-body strong { color: #92400e; font-weight: 600; }
  .session-banner-body span { color: #78350f; font-size: 0.78rem; }
  .session-banner-cta {
    border: none;
    background: #d97706;
    color: white;
    border-radius: 8px;
    padding: 0.5rem 0.85rem;
    font-size: 0.82rem;
    font-weight: 600;
    cursor: pointer;
    white-space: nowrap;
  }
  .session-banner-cta:hover { background: #b45309; }

  .scan-input {
    position: absolute;
    left: -9999px;
    top: 0;
    width: 1px;
    height: 1px;
    opacity: 0;
    pointer-events: none;
  }

  /* ── Grid ── */
  .pos-container {
    display: grid;
    grid-template-columns: 1fr 380px;
    gap: 1.25rem;
    height: calc(100vh - var(--topbar-height, 64px) - 3rem);
    min-height: 500px;
  }

  .product-section {
    display: flex;
    flex-direction: column;
    overflow: hidden;
    min-width: 0;
    min-height: 0;
  }

  .search-bar {
    position: relative;
    margin-bottom: 1rem;
    flex-shrink: 0;
  }
  .search-icon-wrap {
    position: absolute;
    left: 1rem;
    top: 50%;
    transform: translateY(-50%);
    color: var(--text-light, #6b7280);
    pointer-events: none;
    display: inline-flex;
    align-items: center;
  }
  .search-bar input {
    width: 100%;
    padding: 0.75rem 2.5rem 0.75rem 2.75rem;
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
  .search-clear {
    position: absolute;
    right: 0.65rem;
    top: 50%;
    transform: translateY(-50%);
    border: none;
    background: transparent;
    cursor: pointer;
    color: #94a3b8;
    padding: 0.25rem;
    border-radius: 4px;
    line-height: 0;
  }
  .search-clear:hover {
    color: var(--text, #111827);
    background: var(--background, #f9fafb);
  }

  .product-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
    gap: 0.75rem;
    overflow-y: auto;
    padding-right: 0.35rem;
    overscroll-behavior: contain;
    flex: 1;
    min-height: 0;
    align-content: start;
  }

  /* Skeleton for loading state */
  .product-grid-skeleton {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
    gap: 0.75rem;
    flex: 1;
  }
  .skeleton-tile {
    min-height: 96px;
    border-radius: 10px;
    background: var(--background, #f3f4f6);
    animation: skeletonPulse 1.4s infinite;
  }
  @keyframes skeletonPulse {
    0%, 100% { opacity: 0.5; }
    50% { opacity: 0.85; }
  }

  .product-card {
    position: relative;
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
  .product-card:hover:not(:disabled) {
    border-color: var(--primary, #0f6b3e);
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.06);
    transform: translateY(-1px);
  }
  .product-card.in-cart {
    border-color: var(--primary, #0f6b3e);
    background: #f0fdf4;
  }
  .parent-card { border-left: 3px solid var(--primary, #0f6b3e); }
  .out-of-stock { opacity: 0.55; cursor: not-allowed; }

  .in-cart-badge {
    position: absolute;
    top: 0.45rem;
    right: 0.45rem;
    background: var(--primary, #0f6b3e);
    color: white;
    font-size: 0.7rem;
    font-weight: 700;
    min-width: 20px;
    height: 20px;
    border-radius: 10px;
    padding: 0 0.35rem;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    line-height: 1;
  }

  .product-name {
    font-weight: 600;
    font-size: 0.88rem;
    color: var(--text, #111827);
    line-height: 1.3;
    display: flex;
    align-items: center;
    gap: 0.3rem;
    overflow: hidden;
  }
  .layer-icon { color: var(--primary, #0f6b3e); flex-shrink: 0; }
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
    flex: 1;
  }

  /* ── Cart (desktop) ── */
  .cart-section {
    display: flex;
    flex-direction: column;
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 12px;
    padding: 1rem;
    overflow: hidden;
    min-width: 0;
    min-height: 0;
  }
  .cart-desktop { display: flex; }

  .cart-header {
    flex-shrink: 0;
    margin-bottom: 0.5rem;
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 0.5rem;
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
  .cart-count {
    font-size: 0.72rem;
    color: var(--text-light, #6b7280);
    font-weight: 500;
  }

  .cart-items {
    flex: 1 1 auto;
    overflow-y: auto;
    margin: 0.5rem 0;
    padding-right: 0.25rem;
    overscroll-behavior: contain;
    min-height: 80px;
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

  .cart-footer {
    flex-shrink: 0;
    border-top: 2px solid var(--border, #e5e7eb);
    padding-top: 0.75rem;
    margin-top: 0.25rem;
    display: flex;
    flex-direction: column;
    gap: 0.65rem;
  }

  .cart-total {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 1rem;
    color: var(--text-light, #6b7280);
  }
  .cart-total strong {
    color: var(--primary, #0f6b3e);
    font-size: 1.4rem;
    font-weight: 700;
  }
  .empty-hint {
    margin: 0;
    text-align: center;
    font-size: 0.78rem;
    color: var(--text-light, #6b7280);
    padding-top: 0.25rem;
  }

  .credit-section {
    padding: 0.6rem 0.75rem;
    background: var(--background, #f9fafb);
    border-radius: 10px;
  }
  .credit-toggle {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    cursor: pointer;
    font-size: 0.85rem;
    font-weight: 500;
    color: var(--text, #111827);
  }
  .credit-toggle input {
    width: auto;
    cursor: pointer;
    accent-color: var(--primary, #0f6b3e);
  }
  .credit-toggle span {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
  }

  .customer-selector { display: flex; gap: 0.4rem; margin-top: 0.55rem; }
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

  .customer-autocomplete {
    display: flex;
    gap: 0.4rem;
    margin-top: 0.55rem;
    align-items: flex-start;
  }
  .selected-customer {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
    padding: 0.5rem 0.65rem;
    background: #eef2ff;
    border: 1px solid #c7d2fe;
    border-radius: 8px;
    min-width: 0;
  }
  .selected-customer-info {
    display: flex;
    flex-direction: column;
    min-width: 0;
    gap: 0.1rem;
  }
  .selected-customer-info strong {
    font-size: 0.85rem;
    color: #3730a3;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .selected-customer-phone { font-size: 0.72rem; color: #4f46e5; }
  .selected-customer-clear {
    border: none;
    background: transparent;
    color: #4f46e5;
    cursor: pointer;
    padding: 0.2rem;
    border-radius: 4px;
    line-height: 0;
    flex-shrink: 0;
  }
  .selected-customer-clear:hover { background: #e0e7ff; }

  .customer-search-wrap { position: relative; flex: 1; min-width: 0; }
  .customer-search-wrap input {
    width: 100%;
    padding: 0.5rem 0.65rem;
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 8px;
    background: var(--surface, #fff);
    color: var(--text, #111827);
    font-size: 0.85rem;
    box-sizing: border-box;
  }
  .customer-search-wrap input:focus {
    outline: none;
    border-color: var(--primary, #0f6b3e);
    box-shadow: 0 0 0 3px rgba(15, 107, 62, 0.1);
  }

  .customer-dropdown {
    position: absolute;
    top: calc(100% + 4px);
    left: 0;
    right: 0;
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 8px;
    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.15);
    max-height: 220px;
    overflow-y: auto;
    z-index: 50;
  }
  .customer-option {
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
    width: 100%;
    text-align: left;
    padding: 0.5rem 0.7rem;
    border: none;
    background: transparent;
    border-bottom: 1px solid var(--border, #e5e7eb);
    cursor: pointer;
    font-size: 0.85rem;
  }
  .customer-option:last-child { border-bottom: none; }
  .customer-option:hover { background: var(--background, #f9fafb); }
  .customer-opt-name { font-weight: 500; color: var(--text, #111827); }
  .customer-opt-phone { font-size: 0.72rem; color: var(--text-light, #6b7280); }
  .customer-empty {
    padding: 0.65rem 0.7rem;
    text-align: center;
    font-size: 0.82rem;
    color: var(--text-light, #6b7280);
  }

  .cash-block { margin-top: 0.65rem; display: flex; flex-direction: column; gap: 0.4rem; }
  .cash-label {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    font-size: 0.8rem;
    font-weight: 500;
    color: var(--text-light, #6b7280);
  }
  .cash-input-row { display: flex; gap: 0.4rem; }
  .cash-input-row input {
    flex: 1;
    padding: 0.55rem 0.7rem;
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 8px;
    background: var(--surface, #fff);
    color: var(--text, #111827);
    font-size: 1rem;
    font-weight: 600;
    box-sizing: border-box;
    min-width: 0;
  }
  .cash-input-row input:focus {
    outline: none;
    border-color: var(--primary, #0f6b3e);
    box-shadow: 0 0 0 3px rgba(15, 107, 62, 0.1);
  }
  .quick-cash-btn {
    padding: 0 0.75rem;
    border: 1px solid var(--primary, #0f6b3e);
    background: transparent;
    color: var(--primary, #0f6b3e);
    border-radius: 8px;
    font-size: 0.8rem;
    font-weight: 600;
    cursor: pointer;
    white-space: nowrap;
  }
  .quick-cash-btn:hover { background: var(--primary, #0f6b3e); color: white; }

  .cash-quick-btns { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.3rem; }
  .cash-quick-btns button {
    padding: 0.4rem;
    border: 1px solid var(--border, #e5e7eb);
    background: var(--surface, #fff);
    color: var(--text, #111827);
    border-radius: 6px;
    font-size: 0.75rem;
    font-weight: 600;
    cursor: pointer;
  }
  .cash-quick-btns button:hover {
    border-color: var(--primary, #0f6b3e);
    color: var(--primary, #0f6b3e);
  }

  .cash-result {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.5rem 0.65rem;
    border-radius: 8px;
    font-size: 0.85rem;
  }
  .cash-result.ok { background: #f0fdf4; color: #166534; border: 1px solid #86efac; }
  .cash-result.short { background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; }
  .cash-result strong { font-size: 1rem; font-weight: 700; }

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
  }
  .checkout-btn:hover:not(:disabled) { background: var(--primary-dark, #0a4f2e); }
  .checkout-btn:disabled { opacity: 0.55; cursor: not-allowed; }
  .checkout-btn.success { background: #16a34a; }

  .spinner {
    width: 16px;
    height: 16px;
    border: 2px solid rgba(255, 255, 255, 0.4);
    border-top-color: white;
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  /* ── Toast ── */
  .toast {
    position: fixed;
    top: 1rem;
    left: 50%;
    transform: translateX(-50%);
    padding: 0.7rem 1rem;
    border-radius: 10px;
    font-size: 0.88rem;
    font-weight: 500;
    z-index: 2000;
    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.2);
    max-width: 90vw;
    text-align: center;
  }
  .toast-info { background: #111827; color: #fff; }
  .toast-warn { background: #fef3c7; color: #92400e; border: 1px solid #fcd34d; }
  .toast-error { background: #fee2e2; color: #991b1b; border: 1px solid #fecaca; }
  .toast-success { background: #dcfce7; color: #166534; border: 1px solid #86efac; }

  /* ── Modals ── */
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
    max-width: 500px;
    width: 100%;
    max-height: 90vh;
    overflow-y: auto;
  }
  .modal h3 {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-top: 0;
    margin-bottom: 1rem;
    font-size: 1.05rem;
    color: var(--text, #111827);
  }
  .picker-hint {
    text-align: center;
    color: var(--text-light, #6b7280);
    padding: 1.5rem;
    font-size: 0.9rem;
  }
  .variant-options { display: flex; flex-direction: column; gap: 0.5rem; margin-bottom: 1rem; }
  .variant-option {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.85rem 1rem;
    background: var(--background, #f9fafb);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 10px;
    cursor: pointer;
    text-align: left;
    transition: all 0.15s;
    width: 100%;
    gap: 1rem;
  }
  .variant-option:hover { border-color: var(--primary, #0f6b3e); background: var(--surface, #fff); }
  .variant-info { flex: 1; }
  .variant-name { font-weight: 600; font-size: 0.95rem; color: var(--text, #111827); }
  .variant-meta { font-size: 0.78rem; color: var(--text-light, #6b7280); margin-top: 0.15rem; }
  .variant-price { font-weight: 700; color: var(--primary, #0f6b3e); font-size: 0.95rem; flex-shrink: 0; }

  .form-group { margin-bottom: 0.85rem; }
  label { display: block; margin-bottom: 0.3rem; font-weight: 500; font-size: 0.88rem; color: var(--text, #111827); }
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
  .modal-actions { display: flex; justify-content: flex-end; gap: 0.6rem; margin-top: 1.25rem; }

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
  .btn-primary { background: var(--primary, #0f6b3e); color: white; }
  .btn-primary:hover:not(:disabled) { background: var(--primary-dark, #0a4f2e); }
  .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
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
  .btn-outline:hover { border-color: var(--primary, #0f6b3e); color: var(--primary, #0f6b3e); }
  .btn-sm { padding: 0.45rem 0.75rem; font-size: 0.85rem; }

  /* ── Mobile cart FAB + sheet (hidden on desktop) ── */
  .mobile-cart-fab {
    display: none;
  }
  .mobile-cart-backdrop {
    display: none;
  }
  .mobile-cart-sheet {
    display: none;
  }

  /* ── Responsive: tablet ── */
  @media (max-width: 1024px) {
    .pos-container {
      grid-template-columns: 1fr 320px;
    }
  }

  /* ── Responsive: mobile ── */
  @media (max-width: 768px) {
    /* ── SCROLL FIX ─────────────────────────────────────────────
       On mobile we no longer constrain the height of the grid,
       and we let .pos-container itself scroll. This is the key
       change that makes the POS page scrollable on tablets/phones. */
    .pos-container {
      grid-template-columns: 1fr;
      height: auto;
      min-height: auto;
      gap: 1rem;
      overflow-y: auto;
      overflow-x: hidden;
      -webkit-overflow-scrolling: touch;
      /* leave room for the floating cart button + iPhone home bar */
      padding-bottom: calc(96px + env(safe-area-inset-bottom, 0px));
    }

    /* Let the product section grow naturally; the page scrolls instead */
    .product-section {
      overflow: visible;
      min-height: auto;
    }
    .product-grid {
      max-height: none;
      overflow-y: visible;
      flex: none;
      padding-bottom: 0.5rem;
    }
    .product-grid-skeleton {
      flex: none;
    }

    /* Hide the desktop cart on mobile */
    .cart-desktop {
      display: none;
    }

    /* Floating cart button */
    .mobile-cart-fab {
      display: flex;
      position: fixed;
      bottom: calc(1rem + env(safe-area-inset-bottom, 0px));
      left: 1rem;
      right: 1rem;
      align-items: center;
      gap: 0.6rem;
      padding: 0.75rem 1rem;
      background: var(--primary, #0f6b3e);
      color: white;
      border: none;
      border-radius: 14px;
      box-shadow: 0 10px 25px -8px rgba(15, 107, 62, 0.5);
      cursor: pointer;
      z-index: 900;
      transition: transform 0.15s;
    }
    .mobile-cart-fab:hover { transform: translateY(-1px); }
    .fab-icon {
      position: relative;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 40px;
      height: 40px;
      background: rgba(255, 255, 255, 0.15);
      border-radius: 10px;
      flex-shrink: 0;
    }
    .fab-badge {
      position: absolute;
      top: -4px;
      right: -4px;
      background: #f59e0b;
      color: #111827;
      font-size: 0.7rem;
      font-weight: 800;
      min-width: 20px;
      height: 20px;
      border-radius: 10px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 0 0.35rem;
      box-shadow: 0 0 0 2px var(--primary, #0f6b3e);
    }
    .fab-body {
      flex: 1;
      text-align: left;
      display: flex;
      flex-direction: column;
      gap: 0.05rem;
    }
    .fab-label {
      font-size: 0.72rem;
      font-weight: 500;
      opacity: 0.85;
    }
    .fab-body strong {
      font-size: 1.05rem;
      font-weight: 700;
    }
    .fab-chevron { opacity: 0.85; }

    /* Mobile cart sheet */
    .mobile-cart-backdrop {
      display: block;
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.5);
      z-index: 1000;
    }
    .mobile-cart-sheet {
      display: flex;
      flex-direction: column;
      position: fixed;
      left: 0;
      right: 0;
      bottom: 0;
      max-height: 90dvh;
      background: var(--surface, #fff);
      border-radius: 20px 20px 0 0;
      padding: 0.5rem 1rem calc(1rem + env(safe-area-inset-bottom, 0px));
      z-index: 1001;
      box-shadow: 0 -8px 25px rgba(0, 0, 0, 0.2);
      animation: sheetUp 0.2s ease-out;
    }
    @keyframes sheetUp {
      from { transform: translateY(100%); }
      to { transform: translateY(0); }
    }
    .sheet-handle-row {
      display: flex;
      justify-content: center;
      padding: 0.35rem 0 0.65rem;
      flex-shrink: 0;
    }
    .sheet-handle {
      width: 40px;
      height: 4px;
      background: var(--border, #d1d5db);
      border-radius: 2px;
    }
    .close-btn {
      background: none;
      border: none;
      cursor: pointer;
      padding: 0.35rem;
      border-radius: 6px;
      color: var(--text-light, #6b7280);
      line-height: 0;
    }
    .close-btn:hover { background: var(--background, #f9fafb); }
    .mobile-cart-items {
      flex: 1 1 auto;
      overflow-y: auto;
      min-height: 100px;
      -webkit-overflow-scrolling: touch;
    }
  }

  @media (max-width: 480px) {
    .product-grid {
      grid-template-columns: repeat(2, 1fr);
      gap: 0.5rem;
    }
    .product-card {
      padding: 0.65rem;
      min-height: 84px;
    }
    .product-name { font-size: 0.8rem; }
    .product-price { font-size: 0.82rem; }
    .cart-total strong { font-size: 1.15rem; }
    .cash-quick-btns button { font-size: 0.7rem; padding: 0.35rem; }
    .session-banner { padding: 0.6rem 0.75rem; }
    .session-banner-body { font-size: 0.8rem; }
    .session-banner-cta { width: 100%; text-align: center; }
  }
</style>