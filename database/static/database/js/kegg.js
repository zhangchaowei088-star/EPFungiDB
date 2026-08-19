const state = {
  next: null,
  previous: null,
  page: 1,
  organisms: [],
  pathways: [],
  selectedSampleId: "",
  selectedPathwayId: "",
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

function keggMapUrl(pathwayId) {
  if (!pathwayId) return "";
  const mapId = pathwayId.startsWith("ko") ? `map${pathwayId.slice(2)}` : pathwayId;
  return `https://www.kegg.jp/pathway/${encodeURIComponent(mapId)}`;
}

function keggKoUrl(koId) {
  return koId ? `https://www.kegg.jp/entry/${encodeURIComponent(koId)}` : "";
}

async function getJson(url) {
  const response = await fetch(url, { headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  return response.json();
}

async function loadOrganisms() {
  const records = [];
  let url = "/api/samples/?page_size=500&ordering=full_name";
  while (url) {
    const payload = await getJson(url);
    records.push(...(payload.results || []));
    url = normalizeApiUrl(payload.next);
  }
  state.organisms = records;
  renderOrganisms();
}

async function loadPathways(sampleId = "") {
  const query = sampleId ? `?sample_id=${encodeURIComponent(sampleId)}` : "";
  const payload = await getJson(`/api/kegg-pathway-index/${query}`);
  state.pathways = payload.results || [];
  renderPathways();
}

async function loadSummary() {
  const node = document.getElementById("kegg-summary");
  if (!node) return;
  const [members, pathways] = await Promise.all([
    getJson("/api/kegg-pathway-members/?page_size=1"),
    getJson("/api/kegg-pathway-index/"),
  ]);
  node.textContent = `${formatNumber(pathways.count)} KEGG map pathways indexed; ${formatNumber(members.count)} imported gene-pathway membership records currently available in the development database.`;
}

function renderOrganisms() {
  const list = document.getElementById("kegg-organism-list");
  if (!list) return;
  const query = document.getElementById("organism-filter")?.value.trim().toLowerCase() || "";
  const visible = state.organisms.filter((sample) => {
    const text = `${sample.full_name} ${sample.sample_id} ${sample.species} ${sample.genus}`.toLowerCase();
    return !query || text.includes(query);
  }).slice(0, 160);

  const rows = [
    `<label class="kegg-radio-row">
      <input type="radio" name="organism_choice" value="" ${state.selectedSampleId ? "" : "checked"}>
      <span><strong>All organisms</strong><small>Search across imported KEGG membership records</small></span>
    </label>`,
    ...visible.map((sample) => `
      <label class="kegg-radio-row">
        <input type="radio" name="organism_choice" value="${escapeHtml(sample.sample_id)}" ${state.selectedSampleId === sample.sample_id ? "checked" : ""}>
        <span><strong>${escapeHtml(sample.full_name)}</strong><small>${escapeHtml(sample.sample_id)} · ${escapeHtml(sample.order_group || "NA")}</small></span>
      </label>
    `),
  ];
  list.innerHTML = rows.join("");
}

function renderPathways() {
  const list = document.getElementById("kegg-pathway-list");
  if (!list) return;
  const query = document.getElementById("pathway-filter")?.value.trim().toLowerCase() || "";
  const visible = state.pathways.filter((pathway) => {
    const text = `${pathway.pathway_id} ${pathway.pathway_name}`.toLowerCase();
    return !query || text.includes(query);
  }).slice(0, 220);

  if (!visible.length) {
    list.innerHTML = '<div class="kegg-list-empty">No KEGG pathways match the current filter.</div>';
    return;
  }

  list.innerHTML = visible.map((pathway, index) => `
    <label class="kegg-radio-row">
      <input type="radio" name="pathway_choice" value="${escapeHtml(pathway.pathway_id)}" ${state.selectedPathwayId === pathway.pathway_id || (!state.selectedPathwayId && index === 0) ? "checked" : ""}>
      <span>
        <strong><a href="${escapeHtml(keggMapUrl(pathway.pathway_id))}" target="_blank" rel="noreferrer">${escapeHtml(pathway.pathway_id)}</a> · ${escapeHtml(pathway.pathway_name || "Unnamed pathway")}</strong>
        <small>${formatNumber(pathway.n_protein_ko_hits || pathway.total_protein_ko_hits)} protein-KO hits${pathway.n_samples ? ` · ${formatNumber(pathway.n_samples)} samples` : ""}</small>
      </span>
    </label>
  `).join("");

  if (!state.selectedPathwayId && visible[0]) {
    setSelectedPathway(visible[0].pathway_id);
  }
}

function setSelectedSample(sampleId) {
  state.selectedSampleId = sampleId;
  const input = document.getElementById("kegg-organism-value");
  if (input instanceof HTMLInputElement) input.value = sampleId;
}

function setSelectedPathway(pathwayId) {
  state.selectedPathwayId = pathwayId;
  const input = document.getElementById("pathway-input");
  if (input instanceof HTMLInputElement) input.value = pathwayId;
}

function buildSearchUrl() {
  const form = document.getElementById("kegg-search-form");
  if (!(form instanceof HTMLFormElement)) return "";
  const data = new FormData(form);
  const params = new URLSearchParams();
  params.set("page_size", "25");
  params.set("ordering", "sample_id,kegg_pathway_id,seqid,start");

  const sampleId = String(data.get("sample_id") || "").trim();
  const pathway = String(data.get("pathway") || "").trim();
  const ko = String(data.get("ko") || "").trim();
  const geneId = String(data.get("gene_id") || "").trim();
  const description = String(data.get("description") || "").trim();

  if (sampleId) params.set("sample_id", sampleId);
  if (pathway) params.set("kegg_pathway_id", pathway);
  if (ko) params.set("kegg_ko__icontains", ko);
  if (geneId) params.set("gene_id__icontains", geneId);
  if (description) params.set("search", description);

  return `/api/kegg-pathway-members/?${params.toString()}`;
}

function setHint(title, message, loading = false) {
  const hint = document.getElementById("kegg-hint");
  if (!hint) return;
  hint.hidden = false;
  hint.classList.toggle("loading", loading);
  hint.innerHTML = `<strong>${escapeHtml(title)}</strong><p>${escapeHtml(message)}</p>`;
}

function renderRows(records) {
  const tbody = document.getElementById("kegg-table-body");
  if (!tbody) return;
  if (!records.length) {
    tbody.innerHTML = '<tr class="gene-empty"><td colspan="8">No KEGG records match the current query.</td></tr>';
    return;
  }
  tbody.innerHTML = records.map((record) => {
    const detailUrl = `/genes/${encodeURIComponent(record.protein_uid)}/`;
    const mapLabel = record.pathway_name ? `${record.kegg_pathway_id} · ${record.pathway_name}` : record.kegg_pathway_id;
    return `
      <tr>
        <td><span class="organism-name">${escapeHtml(record.full_name)}</span></td>
        <td><a class="kegg-link" href="${escapeHtml(record.kegg_pathway_url || keggMapUrl(record.kegg_pathway_id))}" target="_blank" rel="noreferrer">${escapeHtml(mapLabel)}</a></td>
        <td>${record.kegg_ko ? `<a class="kegg-link ko" href="${escapeHtml(record.kegg_ko_url || keggKoUrl(record.kegg_ko))}" target="_blank" rel="noreferrer">${escapeHtml(record.kegg_ko)}</a>` : "-"}</td>
        <td><a class="gene-id-link" href="${detailUrl}">${escapeHtml(record.gene_id || record.source_protein_id)}</a></td>
        <td class="muted-gene-cell">${escapeHtml(record.source_protein_id)}</td>
        <td>${escapeHtml(compactText(record.preferred_name))}</td>
        <td>${escapeHtml(compactText(record.description))}</td>
        <td class="muted-gene-cell">${escapeHtml(record.score ?? "-")}</td>
      </tr>
    `;
  }).join("");
}

function updatePager(payload) {
  state.next = normalizeApiUrl(payload.next);
  state.previous = normalizeApiUrl(payload.previous);
  const head = document.getElementById("kegg-results-head");
  const count = document.getElementById("kegg-result-count");
  const status = document.getElementById("kegg-page-status");
  const prev = document.getElementById("kegg-prev");
  const next = document.getElementById("kegg-next");
  if (head) head.hidden = false;
  if (count) count.textContent = formatNumber(payload.count || 0);
  if (status) status.textContent = `Page ${state.page}`;
  if (prev instanceof HTMLButtonElement) prev.disabled = !state.previous;
  if (next instanceof HTMLButtonElement) next.disabled = !state.next;
}

async function runSearch(url, page = 1) {
  const button = document.querySelector(".search-button");
  if (button instanceof HTMLButtonElement) button.disabled = true;
  setHint("Searching KEGG Data...", "Querying gene-pathway membership records. Selected map pathways and organisms are applied as filters.", true);
  try {
    const payload = await getJson(url);
    state.page = page;
    renderRows(payload.results || []);
    updatePager(payload);
    setHint("Search complete", "Gene IDs open local gene detail pages; KO and map links open KEGG reference pages.");
  } catch (error) {
    const tbody = document.getElementById("kegg-table-body");
    if (tbody) tbody.innerHTML = '<tr class="gene-error"><td colspan="8">KEGG data could not be loaded from the API.</td></tr>';
    setHint("Search failed", "The query could not be completed. Please adjust filters and try again.");
  } finally {
    if (button instanceof HTMLButtonElement) button.disabled = false;
  }
}

function bindControls() {
  const form = document.getElementById("kegg-search-form");
  if (form instanceof HTMLFormElement) {
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      runSearch(buildSearchUrl(), 1);
    });
  }

  document.getElementById("organism-filter")?.addEventListener("input", renderOrganisms);
  document.getElementById("pathway-filter")?.addEventListener("input", renderPathways);

  document.getElementById("kegg-organism-list")?.addEventListener("change", async (event) => {
    const target = event.target;
    if (!(target instanceof HTMLInputElement)) return;
    setSelectedSample(target.value);
    state.selectedPathwayId = "";
    setSelectedPathway("");
    const list = document.getElementById("kegg-pathway-list");
    if (list) list.innerHTML = '<div class="kegg-list-empty">Loading pathways for selected organism...</div>';
    await loadPathways(target.value);
  });

  document.getElementById("kegg-pathway-list")?.addEventListener("change", (event) => {
    const target = event.target;
    if (target instanceof HTMLInputElement) setSelectedPathway(target.value);
  });

  document.getElementById("clear-kegg-search")?.addEventListener("click", async () => {
    if (form instanceof HTMLFormElement) form.reset();
    setSelectedSample("");
    setSelectedPathway("");
    document.getElementById("organism-filter").value = "";
    document.getElementById("pathway-filter").value = "";
    renderOrganisms();
    await loadPathways("");
    const tbody = document.getElementById("kegg-table-body");
    if (tbody) tbody.innerHTML = '<tr class="gene-empty"><td colspan="8">No query submitted yet.</td></tr>';
    const head = document.getElementById("kegg-results-head");
    if (head) head.hidden = true;
    setHint("Start KEGG Data Search", "Select an organism and KEGG map pathway, then search genes. KO and gene ID filters can further narrow results.");
  });

  document.getElementById("kegg-prev")?.addEventListener("click", () => {
    if (state.previous) runSearch(state.previous, Math.max(1, state.page - 1));
  });
  document.getElementById("kegg-next")?.addEventListener("click", () => {
    if (state.next) runSearch(state.next, state.page + 1);
  });
}

document.addEventListener("DOMContentLoaded", async () => {
  initNav();
  bindControls();
  try {
    await Promise.all([loadOrganisms(), loadPathways(), loadSummary()]);
  } catch (error) {
    const summary = document.getElementById("kegg-summary");
    if (summary) summary.textContent = "KEGG search is available, but summary metadata could not be loaded.";
  }
});
