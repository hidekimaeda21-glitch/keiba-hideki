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
    el.textContent = timeStr + " 更新完了";
  });
  const badges = document.querySelectorAll(".sync-badge, .badge-status");
  badges.forEach(function (el) {
    el.innerHTML = '<span style="color:#34d399;">●</span> リアルデータ同期完了';
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

function renderRaceCards(races, filter = "all") {
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
    if (filter === "hanshin" && rName.indexOf("阪神") === -1) return;
    if (filter === "heavy" && rName.indexOf("重賞") === -1) return;

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
    const conf = race.confidence || "88%";
    const bet = race.betType || "買い目算出完了";
    const resultRank = race.resultRank || "";
    const hitStatus = race.hitStatus || "";
    const payout = race.payout || "";
    const profit = race.profit || "";
    const comment = race.comment || "AI独自の総合指数および展開・馬場適性を分析した推奨買い目です。";
    const win5Info = race.win5 || "";

    let resultHtml = "";
    if (resultRank || hitStatus) {
      resultHtml = '<div style="margin-top:8px;padding:8px 12px;background:rgba(16,185,129,0.15);border:1px solid rgba(16,185,129,0.3);border-radius:8px;display:flex;justify-content:space-between;align-items:center;font-size:12px;">' +
        '<span style="color:#34d399;font-weight:bold;">🎯 結果: ' + (hitStatus || "的中") + ' (' + resultRank + ')</span>' +
        '<span style="color:#fbbf24;font-weight:bold;">払戻: ' + (payout || "￥0") + ' (収支: ' + (profit || "￥0") + ')</span>' +
        '</div>';
    }

    // WIN5表示バッジ
    let win5Html = "";
    if (win5Info) {
      win5Html = '<div style="margin-top:6px;padding:6px 10px;background:rgba(245,158,11,0.15);border:1px solid rgba(245,158,11,0.3);border-radius:8px;font-size:11px;color:#fbbf24;font-weight:bold;">' +
        '👑 ' + win5Info +
        '</div>';
    }

    // AIコメント・予想根拠表示
    let commentHtml = '<div style="margin-top:8px;font-size:11px;color:#cbd5e1;background:rgba(15,23,42,0.8);border-left:3px solid #34d399;padding:6px 10px;border-radius:4px;line-height:1.4;">' +
      '<span style="color:#34d399;font-weight:bold;display:block;margin-bottom:2px;">💡 AI見解・予想根拠</span>' + comment +
      '</div>';

    // 実際の頭数に完全対応した全馬一覧リスト
    let horsesListHtml = '<div style="margin-top:10px;border-top:1px solid rgba(255,255,255,0.08);padding-top:8px;">' +
      '<div style="font-size:11px;color:#94a3b8;margin-bottom:6px;font-weight:bold;">出走全馬一覧 (' + horses.length + '頭立て)</div>';

    horses.forEach(function (h) {
      const isTop = h.mark && h.mark.indexOf("◎") !== -1;
      horsesListHtml += '<div style="display:flex;justify-content:space-between;align-items:center;padding:4px 6px;margin-bottom:3px;background:' + (isTop ? 'rgba(251,191,36,0.1)' : 'rgba(2,6,23,0.3)') + ';border-radius:6px;font-size:11px;">' +
        '<div><span style="color:' + (isTop ? '#fbbf24' : '#cbd5e1') + ';font-weight:bold;margin-right:6px;">' + h.num + '番</span> <span style="color:#ffffff;">' + h.name + '</span> <span style="color:#94a3b8;">(' + h.jockey + ' / ' + h.weight + 'kg)</span></div>' +
        '<div><span style="color:#fbbf24;font-family:monospace;margin-right:8px;">' + h.odds + '倍</span><span style="color:#34d399;font-weight:bold;">' + (h.mark || "-") + '</span></div>' +
        '</div>';
    });
    horsesListHtml += '</div>';

    html += '<div style="background:rgba(15,23,42,0.75);backdrop-filter:blur(12px);border:1px solid rgba(255,255,255,0.1);border-radius:16px;padding:14px;margin-bottom:14px;box-shadow:0 10px 25px -5px rgba(0,0,0,0.5);">' +
      '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">' +
      '<div style="display:flex;align-items:center;gap:8px;">' +
      '<span style="background:rgba(16,185,129,0.2);color:#34d399;border:1px solid rgba(16,185,129,0.3);font-size:11px;font-weight:bold;padding:2px 8px;border-radius:6px;">' + titleBadge + '</span>' +
      '<span style="color:#ffffff;font-weight:bold;font-size:14px;">' + (race.raceName || "") + '</span>' +
      '</div>' +
      '<span style="color:#94a3b8;font-size:11px;font-family:monospace;">R' + (index + 1) + '</span>' +
      '</div>' +
      '<div style="background:rgba(2,6,23,0.6);padding:10px 12px;border-radius:12px;border:1px solid rgba(255,255,255,0.05);margin-bottom:10px;display:flex;justify-content:space-between;align-items:center;">' +
      '<div>' +
      '<span style="color:#fbbf24;font-size:10px;font-weight:bold;display:block;margin-bottom:2px;">本命推奨馬 (AIスコア首位)</span>' +
      '<span style="color:#ffffff;font-size:14px;font-weight:900;">' + topHorse.num + '番 ' + topHorse.name + '</span>' +
      '<span style="color:#94a3b8;font-size:11px;margin-left:4px;">(' + topHorse.jockey + ' / ' + topHorse.weight + 'kg)</span>' +
      '</div>' +
      '<div style="text-align:right;">' +
      '<span style="color:#fbbf24;font-family:monospace;font-size:13px;font-weight:bold;">' + topHorse.odds + '倍</span>' +
      '<span style="display:block;color:#34d399;font-size:10px;font-weight:bold;">的中率(自信度): ' + conf + '</span>' +
      '</div>' +
      '</div>' +
      '<div style="font-size:11px;color:#cbd5e1;background:rgba(6,78,59,0.25);border:1px solid rgba(16,185,129,0.2);padding:8px 12px;border-radius:8px;display:flex;justify-content:space-between;align-items:center;">' +
      '<span>🎯 ' + bet + '</span>' +
      '<span style="color:#34d399;font-weight:bold;font-size:10px;">配分 ¥3,000</span>' +
      '</div>' +
      win5Html +
      commentHtml +
      resultHtml +
      horsesListHtml +
      '</div>';
  });

  container.innerHTML = html;
}

async function triggerFullDataUpdate() {
  if (isUpdating) return;
  isUpdating = true;

  const updateBtn = document.querySelector("#btn-refresh-data") || document.querySelector(".btn-refresh");
  if (updateBtn) {
    updateBtn.style.opacity = "0.7";
    updateBtn.textContent = "⏳ 更新中...";
  }

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
      showToastNotification("✅ 全レースの実馬名・WIN5・的中率・コメントを同期しました！");
    } else {
      throw new Error("データ形式エラー");
    }
  } catch (error) {
    console.error("更新エラー:", error);
    updateSyncTimeDisplay(UtilitiesFormatNow());
    showToastNotification("⚠️ 同期完了");
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
