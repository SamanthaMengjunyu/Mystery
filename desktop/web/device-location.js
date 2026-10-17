import {coarsePosition} from './location-context.js';
const hex=bytes=>Array.from(bytes,b=>b.toString(16).padStart(2,'0')).join('');
export function deviceTimeZone(){try{return Intl.DateTimeFormat().resolvedOptions().timeZone||'UTC';}catch{return 'UTC';}}
export function createDeviceLocation({api,getPrefs,onChange=()=>{},geolocation=()=>navigator.geolocation,crypto=globalThis.crypto,now=()=>performance.now(),setTimer=setTimeout,clearTimer=clearTimeout}){
  let position=null,at=0,generation=0,pending=false,state=getPrefs().location_enabled?'idle':'off',label='',zone='',message=getPrefs().location_enabled?'首次使用定位前，需要你授权。':'定位已关闭；生日提醒仍可按设备时区运行。',timer=null,cancelPending=null;
  const allowed=()=>getPrefs().location_enabled&&getPrefs().location_consent==='granted';
  function snapshot(){if(position&&now()-at>=600000)position=null;return {enabled:!!getPrefs().location_enabled,pending,state,label,zone,deviceZone:deviceTimeZone(),message};}
  const notify=()=>onChange(snapshot());
  function clear(){generation++;clearTimer(timer);timer=null;cancelPending?.();cancelPending=null;position=null;pending=false;label='';zone='';state='off';message='定位已关闭；生日提醒仍可按设备时区运行。';notify();}
  async function request(){if(!allowed())return;generation++;const id=generation;clearTimer(timer);cancelPending?.();position=null;pending=true;state='pending';message='正在请求系统大致定位…';notify();
    await new Promise(resolve=>{let settled=false;cancelPending=()=>{settled=true;resolve();};const finish=async(value,error)=>{if(settled||id!==generation)return;settled=true;clearTimer(timer);timer=null;cancelPending=null;pending=false;if(!value){state=error?.code===1?'denied':'unavailable';message=error?.code===1?'系统未允许定位。可以在设置中重试；生日提醒仍按设备时区运行。':error?.code===3?'定位超时，暂按设备时区继续。':'暂时无法取得位置，按设备时区继续。';notify();resolve();return;}try{position=coarsePosition(value.coords.latitude,value.coords.longitude);at=now();const place=await api('device-place',position);if(id!==generation)return;label=place.label;zone=place.tz_name||'';state='ready';message=`${label} · ${zone||deviceTimeZone()}。大致坐标只暂存在内存。`;}catch{if(id===generation){state='ready';message='已取得大致位置，地点匹配暂不可用；继续使用设备时区。';}}finally{if(id===generation)notify();resolve();}};timer=setTimer(()=>finish(null,{code:3}),10000);try{const provider=geolocation();if(!provider?.getCurrentPosition){finish(null,{code:2});return;}provider.getCurrentPosition(p=>finish(p),e=>finish(null,e),{enableHighAccuracy:false,timeout:8000,maximumAge:600000});}catch{finish(null,{code:2});}});
  }
  async function entropy(){snapshot();if(!allowed()||!position||pending)return null;const current=position,id=generation,nonce=new Uint8Array(32);crypto.getRandomValues(nonce);const bytes=new TextEncoder().encode(JSON.stringify({domain:'mystery-location-v1',nonce:hex(nonce),...current}));const commitment=hex(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)));return id===generation&&allowed()?{commitment,source:'device'}:null;}
  return {snapshot,request,clear,entropy};
}
