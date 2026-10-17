import {deviceTimeZone} from './device-location.js';
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export const reminderKey=r=>r.viewer_time.slice(0,10)+'|'+r.items.map(p=>p.id+':'+p.friend_date+':'+p.days).join(',');
export function mountBirthdayReminders(host,{api,getPrefs,persist,getZone=()=>deviceTimeZone(),onPerson}){
  host.className='birthday-reminders';host.hidden=true;host.innerHTML='<section class="reminder-panel glass" hidden role="region" aria-label="近期生日提醒"><header><div><small>UPCOMING BIRTHDAYS</small><h3>值得记住的日子</h3></div><button type="button" id="reminder-close" aria-label="关闭生日提醒">×</button></header><div id="reminder-items" aria-live="polite"></div><p id="reminder-clock" class="subtle"></p></section>';
  const panel=host.querySelector('.reminder-panel');let serial=0,hasItems=false;
  function open(value){host.hidden=!value||!hasItems;panel.hidden=host.hidden;}
  host.querySelector('#reminder-close').onclick=()=>open(false);
  async function refresh({announce=false,force=false}={}){
    const ticket=++serial;if(getPrefs().birthday_reminders_enabled===false){open(false);return;}
    try{
      const result=await api('birthday-reminders',{viewer_zone:getZone()||deviceTimeZone(),now:new Date().toISOString()});if(ticket!==serial)return;
      hasItems=!!result.items.length;host.dataset.reminderCount=String(result.items.length);
      host.querySelector('#reminder-items').innerHTML=result.items.map(p=>`<button type="button" class="reminder-person" data-person="${esc(p.id)}"><i style="--person-color:${/^#[a-f0-9]{6}$/i.test(p.color)?p.color:'#cbb6d5'}"></i><div><b>${esc(p.name)} <em>${p.days===0?'今天生日':p.days===1?'明天生日':p.days+' 天后生日'}</em></b><span>${esc(p.birthday_date)} · ${esc(p.place||p.tz_name)}</span>${p.zone_source==='birth'?'<span>按出生地当地日期提醒</span>':''}${p.leap_adjusted?'<span>2 月 29 日生日，本平年按 2 月 28 日提醒</span>':''}</div><small>查看 ›</small></button>`).join('');
      host.querySelector('#reminder-clock').textContent='未来五天及当天 · 按每位朋友的当地日期计算';
      for(const b of host.querySelectorAll('[data-person]'))b.onclick=()=>{open(false);onPerson(b.dataset.person);};
      if(!hasItems){open(false);return;}
      const key=reminderKey(result);
      if((force||(announce&&getPrefs().reminders_last_shown!==key))&&!document.body.classList.contains('focus-mode')){open(true);getPrefs().reminders_last_shown=key;persist();}
    }catch{/* No floating status when there is no actionable reminder. */}
  }
  const timer=setInterval(()=>refresh({announce:true}),60000),visible=()=>{if(!document.hidden)refresh({announce:true});};document.addEventListener('visibilitychange',visible);
  return {refresh,open,dispose(){clearInterval(timer);document.removeEventListener('visibilitychange',visible);serial++;host.replaceChildren();}};
}
