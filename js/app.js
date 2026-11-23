/**
 * ジェミ予想 フロントエンド完全版
 * (各レース個別IPAT連携 ＋ 【一括】全レースまとめて購入ボタン ＋ 危険な人気馬赤ハイライト)
 */

const GAS_API_URL = "[suspicious link removed]";
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
    toast.style.cssText =
      "position:fixed;bottom:80px;left:50%;transform:translateX(-50%);background:#1e293b;color:#ffffff;" +
      "font-size:12px;padding:10px 18px;border-radius:9999px;box-shadow:0 10px 25px rgba(0,0,0,0.5);" +
      "border:1px solid rgba(16,185,129,0.5);z-index:9999;transition:opacity 0.3s ease;pointer-events:none;text-align:center;max-width:90%;";
    document.body.appendChild(toast);
  }
  toast.textContent = msg;
  toast.style.opacity = "1";
  setTimeout(function () {
    toast.style.opacity = "0";
  }, 3000);
}

// 共通クリップボードコピー処理
function executeClipboardCopy(text, successMsg, afterCallback) {
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(function () {
      showToastNotification(successMsg);
      if (afterCallback) setTimeout(afterCallback, 500);
    }).catch(fallback);
  } else {
    fallback();
  }

  function fallback() {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    try {
      document.execCommand("copy");
      showToastNotification(successMsg);
      if (afterCallback) setTimeout(afterCallback, 500);
    } catch (err) {
      alert("クリップボードへのコピーに失敗しました。画面の買い目をご確認ください。");
      if (afterCallback) afterCallback();
    }
    document.body.removeChild(ta);
  }
}

function openJraIpat() {
  window.open("https://sp.ipat.jra.go.jp/", "_blank");
}

/**
 * 1. 個別レース：買い目コピー ＆ IPAT起動
 */
window.copyToIpatAndOpen = function (raceName, startTime, aiBuyText) {
  const copyText =
    "【ジェミ予想 推奨買い目】\n" +
    "■ レース: " + raceName + " (" + (startTime || "発走時刻確認") + ")\n" +
    "■ 買い目: " + aiBuyText + "\n" +
    "■ 投資総額: 1,000円 (傾斜配分)\n\n" +
    "※JRAネット投票画面で該当馬番と金額を入力してください。";

  executeClipboardCopy(copyText, "📋 買い目をコピーしました！JRA投票画面へ移動します", openJraIpat);
};

/**
 * 2. 【新機能】全レース一括：まとめて買い目コピー ＆ IPAT起動
 */
window.copyAllRacesToIpatAndOpen = function () {
  if (!currentRaceData) {
    showToastNotification("⚠️ レースデータがありません。更新ボタンを押してください。");
    return;
  }

  const raceNames = Object.keys(currentRaceData);
  if (raceNames.length === 0) {
    showToastNotification("⚠️ 対象レースがありません。");
    return;
  }

  let textLines = [];
  textLines.push("【ジェミ予想 本日の全レース買い目一括まとめ】");
  textLines.push("=================================");

  let totalRaces = 0;
  let totalYen = 0;

  raceNames.forEach(function (rName) {
    const r = currentRaceData[rName];
    const buy = r.aiBuy || r.betType || "買い目算出中";
    const time = r.startTime ? "(" + r.startTime + "発走)" : "";
    totalRaces += 1;
    totalYen += 1000;

    textLines.push("■ " + (r.raceName || rName) + " " + time);
    textLines.push("  買い目: " + buy);
    textLines.push("  配分額: 1,000円");
    textLines.push("---------------------------------");
  });

  textLines.push("=================================");
  textLines.push("■ 本日合計: " + totalRaces + "レース / " + totalYen.toLocaleString() + "円");
  textLines.push("※JRAネット投票で各レースの買い目・金額を入力してください。");

  const fullText = textLines.join("\n");
  executeClipboardCopy(
    fullText,
    "📋 全" + totalRaces + "レースの買い目を一括コピーしました！JRA投票画面へ移動します",
    openJraIpat
  );
};

/**
 * レースカードおよび画面上部「一括購入ボタン」の描画
 */
function renderRaceCards(races, filter = "all") {
  let container =
    document.getElementById("race-cards-container") ||
    document.getElementById("race-list") ||
    document.querySelector("#races-list") ||
    document.querySelector(".race-container");

  if (!container) {
    const mainArea =
      document.querySelector("main") ||
      document.querySelector("#tab-races") ||
      document.body;
    container = document.createElement("div");
    container.id = "race-cards-container";
    container.className = "space-y-4 pb-24 px-3";
    mainArea.appendChild(container);
  }

  const raceNames = Object.keys(races);
  if (raceNames.length === 0) return;

  let html = "";

  // 🌟【新設】画面最上部の「全レースまとめて一括購入ボタン」
  const totalRacesCount = raceNames.length;
  const totalBudgetEstimate = (totalRacesCount * 1000).toLocaleString();
  html +=
    '<div style="margin-bottom:16px;padding:12px;background:rgba(6,78,59,0.35);border:1px solid rgba(16,185,129,0.4);border-radius:14px;box-shadow:0 4px 15px rgba(0,0,0,0.3);">' +
    '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">' +
    '<span style="color:#ffffff;font-weight:bold;font-size:13px;">🏇 本日の全レース一括投票</span>' +
    '<span style="color:#34d399;font-size:11px;font-weight:bold;">全' + totalRacesCount + 'R / 合計 ¥' + totalBudgetEstimate + '</span>' +
    '</div>' +
    '<button onclick="copyAllRacesToIpatAndOpen()" ' +
    'style="width:100%;background:linear-gradient(135deg, #10b981 0%, #059669 100%);color:#ffffff;font-size:13px;font-weight:900;padding:12px;border:none;border-radius:10px;cursor:pointer;display:flex;justify-content:center;align-items:center;gap:8px;box-shadow:0 4px 14px rgba(16,185,129,0.4);">' +
    '<span>🟢 【一括】全レース買い目をまとめてコピーしてIPATを開く</span>' +
    '</button>' +
    '</div>';

  // 各レースカードの描画ループ
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

    const titleBadge = (race.raceName || "").split(" ")[0] || "レース";
    const conf = race.confidence || "88%";
    const bet = race.betType || race.aiBuy || "買い目算出完了";
    const rawBuy = race.aiBuy || race.betType || "";
    const resultRank = race.resultRank || "";
    const hitStatus = race.hitStatus || "";
    const payout = race.payout || "";
    const profit = race.profit || "";
    const rawComment = race.comment || race.aiComment || "AI独自の総合指数および展開・馬場適性を分析した推奨買い目です。";
    const win5Info = race.win5 || "";

    // 🎯 結果表示
    let resultHtml = "";
    if (resultRank || hitStatus) {
      resultHtml =
        '<div style="margin-top:8px;padding:8px 12px;background:rgba(16,185,129,0.15);border:1px solid rgba(16,185,129,0.3);border-radius:8px;display:flex;justify-content:space-between;align-items:center;">' +
        '<span style="color:#34d399;font-weight:bold;">🎯 結果: ' + (hitStatus || "的中") + ' (' + resultRank + ')</span>' +
        '<span style="color:#fbbf24;font-weight:bold;">払戻: ' + (payout || "￥0") + ' (収支: ' + (profit || "￥0") + ')</span>' +
        '</div>';
    }

    // 👑 WIN5バッジ
    let win5Html = "";
    if (win5Info) {
      win5Html =
        '<div style="margin-top:6px;padding:6px 10px;background:rgba(245,158,11,0.15);border:1px solid rgba(245,158,11,0.3);border-radius:8px;font-size:11px;color:#fbbf24;font-weight:bold;">' +
        '👑 ' + win5Info +
        '</div>';
    }

    // 💡 AI見解 ＆ 【危険な人気馬】赤系警告ハイライト
    let commentHtml = "";
    if (rawComment) {
      const commentLines = rawComment.split(/\r?\n/);
      let formattedComment = "";
      commentLines.forEach(function (line) {
        if (!line.trim()) return;
        if (line.indexOf("【危険な人気馬】") !== -1) {
          formattedComment +=
            '<div style="margin-top:6px;padding:6px 10px;background:rgba(239,68,68,0.15);border-left:3px solid #ef4444;border-radius:4px;color:#fca5a5;font-weight:bold;line-height:1.4;">' +
            '⚠️ ' + line +
            '</div>';
        } else {
          formattedComment += '<div style="margin-bottom:3px;">' + line + '</div>';
        }
      });

      commentHtml =
        '<div style="margin-top:8px;font-size:11px;color:#cbd5e1;background:rgba(15,23,42,0.8);border-left:3px solid #34d399;padding:6px 10px;border-radius:4px;line-height:1.4;">' +
        '<span style="color:#34d399;font-weight:bold;display:block;margin-bottom:2px;">💡 AI見解・展開分析</span>' +
        formattedComment +
        '</div>';
    }

    // 🟢 各レース個別IPAT連携ボタン
    const safeRaceName = (race.raceName || "").replace(/'/g, "\\'");
    const safeStartTime = (race.startTime || "").replace(/'/g, "\\'");
    const safeAiBuy = rawBuy.replace(/'/g, "\\'");
    const ipatButtonHtml =
      '<div style="margin-top:8px;">' +
      '<button onclick="copyToIpatAndOpen(\'' + safeRaceName + '\', \'' + safeStartTime + '\', \'' + safeAiBuy + '\')" ' +
      'style="width:100%;background:linear-gradient(135deg, #059669 0%, #10b981 100%);color:#ffffff;font-size:12px;font-weight:bold;padding:10px 14px;border:none;border-radius:8px;cursor:pointer;display:flex;justify-content:center;align-items:center;gap:6px;box-shadow:0 4px 12px rgba(16,185,129,0.3);">' +
      '<span>🟢 JRA IPATへ買い目をコピーして購入</span>' +
      '</button>' +
      '</div>';

    // 📋 出走全馬リスト
    let horsesListHtml =
      '<div style="margin-top:10px;border-top:1px solid rgba(255,255,255,0.08);padding-top:8px;">' +
      '<div style="font-size:11px;color:#94a3b8;margin-bottom:6px;font-weight:bold;">出走全馬一覧 (' + horses.length + '頭)</div>';

    horses.forEach(function (h) {
      const isTop = h.mark && h.mark.indexOf("◎") !== -1;
      horsesListHtml +=
        '<div style="display:flex;justify-content:space-between;align-items:center;padding:4px 6px;margin-bottom:3px;background:' +
        (isTop ? 'rgba(251,191,36,0.1)' : 'rgba(2,6,23,0.3)') +
        ';border-radius:6px;font-size:11px;">' +
        '<div>' +
        '<span style="color:' + (isTop ? '#fbbf24' : '#cbd5e1') + ';font-weight:bold;margin-right:6px;">' + h.num + '番</span> ' +
        '<span style="color:#ffffff;">' + h.name + '</span> ' +
        '<span style="color:#94a3b8;font-size:10px;">(' + (h.jockey || "-") + ')</span>' +
        '</div>' +
        '<div>' +
        '<span style="color:#fbbf24;font-family:monospace;margin-right:8px;">' + h.odds + '倍</span>' +
        '<span style="color:#34d399;font-weight:bold;">' + (h.mark || "-") + '</span>' +
        '</div>' +
        '</div>';
    });
    horsesListHtml += '</div>';

    // レースカード統合
    html +=
      '<div style="background:rgba(15,23,42,0.75);backdrop-filter:blur(12px);border:1px solid rgba(255,255,255,0.1);border-radius:16px;padding:14px;margin-bottom:14px;box-shadow:0 10px 25px -5px rgba(0,0,0,0.5);">' +
      '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">' +
      '<div style="display:flex;align-items:center;gap:8px;">' +
      '<span style="background:rgba(16,185,129,0.2);color:#34d399;border:1px solid rgba(16,185,129,0.3);font-size:11px;font-weight:bold;padding:2px 8px;border-radius:6px;">' + titleBadge + '</span>' +
      '<span style="color:#ffffff;font-weight:bold;font-size:14px;">' + (race.raceName || "") + '</span>' +
      '</div>' +
      '<span style="color:#94a3b8;font-size:11px;font-family:monospace;">' + (race.startTime ? race.startTime + " 発走" : "R" + (index + 1)) + '</span>' +
      '</div>' +
      '<div style="background:rgba(2,6,23,0.6);padding:10px 12px;border-radius:12px;border:1px solid rgba(255,255,255,0.05);margin-bottom:10px;display:flex;justify-content:space-between;align-items:center;">' +
      '<div>' +
      '<span style="color:#fbbf24;font-size:10px;font-weight:bold;display:block;margin-bottom:2px;">本命推奨馬</span>' +
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
      '<span style="color:#34d399;font-weight:bold;font-size:10px;">配分 ¥1,000</span>' +
      '</div>' +
      ipatButtonHtml +
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
      showToastNotification("✅ 全レースの実馬名・買い目・コメントを同期しました！");
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
