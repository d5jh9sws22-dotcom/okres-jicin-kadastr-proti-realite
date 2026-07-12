const state = {
  parcels: [],
  sources: [],
  methodology: {},
  mapLayers: { base_layers: [], parcels: [] },
  mlRun: null,
  mlPredictions: [],
  trainingSamples: [],
  atomSamples: [],
  sampleSource: "parcela",
  activeCase: "A",
  activeImage: "ortho",
  verdictFilter: "all",
  riskOnly: false,
  searchQuery: "",
  methodTab: "useful",
};

const verdictReview = new Set(["partial", "mostly", "mismatch", "unknown"]);

const landTypeLabels = {
  ArableGround: "Orná půda",
  Grassland: "Trvalý travní porost",
  Forest: "Lesní pozemek",
  WaterArea: "Vodní plocha",
  OtherArea: "Ostatní plocha",
  BuiltUpArea: "Zastavěná plocha",
  Garden: "Zahrada",
  Orchard: "Ovocný sad",
};

const landTypeIcons = {
  ArableGround: "sprout",
  Grassland: "leaf",
  Forest: "tree",
  WaterArea: "droplet",
  OtherArea: "layers",
  BuiltUpArea: "building",
  Garden: "flower",
  Orchard: "flower",
};

const iconPaths = {
  alert: '<path d="M12 9v4"/><path d="M12 17h.01"/><path d="M10.3 3.9 2.4 17.2A2 2 0 0 0 4.1 20h15.8a2 2 0 0 0 1.7-2.8L13.7 3.9a2 2 0 0 0-3.4 0Z"/>',
  area: '<path d="M4 5h16v14H4z"/><path d="M8 5v14"/><path d="M16 5v14"/><path d="M4 10h16"/><path d="M4 15h16"/>',
  brain: '<path d="M9 3a3 3 0 0 0-3 3v1a3 3 0 0 0 0 6v1a4 4 0 0 0 4 4h1V3Z"/><path d="M15 3a3 3 0 0 1 3 3v1a3 3 0 0 1 0 6v1a4 4 0 0 1-4 4h-1V3Z"/><path d="M8 9h3"/><path d="M13 9h3"/><path d="M8 14h3"/><path d="M13 14h3"/>',
  building: '<path d="M5 20V4h10v16"/><path d="M15 9h4v11"/><path d="M8 8h3"/><path d="M8 12h3"/><path d="M8 16h3"/>',
  chart: '<path d="M4 19V5"/><path d="M4 19h16"/><path d="M8 16v-5"/><path d="M12 16V8"/><path d="M16 16v-9"/>',
  check: '<path d="m5 12 4 4L19 6"/>',
  clipboard: '<path d="M9 4h6l1 2h3v14H5V6h3Z"/><path d="M9 11h6"/><path d="M9 15h4"/>',
  database: '<ellipse cx="12" cy="5" rx="7" ry="3"/><path d="M5 5v6c0 1.7 3.1 3 7 3s7-1.3 7-3V5"/><path d="M5 11v6c0 1.7 3.1 3 7 3s7-1.3 7-3v-6"/>',
  droplet: '<path d="M12 3s6 6.4 6 10a6 6 0 0 1-12 0c0-3.6 6-10 6-10Z"/>',
  file: '<path d="M6 3h8l4 4v14H6Z"/><path d="M14 3v5h5"/><path d="M9 13h6"/><path d="M9 17h4"/>',
  flower: '<path d="M12 12c2-3 6-2 6 1 0 2-2 3-4 2 1 2 0 4-2 4s-3-2-2-4c-2 1-4 0-4-2 0-3 4-4 6-1Z"/><circle cx="12" cy="12" r="1.5"/>',
  gauge: '<path d="M4 15a8 8 0 1 1 16 0"/><path d="m12 15 4-5"/><path d="M7 15h.01"/><path d="M17 15h.01"/>',
  layers: '<path d="m12 3 9 5-9 5-9-5Z"/><path d="m3 12 9 5 9-5"/><path d="m3 16 9 5 9-5"/>',
  leaf: '<path d="M5 19C5 9 12 4 20 4c0 8-5 15-15 15Z"/><path d="M5 19c4-5 8-7 13-10"/>',
  list: '<path d="M8 6h13"/><path d="M8 12h13"/><path d="M8 18h13"/><path d="M3 6h.01"/><path d="M3 12h.01"/><path d="M3 18h.01"/>',
  map: '<path d="m3 6 6-3 6 3 6-3v15l-6 3-6-3-6 3Z"/><path d="M9 3v15"/><path d="M15 6v15"/>',
  pin: '<path d="M12 21s7-5.2 7-11a7 7 0 0 0-14 0c0 5.8 7 11 7 11Z"/><circle cx="12" cy="10" r="2.5"/>',
  route: '<path d="M5 6h4a3 3 0 0 1 0 6H7a3 3 0 0 0 0 6h12"/><circle cx="5" cy="6" r="2"/><circle cx="19" cy="18" r="2"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="m16 16 4 4"/>',
  shield: '<path d="M12 3 20 6v6c0 5-3.4 8-8 9-4.6-1-8-4-8-9V6Z"/><path d="m9 12 2 2 4-5"/>',
  spark: '<path d="M12 2v5"/><path d="M12 17v5"/><path d="m4.9 4.9 3.5 3.5"/><path d="m15.6 15.6 3.5 3.5"/><path d="M2 12h5"/><path d="M17 12h5"/><path d="m4.9 19.1 3.5-3.5"/><path d="m15.6 8.4 3.5-3.5"/>',
  sprout: '<path d="M12 20V9"/><path d="M12 9c-4 0-7-2-8-6 4 0 7 2 8 6Z"/><path d="M12 12c4 0 7-2 8-6-4 0-7 2-8 6Z"/>',
  tree: '<path d="M12 22v-7"/><path d="M8 17h8l-4-5Z"/><path d="M6 13h12L12 4Z"/>',
  warning: '<path d="M12 9v4"/><path d="M12 17h.01"/><path d="M10.3 3.9 2.4 17.2A2 2 0 0 0 4.1 20h15.8a2 2 0 0 0 1.7-2.8L13.7 3.9a2 2 0 0 0-3.4 0Z"/>',
};

const els = {
  stats: document.querySelector("#stats"),
  parcelList: document.querySelector("#parcelList"),
  detailPane: document.querySelector("#detailModule"),
  analysisPane: document.querySelector("#analysisPane"),
  filterEmpty: document.querySelector("#filterEmpty"),
  parcelMapList: document.querySelector("#parcelMapList"),
  parcelSearch: document.querySelector("#parcelSearch"),
  riskOnly: document.querySelector("#riskOnly"),
  verdictFilter: document.querySelector("#verdictFilter"),
  detailCode: document.querySelector("#detailCode"),
  detailTitle: document.querySelector("#detailTitle"),
  detailMeta: document.querySelector("#detailMeta"),
  detailVerdict: document.querySelector("#detailVerdict"),
  prevParcel: document.querySelector("#prevParcel"),
  nextParcel: document.querySelector("#nextParcel"),
  metrics: document.querySelector("#metrics"),
  portfolioChart: document.querySelector("#portfolioChart"),
  mapSummary: document.querySelector("#mapSummary"),
  osmMap: document.querySelector("#osmMap"),
  osmLink: document.querySelector("#osmLink"),
  evidenceImage: document.querySelector("#evidenceImage"),
  evidenceLink: document.querySelector("#evidenceLink"),
  imageCaption: document.querySelector("#imageCaption"),
  officialSummary: document.querySelector("#officialSummary"),
  observedSummary: document.querySelector("#observedSummary"),
  evidenceFlow: document.querySelector("#evidenceFlow"),
  officialState: document.querySelector("#officialState"),
  observedState: document.querySelector("#observedState"),
  finding: document.querySelector("#finding"),
  nextAction: document.querySelector("#nextAction"),
  indicatorList: document.querySelector("#indicatorList"),
  sourceList: document.querySelector("#sourceList"),
  layerList: document.querySelector("#layerList"),
  methodList: document.querySelector("#methodList"),
  mlBadge: document.querySelector("#mlBadge"),
  mlPrediction: document.querySelector("#mlPrediction"),
  mlConfidence: document.querySelector("#mlConfidence"),
  mlExplanation: document.querySelector("#mlExplanation"),
  mlNote: document.querySelector("#mlNote"),
  mlRunGrid: document.querySelector("#mlRunGrid"),
  mlProbabilities: document.querySelector("#mlProbabilities"),
  mlPredictionTable: document.querySelector("#mlPredictionTable"),
  mlCommand: document.querySelector("#mlCommand"),
  mlParams: document.querySelector("#mlParams"),
  sampleForm: document.querySelector("#sampleForm"),
  sampleSource: document.querySelector("#sampleSource"),
  sampleCase: document.querySelector("#sampleCase"),
  sampleLandType: document.querySelector("#sampleLandType"),
  sampleNote: document.querySelector("#sampleNote"),
  atomSampleSummary: document.querySelector("#atomSampleSummary"),
  sampleList: document.querySelector("#sampleList"),
  trainModelButton: document.querySelector("#trainModelButton"),
  trainStatus: document.querySelector("#trainStatus"),
  assessmentForm: document.querySelector("#assessmentForm"),
  assessmentVerdict: document.querySelector("#assessmentVerdict"),
  assessmentConfidence: document.querySelector("#assessmentConfidence"),
  assessmentRisk: document.querySelector("#assessmentRisk"),
  assessmentObserved: document.querySelector("#assessmentObserved"),
  assessmentFinding: document.querySelector("#assessmentFinding"),
  assessmentAction: document.querySelector("#assessmentAction"),
  assessmentAccessibility: document.querySelector("#assessmentAccessibility"),
  assessmentEnvironment: document.querySelector("#assessmentEnvironment"),
  assessmentGeometry: document.querySelector("#assessmentGeometry"),
  assessmentStatus: document.querySelector("#assessmentStatus"),
  toast: document.querySelector("#toast"),
};

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatArea(value) {
  return `${new Intl.NumberFormat("cs-CZ").format(value)} m2`;
}

function formatHa(value) {
  return `${new Intl.NumberFormat("cs-CZ", { maximumFractionDigits: 2 }).format(value / 10000)} ha`;
}

function formatNumber(value, digits = 5) {
  return new Intl.NumberFormat("cs-CZ", { maximumFractionDigits: digits }).format(value);
}

function displayLandType(value) {
  return landTypeLabels[value] || value;
}

function icon(name) {
  const path = iconPaths[name] || iconPaths.file;
  return `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">${path}</svg>`;
}

function iconForLandType(value) {
  return icon(landTypeIcons[value] || "layers");
}

function clampPercent(value) {
  return Math.min(100, Math.max(0, Math.round(value * 100)));
}

function percent(value) {
  return `${clampPercent(value)} %`;
}

function formatDecimal(value, digits = 3) {
  return new Intl.NumberFormat("cs-CZ", { maximumFractionDigits: digits }).format(value);
}

function formatDateTime(value) {
  return new Intl.DateTimeFormat("cs-CZ", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

async function getJson(path) {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(`${path}: ${response.status}`);
  }
  return response.json();
}

async function sendJson(path, payload) {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(`${path}: ${response.status} ${message}`);
  }
  return response.json();
}

async function putJson(path, payload) {
  const response = await fetch(path, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(`${path}: ${response.status} ${message}`);
  }
  return response.json();
}

async function deleteJson(path) {
  const response = await fetch(path, { method: "DELETE" });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(`${path}: ${response.status} ${message}`);
  }
  return response.json();
}

function showToast(message, tone = "info") {
  els.toast.textContent = message;
  els.toast.className = `toast show ${tone}`;
  window.clearTimeout(showToast.timeoutId);
  showToast.timeoutId = window.setTimeout(() => {
    els.toast.className = "toast";
  }, 3600);
}

function decorateStaticIcons() {
  document.querySelectorAll("[data-icon]").forEach((element) => {
    if (element.querySelector(":scope > .icon")) {
      return;
    }
    element.insertAdjacentHTML("afterbegin", icon(element.dataset.icon));
  });
}

function decorateHelpTips(root = document) {
  root.querySelectorAll("[data-help]").forEach((heading) => {
    if (heading.querySelector(":scope > .help-tip")) {
      return;
    }
    const button = document.createElement("button");
    button.type = "button";
    button.className = "help-tip";
    button.textContent = "?";
    button.setAttribute("aria-label", `Nápověda: ${heading.dataset.help}`);
    button.title = heading.dataset.help;
    button.dataset.tooltip = heading.dataset.help;
    heading.append(button);
  });
}

function activeParcel() {
  const parcel = state.parcels.find((item) => item.case_id === state.activeCase);
  if (!parcel) {
    throw new Error(`active parcel not found: ${state.activeCase}`);
  }
  return parcel;
}

function activeMlPrediction() {
  const prediction = state.mlPredictions.find((item) => item.case_id === state.activeCase);
  if (!prediction) {
    throw new Error(`ML prediction not found: ${state.activeCase}`);
  }
  return prediction;
}

function activeMapParcel() {
  const parcel = state.mapLayers.parcels.find((item) => item.case_id === state.activeCase);
  if (!parcel) {
    throw new Error(`map parcel not found: ${state.activeCase}`);
  }
  return parcel;
}

function osmEmbedUrl(center) {
  const span = 0.018;
  const left = center.lon - span;
  const right = center.lon + span;
  const bottom = center.lat - span;
  const top = center.lat + span;
  return `https://www.openstreetmap.org/export/embed.html?bbox=${left}%2C${bottom}%2C${right}%2C${top}&layer=mapnik&marker=${center.lat}%2C${center.lon}`;
}

function osmLinkUrl(center) {
  return `https://www.openstreetmap.org/?mlat=${center.lat}&mlon=${center.lon}#map=${center.zoom}/${center.lat}/${center.lon}`;
}

function renderStats(stats) {
  const items = [
    ["list", "Parcely", stats.parcel_count],
    ["area", "Celkem", `${new Intl.NumberFormat("cs-CZ", { maximumFractionDigits: 2 }).format(stats.total_area_ha)} ha`],
    ["warning", "Ke kontrole", stats.risk_count],
    ["layers", "Druhy", Object.keys(stats.by_land_type).length],
  ];
  els.stats.innerHTML = items
    .map(
      ([iconName, label, value]) =>
        `<div class="stat" title="${escapeHtml(label)} v aktuálním portfoliu">${icon(iconName)}<span>${label}</span><strong>${value}</strong></div>`,
    )
    .join("");
}

function summarizeParcels(key) {
  return state.parcels.reduce((acc, parcel) => {
    const value = parcel[key];
    if (!acc[value]) {
      acc[value] = { count: 0, area: 0 };
    }
    acc[value].count += 1;
    acc[value].area += parcel.area_m2;
    return acc;
  }, {});
}

function renderPortfolioOverview() {
  const totalArea = state.parcels.reduce((sum, parcel) => sum + parcel.area_m2, 0);
  const averageConfidence =
    state.parcels.reduce((sum, parcel) => sum + parcel.confidence, 0) / Math.max(1, state.parcels.length);
  const reviewCount = state.parcels.filter((parcel) => verdictReview.has(parcel.verdict_level)).length;
  const landRows = Object.entries(summarizeParcels("land_type"))
    .sort((a, b) => b[1].area - a[1].area)
    .map(([landType, summary]) => {
      const share = totalArea ? summary.area / totalArea : 0;
      return `
        <div class="viz-row">
          <div class="viz-label">${iconForLandType(landType)}<span>${displayLandType(landType)}</span><strong>${formatHa(summary.area)}</strong></div>
          <div class="viz-track"><span style="width: ${Math.max(3, clampPercent(share))}%"></span></div>
        </div>
      `;
    })
    .join("");
  const verdictRows = Object.entries(summarizeParcels("verdict_level"))
    .sort((a, b) => b[1].count - a[1].count)
    .map(([verdictLevel, summary]) => {
      const share = summary.count / Math.max(1, state.parcels.length);
      const verdict = state.parcels.find((parcel) => parcel.verdict_level === verdictLevel).verdict;
      const iconName = verdictLevel === "match" ? "check" : "warning";
      return `
        <div class="viz-row compact">
          <div class="viz-label">${icon(iconName)}<span>${escapeHtml(verdict)}</span><strong>${summary.count}</strong></div>
          <div class="viz-track"><span style="width: ${Math.max(8, clampPercent(share))}%"></span></div>
        </div>
      `;
    })
    .join("");
  els.portfolioChart.innerHTML = `
    <article class="portfolio-card">
      <h3 data-help="Součet výměr parcel seskupený podle oficiálního druhu pozemku.">${icon("layers")}Druhy podle výměry</h3>
      ${landRows}
    </article>
    <article class="portfolio-card">
      <h3 data-help="Počet parcel v jednotlivých úrovních ručního analytického závěru.">${icon("clipboard")}Závěry analýzy</h3>
      ${verdictRows}
    </article>
    <article class="portfolio-card score-card">
      <h3 data-help="Průměrná ručně zadaná jistota a počet parcel doporučených ke kontrole.">${icon("gauge")}Jistota a kontrola</h3>
      <div class="score-ring" style="--score: ${clampPercent(averageConfidence)}">
        <strong>${percent(averageConfidence)}</strong>
        <span>průměrná jistota</span>
      </div>
      <div class="score-meta">
        <span>${icon("warning")}Ke kontrole: <strong>${reviewCount}</strong></span>
        <span>${icon("check")}Bez zjevného nesouladu: <strong>${state.parcels.length - reviewCount}</strong></span>
      </div>
    </article>
  `;
}

function parcelPassesFilter(parcel) {
  const query = state.searchQuery.trim().toLowerCase();
  if (query) {
    const haystack = [
      parcel.case_id,
      parcel.zoning,
      parcel.municipality,
      parcel.label,
      parcel.national_ref,
      displayLandType(parcel.land_type),
      parcel.official_label,
      parcel.verdict,
      parcel.risk,
    ]
      .join(" ")
      .toLowerCase();
    if (!haystack.includes(query)) {
      return false;
    }
  }
  if (state.riskOnly && parcel.risk === "Nízké") {
    return false;
  }
  if (state.verdictFilter === "match") {
    return parcel.verdict_level === "match";
  }
  if (state.verdictFilter === "review") {
    return verdictReview.has(parcel.verdict_level);
  }
  return true;
}

function visibleParcels() {
  return state.parcels.filter(parcelPassesFilter);
}

function moveActiveParcel(direction) {
  const visible = visibleParcels();
  if (!visible.length) {
    return;
  }
  const currentIndex = visible.findIndex((parcel) => parcel.case_id === state.activeCase);
  const nextIndex = currentIndex === -1 ? 0 : (currentIndex + direction + visible.length) % visible.length;
  state.activeCase = visible[nextIndex].case_id;
  renderAll();
}

function renderParcelList() {
  const filtered = visibleParcels();
  if (filtered.length && !filtered.some((parcel) => parcel.case_id === state.activeCase)) {
    state.activeCase = filtered[0].case_id;
  }
  if (!filtered.length) {
    els.parcelList.innerHTML = `<div class="empty-state rail-empty">Žádná parcela neodpovídá filtru.</div>`;
    return false;
  }
  els.parcelList.innerHTML = filtered
    .map(
      (parcel) => `
        <button class="parcel-card ${parcel.case_id === state.activeCase ? "active" : ""}" type="button" data-case="${parcel.case_id}" aria-pressed="${parcel.case_id === state.activeCase}" title="Vybrat parcelu ${escapeHtml(parcel.case_id)}: ${escapeHtml(parcel.zoning)} ${escapeHtml(parcel.label)}">
          <strong>${iconForLandType(parcel.land_type)}${parcel.case_id}. ${parcel.zoning} ${parcel.label}</strong>
          <span>${parcel.official_label}</span>
          <div class="card-foot">
            <span class="land-chip">${iconForLandType(parcel.land_type)}${displayLandType(parcel.land_type)}</span>
            <span class="risk-chip ${parcel.risk === "Nízké" ? "low" : ""}">${icon(parcel.risk === "Nízké" ? "check" : "warning")}${parcel.risk}</span>
          </div>
        </button>
      `,
    )
    .join("");

  document.querySelectorAll(".parcel-card").forEach((button) => {
    button.addEventListener("click", () => {
      state.activeCase = button.dataset.case;
      renderAll();
      if (window.matchMedia("(max-width: 820px)").matches) {
        els.detailPane.scrollIntoView({ block: "start" });
      }
    });
  });
  return true;
}

function renderDetail() {
  const parcel = activeParcel();
  const mapParcel = activeMapParcel();
  els.detailCode.textContent = `${parcel.national_ref} | S-JTSK ${parcel.reference_x_sjtsk}, ${parcel.reference_y_sjtsk}`;
  els.detailTitle.textContent = `${parcel.zoning}, parcela ${parcel.label}`;
  els.detailMeta.textContent = `${parcel.municipality}, okres ${parcel.district} | import ${parcel.imported_at}`;
  els.detailVerdict.textContent = parcel.verdict;
  els.detailVerdict.className = `verdict-pill ${parcel.verdict_level}`;
  els.prevParcel.disabled = visibleParcels().length <= 1;
  els.nextParcel.disabled = visibleParcels().length <= 1;

  const landUse = parcel.land_use || "neuvedeno";
  const metrics = [
    ["area", "Výměra", `${formatArea(parcel.area_m2)} / ${formatHa(parcel.area_m2)}`],
    [landTypeIcons[parcel.land_type] || "layers", "Druh", displayLandType(parcel.land_type)],
    ["clipboard", "Využití", landUse],
    ["file", "Vlastnictví/LV", parcel.ownership_reference],
    ["pin", "Centroid", `S-JTSK ${formatNumber(parcel.reference_x_sjtsk, 2)}, ${formatNumber(parcel.reference_y_sjtsk, 2)}`],
    ["gauge", "Důvěra", percent(parcel.confidence)],
  ];
  els.metrics.innerHTML = metrics
    .map(
      ([iconName, label, value]) => `
        <div class="metric">
          <span>${icon(iconName)}${label}</span>
          <strong>${value}</strong>
        </div>
      `,
    )
    .join("");

  els.mapSummary.textContent =
    `OSM slouží jako orientační kontext. Parcelní hranice a právní důkaz jsou v CPX overlay a KN/ortofoto výřezech. ` +
    `WGS84 kontext: ${formatNumber(mapParcel.center.lat)}, ${formatNumber(mapParcel.center.lon)}.`;
  const nextMapUrl = osmEmbedUrl(mapParcel.center);
  if (els.osmMap.dataset.url !== nextMapUrl) {
    els.osmMap.src = nextMapUrl;
    els.osmMap.dataset.url = nextMapUrl;
  }
  els.osmLink.href = osmLinkUrl(mapParcel.center);

  const imagePathByMode = {
    ortho: parcel.ortho_image,
    overlay: parcel.overlay_image,
    kn: parcel.kn_image,
  };
  const captionByMode = {
    ortho: "ČÚZK ortofoto WMS, kříž značí referenční bod parcely.",
    overlay: "Ortofoto s hranicí parcely z ČÚZK CPX; kříž značí referenční bod.",
    kn: "ČÚZK katastrální mapa WMS, kříž značí referenční bod parcely.",
  };
  const imagePath = imagePathByMode[state.activeImage];
  els.evidenceImage.src = imagePath;
  els.evidenceImage.alt = `${captionByMode[state.activeImage]} Parcela ${parcel.zoning} ${parcel.label}.`;
  els.evidenceImage.title = captionByMode[state.activeImage];
  els.evidenceLink.href = imagePath;
  els.imageCaption.textContent = captionByMode[state.activeImage];

  els.officialState.textContent = parcel.official_label;
  els.observedState.textContent = parcel.observed_state;
  els.officialSummary.textContent = parcel.official_label;
  els.observedSummary.textContent = parcel.observed_state;
  els.finding.textContent = parcel.finding;
  els.nextAction.textContent = parcel.action;
  renderEvidenceFlow(parcel, predictionLabelForParcel(parcel.case_id));
}

function predictionLabelForParcel(caseId) {
  const prediction = state.mlPredictions.find((item) => item.case_id === caseId);
  if (!prediction) {
    return "Bez predikce";
  }
  return `${prediction.predicted_label}, ${percent(prediction.confidence)}`;
}

function renderEvidenceFlow(parcel, mlLabel) {
  const steps = [
    ["file", "Katastr", parcel.official_label],
    ["map", "Ortofoto + CPX", parcel.observed_state],
    ["brain", "PyTorch", mlLabel],
    [parcel.verdict_level === "match" ? "check" : "warning", "Závěr", parcel.verdict],
  ];
  els.evidenceFlow.innerHTML = steps
    .map(
      ([iconName, label, value], index) => `
        <article class="flow-step ${index === steps.length - 1 ? parcel.verdict_level : ""}">
          <div class="flow-icon">${icon(iconName)}</div>
          <span>${label}</span>
          <strong>${escapeHtml(value)}</strong>
        </article>
      `,
    )
    .join("");
}

function renderParcelMapList() {
  const visibleIds = new Set(visibleParcels().map((parcel) => parcel.case_id));
  els.parcelMapList.innerHTML = state.mapLayers.parcels
    .filter((parcel) => visibleIds.has(parcel.case_id))
    .map(
      (parcel) => `
        <button class="map-card ${parcel.case_id === state.activeCase ? "active" : ""}" type="button" data-case="${parcel.case_id}" aria-pressed="${parcel.case_id === state.activeCase}" title="Zobrazit detail parcely ${escapeHtml(parcel.case_id)}">
          <strong>${icon("pin")}${parcel.case_id}. ${parcel.municipality} ${parcel.label}</strong>
          <span>${displayLandType(parcel.land_type)} | ${parcel.verdict} | ${parcel.risk}</span>
          <small>WGS84 ${formatNumber(parcel.center.lat)}, ${formatNumber(parcel.center.lon)} | S-JTSK ${formatNumber(parcel.center.sjtsk_x, 2)}, ${formatNumber(parcel.center.sjtsk_y, 2)}</small>
        </button>
      `,
    )
    .join("");

  document.querySelectorAll(".map-card").forEach((button) => {
    button.addEventListener("click", () => {
      state.activeCase = button.dataset.case;
      renderAll();
      document.querySelector("#detailModule").scrollIntoView({ block: "start" });
      showToast(`Vybrána parcela ${state.activeCase}.`);
    });
  });
}

function renderIndicators() {
  const parcel = activeParcel();
  const items = [
    [landTypeIcons[parcel.land_type] || "layers", "Katastrální druh", displayLandType(parcel.land_type)],
    ["map", "Interpretace reality", parcel.observed_state],
    [parcel.verdict_level === "match" ? "check" : "warning", "Shoda/nesoulad", `${parcel.verdict} (${percent(parcel.confidence)})`],
    ["route", "Přístupnost", parcel.accessibility_indicator],
    ["shield", "Environmentální/provozní limity", parcel.environment_indicator],
    ["area", "Geometrie a plocha", `${parcel.geometry_indicator} Výměra ${formatArea(parcel.area_m2)}.`],
    ["database", "Zdroj dat", parcel.data_source],
  ];
  els.indicatorList.innerHTML = items
    .map(
      ([iconName, label, value]) => `
        <div class="indicator-row" title="${escapeHtml(label)} pro aktivní parcelu">
          <dt>${icon(iconName)}${label}</dt>
          <dd>${escapeHtml(value)}</dd>
        </div>
      `,
    )
    .join("");
}

function renderMl() {
  const prediction = activeMlPrediction();
  if (!state.mlRun) {
    throw new Error("ML run is missing from API state");
  }

  const confidence = percent(prediction.confidence);
  const entropy = new Intl.NumberFormat("cs-CZ", { maximumFractionDigits: 2 }).format(prediction.entropy);
  els.mlBadge.textContent = prediction.agreement === "agree" ? "shoda" : "kontrola";
  els.mlBadge.className = `ml-badge ${prediction.agreement === "agree" ? "agree" : "review"}`;
  els.mlNote.textContent =
    `${state.mlRun.model_name} (${state.mlRun.framework} ${state.mlRun.torch_version}) používá ${state.mlRun.training_samples} trénovacích parcel a vzorků z ČÚZK ATOM/CPX. ` +
    state.mlRun.note;
  els.mlPrediction.textContent = `${prediction.predicted_label} (${prediction.predicted_land_type})`;
  els.mlConfidence.textContent = `${confidence} / ${entropy}`;
  els.mlExplanation.textContent = prediction.explanation;

  const artifactState = state.mlRun.model_artifact_exists ? "existuje" : "chybí";
  const runItems = [
    ["brain", "Model", state.mlRun.model_name],
    ["file", "Soubor", `${state.mlRun.model_artifact} (${artifactState})`],
    ["spark", "Natrénováno", formatDateTime(state.mlRun.trained_at)],
    ["database", "Vzorky", state.mlRun.training_samples],
    ["chart", "Chyba", formatDecimal(state.mlRun.final_loss, 4)],
    ["gauge", "Přesnost", percent(state.mlRun.final_accuracy)],
  ];
  els.mlRunGrid.innerHTML = runItems
    .map(([iconName, label, value]) => `<div class="ml-run-item"><span>${icon(iconName)}${label}</span><strong>${value}</strong></div>`)
    .join("");

  const probabilityItems = Object.entries(prediction.probabilities)
    .sort((a, b) => b[1] - a[1])
    .map(([landType, value]) => {
      const label = displayLandType(landType);
      const width = Math.max(2, Math.round(value * 100));
      const activeClass = landType === prediction.predicted_land_type ? "active" : "";
      return `
        <div class="prob-row ${activeClass}">
          <div class="prob-label"><span>${iconForLandType(landType)}${label}</span><strong>${percent(value)}</strong></div>
          <div class="prob-track"><span style="width: ${width}%"></span></div>
        </div>
      `;
    })
    .join("");
  els.mlProbabilities.innerHTML = `<h3 data-help="Pravděpodobnosti všech tříd vypočítané posledním během modelu.">${icon("chart")}Rozdělení tříd</h3>${probabilityItems}`;

  els.mlPredictionTable.innerHTML = state.mlPredictions
    .map(
      (item) => `
        <tr class="${item.case_id === state.activeCase ? "active" : ""}">
          <td>${item.case_id}</td>
          <td>${item.predicted_label}</td>
          <td>${percent(item.confidence)}</td>
          <td>${formatDecimal(item.entropy, 2)}</td>
          <td>${item.agreement === "agree" ? "shoda" : "kontrola"}</td>
        </tr>
      `,
    )
    .join("");
  els.mlCommand.textContent = ".venv/bin/python ml/train_pytorch.py";

  const params = state.mlRun.parameters;
  const items = [
    ["Epochy", state.mlRun.epochs, "Kolikrát model prošel ATOM/CPX trénovací tabulkou."],
    ["ATOM vzorky", params.atom_sample_count, "Počet reálných parcel z lokálního ČÚZK ATOM extraktu."],
    ["Skrytá šířka", params.hidden_width, "Velikost vnitřní reprezentace modelu ParcelAtomMLP."],
    ["Dropout", params.dropout_probability, "Náhodně vypíná část neuronů, aby model méně memoroval konkrétní katastrální území."],
    ["Šum atributů", params.numeric_noise_sigma, "Lehce ruší číselné atributy, aby model nebyl citlivý na jednotlivé hodnoty výměry nebo souřadnic."],
    ["Feature dropout", params.feature_dropout_probability, "Občas potlačí část vstupních atributů a ukazuje robustnost trénování."],
    ["Teplota", params.temperature, "Změkčuje pravděpodobnosti, aby nejistota nebyla skrytá."],
  ];
  els.mlParams.innerHTML = items
    .map(([label, value, description]) => `<span>${icon("spark")}<strong>${label}: ${value}</strong>${description}</span>`)
    .join("");

  renderTrainingSamples();
}

function renderTrainingControls() {
  els.sampleSource.value = state.sampleSource;
  if (state.sampleSource === "atom") {
    els.sampleCase.innerHTML = state.atomSamples
      .map(
        (sample) =>
          `<option value="${sample.atom_sample_id}">${sample.atom_sample_id} | ${sample.municipality} ${sample.label} | ${displayLandType(sample.land_type)} | ${formatArea(sample.area_m2)}</option>`,
      )
      .join("");
  } else {
    els.sampleCase.innerHTML = state.parcels
      .map((parcel) => `<option value="${parcel.case_id}">${parcel.case_id}. ${parcel.zoning} ${parcel.label}</option>`)
      .join("");
  }
  els.sampleLandType.innerHTML = Object.entries(landTypeLabels)
    .map(([key, label]) => `<option value="${key}">${label}</option>`)
    .join("");
  syncSampleLandType();
  renderAtomSampleSummary();
}

function selectedAtomSample() {
  return state.atomSamples.find((sample) => sample.atom_sample_id === els.sampleCase.value);
}

function syncSampleLandType() {
  if (state.sampleSource === "atom") {
    const sample = selectedAtomSample();
    if (sample) {
      els.sampleLandType.value = sample.land_type;
      els.sampleLandType.disabled = true;
    }
  } else {
    els.sampleLandType.disabled = false;
  }
}

function renderAtomSampleSummary() {
  const byType = state.atomSamples.reduce((acc, sample) => {
    acc[sample.land_type] = (acc[sample.land_type] || 0) + 1;
    return acc;
  }, {});
  const rows = Object.entries(byType)
    .sort(([left], [right]) => displayLandType(left).localeCompare(displayLandType(right), "cs"))
    .map(([landType, count]) => `<span>${iconForLandType(landType)}${displayLandType(landType)} <strong>${count}</strong></span>`)
    .join("");
  const manualCount = state.trainingSamples.length;
  const trainingTotal = state.atomSamples.length + state.parcels.length + manualCount;
  els.atomSampleSummary.innerHTML = `
    <div class="training-base-grid">
      <article>
        <span>${icon("database")}ATOM/CPX</span>
        <strong>${state.atomSamples.length}</strong>
        <small>Reálné parcely z lokálního ČÚZK INSPIRE ATOM extraktu.</small>
      </article>
      <article>
        <span>${icon("clipboard")}Analytické parcely</span>
        <strong>${state.parcels.length}</strong>
        <small>Ručně posouzené parcely s důkazními výřezy.</small>
      </article>
      <article>
        <span>${icon("spark")}Ruční doplnění</span>
        <strong>${manualCount}</strong>
        <small>Vzorky přidané přes tento formulář.</small>
      </article>
      <article>
        <span>${icon("brain")}Trénovací řádky</span>
        <strong>${trainingTotal}</strong>
        <small>Aktuální vstup modelu ParcelAtomMLP.</small>
      </article>
    </div>
    <p class="training-source-note">
      ČÚZK INSPIRE ATOM CPX poskytuje předpřipravená GML data po katastrálních územích v ZIP souborech.
      Tato aplikace používá lokální S-JTSK extrakt <strong>data/derived/cpx_parcels.csv</strong>.
    </p>
    <div class="atom-type-grid">${rows}</div>
  `;
}

function renderTrainingSamples() {
  renderAtomSampleSummary();
  const baseText =
    `Základ modelu je aktivní: ${state.atomSamples.length} ATOM/CPX vzorků z ČÚZK + ` +
    `${state.parcels.length} analytických parcel. Ruční doplňky jsou volitelné a slouží k ukázce, jak změna trénovací sady ovlivní predikce po spuštění trénování.`;
  if (!state.trainingSamples.length) {
    els.sampleList.innerHTML = `
      <section class="manual-sample-empty">
        <strong>${icon("check")}Bez ručních doplňků</strong>
        <p>${baseText}</p>
      </section>
    `;
    return;
  }
  els.sampleList.innerHTML = `
    <section class="manual-sample-empty has-samples">
      <strong>${icon("spark")}Ruční doplňkové vzorky: ${state.trainingSamples.length}</strong>
      <p>${baseText}</p>
    </section>
    ${state.trainingSamples
      .map(
        (sample) => `
        <article class="sample-item">
          <div>
            <strong>${iconForLandType(sample.land_type)}${sample.source_type === "atom" ? sample.atom_sample_id : sample.case_id} | ${displayLandType(sample.land_type)}</strong>
            <span>${escapeHtml(sample.note)}</span>
            <small>${formatDateTime(sample.created_at)} | ${sample.source_type === "atom" ? `${sample.atom_municipality} ${sample.atom_label}, ${formatArea(sample.atom_area_m2)}` : sample.image_path}</small>
          </div>
          <button type="button" data-sample-id="${sample.id}" title="Odstranit tento ruční vzorek z příštího trénovacího běhu">Smazat</button>
        </article>
      `,
      )
      .join("")}
  `;

  document.querySelectorAll("[data-sample-id]").forEach((button) => {
    button.addEventListener("click", async () => {
      try {
        els.trainStatus.textContent = "Mažu vzorek...";
        await deleteJson(`/api/training-samples/${button.dataset.sampleId}`);
        state.trainingSamples = await getJson("/api/training-samples");
        els.trainStatus.textContent = "Vzorek byl smazán. Pro promítnutí změny znovu spusť trénování.";
        renderTrainingSamples();
        showToast("Trénovací vzorek byl smazán.");
      } catch (error) {
        els.trainStatus.textContent = "Vzorek se nepodařilo smazat.";
        showToast(error.message, "error");
      }
    });
  });
}

function renderSources() {
  els.sourceList.innerHTML = state.sources
    .map(
      (source) => `
        <article class="source-item">
          <strong>${icon("shield")}${source.name}</strong>
          <span>${source.role}</span>
          <span>${source.evidence}</span>
          <a href="${source.url}" target="_blank" rel="noreferrer">${source.url}</a>
        </article>
      `,
    )
    .join("");
}

function renderMapLayers() {
  els.layerList.innerHTML = state.mapLayers.base_layers
    .map((layer) => {
      const href = layer.id === "cpx_overlay" ? activeParcel().overlay_image : layer.url;
      const link = href ? `<a href="${escapeHtml(href)}" target="_blank" rel="noreferrer">Otevřít zdroj nebo důkaz</a>` : "";
      return `
        <article class="source-item">
          <strong>${icon("layers")}${layer.name}</strong>
          <span>${layer.role}</span>
          ${link}
        </article>
      `;
    })
    .join("");
}

function renderAssessmentForm(force = false) {
  const parcel = activeParcel();
  if (!force && els.assessmentForm.dataset.case === parcel.case_id) {
    return;
  }
  els.assessmentForm.dataset.case = parcel.case_id;
  els.assessmentVerdict.value = parcel.verdict_level;
  els.assessmentConfidence.value = Math.round(parcel.confidence * 100);
  els.assessmentRisk.value = parcel.risk;
  els.assessmentObserved.value = parcel.observed_state;
  els.assessmentFinding.value = parcel.finding;
  els.assessmentAction.value = parcel.action;
  els.assessmentAccessibility.value = parcel.accessibility_indicator;
  els.assessmentEnvironment.value = parcel.environment_indicator;
  els.assessmentGeometry.value = parcel.geometry_indicator;
  els.assessmentStatus.textContent = `Upravujete parcelu ${parcel.case_id}: ${parcel.zoning} ${parcel.label}.`;
}

function renderMethodology() {
  const items = state.methodology[state.methodTab] || [];
  els.methodList.innerHTML = items.map((item) => `<li>${item}</li>`).join("");
}

function syncTabs() {
  document.querySelectorAll(".image-tabs button").forEach((button) => {
    const active = button.dataset.image === state.activeImage;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", active);
  });
  document.querySelectorAll(".method-tabs button").forEach((button) => {
    const active = button.dataset.method === state.methodTab;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", active);
  });
  document.querySelectorAll("#verdictFilter button").forEach((button) => {
    const active = button.dataset.filter === state.verdictFilter;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", active);
  });
  els.riskOnly.checked = state.riskOnly;
}

function renderAll() {
  syncTabs();
  const hasVisibleParcel = renderParcelList();
  els.detailPane.hidden = !hasVisibleParcel;
  els.analysisPane.hidden = !hasVisibleParcel;
  els.filterEmpty.hidden = hasVisibleParcel;
  if (!hasVisibleParcel) {
    decorateHelpTips();
    return;
  }
  renderPortfolioOverview();
  renderDetail();
  renderParcelMapList();
  renderIndicators();
  renderMl();
  renderSources();
  renderMapLayers();
  renderMethodology();
  renderAssessmentForm();
  decorateHelpTips();
}

function bindEvents() {
  document.querySelectorAll(".image-tabs button").forEach((button) => {
    button.addEventListener("click", () => {
      state.activeImage = button.dataset.image;
      renderAll();
      showToast(`Zobrazuji vrstvu ${button.textContent}.`);
    });
  });

  document.querySelectorAll(".method-tabs button").forEach((button) => {
    button.addEventListener("click", () => {
      state.methodTab = button.dataset.method;
      renderAll();
    });
  });

  els.verdictFilter.addEventListener("click", (event) => {
    const button = event.target.closest("button");
    if (!button) {
      return;
    }
    state.verdictFilter = button.dataset.filter;
    const visible = state.parcels.filter(parcelPassesFilter);
    if (visible.length && !visible.some((parcel) => parcel.case_id === state.activeCase)) {
      state.activeCase = visible[0].case_id;
    }
    renderAll();
  });

  els.riskOnly.addEventListener("change", () => {
    state.riskOnly = els.riskOnly.checked;
    const visible = state.parcels.filter(parcelPassesFilter);
    if (visible.length && !visible.some((parcel) => parcel.case_id === state.activeCase)) {
      state.activeCase = visible[0].case_id;
    }
    renderAll();
  });

  els.parcelSearch.addEventListener("input", () => {
    state.searchQuery = els.parcelSearch.value;
    renderAll();
  });

  els.prevParcel.addEventListener("click", () => moveActiveParcel(-1));
  els.nextParcel.addEventListener("click", () => moveActiveParcel(1));

  els.sampleSource.addEventListener("change", () => {
    state.sampleSource = els.sampleSource.value;
    renderTrainingControls();
  });

  els.sampleCase.addEventListener("change", syncSampleLandType);

  els.sampleForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      els.trainStatus.textContent = "Přidávám trénovací vzorek...";
      const payload =
        state.sampleSource === "atom"
          ? {
              source: "atom",
              atom_sample_id: els.sampleCase.value,
              land_type: els.sampleLandType.value,
              note: els.sampleNote.value,
            }
          : {
              source: "parcela",
              case_id: els.sampleCase.value,
              land_type: els.sampleLandType.value,
              note: els.sampleNote.value,
            };
      await sendJson("/api/training-samples", payload);
      els.sampleNote.value = "";
      state.trainingSamples = await getJson("/api/training-samples");
      els.trainStatus.textContent = "Vzorek byl přidán. Spusť trénování modelu.";
      renderTrainingSamples();
      showToast("Trénovací vzorek byl přidán.");
    } catch (error) {
      els.trainStatus.textContent = "Vzorek se nepodařilo přidat.";
      showToast(error.message, "error");
    }
  });

  els.assessmentForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const caseId = activeParcel().case_id;
    const submitButton = els.assessmentForm.querySelector('button[type="submit"]');
    submitButton.disabled = true;
    els.assessmentStatus.textContent = "Ukládám závěr analytika...";
    try {
      const updatedParcel = await putJson(`/api/parcels/${caseId}/assessment`, {
        verdict_level: els.assessmentVerdict.value,
        confidence: Number(els.assessmentConfidence.value) / 100,
        risk: els.assessmentRisk.value,
        observed_state: els.assessmentObserved.value,
        finding: els.assessmentFinding.value,
        action: els.assessmentAction.value,
        accessibility_indicator: els.assessmentAccessibility.value,
        environment_indicator: els.assessmentEnvironment.value,
        geometry_indicator: els.assessmentGeometry.value,
      });
      state.parcels = state.parcels.map((parcel) => (parcel.case_id === caseId ? updatedParcel : parcel));
      const [stats, mapLayers] = await Promise.all([getJson("/api/stats"), getJson("/api/map-layers")]);
      state.mapLayers = mapLayers;
      els.assessmentForm.dataset.case = "";
      renderStats(stats);
      renderAll();
      els.assessmentStatus.textContent = "Závěr analytika byl uložen do databáze.";
      showToast("Analytický závěr byl uložen.", "success");
    } catch (error) {
      els.assessmentStatus.textContent = "Závěr se nepodařilo uložit.";
      showToast(error.message, "error");
    } finally {
      submitButton.disabled = false;
    }
  });

  els.trainModelButton.addEventListener("click", async () => {
    els.trainModelButton.disabled = true;
    els.trainStatus.textContent = "Trénuji model, může to trvat přibližně minutu...";
    try {
      const result = await sendJson("/api/ml/train", {});
      state.mlRun = result.run;
      state.mlPredictions = result.predictions;
      state.trainingSamples = result.training_samples;
      els.trainStatus.textContent = "Model byl přetrénován a predikce jsou aktualizované.";
      renderAll();
      showToast("Model byl přetrénován.", "success");
    } catch (error) {
      els.trainStatus.textContent = "Trénování se nepodařilo dokončit.";
      showToast(error.message, "error");
    } finally {
      els.trainModelButton.disabled = false;
    }
  });
}

async function init() {
  const [parcels, sources, methodology, stats, mapLayers, mlRun, mlPredictions, trainingSamples, atomSamples] = await Promise.all([
    getJson("/api/parcels"),
    getJson("/api/sources"),
    getJson("/api/methodology"),
    getJson("/api/stats"),
    getJson("/api/map-layers"),
    getJson("/api/ml/run"),
    getJson("/api/ml/predictions"),
    getJson("/api/training-samples"),
    getJson("/api/atom-samples"),
  ]);
  state.parcels = parcels;
  state.sources = sources;
  state.methodology = methodology;
  state.mapLayers = mapLayers;
  state.mlRun = mlRun;
  state.mlPredictions = mlPredictions;
  state.trainingSamples = trainingSamples;
  state.atomSamples = atomSamples;
  decorateStaticIcons();
  decorateHelpTips();
  renderStats(stats);
  renderTrainingControls();
  bindEvents();
  renderAll();
}

init().catch((error) => {
  document.body.innerHTML = `<main class="app-shell"><section class="topbar glass"><h1>Chyba při načtení aplikace</h1><p>${escapeHtml(error.message)}</p></section></main>`;
});
