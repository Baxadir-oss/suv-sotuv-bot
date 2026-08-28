import { useEffect, useState } from "react";
import { api } from "./api";
import { initTelegramApp, isInsideTelegram } from "./telegram";
import { DropLoader } from "./components/Loaders";
import Catalog from "./pages/Catalog";
import AgentDashboard from "./pages/AgentDashboard";
import AgentSearch from "./pages/AgentSearch";

function initialAgentTab() {
  const params = new URLSearchParams(window.location.search);
  return params.get("screen") === "search" ? "search" : "reports";
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
    return (
      <div>
        <div className="screen" style={{ paddingBottom: 0 }}>
          <div className="tabs">
            <div
              className={`tab ${agentTab === "reports" ? "active" : ""}`}
              onClick={() => setAgentTab("reports")}
            >
              📊 Hisobot
            </div>
            <div
              className={`tab ${agentTab === "search" ? "active" : ""}`}
              onClick={() => setAgentTab("search")}
            >
              🔎 Qidiruv
            </div>
          </div>
        </div>
        {agentTab === "reports" ? <AgentDashboard /> : <AgentSearch />}
      </div>
    );
  }

  // role === "shop"
  return <Catalog />;
}
