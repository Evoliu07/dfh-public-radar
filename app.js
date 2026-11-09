const $ = (id) => document.getElementById(id);
const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (ch) => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
}[ch]));

const fmt = (value, digits = 2) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '—';
  return Number(value).toFixed(digits);
};
const signed = (value, digits = 2) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '—';
  const n = Number(value);
  return `${n > 0 ? '+' : ''}${n.toFixed(digits)}%`;
};
const trendClass = (value) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return 'flat';
  return Number(value) > 0 ? 'up' : Number(value) < 0 ? 'down' : 'flat';
};
const shortDate = (value) => {
  const text = String(value || '');
  const match = text.match(/^\d{4}-(\d{2})-(\d{2})$/);
  return match ? `${match[1]}/${match[2]}` : text || '—';
};
const safeUrl = (value) => /^https?:\/\//i.test(String(value || '')) ? value : '';

function renderMeta(data) {
  $('updated').textContent = data.meta?.updated_at || '—';
  $('data-date').textContent = data.meta?.data_date || '—';
  $('disclaimer').textContent = data.meta?.disclaimer || '';
  $('sources').textContent = (data.meta?.sources || []).join(' · ');
  const warnings = data.meta?.warnings || [];
  if (warnings.length) {
    const box = $('warning');
    box.style.display = 'block';
    box.textContent = `部分公开数据源暂不可用，已保留上次结果：${warnings.slice(0, 2).join('；')}`;
  }
}

function renderHero(data) {
  const yields = data.market?.yields || [];
  const indices = data.market?.indices || [];
  const y10 = yields.find((x) => x.label.includes('10Y'));
  const y30 = yields.find((x) => x.label.includes('30Y'));
  const csi = indices.find((x) => x.label.includes('沪深300'));
  const hstech = indices.find((x) => x.label.includes('恒生科技'));
  const cards = [
    y10 ? { value: `${fmt(y10.value)}%`, label: '10Y 国债', delta: `${signed(y10.change_bp, 1)}bp`, className: trendClass(-y10.change_bp) } : null,
    y30 ? { value: `${fmt(y30.value)}%`, label: '30Y 国债', delta: `${signed(y30.change_bp, 1)}bp`, className: trendClass(-y30.change_bp) } : null,
    csi ? { value: fmt(csi.value), label: '沪深300', delta: signed(csi.change), className: trendClass(csi.change) } : null,
    hstech ? { value: fmt(hstech.value), label: '恒生科技', delta: signed(hstech.change), className: trendClass(hstech.change) } : null,
  ].filter(Boolean);
  $('hero-side').innerHTML = cards.map((card) => `
    <div class="mini-stat">
      <b>${esc(card.value)}</b>
      <span>${esc(card.label)}</span>
      <div class="delta ${card.className}">${esc(card.delta)}</div>
    </div>`).join('');
}

function renderProducts(data) {
  const wrap = $('products');
  const products = data.products || [];
  if (!products.length) {
    wrap.innerHTML = '<p class="note">产品数据暂不可用。</p>';
    return;
  }
  wrap.innerHTML = products.map((p) => {
    const isYixin = p.id === 'yixin';
    const nav = p.nav;
    const returns = p.returns || {};
    const navBox = nav ? `
      <div class="nav-box">
        <div><b>${fmt(nav.value, 4)}</b><small>${esc(nav.class)} 类 · ${esc(nav.date)}</small></div>
        <div class="delta ${trendClass(nav.daily)}">${signed(nav.daily)}<br><small>日涨跌</small></div>
      </div>` : `
      <div class="nav-box">
        <div><b>发行期</b><small>暂无历史净值</small></div>
        <div class="delta">${esc(p.status_note?.match(/11-09.*11-25/)?.[0] || '以公告为准')}</div>
      </div>`;
    const facts = [
      ['产品类型', p.type],
      ['基金经理', p.manager],
      ['成立日期', p.inception],
      ['股票仓位', p.equity_range],
      ['港股范围', p.hk_range],
      ['风险特征', p.risk],
    ].map(([label, value]) => `<div class="fact"><span>${esc(label)}</span><b>${esc(value)}</b></div>`).join('');
    const returnsGrid = returns && Object.keys(returns).length ? `
      <div class="return-grid">
        <div class="return"><span>近 1 月</span><b class="${trendClass(returns['1m'])}">${signed(returns['1m'])}</b></div>
        <div class="return"><span>近 1 年</span><b class="${trendClass(returns['1y'])}">${signed(returns['1y'])}</b></div>
        <div class="return"><span>近 3 年</span><b class="${trendClass(returns['3y'])}">${signed(returns['3y'])}</b></div>
        <div class="return"><span>今年以来</span><b class="${trendClass(returns.ytd)}">${signed(returns.ytd)}</b></div>
        <div class="return"><span>成立以来</span><b class="${trendClass(returns.since)}">${signed(returns.since)}</b></div>
        <div class="return"><span>近 1 年最大回撤</span><b class="down">${signed(returns.mdd1y)}</b></div>
      </div>
      <p class="note">${esc(returns.basis)}。数据只作学习参考，不是官方业绩公告。</p>` : `
      <p class="note">新发产品，暂无历史业绩。重点看发行公告、产品要素和公开策略，不要把公开报道当成未来收益。</p>`;
    return `
      <article class="product ${isYixin ? 'yixin' : 'jiajun'}">
        <div class="product-top">
          <div>
            <span class="pill ${isYixin ? 'gold' : ''}">${isYixin ? '已运行纯债' : '新发 · 发行期'}</span>
            <h3>${esc(p.short)}</h3>
            <p class="codes">${esc((p.codes || []).join(' / '))}</p>
          </div>
          <span class="status">${esc(p.status)}</span>
        </div>
        ${navBox}
        <div class="facts">${facts}</div>
        ${returnsGrid}
        <div class="issue-line">
          <b>${isYixin ? '看什么' : '关键节点'}</b>
          <span>${esc(isYixin ? '净值、回撤、久期、信用暴露、申赎状态' : '发行公告、募集期、成立公告、建仓期、首次净值')}</span>
        </div>
        <p class="note">来源：${esc(p.source)}</p>
      </article>`;
  }).join('');
}

function renderEvents(data) {
  const wrap = $('events');
  const events = data.events || [];
  wrap.innerHTML = events.map((event) => {
    const tags = (event.impact || []).map((x) => `<span class="tag ${x === '嘉俊' ? 'jiajun' : x === '益鑫' ? 'yixin' : 'policy'}">${esc(x)}</span>`).join('');
    const region = event.region === '产品' ? '<span class="tag policy">产品节点</span>' : `<span class="tag">${esc(event.region)}</span>`;
    const detail = event.actual
      ? `<b class="actual">公布 ${esc(event.actual)}</b>`
      : event.forecast
        ? `预期 ${esc(event.forecast)}`
        : event.previous
          ? `前值 ${esc(event.previous)}`
          : event.region === '产品' ? '' : esc(event.status);
    return `
      <div class="event">
        <div class="event-date"><b>${esc(shortDate(event.date))}</b><span>${esc(event.time || '—')}</span></div>
        <div>
          <h3>${esc(event.title)}</h3>
          <div class="event-meta">${region}${tags}</div>
        </div>
        <div class="event-status"><b>${esc(event.status)}</b>${detail}</div>
      </div>`;
  }).join('');
}

function renderMarket(data) {
  const market = data.market || {};
  const yields = market.yields || [];
  const y10 = yields.find((x) => x.label.includes('10Y'));
  const y30 = yields.find((x) => x.label.includes('30Y'));
  const lpr = market.lpr;
  const shibor = market.shibor;
  const cards = [];
  if (y10) cards.push({ label: '10Y 国债', value: `${fmt(y10.value)}%`, delta: `${signed(y10.change_bp, 1)}bp`, className: trendClass(-y10.change_bp), small: y10.date });
  if (y30) cards.push({ label: '30Y 国债', value: `${fmt(y30.value)}%`, delta: `${signed(y30.change_bp, 1)}bp`, className: trendClass(-y30.change_bp), small: y30.date });
  if (lpr) cards.push({ label: 'LPR', value: `${fmt(lpr['1y'])}% / ${fmt(lpr['5y'])}%`, delta: '1Y / 5Y', className: 'flat', small: lpr.date });
  if (shibor) cards.push({ label: shibor.label || 'Shibor 隔夜', value: `${fmt(shibor.value, 3)}%`, delta: '资金面', className: 'flat', small: shibor.date });
  $('market').innerHTML = cards.map((card) => `
    <div class="metric">
      <span>${esc(card.label)}</span>
      <b>${esc(card.value)}</b>
      <small class="${card.className}">${esc(card.delta)} · ${esc(card.small || '')}</small>
    </div>`).join('');

  const indices = market.indices || [];
  $('indices').innerHTML = indices.map((idx) => `
    <div class="index">
      <span>${esc(idx.label)}</span>
      <b>${fmt(idx.value)}</b>
      <small class="${trendClass(idx.change)}">${signed(idx.change)}</small>
    </div>`).join('');
}

let allNews = [];
let activeFilter = '全部';

function renderNews() {
  const wrap = $('news');
  const filtered = activeFilter === '全部'
    ? allNews
    : allNews.filter((item) => (item.impact || []).includes(activeFilter) || item.tag === activeFilter);
  if (!filtered.length) {
    wrap.innerHTML = '<p class="note">当前筛选下没有公开新闻。</p>';
    return;
  }
  wrap.innerHTML = filtered.map((item) => {
    const url = safeUrl(item.url);
    const title = url
      ? `<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(item.title)}</a>`
      : esc(item.title);
    const impacts = (item.impact || []).map((x) => `<span class="tag ${x === '嘉俊' ? 'jiajun' : 'yixin'}">${esc(x)}</span>`).join('');
    return `
      <article class="news-item">
        <div class="news-side"><b>${esc(item.source || '公开来源')}</b><span>${esc(item.time || '—')}</span></div>
        <div class="news-body">
          <h3>${title}</h3>
          ${item.summary ? `<p class="news-summary">${esc(item.summary)}</p>` : ''}
          <p class="news-why">${esc(item.why || '')}</p>
          <div class="news-meta"><span class="tag policy">${esc(item.tag || '市场')}</span>${impacts}</div>
        </div>
      </article>`;
  }).join('');
}

function initNewsFilters() {
  document.querySelectorAll('#news-toolbar button').forEach((button) => {
    button.addEventListener('click', () => {
      activeFilter = button.dataset.filter;
      document.querySelectorAll('#news-toolbar button').forEach((b) => {
        b.setAttribute('aria-pressed', String(b === button));
      });
      renderNews();
    });
  });
}

function renderQuestions(data) {
  $('questions').innerHTML = (data.questions || []).map((question) => `
    <details>
      <summary>${esc(question)}</summary>
      <p>先把公开事实、自己的判断和待核实的问题分开写。不要用一句“看好”代替依据；也不要把新闻标题当成产品结论。</p>
    </details>`).join('');
}

async function init() {
  try {
    const response = await fetch('data/dashboard.json', { cache: 'no-store' });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    renderMeta(data);
    renderHero(data);
    renderProducts(data);
    renderEvents(data);
    renderMarket(data);
    allNews = data.news || [];
    renderNews();
    initNewsFilters();
    renderQuestions(data);
  } catch (error) {
    console.error('dashboard load failed', error);
    $('products').innerHTML = '<p class="note">数据加载失败。请通过本地服务器或 GitHub Pages 打开，不要直接双击 HTML。</p>';
    $('events').innerHTML = '';
    $('market').innerHTML = '';
    $('indices').innerHTML = '';
    $('news').innerHTML = '';
    $('questions').innerHTML = '';
  }
}

init();
