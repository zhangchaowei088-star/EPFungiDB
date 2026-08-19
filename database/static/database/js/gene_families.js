const state = { next: null, previous: null, page: 1 };

const featureTypeLabels = {
  secreted_signal_peptide: "Secretome signal peptide",
  effector_candidate: "Effector candidate",
  carbohydrate_active_enzyme: "CAZyme repertoire",
  protease: "Protease repertoire",
};

const sourceLabels = {
  signalp6: "SignalP6",
  effectorp: "EffectorP",
  dbcan_cazyme: "run_dbCAN",
  merops: "MEROPS",
  antismash: "antiSMASH",
  bigscape: "BiG-SCAPE",
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
  return text.length > 130 ? `${text.slice(0, 127)}...` : text;
}

function normalizeApiUrl(url) {
  return url ? url.replace(window.location.origin, "") : "";
}

async function getJson(url) {
  const response = await fetch(url, { headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  return response.json();
}

async function loadOrganisms() {
  const select = document.getElementById("family-organism-select");
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
  const node = document.getElementById("family-summary");
  if (!node) return;
  const payload = await getJson("/api/pathogenicity-overview/");
  renderOverview(payload);
}

function renderOverview(payload) {
  const summary = payload.summary || {};
  const bigscape = payload.bigscape || {};
  const c030 = (bigscape.global || []).find((row) => row.cutoff === "c0.30") || {};
  const familySummary = document.getElementById("family-summary");
  if (familySummary) {
    familySummary.textContent = `${formatNumber(summary.sample_count)} genomes, ${formatNumber(summary.bgc_total)} antiSMASH BGCs, and ${formatNumber(c030.gcf_count)} BiG-SCAPE GCFs are integrated with secretome, effector, CAZyme, and protease evidence.`;
  }

  const completeNode = document.getElementById("complete-sample-count");
  if (completeNode) completeNode.textContent = formatNumber(summary.complete_count);

  renderModuleCards(payload.modules || []);
}

function renderModuleCards(modules) {
  const container = document.getElementById("pathogenic-module-grid");
  if (!container) return;
  if (!modules.length) {
    container.innerHTML = '<div class="pathogenic-list-empty">Pathogenic annotation overview is not available.</div>';
    return;
  }
  container.innerHTML = modules.map((module) => `
    <article class="pathogenic-module-card" data-module="${escapeHtml(module.key)}">
      <div class="module-card-top">
        <span>${escapeHtml(module.source)}</span>
        <small>${escapeHtml(module.level)}</small>
      </div>
      <strong>${escapeHtml(module.title)}</strong>
      <div class="module-card-count">${formatNumber(module.primary_count)}</div>
      <p>${escapeHtml(module.interpretation)}</p>
      <div class="module-card-foot">
        <span>${formatNumber(module.sample_count)} genomes</span>
        <span>${formatNumber(module.secondary_count)} ${escapeHtml(module.secondary_label)}</span>
      </div>
    </article>
  `).join("");
}

function buildSearchUrl() {
  const form = document.getElementById("family-search-form");
  if (!(form instanceof HTMLFormElement)) return "";
  const data = new FormData(form);
  const params = new URLSearchParams();
  params.set("page_size", "25");
  params.set("ordering", "sample_id,feature_type,source_key");

  const sampleId = String(data.get("sample_id") || "").trim();
  const featureType = String(data.get("feature_type") || "").trim();
  const sourceKey = String(data.get("source_key") || "").trim();
  const featureId = String(data.get("feature_id") || "").trim();
  const geneId = String(data.get("gene_id") || "").trim();
  const description = String(data.get("description") || "").trim();

  if (sampleId) params.set("sample_id", sampleId);
  if (featureType) params.set("feature_type", featureType);
  if (sourceKey) params.set("source_key", sourceKey);
  if (featureId) params.set("feature_id__icontains", featureId);
  if (geneId) params.set("protein__gene_id__icontains", geneId);
  if (description) params.set("search", description);

  return `/api/pathogenicity-features/?${params.toString()}`;
}

function setHint(title, message, loading = false) {
  const hint = document.getElementById("family-hint");
  if (!hint) return;
  hint.hidden = false;
  hint.classList.toggle("loading", loading);
  hint.innerHTML = `<strong>${escapeHtml(title)}</strong><p>${escapeHtml(message)}</p>`;
}

function renderRows(records) {
  const tbody = document.getElementById("family-table-body");
  if (!tbody) return;
  if (!records.length) {
    tbody.innerHTML = '<tr class="gene-empty"><td colspan="8">No feature records match the current query.</td></tr>';
    return;
  }
  tbody.innerHTML = records.map((record) => {
    const detailUrl = `/genes/${encodeURIComponent(record.protein_uid)}/`;
    const family = [record.feature_label, record.feature_id].filter(Boolean).join(" / ") || "-";
    const evidence = [record.evidence_strength, sourceLabels[record.source_key] || record.source_key, record.score ? `score ${record.score}` : ""].filter(Boolean).join(" · ");
    const featureType = featureTypeLabels[record.feature_type] || record.feature_type;
    return `
      <tr>
        <td><span class="organism-name">${escapeHtml(record.full_name)}</span></td>
        <td><span class="feature-source-chip">${escapeHtml(featureType)}</span></td>
        <td>${escapeHtml(compactText(family))}</td>
        <td><a class="gene-id-link" href="${detailUrl}">${escapeHtml(record.gene_id || record.source_protein_id)}</a></td>
        <td class="muted-gene-cell">${escapeHtml(record.protein_id || record.source_protein_id)}</td>
        <td>${escapeHtml(compactText(record.product))}</td>
        <td>${escapeHtml(compactText(record.prediction || record.notes))}</td>
        <td class="muted-gene-cell">${escapeHtml(evidence || "-")}</td>
      </tr>
    `;
  }).join("");
}

function updatePager(payload) {
  state.next = normalizeApiUrl(payload.next);
  state.previous = normalizeApiUrl(payload.previous);
  const head = document.getElementById("family-results-head");
  const count = document.getElementById("family-result-count");
  const status = document.getElementById("family-page-status");
  const prev = document.getElementById("family-prev");
  const next = document.getElementById("family-next");
  if (head) head.hidden = false;
  if (count) count.textContent = formatNumber(payload.count || 0);
  if (status) status.textContent = `Page ${state.page}`;
  if (prev instanceof HTMLButtonElement) prev.disabled = !state.previous;
  if (next instanceof HTMLButtonElement) next.disabled = !state.next;
}

async function runSearch(url, page = 1) {
  const button = document.querySelector(".search-button");
  if (button instanceof HTMLButtonElement) button.disabled = true;
  setHint("Searching Feature Data...", "Querying candidate feature records. Specific organism and source filters improve speed.", true);
  try {
    const payload = await getJson(url);
    state.page = page;
    renderRows(payload.results || []);
    updatePager(payload);
    setHint("Search complete", "Results are pathogenicity-associated evidence records linked to gene/protein IDs.");
  } catch (error) {
    const tbody = document.getElementById("family-table-body");
    if (tbody) tbody.innerHTML = '<tr class="gene-error"><td colspan="8">Feature data could not be loaded from the API.</td></tr>';
    setHint("Search failed", "The query could not be completed. Please adjust filters and try again.");
  } finally {
    if (button instanceof HTMLButtonElement) button.disabled = false;
  }
}

function bindControls() {
  const form = document.getElementById("family-search-form");
  if (form instanceof HTMLFormElement) {
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      runSearch(buildSearchUrl(), 1);
    });
  }
  document.getElementById("clear-family-search")?.addEventListener("click", () => {
    if (form instanceof HTMLFormElement) form.reset();
    const tbody = document.getElementById("family-table-body");
    if (tbody) tbody.innerHTML = '<tr class="gene-empty"><td colspan="8">No query submitted yet.</td></tr>';
    const head = document.getElementById("family-results-head");
    if (head) head.hidden = true;
    setHint("Start pathogenic evidence search", "Search by evidence class, source, feature ID, gene ID, or product description. Results are returned as a gene/protein table.");
  });
  document.getElementById("family-prev")?.addEventListener("click", () => {
    if (state.previous) runSearch(state.previous, Math.max(1, state.page - 1));
  });
  document.getElementById("family-next")?.addEventListener("click", () => {
    if (state.next) runSearch(state.next, state.page + 1);
  });
}

document.addEventListener("DOMContentLoaded", async () => {
  initNav();
  bindControls();
  try {
    await Promise.all([loadOrganisms(), loadSummary()]);
  } catch (error) {
    const summary = document.getElementById("family-summary");
    if (summary) summary.textContent = "Pathogenic function search is available, but overview metadata could not be loaded.";
  }
});
