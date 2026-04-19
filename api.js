// src/data/api.js
// Toutes les fonctions d'appel à l'API FastAPI

const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || "Erreur API");
  }
  if (res.status === 204) return null;
  return res.json();
}

// ─── Établissements ──────────────────────────────────────────
export const getEtablissements = () => request("/etablissements/");

// ─── Campagnes ───────────────────────────────────────────────
export const getCampagnes = () => request("/campagnes/");
export const createCampagne = (data) =>
  request("/campagnes/", { method: "POST", body: JSON.stringify(data) });
export const cloturerCampagne = (id) =>
  request(`/campagnes/${id}/cloturer`, { method: "PATCH" });

// ─── Veilles ─────────────────────────────────────────────────
export const getVeilles = (params = {}) => {
  const qs = new URLSearchParams(params).toString();
  return request(`/veilles/${qs ? "?" + qs : ""}`);
};
export const getVeille = (id) => request(`/veilles/${id}`);
export const createVeille = (data) =>
  request("/veilles/", { method: "POST", body: JSON.stringify(data) });
export const updateVeille = (id, data) =>
  request(`/veilles/${id}`, { method: "PUT", body: JSON.stringify(data) });
export const soumettreVeille = (id) =>
  request(`/veilles/${id}/soumettre`, { method: "PATCH" });
export const deleteVeille = (id) =>
  request(`/veilles/${id}`, { method: "DELETE" });

// ─── Dashboard ───────────────────────────────────────────────
export const getKpis = (params = {}) => {
  const qs = new URLSearchParams(params).toString();
  return request(`/dashboard/kpis${qs ? "?" + qs : ""}`);
};
export const getParEtablissement = (params = {}) => {
  const qs = new URLSearchParams(params).toString();
  return request(`/dashboard/par-etablissement${qs ? "?" + qs : ""}`);
};
export const getParPathologie = (params = {}) => {
  const qs = new URLSearchParams(params).toString();
  return request(`/dashboard/par-pathologie${qs ? "?" + qs : ""}`);
};
