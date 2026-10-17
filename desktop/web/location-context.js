// Location is optional context, never the source of secure randomness.
// Keep only coarse coordinates in memory, and send a fresh salted commitment locally.
const hex=bytes=>Array.from(bytes,b=>b.toString(16).padStart(2,'0')).join('');
export function coarsePosition(latitude,longitude){
  if(typeof latitude!=='number'||typeof longitude!=='number'||!Number.isFinite(latitude)||!Number.isFinite(longitude)||Math.abs(latitude)>90||Math.abs(longitude)>180)throw Error('请填写有效的纬度（-90～90）和经度（-180～180）。');
  return {latitude:Math.round(latitude*100)/100,longitude:Math.round(longitude*100)/100};
}
export function createLocationContext({geolocation=()=>navigator.geolocation,crypto=globalThis.crypto,now=()=>Date.now(),onChange=()=>{},setTimer=setTimeout,clearTimer=clearTimeout}={}){
  let position=null,source=null,at=0,generation=0,pending=false,message='未启用定位，仍可正常问事。',disposed=false,timer=null,cancelPending=null;
  function notify(){if(!disposed)onChange(snapshot());}
  function expire(){if(position&&now()-at>=600000){position=null;source=null;message='位置已超过 10 分钟，请重新获取或填写。';}}
  function snapshot(){expire();return {pending,ready:!!position,source:position?source:null,message};}
  function cancel(){generation++;clearTimer(timer);timer=null;if(cancelPending){cancelPending();cancelPending=null;}pending=false;}
  function clear(){cancel();position=null;source=null;message='已清除位置，仍可正常问事。';notify();}
  function manual(latitude,longitude){const next=coarsePosition(latitude,longitude);cancel();position=next;source='manual';at=now();message='手填大致位置已准备 · 仅用于下一次随机，10 分钟内有效。';notify();}
  async function request(){
    cancel();const id=generation;position=null;source=null;pending=true;message='等待定位授权与结果…可随时取消。';notify();
    await new Promise(resolve=>{
      let settled=false;cancelPending=()=>{settled=true;resolve();};
      const finish=(value,error)=>{if(settled||disposed||id!==generation)return;settled=true;clearTimer(timer);timer=null;cancelPending=null;pending=false;
        if(value){try{position=coarsePosition(value.coords.latitude,value.coords.longitude);source='device';at=now();message='系统大致位置已准备 · 仅用于下一次随机，10 分钟内有效。';}catch{message='定位结果无效，可手填大致位置或直接继续。';}}
        else message=error?.code===1?'未获得定位授权，可手填大致位置或直接继续。':error?.code===3?'定位超时，可手填大致位置或直接继续。':'暂时无法定位，可手填大致位置或直接继续。';notify();resolve();};
      timer=setTimer(()=>finish(null,{code:3}),10000);
      try{const provider=geolocation();if(!provider?.getCurrentPosition){finish(null,{code:2});return;}provider.getCurrentPosition(p=>finish(p),e=>finish(null,e),{enableHighAccuracy:false,timeout:8000,maximumAge:0});}catch{finish(null,{code:2});}
    });
  }
  async function take(){
    expire();if(pending)throw Error('定位还在等待结果。可取消定位后继续，或稍候再开始。');if(!position||disposed)return null;
    const current=position,kind=source,id=generation;position=null;source=null;message='大致位置已提交本次随机；再次准备时需重新获取或填写。';notify();
    const nonce=new Uint8Array(32);crypto.getRandomValues(nonce);
    const data=new TextEncoder().encode(JSON.stringify({domain:'mystery-location-v1',nonce:hex(nonce),...current}));
    const commitment=hex(new Uint8Array(await crypto.subtle.digest('SHA-256',data)));
    if(disposed||id!==generation)return null;
    return {schema:'location-input-v1',source:kind,commitment};
  }
  function dispose(){disposed=true;cancel();position=null;source=null;}
  return {request,manual,clear,take,snapshot,dispose};
}
