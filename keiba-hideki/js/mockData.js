/**
 * 競馬予想・収支管理 Webアプリケーション モックデータ
 * 関西開催（阪神競馬場 1R〜12R）＋ 全国の注目重賞（東京11R 日本ダービー GI）計13レース
 */

const MOCK_RACES = [
  {
    id: "hanshin-01",
    venue: "阪神",
    raceNumber: 1,
    raceName: "2歳未勝利",
    grade: "",
    time: "10:05",
    track: "ダート",
    distance: 1400,
    weather: "晴",
    condition: "良",
    isGraded: false,
    confidence: { level: "S", percentage: 92, text: "自信度 S (92%)" },
    recommendation: {
      type: "馬連",
      formation: "◎ - ◯▲△ (3点)",
      details: "本命3番軸の安定流し",
      breakdown: [
        { comb: "3 - 7", odds: 3.4, bet: 1500 },
        { comb: "3 - 1", odds: 6.2, bet: 1000 },
        { comb: "3 - 9", odds: 11.5, bet: 500 }
      ],
      totalBet: 3000
    },
    result: {
      isSettled: true,
      orderOfFinish: [3, 7, 9], // 馬番 1着, 2着, 3着
      payout: 5100, // 3-7 馬連 3.4倍 × 1500円 = 5100円
      isHit: true
    },
    horses: [
      { num: 1, waku: 1, name: "メイショウサチ", jockey: "幸 英明", weight: 55.0, odds: 5.8, score: 81.2, mark: "▲" },
      { num: 2, waku: 2, name: "ワンダーブルーム", jockey: "和田 竜二", weight: 55.0, odds: 24.5, score: 68.0, mark: "" },
      { num: 3, waku: 3, name: "アグネススピリット", jockey: "川田 将雅", weight: 55.0, odds: 1.8, score: 94.6, mark: "◎" },
      { num: 4, waku: 4, name: "テイエムストロング", jockey: "角田 大河", weight: 54.0, odds: 45.2, score: 62.4, mark: "" },
      { num: 5, waku: 4, name: "スマートアトラクト", jockey: "藤岡 佑介", weight: 55.0, odds: 31.0, score: 66.8, mark: "" },
      { num: 6, waku: 5, name: "ヤマニンバローズ", jockey: "岩田 康誠", weight: 55.0, odds: 18.2, score: 71.3, mark: "" },
      { num: 7, waku: 5, name: "ゴールドレガシー", jockey: "坂井 瑠星", weight: 55.0, odds: 4.2, score: 87.5, mark: "◯" },
      { num: 8, waku: 6, name: "クリノオーサム", jockey: "団野 大成", weight: 55.0, odds: 58.0, score: 60.5, mark: "" },
      { num: 9, waku: 7, name: "コスモストーム", jockey: "松山 弘平", weight: 55.0, odds: 8.6, score: 78.4, mark: "△" },
      { num: 10, waku: 7, name: "シゲルヒノクニ", jockey: "国分 恭介", weight: 55.0, odds: 72.1, score: 58.2, mark: "" },
      { num: 11, waku: 8, name: "タガノシャンテ", jockey: "富田 暁", weight: 55.0, odds: 14.8, score: 74.0, mark: "☆" },
      { num: 12, waku: 8, name: "マテンロウフラッシュ", jockey: "横山 典弘", weight: 55.0, odds: 39.4, score: 64.1, mark: "" }
    ]
  },
  {
    id: "hanshin-02",
    venue: "阪神",
    raceNumber: 2,
    raceName: "2歳未勝利",
    grade: "",
    time: "10:35",
    track: "芝",
    distance: 1600,
    weather: "晴",
    condition: "良",
    isGraded: false,
    confidence: { level: "A", percentage: 84, text: "自信度 A (84%)" },
    recommendation: {
      type: "3連複",
      formation: "軸 5 - 相手 2, 8, 10, 11 (6点)",
      details: "芝マイル実績最上位◎から流し",
      breakdown: [
        { comb: "5 - 2 - 8", odds: 14.2, bet: 500 },
        { comb: "5 - 2 - 10", odds: 22.8, bet: 500 },
        { comb: "5 - 2 - 11", odds: 8.4, bet: 500 },
        { comb: "5 - 8 - 10", odds: 35.6, bet: 500 },
        { comb: "5 - 8 - 11", odds: 16.5, bet: 500 },
        { comb: "5 - 10 - 11", odds: 29.0, bet: 500 }
      ],
      totalBet: 3000
    },
    result: {
      isSettled: true,
      orderOfFinish: [5, 11, 2], // 5-11-2 的中
      payout: 4200, // 8.4倍 × 500円 = 4200円
      isHit: true
    },
    horses: [
      { num: 1, waku: 1, name: "サトノエール", jockey: "北村 友一", weight: 55.0, odds: 28.0, score: 69.2, mark: "" },
      { num: 2, waku: 2, name: "ロードフォース", jockey: "M.デムーロ", weight: 55.0, odds: 5.6, score: 83.1, mark: "▲" },
      { num: 3, waku: 3, name: "エーシンデュラン", jockey: "小牧 加矢太", weight: 55.0, odds: 64.0, score: 59.8, mark: "" },
      { num: 4, waku: 3, name: "ダイシンキング", jockey: "酒井 学", weight: 55.0, odds: 41.5, score: 64.0, mark: "" },
      { num: 5, waku: 4, name: "ヴィクトリアルート", jockey: "C.ルメール", weight: 55.0, odds: 2.1, score: 95.1, mark: "◎" },
      { num: 6, waku: 4, name: "キタサンマーベル", jockey: "荻野 極", weight: 55.0, odds: 52.0, score: 61.3, mark: "" },
      { num: 7, waku: 5, name: "タガノハルカ", jockey: "西村 淳也", weight: 55.0, odds: 33.2, score: 67.5, mark: "" },
      { num: 8, waku: 6, name: "ハギノオーパス", jockey: "藤岡 佑介", weight: 55.0, odds: 12.4, score: 76.8, mark: "△" },
      { num: 9, waku: 6, name: "ジョーフォレスト", jockey: "鮫島 克駿", weight: 55.0, odds: 88.0, score: 56.4, mark: "" },
      { num: 10, waku: 7, name: "エバークラウン", jockey: "池添 謙一", weight: 55.0, odds: 18.0, score: 73.5, mark: "☆" },
      { num: 11, waku: 8, name: "ダノンプレシャス", jockey: "川田 将雅", weight: 55.0, odds: 3.8, score: 88.7, mark: "◯" },
      { num: 12, waku: 8, name: "シゲルカイチョウ", jockey: "太宰 啓介", weight: 55.0, odds: 105.0, score: 54.0, mark: "" }
    ]
  },
  {
    id: "hanshin-03",
    venue: "阪神",
    raceNumber: 3,
    raceName: "2歳新馬",
    grade: "",
    time: "11:05",
    track: "ダート",
    distance: 1800,
    weather: "晴",
    condition: "良",
    isGraded: false,
    confidence: { level: "B", percentage: 68, text: "自信度 B (68%)" },
    recommendation: {
      type: "馬単",
      formation: "1着 6 → 2着 2, 4, 9 (3点)",
      details: "調教抜群6番から上位相手へ",
      breakdown: [
        { comb: "6 → 2", odds: 8.5, bet: 1000 },
        { comb: "6 → 4", odds: 14.2, bet: 1000 },
        { comb: "6 → 9", odds: 6.8, bet: 1000 }
      ],
      totalBet: 3000
    },
    result: {
      isSettled: true,
      orderOfFinish: [2, 6, 9], // 2着抜け 不的中
      payout: 0,
      isHit: false
    },
    horses: [
      { num: 1, waku: 1, name: "サンライズウェーブ", jockey: "水口 優也", weight: 55.0, odds: 34.0, score: 66.0, mark: "" },
      { num: 2, waku: 2, name: "テーオーリチャード", jockey: "浜中 俊", weight: 55.0, odds: 4.8, score: 84.0, mark: "◯" },
      { num: 3, waku: 3, name: "コパノテンシ", jockey: "国分 恭介", weight: 55.0, odds: 42.0, score: 63.5, mark: "" },
      { num: 4, waku: 4, name: "ウインリベラル", jockey: "松山 弘平", weight: 55.0, odds: 7.9, score: 79.5, mark: "▲" },
      { num: 5, waku: 4, name: "ベルウッドアロー", jockey: "酒井 学", weight: 55.0, odds: 89.0, score: 57.0, mark: "" },
      { num: 6, waku: 5, name: "グランデアルテ", jockey: "武 豊", weight: 55.0, odds: 2.5, score: 91.2, mark: "◎" },
      { num: 7, waku: 6, name: "シゲルセンプー", jockey: "富田 暁", weight: 55.0, odds: 55.0, score: 60.5, mark: "" },
      { num: 8, waku: 7, name: "メイショウオオギ", jockey: "幸 英明", weight: 55.0, odds: 21.0, score: 71.0, mark: "☆" },
      { num: 9, waku: 8, name: "ミッキーフライト", jockey: "坂井 瑠星", weight: 55.0, odds: 3.9, score: 86.8, mark: "△" }
    ]
  },
  {
    id: "hanshin-04",
    venue: "阪神",
    raceNumber: 4,
    raceName: "障害3歳以上未勝利",
    grade: "",
    time: "11:35",
    track: "障害",
    distance: 2970,
    weather: "晴",
    condition: "良",
    isGraded: false,
    confidence: { level: "A", percentage: 80, text: "自信度 A (80%)" },
    recommendation: {
      type: "馬連",
      formation: "◎ 4 - ◯ 7, ▲ 1, △ 8 (3点)",
      details: "飛越安定の4番軸",
      breakdown: [
        { comb: "4 - 7", odds: 4.8, bet: 1500 },
        { comb: "4 - 1", odds: 9.6, bet: 1000 },
        { comb: "4 - 8", odds: 18.5, bet: 500 }
      ],
      totalBet: 3000
    },
    result: {
      isSettled: true,
      orderOfFinish: [4, 7, 1], // 的中
      payout: 7200, // 4.8倍 × 1500円 = 7200円
      isHit: true
    },
    horses: [
      { num: 1, waku: 1, name: "タガノペルフェット", jockey: "黒岩 悠", weight: 60.0, odds: 6.5, score: 80.5, mark: "▲" },
      { num: 2, waku: 2, name: "スマートキャット", jockey: "上野 翔", weight: 60.0, odds: 32.0, score: 65.0, mark: "" },
      { num: 3, waku: 3, name: "メイショウキョウジ", jockey: "難波 剛健", weight: 60.0, odds: 48.0, score: 62.0, mark: "" },
      { num: 4, waku: 4, name: "ダイシンクローバー", jockey: "高田 潤", weight: 60.0, odds: 2.2, score: 93.0, mark: "◎" },
      { num: 5, waku: 5, name: "ケイティクレバー", jockey: "小野寺 祐太", weight: 60.0, odds: 24.0, score: 68.0, mark: "" },
      { num: 6, waku: 6, name: "ロードアクア", jockey: "中村 将之", weight: 60.0, odds: 55.0, score: 59.0, mark: "" },
      { num: 7, waku: 7, name: "マイネルグロン", jockey: "石神 深一", weight: 60.0, odds: 3.5, score: 88.0, mark: "◯" },
      { num: 8, waku: 8, name: "テイエムチューハイ", jockey: "小牧 加矢太", weight: 60.0, odds: 12.0, score: 75.0, mark: "△" }
    ]
  },
  {
    id: "hanshin-05",
    venue: "阪神",
    raceNumber: 5,
    raceName: "2歳新馬",
    grade: "",
    time: "12:25",
    track: "芝",
    distance: 1800,
    weather: "晴",
    condition: "良",
    isGraded: false,
    confidence: { level: "S", percentage: 90, text: "自信度 S (90%)" },
    recommendation: {
      type: "3連単",
      formation: "1着 8 → 2着 3, 5 → 3着 2, 3, 5, 7 (6点)",
      details: "超良血クラシック候補8番の頭固定",
      breakdown: [
        { comb: "8 → 3 → 2", odds: 24.5, bet: 500 },
        { comb: "8 → 3 → 5", odds: 15.2, bet: 500 },
        { comb: "8 → 3 → 7", odds: 38.0, bet: 500 },
        { comb: "8 → 5 → 2", odds: 19.8, bet: 500 },
        { comb: "8 → 5 → 3", odds: 16.5, bet: 500 },
        { comb: "8 → 5 → 7", odds: 32.0, bet: 500 }
      ],
      totalBet: 3000
    },
    result: {
      isSettled: true,
      orderOfFinish: [8, 5, 3], // 的中
      payout: 8250, // 16.5倍 × 500円 = 8250円
      isHit: true
    },
    horses: [
      { num: 1, waku: 1, name: "アドマイヤソラ", jockey: "岩田 望来", weight: 55.0, odds: 29.0, score: 68.5, mark: "" },
      { num: 2, waku: 2, name: "ホウオウプロサンゲ", jockey: "坂井 瑠星", weight: 55.0, odds: 8.4, score: 79.2, mark: "△" },
      { num: 3, waku: 3, name: "インテグレイト", jockey: "松山 弘平", weight: 55.0, odds: 4.5, score: 85.0, mark: "▲" },
      { num: 4, waku: 4, name: "ショウナンラプンタ", jockey: "鮫島 克駿", weight: 55.0, odds: 44.0, score: 65.0, mark: "" },
      { num: 5, waku: 5, name: "ダノンエアズロック", jockey: "C.ルメール", weight: 55.0, odds: 3.2, score: 89.4, mark: "◯" },
      { num: 6, waku: 6, name: "シゲルショウグン", jockey: "和田 竜二", weight: 55.0, odds: 67.0, score: 58.0, mark: "" },
      { num: 7, waku: 7, name: "サトノシュトラーセ", jockey: "M.デムーロ", weight: 55.0, odds: 14.5, score: 75.8, mark: "☆" },
      { num: 8, waku: 8, name: "レガレイラ", jockey: "川田 将雅", weight: 55.0, odds: 1.9, score: 96.0, mark: "◎" }
    ]
  },
  {
    id: "hanshin-06",
    venue: "阪神",
    raceNumber: 6,
    raceName: "3歳以上1勝クラス",
    grade: "",
    time: "12:55",
    track: "ダート",
    distance: 1200,
    weather: "晴",
    condition: "良",
    isGraded: false,
    confidence: { level: "B", percentage: 65, text: "自信度 B (65%)" },
    recommendation: {
      type: "馬連",
      formation: "4頭BOX 2, 7, 11, 14 (6点 各500円)",
      details: "混戦短距離戦を手広くボックス攻略",
      breakdown: [
        { comb: "2 - 7", odds: 18.2, bet: 500 },
        { comb: "2 - 11", odds: 12.5, bet: 500 },
        { comb: "2 - 14", odds: 25.0, bet: 500 },
        { comb: "7 - 11", odds: 8.4, bet: 500 },
        { comb: "7 - 14", odds: 16.0, bet: 500 },
        { comb: "11 - 14", odds: 14.5, bet: 500 }
      ],
      totalBet: 3000
    },
    result: {
      isSettled: true,
      orderOfFinish: [7, 11, 3], // 7-11 的中
      payout: 4200, // 8.4倍 × 500円 = 4200円
      isHit: true
    },
    horses: [
      { num: 1, waku: 1, name: "コパノエミレーツ", jockey: "国分 恭介", weight: 57.0, odds: 38.0, score: 66.0, mark: "" },
      { num: 2, waku: 1, name: "スマートアイ", jockey: "武 豊", weight: 55.0, odds: 5.6, score: 82.5, mark: "▲" },
      { num: 3, waku: 2, name: "エイシンフェンサー", jockey: "川田 将雅", weight: 56.0, odds: 4.8, score: 79.0, mark: "" },
      { num: 4, waku: 3, name: "メイショウカジキ", jockey: "角田 大河", weight: 55.0, odds: 52.0, score: 62.0, mark: "" },
      { num: 5, waku: 3, name: "テイエムリステット", jockey: "酒井 学", weight: 56.0, odds: 70.0, score: 58.5, mark: "" },
      { num: 6, waku: 4, name: "ヤマニンルリュール", jockey: "横山 典弘", weight: 56.0, odds: 22.0, score: 71.0, mark: "" },
      { num: 7, waku: 5, name: "ロードラディウス", jockey: "坂井 瑠星", weight: 57.0, odds: 3.5, score: 88.0, mark: "◎" },
      { num: 8, waku: 5, name: "ミスズグランドオー", jockey: "幸 英明", weight: 57.0, odds: 45.0, score: 64.0, mark: "" },
      { num: 9, waku: 6, name: "タガノアレハンドラ", jockey: "松山 弘平", weight: 56.0, odds: 31.0, score: 68.0, mark: "" },
      { num: 10, waku: 6, name: "アスクビックスター", jockey: "池添 謙一", weight: 57.0, odds: 62.0, score: 60.0, mark: "" },
      { num: 11, waku: 7, name: "カセノダンサー", jockey: "岩田 望来", weight: 56.0, odds: 4.2, score: 85.5, mark: "◯" },
      { num: 12, waku: 7, name: "サンライズプルート", jockey: "富田 暁", weight: 57.0, odds: 85.0, score: 56.0, mark: "" },
      { num: 13, waku: 8, name: "ワンダーブレット", jockey: "和田 竜二", weight: 57.0, odds: 36.0, score: 67.0, mark: "" },
      { num: 14, waku: 8, name: "スズカコーズマン", jockey: "西村 淳也", weight: 57.0, odds: 8.9, score: 78.0, mark: "△" }
    ]
  },
  {
    id: "hanshin-07",
    venue: "阪神",
    raceNumber: 7,
    raceName: "3歳以上1勝クラス",
    grade: "",
    time: "13:25",
    track: "芝",
    distance: 2000,
    weather: "晴",
    condition: "良",
    isGraded: false,
    confidence: { level: "A", percentage: 82, text: "自信度 A (82%)" },
    recommendation: {
      type: "3連複",
      formation: "軸 3 - 相手 1, 6, 8, 10 (6点 各500円)",
      details: "開幕週の芝内枠利を活かす3番軸",
      breakdown: [
        { comb: "3 - 1 - 6", odds: 16.0, bet: 500 },
        { comb: "3 - 1 - 8", odds: 28.5, bet: 500 },
        { comb: "3 - 1 - 10", odds: 9.8, bet: 500 },
        { comb: "3 - 6 - 8", odds: 34.0, bet: 500 },
        { comb: "3 - 6 - 10", odds: 12.4, bet: 500 },
        { comb: "3 - 8 - 10", odds: 21.0, bet: 500 }
      ],
      totalBet: 3000
    },
    result: {
      isSettled: true,
      orderOfFinish: [3, 10, 6], // 3-6-10 的中
      payout: 6200, // 12.4倍 × 500円 = 6200円
      isHit: true
    },
    horses: [
      { num: 1, waku: 1, name: "シルバースペード", jockey: "松山 弘平", weight: 56.0, odds: 6.2, score: 80.0, mark: "▲" },
      { num: 2, waku: 2, name: "マイネルカンパーナ", jockey: "丹内 祐次", weight: 56.0, odds: 44.0, score: 64.0, mark: "" },
      { num: 3, waku: 3, name: "サトノグランツ", jockey: "川田 将雅", weight: 55.0, odds: 2.3, score: 94.0, mark: "◎" },
      { num: 4, waku: 4, name: "アスクドゥポルテ", jockey: "岩田 康誠", weight: 55.0, odds: 32.0, score: 68.0, mark: "" },
      { num: 5, waku: 5, name: "エグランティーヌ", jockey: "藤岡 佑介", weight: 56.0, odds: 58.0, score: 61.0, mark: "" },
      { num: 6, waku: 6, name: "シェイクユアハート", jockey: "古川 吉洋", weight: 55.0, odds: 8.5, score: 77.0, mark: "△" },
      { num: 7, waku: 7, name: "ワンダイレクト", jockey: "武 豊", weight: 55.0, odds: 18.0, score: 72.0, mark: "" },
      { num: 8, waku: 7, name: "キミノナハセンター", jockey: "M.デムーロ", weight: 56.0, odds: 15.0, score: 74.0, mark: "☆" },
      { num: 9, waku: 8, name: "トーセンクライマー", jockey: "富田 暁", weight: 56.0, odds: 75.0, score: 57.0, mark: "" },
      { num: 10, waku: 8, name: "ハーツコンチェルト", jockey: "松若 風馬", weight: 55.0, odds: 3.9, score: 87.0, mark: "◯" }
    ]
  },
  {
    id: "hanshin-08",
    venue: "阪神",
    raceNumber: 8,
    raceName: "3歳以上2勝クラス",
    grade: "",
    time: "13:55",
    track: "ダート",
    distance: 1800,
    weather: "晴",
    condition: "良",
    isGraded: false,
    confidence: { level: "B", percentage: 70, text: "自信度 B (70%)" },
    recommendation: {
      type: "馬単",
      formation: "1着 5 → 2着 1, 9, 11 (3点)",
      details: "スピード上位5番の逃げ切り期待",
      breakdown: [
        { comb: "5 → 1", odds: 7.2, bet: 1000 },
        { comb: "5 → 9", odds: 12.0, bet: 1000 },
        { comb: "5 → 11", odds: 18.5, bet: 1000 }
      ],
      totalBet: 3000
    },
    result: {
      isSettled: true,
      orderOfFinish: [9, 5, 1], // 逆転不的中
      payout: 0,
      isHit: false
    },
    horses: [
      { num: 1, waku: 1, name: "ウェルカムニュース", jockey: "C.ルメール", weight: 57.0, odds: 3.8, score: 86.0, mark: "◯" },
      { num: 2, waku: 2, name: "ホウオウルバン", jockey: "団野 大成", weight: 58.0, odds: 50.0, score: 63.0, mark: "" },
      { num: 3, waku: 3, name: "ロードヴァレンチ", jockey: "永野 猛蔵", weight: 57.0, odds: 29.0, score: 69.0, mark: "" },
      { num: 4, waku: 4, name: "ダンツキャッスル", jockey: "角田 大河", weight: 57.0, odds: 62.0, score: 60.0, mark: "" },
      { num: 5, waku: 5, name: "ミスティックロア", jockey: "川田 将雅", weight: 55.0, odds: 2.1, score: 92.0, mark: "◎" },
      { num: 6, waku: 6, name: "メイショウモズ", jockey: "幸 英明", weight: 58.0, odds: 38.0, score: 66.0, mark: "" },
      { num: 7, waku: 7, name: "サンマルパトロール", jockey: "和田 竜二", weight: 58.0, odds: 45.0, score: 64.0, mark: "" },
      { num: 8, waku: 7, name: "トウセツ", jockey: "藤岡 佑介", weight: 58.0, odds: 33.0, score: 67.0, mark: "" },
      { num: 9, waku: 8, name: "リキサントライ", jockey: "坂井 瑠星", weight: 55.0, odds: 5.4, score: 83.0, mark: "▲" },
      { num: 10, waku: 8, name: "コパノニコルソン", jockey: "松山 弘平", weight: 58.0, odds: 11.0, score: 76.0, mark: "△" }
    ]
  },
  {
    id: "hanshin-09",
    venue: "阪神",
    raceNumber: 9,
    raceName: "野路菊ステークス",
    grade: "OP",
    time: "14:25",
    track: "芝",
    distance: 1800,
    weather: "晴",
    condition: "良",
    isGraded: false,
    confidence: { level: "S", percentage: 89, text: "自信度 S (89%)" },
    recommendation: {
      type: "3連単",
      formation: "1着 2 → 2着 4, 6 → 3着 1, 4, 6 (4点 各750円)",
      details: "素質馬2番の少頭数完勝狙い",
      breakdown: [
        { comb: "2 → 4 → 1", odds: 21.0, bet: 750 },
        { comb: "2 → 4 → 6", odds: 9.6, bet: 750 },
        { comb: "2 → 6 → 1", odds: 34.0, bet: 750 },
        { comb: "2 → 6 → 4", odds: 11.2, bet: 750 }
      ],
      totalBet: 3000
    },
    result: {
      isSettled: true,
      orderOfFinish: [2, 4, 6], // 的中
      payout: 7200, // 9.6倍 × 750円 = 7200円
      isHit: true
    },
    horses: [
      { num: 1, waku: 1, name: "カテドラル", jockey: "横山 典弘", weight: 55.0, odds: 8.5, score: 77.0, mark: "△" },
      { num: 2, waku: 2, name: "ヴェロックス", jockey: "川田 将雅", weight: 55.0, odds: 1.6, score: 96.0, mark: "◎" },
      { num: 3, waku: 3, name: "メイショウショウブ", jockey: "池添 謙一", weight: 55.0, odds: 22.0, score: 68.0, mark: "" },
      { num: 4, waku: 4, name: "ミッキーブラック", jockey: "C.ルメール", weight: 55.0, odds: 3.8, score: 89.0, mark: "◯" },
      { num: 5, waku: 5, name: "アントリューズ", jockey: "武 豊", weight: 55.0, odds: 30.0, score: 65.0, mark: "" },
      { num: 6, waku: 6, name: "ダノンチェイサー", jockey: "坂井 瑠星", weight: 55.0, odds: 5.1, score: 84.0, mark: "▲" }
    ]
  },
  {
    id: "hanshin-10",
    venue: "阪神",
    raceNumber: 10,
    raceName: "甲東特別",
    grade: "2勝クラス",
    time: "15:00",
    track: "芝",
    distance: 1600,
    weather: "晴",
    condition: "良",
    isGraded: false,
    confidence: { level: "A", percentage: 76, text: "自信度 A (76%)" },
    recommendation: {
      type: "3連複",
      formation: "軸 7 - 相手 3, 5, 8, 11 (6点 各500円)",
      details: "マイル巧者7番の末脚強襲",
      breakdown: [
        { comb: "7 - 3 - 5", odds: 24.0, bet: 500 },
        { comb: "7 - 3 - 8", odds: 38.0, bet: 500 },
        { comb: "7 - 3 - 11", odds: 12.0, bet: 500 },
        { comb: "7 - 5 - 8", odds: 19.5, bet: 500 },
        { comb: "7 - 5 - 11", odds: 7.8, bet: 500 },
        { comb: "7 - 8 - 11", odds: 15.0, bet: 500 }
      ],
      totalBet: 3000
    },
    result: {
      isSettled: true,
      orderOfFinish: [7, 5, 8], // 的中
      payout: 9750, // 19.5倍 × 500円 = 9750円
      isHit: true
    },
    horses: [
      { num: 1, waku: 1, name: "エイシンバッカス", jockey: "幸 英明", weight: 58.0, odds: 45.0, score: 63.0, mark: "" },
      { num: 2, waku: 2, name: "ウインシャーロット", jockey: "石川 裕紀人", weight: 56.0, odds: 32.0, score: 68.0, mark: "" },
      { num: 3, waku: 3, name: "ドロップオブライト", jockey: "小沢 大仁", weight: 56.0, odds: 14.0, score: 75.0, mark: "☆" },
      { num: 4, waku: 4, name: "ショウナンアレス", jockey: "池添 謙一", weight: 58.0, odds: 28.0, score: 69.0, mark: "" },
      { num: 5, waku: 5, name: "ディオ", jockey: "岩田 康誠", weight: 58.0, odds: 4.2, score: 86.0, mark: "◯" },
      { num: 6, waku: 6, name: "ルージュラテール", jockey: "藤岡 佑介", weight: 56.0, odds: 50.0, score: 61.0, mark: "" },
      { num: 7, waku: 6, name: "ジュンブロッサム", jockey: "武 豊", weight: 58.0, odds: 2.8, score: 93.0, mark: "◎" },
      { num: 8, waku: 7, name: "スパイダーゴールド", jockey: "C.ルメール", weight: 58.0, odds: 6.8, score: 81.0, mark: "▲" },
      { num: 9, waku: 7, name: "アルナシーム", jockey: "鮫島 克駿", weight: 58.0, odds: 16.0, score: 73.0, mark: "" },
      { num: 10, waku: 8, name: "ソウテン", jockey: "松山 弘平", weight: 58.0, odds: 39.0, score: 66.0, mark: "" },
      { num: 11, waku: 8, name: "グランディア", jockey: "川田 将雅", weight: 58.0, odds: 3.9, score: 88.0, mark: "△" }
    ]
  },
  {
    id: "hanshin-11",
    venue: "阪神",
    raceNumber: 11,
    raceName: "神戸新聞杯",
    grade: "GII",
    time: "15:35",
    track: "芝",
    distance: 2400,
    weather: "晴",
    condition: "良",
    isGraded: true,
    confidence: { level: "S", percentage: 95, text: "自信度 S (95%)" },
    recommendation: {
      type: "3連単",
      formation: "1着 4 → 2着 7, 12 → 3着 1, 7, 10, 12 (6点 各500円)",
      details: "菊花賞最有力4番が断然！相手絞り撃ち",
      breakdown: [
        { comb: "4 → 7 → 1", odds: 22.0, bet: 500 },
        { comb: "4 → 7 → 10", odds: 35.0, bet: 500 },
        { comb: "4 → 7 → 12", odds: 12.8, bet: 500 },
        { comb: "4 → 12 → 1", odds: 18.5, bet: 500 },
        { comb: "4 → 12 → 7", odds: 14.2, bet: 500 },
        { comb: "4 → 12 → 10", odds: 29.0, bet: 500 }
      ],
      totalBet: 3000
    },
    result: {
      isSettled: true,
      orderOfFinish: [4, 7, 12], // 的中
      payout: 6400, // 12.8倍 × 500円 = 6400円
      isHit: true
    },
    horses: [
      { num: 1, waku: 1, name: "サヴォーナ", jockey: "池添 謙一", weight: 57.0, odds: 11.2, score: 79.5, mark: "△" },
      { num: 2, waku: 2, name: "バビット", jockey: "団野 大成", weight: 57.0, odds: 65.0, score: 61.0, mark: "" },
      { num: 3, waku: 3, name: "ナイトインロンドン", jockey: "和田 竜二", weight: 57.0, odds: 28.0, score: 71.0, mark: "" },
      { num: 4, waku: 4, name: "サトノグランツ", jockey: "川田 将雅", weight: 57.0, odds: 2.2, score: 96.5, mark: "◎" },
      { num: 5, waku: 4, name: "マイネルラウレア", jockey: "M.デムーロ", weight: 57.0, odds: 41.0, score: 66.0, mark: "" },
      { num: 6, waku: 5, name: "シーズンリッチ", jockey: "角田 大河", weight: 57.0, odds: 36.0, score: 68.0, mark: "" },
      { num: 7, waku: 5, name: "ファントムシーフ", jockey: "武 豊", weight: 57.0, odds: 3.4, score: 91.0, mark: "◯" },
      { num: 8, waku: 6, name: "スマートファントム", jockey: "藤岡 佑介", weight: 57.0, odds: 88.0, score: 58.0, mark: "" },
      { num: 9, waku: 6, name: "ビキニボーイ", jockey: "幸 英明", weight: 57.0, odds: 110.0, score: 55.0, mark: "" },
      { num: 10, waku: 7, name: "ショウナンバシット", jockey: "M.デムーロ", weight: 57.0, odds: 15.0, score: 76.0, mark: "☆" },
      { num: 11, waku: 7, name: "ロードデルレイ", jockey: "坂井 瑠星", weight: 57.0, odds: 9.8, score: 80.0, mark: "" },
      { num: 12, waku: 8, name: "ハーツコンチェルト", jockey: "松山 弘平", weight: 57.0, odds: 4.8, score: 88.5, mark: "▲" },
      { num: 13, waku: 8, name: "サスツルギ", jockey: "北村 友一", weight: 57.0, odds: 52.0, score: 63.5, mark: "" }
    ]
  },
  {
    id: "hanshin-12",
    venue: "阪神",
    raceNumber: 12,
    raceName: "3歳以上2勝クラス",
    grade: "",
    time: "16:10",
    track: "ダート",
    distance: 1400,
    weather: "晴",
    condition: "良",
    isGraded: false,
    confidence: { level: "A", percentage: 78, text: "自信度 A (78%)" },
    recommendation: {
      type: "馬連",
      formation: "◎ 8 - ◯ 3, ▲ 11, △ 14 (3点)",
      details: "最終レースの波乱抑え！8番軸",
      breakdown: [
        { comb: "8 - 3", odds: 6.5, bet: 1500 },
        { comb: "8 - 11", odds: 11.0, bet: 1000 },
        { comb: "8 - 14", odds: 21.0, bet: 500 }
      ],
      totalBet: 3000
    },
    result: {
      isSettled: true,
      orderOfFinish: [8, 3, 6], // 8-3 的中
      payout: 9750, // 6.5倍 × 1500円 = 9750円
      isHit: true
    },
    horses: [
      { num: 1, waku: 1, name: "タイセイエピソード", jockey: "酒井 学", weight: 58.0, odds: 42.0, score: 65.0, mark: "" },
      { num: 2, waku: 2, name: "テイエムランウェイ", jockey: "国分 恭介", weight: 58.0, odds: 55.0, score: 62.0, mark: "" },
      { num: 3, waku: 3, name: "エーティーマクフィ", jockey: "坂井 瑠星", weight: 57.0, odds: 4.1, score: 87.0, mark: "◯" },
      { num: 4, waku: 3, name: "メイショウヒューマ", jockey: "角田 大河", weight: 57.0, odds: 38.0, score: 67.0, mark: "" },
      { num: 5, waku: 4, name: "スマートラプター", jockey: "武 豊", weight: 58.0, odds: 15.0, score: 74.0, mark: "" },
      { num: 6, waku: 4, name: "ワセダハーツ", jockey: "松山 弘平", weight: 58.0, odds: 18.0, score: 72.0, mark: "" },
      { num: 7, waku: 5, name: "ロードオルデン", jockey: "藤岡 佑介", weight: 58.0, odds: 25.0, score: 70.0, mark: "" },
      { num: 8, waku: 5, name: "パラシュラーマ", jockey: "川田 将雅", weight: 57.0, odds: 2.5, score: 93.0, mark: "◎" },
      { num: 9, waku: 6, name: "ラインガルーダ", jockey: "団野 大成", weight: 58.0, odds: 60.0, score: 61.0, mark: "" },
      { num: 10, waku: 6, name: "グットディール", jockey: "富田 暁", weight: 58.0, odds: 70.0, score: 59.0, mark: "" },
      { num: 11, waku: 7, name: "ペプチドタイガー", jockey: "岩田 望来", weight: 57.0, odds: 6.8, score: 82.0, mark: "▲" },
      { num: 12, waku: 7, name: "コパノパサディナ", jockey: "幸 英明", weight: 58.0, odds: 33.0, score: 68.0, mark: "" },
      { num: 13, waku: 8, name: "タガノエスコート", jockey: "和田 竜二", weight: 58.0, odds: 48.0, score: 64.0, mark: "" },
      { num: 14, waku: 8, name: "メイショウジブリ", jockey: "M.デムーロ", weight: 58.0, odds: 9.4, score: 78.0, mark: "△" }
    ]
  },
  {
    id: "tokyo-11",
    venue: "東京",
    raceNumber: 11,
    raceName: "日本ダービー",
    grade: "GI",
    time: "15:40",
    track: "芝",
    distance: 2400,
    weather: "快晴",
    condition: "良",
    isGraded: true,
    confidence: { level: "S", percentage: 98, text: "自信度 S (98%)" },
    recommendation: {
      type: "3連単",
      formation: "1着 5 → 2着 2, 12 → 3着 1, 2, 9, 12, 14 (8点)",
      details: "【最高評価】二冠確実の本命5番から世代最強布陣へ！",
      breakdown: [
        { comb: "5 → 2 → 1", odds: 38.0, bet: 300 },
        { comb: "5 → 2 → 9", odds: 42.0, bet: 300 },
        { comb: "5 → 2 → 12", odds: 15.5, bet: 600 },
        { comb: "5 → 2 → 14", odds: 55.0, bet: 300 },
        { comb: "5 → 12 → 1", odds: 28.0, bet: 300 },
        { comb: "5 → 12 → 2", odds: 16.8, bet: 600 },
        { comb: "5 → 12 → 9", odds: 32.0, bet: 300 },
        { comb: "5 → 12 → 14", odds: 48.0, bet: 300 }
      ],
      totalBet: 3000
    },
    result: {
      isSettled: true,
      orderOfFinish: [5, 2, 12], // 的中！
      payout: 9300, // 15.5倍 × 600円 = 9300円
      isHit: true
    },
    horses: [
      { num: 1, waku: 1, name: "サンライズジパング", jockey: "菅原 明良", weight: 57.0, odds: 18.5, score: 81.0, mark: "△" },
      { num: 2, waku: 1, name: "レガレイラ", jockey: "C.ルメール", weight: 55.0, odds: 4.2, score: 94.0, mark: "◯" },
      { num: 3, waku: 2, name: "ジューンテイク", jockey: "藤岡 佑介", weight: 57.0, odds: 62.0, score: 68.0, mark: "" },
      { num: 4, waku: 2, name: "ミスタージーティー", jockey: "坂井 瑠星", weight: 57.0, odds: 45.0, score: 72.0, mark: "" },
      { num: 5, waku: 3, name: "ジャスティンミラノ", jockey: "戸崎 圭太", weight: 57.0, odds: 2.1, score: 98.2, mark: "◎" },
      { num: 6, waku: 3, name: "コスモキュランダ", jockey: "M.デムーロ", weight: 57.0, odds: 12.0, score: 83.5, mark: "" },
      { num: 7, waku: 4, name: "ヴェロキラプトル", jockey: "横山 和生", weight: 57.0, odds: 120.0, score: 58.0, mark: "" },
      { num: 8, waku: 4, name: "アーバンシック", jockey: "横山 武史", weight: 57.0, odds: 9.8, score: 82.0, mark: "" },
      { num: 9, waku: 5, name: "ダノンエアズロック", jockey: "J.モレイラ", weight: 57.0, odds: 8.5, score: 85.0, mark: "☆" },
      { num: 10, waku: 5, name: "サンライズアース", jockey: "池添 謙一", weight: 57.0, odds: 38.0, score: 74.0, mark: "" },
      { num: 11, waku: 6, name: "シュガークン", jockey: "武 豊", weight: 57.0, odds: 14.0, score: 79.0, mark: "" },
      { num: 12, waku: 6, name: "シックスペンス", jockey: "川田 将雅", weight: 57.0, odds: 3.8, score: 92.5, mark: "▲" },
      { num: 13, waku: 7, name: "シンエンペラー", jockey: "坂井 瑠星", weight: 57.0, odds: 16.0, score: 80.0, mark: "" },
      { num: 14, waku: 7, name: "ゴンバデカーブース", jockey: "松山 弘平", weight: 57.0, odds: 22.0, score: 77.5, mark: "△" },
      { num: 15, waku: 8, name: "メイショウタバル", jockey: "浜中 俊", weight: 57.0, odds: 26.0, score: 75.0, mark: "" },
      { num: 16, waku: 8, name: "ショウナンラプンタ", jockey: "鮫島 克駿", weight: 57.0, odds: 55.0, score: 70.0, mark: "" }
    ]
  }
];

window.MOCK_RACES = MOCK_RACES;
