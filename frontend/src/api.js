const BASE = '/api'

async function request(path, options = {}) {
  let response
  try {
    response = await fetch(BASE + path, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    })
  } catch {
    throw new ApiError('Cannot reach the tool server. Is it running on :8765?', 0)
  }

  const text = await response.text()
  let body
  try {
    body = text ? JSON.parse(text) : null
  } catch {
    throw new ApiError(`Server sent something that is not JSON (${response.status}).`, response.status)
  }

  if (!response.ok && (body === null || body.ok !== false)) {
    throw new ApiError(body?.detail || `Request failed (${response.status}).`, response.status)
  }
  return body
}

export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.status = status
  }
}

export const api = {
  catalog: () => request('/catalog'),
  tool: (id) => request(`/tools/${encodeURIComponent(id)}`),
  run: (id, params) =>
    request(`/tools/${encodeURIComponent(id)}/run`, {
      method: 'POST',
      body: JSON.stringify({ params }),
    }),
  reload: () => request('/reload', { method: 'POST' }),
}
