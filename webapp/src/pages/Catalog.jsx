import { useEffect, useMemo, useState } from "react";
import { ShoppingCart, Check, Minus, Plus, ArrowLeft } from "lucide-react";
import { api } from "../api";
import { DropLoader, SkeletonCatalog } from "../components/Loaders";
import { hapticImpact, hapticSuccess } from "../telegram";

// 17-bo'lim: kutilganidan sezilarli katta miqdorlarda yumshoq eslatma —
// buyurtmani bloklamaydi, faqat bir marta ko'z bilan tekshirish imkonini beradi.
const LARGE_QTY_HINT = 10;

export default function Catalog() {
  const [products, setProducts] = useState(null);
  const [cart, setCart] = useState({}); // { [productId]: qty }
  const [screen, setScreen] = useState("catalog"); // catalog | confirm | success
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [successData, setSuccessData] = useState(null);

  useEffect(() => {
    api
      .catalog()
      .then(setProducts)
      .catch((e) => setError(e.message));
  }, []);

  const cartItems = useMemo(() => {
    if (!products) return [];
    return Object.entries(cart)
      .filter(([, qty]) => qty > 0)
      .map(([id, qty]) => {
        const product = products.find((p) => p.id === Number(id));
        return product ? { ...product, qty } : null;
      })
      .filter(Boolean);
  }, [cart, products]);

  const totalCount = cartItems.reduce((sum, i) => sum + i.qty, 0);
  const totalAmount = cartItems.reduce((sum, i) => sum + i.qty * i.price, 0);

  function changeQty(productId, delta) {
    hapticImpact("light");
    setCart((prev) => {
      const next = Math.max(0, (prev[productId] || 0) + delta);
      return { ...prev, [productId]: next };
    });
  }

  async function submitOrder() {
    setSubmitting(true);
    setError(null);
    try {
      const items = cartItems.map((i) => ({ product_id: i.id, quantity: i.qty }));
      const result = await api.createOrder(items);
      hapticSuccess();
      setSuccessData(result);
      setScreen("success");
      setCart({});
    } catch (e) {
      setError(e.message);
    } finally {
      setSubmitting(false);
    }
  }

  if (error && !products) {
    return (
      <div className="screen">
        <p className="hint">Xatolik: {error}</p>
      </div>
    );
  }

  if (!products) {
    return (
      <div className="screen">
        <div className="title">🛍 Katalog</div>
        <SkeletonCatalog />
      </div>
    );
  }

  if (screen === "success") {
    return (
      <div className="screen">
        <DropLoader />
        <div className="title" style={{ textAlign: "center" }}>
          <Check size={22} style={{ verticalAlign: "middle", color: "#15803d" }} /> Buyurtma qabul qilindi
        </div>
        <p className="hint" style={{ whiteSpace: "pre-line", textAlign: "center" }}>
          {successData?.summary_text}
        </p>
        <button className="button" onClick={() => setScreen("catalog")} style={{ marginTop: 16 }}>
          Yangi buyurtma
        </button>
      </div>
    );
  }

  if (screen === "confirm") {
    return (
      <div className="screen">
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
          <button
            className="qty-btn"
            style={{ background: "var(--secondary-bg)", color: "var(--text)" }}
            onClick={() => setScreen("catalog")}
          >
            <ArrowLeft size={16} />
          </button>
          <div className="title" style={{ margin: 0 }}>
            Buyurtma tafsiloti
          </div>
        </div>

        {cartItems.map((item) => (
          <div key={item.id} className="summary-row">
            <span>
              {item.name} × {item.qty}
              {item.qty >= LARGE_QTY_HINT && (
                <span className="hint" style={{ display: "block", fontSize: 12 }}>
                  ⚠️ Miqdor katta — tekshirib ko'ring
                </span>
              )}
            </span>
            <span>{(item.qty * item.price).toLocaleString("ru-RU")} so'm</span>
          </div>
        ))}

        <div className="summary-total">
          <span>Jami</span>
          <span>{totalAmount.toLocaleString("ru-RU")} so'm</span>
        </div>

        {error && <p className="hint" style={{ color: "#b91c1c" }}>{error}</p>}

        <button className="button" onClick={submitOrder} disabled={submitting}>
          {submitting ? "Yuborilmoqda..." : "✅ Tasdiqlash"}
        </button>
      </div>
    );
  }

  return (
    <div className="screen">
      <div className="title">🛍 Katalog</div>
      <div className="catalog-grid">
        {products.map((p) => (
          <div key={p.id} className="product-card">
            {p.photo_url ? (
              <img src={p.photo_url} alt={p.name} />
            ) : (
              <div className="placeholder-img" />
            )}
            <div className="body">
              <div className="name">{p.name}</div>
              <div className="price">
                {p.price.toLocaleString("ru-RU")} so'm/{p.unit}
              </div>
              <div className="qty-row">
                <button className="qty-btn" onClick={() => changeQty(p.id, -1)}>
                  <Minus size={16} />
                </button>
                <span className="qty-value">{cart[p.id] || 0}</span>
                <button className="qty-btn" onClick={() => changeQty(p.id, 1)}>
                  <Plus size={16} />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {totalCount > 0 && (
        <div className="cart-bar" onClick={() => setScreen("confirm")}>
          <span>
            <ShoppingCart size={18} style={{ verticalAlign: "middle", marginRight: 8 }} />
            {totalCount} ta mahsulot — {totalAmount.toLocaleString("ru-RU")} so'm
          </span>
          <span>Davom etish →</span>
        </div>
      )}
    </div>
  );
}
