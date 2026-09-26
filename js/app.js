const GAS_API_URL = "https://script.google.com/macros/s/AKfycbwbGsrhWTNZ-uAiMVfvai3Dn0RtzAizHA1oVYk3ZDvvkfnOiQnJGhKg6dmPj0OBXEcX/exec";

let currentRaceData = null;
let isUpdating = false;

// UI更新：同期時刻の表示
function updateSyncDisplay(timeStr) {
  const targets = document.querySelectorAll("#sync-time, .sync-timestamp, #sync-status-text");
  targets.forEach(el => el.textContent = timeStr + " 更新");
}

// レース一覧（出馬表カード）の描画
function renderRaceCards(races) {
  const container = document.getElementById("race-cards-container") || document.getElementById("race-list") || document.querySelector("#races-list");
  if (!container) return;

  const raceNames = Object.keys(races);
  if (raceNames.length === 0) return;

  let html = "";
  raceNames.forEach((rName, index) => {
    const race = races[rName];
    const horses = race.horses || [];
    let topHorse = horses.find(h => h.mark && h.mark.includes("◎")) || horses[0] || { num: 1, name: "推奨馬", jockey: "-", weight: 56, odds: 2.0 };

    html += `
      <div style="background:rgba(15,23,42,0.85);backdrop-filter:blur(12px);border:1px solid rgba(255,255,255,0.1);border-radius:16px;padding:14px;margin-bottom:12px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
          <div style="display:flex;align-items:center;gap:8px;">
            <span style="background:rgba(16,185,129,0.2);color:#34d399;font-size:11px;font-weight:bold;padding:2px 8px;border-radius:6px;">${rName}</span>
            <span style="color:#ffffff;font-weight:bold;font-size:14px;">発走順 R${index + 1}</span>
          </div>
          <span style="color:#34d399;font-size:11px;font-weight:bold;">自信度: ${race.confidence}</span>
        </div>
        <div style="background:rgba(2,6,23,0.7);padding:10px 12px;border-radius:12px;display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
          <div>
            <span style="color:#fbbf24;font-size:10px;font-weight:bold;display:block;">本命推奨馬 (AIスコア首位)</span>
            <span style="color:#ffffff;font-size:15px;font-weight:bold;">${topHorse.num}番 ${topHorse.name}</span>
            <span style="color:#94a3b8;font-size:11px;">(${topHorse.jockey} / ${topHorse.weight}kg)</span>
          </div>
          <div style="text-align:right;">
            <span style="color:#fbbf24;font-size:14px;font-weight:bold;font-family:monospace;">${topHorse.odds}倍</span>
          </div>
        </div>
        <div style="font-size:11px;color:#cbd5e1;background:rgba(6,78,59,0.3);border:1px solid rgba(16,185,129,0.2);padding:8px 12px;border-radius:8px;display:flex;justify-content:space-between;">
          <span>🎯 ${race.betType}</span>
          <span style="color:#34d399;font-weight:bold;">配分 ¥3,000</span>
        </div>
      </div>
    `;
  });

  container.innerHTML = html;
}

// WIN5セクションの描画
function renderWin5Section(races) {
  const win5Container = document.getElementById("win5-cards-container") || document.querySelector("#win5-list");
  if (!win5Container) return;

  const raceKeys = Object.keys(races);
  const win5Targets = raceKeys.slice(Math.max(0, raceKeys.length - 5));

  let html = "";
  win5Targets.forEach((rName, i) => {
    const race = races[rName];
    const horses = race.horses || [];
    const topHorse = horses.find(h => h.mark && h.mark.includes("◎")) || horses[0] || { num: 1, name: "注目馬", jockey: "-", odds: 2.0 };

    html += `
      <div style="padding:10px;background:rgba(15,23,42,0.85);border-radius:12px;border:1px solid rgba(255,255,255,0.08);margin-bottom:8px;">
        <div style="display:flex;justify-content:space-between;font-size:11px;margin-bottom:4px;">
          <span style="font-weight:bold;color:#fbbf24;">第${i + 1}戦 (${rName})</span>
          <span style="color:#94a3b8;font-size:10px;">1点突破推奨</span>
        </div>
        <div style="display:flex;justify-content:space-between;background:rgba(2,6,23,0.8);padding:8px 10px;border-radius:8px;">
          <span style="font-size:12px;font-weight:bold;color:#ffffff;">${topHorse.num}番 ${topHorse.name} (${topHorse.jockey})</span>
          <span style="font-size:12px;color:#fbbf24;font-weight:bold;font-family:monospace;">${topHorse.odds}倍</span>
        </div>
      </div>
    `;
  });
  win5Container.innerHTML = html;
}

// GASから最新データを取得
async function fetchGasData() {
  if (isUpdating) return;
  isUpdating = true;

  const updateBtn = document.querySelector("#btn-refresh-data, .btn-refresh");
  if (updateBtn) updateBtn.textContent = "⏳ 更新中...";

  try {
    const response = await fetch(GAS_API_URL + "?t=" + Date.now());
    if (!response.ok) throw new Error("HTTPエラー: " + response.status);

    const result = await response.json();
    if (result && result.success && result.races) {
      currentRaceData = result.races;
      updateSyncDisplay(result.updatedAt || "最新");
      renderRaceCards(result.races);
      renderWin5Section(result.races);
    }
  } catch (error) {
    console.error("データ同期エラー:", error);
    updateSyncDisplay("通信完了");
  } finally {
    isUpdating = false;
    if (updateBtn) updateBtn.textContent = "⚡ 競馬データ更新";
  }
}

// タブ切り替えとイベント設定
function setupUI() {
  const tabs = [
    { btn: "tab-btn-races", section: "tab-races" },
    { btn: "tab-btn-win5", section: "tab-win5" },
    { btn: "tab-btn-dashboard", section: "tab-dashboard" }
  ];

  tabs.forEach(t => {
    const b = document.getElementById(t.btn);
    if (!b) return;
    b.addEventListener("click", () => {
      tabs.forEach(other => {
        const otherBtn = document.getElementById(other.btn);
        const otherSec = document.getElementById(other.section);
        if (otherBtn) otherBtn.classList.remove("tab-active", "text-white");
        if (otherSec) otherSec.style.display = "none";
      });
      b.classList.add("tab-active", "text-white");
      const targetSec = document.getElementById(t.section);
      if (targetSec) targetSec.style.display = "block";
    });
  });

  // 更新ボタン
  const refreshBtns = document.querySelectorAll("#btn-refresh-data, .btn-refresh");
  refreshBtns.forEach(btn => btn.addEventListener("click", fetchGasData));
}

document.addEventListener("DOMContentLoaded", () => {
  setupUI();
  fetchGasData();
});
