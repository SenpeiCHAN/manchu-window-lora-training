export const API = import.meta.env.VITE_API_BASE || '/api'

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = init?.body instanceof FormData ? init.headers : { 'Content-Type': 'application/json', ...init?.headers }
  const response = await fetch(`${API}${path}`, { ...init, headers })
  if (!response.ok) {
    const content = await response.text()
    try { throw new Error(JSON.parse(content).detail || content) }
    catch (error) { if (error instanceof SyntaxError) throw new Error(content); throw error }
  }
  return response.json()
}
