import { useEffect, useState } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import { Droplets } from "lucide-react";
import { api } from "../api";
import { DropLoader } from "../components/Loaders";

const PIE_COLORS = ["#0EA5E9", "#0369A1", "#7DD3FC", "#38BDF8", "#0C4A6E"];

function isoDate(d) {
  return d.toISOString().slice(0, 10);
}

function rangeFor(key) {
  const today = new Date();
  const end = isoDate(today);
  let start;
  if (key === "today") {
    start = end;
  } else if (key === "week") {
    const monday = new Date(today);
    const day = (today.getDay() + 6) % 7; // dushanba = 0
    monday.setDate(today.getDate() - day);
    start = isoDate(monday);
  } else if (key === "month") {
    start = isoDate(new Date(today.getFullYear(), today.getMonth(), 1));
  } else {
    const past = new Date(today);
    past.setDate(today.getDate() - 30);
    start = isoDate(past);
  }
  return { start, end };
}

export default function AgentDashboard() {
  const [rangeKey, setRangeKey] = useState("week");
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const { start, end } = rangeFor(rangeKey);
    setData(null);
    api
      .reports(start, end)
      .then(setData)
      .catch((e) => setError(e.message));
  }, [rangeKey]);

  return (
    <div className="screen">
      <div className="title">📊 Hisobotlar</div>

      <div className="tabs">
        {[
          ["today", "Bugun"],
          ["week", "Shu hafta"],
          ["month", "Shu oy"],
          ["30d", "30 kun"],
        ].map(([key, label]) => (
          <div
            key={key}
            className={`tab ${rangeKey === key ? "active" : ""}`}
            onClick={() => setRangeKey(key)}
          >
            {label}
          </div>
        ))}
      </div>

      {error && <p className="hint">Xatolik: {error}</p>}
      {!data && !error && <DropLoader />}

      {data && (
        <>
          <div className="stat-cards">
            <div className="stat-card">
              <div className="value">{data.totals.orders_count}</div>
              <div className="label">Buyurtmalar</div>
            </div>
            <div className="stat-card">
              <div className="value">{data.totals.total_amount.toLocaleString("ru-RU")}</div>
              <div className="label">Jami summa (so'm)</div>
            </div>
          </div>

          {data.totals.orders_count === 0 ? (
            <div className="chart-card" style={{ textAlign: "center", padding: "32px 16px" }}>
              <Droplets size={28} color="#7DD3FC" style={{ marginBottom: 8 }} />
              <div className="hint">Bu oraliqda hali buyurtma yo'q.</div>
              <div className="hint">Birinchi buyurtma tushishi bilan bu yerda grafik paydo bo'ladi.</div>
            </div>
          ) : (
            <>
              <div className="chart-card">
                <div className="chart-title">Kunlik daromad tendensiyasi</div>
                <ResponsiveContainer width="100%" height={180}>
                  <LineChart data={data.daily}>
                    <XAxis dataKey="date" tick={{ fontSize: 10 }} />
                    <YAxis tick={{ fontSize: 10 }} width={40} />
                    <Tooltip formatter={(v) => `${Number(v).toLocaleString("ru-RU")} so'm`} />
                    <Line type="monotone" dataKey="total" stroke="#0EA5E9" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              {data.top_shops?.length > 0 && (
                <div className="chart-card">
                  <div className="chart-title">Eng faol do'konlar</div>
                  <ResponsiveContainer width="100%" height={Math.max(120, data.top_shops.length * 34)}>
                    <BarChart data={data.top_shops} layout="vertical" margin={{ left: 8 }}>
                      <XAxis type="number" hide />
                      <YAxis dataKey="shop_name" type="category" width={90} tick={{ fontSize: 10 }} />
                      <Tooltip formatter={(v) => `${Number(v).toLocaleString("ru-RU")} so'm`} />
                      <Bar dataKey="total" fill="#0369A1" radius={[0, 6, 6, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}

              {data.top_products?.length > 0 && (
                <div className="chart-card">
                  <div className="chart-title">Mahsulotlar ulushi</div>
                  <ResponsiveContainer width="100%" height={180}>
                    <PieChart>
                      <Pie data={data.top_products} dataKey="quantity" nameKey="name" innerRadius={40} outerRadius={70}>
                        {data.top_products.map((_, i) => (
                          <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}
