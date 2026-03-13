// @ts-check

(function attachCatalogApi(global) {
  const Catalog = global.Catalog || (global.Catalog = {});
  const { API_BASES, REQUEST_TIMEOUT_MS } = Catalog;

  async function fetchWithTimeout(url) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
    try {
      return await fetch(url, { signal: controller.signal });
    } finally {
      clearTimeout(timeoutId);
    }
  }

  async function fetchFromBases(buildUrl) {
    let lastError = null;

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
        return await response.json();
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

  Object.assign(Catalog, {
    fetchFromBases,
  });
})(window);