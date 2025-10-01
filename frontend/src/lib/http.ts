// src/lib/http.ts
const API_BASE = import.meta.env.VITE_API_BASE; // e.g. https://enthusiast-api.herokuapp.com
let csrfPrimed = false;

export async function ensureCsrf() {
  if (csrfPrimed) return;
  await fetch(`${API_BASE}/api/auth/csrf/`, { credentials: 'include' });
  csrfPrimed = true;
}

export function getCookie(name: string) {
  return document.cookie
    .split('; ')
    .find(c => c.startsWith(name + '='))?.split('=')[1];
}

export async function postJson(path: string, body: unknown) {
  const csrftoken = getCookie('csrftoken') ?? '';
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrftoken,
    },
    body: JSON.stringify(body),
  });
  return res;
}
