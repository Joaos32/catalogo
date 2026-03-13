// @ts-check

(function attachCatalogCore(global) {
  const Catalog = global.Catalog || (global.Catalog = {});

  const API_BASES = ["", "http://127.0.0.1:8000", "http://127.0.0.1:5000"];
  const REQUEST_TIMEOUT_MS = 12000;
  const UI_STATE_STORAGE_KEY = "catalog.ui.v1";

  function escapeSvgText(value) {
    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/\"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function createPlaceholderDataUrl(label, width = 240, height = 240) {
    const safeLabel = escapeSvgText(label).slice(0, 60) || "Imagem";
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" role="img" aria-label="${safeLabel}"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#eef4ff" /><stop offset="100%" stop-color="#d7e7ff" /></linearGradient></defs><rect width="100%" height="100%" fill="url(#g)" /><rect x="1" y="1" width="${width - 2}" height="${height - 2}" fill="none" stroke="#9dbcf2" stroke-width="2" stroke-dasharray="8 7" /><text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" font-family="Manrope, Segoe UI, sans-serif" font-size="${Math.max(13, Math.round(width / 13))}" fill="#2f5aa8">${safeLabel}</text></svg>`;
    return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`;
  }

  function setFallbackImage(event, fallbackUrl) {
    const image = event.currentTarget;
    if (!image || image.dataset.fallbackApplied === "true") return;
    image.dataset.fallbackApplied = "true";
    image.src = fallbackUrl;
  }

  const CARD_FALLBACK_IMAGE = createPlaceholderDataUrl("Sem imagem", 900, 700);
  const DETAIL_FALLBACK_IMAGE = createPlaceholderDataUrl("Sem imagem", 1200, 900);
  const THUMB_FALLBACK_IMAGE = createPlaceholderDataUrl("Sem foto", 240, 240);

  Object.assign(Catalog, {
    API_BASES,
    REQUEST_TIMEOUT_MS,
    UI_STATE_STORAGE_KEY,
    createPlaceholderDataUrl,
    setFallbackImage,
    CARD_FALLBACK_IMAGE,
    DETAIL_FALLBACK_IMAGE,
    THUMB_FALLBACK_IMAGE,
  });
})(window);