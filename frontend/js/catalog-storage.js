// @ts-check

(function attachCatalogStorage(global) {
  const Catalog = global.Catalog || (global.Catalog = {});
  const { UI_STATE_STORAGE_KEY } = Catalog;

  function readPersistedUiState() {
    const fallback = { query: "", category: "Todas", selectedCode: "" };
    if (typeof window === "undefined" || !window.localStorage) {
      return fallback;
    }

    try {
      const raw = window.localStorage.getItem(UI_STATE_STORAGE_KEY);
      if (!raw) return fallback;
      const parsed = JSON.parse(raw);

      return {
        query: typeof parsed.query === "string" ? parsed.query : fallback.query,
        category:
          typeof parsed.category === "string" && parsed.category
            ? parsed.category
            : fallback.category,
        selectedCode:
          typeof parsed.selectedCode === "string"
            ? parsed.selectedCode
            : fallback.selectedCode,
      };
    } catch (error) {
      console.warn("Nao foi possivel ler estado de UI persistido.", error);
      return fallback;
    }
  }

  function persistUiState(state) {
    if (typeof window === "undefined" || !window.localStorage) {
      return;
    }

    try {
      window.localStorage.setItem(
        UI_STATE_STORAGE_KEY,
        JSON.stringify({
          query: state.query || "",
          category: state.category || "Todas",
          selectedCode: state.selectedCode || "",
        })
      );
    } catch (error) {
      console.warn("Nao foi possivel persistir estado de UI.", error);
    }
  }

  Object.assign(Catalog, {
    readPersistedUiState,
    persistUiState,
  });
})(window);