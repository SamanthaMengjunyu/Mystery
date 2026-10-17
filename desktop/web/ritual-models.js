import * as THREE from './vendor/three.module.js';

export function spreadPosition(index,count,key){
  if(key==='celtic')return [[-.65,0],[-.65,0],[-.65,1.65],[-2.25,0],[-.65,-1.65],[1.05,0],[2.6,2.4],[2.6,.8],[2.6,-.8],[2.6,-2.4]][index];
  return [(index-(count-1)/2)*Math.min(1.55,6.2/count),0];
}
export function coinFaces(value,step=0){const n=value-6;return Array.from({length:3},(_,i)=>(i+step)%3<n?3:2);}
export function coinPosition(index,t=0,power=1){const wave=Math.sin(t*Math.PI),bounce=Math.abs(Math.sin(t*Math.PI*2.5))*Math.pow(1-t,1.6);return [(index-1)*(.78+wave*.3),.05+bounce*(1.7+power*.7),(index-1)*wave*.45];}
export const CARD_THICKNESS=.004;
export function deckLayout(count){
  const radius=4.85,scale=count>40?.39:.78;
  return Array.from({length:count},(_,i)=>{const angle=-Math.PI/2+i*Math.PI*2/count;
    return {x:Math.sin(angle)*radius,y:.045,z:Math.cos(angle)*radius,rotation:angle,scale};});
}
export function visualDeckOrder(count,fill=bytes=>crypto.getRandomValues(bytes)){
  const order=Array.from({length:count},(_,i)=>i),word=new Uint32Array(1);
  for(let i=count-1;i>0;i--){const limit=2**32-2**32%(i+1);do{fill(word);}while(word[0]>=limit);const j=word[0]%(i+1);[order[i],order[j]]=[order[j],order[i]];}return order;
}
export function holdingPosition(index,count){return [(index%5-(Math.min(count,5)-1)/2)*(count>5?.95:1),count>5?1.9+Math.floor(index/5)*.95:2.35];}
export function orbitView(yaw,elevation,dx,dy){return {yaw:yaw-dx*.006,elevation:THREE.MathUtils.clamp(elevation+dy*.004,.55,1.3)};}
export function createTable(scene,candlelit=false){
  const base=new THREE.Mesh(new THREE.CircleGeometry(6.3,120),new THREE.MeshStandardMaterial({color:candlelit?0x10131b:0x111d2c,metalness:candlelit?.18:.35,roughness:candlelit?.88:.65,transparent:true,opacity:.88}));base.rotation.x=-Math.PI/2;base.position.y=-.14;base.receiveShadow=true;scene.add(base);
  for(const r of [5.65,5.8]){const ring=new THREE.Mesh(new THREE.TorusGeometry(r,.009,6,144),new THREE.MeshBasicMaterial({color:candlelit?0xa28b60:0x7789a1,transparent:true,opacity:.23}));ring.rotation.x=-Math.PI/2;ring.position.y=-.12;scene.add(ring);}
}
export function createCoin(top,bottom){
  const coin=new THREE.Mesh(new THREE.CylinderGeometry(.33,.33,.065,48),[new THREE.MeshStandardMaterial({color:0x8c7548,metalness:.8,roughness:.38}),new THREE.MeshStandardMaterial({map:top,metalness:.6,roughness:.45}),new THREE.MeshStandardMaterial({map:bottom,metalness:.6,roughness:.45})]);coin.castShadow=true;coin.receiveShadow=true;return coin;
}
export function createCard(back){
  const group=new THREE.Group(),edge=new THREE.MeshStandardMaterial({color:0x9c978a,roughness:.9}),rear=new THREE.MeshStandardMaterial({map:back,roughness:.65});
  const body=new THREE.Mesh(new THREE.BoxGeometry(.88,CARD_THICKNESS,1.43),edge);body.castShadow=true;group.add(body);
  const backFace=new THREE.Mesh(new THREE.PlaneGeometry(.86,1.41),rear);backFace.rotation.x=-Math.PI/2;backFace.position.y=CARD_THICKNESS/2+.0008;group.add(backFace);group.userData.back=backFace;
  const front=new THREE.Mesh(new THREE.PlaneGeometry(.86,1.41),new THREE.MeshStandardMaterial({color:0xe4d8bd,roughness:.85}));front.rotation.x=Math.PI/2;front.position.y=-CARD_THICKNESS/2-.0008;group.add(front);group.userData.front=front;return group;
}
export function addYao(parent,value,index,x=1.8){
  const group=new THREE.Group(),yang=value===7||value===9,moving=value===6||value===9;
  const material=new THREE.MeshStandardMaterial({color:moving?0xd7b477:0xb4c2d5,emissive:moving?0x38260a:0x111a28,roughness:.5,metalness:.45});
  for(const sign of yang?[0]:[-1,1]){const mesh=new THREE.Mesh(new THREE.BoxGeometry(yang?1.45:.61,.065,.13),material);mesh.position.x=sign*.43;group.add(mesh);}
  group.position.set(x,.03,1.6-index*.48);parent.add(group);return group;
}
