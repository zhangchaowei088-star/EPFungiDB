const state = {
  samples: [],
  species: [],
  filtered: [],
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

function formatDecimal(value, digits = 1) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "NA";
  return Number(value).toFixed(digits);
}

function formatMb(value) {
  if (!value) return "NA";
  return `${formatDecimal(Number(value) / 1000000, 1)} Mb`;
}

function average(values) {
  const clean = values.map(Number).filter((value) => Number.isFinite(value) && value > 0);
  if (!clean.length) return null;
  return clean.reduce((sum, value) => sum + value, 0) / clean.length;
}

function groupBy(items, getKey) {
  const map = new Map();
  items.forEach((item) => {
    const key = getKey(item) || "Unassigned";
    if (!map.has(key)) map.set(key, []);
    map.get(key).push(item);
  });
  return map;
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

function buildSpecies(samples) {
  const bySpecies = groupBy(samples, (sample) => sample.species || sample.full_name);
  return Array.from(bySpecies, ([species, rows]) => {
    const first = rows[0] || {};
    return {
      species,
      genus: first.genus || "Unassigned",
      family: first.family || "Unassigned",
      order_group: first.order_group || "Unassigned",
      strain_count: rows.length,
      ready_count: rows.filter((row) => row.ready_full_analysis).length,
      avg_genome_size: average(rows.map((row) => row.genome_size)),
      avg_busco: average(rows.map((row) => row.busco_complete_pct)),
      avg_gc: average(rows.map((row) => row.gc_content)),
      gene_sum: rows.reduce((sum, row) => sum + (Number(row.gene_count) || 0), 0),
      protein_sum: rows.reduce((sum, row) => sum + (Number(row.protein_count) || 0), 0),
      effector_sum: rows.reduce((sum, row) => sum + (Number(row.effector_candidate_count) || 0), 0),
      bgc_sum: rows.reduce((sum, row) => sum + (Number(row.bgc_count) || 0), 0),
      strains: rows.sort((a, b) => String(a.sample_id).localeCompare(String(b.sample_id))),
    };
  });
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

function populateFilters(species) {
  populateSelect("species-lineage-filter", Array.from(new Set(species.map((item) => item.order_group))));
  populateSelect("species-family-filter", Array.from(new Set(species.map((item) => item.family))));
  populateSelect("species-genus-filter", Array.from(new Set(species.map((item) => item.genus))));
}

function animateNumber(node, target, formatter, duration = 900) {
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

function renderSummary(samples, species) {
  const summary = document.getElementById("species-summary");
  if (!summary) return;

  const genusCount = new Set(species.map((item) => item.genus).filter(Boolean)).size;
  const familyCount = new Set(species.map((item) => item.family).filter(Boolean)).size;
  const readyCount = samples.filter((item) => item.ready_full_analysis).length;

  const tiles = [
    { value: species.length, label: "Species", note: "species-level groups", format: formatNumber },
    { value: genusCount, label: "Genera", note: "taxonomic genera", format: formatNumber },
    { value: familyCount, label: "Families", note: "taxonomy families", format: formatNumber },
    { value: readyCount, label: "Full-analysis strains", note: `${formatDecimal((readyCount / Math.max(1, samples.length)) * 100, 1)}% of samples`, format: formatNumber },
  ];

  summary.innerHTML = tiles.map((tile, index) => `
    <div class="summary-tile">
      <strong data-summary-index="${index}">0</strong>
      <span>${escapeHtml(tile.label)}</span>
      <small>${escapeHtml(tile.note)}</small>
    </div>
  `).join("");

  tiles.forEach((tile, index) => {
    const node = summary.querySelector(`[data-summary-index="${index}"]`);
    if (node) animateNumber(node, tile.value, tile.format);
  });
}

function renderTaxonomy(species) {
  const tree = document.getElementById("taxonomy-tree");
  if (!tree) return;

  const byFamily = Array.from(groupBy(species, (item) => item.family), ([family, familyItems]) => {
    const byGenus = Array.from(groupBy(familyItems, (item) => item.genus), ([genus, genusItems]) => ({
      genus,
      speciesCount: genusItems.length,
      strainCount: genusItems.reduce((sum, item) => sum + item.strain_count, 0),
    })).sort((a, b) => b.speciesCount - a.speciesCount || a.genus.localeCompare(b.genus));

    return {
      family,
      speciesCount: familyItems.length,
      strainCount: familyItems.reduce((sum, item) => sum + item.strain_count, 0),
      genera: byGenus.slice(0, 8),
    };
  }).sort((a, b) => b.speciesCount - a.speciesCount || a.family.localeCompare(b.family));

  tree.innerHTML = byFamily.map((group) => `
    <div class="tree-group">
      <strong>${escapeHtml(group.family)} <span>${formatNumber(group.speciesCount)} spp.</span></strong>
      <ul>
        ${group.genera.map((genus) => `
          <li>${escapeHtml(genus.genus)} <span>${formatNumber(genus.speciesCount)} spp. · ${formatNumber(genus.strainCount)} strains</span></li>
        `).join("")}
      </ul>
    </div>
  `).join("");
}

function getFilters() {
  return {
    search: document.getElementById("species-search")?.value.trim().toLowerCase() || "",
    lineage: document.getElementById("species-lineage-filter")?.value || "",
    family: document.getElementById("species-family-filter")?.value || "",
    genus: document.getElementById("species-genus-filter")?.value || "",
    sort: document.getElementById("species-sort")?.value || "species:asc",
  };
}

function matchesFilters(item, filters) {
  if (filters.lineage && item.order_group !== filters.lineage) return false;
  if (filters.family && item.family !== filters.family) return false;
  if (filters.genus && item.genus !== filters.genus) return false;
  if (!filters.search) return true;

  const strainText = item.strains.map((strain) => `${strain.sample_id} ${strain.full_name} ${strain.strain_from_name}`).join(" ");
  const text = `${item.species} ${item.genus} ${item.family} ${item.order_group} ${strainText}`.toLowerCase();
  return text.includes(filters.search);
}

function sortSpecies(items, sortValue) {
  const [field, direction] = sortValue.split(":");
  const multiplier = direction === "desc" ? -1 : 1;

  return [...items].sort((a, b) => {
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

function renderSpeciesGrid() {
  const grid = document.getElementById("species-grid");
  if (!grid) return;

  const visible = document.getElementById("species-visible-count");
  const total = document.getElementById("species-total-count");
  if (visible) visible.textContent = formatNumber(state.filtered.length);
  if (total) total.textContent = formatNumber(state.species.length);

  if (!state.filtered.length) {
    grid.innerHTML = '<div class="species-empty">No species match the current filters.</div>';
    return;
  }

  grid.innerHTML = state.filtered.map((item) => {
    const previewStrains = item.strains.slice(0, 4);
    const extra = item.strains.length - previewStrains.length;
    return `
      <article class="species-card">
        <div class="species-card-head">
          <h3><a href="/api/samples/?species=${encodeURIComponent(item.species)}">${escapeHtml(item.species)}</a></h3>
          <span class="species-chip">${escapeHtml(item.order_group)}</span>
        </div>
        <div class="species-meta">
          <span>${escapeHtml(item.family)}</span>
          <span>${escapeHtml(item.genus)}</span>
          <span>${formatNumber(item.strain_count)} strains</span>
        </div>
        <div class="species-stats">
          <div class="species-stat">
            <strong>${formatDecimal(item.avg_busco, 1)}%</strong>
            <span>BUSCO</span>
          </div>
          <div class="species-stat">
            <strong>${formatMb(item.avg_genome_size)}</strong>
            <span>Genome</span>
          </div>
          <div class="species-stat">
            <strong>${formatNumber(item.effector_sum)}</strong>
            <span>Effectors</span>
          </div>
        </div>
        <div class="strain-list">
          ${previewStrains.map((strain) => `<a href="/genomes/${encodeURIComponent(strain.sample_id)}/">${escapeHtml(strain.sample_id)}</a>`).join(", ")}
          ${extra > 0 ? ` and ${formatNumber(extra)} more` : ""}
        </div>
      </article>
    `;
  }).join("");
}

function applyFilters() {
  const filters = getFilters();
  state.filtered = sortSpecies(state.species.filter((item) => matchesFilters(item, filters)), filters.sort);
  renderSpeciesGrid();
}

function bindControls() {
  ["species-search", "species-lineage-filter", "species-family-filter", "species-genus-filter", "species-sort"].forEach((id) => {
    const node = document.getElementById(id);
    if (!node) return;
    node.addEventListener(id === "species-search" ? "input" : "change", applyFilters);
  });
}

async function initSpecies() {
  bindControls();

  try {
    state.samples = await fetchAllSamples();
    state.species = buildSpecies(state.samples);
    state.filtered = sortSpecies(state.species, "species:asc");
    populateFilters(state.species);
    renderSummary(state.samples, state.species);
    renderTaxonomy(state.species);
    renderSpeciesGrid();
  } catch (error) {
    const grid = document.getElementById("species-grid");
    if (grid) grid.innerHTML = '<div class="species-empty">Species data could not be loaded from the API.</div>';
  }
}

document.addEventListener("DOMContentLoaded", () => {
  initNav();
  initSpecies();
});
