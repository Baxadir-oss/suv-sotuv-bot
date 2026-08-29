import { useEffect, useState } from "react";
import { BarChart3, Search, Package, Megaphone } from "lucide-react";
import { api } from "./api";
import { initTelegramApp, isInsideTelegram } from "./telegram";
import { DropLoader } from "./components/Loaders";
import Catalog from "./pages/Catalog";
import AgentDashboard from "./pages/AgentDashboard";
import AgentSearch from "./pages/AgentSearch";
import AgentProducts from "./pages/AgentProducts";
import AgentBroadcast from "./pages/AgentBroadcast";

const AGENT_TABS = [
  { key: "reports", label: "Hisobot", icon: BarChart3, Component: AgentDashboard },
  { key: "search", label: "Qidiruv", icon: Search, Component: AgentSearch },
  { key: "products", label: "Mahsulot", icon: Package, Component: AgentProducts },
  { key: "broadcast", label: "Reklama", icon: Megaphone, Component: AgentBroadcast },
];

function initialAgentTab() {
  const params = new URLSearchParams(window.location.search);
  const requested = params.get("screen");
  return AGENT_TABS.some((t) => t.key === requested) ? requested : "reports";
}

export default function App() {
  const [me, setMe] = useState(null);
  const [error, setError] = useState(null);
  const [agentTab, setAgentTab] = useState(initialAgentTab);

  useEffect(() => {
    initTelegramApp();
    api
      .me()
      .then(setMe)
      .catch((e) => setError(e.message || "Ulanishda xatolik"));
  }, []);

  if (!isInsideTelegram()) {
    return (
      <div className="screen">
        <p className="hint">
          Bu ilova faqat Telegram ichida ishlaydi. Iltimos, botdagi tugma orqali oching.
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="screen">
        <p className="hint">Xatolik: {error}</p>
      </div>
    );
  }

  if (!me) {
    return <DropLoader />;
  }

  if (me.role === "unregistered") {
    return (
      <div className="screen">
        <p className="hint">
          Bu bot faqat ro'yxatdan o'tgan do'konlar uchun. Ro'yxatdan o'tish uchun agent bilan
          bog'laning.
        </p>
      </div>
    );
  }

  if (me.role === "agent") {
    const Active = AGENT_TABS.find((t) => t.key === agentTab)?.Component ?? AgentDashboard;
    return (
      <div>
        <div className="screen" style={{ paddingBottom: 0 }}>
          <div className="tabs">
            {AGENT_TABS.map((t) => (
              <div
                key={t.key}
                className={`tab ${agentTab === t.key ? "active" : ""}`}
                onClick={() => setAgentTab(t.key)}
                style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}
              >
                <t.icon size={16} />
                <span style={{ fontSize: 11 }}>{t.label}</span>
              </div>
            ))}
          </div>
        </div>
        <Active />
      </div>
    );
  }

  // role === "shop"
  return <Catalog />;
}
