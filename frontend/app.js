// Observacao: usa React 18 via CDN.

const { useEffect, useMemo, useState } = React;

const catalogRuntime = window.Catalog || {};
const {
  DEMO_PRODUCTS = [],
  normalizeText,
  normalizeProduct,
  fallbackPhotos,
  buildGalleryEntries,
  fetchFromBases,
  readPersistedUiState,
  persistUiState,
  setFallbackImage,
  CARD_FALLBACK_IMAGE,
  DETAIL_FALLBACK_IMAGE,
  THUMB_FALLBACK_IMAGE,
} = catalogRuntime;

if (
  typeof normalizeText !== "function" ||
  typeof normalizeProduct !== "function" ||
  typeof fallbackPhotos !== "function" ||
  typeof buildGalleryEntries !== "function" ||
  typeof fetchFromBases !== "function" ||
  typeof readPersistedUiState !== "function" ||
  typeof persistUiState !== "function" ||
  typeof setFallbackImage !== "function"
) {
  throw new Error("Catalog runtime modules were not loaded correctly.");
}

const DEFAULT_PRODUCTS = DEMO_PRODUCTS.map((item, index) => normalizeProduct(item, index));

function App() {
  const initialUiState = useMemo(() => readPersistedUiState(), []);
  const [products, setProducts] = useState(DEFAULT_PRODUCTS);
  const [photosByCode, setPhotosByCode] = useState({});
  const [galleryByCode, setGalleryByCode] = useState({});
  const [loading, setLoading] = useState(false);
  const [loadingPhotos, setLoadingPhotos] = useState(false);
  const [error, setError] = useState("");
  const [query, setQuery] = useState(initialUiState.query);
  const [category, setCategory] = useState(initialUiState.category);
  const [selectedCode, setSelectedCode] = useState(initialUiState.selectedCode);

  useEffect(() => {
    let active = true;

    async function loadProducts() {
      setLoading(true);
      setError("");

      try {
        const localData = await fetchFromBases((base) => `${base}/catalog/local/produtos`);
        if (!active) return;

        if (Array.isArray(localData)) {
          if (localData.length > 0) {
            setProducts(localData.map((item, index) => normalizeProduct(item, index)));
            setError("");
          } else {
            setProducts([]);
            setError("Nenhum produto cadastrado.");
          }
        } else {
          setProducts([]);
          setError("Nao foi possivel carregar os produtos agora.");
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    loadProducts();

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (products.length === 0) {
      setPhotosByCode({});
      setLoadingPhotos(false);
      return;
    }
    let active = true;

    async function loadPhotos() {
      setLoadingPhotos(true);

      const localEntries = [];
      const productsWithoutPhotos = [];

      for (const product of products) {
        const key = product.id;
        const embedded = product.photos;
        if (
          embedded &&
          (embedded.white_background || embedded.ambient || embedded.measures)
        ) {
          localEntries.push([key, embedded]);
        } else {
          productsWithoutPhotos.push(product);
        }
      }

      if (productsWithoutPhotos.length === 0) {
        if (!active) return;
        setPhotosByCode(Object.fromEntries(localEntries));
        setLoadingPhotos(false);
        return;
      }

      try {
        const fetchedEntries = await Promise.all(
          productsWithoutPhotos.map(async (product) => {
            const key = product.id;
            const code = product.code || product.id;
            const payload = await fetchFromBases(
              (base) => `${base}/catalog/photos?code=${encodeURIComponent(code)}`
            );

            if (
              payload &&
              typeof payload === "object" &&
              (payload.white_background || payload.ambient || payload.measures)
            ) {
              return [key, payload];
            }

            return [key, fallbackPhotos(code)];
          })
        );

        if (!active) return;

        setPhotosByCode(Object.fromEntries([...localEntries, ...fetchedEntries]));
      } finally {
        if (active) {
          setLoadingPhotos(false);
        }
      }
    }

    loadPhotos();

    return () => {
      active = false;
    };
  }, [products]);

  useEffect(() => {
    if (!selectedCode) return;
    if (Object.prototype.hasOwnProperty.call(galleryByCode, selectedCode)) return;
    const current = products.find((item) => String(item.id) === String(selectedCode));
    if (!current) return;
    const codeForRequest = current.code || current.id;
    let active = true;

    async function loadGallery() {
      const payload = await fetchFromBases(
        (base) => `${base}/catalog/produtos/${encodeURIComponent(codeForRequest)}/imagens`
      );
      if (!active) return;
      if (payload && Array.isArray(payload.imagens) && payload.imagens.length > 0) {
        setGalleryByCode((currentState) =>
          Object.assign({}, currentState, { [selectedCode]: payload.imagens })
        );
      } else {
        setGalleryByCode((currentState) =>
          Object.assign({}, currentState, { [selectedCode]: [] })
        );
      }
    }

    loadGallery();

    return () => {
      active = false;
    };
  }, [selectedCode, galleryByCode, products]);

  useEffect(() => {
    persistUiState({ query, category, selectedCode });
  }, [query, category, selectedCode]);

  const categories = useMemo(() => {
    const values = Array.from(
      new Set(products.map((item) => item.category).filter(Boolean))
    ).sort((a, b) => a.localeCompare(b));
    return ["Todas", ...values];
  }, [products]);

  useEffect(() => {
    if (category === "Todas") return;
    if (!categories.includes(category)) {
      setCategory("Todas");
    }
  }, [category, categories]);

  useEffect(() => {
    if (!selectedCode) return;
    const stillExists = products.some(
      (item) => String(item.id) === String(selectedCode)
    );
    if (!stillExists) {
      setSelectedCode("");
    }
  }, [products, selectedCode]);

  const filteredProducts = useMemo(() => {
    const search = normalizeText(query);

    return products.filter((item) => {
      const categoryOk = category === "Todas" || item.category === category;
      const textBlob = normalizeText(
        `${item.name} ${item.code} ${item.description} ${item.category}`
      );
      const queryOk = !search || textBlob.includes(search);
      return categoryOk && queryOk;
    });
  }, [products, query, category]);

  const loadedPhotoCount = useMemo(() => Object.keys(photosByCode).length, [photosByCode]);
  const selectedProduct = useMemo(
    () => products.find((item) => String(item.id) === String(selectedCode)) || null,
    [products, selectedCode]
  );
  const selectedPhotos = selectedProduct ? photosByCode[selectedProduct.id] : null;
  const selectedGalleryEntries = useMemo(
    () =>
      selectedProduct
        ? buildGalleryEntries(
            selectedProduct,
            selectedPhotos,
            galleryByCode[selectedProduct.id]
          )
        : [],
    [selectedProduct, selectedPhotos, galleryByCode]
  );

  return (
    <div className="page-shell">
      <div className="bg-orb orb-a" aria-hidden="true"></div>
      <div className="bg-orb orb-b" aria-hidden="true"></div>

      <header className="hero">
        <div className="hero-identity">
          <h1 className="sr-only">Catalogo de produtos Nitrolux</h1>
          <div className="hero-kicker">Catalogo de produtos</div>
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
            onBack={() => setSelectedCode("")}
          />
        ) : (
          <React.Fragment>
            <section className="toolbar" aria-label="Filtros do catalogo">
              <label className="field search-field">
                <span>Buscar produto</span>
                <input
                  type="search"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Nome, codigo ou categoria"
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

            <p className="result-summary" role="status" aria-live="polite">
              {loading ? "Carregando produtos..." : `${filteredProducts.length} itens encontrados`}
            </p>

            {error && <div className="banner banner-warning">{error}</div>}
            {!error && loadingPhotos && (
              <div className="banner banner-info">Carregando fotos dos produtos...</div>
            )}

            <section className="stats-grid" aria-label="Resumo">
              <article className="stat-card">
                <strong>{filteredProducts.length}</strong>
                <span>Itens visiveis</span>
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
              <section className="catalog-grid">
                {filteredProducts.map((item, index) => (
                  <ProductCard
                    key={`${item.code}-${item.id}-${index}`}
                    item={item}
                    photos={photosByCode[item.id]}
                    index={index}
                    onOpen={() => setSelectedCode(item.id)}
                  />
                ))}
              </section>
            ) : (
              <section className="empty-state">
                <h2>Nenhum item encontrado</h2>
                <p>Ajuste a busca ou selecione outra categoria.</p>
              </section>
            )}
          </React.Fragment>
        )}
      </main>
    </div>
  );
}

function ProductCard({ item, photos, index, onOpen }) {
  const previewImage =
    item.cover ||
    (photos && (photos.white_background || photos.ambient || photos.measures)) ||
    CARD_FALLBACK_IMAGE;

  return (
    <article className="product-card" style={{ "--stagger": `${Math.min(index * 70, 700)}ms` }}>
      <button
        type="button"
        className="card-hitbox"
        onClick={onOpen}
        aria-label={`Abrir detalhes de ${item.name || "produto"}`}
      >
        <div className="media">
          <img
            src={previewImage}
            alt={item.name || "Produto"}
            loading="lazy"
            decoding="async"
            width="900"
            height="700"
            onError={(event) => setFallbackImage(event, CARD_FALLBACK_IMAGE)}
          />
          <div className="media-overlay"></div>
          <span className="chip chip-code">#{item.code}</span>
          <span className="chip chip-category">{item.category}</span>
        </div>

        <div className="card-body">
          <h3>{item.name || "Produto"}</h3>
          <p className="description">{item.description || "Descricao indisponivel para este produto."}</p>

          <span className="expand-label">Abrir galeria completa</span>
        </div>
      </button>

      <div className="thumb-strip" aria-label="Fotos do produto">
        <Thumb image={photos && photos.white_background} label="Fundo branco" />
        <Thumb image={photos && photos.ambient} label="Ambientada" />
        <Thumb image={photos && photos.measures} label="Medidas" />
      </div>
    </article>
  );
}

function ProductDetail({ item, photos, galleryEntries, onBack }) {
  const [activeIndex, setActiveIndex] = useState(0);
  const gallery =
    galleryEntries && galleryEntries.length > 0
      ? galleryEntries
      : buildGalleryEntries(item, photos, []);
  const activeImage = gallery[activeIndex] || gallery[0] || null;

  useEffect(() => {
    setActiveIndex(0);
  }, [item.code, item.id]);

  return (
    <section className="detail-panel" aria-label="Detalhes do produto">
      <button type="button" className="detail-back" onClick={onBack}>
        Voltar ao catalogo
      </button>

      <div className="detail-layout">
        <div className="detail-media">
          <img
            src={(activeImage && activeImage.url) || DETAIL_FALLBACK_IMAGE}
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
            <span className="detail-tag">Codigo: {item.code}</span>
            <span className="detail-tag">{item.category || "Sem categoria"}</span>
          </div>
          <p>{item.description || "Descricao indisponivel para este produto."}</p>
          <p>{item.specs || "Sem especificacoes tecnicas cadastradas."}</p>
        </aside>
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

function Thumb({ image, label }) {
  return (
    <figure className="thumb">
      <img
        src={image || THUMB_FALLBACK_IMAGE}
        alt={label}
        loading="lazy"
        decoding="async"
        width="240"
        height="240"
        onError={(event) => setFallbackImage(event, THUMB_FALLBACK_IMAGE)}
      />
      <figcaption>{label}</figcaption>
    </figure>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);