export interface ProductPhotos {
  white_background?: string | null;
  ambient?: string | null;
  measures?: string | null;
}

export interface ProductRecord {
  [key: string]: unknown;
}

export interface ProductAttribute {
  label: string;
  value: string;
}

export interface CatalogProduct {
  id: string;
  routeId: string;
  code: string;
  name: string;
  description: string;
  category: string;
  cover: string;
  specs: string;
  photos: ProductPhotos | null;
  attributes: ProductAttribute[];
}

export interface GalleryApiImage {
  name?: string;
  url?: string;
  variant?: number;
}

export interface ProductImagesResponse {
  codigo: string;
  imagens: GalleryApiImage[];
}

export interface GalleryEntry {
  key: string;
  label: string;
  url: string;
}

export type CatalogExportFormat = "csv" | "xlsx" | "json" | "pdf" | "zip";

export interface CatalogExportOptions {
  format: CatalogExportFormat;
  query?: string;
  category?: string;
  code?: string;
}

export interface ErpImportSummary {
  path: string;
  products_imported: number;
  imported_at: string;
}
