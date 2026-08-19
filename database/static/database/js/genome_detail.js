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

function valueOrDash(value) {
  return value === null || value === undefined || value === "" ? "-" : value;
}

function formatNumber(value) {
  if (value === null || value === undefined || value === "" || Number.isNaN(Number(value))) return "NA";
  return new Intl.NumberFormat("en-US").format(Math.round(Number(value)));
}

function formatDecimal(value, digits = 1) {
  if (value === null || value === undefined || value === "" || Number.isNaN(Number(value))) return "NA";
  return Number(value).toFixed(digits);
}

function formatPercent(value, digits = 1) {
  if (value === null || value === undefined || value === "" || Number.isNaN(Number(value))) return "NA";
  return `${formatDecimal(value, digits)}%`;
}

function formatMb(value) {
  if (!value || Number.isNaN(Number(value))) return "NA";
  return `${formatDecimal(Number(value) / 1000000, 2)} Mb`;
}

function formatKb(value) {
  if (!value || Number.isNaN(Number(value))) return "NA";
  return `${formatDecimal(Number(value) / 1000, 1)} kb`;
}

function ratioToPct(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return null;
  return number <= 1 ? number * 100 : number;
}

function compactUnique(values, limit = 3) {
  const seen = new Set();
  const clean = values
    .map((value) => String(value || "").trim())
    .filter(Boolean)
    .filter((value) => {
      const key = value.toLowerCase();
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  if (!clean.length) return "";
  const shown = clean.slice(0, limit).join("; ");
  const extra = clean.length > limit ? ` (+${clean.length - limit} more)` : "";
  return `${shown}${extra}`;
}

function hostRelationLabel(value) {
  const labels = {
    isolated_from_host: "isolation host",
    experimental_host_only: "experimental target",
    unknown_host_relation: "source host field, relation unresolved",
    environmental_association: "environmental association",
    environmental_association_only: "environmental association",
    pending_curation: "pending curation",
  };
  return labels[value] || value || "pending curation";
}

function hostName(row, scientificKey = "host_scientific_name", verbatimKey = "host_name_verbatim") {
  const scientific = String(row?.[scientificKey] || "").trim();
  const verbatim = String(row?.[verbatimKey] || "").trim();
  if (scientific && verbatim && scientific.toLowerCase() !== verbatim.toLowerCase() && !verbatim.toLowerCase().includes(scientific.toLowerCase())) {
    return `${verbatim} (${scientific})`;
  }
  return scientific || verbatim;
}

function summarizePotentialHosts(record) {
  const basic = record.basic_metadata || {};
  const summary = basic.metadata_summary || {};
  const assays = Array.isArray(basic.virulence_assays) ? basic.virulence_assays : [];
  const associations = Array.isArray(basic.host_associations) ? basic.host_associations : [];
  const candidates = [];
  const evidenceTypes = [];

  assays.forEach((row) => {
    const name = hostName(row, "target_scientific_name", "target_name_verbatim");
    if (name) candidates.push(name);
  });
  if (assays.length) evidenceTypes.push("experimental target");

  const directAssociations = associations.filter((row) => row.association_type !== "environmental_association");
  directAssociations.forEach((row) => {
    const name = hostName(row);
    if (name) candidates.push(name);
  });
  directAssociations.forEach((row) => {
    const label = hostRelationLabel(row.association_type);
    if (label) evidenceTypes.push(label);
  });

  const hostSummary = compactUnique(candidates);
  const evidenceSummary = compactUnique(evidenceTypes, 2);
  if (hostSummary) {
    return evidenceSummary ? `${hostSummary} (${evidenceSummary})` : hostSummary;
  }

  const environmental = associations.filter((row) => row.association_type === "environmental_association");
  const environmentalNames = compactUnique(environmental.map((row) => hostName(row)));
  if (environmentalNames) {
    return `${environmentalNames} (environmental association, not treated as host)`;
  }

  if (summary.isolation_source_summary) {
    const status = hostRelationLabel(summary.strain_host_status);
    return `${summary.isolation_source_summary} (isolation source; ${status})`;
  }

  return summary.strain_host_status ? `No source-supported host listed (${hostRelationLabel(summary.strain_host_status)})` : "No source-supported host listed";
}

async function getJson(url) {
  const response = await fetch(url, { headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error(`${url} returned ${response.status} ${response.statusText}`);
  return response.json();
}

async function getOptionalJson(url, fallback) {
  try {
    return await getJson(url);
  } catch (error) {
    console.warn(error);
    return fallback;
  }
}

function detailRows(rows) {
  return `<dl class="detail-list">${rows.map(([label, value, className = ""]) => `
    <div>
      <dt>${escapeHtml(label)}</dt>
      <dd class="${className}">${escapeHtml(valueOrDash(value))}</dd>
    </div>
  `).join("")}</dl>`;
}

function metricTiles(items) {
  return `<div class="metric-strip">${items.map((item) => `
    <div class="metric-tile">
      <strong>${escapeHtml(item.value)}</strong>
      <span>${escapeHtml(item.label)}</span>
    </div>
  `).join("")}</div>`;
}

function stackedBar(items) {
  const clean = items.map((item) => ({ ...item, value: Math.max(0, Number(item.value) || 0) }));
  const total = clean.reduce((sum, item) => sum + item.value, 0) || 100;
  return `
    <div class="stacked-bar">
      ${clean.map((item) => {
        const width = Math.max(0, (item.value / total) * 100);
        return `<div class="bar-segment" style="width:${width}%;--bar-color:${item.color}">${width >= 8 ? `${escapeHtml(item.short)} ${formatDecimal(item.value, 1)}%` : ""}</div>`;
      }).join("")}
    </div>
    <div class="legend-row">
      ${clean.map((item) => `<span style="--bar-color:${item.color}"><i></i>${escapeHtml(item.label)} ${formatDecimal(item.value, 1)}%</span>`).join("")}
    </div>
  `;
}

function ratioLine(label, value) {
  const pct = Math.max(0, Math.min(100, ratioToPct(value) ?? 0));
  return `
    <div class="ratio-line">
      <span>${escapeHtml(label)}</span>
      <div class="ratio-track"><div class="ratio-fill" style="--value:${pct}%"></div></div>
      <span>${formatPercent(pct, 1)}</span>
    </div>
  `;
}

function renderHero(record) {
  const title = document.getElementById("strain-title");
  const subtitle = document.getElementById("strain-subtitle");
  const breadcrumb = document.getElementById("detail-breadcrumb");
  const geneLink = document.getElementById("gene-search-link");
  const apiLink = document.getElementById("sample-api-link");
  const encoded = encodeURIComponent(record.sample_id);

  document.title = `${record.sample_id} Genome | EPFungiDB`;
  if (title) title.textContent = record.species || record.full_name || record.sample_id;
  if (subtitle) {
    subtitle.textContent = `${record.full_name || record.sample_id} · ${record.sample_id} · ${record.ready_full_analysis ? "full analysis ready" : "partial analysis record"}`;
  }
  if (breadcrumb) {
    const parts = [record.order_group, record.family, record.genus, record.species || record.full_name].filter(Boolean);
    breadcrumb.innerHTML = parts.map((part) => `<span>${escapeHtml(part)}</span>`).join("");
  }
  if (geneLink) geneLink.href = `/genes/?sample_id=${encoded}`;
  if (apiLink) apiLink.href = `/api/samples/${encoded}/`;
  if (document.getElementById("quality-api-link")) document.getElementById("quality-api-link").href = `/api/samples/${encoded}/`;
  if (document.getElementById("file-api-link")) document.getElementById("file-api-link").href = `/api/samples/${encoded}/files/`;
  if (document.getElementById("antismash-api-link")) document.getElementById("antismash-api-link").href = `/api/samples/${encoded}/antismash-regions/`;
}

function renderTopCards(record, keggPathways) {
  const container = document.getElementById("top-cards");
  if (!container) return;
  const genome = record.genome_metric || {};
  const functional = record.functional_summary || {};
  const keggCount = Array.isArray(keggPathways) ? keggPathways.length : 0;
  const potentialHosts = summarizePotentialHosts(record);

  container.innerHTML = `
    <article class="detail-card">
      <div class="card-title">
        <h2>Basic Information</h2>
        <p>Strain-level taxonomy, assembly metrics, and database identifiers.</p>
      </div>
      ${detailRows([
        ["Sample ID", record.sample_id, "mono"],
        ["Full name", record.full_name],
        ["Lineage group", record.order_group],
        ["Family", record.family],
        ["Genus", record.genus],
        ["Species", record.species],
        ["Strain", record.strain_from_name],
        ["Potential host / association", potentialHosts],
        ["Genome size", formatMb(record.genome_size || genome.genome_size)],
        ["GC content", formatPercent(record.gc_content || genome.gc_content, 2)],
        ["N50", formatKb(record.n50 || genome.n50)],
        ["Scaffold number", formatNumber(record.scaffold_count || genome.scaffold_count)],
      ])}
    </article>

    <article class="detail-card">
      <div class="card-title">
        <h2>Annotation Summary</h2>
        <p>Functional annotation counts imported from funannotate and eggNOG-mapper outputs.</p>
      </div>
      ${metricTiles([
        { value: formatNumber(functional.total_genes || record.gene_count), label: "Total genes" },
        { value: formatNumber(record.protein_count || genome.protein_count), label: "Proteins" },
        { value: formatNumber(functional.eggnog_matched_genes), label: "eggNOG matches" },
      ])}
      ${detailRows([
        ["Functionally annotated genes", formatNumber(functional.any_functionally_annotated_genes)],
        ["Unannotated genes", formatNumber(functional.unannotated_genes)],
        ["funannotate annotated", formatNumber(functional.funannotate_annotated_genes)],
        ["eggNOG annotated", formatNumber(functional.eggnog_annotated_genes)],
        ["KEGG pathways in DB", formatNumber(keggCount)],
        ["Annotation output", functional.output, "mono"],
      ])}
    </article>
  `;
}

function renderQuality(record) {
  const container = document.getElementById("quality-card");
  if (!container) return;
  const busco = record.busco_summary || {};
  const functional = record.functional_summary || {};

  const buscoItems = [
    { label: "Single-copy", short: "S", value: busco.single_copy_pct, color: "#62c9a7" },
    { label: "Duplicated", short: "D", value: busco.duplicated_pct, color: "#6fbe6a" },
    { label: "Fragmented", short: "F", value: busco.fragmented_pct, color: "#b9d96a" },
    { label: "Missing", short: "M", value: busco.missing_pct, color: "#d97f72" },
  ];

  container.innerHTML = `
    <div class="section-title-row">
      <div>
        <h2>Quality Assessment</h2>
        <p>Genome and annotation quality summaries from imported local analysis results.</p>
      </div>
      <a href="/api/samples/${encodeURIComponent(record.sample_id)}/">API detail</a>
    </div>
    <div class="quality-body">
      <div class="quality-block">
        <h3>Genome Quality</h3>
        ${stackedBar(buscoItems)}
        <p class="quality-note">${escapeHtml(busco.one_line_summary || "BUSCO one-line summary is not available for this record.")}</p>
      </div>
      <div class="quality-block">
        <h3>Annotation Coverage</h3>
        ${ratioLine("Any functional annotation", functional.any_annotation_ratio)}
        ${ratioLine("eggNOG match ratio", functional.eggnog_match_ratio)}
        ${ratioLine("eggNOG annotation ratio", functional.eggnog_annotation_ratio)}
        ${ratioLine("Unannotated ratio", functional.unannotated_ratio)}
      </div>
    </div>
  `;
}

function renderFeatureCards(record) {
  const container = document.getElementById("feature-cards");
  if (!container) return;
  const path = record.pathogenicity_summary || {};
  const anti = record.antismash_summary || {};
  const signalp = record.signalp_summary || {};

  container.innerHTML = `
    <article class="detail-card">
      <div class="card-title">
        <h2>Candidate Feature Summary</h2>
        <p>Counts are candidate pathogenicity-associated or host-interaction features, not validated virulence genes.</p>
      </div>
      <div class="feature-list">
        <div class="feature-row"><span>Signal peptides</span><strong>${formatNumber(path.signalp_sp_count || signalp.signalp_sp_count)}</strong></div>
        <div class="feature-row"><span>High-confidence signal peptides</span><strong>${formatNumber(path.signalp_high_confidence_sp_count || signalp.signalp_high_confidence_sp_count)}</strong></div>
        <div class="feature-row"><span>Effector candidates</span><strong>${formatNumber(path.effector_candidate_count)}</strong></div>
        <div class="feature-row"><span>CAZyme proteins</span><strong>${formatNumber(path.cazyme_protein_count)}</strong></div>
        <div class="feature-row"><span>MEROPS proteins</span><strong>${formatNumber(path.merops_protein_count)}</strong></div>
        <div class="feature-row"><span>Biosynthetic gene clusters</span><strong>${formatNumber(path.bgc_count || anti.bgc_count)}</strong></div>
      </div>
    </article>

    <article class="detail-card">
      <div class="card-title">
        <h2>Analysis Status</h2>
        <p>Module availability from the ready-for-database analysis matrix.</p>
      </div>
      <div class="status-grid">
        ${[
          ["Genome core", record.has_genome_core],
          ["Functional core", record.has_functional_core],
          ["BUSCO", record.has_busco],
          ["antiSMASH", record.has_antismash],
          ["SignalP", record.has_signalp],
        ].map(([label, ready]) => `
          <div class="status-item ${ready ? "ready" : ""}">
            <strong>${ready ? "Ready" : "Missing"}</strong>
            <span>${escapeHtml(label)}</span>
          </div>
        `).join("")}
      </div>
      ${detailRows([
        ["Ready basic DB", record.ready_basic_db ? "Yes" : "No"],
        ["Ready full analysis", record.ready_full_analysis ? "Yes" : "No"],
        ["antiSMASH products", path.antismash_top_products || anti.top_products],
        ["antiSMASH version", anti.antismash_version],
      ])}
    </article>
  `;
}

function renderAntismash(record, antismash) {
  const section = document.getElementById("antismash-section");
  if (!section) return;
  const summary = record.antismash_summary || {};
  const regionCount = antismash?.region_count ?? summary.bgc_count ?? 0;
  const products = antismash?.product_counts || [];
  const regions = antismash?.regions || [];
  const topRegions = regions.slice(0, 10);

  if (!antismash?.json_present && !summary.json_present) {
    section.innerHTML = `
      <div class="section-title-row">
        <div>
          <h2>antiSMASH Regions</h2>
          <p>No parsed antiSMASH JSON is available for this strain.</p>
        </div>
        <a href="/api/samples/${encodeURIComponent(record.sample_id)}/">Sample API</a>
      </div>
      <div class="empty-panel">antiSMASH region-level information is unavailable for this record.</div>
    `;
    return;
  }

  section.innerHTML = `
    <div class="section-title-row">
      <div>
        <h2>antiSMASH Regions</h2>
        <p>Biosynthetic gene cluster regions parsed from the local antiSMASH result JSON.</p>
      </div>
      <div class="section-actions">
        <a href="${escapeHtml(antismash?.report_url || `/genomes/${encodeURIComponent(record.sample_id)}/antismash/`)}" target="_blank" rel="noreferrer">Open Report</a>
        <a href="/api/samples/${encodeURIComponent(record.sample_id)}/antismash-regions/">antiSMASH API</a>
      </div>
    </div>

    <div class="antismash-body">
      <div class="antismash-summary-grid">
        <div class="antismash-stat"><strong>${formatNumber(regionCount)}</strong><span>BGC regions</span></div>
        <div class="antismash-stat"><strong>${formatNumber(antismash?.protocluster_count)}</strong><span>Protoclusters</span></div>
        <div class="antismash-stat"><strong>${formatNumber(antismash?.candidate_count)}</strong><span>Candidate clusters</span></div>
        <div class="antismash-stat"><strong>${formatNumber(antismash?.contig_edge_count ?? summary.contig_edge_bgcs)}</strong><span>Contig-edge BGCs</span></div>
        <div class="antismash-stat"><strong>${formatDecimal(antismash?.median_region_size_kb ?? summary.median_bgc_size_kb, 1)} kb</strong><span>Median size</span></div>
        <div class="antismash-stat"><strong>${escapeHtml(antismash?.version || summary.antismash_version || "NA")}</strong><span>Version</span></div>
      </div>

      <div class="antismash-products">
        <h3>Product Classes</h3>
        ${products.length ? products.map((item) => {
          const pct = (Number(item.count) / Math.max(1, regionCount)) * 100;
          return `
            <div class="product-row">
              <span>${escapeHtml(item.product)}</span>
              <div class="product-track"><div style="width:${Math.min(100, pct)}%"></div></div>
              <strong>${formatNumber(item.count)}</strong>
            </div>
          `;
        }).join("") : `<p class="quality-note">${escapeHtml(summary.top_products || "Product class counts are not available.")}</p>`}
      </div>

      <div class="antismash-table-wrap">
        <div class="antismash-table-head">
          <h3>Region Preview</h3>
          <span>${formatNumber(topRegions.length)} shown from ${formatNumber(regions.length)} regions</span>
        </div>
        ${topRegions.length ? `
          <table class="antismash-table">
            <thead>
              <tr>
                <th>Region</th>
                <th>Location</th>
                <th>Size</th>
                <th>Products</th>
                <th>Clusters</th>
                <th>Edge</th>
              </tr>
            </thead>
            <tbody>
              ${topRegions.map((region) => `
                <tr>
                  <td><span class="region-id">${escapeHtml(region.region_id)}</span></td>
                  <td>${escapeHtml(region.seqid)}:${formatNumber(region.start)}-${formatNumber(region.end)}</td>
                  <td>${formatDecimal(region.size_kb, 1)} kb</td>
                  <td>${(region.products || []).map((product) => `<span class="product-chip">${escapeHtml(product)}</span>`).join("") || "NA"}</td>
                  <td>${formatNumber(region.protocluster_count)} proto · ${formatNumber(region.candidate_count)} cand</td>
                  <td>${region.contig_edge ? '<span class="edge-pill">edge</span>' : '<span class="edge-pill internal">internal</span>'}</td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        ` : '<div class="empty-panel">No antiSMASH region rows were returned.</div>'}
      </div>

      <div class="antismash-paths">
        ${detailRows([
          ["antiSMASH index.html", antismash?.index_html_path, "mono"],
          ["antiSMASH JSON", antismash?.json_path || record.antismash_json_path, "mono"],
          ["Top products summary", summary.top_products || record.pathogenicity_summary?.antismash_top_products],
        ])}
      </div>
    </div>
  `;
}

function buildFileCards(record, indexedFiles) {
  const busco = record.busco_summary || {};
  const path = record.pathogenicity_summary || {};
  const anti = record.antismash_summary || {};
  const signalp = record.signalp_summary || {};
  const core = [
    ["Genome", "Genome sequence in FASTA format", record.genome_fasta_path],
    ["GFF3", "Gene annotation in GFF3 format", record.gff3_path],
    ["CDS", "Coding sequence FASTA", record.cds_fasta_path],
    ["Protein", "Protein sequence FASTA", record.protein_fasta_path],
    ["GenBank", "Annotated GenBank record", record.genbank_path],
    ["BUSCO JSON", "BUSCO summary output", busco.summary_json_path],
    ["antiSMASH JSON", "Secondary metabolism summary", record.antismash_json_path || path.antismash_json_path || anti.antismash_dir],
    ["SignalP", "Signal peptide prediction output", record.signalp_prediction_path || path.signalp_prediction_path || signalp.prediction_results_path],
    ["EffectorP", "Effector candidate prediction", path.effectorp_path],
    ["CAZyme", "dbCAN CAZyme annotation", path.cazyme_tsv_path],
    ["MEROPS", "Protease annotation", path.merops_tsv_path],
  ];
  const cards = core.filter((item) => item[2]);

  if (cards.length) return cards;
  return (indexedFiles || []).slice(0, 8).map((file) => [file.data_type, file.object_type || "Indexed file", file.path]);
}

function renderFiles(record, indexedFiles) {
  const section = document.getElementById("file-section");
  if (!section) return;
  const cards = buildFileCards(record, indexedFiles);

  section.innerHTML = `
    <div class="section-title-row">
      <div>
        <h2>Indexed Files</h2>
        <p>Core genome and analysis result paths indexed for this strain. Direct downloads can be wired later.</p>
      </div>
      <a href="/api/samples/${encodeURIComponent(record.sample_id)}/files/">File API</a>
    </div>
    <div class="file-grid">
      ${cards.length ? cards.map(([title, description, path]) => `
        <article class="file-card">
          <div>
            <strong>${escapeHtml(title)}</strong>
            <span>${escapeHtml(description)}</span>
          </div>
          <div class="file-path" title="${escapeHtml(path)}">${escapeHtml(path)}</div>
          <button type="button" data-copy="${escapeHtml(path)}">Copy path</button>
        </article>
      `).join("") : '<div class="empty-panel">No indexed file paths were returned for this strain.</div>'}
    </div>
  `;

  section.querySelectorAll("[data-copy]").forEach((button) => {
    button.addEventListener("click", async () => {
      const path = button.getAttribute("data-copy") || "";
      try {
        await navigator.clipboard.writeText(path);
        button.textContent = "Copied";
        setTimeout(() => { button.textContent = "Copy path"; }, 1400);
      } catch (error) {
        button.textContent = "Copy failed";
        setTimeout(() => { button.textContent = "Copy path"; }, 1400);
      }
    });
  });
}

function renderError(error) {
  const shell = document.querySelector(".genome-detail-shell");
  if (!shell) return;
  shell.innerHTML = `
    <a class="detail-back-link" href="/genomes/">Back to Genome Browser</a>
    <div class="load-error">
      <h1>Genome record unavailable</h1>
      <p>The requested sample could not be loaded from the local API. Check the sample ID and server status.</p>
      <p class="error-detail">${escapeHtml(error?.message || "")}</p>
    </div>
  `;
}

async function initGenomeDetail() {
  initNav();
  const sampleId = window.EPFUNGI_SAMPLE_ID;
  if (!sampleId) return renderError();

  const encoded = encodeURIComponent(sampleId);
  try {
    const record = await getJson(`/api/samples/${encoded}/`);
    const [files, keggPathways] = await Promise.all([
      getOptionalJson(`/api/samples/${encoded}/files/`, []),
      getOptionalJson(`/api/samples/${encoded}/kegg-pathways/`, []),
    ]);
    const antismash = await getOptionalJson(`/api/samples/${encoded}/antismash-regions/`, null);
    renderHero(record);
    renderTopCards(record, keggPathways);
    renderQuality(record);
    renderFeatureCards(record);
    renderAntismash(record, antismash);
    renderFiles(record, Array.isArray(files) ? files : []);
  } catch (error) {
    renderError(error);
  }
}

document.addEventListener("DOMContentLoaded", initGenomeDetail);
