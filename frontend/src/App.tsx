import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import ExportActions from "./components/ExportActions";
import ProductCard from "./components/ProductCard";
import ProductDetail from "./components/ProductDetail";
import {
  downloadCatalogExport,
  fetchImagesByCode,
  fetchPhotosByCode,
  fetchProducts,
} from "./lib/catalog-api";
import {
  DEMO_PRODUCTS,
  buildGalleryEntries,
  fallbackPhotos,
  hasAnyPhoto,
  normalizeProduct,
  normalizeText,
} from "./lib/catalog-products";
import { persistUiState, readPersistedUiState } from "./lib/catalog-storage";
import type { CatalogExportFormat, CatalogProduct, ProductPhotos } from "./types";

type PhotosByProductId = Record<string, ProductPhotos>;

function useCatalogProducts() {
  return useQuery({
    queryKey: ["catalog-products"],
    queryFn: fetchProducts,
    staleTime: 60_000,
  });
}

export default function App(): JSX.Element {
  const navigate = useNavigate();
  const { productId } = useParams<{ productId: string }>();
  const initialUiState = useMemo(() => readPersistedUiState(), []);

  const [query, setQuery] = useState(initialUiState.query);
  const [category, setCategory] = useState(initialUiState.category);

  const productsQuery = useCatalogProducts();

  const products = useMemo(() => {
    const source = productsQuery.data && productsQuery.data.length > 0 ? productsQuery.data : DEMO_PRODUCTS;
    return source.map((item, index) => normalizeProduct(item, index));
  }, [productsQuery.data]);

  const photosQuery = useQuery({
    queryKey: [
      "catalog-photos",
      products
        .map((item) => item.code || item.id)
        .join("|")
        .toLowerCase(),
    ],
    enabled: products.length > 0,
    staleTime: 5 * 60_000,
    queryFn: async (): Promise<PhotosByProductId> => {
      const entries = await Promise.all(
        products.map(async (product) => {
          if (hasAnyPhoto(product.photos)) {
            return [product.id, product.photos] as const;
          }

          const code = product.code || product.id;
          const payload = await fetchPhotosByCode(code);
          const normalized = hasAnyPhoto(payload) ? payload : fallbackPhotos(code);
          return [product.id, normalized] as const;
        })
      );

      return Object.fromEntries(entries) as PhotosByProductId;
    },
  });

  const photosByProductId = useMemo(() => photosQuery.data || {}, [photosQuery.data]);

  const selectedProduct = useMemo(() => {
    if (!productId) return null;
    return products.find((item) => item.routeId === productId) || null;
  }, [productId, products]);

  useEffect(() => {
    if (!productId || productsQuery.isLoading) return;
    if (!selectedProduct) {
      navigate("/", { replace: true });
    }
  }, [navigate, productId, productsQuery.isLoading, selectedProduct]);

  const selectedPhotos = selectedProduct ? photosByProductId[selectedProduct.id] || null : null;

  const galleryQuery = useQuery({
    queryKey: ["catalog-gallery", selectedProduct?.code || selectedProduct?.id || "none"],
    enabled: Boolean(selectedProduct),
    staleTime: 5 * 60_000,
    queryFn: async () => {
      if (!selectedProduct) return [];
      const code = selectedProduct.code || selectedProduct.id;
      const payload = await fetchImagesByCode(code);
      return payload && Array.isArray(payload.imagens) ? payload.imagens : [];
    },
  });

  useEffect(() => {
    persistUiState({ query, category });
  }, [query, category]);

  const categories = useMemo(() => {
    const values = Array.from(new Set(products.map((item) => item.category).filter(Boolean))).sort((a, b) =>
      a.localeCompare(b)
    );
    return ["Todas", ...values];
  }, [products]);

  useEffect(() => {
    if (category === "Todas") return;
    if (!categories.includes(category)) {
      setCategory("Todas");
    }
  }, [category, categories]);

  const filteredProducts = useMemo(() => {
    const search = normalizeText(query);

    return products.filter((item) => {
      const categoryOk = category === "Todas" || item.category === category;
      const textBlob = normalizeText(`${item.name} ${item.code} ${item.description} ${item.category}`);
      const queryOk = !search || textBlob.includes(search);
      return categoryOk && queryOk;
    });
  }, [category, products, query]);

  const productsByCategory = useMemo(() => {
    const groups = new Map<string, CatalogProduct[]>();
    for (const item of filteredProducts) {
      const group = item.category || "Sem categoria";
      const list = groups.get(group) || [];
      list.push(item);
      groups.set(group, list);
    }
    return Array.from(groups.entries()).sort(([left], [right]) => left.localeCompare(right));
  }, [filteredProducts]);

  const selectedGalleryEntries = useMemo(() => {
    if (!selectedProduct) return [];
    return buildGalleryEntries(selectedProduct, selectedPhotos, galleryQuery.data || []);
  }, [galleryQuery.data, selectedPhotos, selectedProduct]);

  const loading = productsQuery.isLoading;
  const loadingPhotos = photosQuery.isFetching;
  const loadedPhotoCount = Object.keys(photosByProductId).length;

  const productsError = productsQuery.isError ? "Não foi possível carregar os produtos agora." : "";
  const emptyError = !loading && !productsError && products.length === 0 ? "Nenhum produto cadastrado." : "";

  const openProduct = (item: CatalogProduct) => {
    navigate(`/produto/${item.routeId}`);
  };

  const closeDetail = () => {
    navigate("/");
  };

  const exportCatalog = (format: CatalogExportFormat) => {
    void downloadCatalogExport({
      format,
      query,
      category: category === "Todas" ? "" : category,
    });
  };

  const exportSelectedProduct = (format: CatalogExportFormat) => {
    if (!selectedProduct) return;
    void downloadCatalogExport({
      format,
      code: selectedProduct.code,
    });
  };

  return (
    <div className="page-shell">
      <div className="bg-orb orb-a" aria-hidden="true"></div>
      <div className="bg-orb orb-b" aria-hidden="true"></div>

      <header className="hero">
        <div className="hero-identity">
          <h1 className="sr-only">Catálogo de produtos Nitrolux</h1>
          <div className="hero-kicker">Catálogo de produtos</div>
          <div className="hero-brand" aria-label="Marca NITROLUX">
            <p className="hero-brand-name">NITROLUX</p>
            <p className="hero-brand-subtitle">Sua vida com mais brilho</p>
          </div>
        </div>
      </header>

      <main className="content-wrap" aria-busy={loading || loadingPhotos}>
        {selectedProduct ? (
          <ProductDetail
            item={selectedProduct}
            photos={selectedPhotos}
            galleryEntries={selectedGalleryEntries}
            onBack={closeDetail}
            onExport={exportSelectedProduct}
          />
        ) : (
          <>
            <section className="toolbar" aria-label="Filtros do catálogo">
              <label className="field search-field">
                <span>Buscar produto</span>
                <input
                  type="search"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Nome, código ou categoria"
                />
              </label>

              <label className="field filter-field">
                <span>Categoria</span>
                <select value={category} onChange={(event) => setCategory(event.target.value)}>
                  {categories.map((value) => (
                    <option key={value} value={value}>
                      {value}
                    </option>
                  ))}
                </select>
              </label>
            </section>

            <ExportActions
              title="Exportar itens visíveis"
              note={`${filteredProducts.length} item(ns) no recorte atual, com dados e fotos conforme o formato.`}
              onExport={exportCatalog}
              disabled={loading || filteredProducts.length === 0}
            />

            <p className="result-summary" role="status" aria-live="polite">
              {loading ? "Carregando produtos..." : `${filteredProducts.length} itens encontrados`}
            </p>

            {productsError && <div className="banner banner-warning">{productsError}</div>}
            {emptyError && <div className="banner banner-warning">{emptyError}</div>}
            {!productsError && !emptyError && loadingPhotos && (
              <div className="banner banner-info">Carregando fotos dos produtos...</div>
            )}

            <section className="stats-grid" aria-label="Resumo">
              <article className="stat-card">
                <strong>{filteredProducts.length}</strong>
                <span>Itens visíveis</span>
              </article>
              <article className="stat-card">
                <strong>{categories.length - 1}</strong>
                <span>Categorias</span>
              </article>
              <article className="stat-card">
                <strong>{loadedPhotoCount}</strong>
                <span>Galerias prontas</span>
              </article>
            </section>

            {loading ? (
              <section className="loading-state" role="status" aria-live="polite">
                Carregando lista de produtos...
              </section>
            ) : filteredProducts.length > 0 ? (
              <section className="catalog-groups">
                {productsByCategory.map(([groupName, groupProducts]) => (
                  <section key={groupName} className="category-group">
                    <h2 className="category-title">{groupName}</h2>
                    <div className="catalog-grid">
                      {groupProducts.map((item, index) => (
                        <ProductCard
                          key={`${item.routeId}-${item.id}`}
                          item={item}
                          photos={photosByProductId[item.id]}
                          index={index}
                          onOpen={() => openProduct(item)}
                        />
                      ))}
                    </div>
                  </section>
                ))}
              </section>
            ) : (
              <section className="empty-state">
                <h2>Nenhum item encontrado</h2>
                <p>Ajuste a busca ou selecione outra categoria.</p>
              </section>
            )}
          </>
        )}
      </main>
    </div>
  );
}
