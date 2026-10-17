import assert from 'node:assert/strict';
import {createCandleCenter} from '../desktop/web/candles.js';
import * as THREE from '../desktop/web/vendor/three.module.js';
import {createAnswerBook} from '../desktop/web/answer-book.js';
import {coinFaces,coinPosition,deckLayout,visualDeckOrder,holdingPosition,orbitView,CARD_THICKNESS,spreadPosition,addYao,createCard} from '../desktop/web/ritual-models.js';

for(const value of [6,7,8,9])for(let step=0;step<6;step++){
  const faces=coinFaces(value,step);
  assert.equal(faces.reduce((a,b)=>a+b),value,'Rendered coin faces must equal the recorded line');
  assert(faces.every(f=>f===2||f===3));
}
for(const t of [0,.1,.25,.5,.75,.9,1]){
  const positions=[0,1,2].map(i=>coinPosition(i,t,1.5));
  for(const axis of [0,2])assert(Math.abs(positions.reduce((s,p)=>s+p[axis],0))<1e-8,'Coins stay centered on the table throughout every throw');
}
assert.deepEqual(coinPosition(1),[0,.05,0]);
for(const size of [36,78]){
  const layout=deckLayout(size);assert.equal(layout.length,size);
  assert.equal(new Set(layout.map(p=>`${p.x},${p.y},${p.z}`)).size,size);
  for(const p of layout){assert(Math.abs(Math.hypot(p.x,p.z)-4.85)<1e-8,'Every hidden slot must sit on the same circular ring');assert(4.85+.85*p.scale<6.3,'The full card must remain on the table');assert(4.85-.85*p.scale>4,'Candles and selected cards need a clear center');}
  const p=layout[0];assert(.88*p.scale/2<(4.85-1.43*p.scale/2)*Math.tan(Math.PI/size),'Every card fits inside its own radial sector, including seam; none can cover a neighbor');
  assert.equal(new Set(layout.map(p=>p.y)).size,1,'The full ring is on a single plane');
  const order=visualDeckOrder(size);assert.equal(new Set(order).size,size);assert(order.every(n=>n>=0&&n<size));

}
assert(CARD_THICKNESS<.005,'Cards must have paper-like thickness');
assert.equal(orbitView(0,.9,30,0).elevation,.9);assert.notEqual(orbitView(0,.9,30,0).yaw,0);
assert(orbitView(0,.9,0,10000).elevation<=1.3);assert(orbitView(0,.9,0,-10000).elevation>=.55);
const holding=Array.from({length:10},(_,i)=>holdingPosition(i,10));assert.equal(new Set(holding.map(String)).size,10);
for(const count of [1,3,5]){
  const positions=Array.from({length:count},(_,i)=>spreadPosition(i,count,'three'));
  for(let i=1;i<count;i++)assert(positions[i][0]>positions[i-1][0],'Linear cards retain selection order');
}
const celtic=Array.from({length:10},(_,i)=>spreadPosition(i,10,'celtic'));
assert.deepEqual(celtic[0],celtic[1],'Challenge card crosses the present card');
assert(celtic[2][1]>celtic[0][1]&&celtic[4][1]<celtic[0][1],'Foundation below, goal above');
assert(celtic[6][1]>celtic[9][1],'Right-hand staff runs from self to outcome');
const group=new THREE.Group();
for(const value of [6,7,8,9]){
  const yao=addYao(group,value,value-6,0);
  assert.equal(yao.children.length,value%2?1:2,'Solid/broken lines must agree with the recorded yin/yang');
}
assert(group.children[0].position.z>group.children[3].position.z,'Initial line starts nearest the viewer');
const card=createCard(null);assert(card.children.some(c=>c.geometry.type==='BoxGeometry'));
assert(card.userData.front.position.y<0,'Card face remains underneath until the flip');
const candleScene=new THREE.Group(),candles=createCandleCenter(candleScene);assert.equal(candles.flames.length,3);assert.equal(candles.lights.length,3);candles.update(0);candles.update(1);assert(candles.flames[0].material.uniforms.uTime.value>0);const frozen=candles.flames[0].material.uniforms.uTime.value;candles.update(2,true);assert.equal(candles.flames[0].material.uniforms.uTime.value,frozen);candles.group.position.z=-3.85;candles.reset();assert.equal(candles.group.position.z,0);


const answerBook=createAnswerBook(new THREE.Group(),()=>null);answerBook.setOpen(0);const closedBounds=new THREE.Box3().setFromObject(answerBook.root);assert(closedBounds.min.y>-.14,'Closed book does not sink into the table');answerBook.setOpen(1);assert(Math.abs(answerBook.root.position.x)<1e-9);assert.equal(answerBook.root.userData.open,1);assert(new THREE.Box3().setFromObject(answerBook.root).min.y>-.14,'Open covers remain above the table');

console.log('PASS: coin face sums, all 78/36 cards on circular ring with seam clearance, three animated/frozen candle flames, paper thickness, orbit limits, linear order, Celtic cross semantics, bottom-up yin/yang, physical card front/back');
