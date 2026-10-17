/** Styled popovers retain native form values and change events, including dynamically rendered forms. */
export function installControls(){
  const controllers=new WeakMap(),entries=new Set();let counter=0,active=null,index=0,items=[],typeBuffer='',typeTimer;
  const popup=document.createElement('div');popup.id='control-options';popup.className='control-options';popup.role='listbox';popup.hidden=true;document.body.append(popup);
  const labelOf=el=>el.getAttribute('aria-label')||[...(el.labels?.[0]?.childNodes||[])].filter(n=>n.nodeType===3).map(n=>n.textContent).join('').trim()||el.getAttribute('name')||'选择';
  function close(restore=false){const previous=active;active=null;popup.hidden=true;popup.replaceChildren();if(previous){previous.trigger.setAttribute('aria-expanded','false');previous.trigger.removeAttribute('aria-activedescendant');if(restore&&previous.trigger.isConnected)previous.trigger.focus({preventScroll:true});}}
  function choices(c){if(c.select)return [...c.native.options].filter(o=>!o.hidden).map(o=>({value:o.value,label:o.label||o.textContent,disabled:o.disabled||o.parentElement?.disabled}));const list=document.getElementById(c.list);return [...(list?.options||[])].map(o=>({value:o.value,label:o.label||o.value,disabled:false})).filter(o=>!c.native.value||o.label.toLocaleLowerCase().includes(c.native.value.toLocaleLowerCase())||o.value.toLocaleLowerCase().includes(c.native.value.toLocaleLowerCase()));}
  function place(){if(!active)return;const r=active.trigger.getBoundingClientRect(),width=Math.min(Math.max(r.width,180),innerWidth-24),roomBelow=innerHeight-r.bottom-14,roomAbove=r.top-14,above=roomBelow<180&&roomAbove>roomBelow;popup.style.width=`${width}px`;popup.style.left=`${Math.min(Math.max(12,r.left),innerWidth-width-12)}px`;popup.style.maxHeight=`${Math.min(280,Math.max(100,above?roomAbove:roomBelow))}px`;popup.style.top=above?'auto':`${r.bottom+6}px`;popup.style.bottom=above?`${innerHeight-r.top+6}px`:'auto';}
  function mark(){if(!active)return;for(const option of popup.children){const chosen=Number(option.dataset.index)===index;option.classList.toggle('highlighted',chosen);if(chosen){active.trigger.setAttribute('aria-activedescendant',option.id);option.scrollIntoView({block:'nearest'});}}}
  function open(c,fromKey=false){
    if(c.native.disabled||c.native.closest('fieldset:disabled'))return;close();items=choices(c);if(!items.length)return;active=c;
    index=Math.max(0,items.findIndex(o=>o.value===c.native.value&&!o.disabled));if(items[index]?.disabled)index=items.findIndex(o=>!o.disabled);if(index<0){close();return;}
    popup.setAttribute('aria-label',c.label);popup.hidden=false;c.trigger.setAttribute('aria-expanded','true');
    for(let i=0;i<items.length;i++){const o=items[i],option=document.createElement('div');option.id=`control-option-${i}`;option.role='option';option.dataset.index=i;option.className='control-option';option.setAttribute('aria-selected',String(o.value===c.native.value));option.setAttribute('aria-disabled',String(!!o.disabled));const text=document.createElement('span');text.textContent=o.label;option.append(text);if(o.value===c.native.value){const check=document.createElement('span');check.className='control-check';check.textContent='✓';option.append(check);}option.onpointermove=()=>{if(!o.disabled&&index!==i){index=i;mark();}};option.onpointerdown=e=>{e.preventDefault();if(!o.disabled)choose(i);};popup.append(option);}
    place();mark();if(fromKey)c.trigger.focus({preventScroll:true});
  }
  function choose(i){
    if(!active||items[i]?.disabled)return;const c=active,value=items[i].value,formId=c.native.form?.id,id=c.native.id,name=c.native.name;
    close();c.native.value=value;c.sync();
    c.picking=true;if(!c.select)c.native.dispatchEvent(new Event('input',{bubbles:true}));c.native.dispatchEvent(new Event('change',{bubbles:true}));c.picking=false;
    requestAnimationFrame(()=>{if(c.trigger.isConnected)c.trigger.focus({preventScroll:true});else{const root=formId?document.getElementById(formId):document;const replacement=id?document.getElementById(id):[...root?.querySelectorAll('select')||[]].find(s=>s.name===name);controllers.get(replacement)?.trigger.focus({preventScroll:true});}});
  }
  function keys(c,e){
    const opened=active===c;
    if(['ArrowDown','ArrowUp','Home','End'].includes(e.key)&&(c.select||opened||e.key.startsWith('Arrow'))){
      e.preventDefault();if(!opened){open(c,true);return;}let next=index;
      if(e.key==='Home')next=0;else if(e.key==='End')next=items.length-1;else next=(index+(e.key==='ArrowDown'?1:-1)+items.length)%items.length;
      const step=e.key==='ArrowUp'||e.key==='End'?-1:1;for(let count=0;count<items.length&&items[next]?.disabled;count++)next=(next+step+items.length)%items.length;index=next;mark();
    }else if((e.key==='Enter'||e.key===' ')&&(c.select||opened)){e.preventDefault();if(opened)choose(index);else open(c,true);}
    else if(e.key==='Escape'&&opened){e.preventDefault();e.stopPropagation();close(true);}
    else if(e.key==='Tab'&&opened)close();
    else if(c.select&&e.key.length===1&&!e.ctrlKey&&!e.metaKey&&!e.altKey){e.preventDefault();clearTimeout(typeTimer);typeBuffer+=e.key.toLocaleLowerCase();typeTimer=setTimeout(()=>typeBuffer='',650);if(!opened)open(c,true);const match=items.findIndex(o=>!o.disabled&&o.label.toLocaleLowerCase().startsWith(typeBuffer));if(match>=0){index=match;mark();}}
  }
  function enhance(root){
    if(!(root instanceof Element||root===document))return;
    const candidates=[...(root.matches?.('select,input[list]')?[root]:[]),...root.querySelectorAll('select,input[list]')];
    for(const native of candidates){
      if(controllers.has(native))continue;
      const isSelect=native.tagName==='SELECT',label=labelOf(native),c={native,select:isSelect,label,trigger:native,list:native.getAttribute('list')};
      if(isSelect){
        const wrap=document.createElement('span');wrap.className='styled-select';native.before(wrap);wrap.append(native);
        const trigger=document.createElement('button');trigger.type='button';trigger.className='select-trigger';trigger.id=`select-trigger-${++counter}`;trigger.setAttribute('role','combobox');trigger.setAttribute('aria-label',label);trigger.setAttribute('aria-haspopup','listbox');trigger.setAttribute('aria-controls',popup.id);trigger.setAttribute('aria-expanded','false');
        const text=document.createElement('span');text.className='select-value';trigger.append(text);wrap.append(trigger);native.classList.add('native-select');native.setAttribute('aria-hidden','true');native.tabIndex=-1;c.trigger=trigger;
        c.sync=()=>{if(!native.isConnected)return;const value=native.selectedOptions[0]?.label||native.selectedOptions[0]?.textContent||'请选择';if(text.textContent!==value)text.textContent=value;const disabled=native.disabled||!!native.closest('fieldset:disabled');if(trigger.disabled!==disabled)trigger.disabled=disabled;if(trigger.disabled&&active===c)close();};
        trigger.onclick=e=>{e.preventDefault();if(active===c)close();else open(c);};native.addEventListener('change',c.sync);native.addEventListener('invalid',e=>{e.preventDefault();trigger.focus();trigger.setAttribute('aria-invalid','true');});
      }else{
        native.removeAttribute('list');native.dataset.suggestionList=c.list;native.setAttribute('role','combobox');native.setAttribute('aria-autocomplete','list');native.setAttribute('aria-controls',popup.id);native.setAttribute('aria-expanded','false');c.sync=()=>{};native.addEventListener('input',()=>{if(!c.picking)open(c);});native.addEventListener('focus',()=>{if(!c.picking)open(c);});native.addEventListener('blur',()=>{if(active===c)close();});
      }
      c.trigger.addEventListener('keydown',e=>keys(c,e));controllers.set(native,c);entries.add(c);c.sync();native.dataset.styledControl='true';
    }
  }
  document.addEventListener('pointerdown',e=>{if(active&&!popup.contains(e.target)&&!active.trigger.contains(e.target))close();},true);
  document.addEventListener('keydown',e=>{if(e.key==='Escape'&&active){e.preventDefault();e.stopImmediatePropagation();close(true);}},true);
  document.addEventListener('scroll',e=>{if(active&&e.target!==popup&&!popup.contains(e.target))close();},true);
  addEventListener('resize',()=>close());
  new MutationObserver(records=>{
    for(const c of entries)if(!c.native.isConnected){if(active===c)close();entries.delete(c);}
    for(const record of records){
      if(record.target instanceof Element&&record.target.closest('#control-options'))continue;
      if(record.type==='attributes'){for(const c of entries)c.sync();continue;}
      const select=record.target instanceof Element?record.target.closest('select'):null;if(select)controllers.get(select)?.sync();
      if(active&&!active.select&&record.target instanceof Element&&record.target.closest('datalist')?.id===active.list)open(active);
      for(const added of record.addedNodes)enhance(added);
    }
  }).observe(document.body,{childList:true,subtree:true,attributes:true,attributeFilter:['disabled']});
  enhance(document);document.body.dataset.controlsTheme='nebula';
}
