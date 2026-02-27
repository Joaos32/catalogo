// note: uses React 18 from CDN

const { useState, useEffect } = React;

// Demo products for initial layout
const DEMO_PRODUCTS = [
  {
    id: 1,
    Codigo: "1",
    Nome: "Lustre Pendente Crystal",
    Descrição: "Elegante lustre em cristal com estrutura em latão, ideal para salas de estar e jantar",
    Categoria: "Lustres",
    URLFoto: "https://images.unsplash.com/photo-1565558631492-a199066cfffa?w=400&h=300&fit=crop",
    Especificacoes: "Altura: 60cm | Diâmetro: 40cm | Lâmpadas: 6x E14 | Peso: 3,5kg"
  },
  {
    id: 2,
    Codigo: "2",
    Nome: "Luminária de Parede Moderna",
    Descrição: "Arandela moderna em alumínio anodizado com acabamento preto fosco",
    Categoria: "Arandelas",
    URLFoto: "https://images.unsplash.com/photo-1565558631492-a199066cfffa?w=400&h=300&fit=crop",
    Especificacoes: "Altura: 25cm | Profundidade: 15cm | Lâmpada: 1x G9 | Peso: 0,8kg"
  },
  {
    id: 3,
    Codigo: "3",
    Nome: "Pendente Industrial Edison",
    Descrição: "Luminária pendente com filamento aparente, design industrial vintage",
    Categoria: "Pendentes",
    URLFoto: "https://images.unsplash.com/photo-1516159260535-cb0881c9a5d4?w=400&h=300&fit=crop",
    Especificacoes: "Altura: 35cm | Diâmetro: 20cm | Lâmpada: 1x E27 | Peso: 0,6kg"
  },
  {
    id: 4,
    Codigo: "4",
    Nome: "Plafon LED Redondo",
    Descrição: "Luminária de teto em alumínio com LED integrado e luz branca fria",
    Categoria: "Plafons",
    URLFoto: "https://images.unsplash.com/photo-1606399676374-d1ce13896357?w=400&h=300&fit=crop",
    Especificacoes: "Diâmetro: 30cm | LED: 18W | 1200 lumens | Peso: 1,2kg"
  },
  {
    id: 5,
    Codigo: "5",
    Nome: "Candelabro Dourado Clássico",
    Descrição: "Candelabro em latão com acabamento dourado polido, 5 velas",
    Categoria: "Candelabros",
    URLFoto: "https://images.unsplash.com/photo-1578500494198-246f612d03b3?w=400&h=300&fit=crop",
    Especificacoes: "Altura: 50cm | Largura: 40cm | Velas: 5x E14 | Peso: 2,1kg"
  },
  {
    id: 6,
    Codigo: "6",
    Nome: "Luminária de Piso Tripé",
    Descrição: "Luminária de piso em madeira com base tripé, acabamento natural",
    Categoria: "Luminárias Piso",
    URLFoto: "https://images.unsplash.com/photo-1565558632069-b8b656b521b5?w=400&h=300&fit=crop",
    Especificacoes: "Altura: 160cm | Base: 50x50cm | Lâmpada: 1x E27 | Peso: 2,8kg"
  }
];

function App() {
  const [products, setProducts] = useState(DEMO_PRODUCTS);
  const [photos, setPhotos] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [usedDemo, setUsedDemo] = useState(true);

  // default sheet url (you can change it or prompt user)
  const sheetUrl =
    "https://docs.google.com/spreadsheets/d/14C-BtunMb82fYNwjsulbyqLgBFwrXbrzFh2XCdevvoM/edit?usp=sharing";

  useEffect(() => {
    // Try to load real data from spreadsheet
    async function fetchSheet() {
      setLoading(true);
      async function doFetch(base) {
        const resp = await fetch(
          `${base}/catalog/sheet?url=${encodeURIComponent(sheetUrl)}`
        );
        if (!resp.ok) throw new Error("failed to load sheet");
        return resp.json();
      }

      try {
        // try relative first (same origin)
        const data = await doFetch("");
        setProducts(data);
        setUsedDemo(false);
        setError(null);
      } catch (err) {
        // local failed; try explicit backend
        try {
          const data = await doFetch("http://127.0.0.1:5000");
          setProducts(data);
          setUsedDemo(false);
          setError(null);
        } catch (err) {
          // fallback to demo, UI banner will inform user
          setError("Unable to load sheet; showing demo data.");
        }
      } finally {
        setLoading(false);
      }
    }
    fetchSheet();
  }, []);

  // whenever products change, try to load photos for each
  useEffect(() => {
    if (products.length === 0) return;
    const shareUrl =
      "https://1drv.ms/f/c/6c7678552c6d6cb7/IgDYd9QRHW3BQ6SYZqlFcvR9Aab6__gEdL4dEq8lvlBoajU?e=7F8Sv2";
    async function fetchPhotos(code) {
      try {
        const resp = await fetch(
          `/catalog/photos?shareUrl=${encodeURIComponent(shareUrl)}&code=${encodeURIComponent(code)}`
        );
        if (!resp.ok) {
          console.warn('photo fetch status not ok', resp.status);
          // backend may be returning 500 when credentials are missing or server
          // wasn't restarted; fall back to local placeholders so layout still shows.
          return {
            white_background: `https://placehold.co/150x150?text=Branco+${code}`,
            ambient: `https://placehold.co/150x150?text=Ambient+${code}`,
            measures: `https://placehold.co/150x150?text=Medidas+${code}`,
          };
        }
        return resp.json();
      } catch (e) {
        console.warn('photo fetch error', e);
        return {
          white_background: `https://placehold.co/150x150?text=Branco+${code}`,
          ambient: `https://placehold.co/150x150?text=Ambient+${code}`,
          measures: `https://placehold.co/150x150?text=Medidas+${code}`,
        };
      }
    }

    Promise.all(
      products.map((p) => fetchPhotos(p.Codigo || p.id))
    ).then((results) => {
      const map = {};
      results.forEach((r, idx) => {
        if (r) map[products[idx].Codigo || products[idx].id] = r;
      });
      setPhotos(map);
    });
  }, [products]);

  if (error) return <div className="container">Erro: {error}</div>;

  return (
    <div>
      <header>
        <div className="header-content">
          <h1>✨ Catálogo de Iluminação</h1>
          <p className="subtitle">Lustres, Luminárias e Materiais Premium para sua Casa</p>
        </div>
      </header>
      <div className="container">
        {usedDemo && (
          <div className="demo-banner">
            ℹ️ Visualizando dados de demonstração. Conecte uma planilha Google Sheets para
            exibir seus produtos reais.
          </div>
        )}
        <div className="product-list">
          {products.map((item, idx) => (
            <ProductCard key={idx} item={item} photos={photos} />
          ))}
        </div>
      </div>
    </div>
  );
}

function ProductCard({ item, photos }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="product-card" onClick={() => setExpanded(!expanded)}>
      <div className="product-image-wrapper">
        <img
          src={item.URLFoto || "https://via.placeholder.com/400x300?text=Sem+imagem"}
          alt={item.Nome || "Produto"}
          className="product-image"
        />
        {item.Categoria && (
          <span className="product-category">{item.Categoria}</span>
        )}
      </div>
      <div className="product-info">
        <h3>{item.Nome}</h3>
        {item.Descrição && <p className="description">{item.Descrição}</p>}
        {expanded && item.Especificacoes && (
          <p className="specs">{item.Especificacoes}</p>
        )}
        <p className="expand-hint">{expanded ? "▼ Menos detalhes" : "▶ Mais detalhes"}</p>
      </div>
      {/* photos thumbnails if available */}
      {photos && photos[item.Codigo || item.id] && (
        <div className="photo-thumbs">
          {photos[item.Codigo || item.id].white_background && (
            <img src={photos[item.Codigo || item.id].white_background} alt="fundo branco" />
          )}
          {photos[item.Codigo || item.id].ambient && (
            <img src={photos[item.Codigo || item.id].ambient} alt="ambient" />
          )}
          {photos[item.Codigo || item.id].measures && (
            <img src={photos[item.Codigo || item.id].measures} alt="medidas" />
          )}
        </div>
      )}
    </div>
  );
}

// render
ReactDOM.createRoot(document.getElementById("root")).render(<App />);
