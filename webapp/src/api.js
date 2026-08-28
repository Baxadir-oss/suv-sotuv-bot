import { getInitData } from "./telegram";

async function request(path, options = {}) {
  const res = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-Telegram-Init-Data": getInitData(),
      ...(options.headers || {}),
    },
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    const error = new Error(text || `So'rov muvaffaqiyatsiz (${res.status})`);
    error.status = res.status;
    throw error;
  }
  return res.json();
}

export const api = {
  me: () => request("/api/me"),
  catalog: () => request("/api/catalog"),
  createOrder: (items) =>
    request("/api/order", { method: "POST", body: JSON.stringify({ items }) }),
  reports: (start, end) => request(`/api/reports?start=${start}&end=${end}`),
  searchShops: (q) => request(`/api/shops/search?q=${encodeURIComponent(q)}`),
};
