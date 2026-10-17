import { createTransitions } from './transitions.js';
import { resolvePreferences } from './preferences.js';
import { installControls } from './controls.js';
import { mountRitual } from './rituals.js';
import { tarotImagePath } from './tarot-art.js';
import {createDeviceLocation,deviceTimeZone} from './device-location.js';
import {createMusicPlayer} from './music-player.js';
import {createFocusMode} from './focus-mode.js';
import {mountBirthdayReminders} from './birthday-reminders.js';
import {atlasFilters,atlasPins} from './atlas-filters.js';
import { mountBirthdayAtlas } from './birthday-atlas.js';
import { mountPlacePicker } from './place-picker.js';
import {personColor,personPalette,mountPersonColor} from './person-colors.js';
import {placeFields,mountPlaceSearch} from './place-search.js';
import {renderNatalChart,mountNatalInteractions,mountNatalWorkspace} from './natal-charts.js';
installControls();
const $=(s,root=document)=>root.querySelector(s);
const $$=(s,root=document)=>[...root.querySelectorAll(s)];
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const token=$('meta[name=mystery-token]').content;
async function api(action,p={}){const r=await fetch('/api/'+action,{method:'POST',headers:{'Content-Type':'application/json','X-Mystery-Token':token},body:JSON.stringify(p)});const d=await r.json();if(!d.ok)throw Error(d.error||'本地服务未响应');return d.data;}
let toastTimer,prefsSave=Promise.resolve();
function toast(message,error=false){$('#toast').textContent=message;$('#toast').className='visible'+(error?' error':'');clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('#toast').className='',error?9000:4000);}
const meta={
  bazi:['四柱八字','FOUR PILLARS','以年月日时，读懂命局的结构与节律。','☷'],
  ziwei:['紫微斗数','ZI WEI DOU SHU','十二宫星曜、本命四化与人生运限。','✧'],
  astro:['西方占星','WESTERN ASTROLOGY','从日月升到相位，展开你的出生星图。','☉'],
  jyotish:['印度占星','JYOTISH','Lahiri 恒星黄道，九曜、月宿与大运。','☽'],
  liuyao:['六爻','SIX LINES','六次投掷，观察一件事的动与变。','☰'],
  meihua:['梅花易数','PLUM BLOSSOM','从数字与时间取象，察看本互变与体用。','❋'],
  tarot:['塔罗','TAROT','安静地选牌，让当下的线索逐一显现。','◇'],
  lenormand:['雷诺曼','LENORMAND','把三张或五张牌，连成一条清晰的线索。','⌘'],
  answers:['答案之书','BOOK OF ANSWERS','把问题留在心里，在一页文字里停留。','✦'],
  solar:['真太阳时','TRUE SOLAR TIME','查看出生地经度与均时差带来的时间校正。','◷']
};
const chartModules=['bazi','ziwei','astro','jyotish'];
const oracleModules=['liuyao','meihua','tarot','lenormand','answers'];
let catalog,scene,currentModule=null,currentRecord=null,currentTab='overview',samples=[],sampleStart=0,aiJob=null;
let storedPrefs;try{storedPrefs=JSON.parse(localStorage.getItem('mystery-preferences')||'{}');}catch{storedPrefs={};}
let prefs=resolvePreferences(storedPrefs);
let aiConfig={api_base:prefs.api_base||'',model:prefs.model||'',api_key:'',lite_model:'',fallback:false};
const drafts={};
let birthdays=[],birthOnboarding=false,birthReturnFocus=null;
let ritual=null,atlasPage=null,modalCleanup=null,deviceLocation=null,player=null,focusMode=null,reminders=null,natalWorkspace=null,chartPlaceSearch=null;
function clearRitual(){chartPlaceSearch?.dispose();chartPlaceSearch=null;natalWorkspace?.dispose();natalWorkspace=null;atlasPage?.dispose();atlasPage=null;document.body.classList.remove('birthday-atlas-open');ritual?.dispose();ritual=null;}
const transitions=createTransitions($('#transition-surface'));
function travel(action,returning=false){scene?.cancelEntry();transitions.run(action,{reduced:prefs.reduced,returning});}
function updateExploration({progress}){
  $('#home').classList.toggle('exploring',progress>.26);
  $('#home').style.setProperty('--explore-progress',progress);
  const dismissed=progress>.72||(progress>=.64&&$('#scroll-invitation').classList.contains('dismissed'));
  $('#scroll-invitation').classList.toggle('dismissed',dismissed);
  $('#scroll-invitation').tabIndex=dismissed?-1:0;
  $('#scroll-invitation').setAttribute('aria-hidden',String(dismissed));
  $('#wheel-direction').textContent=progress>.7?'向上滚动 · 退回远景':'向下滚动 · 展开';
}
function persistPrefs(){const snapshot=JSON.stringify(prefs);localStorage.setItem('mystery-preferences',snapshot);document.body.classList.toggle('reduced',prefs.reduced);scene?.preferences(prefs);$('#pin-nav').setAttribute('aria-pressed',String(prefs.pinned));prefsSave=prefsSave.then(()=>api('preferences',JSON.parse(snapshot))).catch(e=>toast('偏好保存失败：'+e.message,true));}
function localNow(){const d=new Date();return new Date(d-d.getTimezoneOffset()*60000).toISOString().slice(0,16);}
function input(name,label,type='text',value='',extra=''){return `<label>${label}<input name="${name}" type="${type}" value="${esc(value)}" ${extra}></label>`;}
function select(name,label,options,value){return `<label>${label}<select name="${name}">${Object.entries(options).map(([k,v])=>`<option value="${esc(k)}"${String(value)===k?' selected':''}>${esc(v)}</option>`).join('')}</select></label>`;}
function check(name,label,value=false){return `<label class="check"><input name="${name}" type="checkbox"${value?' checked':''}>${label}</label>`;}
function dateFields(p,label='出生日期与时间'){return `${input('datetime',label,'datetime-local',p.datetime||'', 'required min="1900-01-01T00:00" max="2100-12-31T23:59"')}<div class="field-row">${input('tz_name','当地 IANA 时区','text',p.tz_name||'Asia/Shanghai','required list="timezones"')}${select('fold','重复时刻（夏令时）',{'':'自动校验','0':'第一次出现','1':'第二次出现'},p.fold??'')}</div><datalist id="timezones">${['Asia/Shanghai','Asia/Hong_Kong','Asia/Tokyo','Asia/Kolkata','America/New_York','America/Los_Angeles','Europe/London','Europe/Paris','Australia/Sydney','Etc/GMT-8','UTC'].map(t=>`<option value="${t}">`).join('')}</datalist>`;}
function fieldsFor(module,p){
  let h='';
  if(chartModules.includes(module)||module==='solar'){
    h+=input('label','记录名称（可选）','text',p.label||'','maxlength="120" placeholder="为这份命盘命名"');
    h+=input('datetime','出生日期与时间','datetime-local',p.datetime||'','required min="1900-01-01T00:00" max="2100-12-31T23:59"')+placeFields(p)+`<details><summary>出生时间规则</summary><div class="fields">${select('fold','重复时刻（夏令时）',{'':'自动校验','0':'第一次出现','1':'第二次出现'},p.fold??'')}</div></details>`;
    if(['bazi','ziwei'].includes(module))h+=select('gender','运限规则使用的性别',{'男':'男','女':'女'},p.gender||'男')+check('use_true_solar','启用真太阳时校正',p.use_true_solar);
    if(module==='bazi')h+=`<details><summary>排盘规则</summary><div class="fields">${select('sect','晚子时换日规则',{'2':'晚子时归当日','1':'晚子时归次日'},p.sect||2)}</div></details>`;
    if(module==='ziwei')h+=`<details><summary>四化与运限规则</summary><div class="fields">${input('target_year','流年年份（可留空）','number',p.target_year||'','min="1900" max="2200" placeholder="填写后生成流年"')}${select('day_divide','晚子时换日',{'forward':'归次日','current':'归当日'},p.day_divide||'forward')}${select('year_divide','换年规则',{'normal':'农历正月初一','exact':'立春'},p.year_divide||'normal')}${check('fix_leap','闰月前后半月调整',p.fix_leap!==false)}</div></details>`;
    if(module==='astro')h+=select('house_system','宫制',{'P':'Placidus 普拉西德','W':'Whole Sign 整宫','K':'Koch 科赫','E':'Equal 等宫'},p.house_system||'P');
    if(module==='jyotish')h+=`<details><summary>节点与大运配置</summary><div class="fields">${select('node_mode','月球节点',{'mean':'平均节点','true':'真节点'},p.node_mode||'mean')}${select('dasha_year','大运年长',{'sidereal':'恒星年 · 365.25636 天','julian':'儒略年 · 365.25 天','savana':'Savana · 360 天'},p.dasha_year||'sidereal')}</div></details>`;
    return h;
  }
  h+=`<label>你想探询什么<textarea name="question" maxlength="4000" placeholder="让问题清晰一些，也可以只放在心里。">${esc(p.question||'')}</textarea></label>`;
  if(module==='tarot'||module==='lenormand'){
    if(module==='lenormand')h+=select('method','取牌方式',{'draw':'洗牌后亲自选牌','manual':'录入实体牌'},p.method||'draw');
    h+=select('spread','牌阵',module==='tarot'?{single:'单张指引',three:'三张 · 过去 / 现在 / 未来',celtic:'凯尔特十字 · 十张'}:{three:'三张线性牌阵',five:'五张线性牌阵'},p.spread||'three');
    if(module==='tarot')h+=check('reversals','启用正逆位',p.reversals!==false);
    if(module==='lenormand'&&p.method==='manual')h+=input('card_ids','牌编号（1–36，按从左到右顺序）','text',(p.card_ids||[]).join(', '),'required placeholder="例如：27, 25, 24"')+`<details><summary>查看 36 张牌编号</summary><p class="subtle">${catalog.lenormand_deck.map(c=>`${c.id} ${esc(c.cn)}`).join('　')}</p></details>`;
    return h;
  }
  if(module==='liuyao'){
    h+=select('method','起卦方式',{'draw':'三钱法 · 亲手逐次投掷','manual':'录入实体投掷'},p.method||'draw');
    if(p.method==='manual')h+=input('tosses','从初爻到上爻（自下而上）','text',(p.tosses||[7,8,7,8,7,8]).join(', '),'required placeholder="6, 7, 8, 9, 7, 8"')+'<p class="subtle">6 老阴 · 7 少阳 · 8 少阴 · 9 老阳</p>';
    h+=select('category','问事主题',{zonghe:'综合',career:'事业',wealth:'财运',love:'感情',health:'健康',study:'学业',children:'子女',travel:'出行'},p.category||'zonghe');
    h+=`<details><summary>问事时刻与时区</summary><div class="fields">${dateFields({...p,datetime:p.datetime||localNow()},'本次问事的当地时刻')}</div></details>`;
  }
  if(module==='meihua'){
    h+=select('method','起卦方式',{numbers:'报数起卦',time:'当地时间起卦',lunar:'农历年月日时数',direct:'直接输入卦数'},p.method||'numbers');
    const method=p.method||'numbers';
    if(method==='numbers')h+=`<div class="field-row">${input('first','第一数','number',p.first??'','min="0" max="2147483647" required')}${input('second','第二数','number',p.second??'','min="0" max="2147483647" required')}</div>${input('third','第三数（可留空）','number',p.third??'','min="0" max="2147483647" placeholder="留空则使用两数之和定动爻"')}${select('hour_number','两数法附加时数（可选）',{'':'不附加时数',...Object.fromEntries(Array.from({length:12},(_,i)=>[i+1,`${i+1}`]))},p.hour_number||'')}`;
    if(method==='time')h+=dateFields({...p,datetime:p.datetime||localNow()},'明确的起卦时刻');
    if(method==='lunar'){const branches=Object.fromEntries([... '子丑寅卯辰巳午未申酉戌亥'].map((b,i)=>[i+1,b]));h+=`<div class="field-row">${select('year_branch','年支',branches,p.year_branch||1)}${select('hour_branch','时支',branches,p.hour_branch||1)}</div><div class="field-row">${input('lunar_month','农历月数','number',p.lunar_month||1,'min="1" max="12" required')}${input('lunar_day','农历日数','number',p.lunar_day||1,'min="1" max="30" required')}</div>${check('leap_month','闰月',p.leap_month)}`;}
    if(method==='direct')h+=`<div class="field-row">${input('upper','上卦先天数','number',p.upper||1,'min="1" max="8" required')}${input('lower','下卦先天数','number',p.lower||1,'min="1" max="8" required')}</div>${input('moving_line','动爻（自下而上）','number',p.moving_line||1,'min="1" max="6" required')}<p class="subtle">乾1 · 兑2 · 离3 · 震4 · 巽5 · 坎6 · 艮7 · 坤8</p>`;
    h+=`<details><summary>互卦规则</summary><div class="fields">${select('nuclear','纯乾纯坤互卦',{'classic':'乾坤无互，互其变卦','standard':'始终取本卦中爻'},p.nuclear||'classic')}</div></details>`;
  }
  return h;
}
function captureForm(){const f=$('#calculation-form');if(!f)return {};const data=Object.fromEntries(new FormData(f));$$('input[type=checkbox]',f).forEach(i=>data[i.name]=i.checked);for(const k of ['tosses','card_ids'])if(typeof data[k]==='string')data[k]=data[k].split(/[,，\s]+/).filter(Boolean).map(Number);return data;}
function rememberDraft(){if(currentModule&&$('#calculation-form'))drafts[currentModule]=$('#calculation-fields')?.disabled&&ritual?ritual.snapshot():captureForm();}
function setWorkspace(nav){clearRitual();$('#home').classList.add('hidden');$('#workspace').classList.remove('hidden');$('#return-nebula').classList.remove('hidden');$$('[data-nav]').forEach(b=>b.classList.toggle('active',b.dataset.nav===nav));wakeNav();}
function home(instant=false){if(instant!==true)return travel(()=>home(true),true);rememberDraft();clearRitual();currentModule=null;currentRecord=null;$('#workspace').classList.add('hidden');$('#return-nebula').classList.add('hidden');$('#home').classList.remove('hidden','exploring');$$('[data-nav]').forEach(b=>b.classList.toggle('active',b.dataset.nav==='home'));scene?.setMode('home');$('#brand-home').focus({preventScroll:true});}
function openModule(module,record=null,instant=false){
  if(instant!==true&&(!currentModule||currentModule!==module||record))return travel(()=>openModule(module,record,true));
  rememberDraft();samples=[];sampleStart=performance.now();currentModule=module;currentRecord=record;currentTab='overview';
  const m=meta[module],p=record?.inputs||drafts[module]||((chartModules.includes(module)||module==='solar')?birthdayInputs(birthdays.find(b=>b.id===prefs.active_birth_id)):{});
  setWorkspace(chartModules.includes(module)||module==='solar'?'charts':'oracles');scene?.setMode('module',module);
  $('#workspace').innerHTML=`<div class="space-layout"><section class="glass input-panel"><button class="back-link" id="back-home">← 返回星云</button><div class="section-kicker">${m[1]}</div><h2>${m[0]}</h2><p class="subtle">${m[2]}</p><form id="calculation-form"><fieldset id="calculation-fields" style="border:0;padding:0;margin:0;min-width:0"><div class="fields">${fieldsFor(module,p)}</div></fieldset><button class="primary full" id="calculate" type="submit">${module==='answers'?'翻开一页':module==='solar'?'校正时间':['tarot','lenormand'].includes(module)&&p.method!=='manual'?'开始洗牌':chartModules.includes(module)?'展开命盘':'开始起卦'} <span>↗</span></button></form><p class="subtle" style="margin:18px 0 0;font-size:10px">结果保存在本机「星迹」中。${module==='answers'?'197 页，每页对应一条固定答案。':['tarot','lenormand','liuyao'].includes(module)?'系统随机；操作轨迹仅保留摘要。':'按明确的时间与规则计算。'}</p></section><section id="result-panel" class="result-empty"><div><div class="empty-symbol">${m[3]}</div><h3>让线索，慢慢展开。</h3><p>${chartModules.includes(module)?'填写出生信息，展开你的命盘。<br>计算与规则分析均在本机完成。':module==='answers'?'带着一个问题，翻开属于此刻的一页。':'准备好后，开启这次探询。<br>你可以随时返回星云，继续探索。'}</p></div></section></div>`;
  $('#back-home').onclick=home;
  if(chartModules.includes(module)||module==='solar'){
    const f=$('#calculation-fields');f.insertAdjacentHTML('afterbegin',birthdayPicker(p));
    $('#birth-profile').onchange=()=>{const id=$('#birth-profile').value;if(id){rememberDraft();applyBirthday(id);openModule(module,null,true);}else{drafts[module]={...captureForm(),birthday_id:''};openModule(module,null,true);}};
    $('#manage-birthdays').onclick=()=>showBirthdays();
    $('#save-birth-inputs').onclick=()=>editBirthday({...p,...captureForm(),name:$('[name=label]').value||''},false,true);
  }
  $('#calculation-form').onsubmit=submitCalculation;
  if(['tarot','lenormand','liuyao','answers'].includes(module)&&p.method!=='manual'){
    const simulation=document.createElement('details');simulation.innerHTML=`<summary>可复现模拟（高级）</summary><div class="fields">${input('seed','模拟 Seed（留空使用系统随机）','text',p.seed??'','inputmode="numeric" pattern="-?[0-9]+" placeholder="仅用于测试与旧版回放兼容"')}</div><p class="subtle">填写 Seed 后使用确定性模拟。正常问事请留空。</p>`;$('#calculation-fields').append(simulation);
  }
  if(oracleModules.includes(module)&&!record){
    $('.space-layout').classList.add('oracle-layout');
    ritual=mountRitual($('#result-panel'),{module,prefs,api,getInputs:async()=>{const f=$('#calculation-form');if(!f.reportValidity())return null;const data={...captureForm(),module,interaction:samples.map(s=>({...s}))},context=!String(data.seed??'').trim()&&['tarot','lenormand','liuyao','answers'].includes(module)&&data.method!=='manual'?await deviceLocation?.entropy():null;if(context)data.random_location=context;return data;},onRecord:(r,details)=>{currentRecord=r;$('#calculation-fields').disabled=false;$('#calculate').disabled=false;$('#calculate').textContent='重新准备一次 ↗';if(details){clearRitual();currentTab='overview';renderRecord(r);}else toast('本次问事已保存到星迹');},onError:e=>toast(e.message,true)});
    $('#calculate').textContent=['tarot','lenormand'].includes(module)?'开始洗牌 ↗':module==='answers'?'翻开答案之书 ↗':'准备起卦 ↗';
  }
  const method=$('select[name=method]');if(method)method.onchange=()=>{drafts[module]=captureForm();openModule(module);};
  if(chartModules.includes(module)||module==='solar')chartPlaceSearch=mountPlaceSearch($('#calculation-form'),{api,onError:e=>toast(e.message,true)});
  if(chartModules.includes(module))natalWorkspace=mountNatalWorkspace($('#workspace'));
  if(record)renderRecord(record);
}
async function submitCalculation(e){
  e.preventDefault();
  if(oracleModules.includes(currentModule)){
    if(!ritual){openModule(currentModule,null,true);return;}
    await ritual.begin();return;
  }
  if(chartPlaceSearch&&!chartPlaceSearch.validate())return;
  const button=$('#calculate'),module=currentModule;
  try{
    button.disabled=true;const p={...captureForm(),module,interaction:samples};drafts[module]={...captureForm()};
    button.textContent='正在计算…';const record=await api('calculate',p);
    if(module!==currentModule){toast('计算完成，已保存在星迹');return;}
    button.disabled=false;button.textContent='再次计算';currentRecord=record;currentTab='overview';renderRecord(record);toast('已保存到星迹');
  }catch(error){toast(error.message,true);if(module===currentModule){button.disabled=false;button.textContent='重新尝试';}}
}

const labels={summary:'概览',analysis:'结构分析',input:'输入信息',time:'时间依据',rules:'计算规则',true_solar:'真太阳时',lunar:'农历',day_master:'日主',pillars:'四柱',wuxing_stats:'五行数量',extra:'辅助信息',da_yun:'大运',birth:'命盘信息',palaces:'十二宫',decadals:'大限',annual:'流年',calculation_time:'排盘时刻',points:'星体位置',houses:'宫位',aspects:'相位',asc_sign:'上升星座',mc_sign:'中天星座',sun_sign:'太阳星座',moon_sign:'月亮星座',grahas:'九曜与月宿',d1:'D1 本命盘',d9:'D9 九分盘',vimshottari:'Vimshottari 大运',question:'问题',ben:'本卦',bian:'变卦',hu:'互卦',dong:'动爻',calendar:'干支历',trace:'起卦过程',source:'来源',random:'随机来源',detail:'校正明细',moving_line:'动爻',category:'主题',category_label:'主题',tosses:'爻值',date:'历法时刻',spread:'牌阵',cards:'所选牌',name:'名称',cn:'中文',en:'英文',lon:'黄经',longitude:'经度',lat:'纬度',latitude:'纬度',sign:'星座',sign_idx:'星座索引',house:'宫位',deg:'度数',degree:'度数',retro:'逆行',retrograde:'逆行',element:'元素',modality:'三态',gan:'天干',zhi:'地支',ganzhi:'干支',nayin:'纳音',hide_gan:'藏干',shishen_gan:'天干十神',shishen_zhi:'藏干十神',dishi:'地势',xunkong:'旬空',gan_wx:'天干五行',zhi_wx:'地支五行',key_insights:'关键看点',compositions:'结构看点',text:'说明',label:'名称',value:'数值',note:'说明',notes:'说明',at_birth:'出生时运限',birth_balance_years:'出生大运余额（年）',mahadashas:'大运',antardashas:'子运',start:'起点',end:'终点',lord:'主星',lagna:'上升',lagna_lord:'命主星',nakshatra:'月宿',pada:'Pada',moon_nakshatra:'月亮月宿',soul_palace:'命宫',body_palace:'身宫',natal_mutagens:'本命四化',soul_surrounding_palaces:'命宫三方四正',empty_major_palaces:'无主星宫位',big_three:'日月升',chart_ruler:'命主星',patterns:'相位格局',hemispheres:'半球分布',strength:'旺衰',yongshen:'用神',structure:'格局',body:'体卦',use:'用卦',changed_use:'变卦用卦',ben_relation:'本卦体用关系',bian_relation:'变卦体用关系',hu_upper_relation:'上互与体',hu_lower_relation:'下互与体',focus:'焦点牌',adjacent_pairs:'相邻组合',mirror_pairs:'镜像组合',theme_counts:'主题数量',reading_hint:'组合提示',has_selected_rule:'命中组合规则',keywords:'关键词',position:'位置',position_name:'位置名',meaning:'牌义',reversed:'逆位',shi:'世爻',ying:'应爻',lines:'爻明细',liuqin:'六亲',liushen:'六神',kong:'旬空',gua_ci:'卦辞',palace:'卦宫',palace_wx:'宫五行',moving:'动爻',line_name:'爻名',bits:'阴阳（自下而上）',upper:'上卦',lower:'下卦',clock_time:'标准钟表时',mean_solar_time:'平太阳时',true_solar_time:'真太阳时',longitude_correction_min:'经度校正（分钟）',equation_of_time_min:'均时差（分钟）',total_correction_min:'总校正（分钟）',year:'年',month:'月',day:'日',hour:'时',minute:'分',tz_name:'时区',utc:'UTC',local:'当地时间',fold:'重复时刻序号',basis:'依据',majorStars:'主星',minorStars:'辅星',adjectiveStars:'杂曜',earthlyBranch:'地支',heavenlyStem:'天干',mutagen:'四化',brightness:'亮度',isBodyPalace:'身宫',soul:'命主',bodyPalace:'身宫',solarDate:'阳历',lunarDate:'农历',chineseDate:'干支',fiveElementsClass:'五行局',schema:'版本',method:'方式',algorithm:'算法',system:'体系',profile:'规则配置',source_kind:'来源类型',location_source:'位置输入来源'};
function dataView(data,depth=0){
  if(data===null||data===undefined)return '<span class="subtle">未设置</span>';
  if(typeof data==='boolean')return data?'是':'否';
  if(typeof data!=='object')return esc(data);
  if(depth>7)return `<pre>${esc(JSON.stringify(data,null,2))}</pre>`;
  if(Array.isArray(data)){if(!data.length)return '<span class="subtle">无</span>';if(data.every(x=>typeof x!=='object'||x===null))return data.map(v=>esc(v)).join(' · ');return `<div>${data.map((v,i)=>`<div class="data-item"><span class="subtle">${String(i+1).padStart(2,'0')}</span>${dataView(v,depth+1)}</div>`).join('')}</div>`;}
  return Object.entries(data).map(([k,v])=>`<div class="data-pair"><span class="data-key">${esc(labels[k]||k)}</span><div class="data-val">${dataView(v,depth+1)}</div></div>`).join('');
}
function section(title,data){return `<section class="data-section"><details><summary>${title}</summary>${dataView(data)}</details></section>`;}
function brief(record){
  const r=record.result,m=record.module,a=r.analysis||{};
  const facts=[];
  if(m==='bazi'){facts.push(['日主',r.day_master],['旺衰',a.strength?.name],['格局',a.pattern?.name],['扶抑喜五行',a.yong_shen?.xi_wuxing?.join(' · ')]);}
  if(m==='jyotish'){facts.push(['D1 上升',r.d1.lagna.sign],['D9 上升',r.d9.lagna.sign],['月亮月宿',a.moon_nakshatra?.name],['出生大运余额',Number(r.vimshottari.birth_balance_years).toFixed(2)+' 年']);}
  if(m==='meihua'){facts.push(['体卦',a.body?.name+' · '+a.body?.element],['用卦',a.use?.name+' · '+a.use?.element],['本卦体用',a.ben_relation?.label],['变卦体用',a.bian_relation?.label]);}
  if(m==='liuyao'){facts.push(['卦宫',r.ben.palace+' · '+r.ben.palace_wx],['动爻',r.dong.length?r.dong.join('、'):'无动爻'],['世爻','第 '+r.ben.shi+' 爻'],['应爻','第 '+r.ben.ying+' 爻']);}
  let h=facts.length?`<div class="fact-grid">${facts.map(([k,v])=>`<div class="fact"><small>${esc(k)}</small><b>${esc(typeof v==='object'&&v!==null?v.gan||v.name||JSON.stringify(v):v||'—')}</b></div>`).join('')}</div>`:'';
  const insights=a.key_insights||a.structures?.compositions||a.compositions||[];
  if(Array.isArray(insights))h+=insights.slice(0,4).map(i=>`<p class="insight">${esc(typeof i==='string'?i:[i.name||i.label,i.text||i.note].filter(Boolean).join(' · '))}</p>`).join('');
  return h;
}
function overview(record){
  const r=record.result,m=record.module;let h='';
  if(chartModules.includes(m))return renderNatalChart(record,{section});
  if(m==='liuyao'||m==='meihua'){
    h+=`<div class="hexagrams">${[['ben','本卦'],...(m==='meihua'?[['hu','互卦']]:[]),['bian','变卦']].filter(([k])=>r[k]).map(([k,title])=>`<article class="hexagram"><small>${title}</small><h4>${esc(r[k].name)}</h4>${[...r[k].bits].map((v,i)=>({v,i})).reverse().map(({v,i})=>`<div class="hex-line ${v?'yang':''} ${k==='ben'&&(r.dong||[r.moving_line]).includes(i+1)?'moving':''}"><span>${k==='ben'&&(r.dong||[r.moving_line]).includes(i+1)?'○':''}</span></div>`).join('')}</article>`).join('')}</div>`+(r.ben.gua_ci?`<p>${esc(r.ben.gua_ci)}</p>`:'')+section('结构分析',r.analysis)+(m==='liuyao'?section('纳甲、六亲与六神',r.ben.lines)+section('干支历参考',r.calendar):section('起卦依据与过程',{source:r.source,trace:r.trace}));
  }
  if(m==='tarot'||m==='lenormand'){
    const glyphs={wands:'♧',cups:'♜',swords:'⚔',pentacles:'✵'};
    const lenGlyph=['♘','♧','⚓','⌂','♣','☁','♧','▱','❀','⚒','⚔','♬','♙','♢','♜','✶','♧','♘','♜','❋','△','⇢','♧','♡','○','▤','✉','♙','♕','❀','☉','☽','⚿','♓','⚓','✝'];
    h+=`<div class="cards">${r.cards.map((c,i)=>`<article class="reading-card ${m==='tarot'?'has-art':''} ${c.reversed?'reverse':''}" style="animation-delay:${i*.08}s"><small>${esc(c.position_name||c.position.name)}</small>${m==='tarot'&&tarotImagePath(c.card)?`<img class="tarot-art" src="${tarotImagePath(c.card)}" alt="${esc(c.card.cn)} · ${c.reversed?'逆位':'正位'}" width="350" height="600" loading="lazy">`:`<div class="card-glyph">${m==='tarot'?(glyphs[c.card.suit]||['☉','☽','✧','♕','♔','✦','♡','♘','∞','☷','☸','⚖','☥','☽','⚗','♄','ϟ','✶','☽','☉','♧','◎'][c.card.num]):lenGlyph[c.card.id-1]}</div>`}<h4>${esc(c.card.cn)}</h4><small>${m==='tarot'?(c.reversed?'逆位':'正位'):String(c.card.id).padStart(2,'0')}</small><p>${esc(c.meaning||c.card.keywords.join(' · '))}</p></article>`).join('')}</div>`+section('结构分析',r.analysis)+`<details><summary>全部牌面与位置释义</summary>${dataView(r.cards)}</details>`;
  }
  if(m==='answers')h+=`<div class="oracle-answer"><small>PAGE ${String(r.page).padStart(3,'0')} / ${r.replay.schema==='answers-legacy-v1'?'888 · 旧版模拟':'197'}</small><h2>${esc(r.answer)}</h2><small>给此刻，留一点回响。</small></div>`;
  if(m==='solar')h+=`<div class="oracle-answer"><small>TRUE SOLAR TIME</small><h2>${esc(r.detail.true_solar_time)}</h2></div>`+dataView(r.detail);
  const where=r.random?.interaction?.location_source;if(where)h+=`<p class="subtle">本次随机已混入${where==='device'?'系统大致位置':'手填大致位置'}；坐标未保存。</p>`;
  const firstDetails=h.indexOf('<section class="data-section">');
  if(firstDetails>=0)h=h.slice(0,firstDetails)+brief(record)+h.slice(firstDetails);
  if(r.question)h=`<p class="subtle" style="border-left:1px solid #b8c4e450;padding-left:15px">${esc(r.question)}</p>`+h;
  return h;
}
function renderRecord(record){
  currentRecord=record;const m=record.module;
  $('#result-panel').className='glass result-panel';
  $('#result-panel').innerHTML=`<header class="result-header"><div><div class="section-kicker">${meta[m][1]}</div><h2>${esc(record.label)}</h2><span class="result-meta">${esc(new Date(record.created).toLocaleString('zh-CN'))} · 已保存本机</span></div><div class="toolbar"><button class="secondary" id="export-record">导出记录 ↗</button></div></header><div class="result-tabs"><button data-tab="overview">${chartModules.includes(m)?'命盘与结构':'结果与结构'}</button>${!['answers','solar'].includes(m)?'<button data-tab="ai">AI 解读与追问</button>':''}<button data-tab="basis">时间与来源</button><button data-tab="raw">原始数据</button></div><div class="result-body" id="result-body"></div>`;
  $('#result-panel').scrollTop=0;
  $('#export-record').onclick=()=>download('Mystery-'+m+'-'+record.id+'.json',JSON.stringify(record,null,2));
  $$('[data-tab]').forEach(b=>b.onclick=()=>{currentTab=b.dataset.tab;$('#result-panel').scrollTop=0;renderTab();});renderTab();
  natalWorkspace?.attach(true);
}
function renderTab(){
  const record=currentRecord;if(!record)return;
  $$('[data-tab]').forEach(b=>b.classList.toggle('active',b.dataset.tab===currentTab));const body=$('#result-body');
  body.onclick=null;body.onkeydown=null;
  if(currentTab==='overview'){body.innerHTML=overview(record);if(chartModules.includes(record.module))mountNatalInteractions(body,record);}
  if(currentTab==='basis'){
    const r=record.result;body.innerHTML='<h3>时间、规则与来源</h3>'+dataView(Object.fromEntries(['input','time','utc','calculation_time','true_solar','rules','random','source'].filter(k=>r[k]!==undefined).map(k=>[k,r[k]])))+(['tarot','lenormand','liuyao','meihua','answers'].includes(record.module)?'<div class="data-section"><button class="secondary" id="replay-record">校验并回放原始快照</button><p class="subtle">回放读取已经保存的结果，不重新抽取。</p></div>':'');
    if($('#replay-record'))$('#replay-record').onclick=async()=>{try{const x=await api('replay',{id:record.id});toast(x.verified?'快照校验通过，回放与原始结果一致':'快照与保存结果不一致，请检查记录',!x.verified);}catch(e){toast(e.message,true);}};
  }
  if(currentTab==='raw')body.innerHTML='<p class="subtle">包含完整结果与回放快照，可导出用于核对。</p><pre>'+esc(JSON.stringify(record.result,null,2))+'</pre>';
  if(currentTab==='ai')renderAI();
}
function download(name,text,type='application/json'){const blob=new Blob([text],{type}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),30000);}
function pageShell(title,kicker,content,actions=''){setWorkspace(title==='生日簿'?'birthdays':title==='星迹'?'records':title==='设置'?'settings':title==='命盘'?'charts':'oracles');$('#workspace').innerHTML=`<section class="glass page-shell"><div class="page-heading"><div><div class="section-kicker">${kicker}</div><h2 class="page-title">${title}</h2></div><div class="toolbar">${actions}<button class="back-link" id="page-home" style="margin:0">← 返回星云</button></div></div>${content}</section>`;$('#page-home').onclick=home;scene?.setMode('page',title==='生日簿'?'birthdays':undefined);}
function moduleMenu(group,instant=false){if(instant!==true)return travel(()=>moduleMenu(group,true));rememberDraft();currentModule=null;currentRecord=null;const keys=group==='charts'?[...chartModules,'solar']:oracleModules;pageShell(group==='charts'?'命盘':'问事',group==='charts'?'NATAL PATTERNS':'THE UNFOLDING',`<p class="subtle">${group==='charts'?'从不同的传统，看见自己的轮廓。':'让一个具体的问题，找到展开的方式。'}</p><div class="module-list">${keys.map(k=>`<button class="module-option" data-module="${k}"><span class="module-symbol">${meta[k][3]}</span><span><strong>${meta[k][0]}</strong><small>${meta[k][1]}</small></span><p>${meta[k][2]}</p><span>↗</span></button>`).join('')}</div>`);$$('[data-module]').forEach(b=>b.onclick=()=>openModule(b.dataset.module));}
async function showRecords(instant=false){
  if(instant!==true)return travel(()=>showRecords(true));
  rememberDraft();currentModule=null;currentRecord=null;pageShell('星迹','YOUR SAVED MOMENTS','<div id="records-content"><p>正在读取本机记录…</p></div>','<button class="secondary" id="import-record">导入记录</button><input id="import-file" type="file" accept=".json" class="hidden">');
  $('#import-record').onclick=()=>$('#import-file').click();$('#import-file').onchange=async e=>{const f=e.target.files[0];if(!f)return;try{if(f.size>4000000)throw Error('记录文件最大 4 MB');const record=await api('import',{record:JSON.parse(await f.text())});openModule(record.module,record);toast('已导入并保存记录');}catch(error){toast(error.message,true);}};
  try{const records=await api('records');if(!$('#records-content'))return;$('#records-content').innerHTML=`<div class="field-row" style="margin:20px 0">${input('search-records','查找星迹','search','','placeholder="输入名称或问题"')}${select('filter-records','模块',{'':'全部模块',...Object.fromEntries(Object.entries(meta).map(([k,v])=>[k,v[0]]))},'')}</div><div id="record-list"></div>`;
    function filter(){const query=$('[name=search-records]').value.toLowerCase(),module=$('[name=filter-records]').value;const rows=records.filter(r=>(!module||r.module===module)&&r.label.toLowerCase().includes(query));$('#record-list').innerHTML=rows.length?rows.map(r=>`<article class="record-row"><span class="badge">${meta[r.module][0]}</span><button class="record-open" data-record="${r.id}"><h3>${esc(r.label)}</h3><small>展开记录 ↗</small></button><small>${esc(new Date(r.created).toLocaleString('zh-CN'))}</small><button class="muted-button danger" data-delete="${r.id}">删除</button></article>`).join(''):'<div class="result-empty" style="min-height:260px"><div><div class="empty-symbol">✧</div><h3>还没有留下星迹</h3><p>完成一次命盘或问事后，记录会出现在这里。</p></div></div>';
      $$('[data-record]').forEach(b=>b.onclick=async()=>{try{const record=await api('record',{id:b.dataset.record});openModule(record.module,record);}catch(e){toast(e.message,true);}});
      $$('[data-delete]').forEach(b=>b.onclick=()=>modal('删除这份星迹？','<p>本机记录及其中的解读将被删除。你可以先导出一份备份。</p>',async()=>{try{await api('delete',{id:b.dataset.delete});closeModal();showRecords();toast('记录已删除');}catch(e){toast(e.message,true);}},'删除记录'));
    }filter();$('[name=search-records]').oninput=filter;$('[name=filter-records]').onchange=filter;
  }catch(e){toast(e.message,true);}
}
function modal(title,content,onConfirm,confirmText='确定'){modalCleanup?.();modalCleanup=null;const root=$('#modal-root');root.innerHTML=`<div class="modal-backdrop"><section class="glass modal" role="dialog" aria-modal="true" aria-label="${esc(title)}"><h3>${esc(title)}</h3>${content}<div class="toolbar"><button id="modal-cancel" class="secondary">关闭</button>${onConfirm?`<button id="modal-confirm" class="primary">${confirmText}</button>`:''}</div></section></div>`;$('#modal-cancel').onclick=closeModal;if(onConfirm)$('#modal-confirm').onclick=onConfirm;$('#modal-cancel').focus();}
function closeModal(){
  modalCleanup?.();modalCleanup=null;$('#modal-root').innerHTML='';
  if(birthOnboarding){birthOnboarding=false;prefs.birth_onboarding_done=true;persistPrefs();}
  if(birthReturnFocus){const target=birthReturnFocus.isConnected?birthReturnFocus:$('#birthday-book-button');birthReturnFocus=null;target?.focus({preventScroll:true});}
}

function birthdayInputs(person){if(!person)return {};const fields=['datetime','tz_name','fold','longitude','latitude','gender','use_true_solar','birth_place','birth_place_id','birth_place_kind'];return {...Object.fromEntries(fields.map(k=>[k,person[k]])),label:person.name,birthday_id:person.id,city:''};}
function updateBirthdayButton(){const active=birthdays.find(b=>b.id===prefs.active_birth_id);$('#birthday-book-label').textContent=active?`生日簿 · ${active.name}`:'生日簿 · 添加生辰';$('#central-star-person').textContent=active?`${active.name} · 当前生辰`:'从这里，展开每个人的星图';$('#birth-count').textContent=birthdays.length;$('#birthday-book-button').title=active?`当前：${active.name}；打开生日簿管理所有人的生辰`:'打开生日簿，添加和管理生辰信息';}
function applyBirthday(id,persist=true){const person=birthdays.find(p=>p.id===id);if(!person)return;prefs.active_birth_id=id;for(const m of [...chartModules,'solar'])drafts[m]={...(drafts[m]||{}),...birthdayInputs(person)};if(persist)persistPrefs();updateBirthdayButton();}
function birthdayPicker(p){return `<div class="birth-picker"><label for="birth-profile">从生日簿填写</label><select id="birth-profile"><option value="">手动填写</option>${birthdays.map(b=>`<option value="${b.id}"${b.id===p.birthday_id?' selected':''}>${esc(b.name)} · ${esc(b.datetime.slice(0,10))}</option>`).join('')}</select><input type="hidden" name="birthday_id" value="${esc(p.birthday_id||'')}"><div class="toolbar"><button class="muted-button" type="button" id="manage-birthdays">管理生日簿</button><button class="muted-button" type="button" id="save-birth-inputs">将本次输入存入生日簿</button></div></div>`;}
function showBirthdays(instant=false){
  if(instant!==true)return travel(()=>showBirthdays(true));rememberDraft();currentModule=null;currentRecord=null;setWorkspace('birthdays');scene?.setMode('page','birthdays');document.body.classList.add('birthday-atlas-open');
  atlasPage=mountBirthdayAtlas($('#workspace'),{getPeople:()=>birthdays,getActive:()=>prefs.active_birth_id,prefs,onError:e=>toast(e.message,true),onAdd:()=>editBirthday(),onEdit:person=>editBirthday(person),onNotes:openPersonNotes,onFilters:filters=>{prefs.atlas_filters=JSON.stringify(filters);persistPrefs();},onChart:person=>{applyBirthday(person.id);openModule('bazi');},onActive:person=>{applyBirthday(person.id);atlasPage?.refresh();toast('已切换当前生辰');},onDelete:deleteBirthday,onCluster:people=>{modal('这里的朋友',`<div class="atlas-cluster-people">${people.map(p=>`<button class="secondary" data-cluster-person="${p.id}">${esc(p.name)} · ${esc(p.birth_place||'出生地未命名')}${p.current_place?' · 现居 '+esc(p.current_place):''}</button>`).join('')}</div>`);for(const b of $$('[data-cluster-person]'))b.onclick=()=>openPersonNotes(people.find(p=>p.id===b.dataset.clusterPerson));},onPoint:point=>editBirthday({_mapPoint:point})});
}
function deleteBirthday(person){modal(`删除 ${person.name} 的生辰？`,'<p>这份资料将从生日簿移除。已经生成的星迹保留原始数据。</p>',async()=>{const button=$('#modal-confirm');button.disabled=true;try{await api('delete-birthday',{id:person.id});birthdays=birthdays.filter(p=>p.id!==person.id);for(const m of [...chartModules,'solar'])if(drafts[m]?.birthday_id===person.id)delete drafts[m];if(prefs.active_birth_id===person.id){prefs.active_birth_id='';persistPrefs();}updateBirthdayButton();closeModal();atlasPage?.refresh();reminders?.refresh();toast('已从生日簿移除');}catch(e){toast(e.message,true);button.disabled=false;}},'删除这份生辰');}

function openPersonNotes(person){
  if(!person)return;
  modal(`${person.name} · 朋友札记`,`<p class="subtle">${esc(person.birth_place||'出生地未命名')}${person.current_place?' · 现居 '+esc(person.current_place):''}</p><label>给这位朋友写几句备注<textarea id="person-note-text" maxlength="1000" placeholder="关系、喜好、想记住的小事…">${esc(person.notes||'')}</textarea></label><p class="subtle" id="person-note-feedback">备注只保存在这台设备的生日簿中。</p>`,async()=>{const b=$('#modal-confirm');b.disabled=true;try{const saved=await api('save-birthday-note',{id:person.id,notes:$('#person-note-text').value});birthdays=birthdays.map(p=>p.id===saved.id?saved:p);closeModal();atlasPage?.refresh();toast('备注已保存');}catch(e){$('#person-note-feedback').textContent=e.message;b.disabled=false;}},'保存备注');
  $('.modal').classList.add('person-note-modal');const button=document.createElement('button');button.type='button';button.className='muted-button';button.textContent='编辑完整资料';button.onclick=()=>editBirthday({...person,notes:$('#person-note-text').value});$('.modal>.toolbar').prepend(button);$('#person-note-text').focus();
}
function renderDeviceLocation(){const state=deviceLocation?.snapshot();if(!state)return;const status=$('#device-location-status');if(status)status.textContent=state.message;const clock=$('#device-clock-status');if(clock)clock.textContent=`设备时区 ${state.deviceZone}${state.zone?' · 位置时区 '+state.zone:''} · ${new Date().toLocaleString('zh-CN')}`;if($('#device-location-enabled'))$('#device-location-enabled').checked=prefs.location_enabled;if($('#device-location-refresh'))$('#device-location-refresh').disabled=!prefs.location_enabled||state.pending;}
function askLocationConsent(after=()=>{}){
  let decided=false;
  function finish(allow){if(decided)return;decided=true;prefs.location_enabled=allow;prefs.location_consent=allow?'granted':'denied';persistPrefs();if(!allow)deviceLocation?.clear();closeModal();after();renderDeviceLocation();if(allow)deviceLocation?.request();}
  modal('允许 Mystery 使用大致位置吗？','<p>Mystery 是本地应用，生日簿、备注和本地音乐都在这台设备上处理。大致定位用于匹配时区、生日提醒和更贴近此时此地的互动体验。</p><p class="subtle">定位坐标只暂存在内存，不写入生日簿、星迹或 AI 请求。系统定位服务可能联网；网络音频也会连接你指定的地址。你可以拒绝，并随时在设置中关闭定位。</p>',()=>finish(true),'允许并启用');$('#modal-cancel').textContent='暂不允许';$('#modal-cancel').onclick=()=>finish(false);modalCleanup=()=>{if(!decided){decided=true;prefs.location_enabled=false;prefs.location_consent='denied';persistPrefs();deviceLocation?.clear();queueMicrotask(after);}};
}

function editBirthday(person={},onboarding=false,fromInputs=false){
  birthReturnFocus=document.activeElement;birthOnboarding=onboarding;
  const title=onboarding?'先记下一份生辰':person.id?'查看 / 编辑生辰':'添加生辰';
  modal(title,`<p class="subtle">${onboarding?'先为自己或朋友留下一处坐标，之后直接展开命盘。':'填写生辰并选择出生地，时区将自动匹配。'}</p><form id="birth-editor"><section class="editor-section"><div class="editor-section-title"><small>01</small><h4>基本资料</h4></div><div class="fields"><div class="field-row">${input('name','姓名或称呼','text',person.name||'','required maxlength="80" placeholder="如何称呼这位朋友"')}${select('gender','运限规则使用的性别',{'男':'男','女':'女'},person.gender||'男')}</div>${input('datetime','出生日期与时间','datetime-local',person.datetime||'','required min="1900-01-01T00:00" max="2100-12-31T23:59"')}</div></section><section class="editor-section"><div class="editor-section-title"><small>02</small><h4>出生地与时区</h4></div><div class="birth-location-grid"><div>${placeFields(person)}<div class="place-quick-cities" aria-label="常用出生地">${['北京','上海','广东省','四川省'].map(n=>`<button type="button" class="secondary" data-quick-place="${n}">${n}</button>`).join('')}</div></div><div class="editor-map-area"><div class="place-map-tabs"><button type="button" data-place-mode="birth" aria-pressed="true">出生地</button><button type="button" data-place-mode="current" aria-pressed="false">现居地</button></div><div id="birth-place-map" class="birth-place-map"></div><small class="map-help">也可点击地球，选择附近城市</small></div></div><div id="map-place-results" class="map-place-results" hidden></div><p class="subtle" id="place-feedback" role="status"></p></section><details id="birth-current-place" ${person.current_place?'open':''}><summary>现居地 · 可选，用于地图和生日提醒</summary><div class="fields">${placeFields(person,'current')}<div class="toolbar"><button type="button" id="clear-current-place" class="muted-button">移除现居地</button></div></div></details><fieldset class="person-color-picker"><legend>代表色</legend><div class="person-color-options">${personPalette.map(c=>`<button type="button" data-person-color="${c}" style="--swatch:${c}" aria-label="选择代表色 ${c}" aria-pressed="false"></button>`).join('')}<label class="person-color-custom">自定义<input type="color" name="color" value="${personColor(person)}" aria-label="自定义代表色"></label><span class="person-color-preview"></span></div></fieldset><details id="birth-advanced"><summary>备注与时间规则</summary><div class="fields">${select('fold','重复时刻（夏令时）',{'':'自动校验','0':'第一次出现','1':'第二次出现'},person.fold??'')}${check('use_true_solar','八字与紫微使用真太阳时校正',person.use_true_solar)}<label>备注<textarea name="notes" maxlength="1000" placeholder="资料来源或想记住的小事">${esc(person.notes||'')}</textarea></label></div></details><p class="subtle" id="birth-feedback" role="status"></p><button type="submit" hidden>保存</button></form>`,()=>$('#birth-editor').requestSubmit(),person.id?'保存修改':'保存到生日簿');
  const picker=mountPlacePicker($('#birth-editor'),$('#birth-place-map'),{api,prefs,onError:e=>toast(e.message,true)});modalCleanup=()=>picker.dispose();mountPersonColor($('#birth-editor'),()=>picker.refreshColor());if(person._mapPoint)picker.pickPoint(person._mapPoint);

  $('.modal').classList.add('birth-editor-modal');$('#modal-cancel').textContent=onboarding?'稍后填写':'取消';
  $('#birth-editor').onsubmit=async e=>{
    e.preventDefault();if(!picker.validate())return;const button=$('#modal-confirm');button.disabled=true;$('#birth-feedback').textContent='正在保存…';
    const data={...Object.fromEntries(new FormData(e.target)),use_true_solar:$('#birth-editor [name=use_true_solar]').checked};if(person.id)data.id=person.id;
    try{
      const saved=await api('save-birthday',data);birthdays=birthdays.filter(p=>p.id!==saved.id);birthdays.push(saved);
      if(!person.id||prefs.active_birth_id===saved.id)applyBirthday(saved.id,false);
      prefs.birth_onboarding_done=true;birthOnboarding=false;persistPrefs();updateBirthdayButton();closeModal();
      reminders?.refresh({announce:true});if(atlasPage)atlasPage.refresh();else if(fromInputs&&currentModule)openModule(currentModule,null,true);
      toast('已收入生日簿');
    }catch(error){$('#birth-feedback').textContent=error.message;$('#birth-advanced').open=true;button.disabled=false;}
  };
  $('#birth-editor [name=name]').focus();
}
function showSettings(instant=false){
  if(instant!==true)return travel(()=>showSettings(true));
  rememberDraft();currentModule=null;currentRecord=null;
  pageShell('设置','MAKE ROOM FOR YOURSELF',`<div class="settings-grid"><div><div class="setting-block"><h3>可选 AI 解读</h3><p class="subtle">只有点击生成解读或追问时，才会将当前结果发送至你填写的服务。API Key 仅在本次运行的内存中使用。</p><form id="ai-settings"><div class="fields">${input('api_base','兼容 API 根地址','url',aiConfig.api_base,'placeholder="https://你的服务/v1" required')}${input('api_key','API Key（关闭软件后清除）','password',aiConfig.api_key,'autocomplete="off" required')}${input('model','模型 ID','text',aiConfig.model,'list="model-options" required')}<datalist id="model-options"></datalist>${input('lite_model','速览模型 ID（可选）','text',aiConfig.lite_model)}${check('fallback','请求失败时启用速览模型',aiConfig.fallback)}</div><div class="toolbar"><button class="primary" type="submit">应用配置</button><button class="secondary" id="fetch-models" type="button">读取模型</button><button class="muted-button" id="clear-key" type="button">清除 Key</button></div><p class="subtle" id="settings-feedback" role="status"></p></form></div></div><div><div class="setting-block"><h3>空间与动效</h3><div class="fields">${select('quality','场景画质',{'high':'精细 · 完整星云','low':'节能 · 减少粒子与刷新频率'},prefs.quality)}${check('reduced','减少动态效果',prefs.reduced)}${check('pinned','固定显示浮动导航',prefs.pinned)}</div><p class="subtle">导航未固定时，移动鼠标到窗口上方中央即可唤出。按 Esc 返回上层，Home 重置星云视角。</p></div><div class="setting-block"><h3>本机数据</h3><p class="subtle">计算、记录和快照均保存在本机。导出的 JSON 包含输入、结果及解读，可在星迹中重新导入。</p><p class="subtle" style="overflow-wrap:anywhere">${esc(catalog.data_dir)}</p></div><div class="setting-block"><h3>定位与生日提醒</h3><label class="check"><input type="checkbox" id="device-location-enabled" ${prefs.location_enabled?'checked':''}>启用系统大致定位</label><p class="subtle" id="device-location-status"></p><p class="subtle" id="device-clock-status"></p><button type="button" class="secondary" id="device-location-refresh">重新获取大致位置</button><label class="check" style="margin-top:18px"><input type="checkbox" id="birthday-reminders-enabled" ${prefs.birthday_reminders_enabled!==false?'checked':''}>提前五天及生日当天在应用内提醒</label><p class="subtle">按朋友现居地当地日期判断；未填现居地时按出生地时区。2 月 29 日生日在平年按 2 月 28 日提醒。定位关闭后仍可使用设备时区。</p></div><div class="setting-block app-about"><div class="section-kicker">ABOUT MYSTERY</div><h3>关于 Mystery</h3><p class="app-version" id="settings-version">版本 ${esc(catalog.version)}</p><p class="subtle">Windows x64 · 星云之间<br>塔罗使用 78 张韦特原版扫描牌面，已内置，可离线显示。<br>画作：Pamela Colman Smith · 设计：Arthur Edward Waite<br>素材来源：metabismuth/tarot-json，随附来源与许可说明。<br>占星与规则是不同传统的描述工具，请结合实际情境理解。</p></div></div></div>`);
  $('#ai-settings').onsubmit=e=>{e.preventDefault();aiConfig={...Object.fromEntries(new FormData(e.target)),fallback:$('[name=fallback]').checked};prefs.api_base=aiConfig.api_base;prefs.model=aiConfig.model;persistPrefs();$('#settings-feedback').textContent='配置已应用。Key 仅保留在当前运行内存中。';toast('AI 配置已应用');};
  $('#fetch-models').onclick=async()=>{const b=$('#fetch-models');b.disabled=true;try{const models=await api('models',{api_base:$('[name=api_base]').value,api_key:$('[name=api_key]').value});const list=Array.isArray(models)?models:(models.data||[]);$('#model-options').innerHTML=list.map(m=>`<option value="${esc(typeof m==='string'?m:m.id)}">`).join('');$('#settings-feedback').textContent=`已读取 ${list.length} 个模型，请在模型 ID 中选择。`;}catch(e){toast(e.message,true);}finally{b.disabled=false;}};
  $('#clear-key').onclick=()=>{aiConfig.api_key='';$('[name=api_key]').value='';toast('API Key 已清除');};
  renderDeviceLocation();$('#device-location-enabled').onchange=e=>{prefs.location_enabled=e.target.checked;if(!prefs.location_enabled){deviceLocation.clear();persistPrefs();renderDeviceLocation();reminders?.refresh();}else if(prefs.location_consent!=='granted')askLocationConsent(renderDeviceLocation);else{persistPrefs();deviceLocation.request();}};$('#device-location-refresh').onclick=()=>{if(prefs.location_consent!=='granted')askLocationConsent(renderDeviceLocation);else deviceLocation.request();};$('#birthday-reminders-enabled').onchange=e=>{prefs.birthday_reminders_enabled=e.target.checked;persistPrefs();reminders?.refresh({announce:true});};
  for(const key of ['quality','reduced','pinned'])$(`[name=${key}]`).onchange=e=>{prefs[key]=e.target.type==='checkbox'?e.target.checked:e.target.value;persistPrefs();};
}
async function renderAI(){
  const record=currentRecord,body=$('#result-body');
  body.innerHTML=`<h3>在既定结果上，展开解读。</h3><p class="subtle">AI 只解释已计算的命盘、牌与卦，不重新选择结果。${!aiConfig.api_key?'请先在设置中填写你自己的 API 服务、Key 和模型。':''}</p><div class="toolbar"><button class="primary" id="generate-ai" ${aiJob?'disabled':''}>${record.interpretation?'重新生成解读':'生成 AI 解读'} ↗</button><button class="secondary" id="export-prompt">导出离线提示词</button><button class="muted-button" id="go-settings">设置 API</button></div><div class="ai-status" id="ai-status">${record.ai_incomplete?'上次请求中断，以下可能是不完整内容。':''}</div><div class="ai-copy" id="ai-copy">${esc(record.interpretation||'')}</div><div id="conversation">${(record.history||[]).map(m=>`<div class="conversation-message ${m.role}"><div class="subtle">${m.role==='user'?'你':'AI'}</div><div class="ai-copy">${esc(m.content)}</div></div>`).join('')}</div><form id="followup-form" class="data-section"><label>继续追问<textarea name="followup" maxlength="4000" placeholder="关于这份结果，你还想了解什么？" required></textarea></label><details><summary>对照同模块星迹（最多四份）</summary><div class="refs" id="ai-refs"><p class="subtle">正在读取记录…</p></div></details><button type="submit" class="secondary" style="margin-top:16px" ${aiJob?'disabled':''}>发送追问 ↗</button><div class="ai-copy" id="followup-live"></div></form>`;
  $('#go-settings').onclick=showSettings;
  $('#generate-ai').onclick=()=>startAI('');
  $('#followup-form').onsubmit=e=>{e.preventDefault();startAI($('[name=followup]').value);};
  $('#export-prompt').onclick=async()=>{try{const p=await api('prompt',{id:record.id});download('Mystery-'+record.module+'-prompt.txt',p.system+'\n\n'+p.user,'text/plain;charset=utf-8');toast('离线提示词已导出');}catch(e){toast(e.message,true);}};
  try{const records=await api('records');if(currentRecord?.id!==record.id||!$('#ai-refs'))return;const same=records.filter(r=>r.id!==record.id&&r.module===record.module);$('#ai-refs').innerHTML=same.length?same.map(r=>`<label><input type="checkbox" value="${r.id}">${esc(r.label)} · ${esc(r.created.slice(0,10))}</label>`).join(''):'<p class="subtle">暂无其他同模块记录。</p>';}catch(e){toast(e.message,true);}
}
async function startAI(question){
  if(!aiConfig.api_key||!aiConfig.api_base||!aiConfig.model){toast('请先在设置中填写 API 根地址、Key 和模型',true);return;}
  if(aiJob){toast('请等待当前解读完成');return;}
  const record=currentRecord,refs=question?$$('#ai-refs input:checked').map(i=>i.value):[];
  if(refs.length>4){toast('最多选择四份对照记录',true);return;}
  try{
    $('#generate-ai').disabled=true;$('#followup-form button[type=submit]').disabled=true;
    $('#ai-status').textContent='正在连接你配置的 AI 服务…';
    const job=await api('ai',{...aiConfig,id:record.id,question,refs});aiJob=job.job;let cursor=0,text='',failure=false;
    if(!question)$('#ai-copy').textContent='';
    while(true){
      await new Promise(r=>setTimeout(r,300));const poll=await api('poll',{job:aiJob,cursor});cursor=poll.cursor;
      const visible=currentRecord?.id===record.id&&currentTab==='ai'&&$('#ai-status');
      for(const event of poll.events){
        if(event.type==='delta')text+=event.text||'';
        if(event.type==='error'){failure=true;toast(event.text||event.message||event.error||'AI 请求失败',true);}
        if(visible){if(event.type==='delta')$(question?'#followup-live':'#ai-copy').textContent=text;else if(['notice','queue'].includes(event.type))$('#ai-status').textContent=event.text||event.message||'请求排队中…';}
      }
      if(poll.done)break;
    }
    aiJob=null;const updated=await api('record',{id:record.id});
    if(currentRecord?.id===record.id){currentRecord=updated;if(currentTab==='ai')renderAI();}
    toast(failure?'解读未完整完成，请检查服务配置':'AI 解读已保存',failure);
  }catch(e){aiJob=null;toast(e.message,true);if(currentRecord?.id===record.id&&currentTab==='ai')renderAI();}
}

$$('[data-nav]').forEach(b=>b.onclick=()=>{const n=b.dataset.nav;if(n==='home')home();else if(n==='birthdays')showBirthdays();else if(n==='records')showRecords();else if(n==='settings')showSettings();else moduleMenu(n);});
$('#birthday-book-button').onclick=()=>showBirthdays();
$('#brand-home').onclick=home;
$('#return-nebula').onclick=home;
$('#explore').onclick=$('#scroll-invitation').onclick=()=>{scene?.explore();};
$('#reset-camera').onclick=()=>{scene?.reset();};
$('#pin-nav').onclick=()=>{prefs.pinned=!prefs.pinned;persistPrefs();wakeNav();};
let navTimer;
function wakeNav(){clearTimeout(navTimer);$('#nav-zone').classList.remove('asleep');if(!prefs.pinned)navTimer=setTimeout(()=>$('#nav-zone').classList.add('asleep'),3500);}
$('#nav-zone').onpointerenter=wakeNav;document.addEventListener('pointermove',e=>{if(e.clientY<100&&Math.abs(e.clientX-innerWidth/2)<300)wakeNav();});
$('#workspace').addEventListener('pointermove',e=>{if(!['tarot','lenormand','liuyao','answers'].includes(currentModule)||$('#calculation-fields')?.disabled||samples.length>=4096||performance.now()-sampleStart>86400000)return;if(!samples.length||performance.now()-sampleStart-samples.at(-1).t_ms>40)samples.push({x:Math.max(0,Math.min(1,e.clientX/innerWidth)),y:Math.max(0,Math.min(1,e.clientY/innerHeight)),t_ms:Math.round(performance.now()-sampleStart)});});
document.addEventListener('keydown',e=>{
  if(focusMode?.active){if(e.key==='Escape'){e.preventDefault();focusMode.exit();}return;}
  if(e.key==='Escape'&&player?.closeIfOpen()){e.preventDefault();return;}
  const editing=!!document.activeElement.closest('input,textarea,select,[contenteditable=true]');
  if(e.key==='Escape'){e.preventDefault();if($('#modal-root').children.length)closeModal();else home();}
  if((e.key==='Home'&&!editing)||(e.altKey&&e.key.toLowerCase()==='h')){e.preventDefault();home();}
  if(e.key==='PageDown'&&!editing&&!$('#home').classList.contains('hidden')){e.preventDefault();scene?.explore();}
  if(e.key==='Tab')wakeNav();if(e.key==='Tab'&&$('.modal')){const items=$$('button,input:not([type=hidden]),textarea,select', $('.modal')).filter(el=>!el.hidden&&el.getClientRects().length),first=items[0],last=items.at(-1);if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}}
});
try{
  catalog=await api('catalog');$('#app-version').textContent='V '+catalog.version;document.body.dataset.appVersion=catalog.version;document.title=`Mystery ${catalog.version} · 星云之间`;
  prefs=resolvePreferences(storedPrefs,catalog.preferences);aiConfig.api_base=prefs.api_base||'';aiConfig.model=prefs.model||'';
  birthdays=catalog.birthdays||[];if(!birthdays.some(b=>b.id===prefs.active_birth_id))prefs.active_birth_id=birthdays[0]?.id||'';updateBirthdayButton();
  deviceLocation=createDeviceLocation({api,getPrefs:()=>prefs,onChange:()=>{renderDeviceLocation();reminders?.refresh();}});
  player=createMusicPlayer($('#music-root'),{api,nativeDialogs:catalog.native_dialogs,onError:e=>toast(e.message,true),onChange:()=>focusMode?.refresh(),onFocus:kind=>focusMode?.enter(kind)});
  focusMode=createFocusMode($('#focus-root'),{getScene:()=>scene,getPins:()=>atlasPage?.visiblePins()||atlasPins(birthdays,atlasFilters(prefs.atlas_filters,birthdays,prefs.active_birth_id)),getPrefs:()=>prefs,persist:persistPrefs,player,onError:e=>toast(e.message,true)});
  reminders=mountBirthdayReminders($('#birthday-reminders'),{api,getPrefs:()=>prefs,persist:persistPrefs,getZone:()=>deviceLocation.snapshot().zone||deviceTimeZone(),onPerson:id=>openPersonNotes(birthdays.find(p=>p.id===id))});
  try{const {createUniverse}=await import('./scene.js');scene=createUniverse(id=>id==='birthdays'?showBirthdays():openModule(id),updateExploration);persistPrefs();document.body.dataset.sceneReady='true';}
  catch(e){document.body.dataset.sceneReady='false';document.body.classList.add('scene-failed');const el=document.createElement('div');el.className='scene-fallback';el.textContent='三维场景初始化失败。请更新显卡驱动或 WebView2；你仍可通过上方导航使用所有功能。';document.body.append(el);console.error(e);prefs.pinned=true;persistPrefs();}
  wakeNav();
  const finishWelcome=()=>{if(!birthdays.length&&!prefs.birth_onboarding_done)editBirthday({},true);reminders.refresh({announce:true});};
  if(!catalog.ui_testing&&prefs.location_enabled&&prefs.location_consent==='unknown')askLocationConsent(finishWelcome);else{finishWelcome();if(!catalog.ui_testing&&prefs.location_enabled&&prefs.location_consent==='granted')deviceLocation.request();}
}catch(e){toast('本地服务连接失败：'+e.message,true);}
