const cabinetCleanupSelection=new Set();

function cabinetCleanupControls(){
  if(!state.view.startsWith('cat:'))return '';
  if(!state.cleanupMode)return '<button class="filter-btn list-action cleanup-toggle" id="cleanupToggle">批量清理</button>';
  const count=cabinetCleanupSelection.size;
  return `<span class="cleanup-count">已选 ${count} 条</span><button class="quiet-action cleanup-select-all" id="cleanupSelectAll">全选当前结果</button><button class="quiet-action cleanup-delete" id="cleanupDelete" ${count?'':'disabled'}>移入回收站${count?`（${count}）`:''}</button><button class="quiet-action cleanup-exit" id="cleanupExit">退出清理</button>`;
}

function cabinetCleanupRank(article,source,defaultRank){
  if(!state.cleanupMode||!state.view.startsWith('cat:'))return defaultRank;
  const checked=cabinetCleanupSelection.has(article.id);
  return `<div class="rank cleanup-rank ${source?.tier==='A'?'a':''}"><input class="cleanup-checkbox" type="checkbox" data-cleanup-id="${cabinetEscape(article.id)}" ${checked?'checked':''} aria-label="选择《${cabinetEscape(article.title)}》"></div>`;
}

function cabinetSetCleanupMode(enabled){
  state.cleanupMode=Boolean(enabled)&&state.view.startsWith('cat:');
  if(!state.cleanupMode)cabinetCleanupSelection.clear();
  render();
}

function cabinetArticleProtectedSummary(articles){
  const saved=articles.filter(article=>article.saved).length;
  const annotated=articles.filter(article=>cabinetArticleNotes(article.id).length).length;
  const details=[];
  if(saved)details.push(`${saved} 条已收藏`);
  if(annotated)details.push(`${annotated} 条含批注`);
  return details;
}

function cabinetOfflineTrash(articles){
  const deletedAt=new Date();
  const purgeAfter=new Date(deletedAt.getTime()+7*24*60*60*1000);
  articles.forEach(article=>{
    state.trash=state.trash.filter(item=>item.articleId!==article.id);
    state.trash.unshift({articleId:article.id,article:structuredClone(article),deletedAt:deletedAt.toISOString(),purgeAfter:purgeAfter.toISOString()});
    if(!state.tombstones.some(item=>item.id===article.id))state.tombstones.push({id:article.id,source:article.source||'',url:article.url||'',title:article.title||''});
  });
}

function cabinetRefreshSourceCounts(){
  state.sources.forEach(source=>{
    const articles=state.articles.filter(article=>article.source===source.id);
    source.articles=articles.length;
    source.unread=articles.filter(article=>!article.read).length;
  });
}

async function cabinetMoveToTrash(articleIds,{batch=false}={}){
  const ids=[...new Set(articleIds)];
  const articles=ids.map(id=>state.articles.find(article=>article.id===id)).filter(Boolean);
  if(!articles.length){toast('没有可清理的文章');return false}
  const protectedItems=cabinetArticleProtectedSummary(articles);
  if(batch||protectedItems.length){
    const warning=protectedItems.length?`\n其中${protectedItems.join('、')}，恢复前相关内容会一起保留。`:'';
    if(!confirm(`将 ${articles.length} 条信息移入回收站？${warning}\n回收站保留 7 天。`))return false;
  }
  try{
    if(backendReady){
      const response=await fetch('/api/articles/trash',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({articleIds:articles.map(article=>article.id)})});
      const result=await response.json();
      if(!response.ok||!result.ok)throw new Error(result.error||'删除失败');
      state.trash=result.trash||[];
    }else cabinetOfflineTrash(articles);
    const removedIds=new Set(articles.map(article=>article.id));
    state.articles=state.articles.filter(article=>!removedIds.has(article.id));
    cabinetRefreshSourceCounts();
    cabinetCleanupSelection.clear();
    if(batch)state.cleanupMode=false;
    localStorage.setItem('cabinet-v1',JSON.stringify({sources:state.sources,articles:state.articles,trash:state.trash,tombstones:state.tombstones}));
    render();
    cabinetUndoToast(`已移入回收站 ${articles.length} 条`,articles.map(article=>article.id));
    return true;
  }catch(error){toast(error.message||'未能移入回收站');return false}
}

function cabinetUndoToast(message,articleIds){
  const element=$('#toast');
  element.classList.add('with-action','show');
  element.innerHTML=`<span>${cabinetEscape(message)}</span><button type="button">撤销</button>`;
  clearTimeout(window.toastTimer);
  element.querySelector('button').onclick=async()=>{element.classList.remove('show','with-action');await cabinetRestoreTrash(articleIds)};
  window.toastTimer=setTimeout(()=>element.classList.remove('show','with-action'),5000);
}

async function cabinetRestoreTrash(articleIds){
  const ids=[...new Set(articleIds)];
  const items=ids.map(id=>state.trash.find(item=>item.articleId===id)).filter(Boolean);
  if(!items.length){toast('这篇文章已不在回收站');return}
  try{
    if(backendReady){
      const response=await fetch('/api/trash/restore',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({articleIds:ids})});
      const result=await response.json();
      if(!response.ok||!result.ok)throw new Error(result.error||'恢复失败');
      state.trash=result.trash||[];
    }else{
      state.trash=state.trash.filter(item=>!ids.includes(item.articleId));
      state.tombstones=state.tombstones.filter(item=>!ids.includes(item.id));
    }
    const activeIds=new Set(state.articles.map(article=>article.id));
    items.forEach(item=>{if(item.article&&!activeIds.has(item.article.id)){state.articles.push(item.article);activeIds.add(item.article.id)}});
    cabinetRefreshSourceCounts();
    persist();render();toast(`已恢复 ${items.length} 条信息`);
  }catch(error){toast(error.message||'恢复失败')}
}

async function cabinetPurgeTrash(articleIds=null){
  const targets=articleIds?.length?state.trash.filter(item=>articleIds.includes(item.articleId)):state.trash.slice();
  if(!targets.length)return;
  if(!confirm(`永久删除 ${targets.length} 条信息？正文、阅读进度、收藏和批注将无法恢复。`))return;
  try{
    const ids=targets.map(item=>item.articleId);
    if(backendReady){
      const response=await fetch('/api/trash/purge',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({articleIds:articleIds?.length?ids:null})});
      const result=await response.json();
      if(!response.ok||!result.ok)throw new Error(result.error||'永久删除失败');
      state.trash=result.trash||[];
    }else state.trash=state.trash.filter(item=>!ids.includes(item.articleId));
    cabinetAnnotations=cabinetAnnotations.filter(item=>!ids.includes(item.articleId));
    ids.forEach(id=>delete cabinetContentStatus[id]);
    persist();render();toast(`已永久删除 ${ids.length} 条信息`);
  }catch(error){toast(error.message||'永久删除失败')}
}

async function cabinetTrashFromReader(articleId){
  if(await cabinetMoveToTrash([articleId]))closeReader();
}

function cabinetTrashPage(){
  const [eye,title,description]=pageInfo();
  const query=state.search.trim().toLowerCase();
  const items=state.trash.filter(item=>{
    const article=item.article||{},source=src(article.source);
    return !query||`${article.title||''} ${article.summary||''} ${source?.name||''}`.toLowerCase().includes(query);
  });
  const rows=items.map(item=>{
    const article=item.article||{},source=src(article.source);
    const purgeTime=Date.parse(item.purgeAfter),days=Number.isFinite(purgeTime)?Math.max(1,Math.ceil((purgeTime-Date.now())/(24*60*60*1000))):7;
    const deletedTime=Date.parse(item.deletedAt),deletedLabel=Number.isFinite(deletedTime)?new Intl.DateTimeFormat('zh-CN',{month:'long',day:'numeric',hour:'2-digit',minute:'2-digit'}).format(new Date(deletedTime)):'刚刚';
    const summary=String(article.summary||'').trim();
    return `<section class="trash-card"><div><div class="trash-meta">${cabinetEscape(source?.name||'原信息源')} · ${cabinetEscape(cats[source?.category]||'其他')} · ${cabinetEscape(deletedLabel)}移入</div><h2>${cabinetEscape(article.title||'未命名信息')}</h2>${summary?`<p>${cabinetEscape(summary)}</p>`:''}<div class="meta-row"><span class="tag">${article.read?'已读':'未读'}</span>${article.saved?'<span class="tag">已收藏</span>':''}<span class="tag">还可恢复 ${days} 天</span></div></div><div class="trash-actions"><button class="action-btn" data-trash-restore="${cabinetEscape(item.articleId)}">恢复</button><button class="action-btn trash-purge" data-trash-purge="${cabinetEscape(item.articleId)}">永久删除</button></div></section>`;
  }).join('');
  return `<div class="page-head"><div><div class="eyebrow">${eye}</div><h1>${title}</h1><p>${description}</p></div><div class="head-stat"><div class="stat"><b>${items.length}</b><span>条待清理</span></div></div></div><div class="trash-summary"><span>到期后正文与个人标记会清除，但文章不会被同步回来。</span><span class="filter-spacer"></span>${state.trash.length?'<button class="filter-btn list-action list-action-wide trash-clear" id="trashClear">清空回收站</button>':''}</div>${rows||`<div class="empty"><div class="empty-mark trash-empty-mark">${trashIcon('empty-trash-icon')}</div><h3>${query?'没有匹配的已删除信息':'回收站是空的'}</h3><p>${query?'试试更换本页搜索词。':'删除的信息会在这里保留 7 天。'}</p></div>`}`;
}

function cabinetWireCleanup(){
  document.querySelectorAll('[data-filter]').forEach(button=>button.onclick=()=>{state.filter=button.dataset.filter;if(state.cleanupMode)cabinetCleanupSelection.clear();render()});
  $('#cleanupToggle')&&($('#cleanupToggle').onclick=()=>cabinetSetCleanupMode(true));
  $('#cleanupExit')&&($('#cleanupExit').onclick=()=>cabinetSetCleanupMode(false));
  $('#cleanupSelectAll')&&($('#cleanupSelectAll').onclick=()=>{visibleArticles().forEach(article=>cabinetCleanupSelection.add(article.id));render()});
  $('#cleanupDelete')&&($('#cleanupDelete').onclick=()=>cabinetMoveToTrash([...cabinetCleanupSelection],{batch:true}));
  document.querySelectorAll('[data-cleanup-id]').forEach(input=>input.onclick=event=>{
    event.preventDefault();
    event.stopPropagation();
    const articleId=input.dataset.cleanupId;
    if(cabinetCleanupSelection.has(articleId))cabinetCleanupSelection.delete(articleId);
    else cabinetCleanupSelection.add(articleId);
    render();
  });
  document.querySelectorAll('[data-trash-one]').forEach(button=>button.onclick=event=>{event.stopPropagation();cabinetMoveToTrash([button.dataset.trashOne])});
  document.querySelectorAll('[data-trash-restore]').forEach(button=>button.onclick=()=>cabinetRestoreTrash([button.dataset.trashRestore]));
  document.querySelectorAll('[data-trash-purge]').forEach(button=>button.onclick=()=>cabinetPurgeTrash([button.dataset.trashPurge]));
  $('#trashClear')&&($('#trashClear').onclick=()=>cabinetPurgeTrash());
}

function cabinetIsTombstoned(article){
  return state.tombstones.some(item=>item.id===article.id||Boolean(article.url&&item.url===article.url)||(item.source===article.source&&item.title===article.title));
}

document.addEventListener('input',event=>{if(event.target?.id==='searchInput'&&state.cleanupMode)cabinetCleanupSelection.clear()},true);
