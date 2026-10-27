<script>
  import { createEventDispatcher, onMount } from "svelte";
  import { X, Printer, Trash2 } from "lucide-svelte";

  export let sale = null;
  export let items = [];
  export let change = null;
  export let amountTendered = null;
  export let shopName = "PHINDU";
  export let customerName = null;
  export let canVoid = false;
  export let alreadyVoided = false;

  const dispatch = createEventDispatcher();

  let printedAt = "";

  onMount(() => {
    printedAt = new Date().toLocaleString();
  });

  function close() {
    dispatch("close");
  }

  function print() {
    window.print();
  }

  function requestVoid() {
    dispatch("void", sale);
  }

  function handleKeydown(e) {
    if (e.key === "Escape") close();
  }

  function fmt(n) {
    return Number(n || 0).toLocaleString(undefined, {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  }
</script>

<svelte:window on:keydown={handleKeydown} />

<div class="receipt-overlay" role="dialog" aria-modal="true" tabindex="-1">
  <div class="receipt-modal">
    <div class="receipt-actions no-print">
      <h3>Sale Receipt</h3>
      <button class="close-btn" on:click={close} type="button" aria-label="Close">
        <X size={20} strokeWidth={2} />
      </button>
    </div>

    <div class="receipt" id="receipt-print-area">
      <div class="receipt-header">
        <h2>{shopName}</h2>
        <p class="receipt-meta">Sale Receipt</p>
      </div>

      <div class="receipt-info">
        <div><span>Date</span><strong>{printedAt}</strong></div>
        {#if sale?.id}
          <div>
            <span>Sale ID</span>
            <strong class="mono">{sale.id.slice(0, 8).toUpperCase()}</strong>
          </div>
        {/if}
        {#if customerName}
          <div>
            <span>Customer</span>
            <strong>{customerName}</strong>
          </div>
        {/if}
        <div>
          <span>Status</span>
          <strong class="status-{alreadyVoided ? 'voided' : (sale?.payment_status || 'paid')}">
            {#if alreadyVoided}
              Voided
            {:else if sale?.payment_status === "unpaid"}
              Credit (unpaid)
            {:else if sale?.payment_status === "partial"}
              Partial payment
            {:else}
              Paid
            {/if}
          </strong>
        </div>
      </div>

      <!-- Rebuilt items table: Qty is a ×N badge in its own centered column;
           price & total carry "MWK" so they can never be confused with qty. -->
      <table class="receipt-items">
        <thead>
          <tr>
            <th class="col-item">Item</th>
            <th class="col-qty">Qty</th>
            <th class="col-num">Price</th>
            <th class="col-num">Total</th>
          </tr>
        </thead>
        <tbody>
          {#each items as it}
            <tr>
              <td class="col-item">{it.name}</td>
              <td class="col-qty"><span class="qty-badge">×{it.qty}</span></td>
              <td class="col-num">MWK {fmt(it.selling_price)}</td>
              <td class="col-num">MWK {fmt(it.selling_price * it.qty)}</td>
            </tr>
          {/each}
        </tbody>
      </table>

      <div class="receipt-totals">
        <div class="row">
          <span>Subtotal</span>
          <strong>MWK {fmt(sale?.total_amount)}</strong>
        </div>
        {#if !alreadyVoided && sale?.payment_status && sale.payment_status !== "paid"}
          <div class="row">
            <span>Paid</span>
            <strong>MWK {fmt(sale?.amount_paid)}</strong>
          </div>
          <div class="row">
            <span>Balance</span>
            <strong>MWK {fmt((sale?.total_amount || 0) - (sale?.amount_paid || 0))}</strong>
          </div>
        {/if}
        {#if amountTendered != null && amountTendered > 0}
          <div class="row">
            <span>Cash given</span>
            <strong>MWK {fmt(amountTendered)}</strong>
          </div>
          <div class="row change">
            <span>Change</span>
            <strong>MWK {fmt(change)}</strong>
          </div>
        {/if}
      </div>

      {#if alreadyVoided && sale?.void_reason}
        <div class="voided-stamp">
          <strong>VOIDED</strong>
          <span>{sale.void_reason}</span>
        </div>
      {/if}

      <div class="receipt-footer">
        <p>Thank you for your business!</p>
        <p class="small">Powered by PHINDU</p>
      </div>
    </div>

    <div class="receipt-actions no-print">
      {#if canVoid && !alreadyVoided}
        <button class="btn btn-danger" on:click={requestVoid} type="button">
          <Trash2 size={16} strokeWidth={2} /> Void
        </button>
      {:else}
        <span></span>
      {/if}
      <div class="action-right">
        <button class="btn btn-secondary" on:click={close} type="button">Close</button>
        <button class="btn btn-primary" on:click={print} type="button">
          <Printer size={16} strokeWidth={2} /> Print
        </button>
      </div>
    </div>
  </div>
</div>

<style>
  .receipt-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1500;
    padding: 1rem;
  }

  .receipt-modal {
    background: var(--surface, #fff);
    border-radius: 12px;
    max-width: 460px;
    width: 100%;
    max-height: 92vh;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    box-shadow: 0 20px 40px -10px rgba(0, 0, 0, 0.3);
  }

  .receipt-actions {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.85rem 1rem;
    border-bottom: 1px solid var(--border, #e5e7eb);
    gap: 0.5rem;
  }
  .receipt-actions:last-child {
    border-bottom: none;
    border-top: 1px solid var(--border, #e5e7eb);
    justify-content: space-between;
  }
  .receipt-actions h3 {
    margin: 0;
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--text, #111827);
  }
  .action-right {
    display: flex;
    gap: 0.5rem;
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
  .close-btn:hover {
    background: var(--background, #f9fafb);
  }

  .receipt {
    padding: 1.25rem 1.25rem 1.5rem;
    font-family: "SF Mono", Consolas, monospace;
    font-size: 0.85rem;
    color: #111827;
    font-variant-numeric: tabular-nums;
  }

  .receipt-header {
    text-align: center;
    margin-bottom: 1rem;
    padding-bottom: 0.75rem;
    border-bottom: 2px dashed #d1d5db;
  }
  .receipt-header h2 {
    margin: 0 0 0.25rem;
    font-size: 1.1rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }
  .receipt-meta {
    margin: 0;
    font-size: 0.72rem;
    color: #6b7280;
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }

  .receipt-info {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    margin-bottom: 0.85rem;
    font-size: 0.78rem;
  }
  .receipt-info div {
    display: flex;
    justify-content: space-between;
    gap: 0.5rem;
  }
  .receipt-info span {
    color: #6b7280;
  }
  .receipt-info strong {
    text-align: right;
    font-weight: 600;
  }
  .mono {
    font-family: inherit;
  }
  .status-paid {
    color: #166534;
  }
  .status-unpaid {
    color: #b45309;
  }
  .status-partial {
    color: #b45309;
  }
  .status-voided {
    color: #991b1b;
  }

  /* ── Items table ──
     Fixed layout so columns never shift between rows.
     Qty gets its own centered column with a "×N" badge. */
  .receipt-items {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.8rem;
    margin-bottom: 0.85rem;
    table-layout: fixed;
  }
  .receipt-items th {
    text-align: left;
    font-size: 0.68rem;
    font-weight: 700;
    color: #6b7280;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    border-bottom: 1px solid #e5e7eb;
    padding: 0.35rem 0;
  }
  .col-item {
    width: 46%;
    text-align: left;
  }
  .col-qty {
    width: 12%;
    text-align: center;
  }
  .col-num {
    width: 21%;
    text-align: right;
    white-space: nowrap;
  }
  .receipt-items td {
    padding: 0.4rem 0;
    border-bottom: 1px dashed #f3f4f6;
    vertical-align: top;
    word-break: break-word;
  }
  .receipt-items td.col-qty {
    text-align: center;
  }
  .receipt-items td.col-num {
    text-align: right;
    white-space: nowrap;
  }
  .qty-badge {
    display: inline-block;
    padding: 0.05rem 0.35rem;
    background: #f3f4f6;
    color: #374151;
    border-radius: 4px;
    font-size: 0.72rem;
    font-weight: 700;
    line-height: 1.3;
  }

  .receipt-totals {
    padding-top: 0.5rem;
    border-top: 2px dashed #d1d5db;
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
    margin-bottom: 1rem;
  }
  .receipt-totals .row {
    display: flex;
    justify-content: space-between;
    font-size: 0.82rem;
  }
  .receipt-totals .row strong {
    font-weight: 700;
  }
  .receipt-totals .row.change strong {
    color: #166534;
  }

  .voided-stamp {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.15rem;
    padding: 0.6rem;
    border: 2px solid #dc2626;
    border-radius: 8px;
    margin-bottom: 1rem;
    color: #991b1b;
    text-align: center;
  }
  .voided-stamp strong {
    font-size: 1.1rem;
    letter-spacing: 0.15em;
    font-weight: 800;
  }
  .voided-stamp span {
    font-size: 0.78rem;
    font-style: italic;
  }

  .receipt-footer {
    text-align: center;
    padding-top: 0.6rem;
    border-top: 2px dashed #d1d5db;
    color: #6b7280;
  }
  .receipt-footer p {
    margin: 0.25rem 0;
    font-size: 0.78rem;
  }
  .receipt-footer .small {
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }

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
  .btn-primary {
    background: var(--primary, #0f6b3e);
    color: white;
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
    background: var(--background, #f9fafb);
  }
  .btn-danger {
    background: var(--danger, #dc2626);
    color: white;
    border: 1px solid var(--danger, #dc2626);
  }
  .btn-danger:hover {
    background: #b91c1c;
    border-color: #b91c1c;
  }

  @media print {
    .no-print {
      display: none !important;
    }
    .receipt-overlay {
      position: static;
      background: transparent;
      padding: 0;
      display: block;
    }
    .receipt-modal {
      box-shadow: none;
      border-radius: 0;
      max-width: none;
      max-height: none;
    }
    .receipt {
      padding: 0.5rem;
    }
    /* :global() is required because we genuinely need to hide the whole
       page during print — scoping would break this behavior. */
    :global(body *) {
      visibility: hidden;
    }
    #receipt-print-area,
    #receipt-print-area * {
      visibility: visible;
    }
    #receipt-print-area {
      position: absolute;
      left: 0;
      top: 0;
      width: 100%;
    }
  }
</style>