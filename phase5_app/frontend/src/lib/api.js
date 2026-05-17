const BASE = '/api'

async function get(path) {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`API error ${res.status}: ${path}`)
  return res.json()
}

export const api = {
  stats:           ()   => get('/meta/stats'),
  sectors:         ()   => get('/meta/sectors'),
  companies:       (params = {}) => {
    const q = new URLSearchParams(
      Object.fromEntries(Object.entries(params).filter(([, v]) => v))
    ).toString()
    return get(`/companies${q ? '?' + q : ''}`)
  },
  company:         (id) => get(`/company/${id}`),
  forecast:        (id) => get(`/company/${id}/forecast`),
  shap:            (id) => get(`/company/${id}/shap`),
  brief:           (id) => get(`/company/${id}/brief`),
}
