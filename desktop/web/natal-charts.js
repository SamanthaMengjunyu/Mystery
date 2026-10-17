// Presentation only: all positions, counts and periods come from the saved result.
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const elements={木:['#9cc9b0','生长 · 舒展'],火:['#e4a799','明亮 · 温度'],土:['#cdb78b','承载 · 稳定'],金:['#d4d9e4','秩序 · 凝练'],水:['#9ebcdc','流动 · 感知'],风:['#c3b0dc','交流 · 思考']};
const signs=['白羊','金牛','双子','巨蟹','狮子','处女','天秤','天蝎','射手','摩羯','水瓶','双鱼'];
const zodiac=['♈','♉','♊','♋','♌','♍','♎','♏','♐','♑','♒','♓'];
const glyphs={'太阳':'☉','月亮':'☽','水星':'☿','金星':'♀','火星':'♂','木星':'♃','土星':'♄','天王星':'♅','海王星':'♆','冥王星':'♇','北交点':'☊','上升':'AC','中天':'MC','罗睺':'☊','计都':'☋'};
const planetNames={Sun:'太阳',Moon:'月亮',Mars:'火星',Mercury:'水星',Jupiter:'木星',Venus:'金星',Saturn:'土星',Rahu:'罗睺',Ketu:'计都'};
const signElement=i=>['火','土','风','水'][((i%4)+4)%4];
const color=e=>elements[e]?.[0]||'#c4b4d7';
const polar=(a,r,c=260)=>[c+Math.cos(a*Math.PI/180)*r,c-Math.sin(a*Math.PI/180)*r];
const point=p=>p.map(n=>Number(n).toFixed(2)).join(',');
const text=(x,y,value,cls='',extra='')=>`<text x="${x}" y="${y}" text-anchor="middle" class="${cls}" ${extra}>${esc(value)}</text>`;
const heading=(n,title,sub)=>`<div class="natal-section-title"><div><span>${n}</span><h3>${title}</h3></div><p>${sub}</p></div>`;
const fact=(label,value,note='',symbol='✧')=>`<article class="natal-fact"><span class="natal-fact-symbol">${symbol}</span><small>${esc(label)}</small><b>${esc(value||'—')}</b><p>${esc(note)}</p></article>`;
const guide=items=>`<nav class="natal-guide" aria-label="命盘阅读顺序">${items.map(([id,label],i)=>`<button data-natal-jump="${id}"><small>0${i+1}</small>${label}<span>↓</span></button>`).join('')}</nav>`;
const shell=(module,eyebrow,title,intro,content)=>`<div class="natal-experience natal-${module}"><header class="natal-intro"><div class="section-kicker">${eyebrow}</div><h2>${title}</h2><p>${intro}</p></header>${content}</div>`;
function insights(analysis){
  const items=analysis.structures?.compositions||analysis.key_insights||analysis.compositions||[];
  if(!items.length)return '';
  return `<section class="natal-insights">${heading('✦','值得先看的线索','这些看点来自本机规则分析，展开后可核对全部依据。')}<div>${items.slice(0,3).map((item,i)=>`<article><small>0${i+1}</small><h4>${esc(typeof item==='string'?item:item.name||item.label)}</h4><p>${esc(typeof item==='string'?'':item.note||item.text)}</p></article>`).join('')}</div></section>`;
}
function bars(values,label){
  const entries=Object.entries(values||{}),total=entries.reduce((s,[,v])=>s+Number(v),0);
  return `<div class="natal-bars" role="img" aria-label="${esc(label)}：${esc(entries.map(([k,v])=>k+' '+v).join('，'))}">${entries.map(([e,v])=>`<div style="--element:${color(e)}"><span>${esc(e)}</span><i><b style="width:${total?Number(v)/total*100:0}%"></b></i><strong>${esc(v)}</strong><small>${total?Math.round(Number(v)/total*1000)/10:0}%</small></div>`).join('')}</div>`;
}
function timeline(items,description){
  if(!items.length)return '<p class="subtle">暂无运限数据</p>';
  return `<p class="natal-caption">${esc(description)} · 横向滚动查看完整时间线</p><div class="natal-timeline" tabindex="0" aria-label="运限时间线">${items.map(i=>`<article><i></i><small>${esc(i.range)}</small><b>${esc(i.title)}</b><span>${esc(i.note||'')}</span></article>`).join('')}</div>`;
}
function elementMandala(r){
  const names=['木','火','土','金','水'],stats=r.wuxing_stats||{},total=names.reduce((s,e)=>s+Number(stats[e]||0),0),max=Math.max(1,...Object.values(stats).map(Number));
  let svg=`<svg class="element-mandala" viewBox="0 0 520 520" role="group" aria-label="五行分布；点击五行查看数量与含义"><circle cx="260" cy="260" r="221" class="natal-orbit"/><circle cx="260" cy="260" r="167" class="natal-orbit"/>`;
  for(let ring=1;ring<=3;ring++)svg+=`<polygon points="${names.map((_,i)=>point(polar(90-i*72,ring*46))).join(' ')}" class="element-grid"/>`;
  svg+=`<polygon points="${names.map((e,i)=>point(polar(90-i*72,28+Number(stats[e]||0)/max*110))).join(' ')}" class="element-profile"/>`;
  names.forEach((e,i)=>{
    const p=polar(90-i*72,198),a=polar(90-i*72+10,198),b=polar(90-(i+1)*72-10,198),v=Number(stats[e]||0);
    svg+=`<path d="M${point(a)} A198 198 0 0 1 ${point(b)}" class="element-cycle"/><g class="natal-svg-control" role="button" tabindex="0" data-natal-select="element:${e}" aria-label="${e}，${v}个，${total?Math.round(v/total*1000)/10:0}%"><circle cx="${p[0]}" cy="${p[1]}" r="31" fill="#111b28" stroke="${color(e)}" stroke-opacity=".55"/>${text(p[0],p[1]+7,e,'element-character',`fill="${color(e)}"`)}${text(p[0],p[1]+51,`${v} · ${total?Math.round(v/total*1000)/10:0}%`,'element-count')}</g>`;
  });
  svg+=text(260,247,r.day_master,'mandala-master')+text(260,278,'日 主','mandala-label')+text(260,301,'五行的观察中心','mandala-note')+'</svg>';
  return svg;
}
function bazi(record,section){
  const r=record.result,a=r.analysis||{},dm=r.pillars?.day?.gan_wx||a.strength?.day_master_wx;
  return shell('bazi','THE FIVE PHASES · 四柱八字','五行流转，见自己的底色。','先看日主与五行，再读四柱，最后沿时间看大运。点击图中的五行或四柱，就能逐项了解。',
    guide([['natal-core','认识五行'],['natal-pillars','读懂四柱'],['natal-periods','查看大运']])+
    `<section id="natal-core" class="natal-hero"><div class="natal-art">${elementMandala(r)}<p class="natal-caption">木 → 火 → 土 → 金 → 水 → 木 · 外环表示相生顺序</p></div><div class="natal-reading"><div class="natal-reading-label">你的观察起点</div><h3><em style="color:${color(dm)}">${esc(r.day_master)}</em> ${esc(dm)}日主</h3><p>日柱的天干代表这份命局的观察中心。五行图展示四柱天干与地支本气的数量，不直接代表旺衰。</p><div class="natal-facts">${fact('旺衰参考',a.strength?.label,'综合季节、通根等因素的规则结果')}${fact('命局格局',a.pattern?.name,'从月令与透干观察结构')}${fact('扶抑喜五行',a.yong_shen?.xi_wuxing?.join(' · '),'扶抑与调候可能有不同侧重')}</div>${bars(r.wuxing_stats,'四柱五行数量')}</div></section>`+
    `<aside class="natal-selection" data-natal-detail aria-live="polite">${baziDetail(r,'element:'+dm)}</aside>`+
    `<section id="natal-pillars">${heading('02','四柱，四个时间坐标','日柱以细金边标出；每个字都保留所属五行。')}<div class="natal-pillars">${Object.entries(r.pillars).map(([k,p])=>`<button class="natal-pillar ${k==='day'?'is-day':''}" data-natal-select="pillar:${k}" aria-label="${({year:'年柱',month:'月柱',day:'日柱',hour:'时柱'})[k]} ${p.ganzhi}"><small>${({year:'年柱',month:'月柱',day:'日柱',hour:'时柱'})[k]}${k==='day'?' · 日主所在':''}</small><span class="natal-pillar-character" style="color:${color(p.gan_wx)}">${esc(p.gan)}<i>${esc(p.gan_wx)}</i></span><span class="natal-pillar-character" style="color:${color(p.zhi_wx)}">${esc(p.zhi)}<i>${esc(p.zhi_wx)}</i></span><span class="natal-pillar-role">${esc(p.shishen_gan)}</span><span class="natal-pillar-note">${esc(p.nayin)}</span><span class="natal-pillar-note">藏干 ${esc(p.hide_gan?.join(' · '))}</span></button>`).join('')}</div></section>`+
    insights(a)+`<section id="natal-periods">${heading('03','沿大运，看时间的节律','每个节点是一段运程；时间范围直接取自排盘结果。')}${timeline((r.da_yun?.list||[]).map(p=>({range:p.start_year+'—'+p.end_year,title:p.ganzhi,note:p.start_age+'岁起'})),'大运 · '+(r.da_yun?.is_forward?'顺行':'逆行'))}</section>`+
    section('命局结构与规则依据',a)+section('大运完整明细',r.da_yun)+section('农历与辅助信息',{lunar:r.lunar,extra:r.extra}));
}
function baziDetail(r,key){
  const [kind,id]=key.split(':');
  if(kind==='pillar'){
    const p=r.pillars[id];if(!p)return '';
    return `<small>四柱细读</small><h4>${esc(p.ganzhi)} · ${esc(({year:'年柱',month:'月柱',day:'日柱',hour:'时柱'})[id])}</h4><p>天干 ${esc(p.gan)}属${esc(p.gan_wx)}，地支 ${esc(p.zhi)}属${esc(p.zhi_wx)}。${id==='day'?'这里的天干就是日主。':'天干十神为'+esc(p.shishen_gan)+'，表示它与日主的五行生克关系。'}藏干：${esc(p.hide_gan?.join('、'))}；地势：${esc(p.dishi)}。</p>`;
  }
  const v=r.wuxing_stats[id]??0;
  return `<small>五行细读 · ${esc(elements[id]?.[1]||'')}</small><h4 style="color:${color(id)}">${esc(id)} · ${v} 个</h4><p>这里统计四柱八个字的表层五行${v===0?'；数量为零表示未出现在表层，藏干中仍可能存在':''}。数量多寡不能单独判断喜忌，请结合季节、日主旺衰与调候阅读。</p>`;
}
// Keep longitude anchors exact; only the glyph label moves when points cluster.
export function placePlanetLabels(entries,asc=0){
  const items=entries.map(([key,p])=>({key,p,angle:((Number(p.lon??p.longitude)-asc)%360+360)%360})).sort((a,b)=>a.angle-b.angle);
  if(!items.length)return [];
  let gap=-1,start=0;
  items.forEach((item,i)=>{const next=items[(i+1)%items.length].angle+(i===items.length-1?360:0);if(next-item.angle>gap){gap=next-item.angle;start=(i+1)%items.length;}});
  const ordered=items.slice(start).concat(items.slice(0,start));
  let previous=-Infinity;
  ordered.forEach((item,i)=>{const unwrapped=item.angle+(i&&item.angle<ordered[0].angle?360:0);item.labelAngle=Math.max(unwrapped,previous+10);previous=item.labelAngle;});
  return ordered;
}
function astroWheel(r,showAspects=true){
  const asc=Number(r.points?.['上升']?.lon||0),pos=(lon,rad)=>polar(180+Number(lon)-asc,rad);
  let svg=`<svg class="natal-wheel" viewBox="0 0 520 520" role="group" aria-label="热带黄道星盘；可选择星体查看位置"><circle cx="260" cy="260" r="248" class="natal-orbit"/><circle cx="260" cy="260" r="235" fill="#0d1421" stroke="#bdb0cf55"/><circle cx="260" cy="260" r="195" class="natal-orbit"/><circle cx="260" cy="260" r="135" class="natal-orbit"/>`;
  for(let i=0;i<360;i+=5){const p=pos(i,231),q=pos(i,i%30===0?196:i%10===0?223:227);svg+=`<path d="M${point(p)} L${point(q)}" stroke="#b4a8c6" stroke-opacity="${i%30===0?.45:.2}"/>`;}
  for(let i=0;i<12;i++){
    const p=pos(i*30+15,214),c=color(signElement(i));
    svg+=`<g role="button" tabindex="0" data-natal-select="sign:${i}" class="natal-svg-control" aria-label="${signs[i]}座">${text(p[0],p[1]+7,zodiac[i],'zodiac-glyph',`fill="${c}"`)}<title>${signs[i]}座 · ${signElement(i)}象</title></g>`;
  }
  for(const [i,h] of (r.houses||[]).entries()){
    const p=pos(h.lon,135),q=pos(h.lon,194),next=r.houses[(i+1)%r.houses.length],sweep=((next.lon-h.lon)%360+360)%360,t=pos(h.lon+sweep/2,145);
    svg+=`<path d="M${point(p)} L${point(q)}" stroke="${h.house===1||h.house===10?'#d3b98b':'#9b9ab3'}" stroke-opacity=".4"/>${text(t[0],t[1]+3,h.house,'house-number')}`;
  }
  if(showAspects)for(const a of r.aspects||[]){
    const p1=r.points[a.p1],p2=r.points[a.p2];if(!p1||!p2)continue;
    const p=pos(p1.lon,132),q=pos(p2.lon,132),c=[90,180].includes(a.angle)?'#d79f9f':'#96b4d5';
    svg+=`<path class="natal-aspect" d="M${point(p)} L${point(q)}" stroke="${c}" stroke-opacity="${a.orb<2?.62:.22}"><title>${esc(a.p1)} ${esc(a.type)} ${esc(a.p2)} · 容许度 ${a.orb}°</title></path>`;
  }
  for(const item of placePlanetLabels(Object.entries(r.points||{}),asc)){
    const {key,p}=item,anchor=pos(p.lon,193),label=polar(180+item.labelAngle,169),name=p.name||key,c=color(p.element),degree=Number(p.deg??p.degree);
    svg+=`<g class="natal-svg-control natal-planet" role="button" tabindex="0" data-natal-select="planet:${esc(key)}" aria-label="${esc(name)} ${esc(p.sign)} ${degree.toFixed(2)}度"><path d="M${point(anchor)} L${point(label)}" stroke="${c}" stroke-opacity=".45"/><circle cx="${anchor[0]}" cy="${anchor[1]}" r="2.5" fill="${c}"/><circle cx="${label[0]}" cy="${label[1]}" r="13" class="planet-hit-target"/>${text(label[0],label[1]+5,glyphs[name]||name,'planet-glyph',`fill="${c}"`)}<title>${esc(name)} · ${esc(p.sign)} ${degree.toFixed(2)}° · 第${p.house}宫${p.retro?' · 逆行':''}</title></g>`;
  }
  svg+=`<circle cx="260" cy="260" r="38" fill="#101725e8"/>${text(260,261,'✦','wheel-heart')}${text(260,281,'NATAL SKY','wheel-signature')}</svg>`;
  return svg;
}
function planetTable(r,vedic=false){
  const points=vedic?r.grahas:r.points;
  return `<div class="natal-positions" aria-label="星体位置">${Object.entries(points||{}).map(([key,p])=>{
    const name=p.name||key,i=p.sign_idx??signs.indexOf(p.sign);
    return `<button data-natal-select="planet:${esc(key)}"><span style="color:${color(signElement(i))}">${esc(glyphs[name]||name)}</span><b>${esc(name)}</b><span>${zodiac[i]||''} ${esc(p.sign)}</span><small>${Number(p.deg??p.degree).toFixed(2)}°</small><em>${(p.retro||p.retrograde)?'逆行':'顺行'}</em>${!vedic?`<small>第 ${p.house} 宫</small>`:''}</button>`;
  }).join('')}</div>`;
}
function astroDetail(r,key){
  const [kind,id]=key.split(':');
  if(kind==='sign'){
    const i=Number(id),members=Object.entries(r.points).filter(([,p])=>p.sign_idx===i).map(([k])=>k);
    return `<small>黄道十二星座 · ${signElement(i)}象</small><h4>${zodiac[i]} ${signs[i]}座</h4><p>本盘落在这里的星体或角点：${esc(members.join('、')||'无')}。外圈每一格为黄道的 30°；内圈宫位由出生时间、地点与宫制计算。</p>`;
  }
  const p=r.points[id];if(!p)return '';
  const aspects=(r.aspects||[]).filter(a=>a.p1===id||a.p2===id).slice(0,3);
  return `<small>星体细读 · ${p.retro?'逆行':'顺行'}</small><h4>${esc(glyphs[id]||'✧')} ${esc(id)} · ${esc(p.sign)} ${Number(p.deg).toFixed(2)}°</h4><p>第 ${p.house} 宫 · ${esc(p.element)}象 · ${esc(p.modality)}星座。${aspects.length?'紧密连接：'+esc(aspects.map(a=>(a.p1===id?a.p2:a.p1)+' '+a.type+'（'+a.orb+'°）').join('、'))+'。':'本盘没有记录与此点的主要相位。'}图上线条连接真实黄经位置，符号通过引线错开。</p>`;
}
function astro(record,section){
  const r=record.result,a=r.analysis||{};
  return shell('astro','THE NATAL SKY · 西方占星','出生时的天空，有你的坐标。','从日月升认识自己，再沿黄道环读星体与宫位。冷蓝与玫瑰色相位线，让盘内关系一眼可见。',
    guide([['natal-core','日月升与星图'],['natal-positions','星体落点'],['natal-balance','元素与结构']])+
    `<section id="natal-core" class="natal-hero"><div class="natal-art"><div data-astro-wheel>${astroWheel(r)}</div><div class="natal-wheel-controls"><label><input type="checkbox" data-natal-aspects checked>显示相位线</label><span><i style="background:#96b4d5"></i>三分／六分等</span><span><i style="background:#d79f9f"></i>四分／对分</span></div><p class="natal-caption">热带黄道 · ${esc(r.house_system)} 宫制 · AC 上升位于左侧</p></div><div class="natal-reading"><div class="natal-reading-label">先认识三个核心</div><div class="natal-big-three">${[['太阳',r.sun_sign,'自我核心 · 主动表达','☉'],['月亮',r.moon_sign,'情绪需要 · 内在感受','☽'],['上升',r.asc_sign,'面对世界 · 呈现方式','AC']].map(([k,v,n,g])=>`<button data-natal-select="planet:${k}"><span>${g}</span><div><small>${k}</small><b>${esc(v)}座</b><p>${n}</p></div></button>`).join('')}</div><p class="natal-caption">符号表示星体，外环表示星座，内圈数字表示宫位；选择任何星体查看具体落点。</p></div></section>`+
    `<aside class="natal-selection" data-natal-detail aria-live="polite">${astroDetail(r,'planet:太阳')}</aside>`+
    `<section id="natal-positions">${heading('02','星体落在何处','符号、名称、度数与宫位一起读；点击任一行查看连接。')}${planetTable(r)}</section>`+
    `<section id="natal-balance">${heading('03','元素与结构的重心','以下为引擎的加权分布；权重并非星体个数。')}<div class="natal-balance"><div>${bars(a.balance?.element,'西占元素加权分布')}</div><div class="natal-facts">${fact('命主星',a.chart_ruler?.planet,a.chart_ruler?.placement)}${fact('主要元素',a.balance?.dom_element,'观察整体表达的侧重')}${fact('主要三态',a.balance?.dom_modality,'本位：启动 · 固定：维持 · 变动：调整')}</div></div></section>`+insights(a)+section('星体、宫位与相位完整明细',{points:r.points,houses:r.houses,aspects:r.aspects})+section('结构分析与计算依据',a));
}
const palacePositions={'巳':[1,1],'午':[2,1],'未':[3,1],'申':[4,1],'酉':[4,2],'戌':[4,3],'亥':[4,4],'子':[3,4],'丑':[2,4],'寅':[1,4],'卯':[1,3],'辰':[1,2]};
const palaceName=name=>name?.endsWith('宫')?name:name+'宫';
function palaceLinks(r){
  const soul=r.palaces.find(p=>p.name==='命宫'),related=r.analysis?.soul_surrounding_palaces||[];
  if(!soul)return '';
  const location=p=>palacePositions[p.earthlyBranch].map(v=>v*100-50),origin=location(soul);
  return `<svg class="natal-palace-links" viewBox="0 0 400 400" preserveAspectRatio="none" aria-hidden="true">${r.palaces.filter(p=>p!==soul&&related.includes(p.name)).map(p=>`<path d="M${origin} L${location(p)}"/>`).join('')}</svg>`;
}
const palaceMeaning={'命宫':'看整体性格与人生主轴，是阅读十二宫的起点。','兄弟':'观察手足、同辈与支持关系。','夫妻':'观察亲密关系与相处模式。','子女':'观察子女、晚辈与创造性的延伸。','财帛':'观察资源、收入与金钱的使用方式。','疾厄':'观察身心与生活习惯的传统象征。','迁移':'观察外部环境、出行与对外表现。','仆役':'观察朋友、合作与人际网络。','交友':'观察朋友、合作与人际网络。','官禄':'观察事业角色与工作方式。','田宅':'观察居所、家庭空间与积累。','福德':'观察内在满足与精神生活。','父母':'观察长辈、传承与支持。'};
function ziweiDetail(r,index){
  const p=r.palaces[index];if(!p)return '';
  const stars=p.majorStars.map(s=>s.name+(s.brightness?'（'+s.brightness+'）':'')+(s.mutagen?' · 化'+s.mutagen:''));
  return `<small>十二宫细读 · ${esc(p.heavenlyStem+p.earthlyBranch)}${p.isBodyPalace?' · 身宫所在':''}</small><h4>${esc(p.name)} · ${esc(stars.join('、')||'无主星')}</h4><p>${esc(palaceMeaning[p.name]||'从这一宫观察对应的人生主题。')}辅星：${esc(p.minorStars?.map(s=>s.name).join('、')||'无')}。${!stars.length?'无主星时需结合对宫与三方四正阅读。':''}${p.decadal?.range?'本宫大限：'+p.decadal.range.join('—')+'岁。':''}</p>`;
}
function ziwei(record,section){
  const r=record.result,a=r.analysis||{},soul=r.palaces.findIndex(p=>p.name==='命宫'),surround=a.soul_surrounding_palaces||[];
  return shell('ziwei','THE TWELVE PALACES · 紫微斗数','十二宫，铺开人生的不同面向。','从金色命宫开始，紫色标记身宫，微光连接命宫三方四正。点击宫位，读懂它关注的人生主题。',
    guide([['natal-core','从命宫开始'],['natal-mutagens','看本命四化'],['natal-periods','沿大限阅读']])+
    `<section id="natal-core"><div class="natal-palaces">${palaceLinks(r)}<div class="natal-palace-center"><div class="palace-constellation" aria-hidden="true">✧</div><small>紫 微 斗 数</small><h3>${esc(r.birth.fiveElementsClass)}</h3><p>命主 ${esc(r.birth.soul)}<br>身主 ${esc(r.birth.body)}</p><span>金 · 命宫　紫 · 身宫<br>微光 · 三方四正</span></div>${r.palaces.map((p,i)=>{const pos=palacePositions[p.earthlyBranch]||[1,1];return `<button class="natal-palace ${i===soul?'is-soul':''} ${p.isBodyPalace?'is-body':''} ${surround.includes(p.name)?'is-related':''}" style="grid-column:${pos[0]};grid-row:${pos[1]}" data-natal-select="palace:${i}" aria-pressed="${i===soul}"><span class="palace-caption">${esc(p.earthlyBranch)}${p.isBodyPalace?' · 身宫':''}</span><h4>${esc(p.name)}</h4><div class="palace-stars">${p.majorStars.map(s=>`<span>${esc(s.name)}${s.mutagen?`<em class="mutagen-${esc(s.mutagen)}">${esc(s.mutagen)}</em>`:''}</span>`).join('')||'<span class="palace-empty">无主星 · 参看对宫</span>'}</div><small>${esc(p.minorStars.map(s=>s.name).join(' · '))}</small><span class="palace-age">${esc(p.decadal?.range?.join('—')||'')}岁</span></button>`;}).join('')}</div></section>`+
    `<aside class="natal-selection" data-natal-detail aria-live="polite">${ziweiDetail(r,soul)}</aside>`+
    `<section id="natal-mutagens">${heading('02','四化，四种变化的线索','禄、权、科、忌是观察重点；请结合所在宫位一起看。')}<div class="natal-mutagens">${(a.natal_mutagens||[]).map(v=>{const idx=r.palaces.findIndex(p=>p.name===v.palace);return `<button data-natal-select="palace:${idx}"><span class="mutagen-${esc(v.mutagen)}">${esc(v.mutagen)}</span><b>${esc(v.star)}</b><small>${esc(v.palace)}宫</small><p>${({禄:'资源与顺势',权:'主动与掌握',科:'声誉与条理',忌:'牵挂与课题'})[v.mutagen]||''}</p></button>`;}).join('')}</div></section>`+
    `<section id="natal-periods">${heading('03','大限，依次展开的篇章','大限年份与年龄范围取自原始排盘。')}${timeline((r.decadals||[]).map(p=>({range:p.yearRange?.join('—'),title:palaceName(p.palaceName),note:p.ageRange?.join('—')+'岁'})),'十二宫大限')}</section>`+
    section('本命结构完整依据',a)+section('全部宫位与杂曜',r.palaces)+section('命盘信息与大限明细',{birth:r.birth,decadals:r.decadals})+(r.annual?section('流年',r.annual):''));
}
function southIndian(r,varga='d1'){
  const chart=r[varga],slots=[[2,1],[3,1],[4,1],[4,2],[4,3],[4,4],[3,4],[2,4],[1,4],[1,3],[1,2],[1,1]];
  return `<div class="natal-rashi"><div class="rashi-center"><span>✧</span><h3>${varga.toUpperCase()}</h3><p>${varga==='d1'?'RĀŚI · 本命盘':'NAVĀṂŚA · 九分盘'}</p><small>上升 ${esc(chart.lagna.sign)}<br>${Number(chart.lagna.degree).toFixed(2)}°</small></div>${signs.map((s,i)=>{const members=Object.entries(chart.points).filter(([,p])=>p.sign_idx===i),house=(i-chart.lagna.sign_idx+12)%12+1;return `<button style="grid-column:${slots[i][0]};grid-row:${slots[i][1]};--element:${color(signElement(i))}" class="rashi-sign ${house===1?'is-lagna':''}" data-natal-select="rashi:${i}"><small>${zodiac[i]} ${s}<em>第${house}宫</em></small>${house===1?'<b class="rashi-asc">AC · 上升</b>':''}<div>${members.map(([k])=>`<span>${esc(glyphs[planetNames[k]])} ${esc(planetNames[k])}</span>`).join('')||'<span class="rashi-empty">—</span>'}</div></button>`;}).join('')}</div>`;
}
function jyotishDetail(r,key,varga='d1'){
  const [kind,id]=key.split(':');
  if(kind==='rashi'){
    const chart=r[varga],idx=Number(id),members=Object.entries(chart.points).filter(([,p])=>p.sign_idx===idx),house=(idx-chart.lagna.sign_idx+12)%12+1;
    return `<small>${varga.toUpperCase()} · 整宫制</small><h4>${zodiac[idx]} ${signs[idx]}座 · 第 ${house} 宫</h4><p>落入此宫：${esc(members.map(([k,p])=>planetNames[k]+' '+Number(p.degree).toFixed(2)+'°').join('、')||'无九曜')}。南印度盘固定星座位置，宫位从上升星座起顺数；D1 与 D9 分别计算，不能混用。</p>`;
  }
  const p=r.grahas[id];if(!p)return '';
  return `<small>九曜细读 · D1 恒星黄道${p.retrograde?' · 逆行':''}</small><h4>${esc(glyphs[p.name])} ${esc(p.name)} · ${esc(p.sign)} ${Number(p.degree).toFixed(2)}°</h4><p>月宿 ${esc(p.nakshatra?.name)} · 第 ${p.nakshatra?.pada}足（Pada） · 月宿主星 ${esc(planetNames[p.nakshatra?.lord]||p.nakshatra?.lord)}。${r.d1.points[id]?'D1 第 '+r.d1.points[id].house+' 宫；D9 第 '+r.d9.points[id].house+' 宫。':''}</p>`;
}
function jyotish(record,section){
  const r=record.result,a=r.analysis||{},moon=a.moon_nakshatra||{},period=r.vimshottari||{};
  return shell('jyotish','THE SIDEREAL PATH · 印度占星','九曜与月宿，展开另一重星空。','Lahiri 恒星黄道，南印度式固定星座宫盘。切换 D1 与 D9 对照观察，再沿 Vimshottari 时间线阅读。',
    guide([['natal-core','D1 与 D9 宫盘'],['natal-positions','九曜与月宿'],['natal-periods','大运时间线']])+
    `<section id="natal-core" class="natal-hero"><div class="natal-art"><div class="natal-varga-tabs" role="group" aria-label="分盘选择"><button data-natal-varga="d1" aria-pressed="true">D1 · 本命盘</button><button data-natal-varga="d9" aria-pressed="false">D9 · 九分盘</button></div><div data-natal-varga-chart>${southIndian(r)}</div><p class="natal-caption">固定星座 · 整宫制 · 金边为当前分盘上升宫</p></div><div class="natal-reading"><div class="natal-reading-label">先看上升与月亮</div><h3>上升 · ${esc(r.d1.lagna.sign)}</h3><p>D1 是本命结构的起点，D9 用于补充观察，D9 上升对出生时刻尤其敏感。</p><div class="natal-facts">${fact('命主星',planetNames[a.lagna_lord?.planet],a.lagna_lord?.sign+' · 第'+a.lagna_lord?.house+'宫')}${fact('月亮月宿',moon.name,'Pada '+moon.pada+' · 月宿主星 '+(planetNames[moon.lord]||moon.lord),'☽')}${fact('出生时大运',planetNames[period.at_birth?.mahadasha],`出生余额 ${Number(period.birth_balance_years).toFixed(2)} 年`,'◷')}</div><p class="natal-caption">“出生时大运”只描述出生时的区段；完整表中包含出生前已经开始的大运。</p></div></section>`+
    `<aside class="natal-selection" data-natal-detail aria-live="polite">${jyotishDetail(r,'planet:Moon')}</aside>`+
    `<section id="natal-positions">${heading('02','九曜与月宿','落点显示 D1 黄经；点选后查看月宿、足与分盘宫位。')}${planetTable(r,true)}</section>`+
    `<section id="natal-periods">${heading('03','Vimshottari 大运','日期按 UTC 标记；每段起点包含、终点不包含。')}${timeline((period.mahadashas||[]).map(p=>({range:p.start_utc?.slice(0,10)+' → '+p.end_utc?.slice(0,10),title:planetNames[p.lord]||p.lord,note:p.years+' 年'})),'大运 · UTC')}</section>`+
    section('九曜、月宿与 D1／D9 完整明细',{grahas:r.grahas,d1:r.d1,d9:r.d9})+section('大运与子运完整时间表',period)+section('结构事实',a));
}
export function renderNatalChart(record,{section}){
  return ({bazi,astro,ziwei,jyotish})[record.module]?.(record,section)||'';
}
export function mountNatalInteractions(root,record){
  if(!root.querySelector('.natal-experience'))return;
  let varga='d1';
  const select=key=>{
    const detail=root.querySelector('[data-natal-detail]');
    const r=record.result;
    const html=record.module==='bazi'?baziDetail(r,key):record.module==='astro'?astroDetail(r,key):record.module==='ziwei'?ziweiDetail(r,Number(key.split(':')[1])):jyotishDetail(r,key,varga);
    if(detail&&html){detail.innerHTML=html;root.querySelectorAll('[data-natal-select]').forEach(b=>{b.classList.toggle('is-selected',b.dataset.natalSelect===key);b.setAttribute('aria-pressed',String(b.dataset.natalSelect===key));});}
    if(detail&&html)detail.scrollIntoView({block:'nearest',behavior:document.body.classList.contains('reduced')?'instant':'smooth'});
  };
  root.onclick=e=>{
    const control=e.target.closest('[data-natal-select]');if(control)select(control.dataset.natalSelect);
    const jump=e.target.closest('[data-natal-jump]');if(jump)root.querySelector('#'+jump.dataset.natalJump)?.scrollIntoView({behavior:document.body.classList.contains('reduced')?'instant':'smooth',block:'start'});
    const tab=e.target.closest('[data-natal-varga]');if(tab){varga=tab.dataset.natalVarga;root.querySelectorAll('[data-natal-varga]').forEach(b=>b.setAttribute('aria-pressed',String(b===tab)));root.querySelector('[data-natal-varga-chart]').innerHTML=southIndian(record.result,varga);select('rashi:'+record.result[varga].lagna.sign_idx);}
  };
  root.onkeydown=e=>{if((e.key==='Enter'||e.key===' ')&&e.target.matches('g[data-natal-select]')){e.preventDefault();select(e.target.dataset.natalSelect);}};
  const toggle=root.querySelector('[data-natal-aspects]');if(toggle)toggle.onchange=()=>{root.querySelector('[data-astro-wheel]').innerHTML=astroWheel(record.result,toggle.checked);};
}

export function mountNatalWorkspace(workspace){
  const layout=workspace.querySelector('.space-layout'),panel=layout?.querySelector('.input-panel');
  if(!layout||!panel)return null;
  layout.classList.add('natal-layout');
  const edge=document.createElement('div');edge.className='natal-edge';edge.innerHTML='<button aria-controls="natal-input-panel" aria-expanded="false">生辰与规则</button>';
  panel.id='natal-input-panel';
  const close=document.createElement('button');close.type='button';close.className='natal-close-sidebar';close.textContent='收起侧栏 ←';panel.prepend(close);layout.append(edge);
  let immersive=false;
  const drawer=open=>{document.body.classList.toggle('natal-drawer-open',open);edge.querySelector('button').setAttribute('aria-expanded',String(open));panel.inert=immersive&&!open;};
  const focusControl=()=>workspace.querySelector('#natal-immersive-toggle')||edge.querySelector('button');
  const setImmersive=value=>{immersive=value;document.body.classList.toggle('natal-immersive',value);drawer(false);const b=workspace.querySelector('#natal-immersive-toggle');if(b){b.textContent=value?'退出沉浸 ↙':'沉浸看盘 ↗';b.setAttribute('aria-pressed',String(value));}};
  close.onclick=()=>{drawer(false);edge.querySelector('button').focus();};
  edge.querySelector('button').onclick=()=>{drawer(true);close.focus();};
  edge.onpointerenter=e=>{if(e.pointerType==='mouse')drawer(true);};
  const outside=e=>{if(immersive&&document.body.classList.contains('natal-drawer-open')&&!panel.contains(e.target)&&!edge.contains(e.target))drawer(false);};
  const key=e=>{if(e.key==='Escape'&&immersive&&!document.body.classList.contains('focus-mode')&&!document.querySelector('.modal,#control-options:not([hidden]),.music-panel:not([hidden])')){e.preventDefault();e.stopImmediatePropagation();if(document.body.classList.contains('natal-drawer-open'))drawer(false);else setImmersive(false);focusControl().focus();}};
  document.addEventListener('pointerdown',outside);document.addEventListener('keydown',key,true);
  return {attach(auto=false){const toolbar=workspace.querySelector('.result-header>.toolbar');if(toolbar&&!workspace.querySelector('#natal-immersive-toggle')){const b=document.createElement('button');b.id='natal-immersive-toggle';b.className='secondary';b.onclick=()=>setImmersive(!immersive);toolbar.prepend(b);}setImmersive(auto||immersive);},dispose(){panel.inert=false;document.body.classList.remove('natal-immersive','natal-drawer-open');document.removeEventListener('pointerdown',outside);document.removeEventListener('keydown',key,true);}};
}
