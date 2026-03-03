// note: uses React 18 from CDN

const { useEffect, useMemo, useState } = React;

const API_BASES = ["", "http://127.0.0.1:8000", "http://127.0.0.1:5000"];
const UI_STATE_STORAGE_KEY = "catalog-ui-state-v1";
const SCROLL_STORAGE_KEY = "catalog-scroll-y-v1";
const THEME_CSS = `
:root {
  --blue-950: #0d2c60;
  --blue-900: #143f87;
  --blue-800: #1d57b3;
  --blue-700: #2a6cd7;
  --blue-200: #d7e7ff;
  --blue-100: #ebf2ff;
  --ink-900: #102845;
  --ink-700: #37506e;
  --ink-500: #617892;
  --line-soft: rgba(27, 88, 176, 0.16);
  --surface: rgba(255, 255, 255, 0.9);
  --surface-strong: rgba(255, 255, 255, 0.96);
  --radius-xl: 30px;
  --radius-lg: 22px;
  --radius-md: 16px;
  --shadow-soft: 0 14px 28px rgba(17, 49, 94, 0.08);
  --shadow-hero: 0 26px 50px rgba(13, 45, 88, 0.15);
  --ribbon-image: url("/assets/azul-nitro.jpg");
}

body {
  margin: 0;
  min-height: 100vh;
  color: var(--ink-900);
  font-family: "Manrope", "Segoe UI", Tahoma, sans-serif;
  background:
    radial-gradient(circle at 88% -10%, rgba(60, 134, 255, 0.16), transparent 42%),
    radial-gradient(circle at 86% 102%, rgba(79, 142, 255, 0.1), transparent 44%),
    linear-gradient(180deg, #f8fbff 0%, #f0f5fc 58%, #edf3fa 100%);
  position: relative;
}
body::before {
  content: "";
  position: fixed;
  left: -118px;
  top: -6vh;
  bottom: -8vh;
  width: min(43vw, 440px);
  background:
    linear-gradient(
      90deg,
      rgba(240, 245, 252, 0.88) 0%,
      rgba(240, 245, 252, 0.24) 45%,
      rgba(240, 245, 252, 0) 74%
    ),
    var(--ribbon-image) no-repeat 78% center / 205% auto;
  filter: saturate(1.08) contrast(1.06);
  opacity: 0.9;
  pointer-events: none;
  z-index: -1;
  transform: rotate(0.8deg);
  animation: ribbon-drift 16s ease-in-out infinite alternate;
}
body::after {
  content: "";
  position: fixed;
  left: 156px;
  top: 14vh;
  width: min(16vw, 150px);
  height: min(42vh, 410px);
  border-radius: 140px;
  background:
    radial-gradient(circle at 30% 20%, rgba(196, 220, 255, 0.66), rgba(196, 220, 255, 0) 72%),
    radial-gradient(circle at 70% 80%, rgba(85, 144, 255, 0.16), rgba(85, 144, 255, 0) 76%);
  opacity: 0.72;
  pointer-events: none;
  z-index: -1;
}
* {
  box-sizing: border-box;
}
.page-shell {
  padding: 18px 16px 26px;
  overflow-x: clip;
  position: relative;
}
.bg-orb {
  position: fixed;
  z-index: -1;
  border-radius: 999px;
  pointer-events: none;
  filter: blur(24px);
  opacity: 0.55;
}
.orb-a {
  width: min(30vw, 280px);
  aspect-ratio: 1;
  right: -90px;
  top: 14vh;
  background: radial-gradient(
    circle at 34% 38%,
    rgba(44, 122, 244, 0.46),
    rgba(44, 122, 244, 0.06) 72%,
    rgba(44, 122, 244, 0)
  );
}
.orb-b {
  width: min(26vw, 220px);
  aspect-ratio: 1;
  right: 6vw;
  top: 66vh;
  background: radial-gradient(
    circle at 50% 50%,
    rgba(122, 170, 255, 0.42),
    rgba(122, 170, 255, 0.08) 70%,
    rgba(122, 170, 255, 0)
  );
}
.hero {
  max-width: 1180px;
  margin: 0 auto;
  border-radius: var(--radius-xl);
  padding: 30px 30px 28px;
  color: var(--ink-900);
  border: 1px solid rgba(34, 111, 224, 0.23);
  background:
    linear-gradient(164deg, rgba(255, 255, 255, 0.97), rgba(238, 247, 255, 0.93)),
    radial-gradient(circle at 16% 14%, rgba(56, 141, 255, 0.2), rgba(56, 141, 255, 0) 44%);
  box-shadow: var(--shadow-hero);
  text-align: center;
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 150px;
}
.hero-identity {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
  position: relative;
  z-index: 1;
}
.hero::before {
  content: "";
  position: absolute;
  left: -64px;
  top: -40px;
  bottom: -70px;
  width: min(30vw, 290px);
  border-radius: 210px;
  background:
    linear-gradient(
      90deg,
      rgba(255, 255, 255, 0.95) 0%,
      rgba(255, 255, 255, 0.12) 48%,
      rgba(255, 255, 255, 0) 76%
    ),
    var(--ribbon-image) no-repeat 74% center / 220% auto;
  opacity: 0.52;
  transform: rotate(4deg);
  pointer-events: none;
}
.hero::after {
  content: "";
  position: absolute;
  width: min(44vw, 440px);
  aspect-ratio: 1;
  right: -160px;
  top: -220px;
  border-radius: 999px;
  background: radial-gradient(
    circle at 42% 45%,
    rgba(88, 154, 255, 0.22),
    rgba(88, 154, 255, 0.08) 48%,
    rgba(88, 154, 255, 0)
  );
  pointer-events: none;
}
.hero-kicker {
  display: inline-block;
  align-items: center;
  border: 1px solid rgba(35, 109, 219, 0.26);
  border-radius: 999px;
  padding: 7px 14px;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.24em;
  color: #2668d8;
  background: rgba(255, 255, 255, 0.82);
  line-height: 1;
}
.hero h1 {
  margin: 14px auto 0;
  max-width: 900px;
  font-size: 44px;
  line-height: 1.1;
  font-family: "Sora", "Manrope", sans-serif;
  letter-spacing: -0.02em;
  color: #123874;
  position: relative;
  z-index: 1;
}
.hero p {
  margin: 14px auto 0;
  max-width: 760px;
  font-size: 17px;
  line-height: 1.5;
  color: rgba(25, 59, 104, 0.86);
  position: relative;
  z-index: 1;
}
.hero-brand {
  margin: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0;
  padding: 0;
  border: 0;
  background: transparent;
  box-shadow: none;
}
.hero-brand-name {
  margin: 0;
  font-family: "Sora", "Manrope", sans-serif;
  font-size: clamp(46px, 7.2vw, 90px);
  line-height: 0.9;
  letter-spacing: 0.08em;
  font-weight: 800;
  background: linear-gradient(180deg, #1e5fc2 0%, #143f86 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  text-shadow: 0 10px 24px rgba(20, 63, 134, 0.16);
}
.hero-brand-subtitle {
  margin: 4px 0 0;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  font-size: clamp(14px, 1.8vw, 24px);
  line-height: 1.2;
  color: #245aa8;
  font-weight: 700;
  letter-spacing: 0.02em;
}
.hero-brand-subtitle::before,
.hero-brand-subtitle::after {
  content: "";
  width: 34px;
  height: 1px;
  background: linear-gradient(90deg, rgba(38, 104, 216, 0), rgba(38, 104, 216, 0.65), rgba(38, 104, 216, 0));
}
.hero-pills {
  margin-top: 18px;
  position: relative;
  z-index: 1;
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 10px;
}
.pill {
  display: inline-flex;
  align-items: center;
  margin: 0;
  border: 1px solid rgba(28, 101, 212, 0.24);
  border-radius: 999px;
  padding: 7px 13px;
  font-size: 13px;
  font-weight: 600;
  color: #1e4f9f;
  background: rgba(255, 255, 255, 0.86);
}
.pill-ok {
  border-color: rgba(34, 152, 98, 0.34);
  color: #1a6f4d;
}
.pill-warn {
  border-color: rgba(229, 159, 56, 0.44);
  color: #955a13;
}
.content-wrap {
  max-width: 1180px;
  margin: 18px auto 0;
}
.toolbar {
  margin-bottom: 12px;
  display: grid;
  grid-template-columns: 1fr minmax(220px, 290px);
  gap: 10px;
  padding: 14px;
  border-radius: var(--radius-lg);
  border: 1px solid var(--line-soft);
  background: linear-gradient(170deg, var(--surface-strong), var(--surface));
  box-shadow: var(--shadow-soft);
}
.field {
  display: block;
  margin: 0;
}
.search-field {
  width: auto;
  min-width: 0;
}
.filter-field {
  width: auto;
}
.field span {
  display: block;
  margin-bottom: 6px;
  font-size: 11px;
  letter-spacing: 0.17em;
  text-transform: uppercase;
  font-weight: 700;
  color: #37639f;
}
.field input,
.field select {
  width: 100%;
  height: 44px;
  border-radius: 999px;
  border: 1px solid rgba(31, 104, 208, 0.2);
  padding: 0 14px;
  color: var(--ink-900);
  background: rgba(255, 255, 255, 0.95);
  font: inherit;
}
.field input:focus,
.field select:focus {
  outline: none;
  border-color: #2b6ad0;
  box-shadow: 0 0 0 3px rgba(43, 106, 208, 0.16);
}
.field select {
  cursor: pointer;
}
.banner {
  border: 1px solid;
  border-radius: 12px;
  padding: 11px 13px;
  margin-bottom: 12px;
  font-size: 14px;
}
.banner-warning {
  border-color: #f3c88a;
  background: #fff6e8;
  color: #946020;
}
.banner-info {
  border-color: rgba(43, 106, 208, 0.22);
  background: #eef5ff;
  color: #2055a6;
}
.stats-grid {
  margin-bottom: 14px;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 10px;
}
.stat-card {
  display: block;
  width: auto;
  margin: 0;
  padding: 13px 14px;
  border-radius: 14px;
  border: 1px solid rgba(24, 92, 193, 0.15);
  background: linear-gradient(165deg, rgba(255, 255, 255, 0.95), rgba(241, 248, 255, 0.94));
  box-shadow: 0 9px 20px rgba(25, 67, 130, 0.08);
}
.stat-card strong {
  display: block;
  font-family: "Sora", "Manrope", sans-serif;
  font-size: 27px;
  line-height: 1.1;
  color: #1b4f9f;
}
.stat-card span {
  color: var(--ink-700);
  font-size: 13px;
}
.catalog-grid {
  display: grid !important;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 16px;
  margin: 0;
}
.product-card {
  display: block;
  width: auto;
  margin: 0;
  border-radius: 20px;
  overflow: hidden;
  border: 1px solid rgba(26, 92, 190, 0.14);
  background: linear-gradient(166deg, rgba(255, 255, 255, 0.97) 0%, rgba(241, 247, 255, 0.95) 100%);
  box-shadow: 0 12px 26px rgba(16, 58, 118, 0.09);
  transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease;
}
.product-card:hover {
  transform: translateY(-2px);
  border-color: rgba(29, 98, 196, 0.3);
  box-shadow: 0 18px 32px rgba(13, 58, 127, 0.14);
}
.card-hitbox {
  display: block;
  width: 100%;
  border: 0;
  background: transparent;
  text-align: left;
  padding: 0;
  cursor: pointer;
  font: inherit;
  color: inherit;
}
.media {
  position: relative;
  height: 220px;
  overflow: hidden;
  background: #dbe8fb;
}
.media img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  transition: transform 0.45s ease;
}
.product-card:hover .media img {
  transform: scale(1.05);
}
.media-overlay {
  position: absolute;
  left: 0;
  top: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(to top, rgba(10, 38, 82, 0.58), rgba(10, 38, 82, 0));
}
.chip {
  position: absolute;
  top: 12px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.3);
  font-size: 11px;
  color: #f8fdfa;
  padding: 5px 10px;
}
.chip-code {
  left: 12px;
  background: rgba(13, 43, 91, 0.55);
}
.chip-category {
  right: 12px;
  background: rgba(32, 101, 205, 0.52);
}
.card-body {
  padding: 14px;
}
.card-body h3 {
  margin: 0;
  font-size: 21px;
  line-height: 1.2;
  font-family: "Sora", "Manrope", sans-serif;
}
.description {
  margin: 10px 0 0;
  font-size: 15px;
  line-height: 1.5;
  color: var(--ink-700);
  min-height: 3em;
}
.specs {
  margin-top: 0;
  max-height: 0;
  overflow: hidden;
  padding: 0 10px;
  border-left: 3px solid transparent;
  border-radius: 10px;
  background: rgba(233, 242, 255, 0.74);
  color: #2d4f7f;
  font-size: 14px;
  line-height: 1.45;
  transition: max-height 0.25s ease, margin-top 0.25s ease, padding 0.25s ease;
}
.specs.is-open {
  margin-top: 10px;
  max-height: 120px;
  padding: 8px 10px;
  border-left-color: #2b6ad0;
}
.expand-label {
  display: inline-block;
  margin-top: 10px;
  font-size: 13px;
  font-weight: 700;
  color: #235bb3;
}
.thumb-strip {
  border-top: 1px solid rgba(29, 98, 196, 0.14);
  background: #f5f9ff;
  padding: 10px;
  display: flex;
  gap: 8px;
  align-items: flex-start;
}
.thumb {
  flex: 1 1 0;
  min-width: 0;
  margin: 0;
}
.thumb img {
  width: 100% !important;
  min-width: 100%;
  height: 100px;
  object-fit: cover;
  border-radius: 10px;
  border: 1px solid rgba(28, 95, 192, 0.18);
  display: block;
  background: #dce7f5;
}
.thumb figcaption {
  margin-top: 6px;
  font-size: 12px;
  color: var(--ink-700);
  text-align: center;
}
.detail-panel {
  border-radius: 20px;
  border: 1px solid rgba(26, 92, 190, 0.17);
  background: linear-gradient(166deg, rgba(255, 255, 255, 0.97), rgba(241, 247, 255, 0.95));
  box-shadow: 0 12px 26px rgba(16, 58, 118, 0.1);
  padding: 14px;
}
.detail-back {
  border: 1px solid rgba(30, 97, 198, 0.35);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.96);
  color: #1f57af;
  padding: 8px 14px;
  font: inherit;
  font-weight: 700;
  cursor: pointer;
  transition: border-color 0.2s ease, transform 0.2s ease;
}
.detail-back:hover {
  border-color: #2667cf;
  transform: translateY(-1px);
}
.detail-layout {
  margin-top: 12px;
  display: grid;
  grid-template-columns: minmax(280px, 2fr) minmax(240px, 1fr);
  gap: 14px;
}
.detail-media {
  border-radius: 14px;
  overflow: hidden;
  background: #dde8f9;
  aspect-ratio: 4 / 3;
  min-height: 320px;
  max-height: min(68vh, 760px);
  display: flex;
  align-items: center;
  justify-content: center;
}
.detail-media img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  object-position: center;
  display: block;
  background: #f7fbff;
}
.detail-meta {
  border-radius: 14px;
  border: 1px solid rgba(26, 92, 190, 0.14);
  background: linear-gradient(165deg, #ffffff 0%, #f3f8ff 100%);
  padding: 12px;
}
.detail-meta h2 {
  margin: 0;
  font-size: 28px;
  line-height: 1.15;
  font-family: "Sora", "Manrope", sans-serif;
  color: #123a75;
}
.detail-meta p {
  margin: 10px 0 0;
  color: var(--ink-700);
  line-height: 1.5;
}
.detail-tags {
  margin-top: 10px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.detail-tag {
  border-radius: 999px;
  padding: 6px 10px;
  font-size: 12px;
  border: 1px solid rgba(30, 98, 198, 0.24);
  background: rgba(42, 111, 215, 0.09);
  color: #1f57af;
}
.detail-gallery {
  margin-top: 12px;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(110px, 1fr));
  gap: 8px;
}
.detail-gallery-btn {
  border: 1px solid rgba(26, 92, 190, 0.2);
  background: #ffffff;
  border-radius: 10px;
  padding: 5px;
  text-align: left;
  cursor: pointer;
}
.detail-gallery-btn.is-active {
  border-color: #2b6ad0;
  box-shadow: 0 0 0 2px rgba(43, 106, 208, 0.16);
}
.detail-gallery-btn img {
  width: 100%;
  height: 84px;
  object-fit: cover;
  border-radius: 8px;
  display: block;
}
.detail-gallery-btn span {
  display: block;
  margin-top: 5px;
  font-size: 11px;
  color: var(--ink-700);
}
.empty-state {
  text-align: center;
  border-radius: 20px;
  border: 1px dashed rgba(31, 104, 208, 0.35);
  background: rgba(255, 255, 255, 0.86);
  padding: 34px 14px;
}
.empty-state h2 {
  margin: 0;
  font-family: "Sora", "Manrope", sans-serif;
  color: #123a75;
}
.empty-state p {
  margin: 8px 0 0;
  color: var(--ink-700);
}
@keyframes ribbon-drift {
  0% {
    transform: rotate(2deg) translateY(-6px);
    opacity: 0.8;
  }
  100% {
    transform: rotate(5deg) translateY(8px);
    opacity: 0.88;
  }
}
@media (max-width: 1024px) {
  .hero h1 {
    font-size: 35px;
  }
  .product-card {
    width: auto;
  }
}
@media (max-width: 740px) {
  body::before {
    left: -88px;
    width: min(58vw, 280px);
    background-size: 232% auto;
    opacity: 0.78;
  }
  body::after {
    display: none;
  }
  .page-shell {
    padding: 10px;
  }
  .hero {
    border-radius: 20px;
    padding: 22px 16px 20px;
    min-height: 124px;
  }
  .hero h1 {
    font-size: 30px;
  }
  .hero p {
    font-size: 15px;
  }
  .hero-brand {
    margin-top: 0;
  }
  .hero-brand-name {
    font-size: clamp(36px, 11vw, 56px);
  }
  .hero-kicker {
    letter-spacing: 0.18em;
    font-size: 10px;
    padding: 6px 12px;
  }
  .hero-brand-subtitle {
    font-size: clamp(12px, 4vw, 18px);
    gap: 8px;
  }
  .hero-brand-subtitle::before,
  .hero-brand-subtitle::after {
    width: 22px;
  }
  .toolbar {
    grid-template-columns: 1fr;
    padding: 12px;
  }
  .search-field,
  .filter-field {
    width: 100%;
    min-width: 0;
  }
  .product-card {
    width: auto;
  }
  .detail-layout {
    grid-template-columns: 1fr;
  }
  .detail-media {
    aspect-ratio: 1 / 1;
    min-height: 260px;
    max-height: 56vh;
  }
}
@media (prefers-reduced-motion: reduce) {
  * {
    transition: none !important;
    animation: none !important;
  }
  body::before {
    animation: none !important;
  }
}
`;

function ensureThemeCss() {
  const existing = document.getElementById("catalog-theme");
  if (existing) {
    if (existing.textContent !== THEME_CSS) {
      existing.textContent = THEME_CSS;
    }
    return;
  }
  const style = document.createElement("style");
  style.id = "catalog-theme";
  style.textContent = THEME_CSS;
  document.head.appendChild(style);
}

ensureThemeCss();

const DEMO_PRODUCTS = [
  {
    Codigo: "1",
    Nome: "Lustre Pendulo Crystal",
    Descricao: "Estrutura metalica com acabamento premium e leitura visual elegante.",
    Categoria: "Lustres",
    URLFoto:
      "https://images.unsplash.com/photo-1565558631492-a199066cfffa?w=900&h=700&fit=crop",
    Especificacoes: "Altura 60cm | Diametro 40cm | 6x E14 | 3.5kg",
  },
  {
    Codigo: "2",
    Nome: "Arandela Minimal",
    Descricao: "Arandela de parede compacta para corredores e quartos.",
    Categoria: "Arandelas",
    URLFoto:
      "https://images.unsplash.com/photo-1540932239986-30128078f3c5?w=900&h=700&fit=crop",
    Especificacoes: "Altura 25cm | Profundidade 15cm | 1x G9 | 0.8kg",
  },
  {
    Codigo: "3",
    Nome: "Pendente Industrial",
    Descricao: "Design urbano com foco no feixe de luz para mesas e bancadas.",
    Categoria: "Pendentes",
    URLFoto:
      "https://images.unsplash.com/photo-1516159260535-cb0881c9a5d4?w=900&h=700&fit=crop",
    Especificacoes: "Altura 35cm | Diametro 20cm | 1x E27 | 0.6kg",
  },
  {
    Codigo: "4",
    Nome: "Plafon LED Round",
    Descricao: "Peca de teto com alta eficiencia e instalacao simplificada.",
    Categoria: "Plafons",
    URLFoto:
      "https://images.unsplash.com/photo-1606399676374-d1ce13896357?w=900&h=700&fit=crop",
    Especificacoes: "Diametro 30cm | LED 18W | 1200 lumens | 1.2kg",
  },
  {
    Codigo: "5",
    Nome: "Candelabro Classico",
    Descricao: "Volume ornamental para salas de jantar e halls de entrada.",
    Categoria: "Candelabros",
    URLFoto:
      "https://images.unsplash.com/photo-1578500494198-246f612d03b3?w=900&h=700&fit=crop",
    Especificacoes: "Altura 50cm | Largura 40cm | 5x E14 | 2.1kg",
  },
  {
    Codigo: "6",
    Nome: "Luminaria de Piso",
    Descricao: "Trabalho de base em madeira para composicao de leitura e estar.",
    Categoria: "Luminarias de Piso",
    URLFoto:
      "https://images.unsplash.com/photo-1565558632069-b8b656b521b5?w=900&h=700&fit=crop",
    Especificacoes: "Altura 160cm | Base 50x50cm | 1x E27 | 2.8kg",
  },
];

function normalizeText(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim()
    .toLowerCase();
}

function getField(item, aliases, fallback = "") {
  if (!item || typeof item !== "object") return fallback;
  const lookup = {};

  Object.keys(item).forEach((key) => {
    lookup[normalizeText(key)] = item[key];
  });

  for (const alias of aliases) {
    const value = lookup[normalizeText(alias)];
    if (value !== undefined && value !== null && String(value).trim() !== "") {
      return value;
    }
  }

  return fallback;
}

function normalizeProduct(item, index) {
  const code = String(
    getField(item, ["Codigo", "Code", "SKU", "id"], index + 1)
  );
  const embeddedPhotos = {
    white_background: String(
      getField(item, ["FotoBranco", "white_background", "WhiteBackground"], "")
    ),
    ambient: String(getField(item, ["FotoAmbient", "ambient", "Ambient"], "")),
    measures: String(getField(item, ["FotoMedidas", "measures", "Measures"], "")),
  };
  const hasEmbeddedPhotos = Object.values(embeddedPhotos).some((value) => value.trim() !== "");

  return {
    id: `item-${index + 1}`,
    code,
    name: String(getField(item, ["Nome", "Produto", "Name"], `Produto ${index + 1}`)),
    description: String(getField(item, ["Descricao", "Description", "Resumo"], "")),
    category: String(getField(item, ["Categoria", "Category", "Tipo"], "Sem categoria")),
    cover: String(getField(item, ["URLFoto", "Imagem", "Image", "Foto", "URL"], "")),
    specs: String(getField(item, ["Especificacoes", "Especificacao", "Specs", "Detalhes"], "")),
    photos: hasEmbeddedPhotos ? embeddedPhotos : null,
  };
}

const DEFAULT_PRODUCTS = DEMO_PRODUCTS.map((item, index) => normalizeProduct(item, index));

function fallbackPhotos(code) {
  return {
    white_background: `https://placehold.co/240x240?text=Branco+${encodeURIComponent(code)}`,
    ambient: `https://placehold.co/240x240?text=Ambient+${encodeURIComponent(code)}`,
    measures: `https://placehold.co/240x240?text=Medidas+${encodeURIComponent(code)}`,
  };
}

function imageOrderKey(name) {
  const value = String(name || "").toLowerCase();
  if (value.includes("descri") || value.includes("description")) {
    return [0, value];
  }
  if (/^\d+\s*-\s*[^\d]/.test(value)) {
    return [1, value];
  }
  const variantMatch = value.match(/^(\d+)(?:\s*[-_]\s*([1-4]))?\./);
  if (variantMatch) {
    const variant = variantMatch[2] ? Number(variantMatch[2]) : 0;
    return [2, variant, value];
  }
  return [3, value];
}

function buildGalleryEntries(item, photos, apiImages) {
  if (Array.isArray(apiImages) && apiImages.length > 0) {
    const ordered = apiImages.slice().sort((left, right) => {
      const a = imageOrderKey(left && left.name);
      const b = imageOrderKey(right && right.name);
      for (let i = 0; i < Math.max(a.length, b.length); i += 1) {
        const av = a[i];
        const bv = b[i];
        if (av === undefined) return -1;
        if (bv === undefined) return 1;
        if (av < bv) return -1;
        if (av > bv) return 1;
      }
      return 0;
    });

    return ordered.map((img, idx) => ({
      key: `${img.name || "img"}-${idx}`,
      label: img.name || `Imagem ${idx + 1}`,
      url: img.url,
    }));
  }

  const candidates = [
    { label: "Capa", url: item && item.cover },
    { label: "Fundo branco", url: photos && photos.white_background },
    { label: "Ambientada", url: photos && photos.ambient },
    { label: "Medidas", url: photos && photos.measures },
  ];
  const seen = new Set();
  const entries = [];
  for (const candidate of candidates) {
    const url = candidate.url || "";
    if (!url || seen.has(url)) continue;
    seen.add(url);
    entries.push({
      key: `${candidate.label}-${entries.length}`,
      label: candidate.label,
      url,
    });
  }
  if (entries.length === 0) {
    entries.push({
      key: "sem-imagem",
      label: "Sem imagem",
      url: "https://placehold.co/1200x900?text=Sem+Imagem",
    });
  }
  return entries;
}

async function fetchFromBases(buildUrl) {
  for (const base of API_BASES) {
    try {
      const response = await fetch(buildUrl(base));
      if (!response.ok) continue;
      return await response.json();
    } catch (error) {
      // try next base
    }
  }
  return null;
}

function readPersistedUiState() {
  const fallback = { query: "", category: "Todas", selectedCode: "" };
  if (typeof window === "undefined" || !window.sessionStorage) {
    return fallback;
  }

  try {
    const raw = window.sessionStorage.getItem(UI_STATE_STORAGE_KEY);
    if (!raw) return fallback;
    const parsed = JSON.parse(raw);
    return {
      query: typeof parsed.query === "string" ? parsed.query : "",
      category:
        typeof parsed.category === "string" && parsed.category.trim()
          ? parsed.category
          : "Todas",
      selectedCode: typeof parsed.selectedCode === "string" ? parsed.selectedCode : "",
    };
  } catch (error) {
    return fallback;
  }
}

function App() {
  const initialUiState = useMemo(() => readPersistedUiState(), []);
  const [products, setProducts] = useState(DEFAULT_PRODUCTS);
  const [photosByCode, setPhotosByCode] = useState({});
  const [galleryByCode, setGalleryByCode] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [usedDemo, setUsedDemo] = useState(true);
  const [query, setQuery] = useState(initialUiState.query);
  const [category, setCategory] = useState(initialUiState.category);
  const [selectedCode, setSelectedCode] = useState(initialUiState.selectedCode);

  useEffect(() => {
    if (typeof window === "undefined" || !window.sessionStorage) return;
    try {
      window.sessionStorage.setItem(
        UI_STATE_STORAGE_KEY,
        JSON.stringify({ query, category, selectedCode })
      );
    } catch (error) {
      // ignore storage failures
    }
  }, [query, category, selectedCode]);

  useEffect(() => {
    if (typeof window === "undefined" || !window.sessionStorage) return;
    if ("scrollRestoration" in window.history) {
      window.history.scrollRestoration = "manual";
    }

    const saveScroll = () => {
      try {
        window.sessionStorage.setItem(
          SCROLL_STORAGE_KEY,
          String(window.scrollY || window.pageYOffset || 0)
        );
      } catch (error) {
        // ignore storage failures
      }
    };

    const restoreScroll = () => {
      const raw = window.sessionStorage.getItem(SCROLL_STORAGE_KEY);
      const y = Number(raw);
      if (Number.isFinite(y) && y > 0) {
        window.scrollTo(0, y);
      }
    };

    restoreScroll();
    const timerA = window.setTimeout(restoreScroll, 120);
    const timerB = window.setTimeout(restoreScroll, 500);

    window.addEventListener("beforeunload", saveScroll);
    window.addEventListener("pagehide", saveScroll);

    return () => {
      window.clearTimeout(timerA);
      window.clearTimeout(timerB);
      window.removeEventListener("beforeunload", saveScroll);
      window.removeEventListener("pagehide", saveScroll);
    };
  }, []);

  useEffect(() => {
    let active = true;

    async function loadProducts() {
      setLoading(true);

      const localData = await fetchFromBases((base) => `${base}/catalog/local/produtos`);
      if (!active) return;

      if (Array.isArray(localData) && localData.length > 0) {
        setProducts(localData.map((item, index) => normalizeProduct(item, index)));
        setUsedDemo(false);
        setError("");
      } else {
        setProducts(DEFAULT_PRODUCTS);
        setUsedDemo(true);
        setError("Nao foi possivel carregar produtos locais. Exibindo modo demo.");
      }

      setLoading(false);
    }

    loadProducts();

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (products.length === 0) return;
    let active = true;

    async function loadPhotos() {
      if (usedDemo) {
        const demoEntries = products.map((product) => {
          const code = product.code || product.id;
          return [code, fallbackPhotos(code)];
        });
        if (!active) return;
        setPhotosByCode(Object.fromEntries(demoEntries));
        return;
      }

      const localEntries = [];
      const productsWithoutPhotos = [];

      for (const product of products) {
        const code = product.code || product.id;
        const embedded = product.photos;
        if (
          embedded &&
          (embedded.white_background || embedded.ambient || embedded.measures)
        ) {
          localEntries.push([code, embedded]);
        } else {
          productsWithoutPhotos.push(product);
        }
      }

      if (productsWithoutPhotos.length === 0) {
        if (!active) return;
        setPhotosByCode(Object.fromEntries(localEntries));
        return;
      }

      const fetchedEntries = await Promise.all(
        productsWithoutPhotos.map(async (product) => {
          const code = product.code || product.id;
          const payload = await fetchFromBases(
            (base) => `${base}/catalog/photos?code=${encodeURIComponent(code)}`
          );

          if (
            payload &&
            typeof payload === "object" &&
            (payload.white_background || payload.ambient || payload.measures)
          ) {
            return [code, payload];
          }

          return [code, fallbackPhotos(code)];
        })
      );

      if (!active) return;

      setPhotosByCode(Object.fromEntries([...localEntries, ...fetchedEntries]));
    }

    loadPhotos();

    return () => {
      active = false;
    };
  }, [products, usedDemo]);

  useEffect(() => {
    if (!selectedCode) return;
    if (galleryByCode[selectedCode]) return;
    let active = true;

    async function loadGallery() {
      const payload = await fetchFromBases(
        (base) => `${base}/catalog/produtos/${encodeURIComponent(selectedCode)}/imagens`
      );
      if (!active) return;
      if (payload && Array.isArray(payload.imagens) && payload.imagens.length > 0) {
        setGalleryByCode((current) =>
          Object.assign({}, current, { [selectedCode]: payload.imagens })
        );
      } else {
        setGalleryByCode((current) => Object.assign({}, current, { [selectedCode]: [] }));
      }
    }

    loadGallery();

    return () => {
      active = false;
    };
  }, [selectedCode, galleryByCode]);

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

  const filteredProducts = useMemo(() => {
    const search = normalizeText(query);

    return products.filter((item) => {
      const categoryOk = category === "Todas" || item.category === category;
      const textBlob = normalizeText(`${item.name} ${item.code} ${item.description} ${item.category}`);
      const queryOk = !search || textBlob.includes(search);
      return categoryOk && queryOk;
    });
  }, [products, query, category]);

  const loadedPhotoCount = useMemo(() => Object.keys(photosByCode).length, [photosByCode]);
  const selectedProduct = useMemo(
    () => products.find((item) => String(item.code || item.id) === String(selectedCode)) || null,
    [products, selectedCode]
  );
  const selectedPhotos = selectedProduct
    ? photosByCode[selectedProduct.code || selectedProduct.id]
    : null;
  const selectedGalleryEntries = useMemo(
    () =>
      selectedProduct
        ? buildGalleryEntries(
            selectedProduct,
            selectedPhotos,
            galleryByCode[selectedProduct.code || selectedProduct.id]
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
          <div className="hero-kicker">Catalogo de produtos</div>
          <div className="hero-brand" aria-label="Marca NITROLUX">
            <p className="hero-brand-name">NITROLUX</p>
            <p className="hero-brand-subtitle">Sua vida com mais brilho</p>
          </div>
        </div>
      </header>

      <main className="content-wrap">
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

            {error && <div className="banner banner-warning">{error}</div>}
            {usedDemo && (
              <div className="banner banner-info">
                Dica: ao conectar uma planilha publica, os cards sao atualizados automaticamente.
              </div>
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

            {filteredProducts.length > 0 ? (
              <section className="catalog-grid">
                {filteredProducts.map((item, index) => (
                  <ProductCard
                    key={`${item.code}-${item.id}-${index}`}
                    item={item}
                    photos={photosByCode[item.code]}
                    index={index}
                    onOpen={() => setSelectedCode(item.code || item.id)}
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
  return (
    <article className="product-card" style={{ "--stagger": `${Math.min(index * 70, 700)}ms` }}>
      <button
        type="button"
        className="card-hitbox"
        onClick={onOpen}
      >
        <div className="media">
          <img
            src={
              item.cover ||
              (photos && (photos.white_background || photos.ambient || photos.measures)) ||
              "https://placehold.co/900x700?text=Sem+Imagem"
            }
            alt={item.name || "Produto"}
            loading="lazy"
          />
          <div className="media-overlay"></div>
          <span className="chip chip-code">#{item.code}</span>
          <span className="chip chip-category">{item.category}</span>
        </div>

        <div className="card-body">
          <h3>{item.name || "Produto"}</h3>
          <p className="description">
            {item.description || "Descricao indisponivel para este produto."}
          </p>

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
  const gallery = galleryEntries && galleryEntries.length > 0
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
            src={(activeImage && activeImage.url) || "https://placehold.co/1200x900?text=Sem+Imagem"}
            alt={item.name || "Produto"}
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
          >
            <img src={image.url || "https://placehold.co/240x240?text=Sem+foto"} alt={image.label} />
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
      <img src={image || "https://placehold.co/240x240?text=Sem+foto"} alt={label} loading="lazy" />
      <figcaption>{label}</figcaption>
    </figure>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
