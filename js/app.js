/**
 * KEIBA AI PRO - メイン制御スクリプト
 * スプレッドシート完全自動同期 & ワンタップ更新対応
 */

const GAS_API_URL = "https://script.google.com/macros/s/AKfycbwbGsrhWTNZ-uAiMVfvai3Dn0RtzAizHA1oVYk3ZDvvkfnOiQnJGhKg6dmPj0OBXEcX/exec";

// アプリケーション状態
let currentRaceData = null;
let isUpdating = false;

/**
 * 画面上の「⚡ 競馬データ更新」ボタンをクリックした時の処理
 */
async function triggerFullDataUpdate() {
  const updateBtn = document.querySelector("#btn-refresh-data, .btn-refresh, [onclick*='refresh']");

  if (isUpdating) return;
  isUpdating = true;

  // ボタンをローディング表示にする
  if (updateBtn) {
    updateBtn.style.opacity = "0.7";
    updateBtn.innerHTML = `<span>⏳</span> 更新中...`;
  }

  const statusText = document.querySelector("#sync-status-text, .status-badge");
  if (statusText) statusText.textContent = "最新データを取得中...";

  try {
    // GASの自動更新APIエンドポイントへ更新リクエストを発行
    const targetUrl = `${GAS_API_URL}?action=update&t=${new Date().getTime()}`;
    const response = await fetch(targetUrl);
    const result = await response.json();

    if (result && result.success && result.races) {
      currentRaceData = result.races;

      // 画面のレース一覧、出走表、WIN5を即時再描画
      renderRaceCards(result.races);
      renderWin5Section(result.races);

      // 更新時刻バッジを更新
      const syncTimeElement = document.querySelector("#sync-time, .sync-timestamp");
      if (syncTimeElement) {
        syncTimeElement.textContent = `${result.updatedAt} 更新`;
      }
      if (statusText) {
        statusText.textContent = "スプレッドシート連携中";
      }

      showToastNotification("✅ 最新の出馬表・オッズへ完全更新しました！");
    } else {
      throw new Error("更新データの取得に失敗しました");
    }
  } catch (error) {
    console.error("データ自動更新エラー:", error);
    showToastNotification("⚠️ 更新に失敗しました。再試行してください。");
  } finally {
    isUpdating = false;
    if (updateBtn) {
      updateBtn.style.opacity = "1";
      updateBtn.innerHTML = `<span>⚡</span> 競馬データ更新`;
    }
  }
}

/**
 * レース出走表カードの動的再描画
 */
function renderRaceCards(races) {
  const container = document.getElementById("race-cards-container");
  if (!container) return;

  const raceNames = Object.keys(races);
  if (raceNames.length === 0) return;

  let html = "";
  raceNames.forEach((rName, index) => {
    const race = races[rName];
    const topHorse = race.horses.find(h => h.mark && h.mark.includes("◎")) || race.horses[0];

    html += `
      <div class="glass-panel p-4 rounded-2xl mb-4 border border-slate-800/80 bg-slate-900/60 shadow-lg">
        <div class="flex items-center justify-between mb-2">
          <div class="flex items-center gap-2">
            <span class="px-2 py-0.5 rounded text-xs font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">${race.raceName.split(" ")[0]}</span>
            <span class="font-bold text-white text-sm">${race.raceName}</span>
          </div>
          <span class="text-xs text-slate-400 font-mono">発走順 R${index + 1}</span>
        </div>
        
        <div class="bg-slate-950/60 p-3 rounded-xl border border-slate-800 mb-3 flex items-center justify-between">
          <div>
            <span class="text-[10px] text-amber-400 font-bold block mb-0.5">本命推奨馬</span>
            <span class="text-sm font-black text-white">${topHorse.num}番 ${topHorse.name}</span>
            <span class="text-xs text-slate-400 ml-1">(${topHorse.jockey} / ${topHorse.weight}kg)</span>
          </div>
          <div class="text-right">
            <span class="text-xs font-mono font-bold text-amber-400">${topHorse.odds}倍</span>
            <span class="block text-[10px] text-emerald-400 font-bold">信頼度: ${race.confidence}</span>
          </div>
        </div>

        <div class="text-xs text-slate-300 font-mono bg-emerald-950/30 border border-emerald-500/20 p-2.5 rounded-lg flex items-center justify-between">
          <span>🎯 ${race.betType || "推奨買い目"}</span>
          <span class="text-[10px] text-emerald-400 font-bold">投資 ¥3,000</span>
        </div>
      </div>
    `;
  });

  container.innerHTML = html;
}

/**
 * WIN5セクションの動的再描画
 */
function renderWin5Section(races) {
  const win5Container = document.getElementById("win5-cards-container");
  if (!win5Container) return;

  const raceKeys = Object.keys(races);
  const win5Targets = raceKeys.slice(Math.max(0, raceKeys.length - 5));

  let html = "";
  win5Targets.forEach((rName, i) => {
    const race = races[rName];
    const topHorse = race.horses.find(h => h.mark && h.mark.includes("◎")) || race.horses[0];

    html += `
      <div class="p-3 bg-slate-900/80 rounded-xl border border-slate-800 mb-2.5">
        <div class="flex items-center justify-between text-xs mb-1.5">
          <span class="font-bold text-amber-400">第${i + 1}戦 ${race.raceName}</span>
          <span class="text-slate-400 text-[10px]">1点突破推奨</span>
        </div>
        <div class="flex items-center justify-between bg-slate-950 p-2 rounded-lg border border-amber-500/20">
          <span class="text-xs font-bold text-white">${topHorse.num}番 ${topHorse.name} (${topHorse.jockey})</span>
          <span class="text-xs font-mono text-amber-400 font-bold">${topHorse.odds}倍 ✔️</span>
        </div>
      </div>
    `;
  });

  win5Container.innerHTML = html;
}

/**
 * トースト通知
 */
function showToastNotification(message) {
  let toast = document.getElementById("app-toast");
  if (!toast) {
    toast = document.createElement("div");
    toast.id = "app-toast";
    toast.className = "fixed bottom-20 left-1/2 transform -translate-x-1/2 bg-slate-800 text-white text-xs px-4 py-2.5 rounded-full shadow-2xl border border-emerald-500/40 z-50 transition-all duration-300 pointer-events-none";
    document.body.appendChild(toast);
  }
  toast.textContent = message;
  toast.style.opacity = "1";
  setTimeout(() => {
    toast.style.opacity = "0";
  }, 2500);
}

// 起動時の初期化とボタンのクリック有効化
document.addEventListener("DOMContentLoaded", () => {
  const updateBtn = document.querySelector("#btn-refresh-data, .btn-refresh, [onclick*='refresh']");
  if (updateBtn) {
    updateBtn.style.cursor = "pointer";
    updateBtn.style.pointerEvents = "auto";
    updateBtn.removeAttribute("disabled");
    updateBtn.addEventListener("click", triggerFullDataUpdate);
  }

  // 初回自動読み込み
  triggerFullDataUpdate();
});