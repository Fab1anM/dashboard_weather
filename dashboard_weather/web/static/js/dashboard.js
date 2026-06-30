function updateClock() {
  const el = document.getElementById("header-clock");
  if (!el) return;
  const now = new Date();
  el.textContent = now.toLocaleTimeString("de-DE", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });

  // Date
  const dateEl = document.getElementById("clock-date");
  if (dateEl) {
    dateEl.textContent = now.toLocaleDateString("de-DE", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    });
  }

  // Update last refresh timestamp (inline with countdown)
  const subTimeEl = document.getElementById("clock-sub-time");
  if (subTimeEl) {
    const pageEl = document.querySelector("[data-fetched-at]");
    const fetchedStr = pageEl ? pageEl.dataset.fetchedAt : "";
    if (fetchedStr) {
      const fetched = new Date(fetchedStr);
      subTimeEl.textContent = fetched.toLocaleTimeString("de-DE", {
        hour: "2-digit",
        minute: "2-digit",
      });
    }
  }
}

function applyNightMode() {
  const hour = new Date().getHours();
  const isNight = hour >= 18 || hour < 7;
  document.documentElement.setAttribute("data-theme", isNight ? "dark" : "light");
}

document.addEventListener("DOMContentLoaded", () => {
  applyNightMode();
  // Re-check every minute in case user leaves the page running overnight
  setInterval(applyNightMode, 60 * 1000);

  const refreshIntervalMs = 15 * 60 * 1000;
  let remaining = refreshIntervalMs;
  const subCountdownEl = document.getElementById("clock-sub-countdown");
  const refreshButtonEl = document.getElementById("refresh-button");

  function formatTime(ms) {
    const totalSec = Math.ceil(ms / 1000);
    const min = Math.floor(totalSec / 60);
    const sec = totalSec % 60;
    return `${min}:${sec.toString().padStart(2, "0")}`;
  }

  function tick() {
    remaining -= 1000;
    if (remaining <= 0) {
      if (subCountdownEl) subCountdownEl.textContent = " Aktualisiere\u2026";
      window.location.href = "/?refresh=1";
      return;
    }
      const remainingTime = formatTime(remaining);
      refreshButtonEl.textContent = `wird geladen in [${remainingTime}]`;
    }
  

  window.setInterval(tick, 1000);

  // Update clock every second
  updateClock();
  window.setInterval(updateClock, 1000);

  // Also allow manual refresh via ?refresh=1 param
  const params = new URLSearchParams(window.location.search);
  if (params.get("refresh") === "1") {
    remaining = refreshIntervalMs;
  }
});

// ===== Flight Info Map =====
(function initFlightMap() {
  const mapEl = document.getElementById("map");
  if (!mapEl) return;

  const L = window.L;
  if (!L) return;

  const pageEl = document.querySelector("[data-lat]");
  const centerLat = pageEl ? parseFloat(pageEl.dataset.lat) : 49.7596;
  const centerLng = pageEl ? parseFloat(pageEl.dataset.lng) : 6.6442;

  const map = L.map("map", {
    center: [centerLat, centerLng],
    zoom: 13,
    zoomControl: true,
    attributionControl: true,
  });

  // Base layer: OpenStreetMap
  const osmLayer = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    maxZoom: 19,
  }).addTo(map);

  // Alternative base layers
  const satelliteLayer = L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", {
    attribution: '&copy; Esri',
    maxZoom: 19,
  });

  const topographicLayer = L.tileLayer("https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png", {
    attribution: '&copy; OpenTopoMap',
    maxZoom: 17,
  });

  // Base layers group
  const baseMaps = {
    "Karte": osmLayer,
    "Satellit": satelliteLayer,
    "Topografisch": topographicLayer,
  };

  // ============================================================
  // DIPUL WMS LAYERS (from dipul.de WMS service)
  // ============================================================
  const dipulWmsUrl = "https://uas-betrieb.de/geoservices/dipul/wms";

  // Luftraum-Einschränkungen (ED-R Restricted Areas)
  const restrictedAreas = L.tileLayer.wms(dipulWmsUrl, {
    layers: "flugbeschraenkungsgebiete",
    format: "image/png",
    transparent: true,
    attribution: "\u00a9 dipul.de",
  });

  // Flughäfen
  const airports = L.tileLayer.wms(dipulWmsUrl, {
    layers: "flughaefen",
    format: "image/png",
    transparent: true,
    attribution: "\u00a9 dipul.de",
  });

  // Flugplätze
  const airfields = L.tileLayer.wms(dipulWmsUrl, {
    layers: "flugplaetze",
    format: "image/png",
    transparent: true,
    attribution: "\u00a9 dipul.de",
  });

  // Naturschutzgebiete
  const natureReserves = L.tileLayer.wms(dipulWmsUrl, {
    layers: "naturschutzgebiete",
    format: "image/png",
    transparent: true,
    attribution: "\u00a9 dipul.de",
  });

  // Vogelschutzgebiete
  const birdAreas = L.tileLayer.wms(dipulWmsUrl, {
    layers: "vogelschutzgebiete",
    format: "image/png",
    transparent: true,
    attribution: "\u00a9 dipul.de",
  });

  // Wohngrundstücke (private property)
  const residential = L.tileLayer.wms(dipulWmsUrl, {
    layers: "wohngrundstuecke",
    format: "image/png",
    transparent: true,
    attribution: "\u00a9 dipul.de",
  });

  // Windkraftanlagen
  const windTurbines = L.tileLayer.wms(dipulWmsUrl, {
    layers: "windkraftanlagen",
    format: "image/png",
    transparent: true,
    attribution: "\u00a9 dipul.de",
  });

  // Temporäre Betriebseinschränkungen
  const temporaryRestrictions = L.tileLayer.wms(dipulWmsUrl, {
    layers: "temporaere_betriebseinschraenkungen",
    format: "image/png",
    transparent: true,
    attribution: "\u00a9 dipul.de",
  });

  // Bahnanlagen
  const railway = L.tileLayer.wms(dipulWmsUrl, {
    layers: "bahnanlagen",
    format: "image/png",
    transparent: true,
    attribution: "\u00a9 dipul.de",
  });

  // Autobahnen
  const motorways = L.tileLayer.wms(dipulWmsUrl, {
    layers: "bundesautobahnen",
    format: "image/png",
    transparent: true,
    attribution: "\u00a9 dipul.de",
  });

  // ============================================================
  // Flyover Zone Circle (1 km radius - common drone limit)
  // ============================================================
  const flyoverZone = L.circle([centerLat, centerLng], {
    color: "#ff6b35",
    fillColor: "#ff6b35",
    fillOpacity: 0.08,
    weight: 2,
    dashArray: "5, 10",
  }).addTo(map);

  const flyoverPopup = `
    <div style="font-family: system-ui; font-size: 13px; min-width: 180px;">
      <strong style="color: #ff6b35;">\u26a0 Flyover Zone</strong><br>
      <span style="color: #666;">Max. 1 km Radius vom Startpunkt</span><br>
      <hr style="margin: 6px 0; border: none; border-top: 1px solid #eee;">
      <div style="font-size: 12px; color: #888;">
        <div>\ud83d\udd35 Unter 150m AGL: Erlaubnis</div>
        <div>\ud83d\udfe1 \u00dcber 150m AGL: Sondergenehmigung</div>
        <div>\ud83d\udd34 Sondergebiete: Kontakt BLSV</div>
      </div>
    </div>
  `;
  flyoverZone.bindPopup(flyoverPopup);

  // ============================================================
  // AIRPORT MARKERS
  // ============================================================
  const airportsNearTrier = [
    { lat: 49.8033, lng: 6.6108, name: "Flughafen Triers", type: "commercial", iata: "TXF" },
    { lat: 50.0661, lng: 6.7708, name: "Flughafen Frankfurth-Hahn", type: "international", iata: "HHN" },
    { lat: 50.2253, lng: 6.1280, name: "Flughafen Köln/Bonn", type: "international", iata: "CGN" },
    { lat: 49.6128, lng: 7.2756, name: "Flugplatz Bitburg", type: "military/civilian", iata: "" },
    { lat: 50.4414, lng: 6.7756, name: "Flugplatz Koblenz-Most", type: "aerodrome", iata: "" },
    { lat: 49.6690, lng: 6.9560, name: "Segelfluggelände Trier-Manderscheid", type: "glider", iata: "" },
  ];

  function getAirportIcon(type) {
    const colors = {
      commercial: "#e74c3c",
      international: "#c0392b",
      military: "#2c3e50",
      aerodrome: "#3498db",
      glider: "#27ae60",
      default: "#f39c12",
    };
    const color = colors[type] || colors.default;
    return L.divIcon({
      className: "airport-marker",
      html: `<div style="
        background: ${color};
        width: 28px;
        height: 28px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: bold;
        font-size: 14px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.3);
        border: 2px solid white;
      ">✈</div>`,
      iconSize: [28, 28],
      iconAnchor: [14, 14],
    });
  }

  const airportMarkers = L.layerGroup();
  airportsNearTrier.forEach((airport) => {
    const marker = L.marker([airport.lat, airport.lng], {
      icon: getAirportIcon(airport.type),
    });

    const typeLabels = {
      commercial: "Commercial",
      international: "International",
      military: "Military",
      aerodrome: "Aerodrome",
      glider: "Glider Airport",
    };

    const popup = `
      <div style="font-family: system-ui; font-size: 13px; min-width: 200px;">
        <strong style="font-size: 15px;">${airport.name}</strong>
        ${airport.iata ? `<br><span style="color: #888; font-size: 11px;">IATA: ${airport.iata}</span>` : ""}
        <hr style="margin: 6px 0; border: none; border-top: 1px solid #eee;">
        <div style="font-size: 12px; color: #666;">
          <div>Typ: <strong>${typeLabels[airport.type] || airport.type}</strong></div>
          <div>Lat: ${airport.lat.toFixed(4)}° N</div>
          <div>Lng: ${airport.lng.toFixed(4)}° E</div>
          <hr style="margin: 4px 0; border: none; border-top: 1px solid #eee;">
          <div style="color: #e74c3c; font-size: 11px;">
            \u26a0 Mindestabstand: 5 km (bei kontrolliertem Luftraum)
          </div>
        </div>
      </div>
    `;
    marker.bindPopup(popup);
    airportMarkers.addLayer(marker);
  });

  // ============================================================
  // DRONE ZONE INFO (UAS regulations)
  // ============================================================
  const zoneInfo = L.layerGroup();

  // Add info marker for UAS categories
  const droneInfo = L.marker([centerLat + 0.02, centerLng + 0.02], {
    icon: L.divIcon({
      className: "drone-info",
      html: `<div style="
        background: #3498db;
        color: white;
        padding: 4px 8px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: bold;
        white-space: nowrap;
        box-shadow: 0 2px 6px rgba(0,0,0,0.3);
        border: 2px solid white;
      ">\ud83d\udef8 UAS Zone Info</div>`,
      iconSize: [100, 24],
      iconAnchor: [50, 12],
    }),
  });

  const dronePopup = `
    <div style="font-family: system-ui; font-size: 13px; min-width: 240px;">
      <strong style="color: #3498db;">\ud83d\udef8 UAS-Regulierung Deutschland</strong>
      <hr style="margin: 6px 0; border: none; border-top: 1px solid #eee;">
      <div style="font-size: 12px;">
        <div style="margin: 4px 0;"><strong>Offene Kategorie:</strong></div>
        <div style="margin-left: 12px; color: #666;">
          \u2022 Unter 120 m AGL<br>
          \u2022 Nicht über besiedeltem Gebiet<br>
          \u2022 Sichtkontakt erforderlich
        </div>
        <div style="margin: 8px 0 4px;"><strong>Geworbene Kategorie:</strong></div>
        <div style="margin-left: 12px; color: #666;">
          \u2022 Für Risiken über Personen<br>
          \u2022 Spezielle Zulassung erforderlich
        </div>
        <div style="margin: 8px 0 4px;"><strong>Spezifische Kategorie:</strong></div>
        <div style="margin-left: 12px; color: #666;">
          \u2022 A2/CMS oder SORA-Ansatz<br>
          \u2022 Risiko-Bewertung notwendig
        </div>
      </div>
    </div>
  `;
  droneInfo.bindPopup(dronePopup);
  zoneInfo.addLayer(droneInfo);

  // ============================================================
  // LAYER CONTROL
  // ============================================================
  const overlayMaps = {
    "\u2708 Flughäfen": airports,
    "\ud83c\udf1e Flugplätze": airfields,
    "\u26a0 Luftraum-Einschränkungen": restrictedAreas,
    "\ud83c\udf33 Naturschutzgebiete": natureReserves,
    "\ud83d\udc26 Vogelschutzgebiete": birdAreas,
    "\ud83c\udfe0 Wohngrundstücke": residential,
    "\ud83c\udf2c Windkraftanlagen": windTurbines,
    "\u23f3 Temporäre Einschränkungen": temporaryRestrictions,
    "\ud83d\ude86 Bahnanlagen": railway,
    "\ud83d\udee3 Autobahnen": motorways,
  };

  // Add all layers to control
  Object.values(overlayMaps).forEach((layer) => layer.addTo(map));

  L.control.layers(baseMaps, overlayMaps, {
    position: "topright",
    collapsed: false,
  }).addTo(map);

  // ============================================================
  // SCALE BAR & ZOOM INFO
  // ============================================================
  L.control.scale({
    position: "bottomleft",
    imperial: false,
    maxWidth: 150,
  }).addTo(map);

  // Save zoom/center to localStorage whenever user pans or zooms
  map.on("moveend zoomend", function() {
    var zoom = map.getZoom();
    var center = map.getCenter();
    try {
      localStorage.setItem("dwl_map_zoom", zoom);
      localStorage.setItem("dwl_map_center", center.lat + "," + center.lng);
    } catch(e) {}
  });

  // Restore zoom/center from localStorage on load
  try {
    var savedZoom = parseInt(localStorage.getItem("dwl_map_zoom"), 10);
    var savedCenter = localStorage.getItem("dwl_map_center");
    if (savedZoom && !isNaN(savedZoom) && savedCenter) {
      var parts = savedCenter.split(",");
      if (parts.length === 2) {
        var savedLat = parseFloat(parts[0]);
        var savedLng = parseFloat(parts[1]);
        if (!isNaN(savedLat) && !isNaN(savedLng)) {
          map.setView([savedLat, savedLng], savedZoom);
        }
      }
    }
  } catch(e) {}

  // ============================================================
  // FIX MAP SIZING
  // ============================================================
  setTimeout(() => map.invalidateSize(), 300);

})();