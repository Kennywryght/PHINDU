<script>
  import { onMount } from "svelte";
  import {
    CreditCard,
    DollarSign,
    PartyPopper,
    ChevronDown,
    ChevronRight,
    Shield,
    ShieldAlert,
    ShieldCheck,
    ShieldQuestion,
    AlertTriangle,
    CheckCircle2,
    Info,
    History,
  } from "lucide-svelte";
  import Layout from "../components/Layout.svelte";
  import PaymentHistoryModal from "../components/PaymentHistoryModal.svelte";
  import API from "../api/api";

  let debtors = [];
  let loading = true;

  // Payment modal
  let showPaymentModal = false;
  let selectedDebtor = null;
  let paymentAmount = 0;
  let paymentMethod = "cash";
  let paymentNote = "";

  // History modal
  let showHistory = false;
  let historyCustomer = null;

  // Risk expansion
  let expandedRisk = {};

  // Filters / sort
  let sortBy = "overdue"; // "overdue" | "amount"
  let filterBucket = "all"; // "all" | "overdue_7" | "overdue_14" | "never"

  const METHODS = [
    { value: "cash", label: "Cash" },
    { value: "airtel_money", label: "Airtel Money" },
    { value: "tnm_mpamba", label: "TNM Mpamba" },
    { value: "bank", label: "Bank" },
    { value: "cheque", label: "Cheque" },
    { value: "other", label: "Other" },
  ];

  onMount(fetchDebtors);

  async function fetchDebtors() {
    loading = true;
    try {
      const res = await API.get("/customers/debtors?include_risk=true");
      debtors = res.data || [];
    } catch (err) {
      console.error("Failed to fetch debtors", err);
    } finally {
      loading = false;
    }
  }

  // ── Derived view ──
  $: filtered = debtors.filter((d) => {
    if (filterBucket === "all") return true;
    if (filterBucket === "never") return d.never_paid;
    if (filterBucket === "overdue_7")
      return d.days_since_last_payment != null
        ? d.days_since_last_payment >= 7
        : d.never_paid;
    if (filterBucket === "overdue_14")
      return d.days_since_last_payment != null
        ? d.days_since_last_payment >= 14
        : d.never_paid;
    return true;
  });

  $: sorted = (() => {
    const arr = [...filtered];
    if (sortBy === "amount") {
      arr.sort((a, b) => (b.total_credit || 0) - (a.total_credit || 0));
    } else {
      // overdue first: never-paid or oldest days first
      arr.sort((a, b) => {
        const aDays = a.never_paid ? 99999 : a.days_since_last_payment || 0;
        const bDays = b.never_paid ? 99999 : b.days_since_last_payment || 0;
        return bDays - aDays;
      });
    }
    return arr;
  })();

  $: totalOwed = debtors.reduce((s, d) => s + Number(d.total_credit || 0), 0);
  $: overdue14Total = debtors
    .filter((d) =>
      d.never_paid ||
      (d.days_since_last_payment != null && d.days_since_last_payment >= 14)
    )
    .reduce((s, d) => s + Number(d.total_credit || 0), 0);
  $: neverPaidCount = debtors.filter((d) => d.never_paid).length;

  // ── Payment modal ──
  function openPaymentModal(debtor) {
    selectedDebtor = debtor;
    paymentAmount = 0;
    paymentMethod = "cash";
    paymentNote = "";
    showPaymentModal = true;
  }

  function closePaymentModal() {
    showPaymentModal = false;
    selectedDebtor = null;
    paymentAmount = 0;
    paymentNote = "";
  }

  function payFullBalance() {
    if (selectedDebtor) {
      paymentAmount = Number(selectedDebtor.total_credit || 0);
    }
  }

  $: remainingAfter =
    selectedDebtor && paymentAmount
      ? Number(selectedDebtor.total_credit || 0) - Number(paymentAmount || 0)
      : null;

  async function recordPayment() {
    if (!selectedDebtor || paymentAmount <= 0) return;
    try {
      await API.post(`/customers/${selectedDebtor.id}/record-payment`, {
        amount: Number(paymentAmount),
        method: paymentMethod,
        note: paymentNote.trim() || null,
      });
      await fetchDebtors();
      closePaymentModal();
    } catch (err) {
      alert("Payment failed: " + (err.response?.data?.detail || "Unknown error"));
    }
  }

  // ── History modal ──
  function openHistory(customer) {
    historyCustomer = customer;
    showHistory = true;
  }
  function closeHistory() {
    showHistory = false;
    historyCustomer = null;
  }

  // ── Risk helpers ──
  function toggleRisk(customerId) {
    expandedRisk = { ...expandedRisk, [customerId]: !expandedRisk[customerId] };
  }

  function riskIcon(level) {
    if (level === "low") return ShieldCheck;
    if (level === "medium") return Shield;
    if (level === "high") return ShieldAlert;
    return ShieldQuestion;
  }

  function riskClass(level) {
    return `risk-${level}`;
  }

  function overdueLabel(d) {
    if (d.never_paid) return "Never paid";
    if (d.days_since_last_payment == null) return "—";
    if (d.days_since_last_payment === 0) return "Paid today";
    if (d.days_since_last_payment === 1) return "1 day ago";
    return `${d.days_since_last_payment}d ago`;
  }

  function overdueClass(bucket) {
    switch (bucket) {
      case "critical":
        return "overdue-critical";
      case "overdue":
        return "overdue-high";
      case "warning":
        return "overdue-warning";
      case "never":
        return "overdue-never";
      default:
        return "overdue-ok";
    }
  }

  function fmt(n) {
    return Number(n || 0).toLocaleString(undefined, {
      maximumFractionDigits: 0,
    });
  }
</script>

<Layout title="Credit / Loans">
  <div class="credit-page">
    <div class="page-header">
      <h2>
        <CreditCard size={22} strokeWidth={2} />
        Outstanding Credit
      </h2>
      <p class="subtitle">Customers who owe money</p>
    </div>

    {#if loading}
      <p class="state-text">Loading...</p>
    {:else if debtors.length === 0}
      <div class="card empty-card">
        <PartyPopper size={48} strokeWidth={1.5} />
        <h3>No outstanding credit</h3>
        <p>Every customer is settled up.</p>
      </div>
    {:else}
      <!-- Summary strip -->
      <div class="summary-strip">
        <div class="sum-cell">
          <span>Total owed</span>
          <strong class="sum-danger">MWK {fmt(totalOwed)}</strong>
        </div>
        <div class="sum-cell">
          <span>Customers</span>
          <strong>{debtors.length}</strong>
        </div>
        <div class="sum-cell">
          <span>Overdue 14+ days</span>
          <strong class="sum-danger">MWK {fmt(overdue14Total)}</strong>
        </div>
        <div class="sum-cell">
          <span>Never paid</span>
          <strong>{neverPaidCount}</strong>
        </div>
      </div>

      <!-- Filters + sort -->
      <div class="filter-bar">
        <div class="filter-pills">
          <button type="button" class:active={filterBucket === "all"} on:click={() => (filterBucket = "all")}>All</button>
          <button type="button" class:active={filterBucket === "overdue_7"} on:click={() => (filterBucket = "overdue_7")}>Overdue 7+</button>
          <button type="button" class:active={filterBucket === "overdue_14"} on:click={() => (filterBucket = "overdue_14")}>Overdue 14+</button>
          <button type="button" class:active={filterBucket === "never"} on:click={() => (filterBucket = "never")}>Never paid</button>
        </div>
        <div class="sort-pills">
          <span class="sort-label">Sort:</span>
          <button type="button" class:active={sortBy === "overdue"} on:click={() => (sortBy = "overdue")}>Most overdue</button>
          <button type="button" class:active={sortBy === "amount"} on:click={() => (sortBy = "amount")}>Highest owed</button>
        </div>
      </div>

      {#if sorted.length === 0}
        <p class="no-matches">No debtors match your filters.</p>
      {:else}
        <!-- Desktop table -->
        <div class="table-wrapper desktop-only">
          <table class="debtors-table">
            <thead>
              <tr>
                <th>Customer</th>
                <th>Phone</th>
                <th>Amount Owed</th>
                <th>Last Payment</th>
                <th>Risk</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {#each sorted as debtor}
                {@const RiskIcon = debtor.risk ? riskIcon(debtor.risk.level) : null}
                <tr>
                  <td>
                    <button
                      class="debtor-name-btn"
                      on:click={() => debtor.risk && toggleRisk(debtor.id)}
                      type="button"
                      disabled={!debtor.risk}
                    >
                      {#if debtor.risk}
                        {#if expandedRisk[debtor.id]}
                          <ChevronDown size={14} />
                        {:else}
                          <ChevronRight size={14} />
                        {/if}
                      {/if}
                      <strong>{debtor.name}</strong>
                    </button>
                  </td>
                  <td>{debtor.phone || "—"}</td>
                  <td><strong class="amount">MWK {fmt(debtor.total_credit)}</strong></td>
                  <td>
                    <span class="overdue-badge {overdueClass(debtor.overdue_bucket)}">
                      {overdueLabel(debtor)}
                    </span>
                  </td>
                  <td>
                    {#if debtor.risk}
                      <span class="risk-badge {riskClass(debtor.risk.level)}">
                        <RiskIcon size={14} strokeWidth={2} />
                        {debtor.risk.label}
                      </span>
                    {:else}
                      <span class="muted">—</span>
                    {/if}
                  </td>
                  <td>
                    <div class="row-actions">
                      <button
                        class="btn btn-sm btn-secondary"
                        on:click={() => openHistory(debtor)}
                        type="button"
                        title="Payment history"
                      >
                        <History size={14} strokeWidth={2} />
                      </button>
                      <button
                        class="btn btn-sm btn-primary"
                        on:click={() => openPaymentModal(debtor)}
                        type="button"
                      >
                        <DollarSign size={14} strokeWidth={2} />
                        Record
                      </button>
                    </div>
                  </td>
                </tr>
                {#if debtor.risk && expandedRisk[debtor.id]}
                  <tr class="risk-detail-row">
                    <td colspan="6">
                      <div class="risk-detail">
                        <div class="risk-header">
                          <span class="risk-score">
                            Score: <strong>{debtor.risk.score}/100</strong>
                          </span>
                          <span class="risk-recommendation">
                            <Info size={14} /> {debtor.risk.recommendation}
                          </span>
                        </div>
                        {#if debtor.risk.warnings.length > 0}
                          <div class="risk-section">
                            <strong class="section-label">
                              <AlertTriangle size={12} /> Risk factors
                            </strong>
                            <ul class="risk-list">
                              {#each debtor.risk.warnings as warning}
                                <li class="warning-item">{warning}</li>
                              {/each}
                            </ul>
                          </div>
                        {/if}
                        {#if debtor.risk.positives.length > 0}
                          <div class="risk-section">
                            <strong class="section-label">
                              <CheckCircle2 size={12} /> Positive signals
                            </strong>
                            <ul class="risk-list">
                              {#each debtor.risk.positives as positive}
                                <li class="positive-item">{positive}</li>
                              {/each}
                            </ul>
                          </div>
                        {/if}
                        <div class="risk-factors-grid">
                          <div class="factor">
                            <span>Payments made</span>
                            <strong>{debtor.risk.factors.payment_count}</strong>
                          </div>
                          <div class="factor">
                            <span>Total sold</span>
                            <strong>MWK {fmt(debtor.risk.factors.total_sold)}</strong>
                          </div>
                          <div class="factor">
                            <span>Avg purchase</span>
                            <strong>MWK {fmt(debtor.risk.factors.avg_purchase)}</strong>
                          </div>
                          <div class="factor">
                            <span>Credit ratio</span>
                            <strong>{Math.round(debtor.risk.factors.credit_ratio * 100)}%</strong>
                          </div>
                          {#if debtor.risk.factors.avg_days_to_pay != null}
                            <div class="factor">
                              <span>Avg days to pay</span>
                              <strong>{debtor.risk.factors.avg_days_to_pay}</strong>
                            </div>
                          {/if}
                          {#if debtor.risk.factors.account_age_days != null}
                            <div class="factor">
                              <span>Account age</span>
                              <strong>{debtor.risk.factors.account_age_days}d</strong>
                            </div>
                          {/if}
                        </div>
                      </div>
                    </td>
                  </tr>
                {/if}
              {/each}
            </tbody>
          </table>
        </div>

        <!-- Mobile cards -->
        <div class="mobile-debtors">
          {#each sorted as debtor}
            {@const RiskIcon = debtor.risk ? riskIcon(debtor.risk.level) : null}
            <div class="debtor-card">
              <div class="debtor-header">
                <div class="debtor-name-block">
                  <h3>{debtor.name}</h3>
                  <div class="badge-line">
                    {#if debtor.risk}
                      <span class="risk-badge {riskClass(debtor.risk.level)}">
                        <RiskIcon size={12} strokeWidth={2} />
                        {debtor.risk.label}
                      </span>
                    {/if}
                    <span class="overdue-badge {overdueClass(debtor.overdue_bucket)}">
                      {overdueLabel(debtor)}
                    </span>
                  </div>
                </div>
                <span class="amount">MWK {fmt(debtor.total_credit)}</span>
              </div>
              <p class="phone-line">{debtor.phone || "No phone"}</p>

              {#if debtor.risk}
                <button
                  class="risk-toggle-btn"
                  on:click={() => toggleRisk(debtor.id)}
                  type="button"
                >
                  {#if expandedRisk[debtor.id]}
                    Hide risk details
                  {:else}
                    View risk details ({debtor.risk.score}/100)
                  {/if}
                </button>

                {#if expandedRisk[debtor.id]}
                  <div class="risk-detail mobile-risk-detail">
                    <div class="risk-recommendation">
                      <Info size={14} /> {debtor.risk.recommendation}
                    </div>
                    {#if debtor.risk.warnings.length > 0}
                      <ul class="risk-list">
                        {#each debtor.risk.warnings as warning}
                          <li class="warning-item">
                            <AlertTriangle size={12} /> {warning}
                          </li>
                        {/each}
                      </ul>
                    {/if}
                    {#if debtor.risk.positives.length > 0}
                      <ul class="risk-list">
                        {#each debtor.risk.positives as positive}
                          <li class="positive-item">
                            <CheckCircle2 size={12} /> {positive}
                          </li>
                        {/each}
                      </ul>
                    {/if}
                  </div>
                {/if}
              {/if}

              <div class="mobile-actions">
                <button
                  class="btn btn-secondary btn-block-sm"
                  on:click={() => openHistory(debtor)}
                  type="button"
                >
                  <History size={14} strokeWidth={2} /> History
                </button>
                <button
                  class="btn btn-primary btn-block-sm"
                  on:click={() => openPaymentModal(debtor)}
                  type="button"
                >
                  <DollarSign size={14} strokeWidth={2} /> Record
                </button>
              </div>
            </div>
          {/each}
        </div>
      {/if}
    {/if}
  </div>

  <!-- Payment modal -->
  {#if showPaymentModal && selectedDebtor}
    <div
      class="modal-overlay"
      role="dialog"
      aria-modal="true"
      tabindex="-1"
      on:click|self={closePaymentModal}
      on:keydown={(e) => e.key === "Escape" && closePaymentModal()}
    >
      <div class="modal">
        <h3>
          <DollarSign size={18} strokeWidth={2} />
          Record Payment — {selectedDebtor.name}
        </h3>
        <p class="modal-info">
          Current balance: <strong>MWK {fmt(selectedDebtor.total_credit)}</strong>
        </p>

        <div class="form-group">
          <div class="label-row">
            <label for="paymentAmt">Amount (MWK)</label>
            <button
              class="pay-full-btn"
              on:click={payFullBalance}
              type="button"
            >
              Pay full
            </button>
          </div>
          <input
            id="paymentAmt"
            type="number"
            min="0.01"
            step="0.01"
            max={selectedDebtor.total_credit}
            bind:value={paymentAmount}
          />
          {#if remainingAfter !== null && remainingAfter >= 0}
            <p class="remaining-hint">
              Remaining after: <strong>MWK {fmt(remainingAfter)}</strong>
            </p>
          {/if}
        </div>

        <div class="form-group">
          <label for="paymentMethod">Method</label>
          <select id="paymentMethod" bind:value={paymentMethod}>
            {#each METHODS as m}
              <option value={m.value}>{m.label}</option>
            {/each}
          </select>
        </div>

        <div class="form-group">
          <label for="paymentNote">Note (optional)</label>
          <input id="paymentNote" type="text" bind:value={paymentNote} placeholder="e.g. Received by son" />
        </div>

        <div class="modal-actions">
          <button class="btn btn-secondary" on:click={closePaymentModal} type="button">
            Cancel
          </button>
          <button
            class="btn btn-primary"
            on:click={recordPayment}
            disabled={!paymentAmount || paymentAmount <= 0}
            type="button"
          >
            Record Payment
          </button>
        </div>
      </div>
    </div>
  {/if}

  <!-- History modal -->
  {#if showHistory && historyCustomer}
    <PaymentHistoryModal customer={historyCustomer} on:close={closeHistory} />
  {/if}
</Layout>

<style>
  .credit-page {
    max-width: 1000px;
    margin: 0 auto;
  }
  .page-header {
    margin-bottom: 1rem;
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
  .state-text {
    text-align: center;
    padding: 2rem;
    color: var(--text-light, #6b7280);
  }
  .no-matches {
    text-align: center;
    padding: 2rem 1rem;
    color: var(--text-light, #6b7280);
    font-size: 0.9rem;
  }

  /* Summary strip */
  .summary-strip {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 0.5rem;
    margin-bottom: 0.85rem;
    padding: 0.75rem 0.85rem;
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 10px;
  }
  .sum-cell {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
    min-width: 0;
  }
  .sum-cell span {
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    font-weight: 700;
    color: var(--text-light, #6b7280);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .sum-cell strong {
    font-size: 1rem;
    font-weight: 700;
    color: var(--text, #111827);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .sum-danger {
    color: #b91c1c;
  }

  /* Filter / sort */
  .filter-bar {
    display: flex;
    justify-content: space-between;
    gap: 0.5rem;
    flex-wrap: wrap;
    margin-bottom: 0.85rem;
  }
  .filter-pills,
  .sort-pills {
    display: flex;
    gap: 0.35rem;
    flex-wrap: wrap;
    align-items: center;
  }
  .filter-pills button,
  .sort-pills button {
    padding: 0.4rem 0.75rem;
    border-radius: 7px;
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    cursor: pointer;
    font-size: 0.78rem;
    font-weight: 500;
    color: var(--text, #111827);
    transition: all 0.15s;
  }
  .filter-pills button:hover,
  .sort-pills button:hover {
    border-color: var(--primary, #0f6b3e);
    color: var(--primary, #0f6b3e);
  }
  .filter-pills button.active,
  .sort-pills button.active {
    background: var(--primary, #0f6b3e);
    color: white;
    border-color: var(--primary, #0f6b3e);
  }
  .sort-label {
    font-size: 0.72rem;
    color: var(--text-light, #6b7280);
    text-transform: uppercase;
    letter-spacing: 0.04em;
    font-weight: 700;
    margin-right: 0.2rem;
  }

  /* Table */
  .table-wrapper {
    overflow-x: auto;
    background: var(--surface, #fff);
    border-radius: 10px;
    border: 1px solid var(--border, #e5e7eb);
  }
  .debtors-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.9rem;
  }
  .debtors-table th {
    text-align: left;
    padding: 0.7rem 0.75rem;
    background: var(--background, #f9fafb);
    font-weight: 600;
    color: var(--text-light, #6b7280);
    font-size: 0.78rem;
    text-transform: uppercase;
  }
  .debtors-table td {
    padding: 0.7rem 0.75rem;
    border-top: 1px solid var(--border, #e5e7eb);
    color: var(--text, #111827);
    vertical-align: middle;
  }
  .debtor-name-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    background: none;
    border: none;
    padding: 0;
    cursor: pointer;
    color: var(--text, #111827);
    font-size: 0.9rem;
    text-align: left;
  }
  .debtor-name-btn:disabled {
    cursor: default;
  }
  .debtor-name-btn:hover:not(:disabled) {
    color: var(--primary, #0f6b3e);
  }
  .amount {
    color: #b91c1c;
    font-weight: 700;
  }
  .muted {
    color: var(--text-light, #6b7280);
  }
  .row-actions {
    display: flex;
    gap: 0.3rem;
    justify-content: flex-end;
  }

  /* Overdue badges */
  .overdue-badge {
    display: inline-block;
    font-size: 0.72rem;
    font-weight: 700;
    padding: 0.15rem 0.5rem;
    border-radius: 20px;
    white-space: nowrap;
    border: 1px solid;
  }
  .overdue-ok {
    background: rgba(22, 163, 74, 0.1);
    color: #166534;
    border-color: #86efac;
  }
  .overdue-warning {
    background: rgba(234, 179, 8, 0.12);
    color: #854d0e;
    border-color: #fde68a;
  }
  .overdue-high {
    background: rgba(234, 88, 12, 0.12);
    color: #9a3412;
    border-color: #fdba74;
  }
  .overdue-critical {
    background: rgba(220, 38, 38, 0.12);
    color: #991b1b;
    border-color: #fca5a5;
  }
  .overdue-never {
    background: rgba(107, 114, 128, 0.1);
    color: #374151;
    border-color: #d1d5db;
  }

  /* Risk badges */
  .risk-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    font-size: 0.72rem;
    font-weight: 700;
    padding: 0.2rem 0.55rem;
    border-radius: 20px;
    text-transform: uppercase;
    letter-spacing: 0.3px;
    border: 1px solid;
  }
  .risk-low {
    background: rgba(22, 163, 74, 0.1);
    color: #166534;
    border-color: #86efac;
  }
  .risk-medium {
    background: rgba(234, 179, 8, 0.12);
    color: #92400e;
    border-color: #fcd34d;
  }
  .risk-high {
    background: rgba(220, 38, 38, 0.1);
    color: #991b1b;
    border-color: #fecaca;
  }
  .risk-new {
    background: var(--background, #f9fafb);
    color: var(--text-light, #6b7280);
    border-color: var(--border, #e5e7eb);
  }

  /* Risk detail row */
  .risk-detail-row td {
    background: var(--background, #f9fafb);
    padding: 1rem;
  }
  .risk-detail {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }
  .risk-header {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem 1rem;
    align-items: center;
  }
  .risk-score {
    font-size: 0.88rem;
    color: var(--text, #111827);
  }
  .risk-recommendation {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    font-size: 0.85rem;
    color: #166534;
    font-weight: 500;
    background: rgba(22, 163, 74, 0.08);
    border: 1px solid #86efac;
    padding: 0.35rem 0.65rem;
    border-radius: 8px;
  }
  .risk-section {
    font-size: 0.85rem;
  }
  .section-label {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    margin-bottom: 0.35rem;
    color: var(--text-light, #6b7280);
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.3px;
  }
  .risk-list {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
  }
  .warning-item,
  .positive-item {
    display: flex;
    align-items: flex-start;
    gap: 0.35rem;
    font-size: 0.83rem;
    padding-left: 0.25rem;
  }
  .warning-item {
    color: #9a3412;
  }
  .positive-item {
    color: #166534;
  }
  .risk-factors-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
    gap: 0.5rem;
    padding-top: 0.5rem;
    border-top: 1px dashed var(--border, #e5e7eb);
  }
  .factor {
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
  }
  .factor span {
    font-size: 0.72rem;
    color: var(--text-light, #6b7280);
  }
  .factor strong {
    font-size: 0.88rem;
    color: var(--text, #111827);
  }

  /* Mobile */
  .mobile-debtors {
    display: none;
    flex-direction: column;
    gap: 0.65rem;
  }
  .debtor-card {
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 10px;
    padding: 1rem;
  }
  .debtor-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 0.5rem;
    margin-bottom: 0.35rem;
  }
  .debtor-name-block {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
    min-width: 0;
    flex: 1;
  }
  .debtor-header h3 {
    margin: 0;
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--text, #111827);
  }
  .badge-line {
    display: flex;
    gap: 0.3rem;
    flex-wrap: wrap;
  }
  .phone-line {
    font-size: 0.85rem;
    color: var(--text-light, #6b7280);
    margin: 0 0 0.75rem;
  }
  .risk-toggle-btn {
    width: 100%;
    padding: 0.45rem;
    background: var(--background, #f9fafb);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 6px;
    cursor: pointer;
    font-size: 0.78rem;
    color: var(--text, #111827);
    font-weight: 500;
    margin: 0.4rem 0;
  }
  .mobile-risk-detail {
    padding: 0.75rem;
    background: var(--background, #f9fafb);
    border-radius: 8px;
    margin-bottom: 0.75rem;
  }
  .mobile-actions {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.4rem;
  }
  .btn-block-sm {
    justify-content: center;
    padding: 0.5rem;
  }

  /* Empty card */
  .card {
    background: var(--surface, #fff);
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 12px;
    padding: 1.25rem;
  }
  .empty-card {
    text-align: center;
    padding: 2.5rem 1.5rem;
  }
  .empty-card h3 {
    margin: 0 0 0.4rem;
    font-size: 1.05rem;
    color: var(--text, #111827);
  }
  .empty-card p {
    color: var(--text-light, #6b7280);
    margin: 0;
    font-size: 0.9rem;
  }

  /* Buttons */
  .btn {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.5rem 0.9rem;
    border-radius: 8px;
    border: none;
    cursor: pointer;
    font-weight: 500;
    font-size: 0.85rem;
    transition: all 0.15s;
  }
  .btn:disabled {
    opacity: 0.55;
    cursor: not-allowed;
  }
  .btn-primary {
    background: var(--primary, #0f6b3e);
    color: white;
  }
  .btn-primary:hover:not(:disabled) {
    background: var(--primary-dark, #0a4f2e);
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
  .btn-sm {
    padding: 0.4rem 0.75rem;
    font-size: 0.82rem;
  }

  /* Modal */
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
    padding: 1.25rem;
    max-width: 440px;
    width: 100%;
    max-height: 90vh;
    overflow-y: auto;
  }
  .modal h3 {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-top: 0;
    margin-bottom: 0.5rem;
    font-size: 1.05rem;
    color: var(--text, #111827);
  }
  .modal-info {
    font-size: 0.85rem;
    color: var(--text-light, #6b7280);
    margin: 0 0 1rem;
  }
  .modal-info strong {
    color: var(--text, #111827);
  }
  .form-group {
    margin-bottom: 0.85rem;
  }
  .label-row {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 0.3rem;
  }
  label {
    display: block;
    font-weight: 500;
    font-size: 0.88rem;
    color: var(--text, #111827);
  }
  .pay-full-btn {
    border: 1px solid var(--primary, #0f6b3e);
    background: transparent;
    color: var(--primary, #0f6b3e);
    border-radius: 6px;
    padding: 0.15rem 0.55rem;
    font-size: 0.72rem;
    font-weight: 600;
    cursor: pointer;
  }
  .pay-full-btn:hover {
    background: var(--primary, #0f6b3e);
    color: white;
  }
  .remaining-hint {
    font-size: 0.78rem;
    color: var(--text-light, #6b7280);
    margin: 0.35rem 0 0;
  }
  .remaining-hint strong {
    color: var(--text, #111827);
  }
  input,
  select {
    width: 100%;
    padding: 0.6rem;
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 8px;
    font-size: 0.9rem;
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
  .modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: 0.6rem;
    margin-top: 1rem;
  }

  @media (max-width: 768px) {
    .desktop-only {
      display: none;
    }
    .mobile-debtors {
      display: flex;
    }
    .summary-strip {
      grid-template-columns: repeat(2, 1fr);
    }
  }
</style>