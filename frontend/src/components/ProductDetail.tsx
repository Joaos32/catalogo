import { useEffect, useState } from "react";

import ExportActions from "./ExportActions";
import type { CatalogExportFormat, CatalogProduct, GalleryEntry, ProductPhotos } from "../types";
import { DETAIL_FALLBACK_IMAGE, THUMB_FALLBACK_IMAGE, setFallbackImage } from "../lib/catalog-core";
import { downloadImageFile } from "../lib/catalog-api";
import { buildGalleryEntries } from "../lib/catalog-products";

interface ProductDetailProps {
  item: CatalogProduct;
  photos?: ProductPhotos | null;
  galleryEntries: GalleryEntry[];
  onBack: () => void;
  onExport: (format: CatalogExportFormat) => void;
}

const ATTRIBUTE_LABEL_MAP: Record<string, string> = {
  CODPROD: "Código",
  CODAUXILIAR: "Código de barras",
  NBM: "NCM",
  PERCIPIVENDA: "IPI",
};

function getAttributeDisplayLabel(label: string): string {
  const normalized = String(label || "").trim().toUpperCase();
  return ATTRIBUTE_LABEL_MAP[normalized] || label;
}

export default function ProductDetail({
  item,
  photos,
  galleryEntries,
  onBack,
  onExport,
}: ProductDetailProps): JSX.Element {
  const [activeIndex, setActiveIndex] = useState(0);
  const gallery =
    galleryEntries && galleryEntries.length > 0 ? galleryEntries : buildGalleryEntries(item, photos, []);
  const activeImage = gallery[activeIndex] || gallery[0] || null;

  useEffect(() => {
    setActiveIndex(0);
  }, [item.routeId]);

  const downloadSelectedImage = () => {
    if (!activeImage?.url) return;
    void downloadImageFile(activeImage.url, `${item.code}-${activeImage.label}`);
  };

  const downloadAllPhotos = () => {
    onExport("zip");
  };

  return (
    <section className="detail-panel" aria-label="Detalhes do produto">
      <button type="button" className="detail-back" onClick={onBack}>
        Voltar ao catálogo
      </button>

      <div className="detail-layout">
        <div className="detail-media">
          <img
            src={activeImage?.url || DETAIL_FALLBACK_IMAGE}
            alt={item.name || "Produto"}
            width="1200"
            height="900"
            decoding="async"
            onError={(event) => setFallbackImage(event, DETAIL_FALLBACK_IMAGE)}
          />
        </div>

        <aside className="detail-meta">
          <h2>{item.name || "Produto"}</h2>
          <div className="detail-tags">
            <span className="detail-tag">Código: {item.code}</span>
            <span className="detail-tag">{item.category || "Sem categoria"}</span>
          </div>
          <ExportActions
            title="Baixar este produto"
            note="Exporte em planilha, PDF, JSON ou ZIP com as fotos disponíveis."
            onExport={onExport}
            compact
          />
          <p>{item.description || "Descrição indisponível para este produto."}</p>
          <p>{item.specs || "Sem especificações técnicas cadastradas."}</p>
          {item.attributes.length > 0 && (
            <dl className="detail-attributes">
              {item.attributes.map((attribute) => (
                <div key={`${attribute.label}-${attribute.value}`} className="detail-attribute-item">
                  <dt>{getAttributeDisplayLabel(attribute.label)}</dt>
                  <dd>{attribute.value}</dd>
                </div>
              ))}
            </dl>
          )}
        </aside>
      </div>

      <div className="detail-gallery-toolbar">
        <div className="detail-gallery-copy">
          <strong>Outras fotos</strong>
          <span>Selecione uma imagem da galeria e baixe a foto atual ou todas em pacote.</span>
        </div>
        <div className="detail-gallery-actions">
          <button
            type="button"
            className="detail-action-button"
            onClick={downloadSelectedImage}
            disabled={!activeImage?.url}
          >
            Baixar foto selecionada
          </button>
          <button type="button" className="detail-action-button is-secondary" onClick={downloadAllPhotos}>
            Baixar todas em ZIP
          </button>
        </div>
      </div>

      <div className="detail-gallery">
        {gallery.map((image, idx) => (
          <button
            key={image.key || `${image.label}-${idx}`}
            type="button"
            className={`detail-gallery-btn ${idx === activeIndex ? "is-active" : ""}`}
            onClick={() => setActiveIndex(idx)}
            aria-pressed={idx === activeIndex}
            aria-label={`Selecionar ${image.label}`}
          >
            <img
              src={image.url || THUMB_FALLBACK_IMAGE}
              alt={image.label}
              width="240"
              height="240"
              loading="lazy"
              decoding="async"
              onError={(event) => setFallbackImage(event, THUMB_FALLBACK_IMAGE)}
            />
            <span>{image.label}</span>
          </button>
        ))}
      </div>
    </section>
  );
}
