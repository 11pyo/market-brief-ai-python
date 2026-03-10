// ===== AI 모닝 마켓 브리핑 - Frontend App =====

const API = {
  briefingLatest: '/api/briefing/latest',
  briefingHistory: '/api/briefing/history',
  briefingById: (id) => `/api/briefing/${id}`,
  briefingGenerate: '/api/briefing/generate/stream',
  marketSnapshot: '/api/market/snapshot',
  portfolio: '/api/portfolio',
  settings: '/api/settings',
  status: '/api/status',
  stats: '/api/stats'
};

// ===== STATE =====
let currentTab = 'dashboard';
let marketRefreshInterval = null;
let currentCurrency = 'KRW';
let rawMarketData = null;

// ===== INITIALIZATION =====
document.addEventListener('DOMContentLoaded', () => {
  initTabs();
  loadDashboard();
  startMarketRefresh();
});

// ===== TAB NAVIGATION =====
function initTabs() {
  document.querySelectorAll('.nav-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      const tabName = tab.dataset.tab;
      switchTab(tabName);
    });
  });
  document.getElementById('btn-generate').addEventListener('click', generateBriefing);
  document.getElementById('btn-refresh-market').addEventListener('click', loadMarketData);
  document.getElementById('btn-save-portfolio').addEventListener('click', savePortfolio);
  document.getElementById('btn-add-allocation').addEventListener('click', addAllocationRow);

  // Currency Toggle Switch
  const currencyCheckbox = document.getElementById('currency-toggle-checkbox');
  const labels = document.querySelectorAll('.currency-label');
  
  // Set initial state
  labels[0].classList.add('active'); // KRW

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
    
    // Instantly re-render market data with new currency if we have data
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
  await Promise.all([
    loadMarketData(),
    loadLatestBriefing(),
    loadStats()
  ]);
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
    console.error('통계 데이터 로드 실패:', err);
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
    }
  } catch (err) {
    console.error('시장 데이터 로드 실패:', err);
  }
}

function getDisplayData(data) {
  // If viewing in USD, show raw data safely
  if (currentCurrency === 'USD') return data;

  // We want to convert to KRW
  const converted = JSON.parse(JSON.stringify(data));
  const exchangeRateInfo = data['USD/KRW'];
  const exchangeRate = exchangeRateInfo ? exchangeRateInfo.price : 1400; // default generic fallback

  const usdAssets = ['S&P 500', 'NASDAQ', 'Dow Jones', 'Crude Oil (WTI)', 'Gold', 'BTC/USD'];

  for (const name of usdAssets) {
    if (converted[name] && converted[name].price != null) {
      converted[name].price = converted[name].price * exchangeRate;
      converted[name].change = converted[name].change * exchangeRate;
    }
  }

  return converted;
}

function renderMarketCards(rawData) {
  const data = getDisplayData(rawData);
  const grid = document.getElementById('cards-grid');
  grid.innerHTML = '';

  for (const [name, info] of Object.entries(data)) {
    const card = document.createElement('div');
    const direction = info.change >= 0 ? 'up' : 'down';
    card.className = `market-card ${direction}`;

    const price = info.price != null
      ? formatNumber(info.price, name)
      : 'N/A';
    const change = info.change != null
      ? `${info.change >= 0 ? '+' : ''}${info.change.toFixed(2)}`
      : '';
    const changePct = info.changePercent != null
      ? `(${info.changePercent >= 0 ? '+' : ''}${info.changePercent.toFixed(2)}%)`
      : '';

    card.innerHTML = `
      <div class="card-label">${name}</div>
      <div class="card-price">${price}</div>
      <div class="card-change ${direction}">${change} ${changePct}</div>
    `;
    grid.appendChild(card);
  }
}

function renderTickerStrip(rawData) {
  const data = getDisplayData(rawData);
  const strip = document.getElementById('ticker-strip');
  const items = [];

  for (const [name, info] of Object.entries(data)) {
    if (info.price == null) continue;
    const direction = info.change >= 0 ? 'up' : 'down';
    const arrow = info.change >= 0 ? '▲' : '▼';
    const changePct = info.changePercent != null
      ? `${info.changePercent >= 0 ? '+' : ''}${info.changePercent.toFixed(2)}%`
      : '';
    items.push(`
      <div class="ticker-item">
        <span class="ticker-name">${name}</span>
        <span class="ticker-price">${formatNumber(info.price, name)}</span>
        <span class="ticker-change ${direction}">${arrow} ${changePct}</span>
      </div>
    `);
  }

  // Duplicate for seamless scrolling
  const allItems = items.join('') + items.join('');
  strip.innerHTML = `<div class="ticker-scroll">${allItems}</div>`;
}

function formatNumber(num, name = '') {
  if (num == null) return 'N/A';
  const lowerName = name.toLowerCase();

  // Special percentages
  if (lowerName.includes('yield') || lowerName.includes('vix') || lowerName.includes('dxy') || lowerName.includes('eur/usd')) {
    return num.toFixed(2);
  }

  // Format based on value size
  if (num >= 10000) {
    // If it's a huge number (like KRW converted BTC which is ~100M+), we don't need decimal
    if (num >= 1000000) return Math.round(num).toLocaleString('en-US');
    return num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
  if (num >= 100) {
    return num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
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
    if (json.data) {
      renderBriefing(json.data);
    }
  } catch (err) {
    console.error('브리핑 로드 실패:', err);
  }
}

function renderBriefing(briefing) {
  const content = document.getElementById('briefing-content');
  const meta = document.getElementById('briefing-meta');

  // Parse markdown-like content to HTML
  const html = parseBriefingContent(briefing.content);
  content.innerHTML = `<div class="briefing-rendered">${html}</div>`;

  // Meta info
  const date = new Date(briefing.generatedAt);
  const dateStr = date.toLocaleDateString('ko-KR', {
    year: 'numeric', month: 'long', day: 'numeric',
    weekday: 'long'
  });
  const timeStr = date.toLocaleTimeString('ko-KR', {
    hour: '2-digit', minute: '2-digit'
  });

  meta.innerHTML = `
    <span class="meta-tag">📅 ${dateStr} ${timeStr}</span>
    <span class="meta-tag">🤖 ${briefing.model || 'GPT-4o'}</span>
    <span class="meta-tag">📰 뉴스 ${briefing.newsCount || '?'}건 분석</span>
    ${briefing.generationTimeMs ? `<span class="meta-tag">⚡ ${(briefing.generationTimeMs / 1000).toFixed(1)}s</span>` : ''}
  `;
}

function parseBriefingContent(text) {
  if (!text) return '';

  // Simple markdown parser
  let html = text
    // Headers
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    // Bold
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    // Italic
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    // Code inline
    .replace(/`(.+?)`/g, '<code>$1</code>')
    // Horizontal rule
    .replace(/^---$/gm, '<hr>')
    // Unordered list
    .replace(/^[-•] (.+)$/gm, '<li>$1</li>')
    // Blockquote
    .replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>')
    // Line breaks
    .replace(/\n\n/g, '</p><p>')
    .replace(/\n/g, '<br>');

  // Wrap lists
  html = html.replace(/(<li>.+?<\/li>(\s*<br>)?)+/g, (match) => {
    return '<ul>' + match.replace(/<br>/g, '') + '</ul>';
  });

  // Wrap in paragraph
  html = '<p>' + html + '</p>';

  // Clean up empty paragraphs
  html = html.replace(/<p>\s*<\/p>/g, '');
  html = html.replace(/<p>\s*(<h[123]>)/g, '$1');
  html = html.replace(/(<\/h[123]>)\s*<\/p>/g, '$1');
  html = html.replace(/<p>\s*(<ul>)/g, '$1');
  html = html.replace(/(<\/ul>)\s*<\/p>/g, '$1');
  html = html.replace(/<p>\s*<hr>\s*<\/p>/g, '<hr>');
  html = html.replace(/<p>\s*(<blockquote>)/g, '$1');
  html = html.replace(/(<\/blockquote>)\s*<\/p>/g, '$1');

  // Highlight probability bars
  html = html.replace(
    /상승\s*\(?\s*Bullish\s*\)?\s*확률\s*[:：]\s*(\d+)%/gi,
    (match, pct) => {
      return `<strong style="color:var(--green)">상승(Bullish) 확률: ${pct}%</strong>`;
    }
  );
  html = html.replace(
    /하락\s*\(?\s*Bearish\s*\)?\s*확률\s*[:：]\s*(\d+)%/gi,
    (match, pct) => {
      return `<strong style="color:var(--red)">하락(Bearish) 확률: ${pct}%</strong>`;
    }
  );

  // Detect section headers and add section markers
  const sectionIcons = {
    '매크로': '🌍',
    '글로벌': '🌍',
    '방향성': '📈',
    '확률': '📈',
    '섹터': '🏭',
    '리더십': '🏭',
    '리스크': '⚠️',
    '트레이드': '💡',
    '대시보드': '📊',
    '포트폴리오': '💼',
    '전문가': '🎙️',
    '패널': '🎙️'
  };

  for (const [keyword, icon] of Object.entries(sectionIcons)) {
    const regex = new RegExp(`(<h2>)(.*${keyword}.*)(<\/h2>)`, 'gi');
    html = html.replace(regex, `$1${icon} $2$3`);
  }

  return html;
}

// ===== GENERATE BRIEFING =====
async function generateBriefing() {
  const btn = document.getElementById('btn-generate');
  const overlay = document.getElementById('loading-overlay');

  btn.disabled = true;
  btn.classList.add('loading');
  overlay.classList.add('active');

  // Reset loading steps
  document.querySelectorAll('.loading-step').forEach(s => {
    s.classList.remove('active', 'done');
  });
  document.getElementById('step-1').classList.add('active');

  try {
    const url = new URL(API.briefingGenerate, window.location.origin);
    url.searchParams.append('currency', currentCurrency);
    const eventSource = new EventSource(url.toString());
    let stepIndex = 1;

    const advanceStep = () => {
      if (stepIndex <= 4) {
        document.getElementById(`step-${stepIndex}`).classList.remove('active');
        document.getElementById(`step-${stepIndex}`).classList.add('done');
        stepIndex++;
        if (stepIndex <= 4) {
          document.getElementById(`step-${stepIndex}`).classList.add('active');
        }
      }
    };

    // Auto-advance steps based on time
    const stepTimers = [
      setTimeout(() => advanceStep(), 3000),
      setTimeout(() => advanceStep(), 7000),
      setTimeout(() => advanceStep(), 12000)
    ];

    eventSource.addEventListener('complete', (e) => {
      stepTimers.forEach(clearTimeout);
      const data = JSON.parse(e.data);
      eventSource.close();

      // Mark all steps done
      document.querySelectorAll('.loading-step').forEach(s => {
        s.classList.remove('active');
        s.classList.add('done');
      });

      setTimeout(() => {
        overlay.classList.remove('active');
        btn.disabled = false;
        btn.classList.remove('loading');

        if (data.briefing) {
          renderBriefing(data.briefing);
          showToast('브리핑이 성공적으로 생성되었습니다!', 'success');
          switchTab('dashboard');
        }
      }, 800);
    });

    eventSource.addEventListener('error', (e) => {
      stepTimers.forEach(clearTimeout);
      let message = 'Unknown error';
      try {
        const data = JSON.parse(e.data);
        message = data.message;
      } catch { /* noop */ }
      eventSource.close();
      overlay.classList.remove('active');
      btn.disabled = false;
      btn.classList.remove('loading');
      showToast(`브리핑 생성 실패: ${message}`, 'error');
    });

    eventSource.onerror = () => {
      stepTimers.forEach(clearTimeout);
      eventSource.close();
      overlay.classList.remove('active');
      btn.disabled = false;
      btn.classList.remove('loading');
      showToast('서버 연결 실패. 다시 시도해 주세요.', 'error');
    };
  } catch (err) {
    overlay.classList.remove('active');
    btn.disabled = false;
    btn.classList.remove('loading');
    showToast(`오류: ${err.message}`, 'error');
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
          <h3>아직 저장된 브리핑이 없습니다</h3>
          <p>브리핑을 생성하면 자동으로 이곳에 기록됩니다.</p>
        </div>
      `;
      return;
    }

    list.innerHTML = json.data.map(item => {
      const date = new Date(item.generatedAt);
      const dateStr = date.toLocaleDateString('ko-KR', {
        year: 'numeric', month: '2-digit', day: '2-digit'
      });
      const timeStr = date.toLocaleTimeString('ko-KR', {
        hour: '2-digit', minute: '2-digit'
      });
      return `
        <div class="history-item" onclick="loadBriefingById('${item.id}')">
          <span class="history-date">${dateStr} ${timeStr}</span>
          <span class="history-preview">${item.preview || ''}</span>
          <span class="history-model">${item.model || '?'}</span>
        </div>
      `;
    }).join('');
  } catch (err) {
    console.error('히스토리 로드 실패:', err);
  }
}

async function loadBriefingById(id) {
  try {
    const res = await fetch(API.briefingById(id));
    const json = await res.json();
    if (json.data) {
      renderBriefing(json.data);
      switchTab('dashboard');
      showToast('이전 브리핑을 불러왔습니다.', 'info');
    }
  } catch (err) {
    showToast('브리핑 로드 실패', 'error');
  }
}

// ===== PORTFOLIO =====
async function loadPortfolio() {
  try {
    const res = await fetch(API.portfolio);
    const json = await res.json();
    if (json.data) {
      populatePortfolioForm(json.data);
    }
  } catch (err) {
    console.error('포트폴리오 로드 실패:', err);
  }
}

function populatePortfolioForm(portfolio) {
  document.getElementById('investment-style').value = portfolio.investmentStyle || 'Growth';
  document.getElementById('risk-tolerance').value = portfolio.riskTolerance || 'Medium-High';
  document.getElementById('total-assets').value = portfolio.totalAssets || '';
  document.getElementById('watchlist').value = (portfolio.watchlist || []).join(', ');

  const container = document.getElementById('allocations');
  container.innerHTML = '';

  (portfolio.allocations || []).forEach(alloc => {
    addAllocationRow(null, alloc);
  });
}

function addAllocationRow(e, data = null) {
  const container = document.getElementById('allocations');
  const row = document.createElement('div');
  row.className = 'allocation-row';
  row.innerHTML = `
    <input type="text" placeholder="자산명 (예: 주식, 테크)" value="${data?.name || ''}">
    <input type="number" min="0" max="100" step="5" placeholder="%" value="${data?.percentage || 0}">
    <span class="allocation-pct">%</span>
    <input type="text" placeholder="상세 (예: 미국 대형주)" value="${data?.details || ''}" style="flex:2">
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
    if (name) {
      allocations.push({ name, percentage: pct, details });
    }
  });

  const watchlistStr = document.getElementById('watchlist').value;
  const watchlist = watchlistStr
    ? watchlistStr.split(',').map(s => s.trim()).filter(Boolean)
    : [];

  const portfolio = {
    allocations,
    investmentStyle: document.getElementById('investment-style').value,
    riskTolerance: document.getElementById('risk-tolerance').value,
    totalAssets: document.getElementById('total-assets').value,
    watchlist
  };

  try {
    const res = await fetch(API.portfolio, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(portfolio)
    });
    const json = await res.json();
    showToast(json.message || '포트폴리오가 저장되었습니다.', 'success');
  } catch (err) {
    showToast('저장 실패', 'error');
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
