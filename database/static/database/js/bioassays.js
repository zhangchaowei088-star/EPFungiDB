let assayRows = [];
let measurementRows = [];
let strainMap = new Map();
let sampleMap = new Map();

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

function compactText(value, maxLength = 150, fallback = "-") {
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

function populateSelect(id, values, defaultLabel) {
  const select = document.getElementById(id);
  if (!(select instanceof HTMLSelectElement)) return;
  select.innerHTML = `<option value="">${escapeHtml(defaultLabel)}</option>` + values.map((value) => (
    `<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`
  )).join("");
}

function buildMappings(mapRows, sampleRows) {
  strainMap = new Map();
  sampleMap = new Map();

  mapRows.forEach((record) => {
    const row = payload(record);
    if (row.strain_id) {
      strainMap.set(row.strain_id, {
        sampleId: row.sample_id || "",
        displayName: row.display_name || row.sample_id || row.strain_id,
      });
    }
  });

  sampleRows.forEach((sample) => {
    sampleMap.set(sample.sample_id, sample);
  });
}

function assaySample(row) {
  const mapped = strainMap.get(row.strain_id) || {};
  const sample = sampleMap.get(mapped.sampleId) || {};
  return {
    sampleId: mapped.sampleId || row.sample_id || "",
    displayName: sample.full_name || mapped.displayName || row.strain_id || "-",
    strainId: row.strain_id || "",
  };
}

function assayMeasurements(assayId) {
  return measurementRows
    .map(payload)
    .filter((row) => row.assay_id === assayId);
}

function renderStats() {
  const targets = uniqueValues(assayRows.map(payload), (row) => row.target_scientific_name || row.target_name_verbatim);
  const sources = uniqueValues(assayRows.map(payload), (row) => row.source_id);
  const endpoints = uniqueValues(measurementRows.map(payload), (row) => row.endpoint);
  const container = document.getElementById("bioassay-stat-grid");
  if (!container) return;
  container.innerHTML = [
    { label: "Curated assays", value: assayRows.length, note: "source-verified condition records" },
    { label: "Endpoint measurements", value: measurementRows.length, note: endpoints.join(", ") || "mortality and time-to-death endpoints" },
    { label: "Target taxa", value: targets.length, note: targets.slice(0, 3).join(", ") || "target organisms" },
    { label: "Evidence sources", value: sources.length, note: "linked literature or source records" },
  ].map((item) => `
    <article class="evidence-stat">
      <strong>${formatNumber(item.value)}</strong>
      <span>${escapeHtml(item.label)}</span>
      <small>${escapeHtml(compactText(item.note, 90))}</small>
    </article>
  `).join("");

  const summary = document.getElementById("bioassay-summary");
  if (summary) {
    summary.textContent = `${formatNumber(assayRows.length)} curated assays with ${formatNumber(measurementRows.length)} endpoint measurements are available from the strain metadata evidence layer.`;
  }
}

function renderFilters() {
  const rows = assayRows.map(payload);
  populateSelect("bioassay-target-filter", uniqueValues(rows, (row) => row.target_scientific_name || row.target_name_verbatim), "All targets");
  populateSelect("bioassay-inoculum-filter", uniqueValues(rows, (row) => row.inoculum_type), "All inoculum types");
  populateSelect("bioassay-purpose-filter", uniqueValues(rows, (row) => row.assay_purpose), "All purposes");
}

function rowText(row, measurements) {
  return [
    row.assay_id,
    row.strain_id,
    row.target_name_verbatim,
    row.target_scientific_name,
    row.assay_purpose,
    row.assay_design,
    row.infection_route,
    row.inoculum_type,
    row.formulation,
    row.dose_value,
    row.dose_unit,
    row.source_record_locator,
    row.note,
    ...measurements.flatMap((item) => [item.endpoint, item.value, item.unit, item.time_point, item.note]),
  ].join(" ").toLowerCase();
}

function currentFilters() {
  return {
    query: String(document.getElementById("bioassay-query")?.value || "").trim().toLowerCase(),
    target: String(document.getElementById("bioassay-target-filter")?.value || ""),
    inoculum: String(document.getElementById("bioassay-inoculum-filter")?.value || ""),
    purpose: String(document.getElementById("bioassay-purpose-filter")?.value || ""),
  };
}

function assayPasses(row, measurements, filters) {
  const target = row.target_scientific_name || row.target_name_verbatim || "";
  if (filters.target && target !== filters.target) return false;
  if (filters.inoculum && row.inoculum_type !== filters.inoculum) return false;
  if (filters.purpose && row.assay_purpose !== filters.purpose) return false;
  if (filters.query && !rowText(row, measurements).includes(filters.query)) return false;
  return true;
}

function renderEndpointCell(measurements) {
  if (!measurements.length) return '<span class="evidence-muted">No endpoint extracted</span>';
  return `<div class="evidence-endpoints">${measurements.map((row) => (
    `<span><strong>${escapeHtml(row.endpoint || "endpoint")}</strong>: ${escapeHtml(row.value || "-")} ${escapeHtml(row.unit || "")} ${escapeHtml(row.time_point || "")}</span>`
  )).join("")}</div>`;
}

function renderRows() {
  const tbody = document.getElementById("bioassay-table-body");
  const count = document.getElementById("bioassay-count");
  if (!tbody) return;

  const filters = currentFilters();
  const records = assayRows
    .map(payload)
    .map((row) => ({ row, measurements: assayMeasurements(row.assay_id), sample: assaySample(row) }))
    .filter((item) => assayPasses(item.row, item.measurements, filters));

  if (count) count.textContent = formatNumber(records.length);
  if (!records.length) {
    tbody.innerHTML = '<tr class="gene-empty"><td colspan="7">No curated assay records match the current filters.</td></tr>';
    return;
  }

  tbody.innerHTML = records.map(({ row, measurements, sample }) => {
    const sampleLink = sample.sampleId ? `<a class="gene-id-link" href="/genomes/${encodeURIComponent(sample.sampleId)}/">${escapeHtml(sample.displayName)}</a>` : escapeHtml(sample.displayName);
    const dose = [row.dose_value, row.dose_unit].filter(Boolean).join(" ") || "-";
    const conditions = [
      row.temperature_c ? `${row.temperature_c} C` : "",
      row.relative_humidity_pct ? `${row.relative_humidity_pct} RH` : "",
      row.photoperiod,
      row.observation_duration,
    ].filter(Boolean).join(" · ") || "-";
    return `
      <tr>
        <td><div class="evidence-primary"><strong>${sampleLink}</strong><small>${escapeHtml(sample.strainId)}</small></div></td>
        <td><div class="evidence-primary"><strong>${escapeHtml(row.target_scientific_name || row.target_name_verbatim || "-")}</strong><small>${escapeHtml(row.target_life_stage || "")}</small></div></td>
        <td>${escapeHtml(compactText(row.assay_design || row.assay_purpose, 140))}</td>
        <td>${escapeHtml(dose)}<br><span class="evidence-muted">${escapeHtml(row.inoculum_type || "")}</span></td>
        <td>${escapeHtml(conditions)}</td>
        <td>${renderEndpointCell(measurements)}</td>
        <td><span class="evidence-chip">${escapeHtml(row.verification_status || "curated")}</span><br><span class="evidence-muted">${escapeHtml(compactText(row.source_record_locator, 120))}</span></td>
      </tr>
    `;
  }).join("");
}

function bindControls() {
  ["bioassay-query", "bioassay-target-filter", "bioassay-inoculum-filter", "bioassay-purpose-filter"].forEach((id) => {
    document.getElementById(id)?.addEventListener("input", renderRows);
    document.getElementById(id)?.addEventListener("change", renderRows);
  });
  document.getElementById("clear-bioassay-search")?.addEventListener("click", () => {
    const form = document.getElementById("bioassay-search-form");
    if (form instanceof HTMLFormElement) form.reset();
    renderRows();
  });
}

async function initBioassays() {
  const [assays, measurements, mapRows, sampleRows] = await Promise.all([
    fetchAll("/api/basic-metadata/?table_name=strain_virulence_assays&page_size=500&ordering=record_key"),
    fetchAll("/api/basic-metadata/?table_name=assay_measurements&page_size=500&ordering=record_key"),
    fetchAll("/api/basic-metadata/?table_name=sample_strain_map&page_size=500&ordering=record_key"),
    fetchAll("/api/samples/?page_size=500&ordering=full_name"),
  ]);
  assayRows = assays;
  measurementRows = measurements;
  buildMappings(mapRows, sampleRows);
  renderStats();
  renderFilters();
  renderRows();
}

document.addEventListener("DOMContentLoaded", async () => {
  initNav();
  bindControls();
  try {
    await initBioassays();
  } catch (error) {
    const summary = document.getElementById("bioassay-summary");
    const tbody = document.getElementById("bioassay-table-body");
    if (summary) summary.textContent = "Bioassay evidence could not be loaded from the local API.";
    if (tbody) tbody.innerHTML = '<tr class="gene-error"><td colspan="7">Bioassay evidence could not be loaded.</td></tr>';
  }
});
