async function init(){
 const data=await fetch('data_master.json').then(r=>r.json()).catch(()=>[]);
 const cats=[...new Set(data.flatMap(r=>[r.primary_category,...(r.categories||[])]).filter(Boolean))].sort();
 const sel=document.getElementById('cat'); sel.innerHTML='<option>All Categories</option>'+cats.map(c=>`<option>${c}</option>`).join('');
 const render=()=>{const c=sel.value,q=document.getElementById('q').value.toLowerCase();
 const rows=data.filter(r=>(c==='All Categories'||r.primary_category===c||(r.categories||[]).includes(c))&&(!q||String(r.review).toLowerCase().includes(q)));
 document.getElementById('list').innerHTML=rows.map(r=>`<article><h3>${r.primary_category||'Uncategorized'} • ⭐${r.rating||''}</h3><p>${r.review||''}</p><small>${r.review_date||''} • ${r.source||''} • ${r.app_version||''}</small></article>`).join('')||'<p>No reviews found.</p>';};
 sel.onchange=render; document.getElementById('q').oninput=render; render();}
init();