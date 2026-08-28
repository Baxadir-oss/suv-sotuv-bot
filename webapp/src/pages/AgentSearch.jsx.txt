import { useEffect, useState } from "react";
import { Search, Phone } from "lucide-react";
import { api } from "../api";
import { SkeletonList } from "../components/Loaders";

export default function AgentSearch() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const handle = setTimeout(() => {
      setError(null);
      api
        .searchShops(query)
        .then(setResults)
        .catch((e) => setError(e.message));
    }, 250); // real-time, lekin har harfda so'rov yubormaslik uchun kichik debounce
    return () => clearTimeout(handle);
  }, [query]);

  return (
    <div className="screen">
      <div className="title">🔎 Do'konlarni qidirish</div>
      <input
        className="search-input"
        placeholder="Nomi, telefon yoki hudud bo'yicha qidiring..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        autoFocus
      />

      {error && <p className="hint">Xatolik: {error}</p>}
      {!results && !error && <SkeletonList />}

      {results && results.length === 0 && <p className="hint">Hech narsa topilmadi.</p>}

      {results?.map((shop) => (
        <div key={shop.id} className="shop-card">
          {shop.photo_url ? (
            <img src={shop.photo_url} alt={shop.shop_name} />
          ) : (
            <div className="placeholder-img" />
          )}
          <div className="info">
            <div className="name">{shop.shop_name}</div>
            <div className="meta">
              {shop.owner_name} · {shop.total_orders} buyurtma
            </div>
            <div style={{ marginTop: 4 }}>
              {shop.is_blocked ? (
                <span className="badge blocked">bloklangan</span>
              ) : shop.is_pending ? (
                <span className="badge pending">lokatsiya kutilmoqda</span>
              ) : (
                <span className="badge ok">faol</span>
              )}
            </div>
          </div>
          <a href={`tel:${shop.phone}`} className="qty-btn" style={{ textDecoration: "none" }}>
            <Phone size={14} />
          </a>
        </div>
      ))}
    </div>
  );
}
