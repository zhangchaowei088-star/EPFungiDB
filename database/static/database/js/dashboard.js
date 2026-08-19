const endpoints = {
  summary: "/api/summary/",
  samples: "/api/samples/",
  proteins: "/api/proteins/",
  kegg: "/api/kegg-pathway-members/",
  features: "/api/pathogenicity-features/",
};

function formatNumber(value) {
  if (value === null || value === undefined || value === "") return "...";
  return new Intl.NumberFormat("en-US").format(Math.round(Number(value)));
}

function formatCompact(value) {
  if (value === null || value === undefined || value === "") return "...";
  return new Intl.NumberFormat("en-US", {
    notation: Number(value) >= 1000000 ? "compact" : "standard",
    maximumFractionDigits: Number(value) >= 1000000 ? 1 : 0,
  }).format(Number(value));
}

function formatPercent(value, digits = 1) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "...";
  return `${Number(value).toFixed(digits)}%`;
}

function formatAnimated(value, format, digits = 0) {
  if (format === "percent") return `${value.toFixed(digits)}%`;
  if (format === "compact") return formatCompact(value);
  return formatNumber(value);
}

async function getJson(url) {
  const response = await fetch(url, { headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  return response.json();
}

function setText(selector, text) {
  const node = document.querySelector(selector);
  if (node) node.textContent = text;
}

function initNavbar() {
  const navbar = document.getElementById("navbar");
  const menuButton = document.getElementById("menu-button");
  const navLinks = document.getElementById("nav-links");
  if (!navbar) return;

  const onScroll = () => {
    navbar.classList.toggle("is-scrolled", window.scrollY > 38);
  };
  onScroll();
  window.addEventListener("scroll", onScroll, { passive: true });

  if (menuButton && navLinks) {
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
}

function initSearch() {
  const form = document.getElementById("global-search");
  const input = document.getElementById("search-query");
  if (!form || !input) return;

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const data = new FormData(form);
    const target = data.get("target") || "samples";
    const query = input.value.trim();
    if (!query) {
      input.focus();
      return;
    }

    const encoded = encodeURIComponent(query);
    const url = target === "samples"
      ? `${endpoints.samples}?search=${encoded}`
      : target === "proteins"
        ? `${endpoints.proteins}?search=${encoded}`
        : target === "kegg"
          ? `${endpoints.kegg}?search=${encoded}`
          : `${endpoints.features}?search=${encoded}`;

    window.location.href = url;
  });
}

function initSpores() {
  const canvas = document.getElementById("spore-canvas");
  if (!(canvas instanceof HTMLCanvasElement)) return;

  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  let width = 0;
  let height = 0;
  let spores = [];
  let frameId = 0;

  const resize = () => {
    const rect = canvas.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    width = Math.max(1, Math.floor(rect.width));
    height = Math.max(1, Math.floor(rect.height));
    canvas.width = Math.floor(width * dpr);
    canvas.height = Math.floor(height * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    const count = width < 700 ? 34 : 64;
    spores = Array.from({ length: count }, () => ({
      x: Math.random() * width,
      y: Math.random() * height,
      r: 1.2 + Math.random() * 2.7,
      vx: (Math.random() - 0.5) * 0.34,
      vy: -(0.16 + Math.random() * 0.46),
      alpha: 0.12 + Math.random() * 0.42,
      phase: Math.random() * Math.PI * 2,
    }));
  };

  const draw = (time) => {
    ctx.clearRect(0, 0, width, height);
    for (const spore of spores) {
      spore.x += spore.vx + Math.sin(time * 0.0008 + spore.phase) * 0.22;
      spore.y += spore.vy;

      if (spore.y < -10) {
        spore.y = height + 10;
        spore.x = Math.random() * width;
      }
      if (spore.x < -20) spore.x = width + 20;
      if (spore.x > width + 20) spore.x = -20;

      const glow = ctx.createRadialGradient(spore.x, spore.y, 0, spore.x, spore.y, spore.r * 3);
      glow.addColorStop(0, `rgba(134,239,172,${spore.alpha})`);
      glow.addColorStop(1, "rgba(134,239,172,0)");
      ctx.beginPath();
      ctx.arc(spore.x, spore.y, spore.r * 3, 0, Math.PI * 2);
      ctx.fillStyle = glow;
      ctx.fill();

      ctx.beginPath();
      ctx.arc(spore.x, spore.y, spore.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(220,255,232,${Math.min(0.82, spore.alpha * 1.6)})`;
      ctx.fill();
    }
    frameId = requestAnimationFrame(draw);
  };

  resize();
  window.addEventListener("resize", resize, { passive: true });
  frameId = requestAnimationFrame(draw);

  document.addEventListener("visibilitychange", () => {
    if (document.hidden) cancelAnimationFrame(frameId);
    else frameId = requestAnimationFrame(draw);
  });
}

function metricTemplate(item, index) {
  const progress = Math.min(100, Math.max(0, item.percent));

  return `
    <article class="metric-card">
      <div class="metric-top">
        <div class="metric-value" data-target="${item.target}" data-format="${item.format}" data-digits="${item.digits || 0}" data-delay="${index * 120}">
          ${formatAnimated(0, item.format, item.digits || 0)}
        </div>
        <span class="metric-chip">${item.chip}</span>
      </div>
      <div>
        <h3>${item.label}</h3>
        <p>${item.sublabel}</p>
        <div class="metric-bar" aria-hidden="true"><span data-progress="${progress}" data-delay="${index * 120}"></span></div>
      </div>
    </article>
  `;
}

function animateNumber(node, target, format, digits, duration = 1500, delay = 0) {
  window.setTimeout(() => {
    const start = performance.now();
    const step = (now) => {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      node.textContent = formatAnimated(target * eased, format, digits);
      if (progress < 1) requestAnimationFrame(step);
      else node.textContent = formatAnimated(target, format, digits);
    };
    requestAnimationFrame(step);
  }, delay);
}

function animateStatsOnce() {
  const section = document.getElementById("stats");
  if (!section) return;

  const run = () => {
    if (section.dataset.animated === "1") return;
    section.dataset.animated = "1";

    document.querySelectorAll(".metric-bar span").forEach((bar) => {
      const delay = Number(bar.dataset.delay || 0);
      window.setTimeout(() => {
        bar.style.width = `${bar.dataset.progress || 0}%`;
      }, delay);
    });

    document.querySelectorAll(".metric-value, [data-countup='true']").forEach((node) => {
      animateNumber(
        node,
        Number(node.dataset.target || 0),
        node.dataset.format || "number",
        Number(node.dataset.digits || 0),
        1600,
        Number(node.dataset.delay || 0),
      );
    });
  };

  const observer = new IntersectionObserver((entries) => {
    if (entries.some((entry) => entry.isIntersecting)) {
      run();
      observer.disconnect();
    }
  }, { threshold: 0.22 });
  observer.observe(section);
}

function updateRings(summary) {
  const grid = document.getElementById("ring-grid");
  if (!grid) return;

  const sourceCount = (summary.annotation_sources || []).reduce((sum, item) => sum + Number(item.source_count || 0), 0);
  const sampleCount = Number(summary.sample_count || 0);
  const fullReady = Number(summary.ready_full_analysis || 0);
  const proteinCount = Number(summary.total_proteins || 0);
  const geneCount = Number(summary.total_genes || 0);
  const maxRecords = Math.max(1, geneCount, proteinCount);

  const items = [
    {
      target: Number(summary.species_count || 0),
      format: "number",
      label: "Fungal Species",
      sublabel: `${formatNumber(summary.genus_count)} genera`,
      chip: "Taxonomy",
      percent: Math.min(100, Number(summary.species_count || 0) / Math.max(1, sampleCount) * 100),
    },
    {
      target: sampleCount,
      format: "number",
      label: "Genome Samples",
      sublabel: "curated strains",
      chip: "Samples",
      percent: Math.min(100, sampleCount / Math.max(1, sampleCount) * 100),
    },
    {
      target: geneCount,
      format: "compact",
      label: "Gene Records",
      sublabel: "coding genes",
      chip: "Genes",
      percent: Math.min(100, geneCount / maxRecords * 100),
    },
    {
      target: proteinCount,
      format: "compact",
      label: "Proteins",
      sublabel: "protein entries",
      chip: "Proteome",
      percent: Math.min(100, proteinCount / maxRecords * 100),
    },
    {
      target: Number(summary.avg_busco_complete_pct || 0),
      format: "percent",
      digits: 0,
      label: "BUSCO Complete",
      sublabel: "average quality",
      chip: "Quality",
      percent: Number(summary.avg_busco_complete_pct || 0),
    },
    {
      target: sourceCount,
      format: "number",
      label: "Data Sources",
      sublabel: "annotation types",
      chip: "Evidence",
      percent: Math.min(100, sourceCount * 12.5),
    },
  ];

  grid.innerHTML = items.map(metricTemplate).join("");

  const featured = [
    ["ready_full_analysis", fullReady, "number", 0],
    ["avg_busco_complete_pct", Number(summary.avg_busco_complete_pct || 0), "percent", 1],
    ["max_bgc_count", Number(summary.max_bgc_count || 0), "number", 0],
    ["annotation_source_count", sourceCount, "number", 0],
  ];
  featured.forEach(([key, target, format, digits], index) => {
    const node = document.querySelector(`[data-feature="${key}"]`);
    if (!node) return;
    node.textContent = formatAnimated(0, format, digits);
    node.dataset.countup = "true";
    node.dataset.target = String(target);
    node.dataset.format = format;
    node.dataset.digits = String(digits);
    node.dataset.delay = String(360 + index * 100);
  });

  animateStatsOnce();
}

async function loadDashboard() {
  try {
    const summary = await getJson(endpoints.summary);
    updateRings(summary);
  } catch (error) {
    const grid = document.getElementById("ring-grid");
    if (grid) grid.innerHTML = '<div class="load-error">Dashboard data unavailable.</div>';
  }
}

document.addEventListener("DOMContentLoaded", () => {
  initNavbar();
  initSearch();
  initSpores();
  loadDashboard();
});
