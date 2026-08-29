import { useEffect, useRef, useState } from "react";
import { Plus, ChevronUp, ChevronDown, Eye, EyeOff, X, Camera } from "lucide-react";
import { api } from "../api";
import { fileToBase64 } from "../fileUtils";
import { DropLoader, SkeletonList } from "../components/Loaders";

const EMPTY_FORM = { name: "", price: "", unit: "blok", photo_base64: null };

export default function AgentProducts() {
  const [products, setProducts] = useState(null);
  const [error, setError] = useState(null);
  const [editing, setEditing] = useState(null); // null | "new" | product object
  const [form, setForm] = useState(EMPTY_FORM);
  const [preview, setPreview] = useState(null);
  const [saving, setSaving] = useState(false);
  const fileInputRef = useRef(null);

  function load() {
    api
      .agentProducts()
      .then(setProducts)
      .catch((e) => setError(e.message));
  }

  useEffect(load, []);

  function openNew() {
    setForm(EMPTY_FORM);
    setPreview(null);
    setEditing("new");
  }

  function openEdit(p) {
    setForm({ name: p.name, price: String(p.price), unit: p.unit, photo_base64: null });
    setPreview(p.photo_url);
    setEditing(p);
  }

  async function handlePhoto(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    const base64 = await fileToBase64(file);
    setForm((f) => ({ ...f, photo_base64: base64 }));
    setPreview(base64);
  }

  async function save() {
    setSaving(true);
    setError(null);
    try {
      const payload = { name: form.name.trim(), price: Number(form.price), unit: form.unit.trim() };
      if (form.photo_base64) payload.photo_base64 = form.photo_base64;

      if (editing === "new") {
        await api.createAgentProduct(payload);
      } else {
        await api.updateAgentProduct(editing.id, payload);
      }
      setEditing(null);
      load();
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  }

  async function toggleVisible(p) {
    setProducts((prev) => prev.map((x) => (x.id === p.id ? { ...x, is_available: !x.is_available } : x)));
    try {
      await api.updateAgentProduct(p.id, { is_available: !p.is_available });
    } catch (e) {
      setError(e.message);
      load();
    }
  }

  async function move(p, direction) {
    const idx = products.findIndex((x) => x.id === p.id);
    const swapIdx = direction === "up" ? idx - 1 : idx + 1;
    if (swapIdx < 0 || swapIdx >= products.length) return;

    const next = [...products];
    [next[idx], next[swapIdx]] = [next[swapIdx], next[idx]];
    setProducts(next);
    try {
      await api.reorderAgentProducts(next.map((x) => x.id));
    } catch (e) {
      setError(e.message);
      load();
    }
  }

  if (editing) {
    return (
      <div className="screen">
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
          <div className="title" style={{ margin: 0 }}>
            {editing === "new" ? "Yangi mahsulot" : "Mahsulotni tahrirlash"}
          </div>
          <button
            className="qty-btn"
            style={{ background: "var(--secondary-bg)", color: "var(--text)" }}
            onClick={() => setEditing(null)}
          >
            <X size={16} />
          </button>
        </div>

        <div
          onClick={() => fileInputRef.current?.click()}
          style={{
            aspectRatio: "1 / 1",
            maxWidth: 160,
            borderRadius: 14,
            background: "var(--brand-100)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            overflow: "hidden",
            marginBottom: 14,
            cursor: "pointer",
          }}
        >
          {preview ? (
            <img src={preview} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
          ) : (
            <Camera size={28} color="#0369A1" />
          )}
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          capture="environment"
          style={{ display: "none" }}
          onChange={handlePhoto}
        />

        <label className="hint">Nomi</label>
        <input
          className="search-input"
          value={form.name}
          onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
          placeholder="Masalan: 19L karboy"
        />

        <label className="hint">Narxi (so'm)</label>
        <input
          className="search-input"
          type="number"
          inputMode="numeric"
          value={form.price}
          onChange={(e) => setForm((f) => ({ ...f, price: e.target.value }))}
          placeholder="25000"
        />

        <label className="hint">Birligi</label>
        <input
          className="search-input"
          value={form.unit}
          onChange={(e) => setForm((f) => ({ ...f, unit: e.target.value }))}
          placeholder="blok, karobka, litr..."
        />

        {error && <p className="hint" style={{ color: "#b91c1c" }}>{error}</p>}

        <button className="button" onClick={save} disabled={saving || !form.name || !form.price}>
          {saving ? "Saqlanmoqda..." : "✅ Saqlash"}
        </button>
      </div>
    );
  }

  return (
    <div className="screen">
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
        <div className="title" style={{ margin: 0 }}>
          📦 Mahsulotlar
        </div>
        <button className="qty-btn" style={{ width: 36, height: 36 }} onClick={openNew}>
          <Plus size={18} />
        </button>
      </div>

      {error && <p className="hint">Xatolik: {error}</p>}
      {!products && <SkeletonList />}
      {products?.length === 0 && (
        <p className="hint">Hozircha mahsulot yo'q. Yuqoridagi ➕ tugmasi orqali qo'shing.</p>
      )}

      {products?.map((p) => (
        <div key={p.id} className="shop-card" style={{ opacity: p.is_available ? 1 : 0.5 }}>
          {p.photo_url ? <img src={p.photo_url} alt={p.name} /> : <div className="placeholder-img" />}
          <div className="info" onClick={() => openEdit(p)} style={{ cursor: "pointer" }}>
            <div className="name">{p.name}</div>
            <div className="meta">
              {p.price.toLocaleString("ru-RU")} so'm/{p.unit}
            </div>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <button className="qty-btn" style={{ width: 26, height: 26 }} onClick={() => move(p, "up")}>
              <ChevronUp size={14} />
            </button>
            <button className="qty-btn" style={{ width: 26, height: 26 }} onClick={() => move(p, "down")}>
              <ChevronDown size={14} />
            </button>
          </div>
          <button
            className="qty-btn"
            style={{ width: 30, height: 30, background: p.is_available ? "#15803d" : "#9ca3af" }}
            onClick={() => toggleVisible(p)}
          >
            {p.is_available ? <Eye size={14} /> : <EyeOff size={14} />}
          </button>
        </div>
      ))}
    </div>
  );
  }
