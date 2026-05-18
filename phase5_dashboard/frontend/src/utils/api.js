// src/utils/api.js
// All API calls go through here — easy to swap base URL for prod

const BASE = '/api'

async function get(path) {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`)
  return res.json()
}

export const api = {
  stats:           ()   => get('/stats'),
  sectors:         ()   => get('/sectors'),
  companies:       (params = {}) => {
    const qs = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v != null && v !== '')
    ).toString()
    return get(`/companies${qs ? '?' + qs : ''}`)
  },
  company:         (id) => get(`/company/${id}`),
  signals:         (id) => get(`/company/${id}/signals`),
  forecast:        (id) => get(`/company/${id}/forecast`),
  shap:            (id) => get(`/company/${id}/shap`),
  brief:           (id) => get(`/company/${id}/brief`),
  ablation:        ()   => get('/ablation'),
}
