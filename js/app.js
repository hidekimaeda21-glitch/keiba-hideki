/**
 * 競馬予想・収支管理 Webアプリケーション メインロジック
 * Optimized for iPhone 17 (Dynamic Island, iOS Safari & PWA)
 */

// アプリの状態管理
const APP_STATE = {
  currentTab: 'races', // 'races' | 'dashboard'
  currentFilter: 'all', // 'all' | 'hanshin' | 'graded'
  betRaces: {}, // { [raceId]: { isBet: boolean, isSettled: boolean, betAmount: 3000, payout: number, isHit: boolean } }
  expandedRaces: {}, // { [raceId]: boolean }
  isStandalone: false // PWAホーム画面起動判定
};

const STORAGE_KEY = 'KEIBA_AI_APP_STATE_V1';

// 初期化
function initApp() {
  loadStateFromStorage();
  checkStandaloneMode();
  registerServiceWorker();

  // 初期状態でデータが空なら、デモ用に全レースをシミュレーション済みとして初期表示
  if (Object.keys(APP_STATE.betRaces).length === 0) {
    applyDefaultSimulation();
  }

  setupEventListeners();
  renderRaces();
  renderDashboard();
  switchTab(APP_STATE.currentTab);
}

// Service Worker登録
function registerServiceWorker() {
  if ('serviceWorker' in navigator && window.location.protocol.startsWith('http')) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('./sw.js')
        .then((reg) => console.log('SW registered successfully:', reg.scope))
        .catch((err) => console.log('SW registration failed:', err));
    });
  }
}

// スタンドアローンモード（ホーム画面からアプリ起動）の判定
function checkStandaloneMode() {
  const isIOSStandalone = window.navigator.standalone === true;
  const isDisplayStandalone = window.matchMedia('(display-mode: standalone)').matches;
  APP_STATE.isStandalone = isIOSStandalone || isDisplayStandalone;

  const banner = document.getElementById('pwa-install-banner');
  const badgeText = document.getElementById('install-badge-text');
  const badgeBtn = document.getElementById('btn-open-install-guide');

  if (APP_STATE.isStandalone) {
    // 既にアプリとして起動中
    if (banner) banner.classList.add('hidden');
    if (badgeText) badgeText.textContent = 'APP MODE';
    if (badgeBtn) {
      badgeBtn.className = "flex items-center gap-1 px-2.5 py-1 rounded-full bg-emerald-500/20 border border-emerald-500/50 text-[11px] text-emerald-400 font-bold";
    }
  } else {
    // ブラウザで表示中
    const dismissed = localStorage.getItem('PWA_BANNER_DISMISSED');
    if (dismissed && banner) {
      banner.classList.add('hidden');
    }
  }
}

// デフォルトシミュレーション（全レース参加状態）
function applyDefaultSimulation() {
  if (!window.MOCK_RACES) return;
  window.MOCK_RACES.forEach(race => {
    APP_STATE.betRaces[race.id] = {
      isBet: true,
      isSettled: race.result.isSettled,
      betAmount: race.recommendation.totalBet,
      payout: race.result.payout,
      isHit: race.result.isHit,
      timestamp: Date.now()
    };
  });
  saveStateToStorage();
}

// LocalStorageの保存と読み込み
function saveStateToStorage() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      betRaces: APP_STATE.betRaces
    }));
  } catch (e) {
    console.warn('Storage save failed:', e);
  }
}

function loadStateFromStorage() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const data = JSON.parse(raw);
      if (data.betRaces) {
        APP_STATE.betRaces = data.betRaces;
      }
    }
  } catch (e) {
    console.warn('Storage load failed:', e);
  }
}

// タブ切り替え
function switchTab(tabId) {
  APP_STATE.currentTab = tabId;
  
  const tabRacesBtn = document.getElementById('tab-btn-races');
  const tabDashBtn = document.getElementById('tab-btn-dashboard');
  const btmRacesBtn = document.getElementById('btm-nav-races');
  const btmDashBtn = document.getElementById('btm-nav-dashboard');

  const viewRaces = document.getElementById('view-races');
  const viewDashboard = document.getElementById('view-dashboard');

  if (tabId === 'races') {
    tabRacesBtn.classList.add('tab-active');
    tabDashBtn.classList.remove('tab-active');
    if (btmRacesBtn) {
      btmRacesBtn.classList.add('text-emerald-400');
      btmRacesBtn.classList.remove('text-slate-400');
    }
    if (btmDashBtn) {
      btmDashBtn.classList.remove('text-emerald-400');
      btmDashBtn.classList.add('text-slate-400');
    }
    viewRaces.classList.remove('hidden');
    viewDashboard.classList.add('hidden');
  } else {
    tabDashBtn.classList.add('tab-active');
    tabRacesBtn.classList.remove('tab-active');
    if (btmDashBtn) {
      btmDashBtn.classList.add('text-emerald-400');
      btmDashBtn.classList.remove('text-slate-400');
    }
    if (btmRacesBtn) {
      btmRacesBtn.classList.remove('text-emerald-400');
      btmRacesBtn.classList.add('text-slate-400');
    }
    viewRaces.classList.add('hidden');
    viewDashboard.classList.remove('hidden');
    renderDashboard();
  }
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// フィルター切り替え
function setFilter(filter) {
  APP_STATE.currentFilter = filter;
  ['all', 'hanshin', 'graded'].forEach(f => {
    const btn = document.getElementById(`filter-${f}`);
    if (btn) {
      if (f === filter) {
        btn.className = "px-4 py-1.5 rounded-full text-xs font-bold bg-emerald-600 text-white shadow-sm";
      } else {
        btn.className = "px-4 py-1.5 rounded-full text-xs font-medium text-slate-400 bg-slate-800/80 hover:bg-slate-700/80 transition-colors";
      }
    }
  });
  renderRaces();
}

// レースアコーディオンの開閉トグル
function toggleRaceAccordion(raceId) {
  APP_STATE.expandedRaces[raceId] = !APP_STATE.expandedRaces[raceId];
  const contentEl = document.getElementById(`accordion-${raceId}`);
  const iconEl = document.getElementById(`chevron-${raceId}`);
  const btnTextEl = document.getElementById(`expand-text-${raceId}`);

  if (contentEl) {
    if (APP_STATE.expandedRaces[raceId]) {
      contentEl.classList.add('expanded');
      if (iconEl) iconEl.classList.add('rotated');
      if (btnTextEl) btnTextEl.textContent = '出馬表を閉じる';
    } else {
      contentEl.classList.remove('expanded');
      if (iconEl) iconEl.classList.remove('rotated');
      if (btnTextEl) btnTextEl.textContent = '出馬表を見る';
    }
  }
}

// 個別レースの購入/的中ステータス切り替え
function toggleRaceBet(raceId) {
  const current = APP_STATE.betRaces[raceId];
  const race = window.MOCK_RACES ? window.MOCK_RACES.find(r => r.id === raceId) : null;
  if (!race) return;

  if (current && current.isBet) {
    delete APP_STATE.betRaces[raceId];
    showToast(`${race.venue}${race.raceNumber}R の購入を解除しました`, 'info');
  } else {
    APP_STATE.betRaces[raceId] = {
      isBet: true,
      isSettled: race.result.isSettled,
      betAmount: race.recommendation.totalBet,
      payout: race.result.payout,
      isHit: race.result.isHit,
      timestamp: Date.now()
    };
    const hitMsg = race.result.isHit 
      ? `的中！ 払戻: ¥${race.result.payout.toLocaleString()}` 
      : '不的中（次回期待）';
    showToast(`${race.venue}${race.raceNumber}R 推奨3,000円購入！[${hitMsg}]`, race.result.isHit ? 'success' : 'warning');
  }

  saveStateToStorage();
  renderRaces();
  renderDashboard();
}

// 全レース一括シミュレーション
function simulateAllRaces() {
  applyDefaultSimulation();
  renderRaces();
  renderDashboard();
  showToast('全13レースの推奨買い目（各3,000円）を一括シミュレーションしました！', 'success');
}

// 収支データのリセット
function resetAllBets() {
  if (confirm('すべての収支シミュレーションデータをリセットしますか？')) {
    APP_STATE.betRaces = {};
    saveStateToStorage();
    renderRaces();
    renderDashboard();
    showToast('収支データをリセットしました', 'info');
  }
}

// トースト通知表示
function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  const bg = type === 'success' ? 'bg-emerald-600 text-white' :
             type === 'warning' ? 'bg-rose-600 text-white' : 'bg-slate-800 text-white border border-slate-700';

  const icon = type === 'success' ? '🎉' : type === 'warning' ? '📉' : 'ℹ️';

  toast.className = `toast-msg ${bg}`;
  toast.innerHTML = `<span>${icon}</span><span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(-10px)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 2800);
}

// モーダルの開閉
function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
  }
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.remove('active');
    document.body.style.overflow = '';
  }
}

// iPhone 接続 QRコードの描画とURL同期
let currentMobileUrl = 'http://192.168.32.184:8080/';

function renderQRCode() {
  const qrImg = document.getElementById('qrcode-img');
  const urlEl = document.getElementById('app-current-url');

  if (qrImg) {
    // キャッシュ回避のタイムスタンプ付きで直接ロード（100%確実に表示）
    qrImg.src = 'iphone_qr.png?t=' + Date.now();
  }

  if (urlEl) {
    urlEl.textContent = '接続URLを取得中...';
  }

  // サーバーの最新情報を取得（HTTPSトンネルURLまたはLAN IP）
  fetch('server_info.json?t=' + Date.now())
    .then(res => res.json())
    .then(data => {
      if (data && data.bestUrl) {
        currentMobileUrl = data.bestUrl;
        if (urlEl) {
          urlEl.textContent = currentMobileUrl;
        }
      }
    })
    .catch(() => {
      if (window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
        currentMobileUrl = window.location.href;
      }
      if (urlEl) {
        urlEl.textContent = currentMobileUrl;
      }
    });
}

// レース一覧のレンダリング
function renderRaces() {
  const container = document.getElementById('races-container');
  if (!container) return;

  let races = window.MOCK_RACES || [];

  if (APP_STATE.currentFilter === 'hanshin') {
    races = races.filter(r => r.venue === '阪神');
  } else if (APP_STATE.currentFilter === 'graded') {
    races = races.filter(r => r.isGraded);
  }

  container.innerHTML = races.map(race => createRaceCardHTML(race)).join('');
}

// レースカードのHTML生成
function createRaceCardHTML(race) {
  const isExpanded = !!APP_STATE.expandedRaces[race.id];
  const betStatus = APP_STATE.betRaces[race.id];
  const isBet = betStatus && betStatus.isBet;
  
  const confColor = race.confidence.level === 'S' ? 'from-amber-500 to-amber-600 text-amber-950' :
                    race.confidence.level === 'A' ? 'from-emerald-500 to-emerald-600 text-emerald-950' :
                    'from-blue-500 to-blue-600 text-blue-950';

  let gradeBadge = '';
  if (race.grade) {
    const gColor = race.grade === 'GI' ? 'bg-gradient-to-r from-red-600 to-amber-600 text-white font-black' :
                   race.grade === 'GII' ? 'bg-gradient-to-r from-red-700 to-rose-800 text-white font-bold' :
                   'bg-slate-700 text-amber-400 font-bold';
    gradeBadge = `<span class="px-2 py-0.5 rounded text-[11px] shadow-sm tracking-wider ${gColor}">${race.grade}</span>`;
  }

  const horsesHTML = race.horses.map(horse => {
    let markBadge = '<span class="inline-block w-5 text-center text-xs text-slate-600">-</span>';
    if (horse.mark === '◎') markBadge = '<span class="inline-flex items-center justify-center w-5 h-5 rounded-full text-xs font-black mark-honmei">◎</span>';
    else if (horse.mark === '◯') markBadge = '<span class="inline-flex items-center justify-center w-5 h-5 rounded-full text-xs font-black mark-taiko">◯</span>';
    else if (horse.mark === '▲') markBadge = '<span class="inline-flex items-center justify-center w-5 h-5 rounded-full text-xs font-black mark-tanana">▲</span>';
    else if (horse.mark === '△') markBadge = '<span class="inline-flex items-center justify-center w-5 h-5 rounded-full text-xs font-black mark-renka">△</span>';
    else if (horse.mark === '☆') markBadge = '<span class="inline-flex items-center justify-center w-5 h-5 rounded-full text-xs font-black mark-ana">☆</span>';

    let finishBadge = '';
    const finishIdx = race.result.orderOfFinish ? race.result.orderOfFinish.indexOf(horse.num) : -1;
    if (finishIdx === 0) finishBadge = '<span class="ml-1.5 px-1.5 py-0.2 rounded text-[10px] bg-amber-400 text-amber-950 font-black">1着</span>';
    else if (finishIdx === 1) finishBadge = '<span class="ml-1.5 px-1.5 py-0.2 rounded text-[10px] bg-slate-300 text-slate-900 font-black">2着</span>';
    else if (finishIdx === 2) finishBadge = '<span class="ml-1.5 px-1.5 py-0.2 rounded text-[10px] bg-amber-700 text-white font-black">3着</span>';

    const scorePercent = Math.min(100, Math.max(0, (horse.score - 50) * 2));

    return `
      <div class="flex items-center justify-between py-2.5 px-3 border-b border-slate-800/80 hover:bg-slate-800/40 transition-colors text-xs">
        <div class="flex items-center gap-2 min-w-0">
          <div class="flex-shrink-0">${markBadge}</div>
          
          <div class="flex-shrink-0 flex items-center gap-1">
            <span class="w-4 h-4 rounded text-[10px] font-black flex items-center justify-center waku-${horse.waku}">${horse.waku}</span>
            <span class="w-5 font-mono font-bold text-slate-200 text-right">${horse.num}</span>
          </div>

          <div class="truncate">
            <div class="font-bold text-slate-100 flex items-center truncate">
              <span class="truncate">${horse.name}</span>
              ${finishBadge}
            </div>
            <div class="text-[11px] text-slate-400 flex items-center gap-2">
              <span>${horse.jockey}</span>
              <span class="text-slate-500">${horse.weight}kg</span>
            </div>
          </div>
        </div>

        <div class="flex items-center gap-3 text-right flex-shrink-0 ml-2">
          <div class="w-12">
            <div class="text-[10px] text-slate-400">単勝</div>
            <div class="font-mono font-bold text-amber-400">${horse.odds.toFixed(1)}</div>
          </div>

          <div class="w-14">
            <div class="text-[10px] text-emerald-400 font-bold">AI指数 ${horse.score.toFixed(1)}</div>
            <div class="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden mt-0.5">
              <div class="bg-gradient-to-r from-emerald-500 to-teal-400 h-full rounded-full" style="width: ${scorePercent}%"></div>
            </div>
          </div>
        </div>
      </div>
    `;
  }).join('');

  const breakdownListHTML = race.recommendation.breakdown.map(b => `
    <div class="flex items-center justify-between text-[11px] py-0.5 text-slate-300 font-mono">
      <span class="font-semibold text-emerald-300">【${b.comb}】</span>
      <span>${b.odds}倍</span>
      <span class="text-amber-400 font-bold">¥${b.bet.toLocaleString()}</span>
    </div>
  `).join('');

  let statusBadgeHTML = '';
  if (isBet) {
    if (betStatus.isHit) {
      statusBadgeHTML = `<span class="px-2.5 py-1 rounded-full text-xs font-black bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 flex items-center gap-1">🎯 的中! +¥${(betStatus.payout - betStatus.betAmount).toLocaleString()}</span>`;
    } else {
      statusBadgeHTML = `<span class="px-2.5 py-1 rounded-full text-xs font-bold bg-rose-500/20 text-rose-400 border border-rose-500/40">不的中</span>`;
    }
  }

  return `
    <div class="glass-panel rounded-2xl mb-4 overflow-hidden border border-slate-700/60 shadow-lg transition-all duration-200 hover:border-emerald-500/30">
      <!-- レースヘッダー -->
      <div class="p-3.5 bg-gradient-to-r from-slate-900/90 to-slate-800/80 border-b border-slate-800 flex items-center justify-between">
        <div class="flex items-center gap-2">
          <span class="px-2.5 py-0.5 rounded-md bg-emerald-950 text-emerald-300 font-black text-xs border border-emerald-800/60">
            ${race.venue} ${race.raceNumber}R
          </span>
          ${gradeBadge}
          <h2 class="text-sm font-bold text-slate-100">${race.raceName}</h2>
        </div>
        <div class="text-right">
          <span class="text-xs font-mono font-bold text-slate-300">${race.time} 発走</span>
        </div>
      </div>

      <!-- コース・コンディション詳細 -->
      <div class="px-3.5 py-1.5 bg-slate-900/40 flex items-center justify-between text-[11px] text-slate-400 border-b border-slate-800/50">
        <div class="flex items-center gap-3">
          <span>${race.track} ${race.distance}m</span>
          <span>天候: ${race.weather} / 馬場: ${race.condition}</span>
          <span>${race.horses.length}頭立て</span>
        </div>
        ${statusBadgeHTML}
      </div>

      <!-- ハイライトバッジ群（推奨買い目・自信度・投資額） -->
      <div class="p-3.5 space-y-2.5 bg-slate-900/60">
        <div class="flex items-center justify-between gap-2">
          <div class="flex-1 flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-gradient-to-r ${confColor} font-black text-xs shadow-md">
            <span>⚡</span>
            <span>${race.confidence.text}</span>
          </div>

          <div class="flex-shrink-0 px-3 py-1.5 rounded-xl bg-gradient-to-r from-amber-500 to-amber-600 text-amber-950 font-black text-xs shadow-md flex items-center gap-1">
            <span>💰</span>
            <span>推奨投資 ¥3,000</span>
          </div>
        </div>

        <div class="p-2.5 rounded-xl bg-slate-800/90 border border-emerald-500/40 relative overflow-hidden">
          <div class="flex items-start justify-between gap-2">
            <div>
              <div class="flex items-center gap-2">
                <span class="px-2 py-0.5 rounded text-[11px] font-black bg-emerald-500 text-slate-950">
                  ${race.recommendation.type}
                </span>
                <span class="text-xs font-bold text-emerald-300">
                  ${race.recommendation.formation}
                </span>
              </div>
              <div class="text-[11px] text-slate-300 mt-1">
                ${race.recommendation.details}
              </div>
            </div>
            <span class="text-[10px] text-slate-400 flex-shrink-0">計 3,000円</span>
          </div>

          <div class="mt-2 pt-2 border-t border-slate-700/60 space-y-0.5">
            ${breakdownListHTML}
          </div>
        </div>
      </div>

      <!-- 操作フッター -->
      <div class="px-3.5 py-2.5 bg-slate-900/80 border-t border-slate-800/80 flex items-center justify-between gap-2">
        <button onclick="toggleRaceAccordion('${race.id}')" class="flex items-center gap-1 text-xs font-bold text-slate-300 hover:text-emerald-400 py-1 px-2 rounded-lg transition-colors">
          <span id="expand-text-${race.id}">${isExpanded ? '出馬表を閉じる' : '出馬表を見る'} (${race.horses.length}頭)</span>
          <svg id="chevron-${race.id}" class="w-4 h-4 rotate-icon ${isExpanded ? 'rotated' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
          </svg>
        </button>

        <button onclick="toggleRaceBet('${race.id}')" class="px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all shadow-sm flex items-center gap-1 ${
          isBet 
            ? 'bg-slate-700 text-slate-300 hover:bg-slate-600' 
            : 'bg-gradient-to-r from-emerald-500 to-teal-600 text-white hover:from-emerald-600 hover:to-teal-700 turf-glow'
        }">
          <span>${isBet ? '✓ 投票済' : '🎯 買い目投票'}</span>
        </button>
      </div>

      <!-- 出馬表アコーディオン（全頭リスト） -->
      <div id="accordion-${race.id}" class="accordion-content ${isExpanded ? 'expanded' : ''}">
        <div class="accordion-inner bg-slate-950/70 border-t border-slate-800">
          <div class="py-1 px-3 bg-slate-900/60 text-[10px] text-slate-400 flex items-center justify-between border-b border-slate-800">
            <span>枠 / 馬番 / 馬名 / 騎手</span>
            <span>単勝オッズ / AI指数</span>
          </div>
          ${horsesHTML}
        </div>
      </div>
    </div>
  `;
}

// 収支ダッシュボードの計算と描画
function renderDashboard() {
  let raceCount = 0;
  let totalBet = 0;
  let totalPayout = 0;
  let hitCount = 0;

  const historyItems = [];

  if (window.MOCK_RACES) {
    window.MOCK_RACES.forEach(race => {
      const bet = APP_STATE.betRaces[race.id];
      if (bet && bet.isBet) {
        raceCount++;
        totalBet += bet.betAmount;
        totalPayout += bet.payout;
        if (bet.isHit) hitCount++;

        historyItems.push({
          race,
          bet
        });
      }
    });
  }

  const netProfit = totalPayout - totalBet;
  const recoveryRate = totalBet > 0 ? ((totalPayout / totalBet) * 100).toFixed(1) : '0.0';
  const hitRate = raceCount > 0 ? ((hitCount / raceCount) * 100).toFixed(1) : '0.0';

  const elRaceCount = document.getElementById('dash-race-count');
  const elTotalBet = document.getElementById('dash-total-bet');
  const elTotalPayout = document.getElementById('dash-total-payout');
  const elNetProfit = document.getElementById('dash-net-profit');
  const elRecoveryRate = document.getElementById('dash-recovery-rate');
  const elHitRate = document.getElementById('dash-hit-rate');

  if (elRaceCount) elRaceCount.textContent = `${raceCount} R`;
  if (elTotalBet) elTotalBet.textContent = `¥${totalBet.toLocaleString()}`;
  if (elTotalPayout) elTotalPayout.textContent = `¥${totalPayout.toLocaleString()}`;
  
  if (elNetProfit) {
    const sign = netProfit > 0 ? '+' : '';
    elNetProfit.textContent = `${sign}¥${netProfit.toLocaleString()}`;
    if (netProfit > 0) {
      elNetProfit.className = 'text-2xl font-black text-emerald-400';
    } else if (netProfit < 0) {
      elNetProfit.className = 'text-2xl font-black text-rose-400';
    } else {
      elNetProfit.className = 'text-2xl font-black text-slate-300';
    }
  }

  if (elRecoveryRate) {
    elRecoveryRate.textContent = `${recoveryRate}%`;
    const num = parseFloat(recoveryRate);
    if (num >= 100) {
      elRecoveryRate.className = 'text-2xl font-black text-emerald-400';
    } else {
      elRecoveryRate.className = 'text-2xl font-black text-rose-400';
    }
  }

  if (elHitRate) elHitRate.textContent = `${hitRate}%`;

  const historyContainer = document.getElementById('dash-history-list');
  if (!historyContainer) return;

  if (historyItems.length === 0) {
    historyContainer.innerHTML = `
      <div class="p-8 text-center text-slate-400 text-xs">
        まだ投票・シミュレーションされたレースがありません。<br>
        「全レース一括シミュレーション」ボタンを押すと初期テストデータを反映できます。
      </div>
    `;
    return;
  }

  historyContainer.innerHTML = historyItems.map(({ race, bet }) => {
    const profit = bet.payout - bet.betAmount;
    const isWin = bet.isHit;
    const sign = profit > 0 ? '+' : '';
    
    return `
      <div class="p-3.5 bg-slate-900/60 rounded-xl border border-slate-800 flex items-center justify-between gap-2">
        <div class="min-w-0">
          <div class="flex items-center gap-1.5 mb-1">
            <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-800 text-slate-300">
              ${race.venue} ${race.raceNumber}R
            </span>
            <span class="text-xs font-bold text-slate-100 truncate">${race.raceName}</span>
          </div>
          <div class="text-[11px] text-slate-400 flex items-center gap-2">
            <span class="text-emerald-400 font-bold">${race.recommendation.type}</span>
            <span>投資: ¥${bet.betAmount.toLocaleString()}</span>
          </div>
        </div>

        <div class="text-right flex-shrink-0">
          <div class="flex items-center justify-end gap-1.5 mb-0.5">
            <span class="px-2 py-0.5 rounded-full text-[10px] font-black ${
              isWin ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
            }">
              ${isWin ? '🎯 的中' : '✕ 不的中'}
            </span>
          </div>
          <div class="font-mono text-xs font-black ${profit > 0 ? 'text-emerald-400' : profit < 0 ? 'text-rose-400' : 'text-slate-400'}">
            払戻: ¥${bet.payout.toLocaleString()} (${sign}¥${profit.toLocaleString()})
          </div>
        </div>
      </div>
    `;
  }).join('');
}

// イベントリスナー設定
function setupEventListeners() {
  // タブ
  const tabRaces = document.getElementById('tab-btn-races');
  const tabDash = document.getElementById('tab-btn-dashboard');
  if (tabRaces) tabRaces.addEventListener('click', () => switchTab('races'));
  if (tabDash) tabDash.addEventListener('click', () => switchTab('dashboard'));

  // ボトムナビ
  const btmRaces = document.getElementById('btm-nav-races');
  const btmDash = document.getElementById('btm-nav-dashboard');
  if (btmRaces) btmRaces.addEventListener('click', () => switchTab('races'));
  if (btmDash) btmDash.addEventListener('click', () => switchTab('dashboard'));

  // フィルター
  const fAll = document.getElementById('filter-all');
  const fHanshin = document.getElementById('filter-hanshin');
  const fGraded = document.getElementById('filter-graded');
  if (fAll) fAll.addEventListener('click', () => setFilter('all'));
  if (fHanshin) fHanshin.addEventListener('click', () => setFilter('hanshin'));
  if (fGraded) fGraded.addEventListener('click', () => setFilter('graded'));

  // シミュレーションボタン
  const btnSim = document.getElementById('btn-simulate-all');
  const btnSimDash = document.getElementById('btn-simulate-all-dash');
  const btnReset = document.getElementById('btn-reset-data');
  if (btnSim) btnSim.addEventListener('click', simulateAllRaces);
  if (btnSimDash) btnSimDash.addEventListener('click', simulateAllRaces);
  if (btnReset) btnReset.addEventListener('click', resetAllBets);

  // iPhone ホーム画面追加ガイド モーダル
  const btnOpenGuide = document.getElementById('btn-open-install-guide');
  const btnBannerGuide = document.getElementById('btn-banner-guide');
  const btnCloseGuide = document.getElementById('btn-close-install-guide');
  const btnOkGuide = document.getElementById('btn-ok-install-guide');
  const modalGuide = document.getElementById('modal-install-guide');

  const openGuide = () => openModal('modal-install-guide');
  const closeGuide = () => {
    closeModal('modal-install-guide');
    localStorage.setItem('PWA_BANNER_DISMISSED', 'true');
    const banner = document.getElementById('pwa-install-banner');
    if (banner) banner.classList.add('hidden');
  };

  if (btnOpenGuide) btnOpenGuide.addEventListener('click', openGuide);
  if (btnBannerGuide) btnBannerGuide.addEventListener('click', openGuide);
  if (btnCloseGuide) btnCloseGuide.addEventListener('click', closeGuide);
  if (btnOkGuide) btnOkGuide.addEventListener('click', closeGuide);
  if (modalGuide) {
    modalGuide.addEventListener('click', (e) => {
      if (e.target === modalGuide) closeGuide();
    });
  }

  // QRコード・モバイル接続 モーダル
  const btnOpenQr = document.getElementById('btn-open-qr-guide');
  const btnCloseQr = document.getElementById('btn-close-qr-guide');
  const btnDoneQr = document.getElementById('btn-done-qr');
  const btnCopyUrl = document.getElementById('btn-copy-url');
  const modalQr = document.getElementById('modal-qr-guide');

  if (btnOpenQr) {
    btnOpenQr.addEventListener('click', () => {
      renderQRCode();
      openModal('modal-qr-guide');
    });
  }
  if (btnCloseQr) btnCloseQr.addEventListener('click', () => closeModal('modal-qr-guide'));
  if (btnDoneQr) btnDoneQr.addEventListener('click', () => closeModal('modal-qr-guide'));
  if (modalQr) {
    modalQr.addEventListener('click', (e) => {
      if (e.target === modalQr) closeModal('modal-qr-guide');
    });
  }

  if (btnCopyUrl) {
    btnCopyUrl.addEventListener('click', () => {
      const urlToCopy = currentMobileUrl || window.location.href;
      navigator.clipboard.writeText(urlToCopy).then(() => {
        showToast('iPhone用URLをコピーしました！', 'success');
      }).catch(() => {
        showToast('URLのコピーに失敗しました', 'warning');
      });
    });
  }
}

// DOM読み込み完了時に実行
document.addEventListener('DOMContentLoaded', initApp);
