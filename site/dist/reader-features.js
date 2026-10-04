let cabinetAnnotations=[];
let cabinetActiveArticleId=null;
let cabinetActiveHtml='';
let cabinetPendingSelection=null;
let cabinetProgressTimer=null;
let cabinetAnnotationLoadAttempts=0;
let cabinetContentStatus={};
let cabinetContentJobs=new Map();
let cabinetReaderIntent=0;
let cabinetBatch={running:false,total:0,done:0,failed:0,runId:0};

const cabinetEscape=value=>String(value??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const cabinetArticleNotes=articleId=>cabinetAnnotations.filter(item=>item.articleId===articleId);

async function cabinetLoadAnnotations(){
  if(!backendReady){
    if(cabinetAnnotationLoadAttempts++<20)setTimeout(cabinetLoadAnnotations,250);
    return;
  }
  try{
    const [annotationResponse,statusResponse]=await Promise.all([
      fetch('/api/annotations',{cache:'no-store'}),
      fetch('/api/article-content-status',{cache:'no-store'})
    ]);
    if(!annotationResponse.ok||!statusResponse.ok)throw new Error('本机阅读资料读取失败');
    cabinetAnnotations=(await annotationResponse.json()).annotations||[];
    cabinetContentStatus=Object.fromEntries(((await statusResponse.json()).articles||[]).map(item=>[item.articleId,item]));
    render();
  }catch{toast('阅读资料暂时无法读取')}
}

async function cabinetSaveAnnotation(annotation){
  const response=await fetch('/api/annotations',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(annotation)});
  const result=await response.json();
  if(!response.ok||!result.ok)throw new Error(result.error||'批注保存失败');
  const saved=result.annotation;
  const index=cabinetAnnotations.findIndex(item=>item.id===saved.id);
  if(index>=0)cabinetAnnotations[index]=saved;else cabinetAnnotations.unshift(saved);
  return saved;
}

async function cabinetDeleteAnnotation(id){
  const response=await fetch(`/api/annotations/${encodeURIComponent(id)}`,{method:'DELETE'});
  if(!response.ok)throw new Error('批注删除失败');
  cabinetAnnotations=cabinetAnnotations.filter(item=>item.id!==id);
}

const cabinetOriginalPageInfo=pageInfo;
pageInfo=function(){
  if(state.view==='notes')return ['READING NOTES','札记','按文章归拢你的划线与随手笔记。'];
  return cabinetOriginalPageInfo();
};

nav=function(){
  const c=counts();
  const noteArticles=new Set(cabinetAnnotations.map(item=>item.articleId)).size;
  const main=[['today','⌂','奏章呈送',c.today],['inbox','▣','批红定案',c.inbox],['continue','▶','继续阅读',c.cont],['saved','★','收藏',c.saved],['notes','✎','札记',noteArticles]];
  const catsNav=Object.entries(cats).filter(([key])=>key!=='OTHER').map(([key,value])=>['cat:'+key,categoryIcons[key],value,'']);
  const tiers=[['tier:A','A','核心来源',''],['tier:B','B','一般来源',''],['tier:C','C','低优先级','']];
  const group=(label,items)=>`<div class="nav-group">${label?`<div class="nav-label">${label}</div>`:''}${items.map(([value,icon,text,count])=>`<button class="nav-btn ${state.view===value?'active':''}" data-view="${value}" onclick="setView('${value}')"><span class="nav-icon ${icon.length===1?'tier-letter':''}">${icon}</span><span>${text}</span>${count!==''?`<span class="nav-count">${count}</span>`:''}</button>`).join('')}</div>`;
  $('#nav').innerHTML=group('',main)+group('信息类型',catsNav)+group('来源等级',tiers)+group('管理',[['sources','◉','信息源',''],['settings','⚙','设置','']]);
};

function cabinetArticleContentState(articleId){return cabinetContentStatus[articleId]?.status||'pending'}
function cabinetArticleContentLabel(articleId){return ({pending:'待调阅',loading:'调阅中',ready:'可阅读',failed:'跳转原文'})[cabinetArticleContentState(articleId)]||'待调阅'}
function cabinetUpdateArticleStatusDom(articleId){
  const status=cabinetArticleContentState(articleId),label=cabinetArticleContentLabel(articleId),selector=CSS.escape(articleId);
  document.querySelectorAll(`[data-content-status="${selector}"]`).forEach(node=>{node.textContent=label;node.className=`article-content-status ${status}`});
  document.querySelectorAll(`[data-article-card="${selector}"]`).forEach(card=>{
    card.classList.toggle('content-failed',status==='failed');const article=state.articles.find(item=>item.id===articleId);if(!article)return;
    const heading=card.querySelector('h2'),row=card.querySelector('.row-actions'),oldAction=row?.querySelector('[data-open],.article-original-action');
    if(status==='failed'){
      if(heading&&!heading.querySelector('.article-original-link')){heading.removeAttribute('data-open');heading.onclick=null;heading.innerHTML=`<a class="article-original-link" href="${cabinetEscape(article.url)}" target="_blank" rel="noopener">${cabinetEscape(article.title)}</a>`}
      if(oldAction&&!oldAction.classList.contains('article-original-action')){const link=document.createElement('a');link.className='mini article-original-action';link.href=article.url;link.target='_blank';link.rel='noopener';link.ariaLabel='跳转原文';link.textContent='↗';oldAction.replaceWith(link)}
    }else{
      if(heading?.querySelector('.article-original-link')){heading.textContent=article.title;heading.dataset.open=articleId;heading.onclick=()=>openReader(articleId)}
      if(oldAction?.classList.contains('article-original-action')){const button=document.createElement('button');button.className='mini';button.dataset.open=articleId;button.ariaLabel='打开阅读器';button.textContent='⋯';button.onclick=()=>openReader(articleId);oldAction.replaceWith(button)}
    }
  });
}
function cabinetSetArticleContentState(articleId,status,error=''){
  cabinetContentStatus[articleId]={articleId,status,error,fetchedAt:new Date().toISOString()};
  cabinetUpdateArticleStatusDom(articleId);cabinetUpdateBatchButton();
}

articleCard=function(article,index){
  const source=src(article.source),cover=coverSrc(article.cover,true),notes=cabinetArticleNotes(article.id),contentState=cabinetArticleContentState(article.id);
  const approved=articleInInbox(article);
  const rank=state.view==='today'
    ?`<div class="rank ${source?.tier==='A'?'a':''}"><button class="today-inbox-check ${approved?'checked':''}" data-approve="${article.id}" aria-label="${approved?'已在批红定案':'选入批红定案'}">${approved?'✓':''}</button></div>`
    :`<div class="rank ${source?.tier==='A'?'a':''}">${String(index+1).padStart(2,'0')}</div>`;
  const noteBadge=notes.length?`<span class="article-note-badge">${notes.length} 条札记</span>`:'';
  const latest=state.view==='saved'&&notes.length?`<div class="note-text">最近札记：${cabinetEscape(notes[0].quote.slice(0,90))}${notes[0].quote.length>90?'…':''}</div>`:'';
  const title=contentState==='failed'?`<h2><a class="article-original-link" href="${cabinetEscape(article.url)}" target="_blank" rel="noopener">${article.title}</a></h2>`:`<h2 data-open="${article.id}">${article.title}</h2>`;
  const openAction=contentState==='failed'?`<a class="mini article-original-action" href="${cabinetEscape(article.url)}" target="_blank" rel="noopener" aria-label="跳转原文">↗</a>`:`<button class="mini" data-open="${article.id}" aria-label="打开阅读器">⋯</button>`;
  return `<article class="article ${article.read?'read':''} ${cover?'has-cover':''} ${contentState==='failed'?'content-failed':''}" data-article-card="${article.id}">${rank}<div><div class="article-source"><span>${source?.name||'未知来源'}</span><span>·</span><span class="tier ${source?.tier}">${source?.tier}</span><span>·</span><span>${cats[source?.category]||'其他'}</span>${!source?.inbox?'<span title="不进入 Inbox">静默源</span>':''}</div>${title}<p class="summary">${article.summary}</p>${latest}<div class="meta-row">${(article.tags||[]).map(tag=>`<span class="tag">#${tag}</span>`).join('')}<span class="tag">${article.mins} 分钟</span><span class="article-content-status ${contentState}" data-content-status="${article.id}">${cabinetArticleContentLabel(article.id)}</span>${noteBadge}</div></div>${cover?`<img class="article-cover" src="${cover}" alt="${article.title} 封面" loading="lazy" referrerpolicy="no-referrer" onerror="this.closest('.article').classList.remove('has-cover');this.remove()">`:''}<div class="article-side"><span>${formatPublishedAt(article)}</span><div class="row-actions"><button class="mini ${article.saved?'saved':''}" data-save="${article.id}" aria-label="收藏">${article.saved?'★':'☆'}</button><button class="mini" data-read="${article.id}" aria-label="${article.read?'标记未读':'标记已读'}">${article.read?'◌':'✓'}</button>${openAction}</div>${article.progress>0&&article.progress<1?`<div><span>${Math.round(article.progress*100)}%</span><div class="progress"><i style="width:${article.progress*100}%"></i></div></div>`:''}</div></article>`;
};

function cabinetNotesPage(){
  const [eye,title,description]=pageInfo();
  const groups=new Map();
  cabinetAnnotations.forEach(annotation=>{
    const article=state.articles.find(item=>item.id===annotation.articleId);
    if(!article)return;
    const source=src(article.source);
    const haystack=`${article.title} ${source?.name||''} ${annotation.quote} ${annotation.note}`.toLowerCase();
    if(state.search&& !haystack.includes(state.search.trim().toLowerCase()))return;
    if(!groups.has(article.id))groups.set(article.id,{article,source,items:[]});
    groups.get(article.id).items.push(annotation);
  });
  const ordered=[...groups.values()].sort((a,b)=>String(b.items[0]?.updatedAt||'').localeCompare(String(a.items[0]?.updatedAt||'')));
  const body=ordered.length?ordered.map(group=>`<section class="note-article"><div class="note-article-head"><div><div class="note-article-meta">${cabinetEscape(group.source?.name||'未知来源')} · ${cabinetEscape(cats[group.source?.category]||'其他')}</div><h2 data-note-article="${group.article.id}">${cabinetEscape(group.article.title)}</h2></div><span class="note-count">${group.items.length} 条批注</span></div>${group.items.map(item=>`<button class="note-excerpt" data-note-open="${item.id}" data-article-id="${group.article.id}"><div class="note-quote">“${cabinetEscape(item.quote)}”</div>${item.note?`<div class="note-text">${cabinetEscape(item.note)}</div>`:''}</button>`).join('')}</section>`).join(''):`<div class="empty"><div class="empty-mark">✎</div><h3>尚无札记</h3><p>在正文中选择文字并右键，即可划线或写下笔记。</p></div>`;
  return `<div class="page-head"><div><div class="eyebrow">${eye}</div><h1>${title}</h1><p>${description}</p></div></div><div class="notes-list">${body}</div>`;
}

function cabinetUpdateBatchButton(){
  const button=$('#bulkPrefetch');if(!button)return;
  if(cabinetBatch.running){button.disabled=true;button.textContent=`调阅中 ${cabinetBatch.done}/${cabinetBatch.total}`;return}
  button.disabled=false;
  if(cabinetBatch.total){const ready=cabinetBatch.total-cabinetBatch.failed;button.textContent=cabinetBatch.failed?`已调阅 ${ready}/${cabinetBatch.total} · ${cabinetBatch.failed}篇原文`:`已调阅 ${ready}/${cabinetBatch.total}`}
  else button.textContent='一键调阅';
}

async function cabinetFetchArticleContent(article,{force=false}={}){
  if(cabinetContentJobs.has(article.id))return cabinetContentJobs.get(article.id);
  cabinetSetArticleContentState(article.id,'loading');
  const job=(async()=>{
    try{
      const response=await fetch('/api/article-content',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({articleId:article.id,url:article.url,force})});
      const result=await response.json();
      if(!response.ok||!result.ok)throw new Error(result.error||'正文调阅失败');
      cabinetContentStatus[article.id]={articleId:article.id,status:'ready',error:'',fetchedAt:result.content.fetchedAt};
      const plainLength=(result.content.text||'').length;article.mins=Math.max(3,Math.min(60,Math.round(plainLength/500)||5));if(result.content.publishedAt)article.publishedAt=result.content.publishedAt;delete article.hours;persist();
      cabinetUpdateArticleStatusDom(article.id);return true;
    }catch(error){cabinetSetArticleContentState(article.id,'failed',error.message||'正文调阅失败');return false}
    finally{cabinetContentJobs.delete(article.id)}
  })();
  cabinetContentJobs.set(article.id,job);return job;
}

async function cabinetStartBulkPrefetch(){
  if(cabinetBatch.running)return;
  const articles=state.articles.filter(article=>!article.read&&articleInInbox(article));
  const runId=Date.now();cabinetBatch={running:true,total:articles.length,done:0,failed:0,runId};
  const queue=[];
  articles.forEach(article=>{if(cabinetArticleContentState(article.id)==='ready'&&article.publishedAt)cabinetBatch.done++;else queue.push(article)});
  cabinetUpdateBatchButton();
  if(!articles.length){cabinetBatch.running=false;cabinetUpdateBatchButton();return}
  const worker=async()=>{while(queue.length){const article=queue.shift();const ok=await cabinetFetchArticleContent(article,{force:cabinetArticleContentState(article.id)==='failed'||!article.publishedAt});cabinetBatch.done++;if(!ok)cabinetBatch.failed++;cabinetUpdateBatchButton()}};
  await Promise.all([worker(),worker()]);cabinetBatch.running=false;cabinetUpdateBatchButton();
  setTimeout(()=>{if(cabinetBatch.runId===runId&&!cabinetBatch.running){cabinetBatch={running:false,total:0,done:0,failed:0,runId};cabinetUpdateBatchButton()}},4200);
}
window.cabinetStartBulkPrefetch=cabinetStartBulkPrefetch;

render=function(){
  nav();
  $('#content').innerHTML=state.view==='sources'?sourcesPage():state.view==='settings'?settingsPage():state.view==='notes'?cabinetNotesPage():listPage();
  wire();
  const bulkButton=$('#bulkPrefetch');if(bulkButton)bulkButton.onclick=cabinetStartBulkPrefetch;cabinetUpdateBatchButton();
  document.querySelectorAll('[data-note-open]').forEach(button=>button.onclick=()=>openReader(button.dataset.articleId,button.dataset.noteOpen));
  document.querySelectorAll('[data-note-article]').forEach(button=>button.onclick=()=>openReader(button.dataset.noteArticle));
};

function cabinetReaderHeader(article,source){
  return `<div class="reader-progress" id="readerProgress" style="width:${(article.progress||0)*100}%"></div><div class="reader-head"><div class="reader-top"><span class="tier ${source.tier}">${source.tier} 级</span><span>${cabinetEscape(source.name)}</span><button class="icon-btn close" id="closeReader" aria-label="关闭阅读器">×</button></div><h1>${cabinetEscape(article.title)}</h1><div class="reader-byline">${cabinetEscape(article.author)}　·　${formatPublishedAt(article)}　·　预计 ${article.mins} 分钟</div><div class="reader-actions"><button class="action-btn ${article.saved?'primary':''}" id="readerSave">${article.saved?'★ 已收藏':'☆ 收藏'}</button><button class="action-btn" id="readerRead">${article.read?'标记未读':'标记已读'}</button><a class="action-btn" href="${cabinetEscape(article.url)}" target="_blank" rel="noopener">查看微信原文</a></div></div>`;
}

function cabinetSanitizeArticleHtml(raw){
  const documentCopy=new DOMParser().parseFromString(`<article>${raw}</article>`,'text/html');
  const root=documentCopy.querySelector('article');
  let imageIndex=0;
  root.querySelectorAll('script,style,iframe,object,embed,form,input,button,textarea,select,video,audio').forEach(node=>node.remove());
  root.querySelectorAll('*').forEach(node=>{
    [...node.attributes].forEach(attribute=>{
      const name=attribute.name.toLowerCase();
      if(name.startsWith('on')||['style','class','id'].includes(name))node.removeAttribute(attribute.name);
    });
    if(node.tagName==='A'){
      try{const target=new URL(node.getAttribute('href')||'',location.href);if(!['http:','https:'].includes(target.protocol))throw new Error();node.href=target.href;node.target='_blank';node.rel='noopener'}catch{node.removeAttribute('href')}
    }
    if(node.tagName==='IMG'){
      const rawSource=node.getAttribute('data-src')||node.getAttribute('src')||'';
      try{
        const target=new URL(rawSource,location.href);if(!['http:','https:'].includes(target.protocol))throw new Error();
        node.src=coverSrc(target.href);node.loading=imageIndex++===0?'eager':'lazy';node.referrerPolicy='no-referrer';node.className='reader-content-image';
        const frame=documentCopy.createElement('span');frame.className='reader-image-frame';node.replaceWith(frame);frame.appendChild(node);
      }catch{node.remove()}
    }
  });
  let blocks=[...root.querySelectorAll('p,h1,h2,h3,h4,li,blockquote,figcaption')].filter(node=>node.textContent.trim());
  if(!blocks.length&&root.textContent.trim()){const paragraph=documentCopy.createElement('p');paragraph.textContent=root.textContent.trim();root.replaceChildren(paragraph);blocks=[paragraph]}
  blocks.forEach((block,index)=>{block.classList.add('reader-block');block.dataset.blockIndex=String(index)});
  return root.innerHTML;
}

function cabinetTextPoint(block,offset){
  const walker=document.createTreeWalker(block,NodeFilter.SHOW_TEXT);
  let node,total=0,last=null;
  while((node=walker.nextNode())){last=node;const next=total+node.nodeValue.length;if(offset<=next)return {node,offset:Math.max(0,offset-total)};total=next}
  return last?{node:last,offset:last.nodeValue.length}:null;
}

function cabinetRangeForAnnotation(annotation){
  const block=document.querySelector(`.reader-block[data-block-index="${annotation.blockIndex}"]`);
  if(!block)return null;
  const text=block.textContent||'';
  let start=Number(annotation.startOffset||0),end=Number(annotation.endOffset||0);
  if(text.slice(start,end)!==annotation.quote){start=text.indexOf(annotation.quote);end=start+annotation.quote.length}
  if(start<0||end<=start)return null;
  const from=cabinetTextPoint(block,start),to=cabinetTextPoint(block,end);
  if(!from||!to)return null;
  const range=document.createRange();range.setStart(from.node,from.offset);range.setEnd(to.node,to.offset);return range;
}

function cabinetWrapRange(range,annotation){
  const mark=document.createElement('mark');mark.className='annotation-mark';mark.dataset.annotationId=annotation.id;mark.tabIndex=0;if(annotation.note)mark.title=annotation.note;
  try{mark.appendChild(range.extractContents());range.insertNode(mark);return mark}catch{return null}
}

function cabinetApplyAnnotations(articleId){
  cabinetArticleNotes(articleId).slice().sort((a,b)=>b.blockIndex-a.blockIndex||b.startOffset-a.startOffset).forEach(annotation=>{
    const range=cabinetRangeForAnnotation(annotation);if(range)cabinetWrapRange(range,annotation);
  });
  cabinetWireAnnotationMarks();
}

function cabinetWireAnnotationMarks(){
  document.querySelectorAll('.annotation-mark').forEach(mark=>{
    mark.onclick=event=>{event.stopPropagation();cabinetOpenExistingAnnotation(mark.dataset.annotationId,mark.getBoundingClientRect())};
    mark.onmouseenter=()=>{const item=cabinetAnnotations.find(annotation=>annotation.id===mark.dataset.annotationId);if(item?.note)cabinetShowTip(item.note,mark.getBoundingClientRect())};
    mark.onmouseleave=()=>cabinetHideTip();
  });
}

function cabinetRestoreProgress(article,jumpAnnotationId){
  const drawer=$('#reader');
  if(jumpAnnotationId){const mark=drawer.querySelector(`[data-annotation-id="${jumpAnnotationId}"]`);if(mark){mark.scrollIntoView({block:'center'});mark.focus();return}}
  const anchor=article.readingAnchor;
  if(anchor){const block=drawer.querySelector(`.reader-block[data-block-index="${anchor.blockIndex}"]`);if(block){drawer.scrollTop=Math.max(0,block.offsetTop-130);return}}
  if(article.progress>0)drawer.scrollTop=(drawer.scrollHeight-drawer.clientHeight)*article.progress;
}

function cabinetBindReader(article,source,jumpAnnotationId){
  $('#closeReader').onclick=closeReader;
  $('#readerSave').onclick=()=>{article.saved=!article.saved;persist();openReader(article.id,jumpAnnotationId);toast(article.saved?'已加入收藏':'已取消收藏')};
  $('#readerRead').onclick=()=>{article.read=!article.read;persist();openReader(article.id,jumpAnnotationId);toast(article.read?'已标为已读':'已标为未读')};
  const body=$('#readerBody');
  if(body){
    body.oncontextmenu=event=>cabinetHandleSelection(event,article.id);
    body.onmouseup=event=>{if(event.pointerType==='touch')cabinetHandleSelection(event,article.id)};
    body.querySelectorAll('.reader-content-image').forEach(image=>{
      const frame=image.closest('.reader-image-frame');
      const loaded=()=>image.classList.add('loaded');const failed=()=>frame?.classList.add('image-error');
      image.addEventListener('load',loaded,{once:true});image.addEventListener('error',failed,{once:true});
      if(image.complete)(image.naturalWidth?loaded:failed)();
    });
  }
  $('#reader').onscroll=()=>{
    const drawer=$('#reader'),denominator=drawer.scrollHeight-drawer.clientHeight;
    const progress=denominator>0?Math.min(1,Math.max(0,drawer.scrollTop/denominator)):0;
    article.progress=Math.max(article.progress||0,progress);
    if(article.progress>=.95)article.read=true;
    const blocks=[...drawer.querySelectorAll('.reader-block')];
    const current=blocks.find(block=>block.getBoundingClientRect().bottom>150)||blocks.at(-1);
    if(current)article.readingAnchor={blockIndex:Number(current.dataset.blockIndex||0)};
    const progressBar=$('#readerProgress');if(progressBar)progressBar.style.width=(article.progress*100)+'%';
    clearTimeout(cabinetProgressTimer);cabinetProgressTimer=setTimeout(()=>persist(),650);
  };
  requestAnimationFrame(()=>cabinetRestoreProgress(article,jumpAnnotationId));
}

openReader=async function(id,jumpAnnotationId=null){
  const article=state.articles.find(item=>item.id===id),source=src(article?.source);
  if(!article||!source)return;
  const contentState=cabinetArticleContentState(id);
  if(contentState==='failed'){window.open(article.url,'_blank','noopener');return}
  if(contentState!=='ready'){cabinetFetchArticleContent(article,{force:false});return}
  const intent=++cabinetReaderIntent;cabinetHideMenus();
  try{
    const response=await fetch(`/api/article-content?articleId=${encodeURIComponent(article.id)}`,{cache:'no-store'});
    const result=await response.json();
    if(intent!==cabinetReaderIntent)return;
    if(!response.ok||!result.ok||result.content.status!=='ready')throw new Error(result.error||'正文缓存不可用');
    cabinetActiveArticleId=id;
    cabinetActiveHtml=result.content.html;
    const safeHtml=cabinetSanitizeArticleHtml(cabinetActiveHtml);
    $('#reader').innerHTML=cabinetReaderHeader(article,source)+`<article class="reader-body reader-rich" id="readerBody">${safeHtml}</article>`;
    $('#reader').classList.add('show');$('#scrim').classList.add('show');document.body.style.overflow='hidden';
    cabinetApplyAnnotations(article.id);cabinetBindReader(article,source,jumpAnnotationId);
  }catch(error){
    if(intent!==cabinetReaderIntent)return;
    cabinetSetArticleContentState(id,'failed',error.message||'正文缓存不可用');
  }
};

closeReader=function(){
  cabinetReaderIntent++;
  if(!$('#reader').classList.contains('show'))return;
  clearTimeout(cabinetProgressTimer);persist();cabinetHideMenus();cabinetActiveArticleId=null;
  $('#reader').classList.remove('show');$('#scrim').classList.remove('show');document.body.style.overflow='';render();
};

function cabinetSelectionData(articleId){
  const selection=window.getSelection();if(!selection||selection.isCollapsed||!selection.rangeCount)return null;
  const range=selection.getRangeAt(0);const block=range.commonAncestorContainer.nodeType===Node.ELEMENT_NODE?range.commonAncestorContainer.closest?.('.reader-block'):range.commonAncestorContainer.parentElement?.closest('.reader-block');
  if(!block||!$('#readerBody')?.contains(block))return null;
  const quote=selection.toString().trim();if(!quote||quote.length>4000)return null;
  const before=document.createRange();before.selectNodeContents(block);before.setEnd(range.startContainer,range.startOffset);const startOffset=before.toString().length;
  const endOffset=startOffset+selection.toString().length;const text=block.textContent||'';
  const overlaps=cabinetArticleNotes(articleId).some(item=>item.blockIndex===Number(block.dataset.blockIndex)&&startOffset<item.endOffset&&endOffset>item.startOffset);
  if(overlaps){toast('这一段已有批注，可以点击原有划线编辑');return null}
  return {articleId,quote,prefix:text.slice(Math.max(0,startOffset-80),startOffset),suffix:text.slice(endOffset,endOffset+80),blockIndex:Number(block.dataset.blockIndex||0),startOffset,endOffset,range:range.cloneRange()};
}

function cabinetHandleSelection(event,articleId){
  const data=cabinetSelectionData(articleId);if(!data)return;
  event.preventDefault();cabinetPendingSelection=data;
  const rect=data.range.getBoundingClientRect();cabinetShowToolbar(rect);
}

function cabinetEnsureMenus(){
  if(!$('#annotationToolbar')){
    document.body.insertAdjacentHTML('beforeend','<div class="annotation-toolbar" id="annotationToolbar" hidden><button id="makeHighlight">划线</button><button id="makeNote">笔记</button></div><div class="annotation-popover" id="annotationPopover" hidden><textarea id="annotationText" placeholder="记一条笔记…"></textarea><div class="annotation-popover-actions"><button class="danger-note" id="deleteAnnotation" hidden>删除批注</button><button id="cancelAnnotation">取消</button><button class="primary" id="saveAnnotation">保存</button></div></div><div class="annotation-tip" id="annotationTip" hidden></div>');
    $('#makeHighlight').onclick=()=>cabinetCreateAnnotation('highlight');$('#makeNote').onclick=()=>cabinetOpenComposer();$('#cancelAnnotation').onclick=cabinetHideMenus;
  }
}

function cabinetPlace(element,rect,above=true){
  const x=Math.min(innerWidth-18,Math.max(18,rect.left+rect.width/2));
  const y=above?Math.max(48,rect.top-8):Math.min(innerHeight-18,rect.bottom+8);
  element.style.left=`${x}px`;element.style.top=`${y}px`;
}

function cabinetShowToolbar(rect){cabinetEnsureMenus();cabinetHideTip();const toolbar=$('#annotationToolbar');toolbar.hidden=false;cabinetPlace(toolbar,rect,true)}
function cabinetOpenComposer(existing=null,rect=null){
  cabinetEnsureMenus();$('#annotationToolbar').hidden=true;const popover=$('#annotationPopover');popover.hidden=false;popover.dataset.annotationId=existing?.id||'';$('#annotationText').value=existing?.note||'';$('#deleteAnnotation').hidden=!existing;
  const target=rect||cabinetPendingSelection?.range.getBoundingClientRect();cabinetPlace(popover,target||{left:innerWidth/2,width:0,bottom:80},false);
  $('#saveAnnotation').onclick=()=>existing?cabinetUpdateExisting(existing):cabinetCreateAnnotation('note',$('#annotationText').value);
  $('#deleteAnnotation').onclick=()=>existing&&cabinetRemoveExisting(existing);
  setTimeout(()=>$('#annotationText').focus(),20);
}
function cabinetHideMenus(){cabinetEnsureMenus();$('#annotationToolbar').hidden=true;$('#annotationPopover').hidden=true;cabinetHideTip();cabinetPendingSelection=null}

async function cabinetCreateAnnotation(kind,note=''){
  if(!cabinetPendingSelection)return;
  const data=cabinetPendingSelection;
  try{
    const saved=await cabinetSaveAnnotation({...data,range:undefined,kind,note});
    cabinetWrapRange(data.range,saved);cabinetWireAnnotationMarks();window.getSelection()?.removeAllRanges();cabinetHideMenus();toast(kind==='note'?'笔记已保存':'划线已保存');render();
  }catch(error){toast(error.message||'批注保存失败')}
}

function cabinetOpenExistingAnnotation(id,rect){const item=cabinetAnnotations.find(annotation=>annotation.id===id);if(item)cabinetOpenComposer(item,rect)}
async function cabinetUpdateExisting(item){
  try{const saved=await cabinetSaveAnnotation({...item,kind:$('#annotationText').value.trim()?'note':'highlight',note:$('#annotationText').value.trim()});const mark=document.querySelector(`[data-annotation-id="${saved.id}"]`);if(mark)mark.title=saved.note||'';cabinetHideMenus();toast('批注已更新');render()}catch(error){toast(error.message||'批注保存失败')}
}
async function cabinetRemoveExisting(item){
  try{await cabinetDeleteAnnotation(item.id);const mark=document.querySelector(`[data-annotation-id="${item.id}"]`);if(mark)mark.replaceWith(...mark.childNodes);cabinetHideMenus();toast('批注已删除');render()}catch(error){toast(error.message||'批注删除失败')}
}
function cabinetShowTip(text,rect){cabinetEnsureMenus();const tip=$('#annotationTip');tip.textContent=text;tip.hidden=false;tip.style.left=`${Math.min(innerWidth-360,Math.max(12,rect.left))}px`;tip.style.top=`${Math.max(12,rect.top-56)}px`}
function cabinetHideTip(){const tip=$('#annotationTip');if(tip)tip.hidden=true}

document.addEventListener('mousedown',event=>{if(!event.target.closest?.('#annotationToolbar,#annotationPopover,.annotation-mark'))cabinetHideMenus()});
setTimeout(cabinetLoadAnnotations,0);
