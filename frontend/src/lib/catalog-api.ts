import { API_BASES, REQUEST_TIMEOUT_MS } from "./catalog-core";
import type {
  CatalogExportOptions,
  ErpImportSummary,
  ProductImagesResponse,
  ProductPhotos,
  ProductRecord,
} from "../types";

let activeApiOrigin: string | null = null;

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object";
}

function resolveBaseOrigin(base: string): string {
  if (!base) return window.location.origin;
  return new URL(base, window.location.origin).origin;
}

export function getActiveApiOrigin(): string {
  return activeApiOrigin || window.location.origin;
}

export function absolutizeApiUrl(value: string): string {
  const url = String(value || "").trim();
  if (!url) return "";
  if (/^(https?:)?\/\//i.test(url) || url.startsWith("data:") || url.startsWith("blob:")) {
    return url;
  }
  if (url.startsWith("/")) {
    return new URL(url, getActiveApiOrigin()).toString();
  }
  return url;
}

export function buildCatalogExportUrl(options: CatalogExportOptions): string {
  return buildCatalogExportUrlForBase(getActiveApiOrigin(), options);
}

function buildCatalogExportUrlForBase(baseOrigin: string, options: CatalogExportOptions): string {
  const url = new URL("/catalog/export", baseOrigin);
  url.searchParams.set("format", options.format);

  const query = String(options.query || "").trim();
  const category = String(options.category || "").trim();
  const code = String(options.code || "").trim();

  if (query) url.searchParams.set("query", query);
  if (category) url.searchParams.set("category", category);
  if (code) url.searchParams.set("code", code);

  return url.toString();
}

function parseDownloadFilename(response: Response, fallbackName: string): string {
  const header = response.headers.get("content-disposition") || "";
  const utf8Match = header.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match?.[1]) {
    return decodeURIComponent(utf8Match[1]);
  }

  const plainMatch = header.match(/filename="([^"]+)"/i) || header.match(/filename=([^;]+)/i);
  if (plainMatch?.[1]) {
    return plainMatch[1].trim().replace(/^"|"$/g, "");
  }

  return fallbackName;
}

function fallbackExportFilename(options: CatalogExportOptions): string {
  const suffix = options.format;
  if (options.code) return `produto-${options.code}.${suffix}`;
  return `catalogo-produtos.${suffix}`;
}

function sanitizeDownloadName(value: string, fallback: string): string {
  const normalized = String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-zA-Z0-9._-]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-+|-+$/g, "");
  return normalized || fallback;
}

function inferExtensionFromUrl(url: string, blobType = ""): string {
  try {
    const parsed = new URL(url, window.location.origin);
    const pathname = parsed.pathname || "";
    const match = pathname.match(/\.([a-zA-Z0-9]{2,5})$/);
    if (match?.[1]) {
      return `.${match[1].toLowerCase()}`;
    }
  } catch {
    // ignora URL invalida e aplica fallback por tipo MIME
  }

  const mimeMap: Record<string, string> = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/bmp": ".bmp",
    "image/tiff": ".tif",
  };
  return mimeMap[blobType] || ".jpg";
}

function triggerBrowserDownload(url: string, filename: string): void {
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.rel = "noopener";
  document.body.appendChild(link);
  link.click();
  link.remove();
}

export async function downloadCatalogExport(options: CatalogExportOptions): Promise<void> {
  let lastError: unknown = null;

  for (const base of API_BASES) {
    const targetUrl = buildCatalogExportUrlForBase(resolveBaseOrigin(base), options);

    try {
      const response = await fetchWithTimeout(targetUrl);
      if (!response.ok) {
        lastError = new Error(`Resposta nao-ok para ${targetUrl}: ${response.status}`);
        continue;
      }

      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = objectUrl;
      link.download = parseDownloadFilename(response, fallbackExportFilename(options));
      link.rel = "noopener";
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
      activeApiOrigin = resolveBaseOrigin(base);
      return;
    } catch (error) {
      lastError = error;
      console.warn(`Falha ao baixar exportacao em ${targetUrl}. Tentando proxima base.`);
    }
  }

  console.error("Todas as bases falharam na exportacao do catalogo.", lastError);
  throw lastError instanceof Error ? lastError : new Error("Nao foi possivel exportar o catalogo.");
}

export async function downloadImageFile(url: string, filenameBase: string): Promise<void> {
  const targetUrl = absolutizeApiUrl(url);
  const safeBase = sanitizeDownloadName(filenameBase, "imagem-produto");

  try {
    const response = await fetchWithTimeout(targetUrl);
    if (!response.ok) {
      throw new Error(`Resposta nao-ok para ${targetUrl}: ${response.status}`);
    }

    const blob = await response.blob();
    const extension = inferExtensionFromUrl(targetUrl, blob.type);
    const objectUrl = URL.createObjectURL(blob);
    triggerBrowserDownload(objectUrl, `${safeBase}${extension}`);
    window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
  } catch (error) {
    console.warn(`Falha ao baixar imagem em ${targetUrl}. Abrindo fallback do navegador.`, error);
    const extension = inferExtensionFromUrl(targetUrl);
    triggerBrowserDownload(targetUrl, `${safeBase}${extension}`);
  }
}

async function fetchWithTimeout(url: string, init?: RequestInit): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    return await fetch(url, { ...(init || {}), signal: controller.signal });
  } finally {
    window.clearTimeout(timeoutId);
  }
}

export async function fetchFromBases<T>(buildUrl: (base: string) => string): Promise<T | null> {
  let lastError: unknown = null;

  for (const base of API_BASES) {
    const targetUrl = buildUrl(base);
    try {
      const response = await fetchWithTimeout(targetUrl);
      if (!response.ok) {
        if (response.status !== 404) {
          console.warn(`Resposta nao-ok para ${targetUrl}: ${response.status}`);
        }
        continue;
      }
      const payload = (await response.json()) as T;
      activeApiOrigin = resolveBaseOrigin(base);
      return payload;
    } catch (error) {
      lastError = error;
      console.warn(`Falha ao consultar ${targetUrl}. Tentando proxima base.`);
    }
  }

  if (lastError) {
    console.error("Todas as bases falharam na consulta da API.", lastError);
  }
  return null;
}

export async function postJsonToBases<T>(
  buildUrl: (base: string) => string,
  payload: unknown
): Promise<T | null> {
  let lastError: unknown = null;

  for (const base of API_BASES) {
    const targetUrl = buildUrl(base);
    try {
      const response = await fetchWithTimeout(targetUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        const details = await response.text();
        console.warn(`Resposta nao-ok para ${targetUrl}: ${response.status} ${details}`);
        continue;
      }
      const parsed = (await response.json()) as T;
      activeApiOrigin = resolveBaseOrigin(base);
      return parsed;
    } catch (error) {
      lastError = error;
      console.warn(`Falha ao enviar dados para ${targetUrl}. Tentando proxima base.`);
    }
  }

  if (lastError) {
    console.error("Todas as bases falharam no envio para a API.", lastError);
  }
  return null;
}

function normalizePhotos(payload: unknown): ProductPhotos | null {
  if (!isRecord(payload)) return null;
  const whiteBackground = payload.white_background;
  const ambient = payload.ambient;
  const measures = payload.measures;

  if (
    typeof whiteBackground !== "string" &&
    typeof ambient !== "string" &&
    typeof measures !== "string"
  ) {
    return null;
  }

  return {
    white_background: typeof whiteBackground === "string" ? whiteBackground : null,
    ambient: typeof ambient === "string" ? ambient : null,
    measures: typeof measures === "string" ? measures : null,
  };
}

export async function fetchProducts(): Promise<ProductRecord[]> {
  const payload = await fetchFromBases<unknown>((base) => `${base}/catalog/local/produtos`);
  return Array.isArray(payload) ? (payload as ProductRecord[]) : [];
}

export async function fetchPhotosByCode(code: string): Promise<ProductPhotos | null> {
  const payload = await fetchFromBases<unknown>(
    (base) => `${base}/catalog/photos?code=${encodeURIComponent(code)}`
  );
  return normalizePhotos(payload);
}

export async function fetchImagesByCode(code: string): Promise<ProductImagesResponse | null> {
  const payload = await fetchFromBases<unknown>(
    (base) => `${base}/catalog/produtos/${encodeURIComponent(code)}/imagens`
  );

  if (!isRecord(payload)) return null;
  const codigo = payload.codigo;
  const imagens = payload.imagens;
  if (typeof codigo !== "string" || !Array.isArray(imagens)) {
    return null;
  }

  return {
    codigo,
    imagens: imagens.filter((image) => isRecord(image)) as ProductImagesResponse["imagens"],
  };
}

export async function importErpCatalog(payload: unknown): Promise<ErpImportSummary | null> {
  return postJsonToBases<ErpImportSummary>((base) => `${base}/catalog/erp/import`, payload);
}
