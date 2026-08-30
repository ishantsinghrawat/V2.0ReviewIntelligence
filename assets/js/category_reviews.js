const $ = s => document.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
let reviews = [];

async function loadJson(path, fallback=[]) {
  try {
    const r = await fetch(path + '?v=' + Date.now());
    if (!r.ok) throw new Error('HTTP ' + r.status);
    return await r.json();
  } catch (e) {
    console.error(e);
    return fallback;
  }
}

function reviewCategories(r) {
  const values = [];
  const primary = r.primary_category || r.category;
  if (primary) values.push(primary);
  for (const issue of (r.issues || [])) {
    const label = typeof issue === 'string' ? issue : issue?.label;
    if (label) values.push(label);
  }
  return [...new Set(values.filter(Boolean))];
}

function sentimentOf(r) {
  if (r.sentiment_std) return r.sentiment_std;
  const rating = Number(r.rating || 0);
  if (rating <= 2) return 'Negative';
  if (rating >= 4) return 'Positive';
  return 'Neutral';
}

function allCategories() {
  return [...new Set(reviews.flatMap(reviewCategories))].sort((a,b)=>a.localeCompare(b));
}

function fillSelect(id, values, label) {
  const el = $(id);
  const current = el.value;
  el.innerHTML = `<option value="">${label}</option>` + [...new Set(values.filter(Boolean))].sort().map(v => `<option value="${esc(v)}">${esc(v)}</option>`).join('');
  if ([...el.options].some(o => o.value === current)) el.value = current;
}

function baseFiltered() {
  const src = $('#source').value;
  const ver = $('#version').value;
  const sent = $('#sentiment').value;
  const query = $('#search').value.trim().toLowerCase();
  return reviews.filter(r => {
    if (src && r.source !== src) return false;
    if (ver && String(r.app_version || '') !== ver) return false;
    if (sent && sentimentOf(r) !== sent) return false;
    if (query && !String(r.review || '').toLowerCase().includes(query)) return false;
    return true;
  });
}

function filtered() {
  const category = $('#category').value;
  return baseFiltered().filter(r => !category || reviewCategories(r).includes(category));
}

function renderCards() {
  const base = baseFiltered();
  const selected = $('#category').value;
  const counts = new Map();
  for (const r of base) {
    for (const c of reviewCategories(r)) {
      if (!counts.has(c)) counts.set(c, {total:0, negative:0});
      const x = counts.get(c); x.total += 1; if (sentimentOf(r) === 'Negative') x.negative += 1;
    }
  }
  const rows = [...counts.entries()].sort((a,b)=>b[1].total-a[1].total || a[0].localeCompare(b[0]));
  $('#categoryCards').innerHTML = rows.length ? rows.map(([cat,x]) => {
    const pct = x.total ? Math.round(100*x.negative/x.total) : 0;
    return `<button class="category-card ${selected===cat?'selected':''}" data-category="${esc(cat)}" type="button"><span class="category-name">${esc(cat)}</span><span class="category-count">${x.total}</span><span class="category-sub">${x.negative} negative · ${pct}%</span></button>`;
  }).join('') : '<div class="empty">No categories match the current filters.</div>';
  document.querySelectorAll('.category-card').forEach(btn => btn.addEventListener('click', () => {
    $('#category').value = btn.dataset.category;
    render();
    window.scrollTo({top: document.querySelector('#resultsTitle').getBoundingClientRect().top + window.scrollY - 135, behavior:'smooth'});
  }));
}

function reviewHtml(r, matchedCategory) {
  const cats = reviewCategories(r);
  const categoryPills = cats.map(c => `<span class="pill ${c===matchedCategory?'pill-active':''}">${esc(c)}</span>`).join(' ');
  const conf = r.classification_confidence || 'Legacy';
  return `<article class="review review-full"><div class="review-top"><div class="meta">${esc(r.review_date)} · ${esc(r.source)} · ${esc(r.app_version || 'unknown version')} · ⭐ ${esc(r.rating ?? '—')} · ${esc(sentimentOf(r))} · ${esc(conf)}</div></div><div class="review-text">${esc(r.review)}</div><div class="review-tags">${categoryPills}</div></article>`;
}

function renderReviews() {
  const selectedCategory = $('#category').value;
  const data = filtered().sort((a,b)=>String(b.review_date||'').localeCompare(String(a.review_date||'')));
  $('#reviewCount').textContent = `${data.length} matching review${data.length===1?'':'s'}`;
  $('#resultsTitle').textContent = selectedCategory ? selectedCategory : 'All reviews by category';
  $('#resultsMeta').textContent = `${data.length} review${data.length===1?'':'s'} shown${selectedCategory ? ' · includes primary and multi-label matches' : ' · grouped by category'}`;

  if (!data.length) {
    $('#groupedReviews').innerHTML = '<div class="empty">No matching reviews.</div>';
    return;
  }

  if (selectedCategory) {
    $('#groupedReviews').innerHTML = `<div class="category-section"><div class="category-section-head"><h3>${esc(selectedCategory)}</h3><span class="pill">${data.length} reviews</span></div>${data.map(r=>reviewHtml(r, selectedCategory)).join('')}</div>`;
    return;
  }

  const groups = new Map();
  for (const r of data) {
    const cats = reviewCategories(r);
    const primary = r.primary_category || r.category || cats[0] || 'Unclassified';
    if (!groups.has(primary)) groups.set(primary, []);
    groups.get(primary).push(r);
  }
  const ordered = [...groups.entries()].sort((a,b)=>b[1].length-a[1].length || a[0].localeCompare(b[0]));
  $('#groupedReviews').innerHTML = ordered.map(([cat, items]) => `<section class="category-section"><div class="category-section-head"><h3>${esc(cat)}</h3><button class="text-button choose-category" data-category="${esc(cat)}" type="button">View ${items.length} review${items.length===1?'':'s'} →</button></div>${items.map(r=>reviewHtml(r,cat)).join('')}</section>`).join('');
  document.querySelectorAll('.choose-category').forEach(btn=>btn.addEventListener('click',()=>{$('#category').value=btn.dataset.category;render();}));
}

function render() { renderCards(); renderReviews(); }

function csvEscape(value) { return `"${String(value ?? '').replace(/"/g,'""')}"`; }
function downloadCsv() {
  const rows = filtered().sort((a,b)=>String(b.review_date||'').localeCompare(String(a.review_date||'')));
  if (!rows.length) return;
  const header = ['review_date','source','app_version','rating','sentiment','categories','classification_confidence','review'];
  const body = rows.map(r => [r.review_date,r.source,r.app_version,r.rating,sentimentOf(r),reviewCategories(r).join(' | '),r.classification_confidence||'Legacy',r.review].map(csvEscape).join(','));
  const blob = new Blob([[header.join(','), ...body].join('\n')], {type:'text/csv;charset=utf-8'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  const cat = $('#category').value ? $('#category').value.replace(/[^a-z0-9]+/gi,'_') : 'all_categories';
  a.download = `customer_voice_reviews_${cat}.csv`;
  document.body.appendChild(a); a.click(); URL.revokeObjectURL(a.href); a.remove();
}

async function boot() {
  reviews = await loadJson('data.json', []);
  fillSelect('#category', allCategories(), 'All categories');
  fillSelect('#source', reviews.map(r=>r.source), 'All stores');
  fillSelect('#version', reviews.map(r=>String(r.app_version||'')), 'All versions');
  ['#category','#source','#version','#sentiment'].forEach(id => $(id).addEventListener('change', render));
  $('#search').addEventListener('input', render);
  $('#clearCategory').addEventListener('click', ()=>{$('#category').value='';render();});
  $('#downloadCsv').addEventListener('click', downloadCsv);
  render();
}
boot();
