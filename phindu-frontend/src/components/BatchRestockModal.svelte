<script>
  import { createEventDispatcher, onMount, onDestroy } from "svelte";
  import { X, Upload, FileText, Check, AlertCircle, Loader2, Download } from "lucide-svelte";
  import API from "../api/api";

  const dispatch = createEventDispatcher();

  let csvText = "";
  let products = [];
  let loadingProducts = true;
  let parsing = false;
  let submitting = false;
  let error = null;
  let applyError = null;
  let preview = []; // [{row, name, quantity, cost_per_unit, notes, match, issue}]
  let applied = false;
  let applyResult = null;
  let debounceTimer = null;

  const SAMPLE_CSV = `name,quantity,cost_per_unit,notes
Sugar 1kg,30,800,From ABC supplier
Salt,50,,
Cooking Oil 1L,20,4500,`;

  onMount(async () => {
    try {
      const res = await API.get("/products/?include_archived=false");
      products = (res.data || []).filter((p) => !p.is_deleted);
    } catch (err) {
      console.error("Failed to load products", err);
      products = [];
    } finally {
      loadingProducts = false;
    }
  });

  onDestroy(() => {
    if (debounceTimer) clearTimeout(debounceTimer);
  });

  function close() {
    dispatch("close");
  }

  function handleKeydown(e) {
    if (e.key === "Escape" && !submitting) close();
  }

  function downloadSample() {
    const blob = new Blob([SAMPLE_CSV], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "phindu-restock-template.csv";
    a.click();
    URL.revokeObjectURL(url);
  }

  function normalize(s) {
    return (s || "").trim().toLowerCase();
  }

  // Simple CSV parser that tolerates quoted fields, commas inside quotes,
  // and CRLF. Returns array of arrays.
  function parseCSV(text) {
    const rows = [];
    let row = [];
    let cur = "";
    let inQuotes = false;
    for (let i = 0; i < text.length; i++) {
      const ch = text[i];
      if (inQuotes) {
        if (ch === '"' && text[i + 1] === '"') {
          cur += '"';
          i++;
        } else if (ch === '"') {
          inQuotes = false;
        } else {
          cur += ch;
        }
      } else {
        if (ch === '"') {
          inQuotes = true;
        } else if (ch === ",") {
          row.push(cur);
          cur = "";
        } else if (ch === "\n" || ch === "\r") {
          if (cur.length > 0 || row.length > 0) {
            row.push(cur);
            rows.push(row);
          }
          cur = "";
          row = [];
          if (ch === "\r" && text[i + 1] === "\n") i++;
        } else {
          cur += ch;
        }
      }
    }
    if (cur.length > 0 || row.length > 0) {
      row.push(cur);
      rows.push(row);
    }
    return rows.filter((r) => r.some((c) => (c || "").trim().length > 0));
  }

  function buildPreview() {
    parsing = true;
    error = null;
    preview = [];
    try {
      const rows = parseCSV(csvText);
      if (rows.length === 0) {
        error = "CSV is empty";
        return;
      }

      const header = rows[0].map((c) => normalize(c));
      const nameIdx = header.findIndex((h) => h === "name" || h === "product" || h === "product name");
      const qtyIdx = header.findIndex(
        (h) => h === "quantity" || h === "qty" || h === "units" || h === "amount"
      );
      const costIdx = header.findIndex(
        (h) => h === "cost_per_unit" || h === "cost" || h === "unit_cost" || h === "price"
      );
      const notesIdx = header.findIndex((h) => h === "notes" || h === "note" || h === "comment");

      if (nameIdx === -1) {
        error = "Missing required column: name";
        return;
      }
      if (qtyIdx === -1) {
        error = "Missing required column: quantity";
        return;
      }

      // Build lookup: by normalized name → product (or products array for duplicates)
      const byName = {};
      products.forEach((p) => {
        const k = normalize(p.name);
        if (!byName[k]) byName[k] = [];
        byName[k].push(p);
      });

      const newPreview = [];
      for (let r = 1; r < rows.length; r++) {
        const cells = rows[r];
        const rawName = (cells[nameIdx] || "").trim();
        const rawQty = (cells[qtyIdx] || "").trim();
        const rawCost = costIdx >= 0 ? (cells[costIdx] || "").trim() : "";
        const rawNotes = notesIdx >= 0 ? (cells[notesIdx] || "").trim() : "";

        if (!rawName) continue;

        const qty = parseFloat(rawQty);
        const cost = rawCost === "" ? null : parseFloat(rawCost);

        const issue = [];
        if (isNaN(qty) || qty <= 0) issue.push("quantity must be > 0");
        if (cost !== null && (isNaN(cost) || cost < 0)) issue.push("cost_per_unit invalid");

        const candidates = byName[normalize(rawName)] || [];
        let match = null;
        if (candidates.length === 1) {
          match = candidates[0];
        } else if (candidates.length > 1) {
          issue.push("multiple products with this name — restock manually");
        } else {
          // Fuzzy: try startsWith / includes
          const q = normalize(rawName);
          const fuzzy = products.filter((p) => normalize(p.name).includes(q) || q.includes(normalize(p.name)));
          if (fuzzy.length === 1) {
            match = fuzzy[0];
          } else {
            issue.push("no match found");
          }
        }

        // Refuse parents with variants
        if (match && !match.parent_id && match.is_parent) {
          issue.push("parent product — restock its variants");
        }
        if (match && match.is_deleted) {
          issue.push("product is soft-deleted");
        }
        if (match && match.archived) {
          issue.push("product is archived");
        }

        newPreview.push({
          rowNumber: r + 1,
          name: rawName,
          quantity: qty,
          cost_per_unit: cost,
          notes: rawNotes,
          match,
          issue,
        });
      }

      if (newPreview.length === 0) {
        error = "No data rows found";
      }
      preview = newPreview;
    } catch (err) {
      error = "Could not parse CSV: " + (err.message || err);
    } finally {
      parsing = false;
    }
  }

  $: if (csvText.trim()) {
    if (debounceTimer) clearTimeout(debounceTimer);
    debounceTimer = setTimeout(buildPreview, 250);
  } else {
    preview = [];
    error = null;
  }

  function onFileChange(e) {
    const f = e.target.files?.[0];
    if (!f) return;
    const reader = new FileReader();
    reader.onload = () => {
      csvText = String(reader.result || "");
    };
    reader.readAsText(f);
  }

  $: validRows = preview.filter((r) => r.match && r.issue.length === 0);
  $: hasIssues = preview.some((r) => r.issue.length > 0);
  $: canApply = validRows.length > 0 && !submitting;

  async function apply() {
    if (!canApply) return;
    submitting = true;
    applyError = null;
    try {
      const payload = {
        items: validRows.map((r) => ({
          product_id: r.match.id,
          quantity: r.quantity,
          cost_per_unit: r.cost_per_unit,
          notes: r.notes || "Batch restock",
        })),
      };
      const res = await API.post("/products/batch-restock", payload);
      applyResult = res.data;
      applied = true;
      dispatch("saved", res.data);
    } catch (err) {
      applyError = err.response?.data?.detail || "Batch restock failed";
    } finally {
      submitting = false;
    }
  }

  function reset() {
    csvText = "";
    preview = [];
    error = null;
    applyError = null;
    applied = false;
    applyResult = null;
  }
</script>

<svelte:window on:keydown={handleKeydown} />

<div class="modal-overlay" role="dialog" aria-modal="true" tabindex="-1">
  <div class="modal">
    <div class="modal-header">
      <div>
        <h2>Batch Restock</h2>
        <p class="subtitle">Paste a CSV or upload a file to restock multiple products at once</p>
      </div>
      <button class="close-btn" on:click={close} type="button" aria-label="Close">
        <X size={20} strokeWidth={2} />
      </button>
    </div>

    {#if applied && applyResult}
      <div class="success-box">
        <Check size={20} strokeWidth={2} />
        <div>
          <strong>{applyResult.items.length} product(s) restocked</strong>
          <ul class="applied-list">
            {#each applyResult.items as item}
              <li>
                {item.product_name}: +{item.quantity_added} → stock {item.new_stock}
              </li>
            {/each}
          </ul>
        </div>
      </div>
      <div class="modal-actions">
        <button class="btn btn-secondary" on:click={reset} type="button">Restock More</button>
        <button class="btn btn-primary" on:click={close} type="button">Done</button>
      </div>
    {:else}
      <div class="toolbar">
        <label class="upload-btn">
          <Upload size={14} strokeWidth={2} />
          <span>Upload CSV</span>
          <input type="file" accept=".csv,text/csv" on:change={onFileChange} />
        </label>
        <button type="button" class="upload-btn" on:click={downloadSample}>
          <Download size={14} strokeWidth={2} />
          <span>Template</span>
        </button>
      </div>

      <div class="form-group">
        <label for="csv-input">
          Paste CSV <span class="hint-inline">Columns: name, quantity, cost_per_unit?, notes?</span>
        </label>
        <textarea
          id="csv-input"
          bind:value={csvText}
          rows="6"
          placeholder={SAMPLE_CSV}
          spellcheck="false"
        ></textarea>
      </div>

      {#if loadingProducts}
        <p class="hint"><Loader2 size={14} class="spin" /> Loading products…</p>
      {/if}

      {#if error}
        <div class="error-box">
          <AlertCircle size={14} /> {error}
        </div>
      {/if}

      {#if parsing}
        <p class="hint"><Loader2 size={14} class="spin" /> Parsing…</p>
      {/if}

      {#if preview.length > 0 && !parsing}
        <div class="preview-wrap">
          <table class="preview-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Qty</th>
                <th>Cost</th>
                <th>Matched</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {#each preview as row}
                <tr class:invalid={row.issue.length > 0}>
                  <td>{row.name}</td>
                  <td>{row.quantity || "—"}</td>
                  <td>{row.cost_per_unit ?? "—"}</td>
                  <td>{row.match ? row.match.name : "—"}</td>
                  <td>
                    {#if row.issue.length > 0}
                      <span class="status-bad">{row.issue.join(", ")}</span>
                    {:else}
                      <span class="status-ok">✓ Will restock</span>
                    {/if}
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>

        {#if hasIssues}
          <p class="hint">
            <FileText size={13} /> Rows with issues will be skipped. Only valid rows are applied.
          </p>
        {/if}
      {/if}

      {#if applyError}
        <div class="error-box">
          <AlertCircle size={14} /> {applyError}
        </div>
      {/if}

      <div class="modal-actions">
        <button class="btn btn-secondary" on:click={close} type="button" disabled={submitting}>
          Cancel
        </button>
        <button
          class="btn btn-primary"
          on:click={apply}
          type="button"
          disabled={!canApply}
        >
          {#if submitting}
            <Loader2 size={14} class="spin" /> Applying…
          {:else}
            Apply {validRows.length} Row{validRows.length === 1 ? "" : "s"}
          {/if}
        </button>
      </div>
    {/if}
  </div>
</div>

<style>
  .modal-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1300;
    padding: 1rem;
  }

  .modal {
    background: var(--surface, #fff);
    border-radius: 12px;
    padding: 1.5rem;
    max-width: 720px;
    width: 100%;
    max-height: 92vh;
    overflow-y: auto;
    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.2);
  }

  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 1rem;
    gap: 0.5rem;
  }
  .modal-header h2 {
    margin: 0;
    font-size: 1.15rem;
    font-weight: 700;
    color: var(--text, #111827);
  }
  .subtitle {
    margin: 0.2rem 0 0;
    font-size: 0.82rem;
    color: var(--text-light, #6b7280);
  }
  .close-btn {
    background: none;
    border: none;
    cursor: pointer;
    padding: 0.35rem;
    border-radius: 6px;
    color: var(--text-light, #6b7280);
    line-height: 0;
    flex-shrink: 0;
  }
  .close-btn:hover {
    background: var(--background, #f9fafb);
  }

  .toolbar {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 0.85rem;
    flex-wrap: wrap;
  }
  .upload-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.5rem 0.9rem;
    border: 1px solid var(--border, #e5e7eb);
    background: var(--surface, #fff);
    color: var(--text, #111827);
    border-radius: 8px;
    font-size: 0.85rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.15s;
  }
  .upload-btn:hover {
    border-color: var(--primary, #0f6b3e);
    color: var(--primary, #0f6b3e);
  }
  .upload-btn input[type="file"] {
    display: none;
  }

  .form-group {
    margin-bottom: 0.85rem;
  }
  label {
    display: block;
    margin-bottom: 0.3rem;
    font-weight: 500;
    font-size: 0.88rem;
    color: var(--text, #111827);
  }
  .hint-inline {
    font-weight: 400;
    color: var(--text-light, #6b7280);
    font-size: 0.78rem;
  }
  textarea {
    width: 100%;
    padding: 0.65rem 0.8rem;
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 8px;
    font-family: "SF Mono", Consolas, monospace;
    font-size: 0.82rem;
    background: var(--surface, #fff);
    color: var(--text, #111827);
    box-sizing: border-box;
    resize: vertical;
    line-height: 1.4;
  }
  textarea:focus {
    outline: none;
    border-color: var(--primary, #0f6b3e);
    box-shadow: 0 0 0 3px rgba(15, 107, 62, 0.1);
  }

  .hint {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    font-size: 0.8rem;
    color: var(--text-light, #6b7280);
    margin: 0.4rem 0;
  }

  .error-box {
    display: flex;
    align-items: flex-start;
    gap: 0.4rem;
    background: #fee2e2;
    color: #991b1b;
    padding: 0.65rem 0.85rem;
    border-radius: 8px;
    font-size: 0.85rem;
    margin-bottom: 0.75rem;
  }

  .success-box {
    display: flex;
    align-items: flex-start;
    gap: 0.6rem;
    background: #f0fdf4;
    color: #166534;
    padding: 0.9rem 1rem;
    border-radius: 10px;
    border: 1px solid #86efac;
    margin-bottom: 1rem;
    font-size: 0.88rem;
  }
  .success-box strong {
    display: block;
    margin-bottom: 0.35rem;
    font-weight: 700;
  }
  .applied-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
    font-size: 0.82rem;
    color: #166534;
  }

  .preview-wrap {
    overflow-x: auto;
    border: 1px solid var(--border, #e5e7eb);
    border-radius: 8px;
    margin-bottom: 0.6rem;
    max-height: 260px;
    overflow-y: auto;
  }
  .preview-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.82rem;
  }
  .preview-table th {
    text-align: left;
    padding: 0.5rem 0.65rem;
    background: var(--background, #f9fafb);
    font-weight: 600;
    color: var(--text-light, #6b7280);
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    white-space: nowrap;
    position: sticky;
    top: 0;
  }
  .preview-table td {
    padding: 0.45rem 0.65rem;
    border-top: 1px solid var(--border, #e5e7eb);
    color: var(--text, #111827);
  }
  .preview-table tr.invalid {
    background: #fef2f2;
  }
  .status-ok {
    color: #166534;
    font-weight: 600;
  }
  .status-bad {
    color: #b91c1c;
    font-size: 0.75rem;
  }

  .modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: 0.6rem;
    margin-top: 1rem;
  }

  .btn {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
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
    background: var(--background, #f9fafb);
  }

  .spin {
    animation: spin 1s linear infinite;
  }
  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  @media (max-width: 640px) {
    .modal-overlay {
      padding: 0.5rem;
    }
    .modal {
      padding: 1rem;
      max-height: 95vh;
    }
    .modal-actions {
      flex-direction: column-reverse;
    }
    .modal-actions .btn {
      width: 100%;
      justify-content: center;
    }
    .preview-table {
      font-size: 0.75rem;
    }
    .preview-table th,
    .preview-table td {
      padding: 0.35rem 0.45rem;
    }
  }
</style>