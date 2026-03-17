// ===== AI 모닝 마켓 브리핑 - Frontend App =====

// ===== CLIENT ID (사용자 식별) =====
function getClientId() {
  let id = localStorage.getItem('mbai_client_id');
  if (!id) {
    id = crypto.randomUUID().replace(/-/g, '');
    localStorage.setItem('mbai_client_id', id);
  }
  return id;
}

const API = {
  briefingLatest: '/api/briefing/latest',
  briefingHistory: '/api/briefing/history',
  briefingById: (id) => `/api/briefing/${id}`,
  briefingGenerate: '/api/briefing/generate/stream',
  marketSnapshot: '/api/market/snapshot',
  marketChart: (name, period) => `/api/market/chart?name=${encodeURIComponent(name)}&period=${period}`,
  portfolio: () => `/api/portfolio?client_id=${getClientId()}`,
  sectors: '/api/market/sectors',
  settings: '/api/settings',
  status: '/api/status',
  stats: '/api/stats',
  calendar: '/api/calendar'
};

// ===== STATE =====
let currentTab = 'dashboard';
let marketRefreshInterval = null;
let currentCurrency = 'KRW';
let rawMarketData = null;
let chartInstance = null;
let currentChartName = null;
let currentChartPeriod = '1d';
let favorites = new Set(JSON.parse(localStorage.getItem('mkt-favorites') || '[]'));

// ===== INITIALIZATION =====
document.addEventListener('DOMContentLoaded', () => {
  applyLanguage();
  highlightActiveLangBtn();
  initTabs();
  loadDashboard();
  startMarketRefresh();
  checkUrlBriefing();
});

function highlightActiveLangBtn() {
  document.querySelectorAll('.lang-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.lang === currentLang);
  });
}

// ===== 언어 변경 (브리핑 재생성 확인 포함) =====
function changeLang(lang) {
  if (lang === currentLang) return;
  const hasBriefing = !!_currentBriefingId;
  setLang(lang); // UI 즉시 전환
  highlightActiveLangBtn();
  if (!hasBriefing) return;

  // 브리핑이 있으면 재생성 확인 팝업
  const modal = document.getElementById('lang-confirm-modal');
  const msgEl = document.getElementById('lang-confirm-msg');
  const okBtn = document.getElementById('lang-confirm-ok');
  const cancelBtn = document.getElementById('lang-confirm-cancel');

  msgEl.textContent = t('regenConfirmMsg');
  okBtn.textContent = t('regenConfirmOk');
  cancelBtn.textContent = t('regenConfirmCancel');

  modal.classList.add('active');

  okBtn.onclick = () => {
    modal.classList.remove('active');
    generateBriefing();
  };
  cancelBtn.onclick = () => modal.classList.remove('active');
  modal.onclick = (e) => { if (e.target === modal) modal.classList.remove('active'); };
}

// ===== TAB NAVIGATION =====
function initTabs() {
  document.querySelectorAll('.nav-tab').forEach(tab => {
    tab.addEventListener('click', () => switchTab(tab.dataset.tab));
  });
  document.getElementById('btn-generate').addEventListener('click', generateBriefing);
  document.getElementById('btn-refresh-market').addEventListener('click', loadMarketData);
  document.getElementById('btn-save-portfolio').addEventListener('click', savePortfolio);
  document.getElementById('btn-add-allocation').addEventListener('click', addAllocationRow);

  // Currency Toggle Switch
  const currencyCheckbox = document.getElementById('currency-toggle-checkbox');
  const labels = document.querySelectorAll('.currency-label');
  labels[0].classList.add('active');

  currencyCheckbox.addEventListener('change', (e) => {
    if (e.target.checked) {
      currentCurrency = 'USD';
      labels[0].classList.remove('active');
      labels[1].classList.add('active');
    } else {
      currentCurrency = 'KRW';
      labels[1].classList.remove('active');
      labels[0].classList.add('active');
    }
    if (rawMarketData) {
      renderMarketCards(rawMarketData);
      renderTickerStrip(rawMarketData);
    }
  });
}

function switchTab(tabName) {
  currentTab = tabName;
  document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
  document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
  document.getElementById(`content-${tabName}`).classList.add('active');
  if (tabName === 'history') loadHistory();
  if (tabName === 'portfolio') loadPortfolio();
}

// ===== DASHBOARD =====
async function loadDashboard() {
  await Promise.all([loadMarketData(), loadLatestBriefing(), loadStats(), loadCalendar(), loadSectors()]);
}

// ===== SYSTEM STATS =====
async function loadStats() {
  try {
    const res = await fetch(API.stats);
    const json = await res.json();
    if (json.data) {
      document.getElementById('stat-today-visitors').textContent = json.data.todayVisitors.toLocaleString('en-US');
      document.getElementById('stat-total-visitors').textContent = json.data.totalVisitors.toLocaleString('en-US');
      document.getElementById('stat-today-api').textContent = json.data.todayApiCalls.toLocaleString('en-US');
      document.getElementById('stat-total-api').textContent = json.data.totalApiCalls.toLocaleString('en-US');
    }
  } catch (err) {
    console.error('Stats load failed:', err);
  }
}

// ===== MARKET DATA =====
async function loadMarketData() {
  try {
    const res = await fetch(API.marketSnapshot);
    const json = await res.json();
    if (json.data) {
      rawMarketData = json.data;
      renderMarketCards(rawMarketData);
      renderTickerStrip(rawMarketData);
      renderFearGreed(rawMarketData);
      const updEl = document.getElementById('market-updated');
      if (updEl) {
        const now = new Date();
        updEl.textContent = `기준 ${now.getHours().toString().padStart(2,'0')}:${now.getMinutes().toString().padStart(2,'0')}`;
      }
    }
  } catch (err) {
    console.error('Market data load failed:', err);
  }
}

function getDisplayData(data) {
  if (currentCurrency === 'USD') return data;
  const converted = JSON.parse(JSON.stringify(data));
  const exchangeRateInfo = data['USD/KRW'];
  const exchangeRate = exchangeRateInfo ? exchangeRateInfo.price : 1400;
  // 지수 포인트(S&P 500, NASDAQ, Dow Jones)는 통화 단위가 아니므로 환산 제외
  const usdAssets = ['Crude Oil (WTI)', 'Gold', 'BTC/USD'];
  for (const name of usdAssets) {
    if (converted[name] && converted[name].price != null) {
      converted[name].price = converted[name].price * exchangeRate;
      converted[name].change = converted[name].change * exchangeRate;
    }
  }
  return converted;
}

function _makeMarketCard(name, info) {
  const direction = info.change >= 0 ? 'up' : 'down';
  const price = info.price != null ? formatNumber(info.price, name) : 'N/A';
  const change = info.change != null ? `${info.change >= 0 ? '+' : ''}${info.change.toFixed(2)}` : '';
  const changePct = info.changePercent != null ? `(${info.changePercent >= 0 ? '+' : ''}${info.changePercent.toFixed(2)}%)` : '';
  const isFav = favorites.has(name);
  const card = document.createElement('div');
  card.className = `market-card ${direction}`;
  card.innerHTML = `
    <div class="card-label">${name}</div>
    <div class="card-price">${price}</div>
    <div class="card-change ${direction}">${change} ${changePct}</div>
    <div class="card-chart-hint">📈</div>
    <button class="card-star ${isFav ? 'active' : ''}" data-name="${name}"
      onclick="toggleFavorite('${name.replace(/'/g, "\\'")}', event)" title="즐겨찾기">${isFav ? '⭐' : '☆'}</button>
  `;
  card.addEventListener('click', () => openChartModal(name));
  return card;
}

function renderMarketCards(rawData) {
  const data = getDisplayData(rawData);
  const grid = document.getElementById('cards-grid');
  grid.innerHTML = '';
  for (const [name, info] of Object.entries(data)) {
    grid.appendChild(_makeMarketCard(name, info));
  }
  renderFavoritesRow();
}

function saveFavorites() {
  localStorage.setItem('mkt-favorites', JSON.stringify([...favorites]));
}

function toggleFavorite(name, e) {
  e.stopPropagation();
  if (favorites.has(name)) {
    favorites.delete(name);
  } else {
    favorites.add(name);
  }
  saveFavorites();
  // 별 버튼 상태 즉시 갱신
  document.querySelectorAll('.card-star').forEach(btn => {
    if (btn.dataset.name === name) {
      const isFav = favorites.has(name);
      btn.classList.toggle('active', isFav);
      btn.textContent = isFav ? '⭐' : '☆';
    }
  });
  renderFavoritesRow();
}

function renderFavoritesRow() {
  const favRow = document.getElementById('favorites-row');
  const favGrid = document.getElementById('favorites-grid');
  if (!favGrid || !rawMarketData) return;
  const favNames = [...favorites].filter(n => rawMarketData[n]);
  if (favNames.length === 0) {
    favRow.style.display = 'none';
    return;
  }
  favRow.style.display = '';
  const data = getDisplayData(rawMarketData);
  favGrid.innerHTML = '';
  for (const name of favNames) {
    const info = data[name];
    if (!info) continue;
    const card = _makeMarketCard(name, info);
    favGrid.appendChild(card);
    // 스파크라인 비동기 추가
    _attachSparkline(card, name);
  }
}

async function _attachSparkline(cardEl, name) {
  try {
    const res = await fetch(API.marketChart(name, '1d'));
    const json = await res.json();
    const candles = json.data?.candles;
    if (!candles || candles.length < 3) return;
    const sparkEl = document.createElement('div');
    sparkEl.className = 'card-sparkline';
    sparkEl.innerHTML = _buildSparklineSVG(candles);
    cardEl.appendChild(sparkEl);
  } catch (_) {}
}

function _buildSparklineSVG(candles) {
  const prices = candles.map(c => c.close);
  const min = Math.min(...prices), max = Math.max(...prices);
  const range = max - min || 1;
  const W = 110, H = 28;
  const pts = prices.map((p, i) => {
    const x = (i / (prices.length - 1)) * W;
    const y = H - ((p - min) / range) * (H - 2) - 1;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');
  const isUp = prices[prices.length - 1] >= prices[0];
  const color = isUp ? '#22c55e' : '#ef4444';
  return `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" preserveAspectRatio="none">
    <polyline points="${pts}" fill="none" stroke="${color}" stroke-width="1.5" stroke-linejoin="round" stroke-linecap="round"/>
  </svg>`;
}

function renderTickerStrip(rawData) {
  const data = getDisplayData(rawData);
  const strip = document.getElementById('ticker-strip');
  const items = [];
  for (const [name, info] of Object.entries(data)) {
    if (info.price == null) continue;
    const direction = info.change >= 0 ? 'up' : 'down';
    const arrow = info.change >= 0 ? '▲' : '▼';
    const changePct = info.changePercent != null ? `${info.changePercent >= 0 ? '+' : ''}${info.changePercent.toFixed(2)}%` : '';
    items.push(`
      <div class="ticker-item">
        <span class="ticker-name">${name}</span>
        <span class="ticker-price">${formatNumber(info.price, name)}</span>
        <span class="ticker-change ${direction}">${arrow} ${changePct}</span>
      </div>
    `);
  }
  const allItems = items.join('') + items.join('');
  strip.innerHTML = `<div class="ticker-scroll">${allItems}</div>`;
}

function formatNumber(num, name = '') {
  if (num == null) return 'N/A';
  const lowerName = name.toLowerCase();
  if (lowerName.includes('yield') || lowerName.includes('vix') || lowerName.includes('dxy') || lowerName.includes('eur/usd')) {
    return num.toFixed(2);
  }
  if (num >= 10000) {
    if (num >= 1000000) return Math.round(num).toLocaleString('en-US');
    return num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
  if (num >= 100) return num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return num.toFixed(2);
}

function startMarketRefresh() {
  if (marketRefreshInterval) clearInterval(marketRefreshInterval);
  marketRefreshInterval = setInterval(() => {
    if (currentTab === 'dashboard') loadMarketData();
  }, 60000);
}

// ===== BRIEFING =====
async function loadLatestBriefing() {
  try {
    const res = await fetch(API.briefingLatest);
    const json = await res.json();
    if (json.data) renderBriefing(json.data);
  } catch (err) {
    console.error('Briefing load failed:', err);
  }
}

let _currentBriefingId = null;

function renderBriefing(briefing) {
  _currentBriefingId = briefing.id || null;
  const content = document.getElementById('briefing-content');
  const meta = document.getElementById('briefing-meta');
  const html = parseBriefingContent(briefing.content);
  content.innerHTML = `<div class="briefing-rendered">${html}</div>`;

  const locale = t('metaDateLocale');
  const date = new Date(briefing.generatedAt);
  const dateStr = date.toLocaleDateString(locale, { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' });
  const timeStr = date.toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit' });
  const newsLabel = typeof t('metaNews') === 'function' ? t('metaNews')(briefing.newsCount || '?') : `📰 ${briefing.newsCount || '?'}`;

  meta.innerHTML = `
    <span class="meta-tag">📅 ${dateStr} ${timeStr}</span>
    <span class="meta-tag">🤖 ${briefing.model || 'AI'}</span>
    <span class="meta-tag">${newsLabel}</span>
    ${briefing.generationTimeMs ? `<span class="meta-tag">⚡ ${(briefing.generationTimeMs / 1000).toFixed(1)}s</span>` : ''}
    <button class="meta-share-btn" onclick="shareBriefing()" title="${t('shareBtn')}">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/>
        <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/>
      </svg>
      ${t('shareBtn')}
    </button>
  `;

  // 모바일 전용 한 줄 메타
  const mobileMeta = document.getElementById('briefing-meta-mobile');
  if (mobileMeta) {
    const shortDate = `${date.getMonth() + 1}월 ${date.getDate()}일`;
    const shortModel = (briefing.model || 'AI').replace('gemini-', 'G-').replace('gpt-', 'GPT-').split('-preview')[0];
    mobileMeta.innerHTML = `
      <span class="meta-pill">🧠 AI 브리핑</span>
      <span class="meta-pill">📅 ${shortDate}</span>
      <span class="meta-pill meta-pill-model" title="${briefing.model || 'AI'}">🤖 ${shortModel}</span>
      ${briefing.newsCount ? `<span class="meta-pill">📰 ${briefing.newsCount}건</span>` : ''}
      ${briefing.generationTimeMs ? `<span class="meta-pill">⚡ ${(briefing.generationTimeMs / 1000).toFixed(0)}s</span>` : ''}
      <button class="meta-pill-share" onclick="shareBriefing()">공유 ↗</button>
    `;
  }
}

async function shareBriefing() {
  if (!_currentBriefingId) return;
  const url = `${location.origin}${location.pathname}?briefing=${_currentBriefingId}`;
  const title = t('shareNative');
  if (navigator.share) {
    try {
      await navigator.share({ title, url });
      return;
    } catch { /* 취소 시 무시 */ }
  }
  try {
    await navigator.clipboard.writeText(url);
    showToast(t('shareCopied'), 'success');
  } catch {
    prompt(t('shareBtn'), url);
  }
}

function checkUrlBriefing() {
  const params = new URLSearchParams(location.search);
  const id = params.get('briefing');
  if (id) loadBriefingById(id);
}

function parseBriefingContent(text) {
  if (!text) return '';
  let html = text
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`(.+?)`/g, '<code>$1</code>')
    .replace(/^---$/gm, '<hr>')
    .replace(/^[-•] (.+)$/gm, '<li>$1</li>')
    .replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>')
    .replace(/\n\n/g, '</p><p>')
    .replace(/\n/g, '<br>');

  html = html.replace(/(<li>.+?<\/li>(\s*<br>)?)+/g, (match) => '<ul>' + match.replace(/<br>/g, '') + '</ul>');
  html = '<p>' + html + '</p>';
  html = html.replace(/<p>\s*<\/p>/g, '');
  html = html.replace(/<p>\s*(<h[123]>)/g, '$1');
  html = html.replace(/(<\/h[123]>)\s*<\/p>/g, '$1');
  html = html.replace(/<p>\s*(<ul>)/g, '$1');
  html = html.replace(/(<\/ul>)\s*<\/p>/g, '$1');
  html = html.replace(/<p>\s*<hr>\s*<\/p>/g, '<hr>');
  html = html.replace(/<p>\s*(<blockquote>)/g, '$1');
  html = html.replace(/(<\/blockquote>)\s*<\/p>/g, '$1');

  // PART 2 확률 바 (📈/📉/➡️ XX% 형식)
  html = html.replace(
    /(📈\s*(?:상승|Bullish|Hausse|上昇)\s*[:：]\s*)(\d+)%/gi,
    (_, label, pct) => `${label}<span class="prob-bar-wrap up"><span class="prob-bar-fill" style="width:${pct}%"></span></span><strong style="color:var(--green)">${pct}%</strong>`
  );
  html = html.replace(
    /(📉\s*(?:하락|Bearish|Baisse|下落)\s*[:：]\s*)(\d+)%/gi,
    (_, label, pct) => `${label}<span class="prob-bar-wrap down"><span class="prob-bar-fill" style="width:${pct}%"></span></span><strong style="color:var(--red)">${pct}%</strong>`
  );
  html = html.replace(
    /(➡️\s*(?:횡보|Neutral|Neutre|中立)\s*[:：]\s*)(\d+)%/gi,
    (_, label, pct) => `${label}<span class="prob-bar-wrap neutral"><span class="prob-bar-fill" style="width:${pct}%"></span></span><strong style="color:var(--text-secondary)">${pct}%</strong>`
  );

  // 섹션 아이콘 (언어 무관 키워드 + i18n 키워드)
  const sectionIcons = {
    'macro|매크로|宏观|マクロ': '🌍',
    'global|글로벌|全球|グローバル': '🌍',
    'direction|방향성|方向|方向性': '📈',
    'probability|확률|概率|確率': '📈',
    'sector|섹터|板块|セクター': '🏭',
    'leadership|리더십|领导|リーダーシップ': '🏭',
    'risk|리스크|风险|リスク': '⚠️',
    'trade|트레이드|交易|トレード': '💡',
    'dashboard|대시보드|仪表盘|ダッシュボード': '📊',
    'portfolio|포트폴리오|投资组合|ポートフォリオ': '💼',
  };
  for (const [keywords, icon] of Object.entries(sectionIcons)) {
    const regex = new RegExp(`(<h2>)(.*(?:${keywords}).*)(<\/h2>)`, 'gi');
    html = html.replace(regex, `$1${icon} $2$3`);
  }
  // ② 인아티클 광고: PART 3 제목 직전에 삽입
  const inArticleAd = `
    <div class="ad-slot ad-slot--in-article">
      <span class="ad-label">AD</span>
      <div class="ad-inner">
        <!-- Google AdSense: data-ad-client="ca-pub-XXXXXXXX" data-ad-slot="XXXXXXXX" 입력 후 주석 해제
        <ins class="adsbygoogle" style="display:block;text-align:center" data-ad-client="ca-pub-XXXXXXXX"
          data-ad-slot="XXXXXXXX" data-ad-layout="in-article" data-ad-format="fluid"></ins>
        <script>(adsbygoogle = window.adsbygoogle || []).push({});</script>
        -->
      </div>
    </div>`;
  // PART 3 또는 섹터/Sector 관련 h2 앞에 삽입 (다국어 대응)
  html = html.replace(
    /(<h2>[^<]*(?:PART 3|섹터|Sector|板块|セクター)[^<]*<\/h2>)/i,
    inArticleAd + '$1'
  );

  return html;
}

// ===== GENERATE BRIEFING =====
async function generateBriefing() {
  const btn = document.getElementById('btn-generate');
  const overlay = document.getElementById('loading-overlay');

  btn.disabled = true;
  btn.classList.add('loading');
  overlay.classList.add('active');

  document.querySelectorAll('.loading-step').forEach(s => s.classList.remove('active', 'done'));
  document.getElementById('step-1').classList.add('active');

  try {
    const url = new URL(API.briefingGenerate, window.location.origin);
    url.searchParams.append('currency', currentCurrency);
    url.searchParams.append('lang', currentLang);
    url.searchParams.append('client_id', getClientId());
    const eventSource = new EventSource(url.toString());
    let stepIndex = 1;

    const advanceStep = () => {
      if (stepIndex <= 4) {
        document.getElementById(`step-${stepIndex}`).classList.remove('active');
        document.getElementById(`step-${stepIndex}`).classList.add('done');
        stepIndex++;
        if (stepIndex <= 4) document.getElementById(`step-${stepIndex}`).classList.add('active');
      }
    };

    const stepTimers = [
      setTimeout(() => advanceStep(), 3000),
      setTimeout(() => advanceStep(), 7000),
      setTimeout(() => advanceStep(), 12000)
    ];

    eventSource.addEventListener('complete', (e) => {
      stepTimers.forEach(clearTimeout);
      const data = JSON.parse(e.data);
      eventSource.close();
      document.querySelectorAll('.loading-step').forEach(s => { s.classList.remove('active'); s.classList.add('done'); });
      setTimeout(() => {
        overlay.classList.remove('active');
        btn.disabled = false;
        btn.classList.remove('loading');
        if (data.briefing) {
          renderBriefing(data.briefing);
          showToast(t('toastBriefingOk'), 'success');
          switchTab('dashboard');
        }
      }, 800);
    });

    eventSource.addEventListener('error', (e) => {
      stepTimers.forEach(clearTimeout);
      let message = 'Unknown error';
      try { message = JSON.parse(e.data).message; } catch { /* noop */ }
      eventSource.close();
      overlay.classList.remove('active');
      btn.disabled = false;
      btn.classList.remove('loading');
      showToast(t('toastBriefingFail') + message, 'error');
    });

    eventSource.onerror = () => {
      stepTimers.forEach(clearTimeout);
      eventSource.close();
      overlay.classList.remove('active');
      btn.disabled = false;
      btn.classList.remove('loading');
      showToast(t('toastConnFail'), 'error');
    };
  } catch (err) {
    overlay.classList.remove('active');
    btn.disabled = false;
    btn.classList.remove('loading');
    showToast(`${t('toastBriefingFail')}${err.message}`, 'error');
  }
}

// ===== HISTORY =====
async function loadHistory() {
  try {
    const res = await fetch(API.briefingHistory);
    const json = await res.json();
    const list = document.getElementById('history-list');
    if (!json.data || json.data.length === 0) {
      list.innerHTML = `
        <div class="empty-state">
          <h3>${t('emptyHistoryTitle')}</h3>
          <p>${t('emptyHistoryDesc')}</p>
        </div>`;
      return;
    }
    const locale = t('metaDateLocale');
    list.innerHTML = json.data.map(item => {
      const date = new Date(item.generatedAt);
      const dateStr = date.toLocaleDateString(locale, { year: 'numeric', month: '2-digit', day: '2-digit' });
      const timeStr = date.toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit' });
      return `
        <div class="history-item" onclick="loadBriefingById('${item.id}')">
          <span class="history-date">${dateStr} ${timeStr}</span>
          <span class="history-preview">${item.preview || ''}</span>
          <span class="history-model">${item.model || '?'}</span>
        </div>`;
    }).join('');
  } catch (err) {
    console.error('History load failed:', err);
  }
}

async function loadBriefingById(id) {
  try {
    const res = await fetch(API.briefingById(id));
    const json = await res.json();
    if (json.data) {
      renderBriefing(json.data);
      switchTab('dashboard');
      showToast(t('toastBriefingLoaded'), 'info');
    }
  } catch (err) {
    showToast(t('toastBriefingLoadFail'), 'error');
  }
}

// ===== PORTFOLIO =====
async function loadPortfolio() {
  try {
    const res = await fetch(API.portfolio());
    const json = await res.json();
    if (json.data) populatePortfolioForm(json.data);
  } catch (err) {
    console.error('Portfolio load failed:', err);
  }
}

function populatePortfolioForm(portfolio) {
  document.getElementById('investment-style').value = portfolio.investmentStyle || 'Growth';
  document.getElementById('risk-tolerance').value = portfolio.riskTolerance || 'Medium-High';
  document.getElementById('total-assets').value = portfolio.totalAssets || '';
  document.getElementById('watchlist').value = (portfolio.watchlist || []).join(', ');
  const container = document.getElementById('allocations');
  container.innerHTML = '';
  (portfolio.allocations || []).forEach(alloc => addAllocationRow(null, alloc));
}

function addAllocationRow(e, data = null) {
  const container = document.getElementById('allocations');
  const row = document.createElement('div');
  row.className = 'allocation-row';
  row.innerHTML = `
    <input type="text" placeholder="${t('placeholderAllocName')}" value="${data?.name || ''}">
    <input type="number" min="0" max="100" step="5" placeholder="%" value="${data?.percentage || 0}">
    <span class="allocation-pct">%</span>
    <input type="text" placeholder="${t('placeholderAllocDetail')}" value="${data?.details || ''}" style="flex:2">
    <button class="btn-remove" onclick="this.parentElement.remove()">✕</button>
  `;
  container.appendChild(row);
}

async function savePortfolio() {
  const allocations = [];
  document.querySelectorAll('.allocation-row').forEach(row => {
    const inputs = row.querySelectorAll('input');
    const name = inputs[0].value.trim();
    const pct = parseInt(inputs[1].value) || 0;
    const details = inputs[2].value.trim();
    if (name) allocations.push({ name, percentage: pct, details });
  });
  const watchlistStr = document.getElementById('watchlist').value;
  const watchlist = watchlistStr ? watchlistStr.split(',').map(s => s.trim()).filter(Boolean) : [];
  const portfolio = {
    allocations,
    investmentStyle: document.getElementById('investment-style').value,
    riskTolerance: document.getElementById('risk-tolerance').value,
    totalAssets: document.getElementById('total-assets').value,
    watchlist
  };
  try {
    const res = await fetch(API.portfolio(), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(portfolio)
    });
    const json = await res.json();
    showToast(json.message || t('toastPortfolioOk'), 'success');
  } catch (err) {
    showToast(t('toastSaveFail'), 'error');
  }
}

// ===== CHART MODAL =====
async function openChartModal(name) {
  currentChartName = name;
  currentChartPeriod = '1d';
  document.getElementById('chart-modal-title').textContent = name;
  document.getElementById('chart-modal').classList.add('active');

  // 기간 탭 초기화
  document.querySelectorAll('.period-tab').forEach(t => t.classList.remove('active'));
  document.querySelector('.period-tab[data-period="1d"]').classList.add('active');

  // 기간 탭 이벤트 (중복 등록 방지)
  document.querySelectorAll('.period-tab').forEach(tab => {
    tab.onclick = async () => {
      document.querySelectorAll('.period-tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      currentChartPeriod = tab.dataset.period;
      await loadChart(name, currentChartPeriod);
    };
  });

  await loadChart(name, '1d');
}

function closeChartModal() {
  document.getElementById('chart-modal').classList.remove('active');
  if (chartInstance) {
    chartInstance.remove();
    chartInstance = null;
  }
}

function handleChartModalClick(e) {
  if (e.target === document.getElementById('chart-modal')) closeChartModal();
}

async function loadChart(name, period) {
  const container = document.getElementById('chart-container');
  container.innerHTML = `<div class="chart-loading">${t('chartLoading')}</div>`;

  if (chartInstance) {
    chartInstance.remove();
    chartInstance = null;
  }

  try {
    const res = await fetch(API.marketChart(name, period));
    const json = await res.json();

    if (!json.data || !json.data.candles || json.data.candles.length === 0) {
      container.innerHTML = `<div class="chart-empty">${t('chartNoData')}</div>`;
      return;
    }

    container.innerHTML = '';

    if (typeof LightweightCharts === 'undefined') {
      container.innerHTML = `<div class="chart-empty">차트 라이브러리 로드 실패. 페이지를 새로고침해 주세요.</div>`;
      return;
    }

    chartInstance = LightweightCharts.createChart(container, {
      autoSize: true,
      height: 320,
      layout: {
        background: { color: '#111827' },
        textColor: '#94a3b8',
        fontSize: 12,
      },
      grid: {
        vertLines: { color: 'rgba(99, 102, 241, 0.08)' },
        horzLines: { color: 'rgba(99, 102, 241, 0.08)' },
      },
      crosshair: { mode: 1 },
      rightPriceScale: { borderColor: 'rgba(99, 102, 241, 0.2)' },
      timeScale: {
        borderColor: 'rgba(99, 102, 241, 0.2)',
        timeVisible: period !== '1mo',
        secondsVisible: false,
      },
    });

    const candles = json.data.candles;

    if (period === '1d') {
      const series = chartInstance.addCandlestickSeries({
        upColor: '#10b981',
        downColor: '#ef4444',
        borderUpColor: '#10b981',
        borderDownColor: '#ef4444',
        wickUpColor: '#10b981',
        wickDownColor: '#ef4444',
      });
      series.setData(candles);
    } else {
      const series = chartInstance.addAreaSeries({
        lineColor: '#6366f1',
        topColor: 'rgba(99, 102, 241, 0.25)',
        bottomColor: 'rgba(99, 102, 241, 0)',
        lineWidth: 2,
        crosshairMarkerVisible: true,
        crosshairMarkerRadius: 4,
      });
      series.setData(candles.map(c => ({ time: c.time, value: c.close })));
    }

    chartInstance.timeScale().fitContent();

  } catch (err) {
    container.innerHTML = `<div class="chart-empty">${t('chartError')}: ${err.message}</div>`;
  }
}

// ===== TOAST NOTIFICATION =====
function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  const icons = { success: '✅', error: '❌', info: 'ℹ️' };
  toast.innerHTML = `<span>${icons[type] || ''}</span> ${message}`;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}

// ===== SECTOR ETF =====
async function loadSectors() {
  const section = document.getElementById('sector-section');
  const grid    = document.getElementById('sector-grid');
  if (!section || !grid) return;
  try {
    const res  = await fetch(API.sectors);
    const json = await res.json();
    if (!json.data || !Object.keys(json.data).length) return;
    section.style.display = '';
    const sorted = Object.entries(json.data).sort((a, b) => b[1].changePercent - a[1].changePercent);
    grid.innerHTML = sorted.map(([name, info]) => {
      const pct = info.changePercent;
      const dir = pct >= 0 ? 'up' : 'down';
      const sign = pct >= 0 ? '+' : '';
      return `<div class="sector-chip ${dir}">
        <span class="sector-sym">${info.symbol}</span>
        <span class="sector-name">${name}</span>
        <span class="sector-pct">${sign}${pct.toFixed(2)}%</span>
      </div>`;
    }).join('');
  } catch (err) {
    console.error('Sector load failed:', err);
  }
}

// ===== FEAR & GREED INDEX =====
function renderFearGreed(data) {
  const section = document.getElementById('fg-section');
  const svgEl   = document.getElementById('fg-svg');
  if (!section || !svgEl || !data) return;

  const fg = _computeFearGreed(data);
  if (!fg) return;

  section.style.display = '';
  svgEl.innerHTML = _buildGaugeSVG(fg.score, fg.color);

  document.getElementById('fg-score-num').textContent   = fg.score;
  document.getElementById('fg-score-num').style.color   = fg.color;
  document.getElementById('fg-score-label').textContent = fg.label;
  document.getElementById('fg-score-label').style.color = fg.color;

  const badge = document.getElementById('fg-badge');
  badge.textContent = fg.label;
  badge.style.color       = fg.color;
  badge.style.background  = fg.color + '18';
  badge.style.borderColor = fg.color + '50';

  document.getElementById('fg-components').innerHTML =
    `<div class="fg-comp-row">
      <span class="fg-comp-label">VIX</span>
      <div class="fg-comp-bar"><div style="width:${fg.vixScore}%;background:${fg.color}"></div></div>
      <span class="fg-comp-val">${fg.vixScore}</span>
    </div>
    <div class="fg-comp-row">
      <span class="fg-comp-label">S&P 모멘텀</span>
      <div class="fg-comp-bar"><div style="width:${fg.spScore}%;background:${fg.color}"></div></div>
      <span class="fg-comp-val">${fg.spScore}</span>
    </div>
    <div class="fg-comp-row">
      <span class="fg-comp-label">금 안전자산</span>
      <div class="fg-comp-bar"><div style="width:${fg.goldScore}%;background:${fg.color}"></div></div>
      <span class="fg-comp-val">${fg.goldScore}</span>
    </div>`;
}

function _computeFearGreed(data) {
  const vix       = data['VIX']?.price;
  const spChange  = data['S&P 500']?.changePercent;
  const goldChange = data['Gold']?.changePercent;
  if (vix == null || spChange == null) return null;

  // VIX component (40%): VIX 10→100점, VIX 40→0점
  const vixScore  = Math.round(Math.max(0, Math.min(100, (40 - vix) / 30 * 100)));
  // S&P 하루 모멘텀 (35%): -3%→0점, +3%→100점
  const spScore   = Math.round(Math.max(0, Math.min(100, (spChange + 3) / 6 * 100)));
  // 금 안전자산 수요 (25%): 금↑ + SP↓ = 공포 → 낮은 점수
  const div       = goldChange != null ? goldChange - spChange : 0;
  const goldScore = Math.round(Math.max(0, Math.min(100, 50 - div * 8)));

  const score = Math.round(0.40 * vixScore + 0.35 * spScore + 0.25 * goldScore);

  const zones = [
    { max: 20,  label: '극도의 공포', color: '#ef4444' },
    { max: 40,  label: '공포',        color: '#f97316' },
    { max: 60,  label: '중립',        color: '#eab308' },
    { max: 80,  label: '탐욕',        color: '#84cc16' },
    { max: 100, label: '극도의 탐욕', color: '#22c55e' },
  ];
  const zone = zones.find(z => score <= z.max) || zones[4];
  return { score, label: zone.label, color: zone.color, vixScore, spScore, goldScore };
}

function _buildGaugeSVG(score, activeColor) {
  const cx = 100, cy = 100, r = 74, sw = 14;
  const toRad = d => d * Math.PI / 180;
  const pt = (s, rad = r) => ({
    x: cx + rad * Math.cos(toRad(180 - s * 1.8)),
    y: cy - rad * Math.sin(toRad(180 - s * 1.8)),
  });

  const zoneColors = ['#ef4444', '#f97316', '#eab308', '#84cc16', '#22c55e'];
  let html = '';

  // 배경 5구간 아크
  for (let i = 0; i < 5; i++) {
    const s1 = i * 20 + 1.2, s2 = (i + 1) * 20 - 1.2;
    const p1 = pt(s1), p2 = pt(s2);
    html += `<path d="M${p1.x.toFixed(2)},${p1.y.toFixed(2)} A${r},${r} 0 0,0 ${p2.x.toFixed(2)},${p2.y.toFixed(2)}" `
          + `stroke="${zoneColors[i]}" stroke-width="${sw}" fill="none" stroke-linecap="round" opacity="0.32"/>`;
  }

  // 현재 점수까지 밝게 강조 (0 ~ score)
  if (score >= 2) {
    const p0 = pt(0.5), pS = pt(Math.min(score, 99.5));
    const large = score > 50 ? 1 : 0;
    html += `<path d="M${p0.x.toFixed(2)},${p0.y.toFixed(2)} A${r},${r} 0 ${large},0 ${pS.x.toFixed(2)},${pS.y.toFixed(2)}" `
          + `stroke="${activeColor}" stroke-width="${sw - 6}" fill="none" stroke-linecap="round" opacity="0.55"/>`;
  }

  // 바늘
  const np = pt(score, r - sw / 2 - 1);
  html += `<line x1="${cx}" y1="${cy}" x2="${np.x.toFixed(2)}" y2="${np.y.toFixed(2)}" `
        + `stroke="white" stroke-width="2.5" stroke-linecap="round"/>`;
  html += `<circle cx="${cx}" cy="${cy}" r="4" fill="white"/>`;

  // 점수 텍스트 (중앙 아래)
  html += `<text x="${cx}" y="${cy + 22}" text-anchor="middle" fill="white" `
        + `font-size="20" font-weight="700" font-family="Inter,sans-serif">${score}</text>`;

  // FEAR / GREED 레이블
  const lp = pt(1); const rp = pt(99);
  html += `<text x="${(lp.x - 2).toFixed(0)}" y="${cy + 15}" text-anchor="middle" `
        + `fill="#ef4444" font-size="8.5" font-family="Inter,sans-serif">FEAR</text>`;
  html += `<text x="${(rp.x + 2).toFixed(0)}" y="${cy + 15}" text-anchor="middle" `
        + `fill="#22c55e" font-size="8.5" font-family="Inter,sans-serif">GREED</text>`;

  return html;
}

// ===== CALENDAR =====
async function loadCalendar() {
  const grid = document.getElementById('calendar-grid');
  if (!grid) return;
  try {
    const res = await fetch(API.calendar);
    const json = await res.json();
    if (!json.data) { grid.innerHTML = ''; return; }
    const { economic = [], earnings = [] } = json.data;
    if (!economic.length && !earnings.length) {
      grid.innerHTML = '<div class="calendar-empty">예정된 주요 일정이 없습니다.</div>';
      return;
    }
    grid.innerHTML = _renderCalendar(economic, earnings);
  } catch (err) {
    console.error('Calendar load failed:', err);
    grid.innerHTML = '';
  }
}

function _renderCalendar(economic, earnings) {
  const impactIcon = { high: '🔴', medium: '🟡', low: '⚪' };
  const hourLabel = { bmo: '장전', amc: '장후', dmh: '장중' };

  // 날짜별 그룹핑
  const byDate = {};
  const addToDate = (date, type, item) => {
    if (!byDate[date]) byDate[date] = { economic: [], earnings: [] };
    byDate[date][type].push(item);
  };

  economic.forEach(ev => {
    const date = (ev.time || '').substring(0, 10) || '미정';
    addToDate(date, 'economic', ev);
  });
  earnings.forEach(ev => {
    addToDate(ev.date || '미정', 'earnings', ev);
  });

  const today = new Date().toISOString().substring(0, 10);
  const sortedDates = Object.keys(byDate).sort();

  let html = '<div class="cal-columns">';
  for (const date of sortedDates) {
    const isToday = date === today;
    const dayLabel = _calDayLabel(date);
    html += `<div class="cal-day${isToday ? ' cal-day--today' : ''}">`;
    html += `<div class="cal-day-header">${isToday ? '🔔 ' : ''}${dayLabel}</div>`;

    // 경제지표
    for (const ev of byDate[date].economic) {
      const icon = impactIcon[ev.impact] || '⚪';
      const time = (ev.time || '').substring(11, 16) || '';
      const est = ev.estimate != null ? ` <span class="cal-est">예상: ${ev.estimate}${ev.unit || ''}</span>` : '';
      const prev = ev.prev != null ? ` <span class="cal-prev">이전: ${ev.prev}${ev.unit || ''}</span>` : '';
      html += `<div class="cal-item cal-item--eco">
        <span class="cal-icon">${icon}</span>
        <div class="cal-item-body">
          <span class="cal-name">${ev.country} · ${ev.event}</span>
          <span class="cal-detail">${time}${est}${prev}</span>
        </div>
      </div>`;
    }

    // 어닝
    for (const ev of byDate[date].earnings) {
      const badge = ev.isMajor ? '<span class="cal-major">★</span>' : '';
      const when = hourLabel[ev.hour] || ev.hour || '';
      const eps = ev.epsEstimate != null ? ` <span class="cal-est">EPS 예상: $${ev.epsEstimate}</span>` : '';
      html += `<div class="cal-item cal-item--earn${ev.isMajor ? ' cal-item--major' : ''}">
        <span class="cal-icon">🏢</span>
        <div class="cal-item-body">
          <span class="cal-name">${badge}${ev.symbol} <span class="cal-co">${ev.company}</span></span>
          <span class="cal-detail">${when}${eps}</span>
        </div>
      </div>`;
    }

    html += '</div>';
  }
  html += '</div>';
  return html;
}

function _calDayLabel(dateStr) {
  if (!dateStr || dateStr === '미정') return '미정';
  const d = new Date(dateStr + 'T00:00:00');
  const today = new Date(); today.setHours(0,0,0,0);
  const diff = Math.round((d - today) / 86400000);
  const weekdays = ['일','월','화','수','목','금','토'];
  const wd = weekdays[d.getDay()];
  const mmdd = `${d.getMonth()+1}/${d.getDate()}`;
  if (diff === 0) return `오늘 (${mmdd} ${wd})`;
  if (diff === 1) return `내일 (${mmdd} ${wd})`;
  return `${mmdd} (${wd})`;
}
