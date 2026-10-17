import {mountWorldMap} from './world-map.js';
import {personColor} from './person-colors.js';
import {applyPlace,mountPlaceSearch,updatePlaceStatus} from './place-search.js';

export function mountPlacePicker(form,host,{api,onError,prefs}){
  let mode='birth',disposed=false,version=0;
  const field=name=>form.querySelector(`[name=${name}]`),hint=form.querySelector('#place-feedback'),mapResults=form.querySelector('#map-place-results');
  const coordinates=target=>target==='birth'?['latitude','longitude']:['current_latitude','current_longitude'];
  const placeName=target=>target==='birth'?'birth_place':'current_place';
  const valid=name=>field(name).value.trim()!==''&&Number.isFinite(Number(field(name).value));
  const map=mountWorldMap(host,{mini:true,reduced:prefs.reduced,selectable:true,onPoint:pickPoint,onSelect:()=>{},onError});
  const searches=[];
  function markers(focus=false){const pins=[];for(const target of ['birth','current']){const [lat,lon]=coordinates(target);if(valid(lat)&&valid(lon))pins.push({id:'person',name:target==='birth'?'出生地':'现居地',kind:target,latitude:Number(field(lat).value),longitude:Number(field(lon).value),color:personColor({color:field('color').value})});}map.updatePlaces(pins);const pin=pins.find(p=>p.kind===mode);if(focus&&pin)map.focus(pin.latitude,pin.longitude);}
  function updateMode(){for(const b of form.querySelectorAll('[data-place-mode]'))b.setAttribute('aria-pressed',String(b.dataset.placeMode===mode));if(mode==='current')form.querySelector('#birth-current-place').open=true;}
  function choose(place,target){version++;mode=target;for(const s of searches)s.cancel();applyPlace(form,place,target);hint.textContent='';mapResults.hidden=true;updateMode();markers(true);}
  function option(place,target){const b=document.createElement('button');b.type='button';b.setAttribute('role','option');b.setAttribute('aria-selected','false');b.textContent=`${place.display_name||place.name} · ${place.region_name||place.region} · ${place.kind==='province'?'省域参考点':place.country}${place.distance_km!==undefined?' · 距点位约 '+Math.round(place.distance_km)+' km':''}`;b.onclick=()=>choose(place,target);b.onkeydown=e=>{if(e.key==='ArrowDown'){e.preventDefault();b.nextElementSibling?.focus();}if(e.key==='ArrowUp'){e.preventDefault();b.previousElementSibling?.focus();}if(e.key==='Escape'){e.preventDefault();e.stopPropagation();b.parentElement.hidden=true;field(placeName(target)).focus();}};return b;}
  async function pickPoint(point){const id=++version,target=mode;hint.textContent='正在查找附近城市，请选择实际地点…';mapResults.hidden=true;try{const places=await api('nearby-places',point);if(disposed||id!==version)return;mapResults.replaceChildren();const title=document.createElement('p');title.textContent=places.length?`选择附近城市作为${target==='birth'?'出生地':'现居地'}`:'附近未找到城市，请旋转地球重新选择，或输入城市名称搜索。';mapResults.append(title);for(const p of places)mapResults.append(option(p,target));mapResults.hidden=false;hint.textContent='地图点位只用于查找候选；选择城市后才会更新地点和时区。';}catch(e){if(!disposed&&id===version){hint.textContent='地点查询失败，请重试或搜索城市名。';onError(e);}}}
  for(const target of ['birth','current'])searches.push(mountPlaceSearch(form,{api,target,onChoose:choose,onInvalidate:()=>{version++;mode=target;updateMode();mapResults.hidden=true;markers();hint.textContent='从候选中确认城市或省份，时区会自动匹配。';},onError}));
  for(const b of form.querySelectorAll('[data-quick-place]'))b.onclick=()=>{const input=field('birth_place');input.value=b.dataset.quickPlace;input.dispatchEvent(new Event('input',{bubbles:true}));};
  for(const b of form.querySelectorAll('[data-place-mode]'))b.onclick=()=>{version++;mapResults.hidden=true;mode=b.dataset.placeMode;updateMode();markers(true);hint.textContent=mode==='birth'?'点击地球后选择附近城市作为出生地。':'点击地球后选择附近城市作为现居地。';};
  form.querySelector('#clear-current-place').onclick=()=>{version++;for(const s of searches)s.cancel();for(const n of ['current_place','current_latitude','current_longitude','current_tz_name','current_place_id','current_place_kind'])field(n).value='';field('current_place').setCustomValidity('');mapResults.hidden=true;updatePlaceStatus(form,'current');markers();hint.textContent='现居地已移除，保存后生效。';};
  function validate(){for(const target of ['birth','current']){const [lat,lon]=coordinates(target),input=field(placeName(target));if((target==='birth'||input.value.trim())&&(!valid(lat)||!valid(lon))){if(target==='current')form.querySelector('#birth-current-place').open=true;input.setCustomValidity(`请搜索并选择${target==='birth'?'出生地':'现居地'}候选地点`);input.reportValidity();input.focus();return false;}}return true;}
  updateMode();markers(true);
  return {validate,pickPoint,refreshColor:()=>markers(),dispose(){disposed=true;version++;for(const s of searches)s.dispose();map.dispose();}};
}
