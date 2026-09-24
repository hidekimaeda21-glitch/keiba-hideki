/**
 * 競馬予想・収支管理 Webアプリケーション メインロジック
 * Optimized for iPhone 17 (Dynamic Island, iOS Safari & PWA)
 * Google Apps Script (GAS) API 連携 & WIN5 完全対応
 */

// Google Apps Script API エンドポイント
const GAS_API_URL = 'https://script.google.com/macros/s/AKfycbwbGsrhWTNZ-uAiMVfvai3Dn0RtzAizHA1oVYk3ZDvvkfnOiQnJGhKg6dmPj0OBXEcX/exec';
const STORAGE_KEY = 'KEIBA_AI_APP_STATE_V2';
const GAS_CACHE_KEY = 'KEIBA_AI_GAS_DATA_CACHE_V2';

// アプリ全体の状態管理
const APP_STATE = {
  currentTab: 'races', // 'races' | 'win5' | 'dashboard'
  currentFilter: 'all', // 'all' | 'hanshin' | 'graded' | 'win5'
  betRaces: {}, // { [raceId]: { isBet: boolean, isSettled: boolean, betAmount: number, payout: number, isHit: boolean, timestamp: number } }
  expandedRaces: {}, // { [raceId]: boolean }
  isStandalone: false, // PWAホーム画面起動判定
  races: [], // 現在表示中のレースリスト
  rawGasData: null, // GASから取得した生データ
  lastUpdatedAt: null, // 最終更新時刻
  isSyncing: false, // API同期中フラグ
  win5: {
    targetRaceIds: [],
    picks: {}, // { [raceId]: number[] } 選択馬番配列
    strategy: 'balanced', // 'balanced' (32点) | 'solid' (8点) | 'jackpot' (243点)
    isBet: false,
    totalPoints: 32,
    totalCost: 3200,
    estPayout: 28400000,
    isSettled: true,
    isHit: true,
    payout: 34200000
  }
};

// ==========================================
// 1. 初期化 & アプリ起動
// ==========================================
function initApp() {
  loadStateFromStorage();
  checkStandaloneMode();
  registerServiceWorker();
  setupEventListeners();

  // 1. まずローカルキャッシュまたはモックデータで即座に初期描画（体感0秒表示）
  initInitialData();

  // 2. バックグラウンドでGoogle Apps Script APIから最新スプレッドシートデータを自動取得
  fetchGasRaceData(false);
}

// 初期データの読み込み（キャッシュ優先、なければモック）
function initInitialData() {
  const cachedGas = localStorage.getItem(GAS_CACHE_KEY);
  if (cachedGas) {
    try {
      const parsed = JSON.parse(cachedGas);
      const converted = convertGasDataToRaces(parsed);
      if (converted && converted.length > 0) {
        APP_STATE.races = converted;
        APP_STATE.lastUpdatedAt = parsed.updatedAt || 'キャッシュ';
        initWin5Data();
        renderAllViews();
        updateSyncStatusUI('synced', APP_STATE.lastUpdatedAt);
        return;
      }
    } catch (e) {
      console.warn('Cache parse failed:', e);
    }
  }

  // キャッシュがない場合はMOCK_RACESから初期化
  if (window.MOCK_RACES && window.MOCK_RACES.length > 0) {
    APP_STATE.races = window.MOCK_RACES.map(r => ({ ...r }));
    // WIN5対象フラグを付与
    tagWin5Races(APP_STATE.races);
    initWin5Data();
    renderAllViews();
  }
}

// 全ビューの一括再描画
function renderAllViews() {
  renderRaces();
  renderWin5();
  renderDashboard();
}

// ==========================================
// 2. Google Apps Script API 連携
// ==========================================
async function fetchGasRaceData(isManual = false) {
  if (APP_STATE.isSyncing) return;
  APP_STATE.isSyncing = true;
  updateSyncStatusUI('loading');

  if (isManual) {
    showToast('スプレッドシートから最新データを取得中...', 'info');
  }

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 12000); // 12秒タイムアウト

    const response = await fetch(GAS_API_URL + '?t=' + Date.now(), {
      method: 'GET',
      headers: { 'Accept': 'application/json' },
      signal: controller.signal
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();

    if (!data || !data.races || Object.keys(data.races).length === 0) {
      throw new Error('スプレッドシートのレースデータが空です');
    }

    APP_STATE.rawGasData = data;
    APP_STATE.lastUpdatedAt = data.updatedAt || formatCurrentTime();

    // キャッシュを保存
    try {
      localStorage.setItem(GAS_CACHE_KEY, JSON.stringify(data));
    } catch (e) {
      console.warn('Storage save error:', e);
    }

    // スプレッドシートデータをアプリ内データ構造に変換
    const convertedRaces = convertGasDataToRaces(data);
    if (convertedRaces && convertedRaces.length > 0) {
      APP_STATE.races = convertedRaces;

      // 初回またはデータリフレッシュ時のシミュレーション初期化
      if (Object.keys(APP_STATE.betRaces).length === 0) {
        applyDefaultSimulation();
      }

      initWin5Data();
      renderAllViews();
      updateSyncStatusUI('synced', APP_STATE.lastUpdatedAt);

      showToast(`スプレッドシート連携完了 (${convertedRaces.length}レース取得)`, 'success');
    }

  } catch (error) {
    console.error('GAS API Fetch Error:', error);
    updateSyncStatusUI('error', APP_STATE.lastUpdatedAt);
    if (isManual) {
      showToast('スプレッドシートの取得に失敗しました。キャッシュで表示中', 'warning');
    }
  } finally {
    APP_STATE.isSyncing = false;
  }
}

// 同期ステータスUIの更新
function updateSyncStatusUI(status, timeStr = '') {
  const indicator = document.getElementById('gas-sync-indicator');
  const statusEl = document.getElementById('gas-sync-status');
  const timeEl = document.getElementById('gas-sync-time');
  const refreshIcon = document.getElementById('refresh-icon');
  const refreshText = document.getElementById('refresh-text');

  if (status === 'loading') {
    if (indicator) {
      indicator.className = 'w-2 h-2 rounded-full bg-amber-400 animate-ping flex-shrink-0';
    }
    if (statusEl) statusEl.textContent = 'スプレッドシート通信中...';
    if (timeEl) timeEl.textContent = '同期中';
    if (refreshIcon) refreshIcon.classList.add('animate-spin');
    if (refreshText) refreshText.textContent = '取得中';
  } else if (status === 'synced') {
    if (indicator) {
      indicator.className = 'w-2 h-2 rounded-full bg-emerald-400 animate-pulse flex-shrink-0';
    }
    if (statusEl) statusEl.textContent = 'スプレッドシート連携中';
    if (timeEl) {
      // "2026/09/24 11:14:44" -> "11:14 更新"
      const shortTime = timeStr ? timeStr.split(' ').pop().slice(0, 5) : formatCurrentTime();
      timeEl.textContent = `${shortTime} 更新`;
    }
    if (refreshIcon) refreshIcon.classList.remove('animate-spin');
    if (refreshText) refreshText.textContent = '更新';
  } else {
    // error
    if (indicator) {
      indicator.className = 'w-2 h-2 rounded-full bg-rose-400 flex-shrink-0';
    }
    if (statusEl) statusEl.textContent = 'オフライン/キャッシュ表示';
    if (refreshIcon) refreshIcon.classList.remove('animate-spin');
    if (refreshText) refreshText.textContent = '再試行';
  }
}

// ==========================================
// 3. JRA公式枠番計算 & データ変換
// ==========================================
// JRAの標準頭数別枠番割り当てテーブル
function getJraWaku(horseNum, totalHorses) {
  const count = Math.max(1, Math.min(totalHorses, 18));
  const wakuBrackets = [
    [],
    [1],
    [1, 2],
    [1, 2, 3],
    [1, 2, 3, 4],
    [1, 2, 3, 4, 5],
    [1, 2, 3, 4, 5, 6],
    [1, 2, 3, 4, 5, 6, 7],
    [1, 2, 3, 4, 5, 6, 7, 8],
    [1, 2, 3, 4, 5, 6, 7, 8, 8],
    [1, 2, 3, 4, 5, 6, 7, 7, 8, 8],
    [1, 2, 3, 4, 5, 6, 6, 7, 7, 8, 8],
    [1, 2, 3, 4, 5, 5, 6, 6, 7, 7, 8, 8],
    [1, 2, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8],
    [1, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8],
    [1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8],
    [1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8],
    [1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 8],
    [1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 8, 8]
  ];
  const table = wakuBrackets[count] || wakuBrackets[18];
  return table[horseNum - 1] || Math.min(8, Math.max(1, Math.ceil(horseNum / 2)));
}

// GASレスポンスの races オブジェクトをアプリ形式のレース配列に変換
function convertGasDataToRaces(gasJson) {
  if (!gasJson || !gasJson.races) return [];

  const racesObj = gasJson.races;
  const raceKeys = Object.keys(racesObj);
  const converted = [];

  // レースの順序を自然な順序（阪神1R〜12R、中山重賞など）にソート
  raceKeys.sort((a, b) => {
    const numA = parseInt((a.match(/\d+/) || [0])[0], 10);
    const numB = parseInt((b.match(/\d+/) || [0])[0], 10);
    const isGradedA = a.includes('重賞') || a.includes('G');
    const isGradedB = b.includes('重賞') || b.includes('G');
    if (isGradedA !== isGradedB) return isGradedA ? 1 : -1;
    return numA - numB;
  });

  raceKeys.forEach((key, index) => {
    const r = racesObj[key];
    const raceNameFull = r.raceName || key;

    // 会場とレース番号の解析
    let venue = '阪神';
    if (raceNameFull.includes('中山')) venue = '中山';
    else if (raceNameFull.includes('東京')) venue = '東京';
    else if (raceNameFull.includes('京都')) venue = '京都';
    else if (raceNameFull.includes('中京')) venue = '中京';
    else if (raceNameFull.includes('小倉')) venue = '小倉';

    const raceNumMatch = raceNameFull.match(/(\d+)R/);
    const raceNumber = raceNumMatch ? parseInt(raceNumMatch[1], 10) : index + 1;

    // 重賞判定
    let grade = '';
    let isGraded = false;
    if (raceNameFull.includes('G1') || raceNameFull.includes('GI')) { grade = 'GI'; isGraded = true; }
    else if (raceNameFull.includes('G2') || raceNameFull.includes('GII')) { grade = 'GII'; isGraded = true; }
    else if (raceNameFull.includes('G3') || raceNameFull.includes('GIII')) { grade = 'GIII'; isGraded = true; }
    else if (raceNameFull.includes('重賞')) { isGraded = true; }

    // 発走時刻（標準スケジュール）
    const scheduleTimes = [
      '10:05', '10:35', '11:05', '11:35', '12:25',
      '12:55', '13:25', '13:55', '14:30', '15:05', '15:45', '16:25'
    ];
    let time = scheduleTimes[raceNumber - 1] || '15:45';
    if (isGraded && venue === '中山') time = '15:45';

    // コース・距離
    let track = raceNumber % 2 === 0 ? '芝' : 'ダート';
    let distance = 1400 + (raceNumber % 4) * 200;
    if (raceNameFull.includes('オールカマー')) {
      track = '芝';
      distance = 2200;
    }

    // 自信度
    const rawConf = typeof r.confidence === 'number' ? r.confidence : 0.8;
    const percentage = Math.round(rawConf * 100);
    const confLevel = percentage >= 85 ? 'S' : percentage >= 75 ? 'A' : 'B';

    // 出走馬一覧の変換
    const rawHorses = Array.isArray(r.horses) ? r.horses : [];
    const totalHorses = rawHorses.length;

    const horses = rawHorses.map((h, hIdx) => {
      const num = typeof h.num === 'number' ? h.num : hIdx + 1;
      const waku = getJraWaku(num, totalHorses);

      // 印の整形（"◎ 本命" -> "◎"）
      let cleanMark = '';
      if (h.mark) {
        if (h.mark.includes('◎')) cleanMark = '◎';
        else if (h.mark.includes('○') || h.mark.includes('◯')) cleanMark = '◯';
        else if (h.mark.includes('▲')) cleanMark = '▲';
        else if (h.mark.includes('△')) cleanMark = '△';
        else if (h.mark.includes('☆')) cleanMark = '☆';
      }

      return {
        num: num,
        waku: waku,
        name: h.name || `${venue}${raceNumber}R-出走馬${num}`,
        jockey: h.jockey || '武豊',
        weight: typeof h.weight === 'number' ? h.weight : 56.0,
        odds: typeof h.odds === 'number' ? h.odds : 9.9,
        score: typeof h.score === 'number' ? h.score : 50.0,
        mark: cleanMark
      };
    });

    // 推奨買い目の解析
    const betTypeStr = r.betType || '【馬連】1 - 2,4,5,8 4点配分(計3,000円)';
    const typeMatch = betTypeStr.match(/【(.*?)】/);
    const recType = typeMatch ? typeMatch[1] : '馬連';
    const formation = betTypeStr.replace(/【.*?】/, '').replace(/\(.*?\)/, '').trim();

    // 買い目詳細内訳の生成
    const breakdown = generateBreakdown(recType, horses);

    // シミュレーション用結果データ（的中判定など）
    const honmeiHorse = horses.find(h => h.mark === '◎') || horses[0];
    const taikoHorse = horses.find(h => h.mark === '◯') || horses[1] || horses[0];
    const tananaHorse = horses.find(h => h.mark === '▲') || horses[2] || horses[0];

    const orderOfFinish = [
      honmeiHorse ? honmeiHorse.num : 1,
      taikoHorse ? taikoHorse.num : 2,
      tananaHorse ? tananaHorse.num : 3
    ];

    // 回収シミュレーション
    const isHit = Math.random() < rawConf; // 自信度に応じた的中判定
    const payout = isHit ? Math.round(3000 * ((honmeiHorse ? honmeiHorse.odds : 3.0) * 1.6)) : 0;

    const raceId = `${venue === '中山' ? 'nakayama' : 'hanshin'}-${String(raceNumber).padStart(2, '0')}`;

    converted.push({
      id: raceId,
      venue: venue,
      raceNumber: raceNumber,
      raceName: raceNameFull,
      grade: grade,
      time: time,
      track: track,
      distance: distance,
      weather: '晴',
      condition: '良',
      isGraded: isGraded,
      confidence: {
        level: confLevel,
        percentage: percentage,
        text: `自信度 ${confLevel} (${percentage}%)`
      },
      recommendation: {
        type: recType,
        formation: formation,
        details: `${recType} ${formation}`,
        breakdown: breakdown,
        totalBet: 3000
      },
      result: {
        isSettled: true,
        orderOfFinish: orderOfFinish,
        payout: payout,
        isHit: isHit
      },
      horses: horses,
      isWin5Target: false
    });
  });

  // WIN5対象レースにフラグを付与
  tagWin5Races(converted);

  return converted;
}

// WIN5対象レースの自動選定フラグ付与
function tagWin5Races(races) {
  // WIN5の対象5レース: 通常後半メインを中心とする5レース
  // 今回の構成: 阪神9R, 阪神10R, 阪神11R, 中山11R(重賞), 阪神12R
  const win5Keys = ['hanshin-09', 'hanshin-10', 'hanshin-11', 'nakayama-11', 'hanshin-12'];

  races.forEach(r => {
    if (win5Keys.includes(r.id)) {
      r.isWin5Target = true;
    } else if (r.venue === '阪神' && r.raceNumber >= 8 && r.raceNumber <= 12) {
      r.isWin5Target = true;
    }
  });

  // 対象が5レースに満たない場合は重賞や10R以降を対象に
  const targets = races.filter(r => r.isWin5Target);
  if (targets.length < 5) {
    races.slice(-5).forEach(r => r.isWin5Target = true);
  }
}

// 買い目内訳の生成ヘルパー
function generateBreakdown(betType, horses) {
  const honmei = horses.find(h => h.mark === '◎') || horses[0];
  const opponents = horses.filter(h => h.mark && h.mark !== '◎').slice(0, 4);

  if (opponents.length === 0) {
    return [{ comb: `${honmei.num} 単勝`, odds: honmei.odds, bet: 3000 }];
  }

  const betPerItem = Math.floor(3000 / opponents.length);
  return opponents.map((opp, idx) => {
    const isBox = betType.includes('BOX');
    const comb = isBox 
      ? `${honmei.num} - ${opp.num}` 
      : `${honmei.num} → ${opp.num}`;
    const odds = (honmei.odds * (opp.odds * 0.4)).toFixed(1);
    const bet = idx === 0 ? 3000 - (betPerItem * (opponents.length - 1)) : betPerItem;

    return {
      comb: comb,
      odds: parseFloat(odds) || 12.5,
      bet: bet
    };
  });
}

// ==========================================
// 4. WIN5 ロジック & 状態管理
// ==========================================
function initWin5Data() {
  const win5Races = APP_STATE.races.filter(r => r.isWin5Target);
  if (win5Races.length === 0) return;

  APP_STATE.win5.targetRaceIds = win5Races.map(r => r.id);

  // 戦略に応じた初期ピックの設定
  applyWin5Strategy(APP_STATE.win5.strategy);
}

// 戦略切り替え
function applyWin5Strategy(strategyName) {
  APP_STATE.win5.strategy = strategyName;
  const win5Races = APP_STATE.races.filter(r => r.isWin5Target);
  APP_STATE.win5.picks = {};

  win5Races.forEach((race, idx) => {
    const sortedHorses = [...race.horses].sort((a, b) => {
      const markRank = { '◎': 1, '◯': 2, '▲': 3, '△': 4, '☆': 5, '': 6 };
      const rankA = markRank[a.mark] || 6;
      const rankB = markRank[b.mark] || 6;
      if (rankA !== rankB) return rankA - rankB;
      return a.odds - b.odds;
    });

    if (strategyName === 'balanced') {
      // バランス型: 各レース上位2頭 (2×2×2×2×2 = 32点)
      APP_STATE.win5.picks[race.id] = sortedHorses.slice(0, 2).map(h => h.num);
    } else if (strategyName === 'solid') {
      // 鉄板絞り型: 自信度高の2レースは1頭、他は2頭 (1×1×2×2×2 = 8点)
      const pickCount = (idx === 0 || idx === 2) ? 1 : 2;
      APP_STATE.win5.picks[race.id] = sortedHorses.slice(0, pickCount).map(h => h.num);
    } else if (strategyName === 'jackpot') {
      // 万馬券型: 各レース上位3頭 (3×3×3×3×3 = 243点)
      APP_STATE.win5.picks[race.id] = sortedHorses.slice(0, 3).map(h => h.num);
    }
  });

  recalculateWin5Totals();
}

// WIN5の点数と投資金額の再計算
function recalculateWin5Totals() {
  const win5Races = APP_STATE.races.filter(r => r.isWin5Target);
  let totalCombos = 1;

  win5Races.forEach(race => {
    const picks = APP_STATE.win5.picks[race.id] || [];
    const count = Math.max(1, picks.length);
    totalCombos *= count;
  });

  APP_STATE.win5.totalPoints = totalCombos;
  APP_STATE.win5.totalCost = totalCombos * 100;

  // 推定配当の動的算出（点数や穴馬選択に応じる）
  const basePayout = 18000000;
  APP_STATE.win5.estPayout = Math.min(250000000, Math.round(basePayout * (totalCombos / 32) * 1.5));

  updateWin5HeaderUI();
}

// WIN5のヘッダーUIの更新
function updateWin5HeaderUI() {
  const elPoints = document.getElementById('win5-total-points');
  const elCost = document.getElementById('win5-total-cost');
  const elPayout = document.getElementById('win5-est-payout');
  const btnBet = document.getElementById('btn-bet-win5');
  const btnBetText = document.getElementById('btn-bet-win5-text');

  if (elPoints) elPoints.textContent = APP_STATE.win5.totalPoints.toLocaleString();
  if (elCost) elCost.textContent = `¥${APP_STATE.win5.totalCost.toLocaleString()}`;
  if (elPayout) elPayout.textContent = `推定 ¥${APP_STATE.win5.estPayout.toLocaleString()}`;

  // 戦略ボタンのアクティブクラス更新
  ['balanced', 'solid', 'jackpot'].forEach(st => {
    const btn = document.getElementById(`win5-strat-${st}`);
    if (btn) {
      if (st === APP_STATE.win5.strategy) {
        btn.className = "flex-1 py-1.5 rounded-lg text-[11px] font-bold transition-all text-amber-300 bg-amber-500/20 border border-amber-500/40 shadow-sm text-center";
      } else {
        btn.className = "flex-1 py-1.5 rounded-lg text-[11px] font-bold transition-all text-slate-400 hover:text-slate-200 text-center";
      }
    }
  });

  // 投票ボタンの状態
  if (btnBet && btnBetText) {
    if (APP_STATE.win5.isBet) {
      btnBet.className = "px-3.5 py-2 rounded-xl bg-slate-700 text-slate-300 font-black text-xs shadow-md transition-all flex items-center gap-1.5 flex-shrink-0";
      btnBetText.textContent = "✓ WIN5投票済";
    } else {
      btnBet.className = "px-3.5 py-2 rounded-xl bg-gradient-to-r from-amber-500 to-amber-600 text-slate-950 font-black text-xs shadow-lg hover:from-amber-400 hover:to-amber-500 active:scale-95 transition-all flex items-center gap-1.5 flex-shrink-0";
      btnBetText.textContent = "WIN5に投票";
    }
  }
}

// WIN5 馬番トグル（ユーザーによる自由な選択/解除）
function toggleWin5HorsePick(raceId, horseNum) {
  if (!APP_STATE.win5.picks[raceId]) {
    APP_STATE.win5.picks[raceId] = [];
  }

  const currentPicks = APP_STATE.win5.picks[raceId];
  const idx = currentPicks.indexOf(horseNum);

  if (idx > -1) {
    // 最低1頭は選択を維持
    if (currentPicks.length <= 1) {
      showToast('各レース最低1頭は選択が必要です', 'warning');
      return;
    }
    currentPicks.splice(idx, 1);
  } else {
    currentPicks.push(horseNum);
  }

  APP_STATE.win5.strategy = 'custom';
  recalculateWin5Totals();
  renderWin5();
}

// WIN5 投票切り替え
function toggleWin5Bet() {
  APP_STATE.win5.isBet = !APP_STATE.win5.isBet;
  updateWin5HeaderUI();

  if (APP_STATE.win5.isBet) {
    showToast(`WIN5 (${APP_STATE.win5.totalPoints}点 / ¥${APP_STATE.win5.totalCost.toLocaleString()}) に投票しました！`, 'success');
  } else {
    showToast('WIN5の投票を取り消しました', 'info');
  }

  renderDashboard();
}

// ==========================================
// 5. 画面レンダリング（出走表・WIN5・収支）
// ==========================================

// レース一覧（出走表）の描画
function renderRaces() {
  const container = document.getElementById('races-container');
  if (!container) return;

  let races = APP_STATE.races || [];

  if (APP_STATE.currentFilter === 'hanshin') {
    races = races.filter(r => r.venue === '阪神');
  } else if (APP_STATE.currentFilter === 'graded') {
    races = races.filter(r => r.isGraded);
  } else if (APP_STATE.currentFilter === 'win5') {
    races = races.filter(r => r.isWin5Target);
  }

  if (races.length === 0) {
    container.innerHTML = `
      <div class="p-8 text-center text-slate-400 text-xs glass-panel rounded-2xl">
        条件に一致するレースがありません。<br>
        上部の「すべて」フィルターを選択してください。
      </div>
    `;
    return;
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

  const win5Badge = race.isWin5Target
    ? `<span class="px-1.5 py-0.2 rounded text-[10px] bg-amber-500/20 text-amber-300 border border-amber-500/40 font-bold">WIN5</span>`
    : '';

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
          ${win5Badge}
          <h2 class="text-sm font-bold text-slate-100 truncate">${race.raceName}</h2>
        </div>
        <div class="text-right flex-shrink-0">
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

// WIN5 ビューのレンダリング
function renderWin5() {
  const container = document.getElementById('win5-races-container');
  if (!container) return;

  const win5Races = APP_STATE.races.filter(r => r.isWin5Target);
  updateWin5HeaderUI();

  if (win5Races.length === 0) {
    container.innerHTML = `
      <div class="p-8 text-center text-slate-400 text-xs glass-panel rounded-2xl">
        WIN5対象レースを準備中...<br>
        右上の「データ更新」ボタンを押してください。
      </div>
    `;
    return;
  }

  const raceCardsHTML = win5Races.map((race, rIdx) => {
    const picks = APP_STATE.win5.picks[race.id] || [];

    // 馬番順、印順で上位有力馬を表示
    const candidateHorses = [...race.horses].sort((a, b) => {
      const markRank = { '◎': 1, '◯': 2, '▲': 3, '△': 4, '☆': 5, '': 6 };
      return (markRank[a.mark] || 6) - (markRank[b.mark] || 6);
    });

    const horseSelectorsHTML = candidateHorses.slice(0, 6).map(horse => {
      const isSelected = picks.includes(horse.num);
      let markBadge = '';
      if (horse.mark === '◎') markBadge = '<span class="text-rose-400 font-black">◎</span>';
      else if (horse.mark === '◯') markBadge = '<span class="text-blue-400 font-black">◯</span>';
      else if (horse.mark === '▲') markBadge = '<span class="text-emerald-400 font-black">▲</span>';
      else if (horse.mark === '☆') markBadge = '<span class="text-purple-400 font-black">☆</span>';

      return `
        <div onclick="toggleWin5HorsePick('${race.id}', ${horse.num})" class="cursor-pointer p-2 rounded-xl border transition-all flex items-center justify-between ${
          isSelected 
            ? 'bg-amber-500/15 border-amber-500/60 shadow-sm' 
            : 'bg-slate-900/60 border-slate-800 hover:border-slate-700 text-slate-400'
        }">
          <div class="flex items-center gap-2 min-w-0">
            <span class="w-4 h-4 rounded text-[9px] font-black flex items-center justify-center flex-shrink-0 waku-${horse.waku}">${horse.waku}</span>
            <span class="w-4 font-mono font-bold text-xs ${isSelected ? 'text-amber-300 font-black' : 'text-slate-300'}">${horse.num}</span>
            <div class="truncate text-xs">
              <span class="font-bold ${isSelected ? 'text-white' : 'text-slate-300'}">${horse.name}</span>
              <span class="text-[10px] text-slate-400 ml-1">(${horse.jockey})</span>
            </div>
            ${markBadge}
          </div>

          <div class="flex items-center gap-2 flex-shrink-0">
            <span class="text-[10px] font-mono text-amber-400">${horse.odds.toFixed(1)}倍</span>
            <div class="w-5 h-5 rounded-md flex items-center justify-center border ${
              isSelected ? 'bg-amber-500 border-amber-400 text-slate-950 font-black' : 'border-slate-700 bg-slate-800'
            }">
              ${isSelected ? '✓' : ''}
            </div>
          </div>
        </div>
      `;
    }).join('');

    return `
      <div class="glass-panel rounded-2xl p-3.5 mb-3 border border-slate-800 shadow-md">
        <div class="flex items-center justify-between mb-2">
          <div class="flex items-center gap-2">
            <span class="px-2 py-0.5 rounded-lg bg-amber-500 text-slate-950 font-black text-xs">
              第${rIdx + 1}戦
            </span>
            <span class="text-xs font-bold text-slate-200">
              ${race.venue} ${race.raceNumber}R ${race.raceName}
            </span>
          </div>
          <span class="text-[11px] font-mono text-slate-400 font-bold">${race.time} 発走</span>
        </div>

        <div class="flex items-center justify-between text-[11px] text-slate-400 mb-2 pb-1.5 border-b border-slate-800/60">
          <span>${race.track} ${race.distance}m / ${race.horses.length}頭立て</span>
          <span class="text-amber-300 font-bold">選択中: ${picks.length}頭 (${picks.join(', ')}番)</span>
        </div>

        <div class="space-y-1.5">
          ${horseSelectorsHTML}
        </div>
      </div>
    `;
  }).join('');

  container.innerHTML = raceCardsHTML;
}

// 収支ダッシュボードの計算と描画
function renderDashboard() {
  let raceCount = 0;
  let totalBet = 0;
  let totalPayout = 0;
  let hitCount = 0;

  const historyItems = [];

  // 1. 各レースの投票集計
  if (APP_STATE.races) {
    APP_STATE.races.forEach(race => {
      const bet = APP_STATE.betRaces[race.id];
      if (bet && bet.isBet) {
        raceCount++;
        totalBet += bet.betAmount;
        totalPayout += bet.payout;
        if (bet.isHit) hitCount++;

        historyItems.push({
          type: 'race',
          race: race,
          bet: bet
        });
      }
    });
  }

  // 2. WIN5の投票集計
  if (APP_STATE.win5.isBet) {
    raceCount++;
    totalBet += APP_STATE.win5.totalCost;
    totalPayout += APP_STATE.win5.payout;
    if (APP_STATE.win5.isHit) hitCount++;

    historyItems.unshift({
      type: 'win5',
      points: APP_STATE.win5.totalPoints,
      betAmount: APP_STATE.win5.totalCost,
      payout: APP_STATE.win5.payout,
      isHit: APP_STATE.win5.isHit
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
        「全レースを一括反映」ボタンを押すと初期テストデータを反映できます。
      </div>
    `;
    return;
  }

  historyContainer.innerHTML = historyItems.map(item => {
    if (item.type === 'win5') {
      const profit = item.payout - item.betAmount;
      const isWin = item.isHit;
      return `
        <div class="p-3.5 bg-gradient-to-r from-amber-950/40 via-slate-900/80 to-amber-950/40 rounded-xl border border-amber-500/40 flex items-center justify-between gap-2 shadow-md">
          <div class="min-w-0">
            <div class="flex items-center gap-1.5 mb-1">
              <span class="px-2 py-0.5 rounded text-[10px] font-black bg-amber-500 text-slate-950">
                🎯 WIN5
              </span>
              <span class="text-xs font-bold text-amber-300">5レース完全的中シミュレーション</span>
            </div>
            <div class="text-[11px] text-slate-300 flex items-center gap-2">
              <span class="text-emerald-400 font-bold">${item.points}点購入</span>
              <span>投資: ¥${item.betAmount.toLocaleString()}</span>
            </div>
          </div>

          <div class="text-right flex-shrink-0">
            <div class="flex items-center justify-end gap-1.5 mb-0.5">
              <span class="px-2 py-0.5 rounded-full text-[10px] font-black bg-amber-500/20 text-amber-300 border border-amber-500/40">
                ${isWin ? '👑 WIN5的中!!' : '✕ 不的中'}
              </span>
            </div>
            <div class="font-mono text-xs font-black text-amber-400">
              払戻: ¥${item.payout.toLocaleString()} (+¥${profit.toLocaleString()})
            </div>
          </div>
        </div>
      `;
    }

    const { race, bet } = item;
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

// ==========================================
// 6. 操作系（タブ、フィルター、シミュレーション）
// ==========================================

// タブ切り替え（3タブ対応: races, win5, dashboard）
function switchTab(tabId) {
  APP_STATE.currentTab = tabId;

  const tabRacesBtn = document.getElementById('tab-btn-races');
  const tabWin5Btn = document.getElementById('tab-btn-win5');
  const tabDashBtn = document.getElementById('tab-btn-dashboard');

  const btmRacesBtn = document.getElementById('btm-nav-races');
  const btmWin5Btn = document.getElementById('btm-nav-win5');
  const btmDashBtn = document.getElementById('btm-nav-dashboard');

  const viewRaces = document.getElementById('view-races');
  const viewWin5 = document.getElementById('view-win5');
  const viewDashboard = document.getElementById('view-dashboard');

  // リセット
  [tabRacesBtn, tabWin5Btn, tabDashBtn].forEach(b => b && b.classList.remove('tab-active'));
  [btmRacesBtn, btmWin5Btn, btmDashBtn].forEach(b => {
    if (b) {
      b.classList.remove('text-emerald-400', 'text-amber-400');
      b.classList.add('text-slate-400');
    }
  });
  [viewRaces, viewWin5, viewDashboard].forEach(v => v && v.classList.add('hidden'));

  if (tabId === 'races') {
    if (tabRacesBtn) tabRacesBtn.classList.add('tab-active');
    if (btmRacesBtn) {
      btmRacesBtn.classList.add('text-emerald-400');
      btmRacesBtn.classList.remove('text-slate-400');
    }
    if (viewRaces) viewRaces.classList.remove('hidden');
    renderRaces();
  } else if (tabId === 'win5') {
    if (tabWin5Btn) tabWin5Btn.classList.add('tab-active');
    if (btmWin5Btn) {
      btmWin5Btn.classList.add('text-amber-400');
      btmWin5Btn.classList.remove('text-slate-400');
    }
    if (viewWin5) viewWin5.classList.remove('hidden');
    renderWin5();
  } else {
    // dashboard
    if (tabDashBtn) tabDashBtn.classList.add('tab-active');
    if (btmDashBtn) {
      btmDashBtn.classList.add('text-emerald-400');
      btmDashBtn.classList.remove('text-slate-400');
    }
    if (viewDashboard) viewDashboard.classList.remove('hidden');
    renderDashboard();
  }

  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// フィルター切り替え（all, hanshin, graded, win5）
function setFilter(filter) {
  APP_STATE.currentFilter = filter;
  ['all', 'hanshin', 'graded', 'win5'].forEach(f => {
    const btn = document.getElementById(`filter-${f}`);
    if (btn) {
      if (f === filter) {
        btn.className = "px-3.5 py-1.5 rounded-full text-xs font-bold bg-emerald-600 text-white shadow-sm flex-shrink-0";
      } else {
        btn.className = "px-3.5 py-1.5 rounded-full text-xs font-medium text-slate-400 bg-slate-800/80 hover:bg-slate-700/80 transition-colors flex-shrink-0";
      }
    }
  });
  renderRaces();
}

// レースアコーディオンの開閉
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

// 個別レース投票切り替え
function toggleRaceBet(raceId) {
  const current = APP_STATE.betRaces[raceId];
  const race = APP_STATE.races.find(r => r.id === raceId);
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

// 全レース一括シミュレーション反映
function simulateAllRaces() {
  applyDefaultSimulation();
  renderRaces();
  renderDashboard();
  showToast('全レースの推奨買い目を一括反映しました！', 'success');
}

function applyDefaultSimulation() {
  if (!APP_STATE.races) return;
  APP_STATE.races.forEach(race => {
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

// 収支データのリセット
function resetAllBets() {
  if (confirm('すべての収支シミュレーションデータをリセットしますか？')) {
    APP_STATE.betRaces = {};
    APP_STATE.win5.isBet = false;
    saveStateToStorage();
    renderRaces();
    renderWin5();
    renderDashboard();
    showToast('収支データをリセットしました', 'info');
  }
}

// ==========================================
// 7. ユーティリティ & モーダル & PWA
// ==========================================
function saveStateToStorage() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      betRaces: APP_STATE.betRaces,
      win5: {
        isBet: APP_STATE.win5.isBet,
        strategy: APP_STATE.win5.strategy
      }
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
      if (data.betRaces) APP_STATE.betRaces = data.betRaces;
      if (data.win5) {
        if (data.win5.strategy) APP_STATE.win5.strategy = data.win5.strategy;
        if (typeof data.win5.isBet === 'boolean') APP_STATE.win5.isBet = data.win5.isBet;
      }
    }
  } catch (e) {
    console.warn('Storage load failed:', e);
  }
}

function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  const bg = type === 'success' ? 'bg-emerald-600 text-white shadow-lg' :
             type === 'warning' ? 'bg-rose-600 text-white shadow-lg' : 'bg-slate-800 text-white border border-slate-700 shadow-lg';

  const icon = type === 'success' ? '🎉' : type === 'warning' ? '⚠️' : 'ℹ️';

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

function formatCurrentTime() {
  const d = new Date();
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
}

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

function registerServiceWorker() {
  if ('serviceWorker' in navigator && window.location.protocol.startsWith('http')) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('./sw.js')
        .then((reg) => console.log('SW registered:', reg.scope))
        .catch((err) => console.log('SW registration failed:', err));
    });
  }
}

function checkStandaloneMode() {
  const isIOSStandalone = window.navigator.standalone === true;
  const isDisplayStandalone = window.matchMedia('(display-mode: standalone)').matches;
  APP_STATE.isStandalone = isIOSStandalone || isDisplayStandalone;

  const banner = document.getElementById('pwa-install-banner');
  const badgeText = document.getElementById('install-badge-text');
  const badgeBtn = document.getElementById('btn-open-install-guide');

  if (APP_STATE.isStandalone) {
    if (banner) banner.classList.add('hidden');
    if (badgeText) badgeText.textContent = 'APP MODE';
    if (badgeBtn) {
      badgeBtn.className = "flex items-center gap-1 px-2.5 py-1 rounded-full bg-emerald-500/20 border border-emerald-500/50 text-[11px] text-emerald-400 font-bold";
    }
  } else {
    const dismissed = localStorage.getItem('PWA_BANNER_DISMISSED');
    if (dismissed && banner) banner.classList.add('hidden');
  }
}

let currentMobileUrl = 'http://192.168.32.184:8080/';
function renderQRCode() {
  const qrImg = document.getElementById('qrcode-img');
  const urlEl = document.getElementById('app-current-url');
  if (qrImg) qrImg.src = 'iphone_qr.png?t=' + Date.now();
  if (urlEl) urlEl.textContent = '接続URLを取得中...';

  fetch('server_info.json?t=' + Date.now())
    .then(res => res.json())
    .then(data => {
      if (data && data.bestUrl) {
        currentMobileUrl = data.bestUrl;
        if (urlEl) urlEl.textContent = currentMobileUrl;
      }
    })
    .catch(() => {
      if (window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
        currentMobileUrl = window.location.href;
      }
      if (urlEl) urlEl.textContent = currentMobileUrl;
    });
}

// ==========================================
// 8. イベントリスナー登録
// ==========================================
function setupEventListeners() {
  // 上部タブ
  const tabRaces = document.getElementById('tab-btn-races');
  const tabWin5 = document.getElementById('tab-btn-win5');
  const tabDash = document.getElementById('tab-btn-dashboard');
  if (tabRaces) tabRaces.addEventListener('click', () => switchTab('races'));
  if (tabWin5) tabWin5.addEventListener('click', () => switchTab('win5'));
  if (tabDash) tabDash.addEventListener('click', () => switchTab('dashboard'));

  // ボトムナビ
  const btmRaces = document.getElementById('btm-nav-races');
  const btmWin5 = document.getElementById('btm-nav-win5');
  const btmDash = document.getElementById('btm-nav-dashboard');
  if (btmRaces) btmRaces.addEventListener('click', () => switchTab('races'));
  if (btmWin5) btmWin5.addEventListener('click', () => switchTab('win5'));
  if (btmDash) btmDash.addEventListener('click', () => switchTab('dashboard'));

  // GAS手動更新ボタン
  const btnRefreshGas = document.getElementById('btn-refresh-gas');
  if (btnRefreshGas) {
    btnRefreshGas.addEventListener('click', () => fetchGasRaceData(true));
  }

  // フィルター
  const fAll = document.getElementById('filter-all');
  const fHanshin = document.getElementById('filter-hanshin');
  const fGraded = document.getElementById('filter-graded');
  const fWin5 = document.getElementById('filter-win5');
  if (fAll) fAll.addEventListener('click', () => setFilter('all'));
  if (fHanshin) fHanshin.addEventListener('click', () => setFilter('hanshin'));
  if (fGraded) fGraded.addEventListener('click', () => setFilter('graded'));
  if (fWin5) fWin5.addEventListener('click', () => setFilter('win5'));

  // WIN5戦略ボタン
  const stratBalanced = document.getElementById('win5-strat-balanced');
  const stratSolid = document.getElementById('win5-strat-solid');
  const stratJackpot = document.getElementById('win5-strat-jackpot');
  if (stratBalanced) stratBalanced.addEventListener('click', () => { applyWin5Strategy('balanced'); renderWin5(); });
  if (stratSolid) stratSolid.addEventListener('click', () => { applyWin5Strategy('solid'); renderWin5(); });
  if (stratJackpot) stratJackpot.addEventListener('click', () => { applyWin5Strategy('jackpot'); renderWin5(); });

  // WIN5投票ボタン
  const btnBetWin5 = document.getElementById('btn-bet-win5');
  if (btnBetWin5) btnBetWin5.addEventListener('click', toggleWin5Bet);

  // シミュレーションボタン
  const btnSim = document.getElementById('btn-simulate-all');
  const btnSimDash = document.getElementById('btn-simulate-all-dash');
  const btnReset = document.getElementById('btn-reset-data');
  if (btnSim) btnSim.addEventListener('click', simulateAllRaces);
  if (btnSimDash) btnSimDash.addEventListener('click', simulateAllRaces);
  if (btnReset) btnReset.addEventListener('click', resetAllBets);

  // モーダル
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

  // QRコード
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

// 起動
document.addEventListener('DOMContentLoaded', initApp);
