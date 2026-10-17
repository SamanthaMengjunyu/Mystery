const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const countryNames={CN:'中国',TW:'台湾',HK:'香港',MO:'澳门',US:'美国',GB:'英国',JP:'日本',AU:'澳大利亚',CA:'加拿大',IN:'印度',FR:'法国',DE:'德国',SG:'新加坡',NZ:'新西兰',KR:'韩国'};
export const placeNames=target=>target==='current'?{name:'current_place',lat:'current_latitude',lon:'current_longitude',zone:'current_tz_name',id:'current_place_id',kind:'current_place_kind'}:{name:'birth_place',lat:'latitude',lon:'longitude',zone:'tz_name',id:'birth_place_id',kind:'birth_place_kind'};
export function placeFields(p={},target='birth'){
  const n=placeNames(target),birth=target==='birth';
  return `<div class="place-field" data-place-field="${target}"><label>${birth?'出生地':'现居地'}<input name="${n.name}" value="${esc(p[n.name]||'')}" maxlength="200" ${birth?'required':''} placeholder="城市、省份、拼音或首字母，如湖南 / changsha / cs"></label>${[n.lat,n.lon,n.zone,n.id,n.kind].map(k=>`<input type="hidden" name="${k}" value="${esc(p[k]??'')}">`).join('')}<div class="place-auto-zone" data-place-zone="${target}" role="status">${p[n.zone]?'时区已自动匹配 · '+esc(p[n.zone]):'选择地点后自动匹配时区'}</div><p class="place-precision" data-place-precision="${target}">${p[n.kind]==='province'?'省域参考点 · 地名变更或不确定城市时可使用省份。':'支持中文、全拼、首字母及轻微错拼。请从候选中确认地点。'}</p></div>`;
}
export function applyPlace(form,place,target='birth'){
  const n=placeNames(target),field=k=>form.querySelector(`[name="${k}"]`);
  for(const [k,value] of [[n.name,place.display_name||place.name],[n.lat,Number(place.latitude).toFixed(5)],[n.lon,Number(place.longitude).toFixed(5)],[n.zone,place.tz_name],[n.id,place.id||''],[n.kind,place.kind||'city']])if(field(k))field(k).value=value;
  field(n.name)?.setCustomValidity('');updatePlaceStatus(form,target);
}
export function updatePlaceStatus(form,target='birth'){
  const n=placeNames(target),value=k=>form.querySelector(`[name="${k}"]`)?.value||'';
  const zone=form.querySelector(`[data-place-zone="${target}"]`),precision=form.querySelector(`[data-place-precision="${target}"]`);
  if(zone)zone.textContent=value(n.zone)?'时区已自动匹配 · '+value(n.zone):'选择地点后自动匹配时区';
  if(precision)precision.textContent=value(n.kind)==='province'?'省域参考点 · 采用该省的参考坐标；有具体城市时可进一步选择。':'地点与时区自动关联，历史夏令时按出生日期计算。';
}
export function mountPlaceSearch(form,{api,target='birth',onChoose=()=>{},onInvalidate=()=>{},onError=()=>{}}){
  const n=placeNames(target),input=form.querySelector(`[name="${n.name}"]`);if(!input)return null;
  const results=document.createElement('div');results.className='place-results';results.hidden=true;results.setAttribute('role','listbox');results.setAttribute('aria-label',target==='birth'?'出生地候选':'现居地候选');input.after(results);
  input.autocomplete='off';input.setAttribute('aria-autocomplete','list');input.setAttribute('aria-expanded','false');
  let ticket=0,pending,disposed=false;
  const cancel=()=>{clearTimeout(pending);ticket++;results.hidden=true;input.setAttribute('aria-expanded','false');};
  function choose(p){cancel();applyPlace(form,p,target);onChoose(p,target);}
  const search=()=>{
    cancel();for(const k of [n.lat,n.lon,n.zone,n.id,n.kind]){const f=form.querySelector(`[name="${k}"]`);if(f)f.value='';}
    input.setCustomValidity('');updatePlaceStatus(form,target);onInvalidate(target);
    const query=input.value.trim(),id=ticket;if(!query)return;
    pending=setTimeout(async()=>{try{const places=await api('search-places',{query});if(disposed||id!==ticket)return;results.replaceChildren();
      for(const p of places){const b=document.createElement('button');b.type='button';b.setAttribute('role','option');b.setAttribute('aria-selected','false');const title=document.createElement('b');title.textContent=p.display_name||p.name;const detail=document.createElement('small');detail.textContent=[p.kind==='province'?'省份 · 省域参考点':p.region_name||p.region,countryNames[p.country]||p.country].filter(Boolean).join(' · ');b.append(title,detail);b.onclick=()=>choose(p);b.onkeydown=e=>{if(e.key==='ArrowDown'){e.preventDefault();b.nextElementSibling?.focus();}if(e.key==='ArrowUp'){e.preventDefault();b.previousElementSibling?.focus();}if(e.key==='Escape'){e.preventDefault();e.stopPropagation();cancel();input.focus();}};results.append(b);}
      if(!places.length){const p=document.createElement('p');p.textContent='没有找到这个地名，可输入所在省份，或尝试附近城市与拼音。';results.append(p);}
      results.hidden=false;input.setAttribute('aria-expanded','true');
    }catch(e){if(!disposed&&id===ticket)onError(e);}},180);
  };
  const keys=e=>{if(e.key==='ArrowDown'&&!results.hidden){e.preventDefault();results.querySelector('button')?.focus();}if(e.key==='Enter'){e.preventDefault();if(!results.hidden)results.querySelector('button')?.click();}if(e.key==='Escape'&&!results.hidden){e.preventDefault();e.stopPropagation();cancel();}};
  input.addEventListener('input',search);input.addEventListener('keydown',keys);
  return {cancel,choose,validate(){const value=k=>form.querySelector(`[name="${k}"]`)?.value||'';if((target==='birth'||input.value.trim())&&(!value(n.lat)||!value(n.lon)||!value(n.zone))){input.setCustomValidity('请搜索并选择'+(target==='birth'?'出生地':'现居地')+'候选地点');input.reportValidity();input.focus();return false;}return true;},dispose(){disposed=true;cancel();input.removeEventListener('input',search);input.removeEventListener('keydown',keys);results.remove();}};
}
