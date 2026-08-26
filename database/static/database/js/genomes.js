const state = {
  records: [],
  filtered: [],
  page: 1,
  pageSize: 20,
};

const groupColors = ["#9be15d", "#62c9a7", "#76b852", "#b7e57d", "#4aa66f", "#a6d96a"];

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

function formatNumber(value) {
  if (value === null || value === undefined || value === "") return "NA";
  return new Intl.NumberFormat("en-US").format(Math.round(Number(value)));
}

function formatDecimal(value, digits = 1) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "NA";
  return Number(value).toFixed(digits);
}

function formatMb(value) {
  if (!value) return "NA";
  return `${formatDecimal(Number(value) / 1000000, 1)} Mb`;
}

function formatKb(value) {
  if (!value) return "NA";
  return `${formatDecimal(Number(value) / 1000, 0)} kb`;
}

function average(records, field) {
  const values = records.map((record) => Number(record[field])).filter((value) => Number.isFinite(value) && value > 0);
  if (!values.length) return null;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function sum(records, field) {
  return records.reduce((total, record) => total + (Number(record[field]) || 0), 0);
}

function groupByCount(records, field) {
  const counts = new Map();
  records.forEach((record) => {
    const key = record[field] || "Unassigned";
    counts.set(key, (counts.get(key) || 0) + 1);
  });
  return Array.from(counts, ([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count || a.name.localeCompare(b.name));
}

async function getJson(url) {
  const response = await fetch(url, { headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  return response.json();
}

async function fetchAllSamples() {
  let url = "/api/samples/?page_size=500";
  const records = [];

  while (url) {
    const payload = await getJson(url);
    records.push(...(payload.results || []));
    url = payload.next ? payload.next.replace(window.location.origin, "") : "";
  }

  return records;
}

function populateSelect(id, values) {
  const select = document.getElementById(id);
  if (!(select instanceof HTMLSelectElement)) return;
  const first = select.options[0]?.outerHTML || "";
  select.innerHTML = first + values
    .filter(Boolean)
    .sort((a, b) => a.localeCompare(b))
    .map((value) => `<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`)
    .join("");
}

function populateFilters(records) {
  populateSelect("lineage-filter", Array.from(new Set(records.map((record) => record.order_group))));
  populateSelect("family-filter", Array.from(new Set(records.map((record) => record.family))));
  populateSelect("genus-filter", Array.from(new Set(records.map((record) => record.genus))));
}

function animateTextNumber(node, target, formatter, duration = 900) {
  const start = performance.now();
  const step = (now) => {
    const progress = Math.min((now - start) / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    node.textContent = formatter(target * eased);
    if (progress < 1) requestAnimationFrame(step);
    else node.textContent = formatter(target);
  };
  requestAnimationFrame(step);
}

function updateMetrics(records) {
  const metrics = document.getElementById("genome-metrics");
  if (!metrics) return;

  const ready = records.filter((record) => record.ready_full_analysis).length;
  const avgGenomeMb = (average(records, "genome_size") || 0) / 1000000;
  const avgN50Kb = (average(records, "n50") || 0) / 1000;
  const avgBusco = average(records, "busco_complete_pct") || 0;
  const totalGenes = sum(records, "gene_count");
  const totalProteins = sum(records, "protein_count");

  const items = [
    { value: records.length, label: "Assembled genomes", note: "sample-level records", format: (value) => formatNumber(value) },
    { value: ready, label: "Full-analysis genomes", note: `${formatDecimal((ready / Math.max(1, records.length)) * 100, 1)}% of records`, format: (value) => formatNumber(value) },
    { value: avgGenomeMb, label: "Mean genome size", note: "assembled genome length", format: (value) => `${formatDecimal(value, 1)} Mb` },
    { value: avgBusco, label: "Mean BUSCO complete", note: `mean N50 ${formatDecimal(avgN50Kb, 0)} kb`, format: (value) => `${formatDecimal(value, 1)}%` },
    { value: totalGenes, label: "Gene records", note: "summed across genomes", format: (value) => formatNumber(value) },
    { value: totalProteins, label: "Protein records", note: "summed across genomes", format: (value) => formatNumber(value) },
  ];

  metrics.innerHTML = items.map((item, index) => `
    <article class="genome-metric">
      <strong data-metric-index="${index}">0</strong>
      <span>${escapeHtml(item.label)}</span>
      <small>${escapeHtml(item.note)}</small>
    </article>
  `).join("");

  items.forEach((item, index) => {
    const node = metrics.querySelector(`[data-metric-index="${index}"]`);
    if (node) animateTextNumber(node, item.value, item.format);
  });
}

function updateLineageBar(records) {
  const container = document.getElementById("lineage-bar");
  if (!container) return;

  const groups = groupByCount(records, "order_group");
  const total = records.length || 1;
  const segments = groups.map((group, index) => {
    const color = groupColors[index % groupColors.length];
    const pct = (group.count / total) * 100;
    return `
      <div class="lineage-segment" style="width:${pct}%;--segment:${color}">
        <strong>${escapeHtml(group.name)}</strong>
        <span>${formatNumber(group.count)} · ${formatDecimal(pct, 1)}%</span>
      </div>
    `;
  }).join("");

  const keys = groups.map((group, index) => `
    <span style="--segment:${groupColors[index % groupColors.length]}"><i></i>${escapeHtml(group.name)} ${formatNumber(group.count)}</span>
  `).join("");

  container.innerHTML = `<div class="lineage-stack">${segments}</div><div class="lineage-key">${keys}</div>`;
}

function getFilters() {
  return {
    search: document.getElementById("genome-search")?.value.trim().toLowerCase() || "",
    lineage: document.getElementById("lineage-filter")?.value || "",
    family: document.getElementById("family-filter")?.value || "",
    genus: document.getElementById("genus-filter")?.value || "",
    ready: document.getElementById("ready-filter")?.value || "",
    sort: document.getElementById("sort-select")?.value || "species:asc",
  };
}

function recordMatches(record, filters) {
  if (filters.lineage && record.order_group !== filters.lineage) return false;
  if (filters.family && record.family !== filters.family) return false;
  if (filters.genus && record.genus !== filters.genus) return false;
  if (filters.ready === "ready" && !record.ready_full_analysis) return false;
  if (filters.ready === "basic" && !record.ready_basic_db) return false;
  if (filters.ready === "busco" && record.busco_complete_pct === null) return false;

  if (!filters.search) return true;
  const haystack = [
    record.sample_id,
    record.full_name,
    record.order_group,
    record.family,
    record.genus,
    record.species,
    record.strain_from_name,
  ].join(" ").toLowerCase();
  return haystack.includes(filters.search);
}

function sortRecords(records, sortValue) {
  const [field, direction] = sortValue.split(":");
  const multiplier = direction === "desc" ? -1 : 1;

  return [...records].sort((a, b) => {
    const aValue = a[field] ?? "";
    const bValue = b[field] ?? "";
    const aNum = Number(aValue);
    const bNum = Number(bValue);

    if (Number.isFinite(aNum) && Number.isFinite(bNum) && (aValue !== "" || bValue !== "")) {
      return (aNum - bNum) * multiplier;
    }
    return String(aValue).localeCompare(String(bValue)) * multiplier;
  });
}

function renderTable() {
  const tbody = document.getElementById("genome-table-body");
  if (!tbody) return;

  const visibleCount = document.getElementById("visible-count");
  const totalCount = document.getElementById("total-count");
  if (visibleCount) visibleCount.textContent = formatNumber(state.filtered.length);
  if (totalCount) totalCount.textContent = formatNumber(state.records.length);

  const totalPages = Math.max(1, Math.ceil(state.filtered.length / state.pageSize));
  state.page = Math.min(state.page, totalPages);
  const start = (state.page - 1) * state.pageSize;
  const pageRows = state.filtered.slice(start, start + state.pageSize);

  if (!pageRows.length) {
    tbody.innerHTML = '<tr class="table-empty"><td colspan="11">No genomes match the current filters.</td></tr>';
  } else {
    tbody.innerHTML = pageRows.map((record) => {
      const status = record.ready_full_analysis
        ? ["Full analysis", ""]
        : record.ready_basic_db
          ? ["Basic ready", "partial"]
          : ["Pending", "missing"];
      return `
        <tr>
          <td><a class="species-link" href="/genomes/${encodeURIComponent(record.sample_id)}/">${escapeHtml(record.species || record.full_name)}</a></td>
          <td><a class="sample-link" href="/genomes/${encodeURIComponent(record.sample_id)}/">${escapeHtml(record.sample_id)}</a></td>
          <td>${escapeHtml(record.order_group || "NA")}</td>
          <td>${formatMb(record.genome_size)}</td>
          <td>${formatDecimal(record.gc_content, 1)}%</td>
          <td>${formatKb(record.n50)}</td>
          <td>${formatNumber(record.gene_count)}</td>
          <td>${formatNumber(record.protein_count)}</td>
          <td>${formatDecimal(record.busco_complete_pct, 1)}%</td>
          <td>${formatNumber(record.bgc_count)}</td>
          <td><span class="status-pill ${status[1]}">${status[0]}</span></td>
        </tr>
      `;
    }).join("");
  }

  const pageStatus = document.getElementById("page-status");
  const prev = document.getElementById("prev-page");
  const next = document.getElementById("next-page");
  if (pageStatus) pageStatus.textContent = `Page ${state.page} / ${totalPages}`;
  if (prev instanceof HTMLButtonElement) prev.disabled = state.page <= 1;
  if (next instanceof HTMLButtonElement) next.disabled = state.page >= totalPages;
}

function applyFilters(resetPage = true) {
  const filters = getFilters();
  if (resetPage) state.page = 1;
  state.filtered = sortRecords(state.records.filter((record) => recordMatches(record, filters)), filters.sort);
  renderTable();
}

function bindControls() {
  ["genome-search", "lineage-filter", "family-filter", "genus-filter", "ready-filter", "sort-select"].forEach((id) => {
    const node = document.getElementById(id);
    if (!node) return;
    node.addEventListener(id === "genome-search" ? "input" : "change", () => applyFilters(true));
  });

  document.getElementById("prev-page")?.addEventListener("click", () => {
    state.page = Math.max(1, state.page - 1);
    renderTable();
  });

  document.getElementById("next-page")?.addEventListener("click", () => {
    state.page += 1;
    renderTable();
  });
}

async function initGenomes() {
  bindControls();

  try {
    state.records = await fetchAllSamples();
    state.filtered = [...state.records];
    populateFilters(state.records);
    updateMetrics(state.records);
    updateLineageBar(state.records);
    applyFilters(true);
  } catch (error) {
    const tbody = document.getElementById("genome-table-body");
    if (tbody) tbody.innerHTML = '<tr class="table-error"><td colspan="11">Genome data could not be loaded from the API.</td></tr>';
  }
}

document.addEventListener("DOMContentLoaded", () => {
  initNav();
  initGenomes();
});
