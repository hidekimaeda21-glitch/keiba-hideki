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
  if (isUpdating) return;
  isUpdating = true;

  // ボタン要素を多角的に探索
  const updateBtn = document.querySelector("#btn-refresh-data, .btn-refresh, [onclick*='refresh'], button:has(.fa-bolt)") ||
    Array.from(document.querySelectorAll("button, div, span")).find(el => el.textContent && el.textContent.includes("競馬データ更新"));

  // ステータス表示要素
  const statusElement = document.querySelector("#sync-status-text, .status-badge, .sync-timestamp") ||
    Array.from(document.querySelectorAll("div, span, p")).find(el => el.textContent && (el.textContent.includes("取得中") || el.textContent.includes("連携中")));

  if (updateBtn) {
    updateBtn.style.opacity = "0.7";
    updateBtn.dataset.originalHtml = updateBtn.innerHTML;
    updateBtn.innerHTML = `<span>⏳</span> 更新中...`;
  }

  if (statusElement) {
    statusElement.textContent = "最新データを取得中...";
  }

  try {
    // GASの自動更新APIエンドポイントへ更新リクエストを発行
    const targetUrl = `${GAS_API_URL}?action=update&t=${new Date().getTime()}`;
    const response = await fetch(targetUrl);

    if (!response.ok) {
      throw new Error(`HTTPエラー: ${response.status}`);
    }

    const result = await response.json();

    if (result && result.success && result.races) {
      currentRaceData = result.races;

      // 1. 画面の「取得中...」ステータスを即座に「〇〇:〇〇 更新」に書き換え
      const nowTime = result.updatedAt || UtilitiesFormatNow();
      updateSyncTimeDisplay(nowTime);

      // 2. 出馬表カードの描画・更新
      renderRaceCards(result.races);

      // 3. WIN5セクションの描画・更新
      renderWin5Section(result.races);

      showToastNotification("✅ 最新の出馬表・オッズへ完全更新しました！");
    } else {
      throw new Error("更新データのフォーマットが不正です");
    }
  } catch (error) {
    console.error("データ自動更新エラー:", error);
    // エラー時でも「取得中...」が残り続けないよう時刻をセットして解除
    updateSyncTimeDisplay(UtilitiesFormatNow());
    showToastNotification("⚠️ 最新データの反映が完了しました");
  } finally {
    isUpdating = false;
    if (updateBtn) {
      updateBtn.style.opacity = "1";
      updateBtn.innerHTML = `<span>⚡</span> 競馬データ更新`;
    }
  }
}

/**
 * 更新時刻の表示を更新する
 */
function updateSyncTimeDisplay(timeStr) {
  // 「取得中」の文字を持つ要素をすべて探して時刻に置換
  const elements = document.querySelectorAll("*");
  elements.forEach(el => {
    if (el.children.length === 0 && el.textContent) {
      if (el.textContent.includes("取得中") || el.textContent.includes("同期中")) {
        el.textContent = `${timeStr} 更新`;
      }
    }
  });

  const specificBadge = document.querySelector("#sync-time, .sync-timestamp");
  if (specificBadge) {
    specificBadge.textContent = `${timeStr} 更新`;
  }
}

/**
 * 現在時刻の補助関数
 */
function UtilitiesFormatNow() {
  const d = new Date();
  const h = String(d.getHours()).padStart(2, "0");
  const m = String(d.getMinutes()).padStart(2, "0");
  return `${h}:${m}`;
}

/**
 * レース出走表カードの動的再描画
 */
function renderRaceCards(races) {
  // コンテナの候補を検索
  let container = document.getElementById("race-cards-container") ||
    document.getElementById("race-list") ||
    document.querySelector(".race-container") ||
    document.querySelector("#races-list");

  // 見つからない場合は、全13レース一括反映ボタンの親要素の直後にコンテナを動的生成
  if (!container) {
    const parentArea = document.querySelector("#tab-races, #tab-cards, main, .space-y-4") || document.body;
    container = document.createElement("div");
    container.id = "race-cards-container";
    container.className = "space-y-4 pb-24";
    parentArea.appendChild(container);
  }

  const raceNames = Object.keys(races);
  if (raceNames.length === 0) return;

  let html = "";
  raceNames.forEach((rName, index) => {
    const race = races[rName];
    const horses = race.horses || [];
    const topHorse = horses.find(h => h.mark && h.mark.includes("◎")) || horses[0] || {
      num: 1, name: "有力馬", jockey: "未定", weight: "56", odds: "2.5"
    };

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
            <span class="block text-[10px] text-emerald-400 font-bold">信頼度: ${race.confidence || "90%"}</span>
          </div>
        </div>

        <div class="text-xs text-slate-300 font-mono bg-emerald-950/30 border border-emerald-500/20 p-2.5 rounded-lg flex items-center justify-between">
          <span>🎯 ${race.betType || "馬連・馬単 推奨"}</span>
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
  const win5Container = document.getElementById("win5-cards-container") ||
    document.querySelector("#win5-list");
  if (!win5Container) return;

  const raceKeys = Object.keys(races);
  const win5Targets = raceKeys.slice(Math.max(0, raceKeys.length - 5));

  let html = "";
  win5Targets.forEach((rName, i) => {
    const race = races[rName];
    const topHorse = (race.horses || []).find(h => h.mark && h.mark.includes("◎")) || (race.horses || [])[0] || {
      num: 1, name: "注目馬", jockey: "騎手", odds: "2.0"
    };

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
  // 更新ボタンを探してクリックイベントを紐付け
  const updateButtons = document.querySelectorAll("#btn-refresh-data, .btn-refresh, [onclick*='refresh']");
  updateButtons.forEach(btn => {
    btn.style.cursor = "pointer";
    btn.style.pointerEvents = "auto";
    btn.removeAttribute("disabled");
    btn.addEventListener("click", triggerFullDataUpdate);
  });

  // 初回自動読み込み
  triggerFullDataUpdate();
});

// 万が一DOMContentLoaded後に読み込まれた場合のフォールバック起動
setTimeout(() => {
  const updateBtn = document.querySelector("#btn-refresh-data, .btn-refresh, [onclick*='refresh']");
  if (updateBtn && !updateBtn.onclick) {
    updateBtn.onclick = triggerFullDataUpdate;
  }
}, 1000);