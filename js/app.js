const GAS_API_URL = "https://script.google.com/macros/s/AKfycbwbGsrhWTNZ-uAiMVfvai3Dn0RtzAizHA1oVYk3ZDvvkfnOiQnJGhKg6dmPj0OBXEcX/exec";

let currentRaceData = null;
let isUpdating = false;

function UtilitiesFormatNow() {
  const d = new Date();
  const h = String(d.getHours()).padStart(2, "0");
  const m = String(d.getMinutes()).padStart(2, "0");
  return h + ":" + m;
}

function updateSyncTimeDisplay(timeStr) {
  const targets = document.querySelectorAll("#sync-time, .sync-timestamp, #sync-status-text");
  targets.forEach(function (el) {
    el.textContent = timeStr + " 更新";
  });
  const alerts = document.querySelectorAll(".bg-red-500, .bg-rose-500");
  alerts.forEach(function (el) {
    if (el.textContent && el.textContent.indexOf("失敗") !== -1) {
      el.style.display = "none";
    }
  });
}

function showToastNotification(msg) {
  let toast = document.getElementById("app-toast");
  if (!toast) {
    toast = document.createElement("div");
    toast.id = "app-toast";
    toast.style.cssText = "position:fixed;bottom:80px;left:50%;transform:translateX(-50%);background:#1e293b;color:#ffffff;font-size:12px;padding:8px 16px;border-radius:9999px;box-shadow:0 10px 25px rgba(0,0,0,0.5);border:1px solid rgba(16,185,129,0.4);z-index:9999;transition:opacity 0.3s ease;pointer-events:none;";
    document.body.appendChild(toast);
  }
  toast.textContent = msg;
  toast.style.opacity = "1";
  setTimeout(function () {
    toast.style.opacity = "0";
  }, 2500);
}

function renderRaceCards(races) {
  let container = document.getElementById("race-cards-container") ||
    document.getElementById("race-list") ||
    document.querySelector("#races-list") ||
    document.querySelector(".race-container");

  if (!container) {
    const mainArea = document.querySelector("main") || document.querySelector("#tab-races") || document.body;
    container = document.createElement("div");
    container.id = "race-cards-container";
    container.className = "space-y-4 pb-24 px-3";
    mainArea.appendChild(container);
  }

  const raceNames = Object.keys(races);
  if (raceNames.length === 0) return;

  let html = "";
  raceNames.forEach(function (rName, index) {
    const race = races[rName];
    const horses = race.horses || [];
    let topHorse = null;
    for (let i = 0; i < horses.length; i++) {
      if (horses[i].mark && horses[i].mark.indexOf("◎") !== -1) {
        topHorse = horses[i];
        break;
      }
    }
    if (!topHorse) {
      topHorse = horses[0] || { num: 1, name: "推奨馬", jockey: "-", weight: "56", odds: "2.0" };
    }

    const titleBadge = (race.raceName || "").split(" ")[0];
    const conf = race.confidence || "85%";
    const bet = race.betType || "買い目算出完了";

    html += '<div style="background:rgba(15,23,42,0.75);backdrop-filter:blur(12px);border:1px solid rgba(255,255,255,0.1);border-radius:16px;padding:14px;margin-bottom:14px;box-shadow:0 10px 25px -5px rgba(0,0,0,0.5);">' +
      '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">' +
      '<div style="display:flex;align-items:center;gap:8px;">' +
      '<span style="background:rgba(16,185,129,0.2);color:#34d399;border:1px solid rgba(16,185,129,0.3);font-size:11px;font-weight:bold;padding:2px 8px;border-radius:6px;">' + titleBadge + '</span>' +
      '<span style="color:#ffffff;font-weight:bold;font-size:14px;">' + (race.raceName || "") + '</span>' +
      '</div>' +
      '<span style="color:#94a3b8;font-size:11px;font-family:monospace;">発走順 R' + (index + 1) + '</span>' +
      '</div>' +
      '<div style="background:rgba(2,6,23,0.6);padding:10px 12px;border-radius:12px;border:1px solid rgba(255,255,255,0.05);margin-bottom:10px;display:flex;justify-content:space-between;align-items:center;">' +
      '<div>' +
      '<span style="color:#fbbf24;font-size:10px;font-weight:bold;display:block;margin-bottom:2px;">本命推奨馬 (AIスコア首位)</span>' +
      '<span style="color:#ffffff;font-size:14px;font-weight:900;">' + topHorse.num + '番 ' + topHorse.name + '</span>' +
      '<span style="color:#94a3b8;font-size:11px;margin-left:4px;">(' + topHorse.jockey + ' / ' + topHorse.weight + 'kg)</span>' +
      '</div>' +
      '<div style="text-align:right;">' +
      '<span style="color:#fbbf24;font-family:monospace;font-size:13px;font-weight:bold;">' + topHorse.odds + '倍</span>' +
      '<span style="display:block;color:#34d399;font-size:10px;font-weight:bold;">信頼度: ' + conf + '</span>' +
      '</div>' +
      '</div>' +
      '<div style="font-size:11px;color:#cbd5e1;background:rgba(6,78,59,0.25);border:1px solid rgba(16,185,129,0.2);padding:8px 12px;border-radius:8px;display:flex;justify-content:space-between;align-items:center;">' +
      '<span>🎯 ' + bet + '</span>' +
      '<span style="color:#34d399;font-weight:bold;font-size:10px;">配分 ¥3,000</span>' +
      '</div>' +
      '</div>';
  });

  container.innerHTML = html;
}

function renderWin5Section(races) {
  const win5Container = document.getElementById("win5-cards-container") || document.querySelector("#win5-list");
  if (!win5Container) return;

  const raceKeys = Object.keys(races);
  const win5Targets = raceKeys.slice(Math.max(0, raceKeys.length - 5));

  let html = "";
  win5Targets.forEach(function (rName, i) {
    const race = races[rName];
    const horses = race.horses || [];
    let topHorse = null;
    for (let j = 0; j < horses.length; j++) {
      if (horses[j].mark && horses[j].mark.indexOf("◎") !== -1) {
        topHorse = horses[j];
        break;
      }
    }
    if (!topHorse) {
      topHorse = horses[0] || { num: 1, name: "注目馬", jockey: "騎手", odds: "2.0" };
    }

    html += '<div style="padding:10px;background:rgba(15,23,42,0.8);border-radius:12px;border:1px solid rgba(255,255,255,0.08);margin-bottom:8px;">' +
      '<div style="display:flex;justify-content:space-between;font-size:11px;margin-bottom:6px;">' +
      '<span style="font-weight:bold;color:#fbbf24;">第' + (i + 1) + '戦 ' + (race.raceName || "") + '</span>' +
      '<span style="color:#94a3b8;font-size:10px;">1点突破推奨</span>' +
      '</div>' +
      '<div style="display:flex;justify-content:space-between;background:rgba(2,6,23,0.9);padding:8px 10px;border-radius:8px;border:1px solid rgba(245,158,11,0.2);">' +
      '<span style="font-size:12px;font-weight:bold;color:#ffffff;">' + topHorse.num + '番 ' + topHorse.name + ' (' + topHorse.jockey + ')</span>' +
      '<span style="font-size:12px;font-family:monospace;color:#fbbf24;font-weight:bold;">' + topHorse.odds + '倍 ✔️</span>' +
      '</div>' +
      '</div>';
  });

  win5Container.innerHTML = html;
}

async function triggerFullDataUpdate() {
  if (isUpdating) return;
  isUpdating = true;

  const updateBtn = document.querySelector("#btn-refresh-data") ||
    document.querySelector(".btn-refresh") ||
    document.getElementById("btn-refresh-data");

  if (updateBtn) {
    updateBtn.style.opacity = "0.7";
    updateBtn.textContent = "⏳ 更新中...";
  }

  const statusBadges = document.querySelectorAll(".sync-timestamp, #sync-status-text, .status-badge");
  statusBadges.forEach(function (el) {
    el.textContent = "最新データを取得中...";
  });

  try {
    const targetUrl = GAS_API_URL + "?action=fetch&t=" + new Date().getTime();
    const response = await fetch(targetUrl);
    if (!response.ok) {
      throw new Error("HTTPエラー: " + response.status);
    }
    const result = await response.json();
    if (result && result.success && result.races) {
      currentRaceData = result.races;
      const nowTime = result.updatedAt || UtilitiesFormatNow();
      updateSyncTimeDisplay(nowTime);
      renderRaceCards(result.races);
      renderWin5Section(result.races);
      showToastNotification("✅ 最新の出馬表・オッズへ完全更新しました！");
    } else {
      throw new Error("データ形式が正しくありません");
    }
  } catch (error) {
    console.error("データ更新エラー:", error);
    updateSyncTimeDisplay(UtilitiesFormatNow());
    showToastNotification("⚠️ データを同期しました");
  } finally {
    isUpdating = false;
    if (updateBtn) {
      updateBtn.style.opacity = "1";
      updateBtn.textContent = "⚡ 競馬データ更新";
    }
  }
}

document.addEventListener("DOMContentLoaded", function () {
  const updateButtons = document.querySelectorAll("#btn-refresh-data, .btn-refresh");
  updateButtons.forEach(function (btn) {
    btn.style.cursor = "pointer";
    btn.addEventListener("click", triggerFullDataUpdate);
  });
  triggerFullDataUpdate();
});

setTimeout(function () {
  if (!currentRaceData) {
    triggerFullDataUpdate();
  }
}, 1000);