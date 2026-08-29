import { useEffect, useRef, useState } from "react";
import { Megaphone, Tag, Bell, Camera, X } from "lucide-react";
import { api } from "../api";
import { fileToBase64 } from "../fileUtils";
import { DropLoader } from "../components/Loaders";

const TEMPLATES = [
  { key: "new", label: "Yangi mahsulot", icon: Megaphone, sample: "Yangi keldi: [nom], [narx] so'm" },
  { key: "discount", label: "Chegirma/aksiya", icon: Tag, sample: "Bugun [mahsulot]ga chegirma bor" },
  { key: "reminder", label: "Eslatma", icon: Bell, sample: "Issiq kunlarda suv zaxirasini oshirib qo'ying" },
];

export default function AgentBroadcast() {
  const [status, setStatus] = useState(null);
  const [template, setTemplate] = useState(null);
  const [text, setText] = useState("");
  const [photoBase64, setPhotoBase64] = useState(null);
  const [preview, setPreview] = useState(null);
  const [sending, setSending] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    api
      .broadcastStatus()
      .then(setStatus)
      .catch((e) => setError(e.message));
  }, []);

  async function handlePhoto(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    const base64 = await fileToBase64(file);
    setPhotoBase64(base64);
    setPreview(base64);
  }

  async function send() {
    setSending(true);
    setError(null);
    try {
      const payload = { template_type: template.key, text: text.trim() };
      if (photoBase64) payload.photo_base64 = photoBase64;
      const res = await api.submitBroadcast(payload);
      setResult(res);
    } catch (e) {
      setError(e.message);
    } finally {
      setSending(false);
    }
  }

  function reset() {
    setTemplate(null);
    setText("");
    setPhotoBase64(null);
    setPreview(null);
    setResult(null);
    api.broadcastStatus().then(setStatus);
  }

  if (!status && !error) return <DropLoader />;

  if (status && !status.can_send && !result) {
    return (
      <div className="screen">
        <div className="title">📢 Reklama</div>
        <p className="hint">
          Keyingi reklama uchun <b>{status.days_remaining} kun</b> qoldi. Haftada bir marta yuborish — do'konchilarni
          charchatib qo'ymaslik uchun.
        </p>
      </div>
    );
  }

  if (result) {
    return (
      <div className="screen">
        <div className="title">📢 Reklama</div>
        {result.status === "sent" && <p className="hint">✅ Reklama {result.delivered} ta do'konga yuborildi.</p>}
        {result.status === "queued" && (
          <p className="hint">
            🕐 Hozir 10:00–18:00 oralig'idan tashqari. Xabaringiz {result.scheduled_at.slice(11, 16)}'da avtomatik
            yuboriladi.
          </p>
        )}
        {result.status === "too_soon" && <p className="hint">Keyingi reklama uchun {result.days_remaining} kun qoldi.</p>}
        <button className="button secondary" onClick={reset} style={{ marginTop: 12 }}>
          Ortga
        </button>
      </div>
    );
  }

  if (!template) {
    return (
      <div className="screen">
        <div className="title">📢 Reklama</div>
        <p className="hint" style={{ marginBottom: 12 }}>
          Shablonni tanlang:
        </p>
        {TEMPLATES.map((t) => (
          <div
            key={t.key}
            className="shop-card"
            style={{ cursor: "pointer" }}
            onClick={() => {
              setTemplate(t);
              setText(t.sample);
            }}
          >
            <div className="placeholder-img" style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
              <t.icon size={22} color="#0369A1" />
            </div>
            <div className="info">
              <div className="name">{t.label}</div>
              <div className="meta">{t.sample}</div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="screen">
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
        <div className="title" style={{ margin: 0 }}>
          {template.label}
        </div>
        <button
          className="qty-btn"
          style={{ background: "var(--secondary-bg)", color: "var(--text)" }}
          onClick={() => setTemplate(null)}
        >
          <X size={16} />
        </button>
      </div>

      <label className="hint">Matn (qisqa, 2-3 gap)</label>
      <textarea
        className="search-input"
        rows={4}
        value={text}
        onChange={(e) => setText(e.target.value)}
        style={{ resize: "vertical" }}
      />

      <div
        onClick={() => fileInputRef.current?.click()}
        style={{
          aspectRatio: "16 / 9",
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
          <div style={{ textAlign: "center" }}>
            <Camera size={24} color="#0369A1" />
            <div className="hint">Rasm qo'shish (ixtiyoriy)</div>
          </div>
        )}
      </div>
      <input ref={fileInputRef} type="file" accept="image/*" style={{ display: "none" }} onChange={handlePhoto} />

      {error && <p className="hint" style={{ color: "#b91c1c" }}>{error}</p>}

      <button className="button" onClick={send} disabled={sending || !text.trim()}>
        {sending ? "Yuborilmoqda..." : "📤 Yuborish"}
      </button>
    </div>
  );
}
  
