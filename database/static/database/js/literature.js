let literatureRows = [];
let retrievalRows = [];

function initNav() {
  const navbar = document.getElementById("navbar");
  const menuButton = document.getElementById("menu-button");
  const navLinks = document.getElementById("nav-links");
  if (!navbar || !menuButton || !navLinks) return;
  menuButton.addEventListener("click", () => {
    const isOpen = navbar.classList.toggle("is-open");
    menuButton.setAttribute("aria-expanded", String(isOpen));
  });
  navLinks.addEventListener("click", (event) => {
    if (event.target instanceof HTMLAnchorElement) {
      navbar.classList.remove("is-open");
      menuButton.setAttribute("aria-expanded", "false");
    }
  });
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function compactText(value, maxLength = 180, fallback = "-") {
  const text = String(value || "").trim();
  if (!text) return fallback;
  return text.length > maxLength ? `${text.slice(0, maxLength - 3)}...` : text;
}

function formatNumber(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "0";
  return new Intl.NumberFormat("en-US").format(Math.round(Number(value)));
}

function normalizeApiUrl(url) {
  return url ? url.replace(window.location.origin, "") : "";
}

async function getJson(url) {
  const response = await fetch(url, { headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  return response.json();
}

async function fetchAll(url) {
  const records = [];
  let nextUrl = url;
  while (nextUrl) {
    const payload = await getJson(nextUrl);
    records.push(...(payload.results || []));
    nextUrl = normalizeApiUrl(payload.next);
  }
  return records;
}

function payload(record) {
  return record?.payload || {};
}

function uniqueValues(rows, getter) {
  return [...new Set(rows.map(getter).filter(Boolean))].sort((a, b) => a.localeCompare(b));
}

function countValues(rows, getter) {
  const counts = new Map();
  rows.forEach((row) => {
    const value = getter(row) || "unassigned";
    counts.set(value, (counts.get(value) || 0) + 1);
  });
  return [...counts.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
}

function populateSelect(id, values, defaultLabel) {
  const select = document.getElementById(id);
  if (!(select instanceof HTMLSelectElement)) return;
  select.innerHTML = `<option value="">${escapeHtml(defaultLabel)}</option>` + values.map((value) => (
    `<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`
  )).join("");
}

function renderStats() {
  const evidence = literatureRows.map(payload);
  const retrievals = retrievalRows.map(payload);
  const directAssays = evidence.filter((row) => row.evidence_scope === "direct_live_strain_insect_assay").length;
  const reviewed = evidence.filter((row) => String(row.fulltext_access_status || "").includes("reviewed")).length;
  const retrievalHits = retrievals.filter((row) => Number(row.hit_count || 0) > 0).length;
  const scopeTop = countValues(evidence, (row) => row.evidence_scope)[0];

  const container = document.getElementById("literature-stat-grid");
  if (!container) return;
  container.innerHTML = [
    { label: "Retrieval records", value: retrievalRows.length, note: "strain-level literature queries across the release" },
    { label: "Curated evidence", value: literatureRows.length, note: "manually reviewed strain-linked records" },
    { label: "Direct assay evidence", value: directAssays, note: "records scoped to live-strain insect assays" },
    { label: "Reviewed full text", value: reviewed, note: scopeTop ? `top scope: ${scopeTop[0]}` : "fulltext or public source reviewed" },
  ].map((item) => `
    <article class="evidence-stat">
      <strong>${formatNumber(item.value)}</strong>
      <span>${escapeHtml(item.label)}</span>
      <small>${escapeHtml(compactText(item.note, 90))}</small>
    </article>
  `).join("");

  const summary = document.getElementById("literature-summary");
  if (summary) {
    summary.textContent = `${formatNumber(literatureRows.length)} curated literature evidence records are available from ${formatNumber(retrievalRows.length)} strain-level retrieval records. ${formatNumber(retrievalHits)} retrievals reported at least one indexed hit.`;
  }
}

function renderFilters() {
  const rows = literatureRows.map(payload);
  populateSelect("literature-scope-filter", uniqueValues(rows, (row) => row.evidence_scope), "All scopes");
  populateSelect("literature-status-filter", uniqueValues(rows, (row) => row.exact_strain_use_status), "All statuses");
  populateSelect("literature-assay-filter", uniqueValues(rows, (row) => row.assay_extraction_status), "All extraction states");
}

function currentFilters() {
  return {
    query: String(document.getElementById("literature-query")?.value || "").trim().toLowerCase(),
    scope: String(document.getElementById("literature-scope-filter")?.value || ""),
    status: String(document.getElementById("literature-status-filter")?.value || ""),
    assay: String(document.getElementById("literature-assay-filter")?.value || ""),
  };
}

function rowText(row) {
  return [
    row.sample_id,
    row.strain_id,
    row.doi,
    row.title,
    row.evidence_scope,
    row.exact_strain_use_status,
    row.author_reported_result_summary,
    row.assay_extraction_status,
    row.linked_assay_ids,
    row.note,
  ].join(" ").toLowerCase();
}

function rowPasses(row, filters) {
  if (filters.scope && row.evidence_scope !== filters.scope) return false;
  if (filters.status && row.exact_strain_use_status !== filters.status) return false;
  if (filters.assay && row.assay_extraction_status !== filters.assay) return false;
  if (filters.query && !rowText(row).includes(filters.query)) return false;
  return true;
}

function doiLink(row) {
  if (!row.doi) return "";
  return `<a class="literature-doi" href="https://doi.org/${encodeURIComponent(row.doi)}" target="_blank" rel="noopener">${escapeHtml(row.doi)}</a>`;
}

function assayLink(row) {
  if (row.linked_assay_ids) return `<span class="evidence-chip">${escapeHtml(row.linked_assay_ids)}</span>`;
  if (row.assay_extraction_status) return `<span class="evidence-muted">${escapeHtml(row.assay_extraction_status)}</span>`;
  return '<span class="evidence-muted">-</span>';
}

function renderRows() {
  const tbody = document.getElementById("literature-table-body");
  const count = document.getElementById("literature-count");
  if (!tbody) return;

  const filters = currentFilters();
  const records = literatureRows
    .map(payload)
    .filter((row) => rowPasses(row, filters));

  if (count) count.textContent = formatNumber(records.length);
  if (!records.length) {
    tbody.innerHTML = '<tr class="gene-empty"><td colspan="6">No curated literature records match the current filters.</td></tr>';
    return;
  }

  tbody.innerHTML = records.map((row) => {
    const sample = row.sample_id ? `<a class="gene-id-link" href="/genomes/${encodeURIComponent(row.sample_id)}/">${escapeHtml(row.sample_id)}</a>` : "-";
    return `
      <tr>
        <td><div class="evidence-primary"><strong>${sample}</strong><small>${escapeHtml(row.strain_id || "")}</small></div></td>
        <td><div class="evidence-primary"><strong>${escapeHtml(compactText(row.title, 150))}</strong><small>${doiLink(row)}</small></div></td>
        <td><span class="evidence-chip">${escapeHtml(row.evidence_scope || "unassigned")}</span></td>
        <td>${escapeHtml(compactText(row.exact_strain_use_status, 120))}</td>
        <td class="evidence-summary-cell">${escapeHtml(compactText(row.author_reported_result_summary, 360))}</td>
        <td>${assayLink(row)}</td>
      </tr>
    `;
  }).join("");
}

function bindControls() {
  ["literature-query", "literature-scope-filter", "literature-status-filter", "literature-assay-filter"].forEach((id) => {
    document.getElementById(id)?.addEventListener("input", renderRows);
    document.getElementById(id)?.addEventListener("change", renderRows);
  });
  document.getElementById("clear-literature-search")?.addEventListener("click", () => {
    const form = document.getElementById("literature-search-form");
    if (form instanceof HTMLFormElement) form.reset();
    renderRows();
  });
}

async function initLiterature() {
  const [evidence, retrievals] = await Promise.all([
    fetchAll("/api/basic-metadata/?table_name=strain_literature_evidence&page_size=500&ordering=record_key"),
    fetchAll("/api/basic-metadata/?table_name=strain_literature_retrievals&page_size=500&ordering=record_key"),
  ]);
  literatureRows = evidence;
  retrievalRows = retrievals;
  renderStats();
  renderFilters();
  renderRows();
}

document.addEventListener("DOMContentLoaded", async () => {
  initNav();
  bindControls();
  try {
    await initLiterature();
  } catch (error) {
    const summary = document.getElementById("literature-summary");
    const tbody = document.getElementById("literature-table-body");
    if (summary) summary.textContent = "Literature evidence could not be loaded from the local API.";
    if (tbody) tbody.innerHTML = '<tr class="gene-error"><td colspan="6">Literature evidence could not be loaded.</td></tr>';
  }
});
