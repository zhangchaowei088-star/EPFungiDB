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

function formatDecimal(value, digits = 3) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "NA";
  return Number(value).toFixed(digits);
}

async function getJson(url) {
  const response = await fetch(url, { headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  return response.json();
}

function valueOrDash(value) {
  return value === null || value === undefined || value === "" ? "-" : value;
}

function detailRows(rows) {
  return `<dl class="detail-list">${rows.map(([label, value]) => `
    <div><dt>${escapeHtml(label)}</dt><dd>${escapeHtml(valueOrDash(value))}</dd></div>
  `).join("")}</dl>`;
}

function linkedDetailRows(rows) {
  return `<dl class="detail-list">${rows.map(([label, value]) => `
    <div><dt>${escapeHtml(label)}</dt><dd>${value || "-"}</dd></div>
  `).join("")}</dl>`;
}

function splitValues(value) {
  return String(value || "").split(/[;,]\s*|\s+/).map((item) => item.trim()).filter(Boolean);
}

function keggMapUrl(pathwayId) {
  const mapId = pathwayId.startsWith("ko") ? `map${pathwayId.slice(2)}` : pathwayId;
  return `https://www.kegg.jp/pathway/${encodeURIComponent(mapId)}`;
}

function linkKeggKo(value) {
  const items = splitValues(value).filter((item) => /^K\d{5}$/.test(item));
  return items.length ? items.map((ko) => `<a class="kegg-link ko" href="https://www.kegg.jp/entry/${escapeHtml(ko)}" target="_blank" rel="noreferrer">${escapeHtml(ko)}</a>`).join(" ") : "";
}

function linkKeggMaps(value) {
  const items = splitValues(value).filter((item) => /^(map|ko)\d{5}$/.test(item));
  return items.length ? items.map((pathway) => `<a class="kegg-link" href="${escapeHtml(keggMapUrl(pathway))}" target="_blank" rel="noreferrer">${escapeHtml(pathway)}</a>`).join(" ") : "";
}

function pill(label, active) {
  return active ? `<span>${escapeHtml(label)}</span>` : "";
}

function renderDetail(record, features) {
  const annotation = record.general_annotation || {};
  const path = record.pathogenicity_summary || {};
  const title = document.getElementById("detail-title");
  const subtitle = document.getElementById("detail-subtitle");
  const grid = document.getElementById("gene-detail-grid");

  if (title) title.textContent = record.gene_id || record.protein_id || record.protein_uid;
  if (subtitle) subtitle.textContent = `${record.full_name} · ${record.protein_id} · ${record.seqid}:${formatNumber(record.start)}-${formatNumber(record.end)} (${record.strand || "NA"})`;
  if (!grid) return;

  const featurePills = [
    pill("General annotation", record.has_general_functional_annotation),
    pill("Pathogenicity-associated feature", record.has_pathogenicity_associated_feature),
    pill("Secreted", path.is_secreted),
    pill("Effector candidate", path.is_effector_candidate),
    pill("CAZyme", path.has_cazyme),
    pill("MEROPS", path.has_merops),
  ].filter(Boolean).join("");

  grid.innerHTML = `
    <article class="detail-card">
      <h2>Gene Record</h2>
      ${detailRows([
        ["Sample ID", record.sample_id],
        ["Organism", record.full_name],
        ["Gene ID", record.gene_id],
        ["Transcript ID", record.transcript_id],
        ["Protein ID", record.protein_id],
        ["Protein length", record.protein_length ? `${formatNumber(record.protein_length)} aa` : ""],
      ])}
    </article>

    <article class="detail-card">
      <h2>Genome Location</h2>
      ${detailRows([
        ["SeqID", record.seqid],
        ["Start", formatNumber(record.start)],
        ["End", formatNumber(record.end)],
        ["Strand", record.strand],
        ["Product", record.product],
        ["API", `/api/proteins/${encodeURIComponent(record.protein_uid)}/`],
      ])}
    </article>

    <article class="detail-card">
      <h2>Feature Status</h2>
      <div class="feature-pills">${featurePills || "<span>No feature flags</span>"}</div>
      ${detailRows([
        ["Feature count", path.pathogenicity_feature_count],
        ["SignalP", path.signalp_prediction],
        ["SignalP score", formatDecimal(path.signalp_sp_score, 3)],
        ["EffectorP", path.effectorp_prediction],
        ["EffectorP score", formatDecimal(path.effectorp_score, 3)],
      ])}
    </article>

    <article class="detail-card wide">
      <h2>Functional Annotation</h2>
      ${detailRows([
        ["Preferred name", annotation.eggnog_preferred_name],
        ["Description", annotation.eggnog_description || annotation.funannotate_product || record.product],
        ["GO terms", annotation.go_terms],
        ["EC numbers", annotation.ec_numbers],
        ["PFAM", annotation.pfam_domains],
      ])}
    </article>

    <article class="detail-card">
      <h2>KEGG</h2>
      ${linkedDetailRows([
        ["KO", linkKeggKo(annotation.kegg_ko)],
        ["Pathways", linkKeggMaps(annotation.kegg_pathways)],
        ["Modules", escapeHtml(valueOrDash(annotation.kegg_modules))],
        ["Reactions", escapeHtml(valueOrDash(annotation.kegg_reactions))],
        ["BRITE", escapeHtml(valueOrDash(annotation.brite_terms))],
      ])}
    </article>

    <article class="detail-card full">
      <h2>Pathogenicity-Associated Features</h2>
      ${features.length ? detailRows(features.map((feature) => [
        feature.feature_type || feature.source_key,
        [feature.feature_label, feature.feature_id, feature.prediction, feature.score].filter(Boolean).join(" · "),
      ])) : "<p class=\"muted-gene-cell\">No long-form feature records were returned for this protein.</p>"}
    </article>
  `;
}

async function initDetail() {
  initNav();
  const uid = window.EPFUNGI_GENE_UID;
  const grid = document.getElementById("gene-detail-grid");
  if (!uid || !grid) return;

  try {
    const encoded = encodeURIComponent(uid);
    const [record, featurePayload] = await Promise.all([
      getJson(`/api/proteins/${encoded}/`),
      getJson(`/api/proteins/${encoded}/features/`),
    ]);
    renderDetail(record, Array.isArray(featurePayload) ? featurePayload : []);
  } catch (error) {
    const title = document.getElementById("detail-title");
    const subtitle = document.getElementById("detail-subtitle");
    if (title) title.textContent = "Gene detail unavailable";
    if (subtitle) subtitle.textContent = "The requested gene record could not be loaded.";
    grid.innerHTML = '<article class="detail-card full"><h2>Load Error</h2><p>Check the protein UID and API status, then try again.</p></article>';
  }
}

document.addEventListener("DOMContentLoaded", initDetail);
