// ===== i18n — 다국어 지원 =====
// 지원 언어: ko(기본), en, zh, ja
// 그 외 브라우저 언어 → 영어 자동 선택

const LANGS = {
  ko: {
    // 브랜드
    brandTitle: 'AI 모닝 브리핑',
    brandSubtitle: '증시흐름',
    // 탭
    tabDashboard: '대시보드',
    tabHistory: '히스토리',
    tabPortfolio: '포트폴리오',
    // 버튼
    btnGenerate: '새 브리핑 생성',
    btnRefresh: '새로고침',
    btnSave: '저장',
    btnAddAsset: '자산 추가',
    btnFirstBriefing: '첫 번째 브리핑 생성하기',
    // 상태
    statusConnected: '연결됨',
    // 통계 리본
    statTodayVisitors: '오늘 방문자',
    statTotalVisitors: '누적 방문자',
    statTodayApi: '오늘 API 호출',
    statTotalApi: '누적 API 호출',
    // 섹션 헤더
    sectionMarket: '📊 실시간 시장 데이터',
    sectionBriefing: '🧠 AI 모닝 브리핑',
    sectionHistory: '📅 브리핑 히스토리',
    sectionPortfolio: '💼 포트폴리오 설정',
    // 빈 상태
    emptyBriefingTitle: '아직 생성된 브리핑이 없습니다',
    emptyBriefingDesc: '상단의 "새 브리핑 생성" 버튼을 클릭하여 오늘의 AI 마켓 브리핑을 생성하세요.',
    emptyHistoryTitle: '아직 저장된 브리핑이 없습니다',
    emptyHistoryDesc: '브리핑을 생성하면 자동으로 이곳에 기록됩니다.',
    // 로딩
    loadingTitle: 'AI 브리핑 생성 중',
    loadingDesc: '글로벌 뉴스와 시장 데이터를 분석하고 있습니다...',
    step1: '뉴스 수집',
    step2: '뉴스 필터링',
    step3: '시장 데이터 조회',
    step4: 'AI 분석',
    // 포트폴리오
    labelStyle: '투자 스타일',
    labelRisk: '리스크 허용도',
    labelAssets: '총 자산 규모 (선택사항)',
    labelAllocation: '자산 배분',
    labelWatchlist: '관심 종목 (Watchlist)',
    placeholderAssets: '예: 1억원, $100,000',
    placeholderWatchlist: '쉼표로 구분. 예: NVDA, AAPL, TSLA',
    placeholderAllocName: '자산명 (예: 주식, 테크)',
    placeholderAllocDetail: '상세 (예: 미국 대형주)',
    optConservative: '보수적 (Conservative)',
    optModerate: '중립 (Moderate)',
    optGrowth: '성장 (Growth)',
    optAggressive: '공격적 (Aggressive)',
    optLow: '낮음 (Low)',
    optMedium: '중간 (Medium)',
    optMediumHigh: '중간-높음 (Medium-High)',
    optHigh: '높음 (High)',
    // 메타
    metaNews: (n) => `📰 뉴스 ${n}건 분석`,
    metaDateLocale: 'ko-KR',
    // 토스트
    toastBriefingOk: '브리핑이 성공적으로 생성되었습니다!',
    toastBriefingFail: '브리핑 생성 실패: ',
    toastConnFail: '서버 연결 실패. 다시 시도해 주세요.',
    toastBriefingLoaded: '이전 브리핑을 불러왔습니다.',
    toastBriefingLoadFail: '브리핑 로드 실패',
    toastPortfolioOk: '저장되었습니다. 다음 브리핑에 포트폴리오 기반 분석이 포함됩니다.',
    toastSaveFail: '저장 실패',
    toastAlreadyRunning: '이미 브리핑 생성 중입니다. 잠시 후 다시 시도하세요.',
    shareBtn: '공유',
    shareCopied: '링크가 클립보드에 복사되었습니다!',
    shareNative: '브리핑 공유',
    // 차트
    chartLoading: '차트 로딩 중...',
    chartNoData: '데이터 없음',
    chartClose: '닫기',
    chartError: '차트 로드 실패',
    // 브리핑 콘텐츠 키워드 (섹션 아이콘용)
    kw_macro: '매크로',
    kw_global: '글로벌',
    kw_direction: '방향성',
    kw_probability: '확률',
    kw_sector: '섹터',
    kw_leadership: '리더십',
    kw_risk: '리스크',
    kw_trade: '트레이드',
    kw_dashboard: '대시보드',
    kw_portfolio: '포트폴리오',
  },

  en: {
    brandTitle: 'AI Morning Briefing',
    brandSubtitle: 'Market Flow',
    tabDashboard: 'Dashboard',
    tabHistory: 'History',
    tabPortfolio: 'Portfolio',
    btnGenerate: 'New Briefing',
    btnRefresh: 'Refresh',
    btnSave: 'Save',
    btnAddAsset: 'Add Asset',
    btnFirstBriefing: 'Generate First Briefing',
    statusConnected: 'Connected',
    statTodayVisitors: "Today's Visitors",
    statTotalVisitors: 'Total Visitors',
    statTodayApi: "Today's Generations",
    statTotalApi: 'Total Generations',
    sectionMarket: '📊 Real-time Market Data',
    sectionBriefing: '🧠 AI Morning Briefing',
    sectionHistory: '📅 Briefing History',
    sectionPortfolio: '💼 Portfolio Settings',
    emptyBriefingTitle: 'No briefings generated yet',
    emptyBriefingDesc: 'Click the "New Briefing" button above to generate today\'s AI market briefing.',
    emptyHistoryTitle: 'No saved briefings yet',
    emptyHistoryDesc: 'Briefings will be automatically saved here.',
    loadingTitle: 'Generating AI Briefing',
    loadingDesc: 'Analyzing global news and market data...',
    step1: 'News Collection',
    step2: 'News Filtering',
    step3: 'Market Data Fetch',
    step4: 'AI Analysis',
    labelStyle: 'Investment Style',
    labelRisk: 'Risk Tolerance',
    labelAssets: 'Total Assets (Optional)',
    labelAllocation: 'Asset Allocation',
    labelWatchlist: 'Watchlist',
    placeholderAssets: 'e.g. $100,000',
    placeholderWatchlist: 'Comma separated. e.g. NVDA, AAPL, TSLA',
    placeholderAllocName: 'Asset (e.g. Stocks, Tech)',
    placeholderAllocDetail: 'Details (e.g. US Large Cap)',
    optConservative: 'Conservative',
    optModerate: 'Moderate',
    optGrowth: 'Growth',
    optAggressive: 'Aggressive',
    optLow: 'Low',
    optMedium: 'Medium',
    optMediumHigh: 'Medium-High',
    optHigh: 'High',
    metaNews: (n) => `📰 ${n} news analyzed`,
    metaDateLocale: 'en-US',
    toastBriefingOk: 'Briefing generated successfully!',
    toastBriefingFail: 'Briefing generation failed: ',
    toastConnFail: 'Server connection failed. Please try again.',
    toastBriefingLoaded: 'Previous briefing loaded.',
    toastBriefingLoadFail: 'Failed to load briefing',
    toastPortfolioOk: 'Saved. Portfolio analysis will be included in the next briefing.',
    toastSaveFail: 'Save failed',
    toastAlreadyRunning: 'Briefing is already being generated. Please wait.',
    shareBtn: 'Share',
    shareCopied: 'Link copied to clipboard!',
    shareNative: 'Share this briefing',
    chartLoading: 'Loading chart...',
    chartNoData: 'No data available',
    chartClose: 'Close',
    chartError: 'Failed to load chart',
    kw_macro: 'Macro',
    kw_global: 'Global',
    kw_direction: 'Direction',
    kw_probability: 'Probability',
    kw_sector: 'Sector',
    kw_leadership: 'Leadership',
    kw_risk: 'Risk',
    kw_trade: 'Trade',
    kw_dashboard: 'Dashboard',
    kw_portfolio: 'Portfolio',
  },

  zh: {
    brandTitle: 'AI 晨间简报',
    brandSubtitle: '市场动态',
    tabDashboard: '仪表盘',
    tabHistory: '历史',
    tabPortfolio: '投资组合',
    btnGenerate: '生成简报',
    btnRefresh: '刷新',
    btnSave: '保存',
    btnAddAsset: '添加资产',
    btnFirstBriefing: '生成第一份简报',
    statusConnected: '已连接',
    statTodayVisitors: '今日访客',
    statTotalVisitors: '累计访客',
    statTodayApi: '今日生成次数',
    statTotalApi: '累计生成次数',
    sectionMarket: '📊 实时市场数据',
    sectionBriefing: '🧠 AI 晨间简报',
    sectionHistory: '📅 简报历史',
    sectionPortfolio: '💼 投资组合设置',
    emptyBriefingTitle: '尚未生成简报',
    emptyBriefingDesc: '点击上方"生成简报"按钮，生成今日 AI 市场简报。',
    emptyHistoryTitle: '暂无保存的简报',
    emptyHistoryDesc: '生成简报后将自动保存在此处。',
    loadingTitle: '正在生成 AI 简报',
    loadingDesc: '正在分析全球新闻和市场数据...',
    step1: '新闻收集',
    step2: '新闻过滤',
    step3: '市场数据获取',
    step4: 'AI 分析',
    labelStyle: '投资风格',
    labelRisk: '风险承受度',
    labelAssets: '总资产规模（可选）',
    labelAllocation: '资产配置',
    labelWatchlist: '关注列表',
    placeholderAssets: '例：$100,000',
    placeholderWatchlist: '逗号分隔，例：NVDA, AAPL, TSLA',
    placeholderAllocName: '资产名称（如：股票、科技）',
    placeholderAllocDetail: '详情（如：美国大盘股）',
    optConservative: '保守型',
    optModerate: '均衡型',
    optGrowth: '成长型',
    optAggressive: '激进型',
    optLow: '低',
    optMedium: '中',
    optMediumHigh: '中高',
    optHigh: '高',
    metaNews: (n) => `📰 分析了 ${n} 条新闻`,
    metaDateLocale: 'zh-CN',
    toastBriefingOk: '简报生成成功！',
    toastBriefingFail: '简报生成失败：',
    toastConnFail: '服务器连接失败，请重试。',
    toastBriefingLoaded: '已加载历史简报。',
    toastBriefingLoadFail: '加载简报失败',
    toastPortfolioOk: '已保存。下次生成简报时将包含投资组合分析。',
    toastSaveFail: '保存失败',
    toastAlreadyRunning: '简报正在生成中，请稍后再试。',
    shareBtn: '分享',
    shareCopied: '链接已复制到剪贴板！',
    shareNative: '分享简报',
    chartLoading: '图表加载中...',
    chartNoData: '暂无数据',
    chartClose: '关闭',
    chartError: '图表加载失败',
    kw_macro: 'Macro',
    kw_global: 'Global',
    kw_direction: 'Direction',
    kw_probability: 'Probability',
    kw_sector: 'Sector',
    kw_leadership: 'Leadership',
    kw_risk: 'Risk',
    kw_trade: 'Trade',
    kw_dashboard: 'Dashboard',
    kw_portfolio: 'Portfolio',
  },

  ja: {
    brandTitle: 'AI モーニングブリーフィング',
    brandSubtitle: '市場動向',
    tabDashboard: 'ダッシュボード',
    tabHistory: '履歴',
    tabPortfolio: 'ポートフォリオ',
    btnGenerate: '新規ブリーフィング',
    btnRefresh: '更新',
    btnSave: '保存',
    btnAddAsset: '資産追加',
    btnFirstBriefing: '最初のブリーフィングを生成',
    statusConnected: '接続済み',
    statTodayVisitors: '今日の訪問者',
    statTotalVisitors: '累計訪問者',
    statTodayApi: '今日の生成数',
    statTotalApi: '累計生成数',
    sectionMarket: '📊 リアルタイム市場データ',
    sectionBriefing: '🧠 AI モーニングブリーフィング',
    sectionHistory: '📅 ブリーフィング履歴',
    sectionPortfolio: '💼 ポートフォリオ設定',
    emptyBriefingTitle: 'まだブリーフィングがありません',
    emptyBriefingDesc: '上部の「新規ブリーフィング」ボタンをクリックして、今日のAIマーケットブリーフィングを生成してください。',
    emptyHistoryTitle: '保存されたブリーフィングはありません',
    emptyHistoryDesc: 'ブリーフィングを生成すると自動的にここに記録されます。',
    loadingTitle: 'AIブリーフィング生成中',
    loadingDesc: 'グローバルなニュースと市場データを分析しています...',
    step1: 'ニュース収集',
    step2: 'ニュースフィルタリング',
    step3: '市場データ取得',
    step4: 'AI分析',
    labelStyle: '投資スタイル',
    labelRisk: 'リスク許容度',
    labelAssets: '総資産規模（任意）',
    labelAllocation: '資産配分',
    labelWatchlist: 'ウォッチリスト',
    placeholderAssets: '例：$100,000',
    placeholderWatchlist: 'カンマ区切り。例：NVDA, AAPL, TSLA',
    placeholderAllocName: '資産名（例：株式、テック）',
    placeholderAllocDetail: '詳細（例：米国大型株）',
    optConservative: '保守的',
    optModerate: '均衡型',
    optGrowth: 'グロース型',
    optAggressive: 'アグレッシブ型',
    optLow: '低',
    optMedium: '中',
    optMediumHigh: '中高',
    optHigh: '高',
    metaNews: (n) => `📰 ${n}件のニュースを分析`,
    metaDateLocale: 'ja-JP',
    toastBriefingOk: 'ブリーフィングが正常に生成されました！',
    toastBriefingFail: 'ブリーフィング生成に失敗しました：',
    toastConnFail: 'サーバー接続に失敗しました。もう一度お試しください。',
    toastBriefingLoaded: '過去のブリーフィングを読み込みました。',
    toastBriefingLoadFail: 'ブリーフィングの読み込みに失敗しました',
    toastPortfolioOk: '保存しました。次のブリーフィングにポートフォリオ分析が含まれます。',
    toastSaveFail: '保存に失敗しました',
    toastAlreadyRunning: 'ブリーフィングを生成中です。しばらくお待ちください。',
    shareBtn: '共有',
    shareCopied: 'リンクをクリップボードにコピーしました！',
    shareNative: 'ブリーフィングを共有',
    chartLoading: 'チャート読み込み中...',
    chartNoData: 'データなし',
    chartClose: '閉じる',
    chartError: 'チャートの読み込みに失敗しました',
    kw_macro: 'Macro',
    kw_global: 'Global',
    kw_direction: 'Direction',
    kw_probability: 'Probability',
    kw_sector: 'Sector',
    kw_leadership: 'Leadership',
    kw_risk: 'Risk',
    kw_trade: 'Trade',
    kw_dashboard: 'Dashboard',
    kw_portfolio: 'Portfolio',
  },
};

const SUPPORTED_LANGS = ['ko', 'en', 'zh', 'ja'];
let currentLang = 'ko';

function detectLang() {
  const saved = localStorage.getItem('lang');
  if (saved && SUPPORTED_LANGS.includes(saved)) return saved;

  const nav = (navigator.language || 'en').toLowerCase();
  if (nav.startsWith('zh')) return 'zh';
  if (nav.startsWith('ja')) return 'ja';
  if (nav.startsWith('ko')) return 'ko';
  if (SUPPORTED_LANGS.includes(nav.slice(0, 2))) return nav.slice(0, 2);
  return 'en'; // 그 외 모두 영어
}

function t(key) {
  const dict = LANGS[currentLang] || LANGS['en'];
  return dict[key] !== undefined ? dict[key] : (LANGS['en'][key] !== undefined ? LANGS['en'][key] : key);
}

function setLang(lang) {
  if (!SUPPORTED_LANGS.includes(lang)) lang = 'en';
  currentLang = lang;
  localStorage.setItem('lang', lang);
  document.documentElement.lang = lang;
  applyLanguage();
  document.querySelectorAll('.lang-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.lang === lang);
  });
}

function applyLanguage() {
  document.querySelectorAll('[data-i18n]').forEach(el => {
    el.textContent = t(el.dataset.i18n);
  });
  document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
    el.placeholder = t(el.dataset.i18nPlaceholder);
  });
  // select option 번역
  document.querySelectorAll('[data-i18n-option]').forEach(el => {
    el.textContent = t(el.dataset.i18nOption);
  });
}

// 초기화 (DOMContentLoaded 이전에 lang 감지)
currentLang = detectLang();
document.documentElement.lang = currentLang;
