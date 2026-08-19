const state = {
  next: null,
  previous: null,
  currentUrl: null,
  page: 1,
};

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
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "NA";
  return new Intl.NumberFormat("en-US").format(Math.round(Number(value)));
}

function compactText(value, fallback = "-") {
  const text = String(value || "").trim();
  if (!text) return fallback;
  return text.length > 140 ? `${text.slice(0, 137)}...` : text;
}

function keggMapUrl(pathwayId) {
  const mapId = pathwayId.startsWith("ko") ? `map${pathwayId.slice(2)}` : pathwayId;
  return `https://www.kegg.jp/pathway/${encodeURIComponent(mapId)}`;
}

function linkKeggInfo(value) {
  const text = compactText(value);
  if (text === "-") return "-";
  return text.split(/[\s;,]+/).filter(Boolean).map((token) => {
    if (/^K\d{5}$/.test(token)) {
      return `<a class="kegg-link ko" href="https://www.kegg.jp/entry/${escapeHtml(token)}" target="_blank" rel="noreferrer">${escapeHtml(token)}</a>`;
    }
    if (/^(map|ko)\d{5}$/.test(token)) {
      return `<a class="kegg-link" href="${escapeHtml(keggMapUrl(token))}" target="_blank" rel="noreferrer">${escapeHtml(token)}</a>`;
    }
    return escapeHtml(token);
  }).join(" ");
}

async function getJson(url) {
  const response = await fetch(url, { headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  return response.json();
}

function normalizeApiUrl(url) {
  if (!url) return "";
  return url.replace(window.location.origin, "");
}

async function loadOrganisms() {
  const select = document.getElementById("organism-select");
  if (!(select instanceof HTMLSelectElement)) return;

  const records = [];
  let url = "/api/samples/?page_size=500&ordering=full_name";
  while (url) {
    const payload = await getJson(url);
    records.push(...(payload.results || []));
    url = normalizeApiUrl(payload.next);
  }

  select.innerHTML = '<option value="">All organisms</option>' + records.map((sample) => (
    `<option value="${escapeHtml(sample.sample_id)}">${escapeHtml(sample.full_name)} (${escapeHtml(sample.sample_id)})</option>`
  )).join("");
}

async function loadSummary() {
  const node = document.getElementById("gene-summary");
  if (!node) return;

  const [summary, proteins] = await Promise.all([
    getJson("/api/summary/"),
    getJson("/api/proteins/?page_size=1"),
  ]);
  node.textContent = `${formatNumber(proteins.count)} imported gene/protein records from ${formatNumber(summary.sample_count)} genomes; ${formatNumber(summary.total_genes)} sample-level gene counts in the full release.`;
}

function buildSearchUrl() {
  const form = document.getElementById("gene-search-form");
  if (!(form instanceof HTMLFormElement)) return "";

  const data = new FormData(form);
  const params = new URLSearchParams();
  params.set("page_size", "25");
  params.set("ordering", "sample_id,seqid,start");

  const sampleId = String(data.get("sample_id") || "").trim();
  const geneId = String(data.get("gene_id") || "").trim();
  const proteinId = String(data.get("protein_id") || "").trim();
  const geneName = String(data.get("gene_name") || "").trim();
  const description = String(data.get("description") || "").trim();
  const kegg = String(data.get("kegg_id") || "").trim();

  if (sampleId) params.set("sample_id", sampleId);
  if (geneId) params.set("gene_id__icontains", geneId);
  if (proteinId) params.set("protein_id__icontains", proteinId);
  if (geneName) params.set("general_annotation__eggnog_preferred_name__icontains", geneName);
  if (description) params.set("search", description);
  if (kegg) params.set("general_annotation__kegg_ko__icontains", kegg);

  return `/api/proteins/?${params.toString()}`;
}

function setLoading(message = "Searching Gene Data...") {
  const hint = document.getElementById("gene-hint");
  if (!hint) return;
  hint.hidden = false;
  hint.classList.add("loading");
  hint.innerHTML = `<strong>${message}</strong><p>Large gene datasets can take a moment to query. Selecting a specific organism usually improves speed.</p>`;
}

function setHint(title, message) {
  const hint = document.getElementById("gene-hint");
  if (!hint) return;
  hint.hidden = false;
  hint.classList.remove("loading");
  hint.innerHTML = `<strong>${escapeHtml(title)}</strong><p>${escapeHtml(message)}</p>`;
}

function renderRows(records) {
  const tbody = document.getElementById("gene-table-body");
  if (!tbody) return;

  if (!records.length) {
    tbody.innerHTML = '<tr class="gene-empty"><td colspan="7">No gene records match the current query.</td></tr>';
    return;
  }

  tbody.innerHTML = records.map((record) => {
    const detailUrl = `/genes/${encodeURIComponent(record.protein_uid)}/`;
    const location = [record.seqid, record.start && record.end ? `${formatNumber(record.start)}-${formatNumber(record.end)}` : "", record.strand]
      .filter(Boolean)
      .join(":");

    return `
      <tr>
        <td><span class="organism-name">${escapeHtml(record.full_name)}</span></td>
        <td><a class="gene-id-link" href="${detailUrl}">${escapeHtml(record.gene_id || record.protein_id)}</a></td>
        <td class="muted-gene-cell">${escapeHtml(record.protein_id)}</td>
        <td>${escapeHtml(compactText(record.gene_name || record.gene_id))}</td>
        <td>${escapeHtml(compactText(record.description || record.product))}</td>
        <td>${linkKeggInfo(record.kegg_info)}</td>
        <td class="muted-gene-cell">${escapeHtml(location || "-")}</td>
      </tr>
    `;
  }).join("");
}

function updatePager(payload) {
  state.next = normalizeApiUrl(payload.next);
  state.previous = normalizeApiUrl(payload.previous);

  const head = document.getElementById("gene-results-head");
  const count = document.getElementById("gene-result-count");
  const pageStatus = document.getElementById("gene-page-status");
  const prev = document.getElementById("gene-prev");
  const next = document.getElementById("gene-next");

  if (head) head.hidden = false;
  if (count) count.textContent = formatNumber(payload.count || 0);
  if (pageStatus) pageStatus.textContent = `Page ${state.page}`;
  if (prev instanceof HTMLButtonElement) prev.disabled = !state.previous;
  if (next instanceof HTMLButtonElement) next.disabled = !state.next;
}

async function runSearch(url, page = 1) {
  const searchButton = document.querySelector(".search-button");
  if (searchButton instanceof HTMLButtonElement) searchButton.disabled = true;
  setLoading();

  try {
    const payload = await getJson(url);
    state.currentUrl = url;
    state.page = page;
    renderRows(payload.results || []);
    updatePager(payload);
    setHint("Search complete", "If results do not match expectations, try exact gene IDs, protein IDs, or selecting one organism.");
  } catch (error) {
    const tbody = document.getElementById("gene-table-body");
    if (tbody) tbody.innerHTML = '<tr class="gene-error"><td colspan="7">Gene data could not be loaded from the API.</td></tr>';
    setHint("Search failed", "The query could not be completed. Please adjust filters and try again.");
  } finally {
    if (searchButton instanceof HTMLButtonElement) searchButton.disabled = false;
  }
}

function bindControls() {
  const form = document.getElementById("gene-search-form");
  if (form instanceof HTMLFormElement) {
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      runSearch(buildSearchUrl(), 1);
    });
  }

  document.getElementById("clear-gene-search")?.addEventListener("click", () => {
    if (form instanceof HTMLFormElement) form.reset();
    const tbody = document.getElementById("gene-table-body");
    if (tbody) tbody.innerHTML = '<tr class="gene-empty"><td colspan="7">No query submitted yet.</td></tr>';
    const head = document.getElementById("gene-results-head");
    if (head) head.hidden = true;
    setHint("Start Gene Data Search", "Enter one or more criteria above, then execute the query. Exact gene or protein IDs return the fastest results.");
  });

  document.getElementById("gene-prev")?.addEventListener("click", () => {
    if (state.previous) runSearch(state.previous, Math.max(1, state.page - 1));
  });

  document.getElementById("gene-next")?.addEventListener("click", () => {
    if (state.next) runSearch(state.next, state.page + 1);
  });
}

async function initGenes() {
  initNav();
  bindControls();

  try {
    await Promise.all([loadOrganisms(), loadSummary()]);
  } catch (error) {
    const summary = document.getElementById("gene-summary");
    if (summary) summary.textContent = "Gene search is available, but summary metadata could not be loaded.";
  }
}

document.addEventListener("DOMContentLoaded", initGenes);
