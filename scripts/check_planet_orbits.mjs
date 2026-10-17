// Run with Node.js: verify the actual scene objects stay bound during interaction.
import assert from 'node:assert/strict';
import * as THREE from '../desktop/web/vendor/three.module.js';
import {createStarTrails} from '../desktop/web/star-trails.js';
import {NODE_LAYOUT} from '../desktop/web/node-layout.js';
import {resolvePreferences} from '../desktop/web/preferences.js';
import {createBirthStar} from '../desktop/web/central-star.js';

globalThis.document={body:{dataset:{}}};
const ids=['charts','oracles','quiet','bazi','ziwei','astro','jyotish','liuyao','meihua','tarot','lenormand','answers'];
const nodes=ids.map(id=>({id,p:new THREE.Vector3(...NODE_LAYOUT[id].position),radius:NODE_LAYOUT[id].radius,btn:{style:{setProperty(){}},classList:{toggle(){}}}}));
const parent=new THREE.Group(),system=createStarTrails(parent,nodes);
const ribbons=parent.children.find(obj=>obj.material?.uniforms?.uStates);
const attrs=ribbons.geometry.attributes,camera=new THREE.Vector3(0,1,21);
const context={progress:1,near:true,region:''};
let time=0;
function step(){system.update(time+=.1,'home',camera,context);}
function assertBound(){
  for(let i=0;i<nodes.length;i++){
    const index=(i*(160+1)+160)*2;
    const x=new THREE.Vector3().fromBufferAttribute(attrs.aAxisX,index),y=new THREE.Vector3().fromBufferAttribute(attrs.aAxisY,index);
    const radius=attrs.aOrbit.getX(index),ratio=attrs.aOrbit.getY(index),angle=ribbons.material.uniforms.uStates.value[i].x;
    const head=x.multiplyScalar(radius*Math.cos(angle)).addScaledVector(y,radius*ratio*Math.sin(angle));
    assert(head.distanceTo(nodes[i].body.position)<2e-6,`${nodes[i].id}: orbit tail must terminate at its own planet`);
    assert(nodes[i].body.position.equals(nodes[i].p),`${nodes[i].id}: label must share the planet anchor`);
  }
}
system.preferences({reduced:false,quality:'high'});
for(let i=0;i<120;i++){step();assertBound();}
assert.equal(document.body.dataset.visiblePlanets,'9');
system.hover('tarot');
const locked=nodes[9].p.clone(),moving=nodes[3].p.clone();
for(let i=0;i<30;i++)step();
assert(nodes[9].p.equals(locked),'Focused planet must stay still');
assert(!nodes[3].p.equals(moving),'Unfocused planets continue orbiting');
assert.equal(document.body.dataset.highlightedOrbit,'tarot');assertBound();
system.hover('');system.preferences({reduced:true,quality:'high'});
const frozen=nodes.map(n=>n.p.clone());
for(let i=0;i<10;i++)step();
assert(nodes.every((n,i)=>n.p.equals(frozen[i])),'Reduced motion preserves all static planet/orbit pairs');
const fullCount=nodes[0].body.geometry.attributes.position.count;
system.preferences({reduced:true,quality:'low'});
assert(nodes[0].body.geometry.attributes.position.count<fullCount,'Low quality reduces sphere geometry');
assert.equal(document.body.dataset.boundOrbits,'12');assertBound();
system.select('tarot');system.update(time+=1,'module',camera,context);
assert(nodes[9].body.visible&&nodes.filter(n=>n.body.visible).length===1,'Function page preserves only its selected planet');
system.activate('answers');assert.equal(document.body.dataset.activatedPlanet,'answers');
// Test the shipped layout through the real perspective camera, including its initial cloud rotation.
const transform=new THREE.Matrix4().makeRotationFromEuler(new THREE.Euler(.12,-.18,-.12));
const view=new THREE.PerspectiveCamera(43,16/9,.1,180);view.position.set(0,1,13);view.lookAt(0,0,0);view.updateMatrixWorld();
const sample=Object.entries(NODE_LAYOUT).filter(([id])=>!['charts','oracles','quiet'].includes(id)).map(([id,item])=>{
  const world=new THREE.Vector3(...item.position).applyMatrix4(transform),depth=-world.clone().applyMatrix4(view.matrixWorldInverse).z;
  return {id,world,depth,radius:item.radius*360/(Math.tan(THREE.MathUtils.degToRad(43/2))*depth),x:world.clone().project(view).x};
});
const span=Math.max(...sample.map(p=>p.depth))-Math.min(...sample.map(p=>p.depth));
const ratio=Math.max(...sample.map(p=>p.radius))/Math.min(...sample.map(p=>p.radius));
assert(span>7,'Entries must span the front and back of the cloud');
assert(ratio>3,'Perspective sizes must visibly distinguish foreground and background');
view.position.applyAxisAngle(new THREE.Vector3(0,1,0),.2);view.lookAt(0,0,0);view.updateMatrixWorld();
const shift=id=>{const p=sample.find(p=>p.id===id);return Math.abs(p.world.clone().project(view).x-p.x);};
assert(shift('liuyao')>shift('jyotish')*1.5,'Camera rotation must produce stronger foreground parallax');
const migrated=resolvePreferences({reduced:true,quality:'low',active_birth_id:'keep-me'});
assert.equal(migrated.reduced,false);assert.equal(migrated.quality,'high');assert.equal(migrated.active_birth_id,'keep-me');
assert.equal(resolvePreferences({effects_default:'full-1',reduced:true,quality:'low'}).quality,'low');
assert.equal(resolvePreferences({effects_default:'full-1',reduced:true}).reduced,true);
const sunParent=new THREE.Group(),sun=createBirthStar(sunParent);sun.preferences({reduced:false});sun.update(0,'home','');sun.update(1,'home','');
assert(sun.body.position.equals(new THREE.Vector3()),'Birthday star must stay at the center of all bound orbits');
assert(sun.body.material.uniforms.uTime.value>0,'Central corona must animate by default');
sun.preferences({reduced:true});const sunTime=sun.body.material.uniforms.uTime.value;sun.update(2,'page','birthdays');
assert.equal(sun.body.material.uniforms.uTime.value,sunTime);assert.equal(sun.body.material.uniforms.uOpacity.value,1);
for(const item of Object.values(NODE_LAYOUT))assert(new THREE.Vector3(...item.position).length()*.72-item.radius>sun.radius,'Feature orbits must surround the birthday star');
console.log(`PASS: 12 bindings, focus lock, reduced motion, quality, selected context; depth span ${span.toFixed(1)}, projected radius ratio ${ratio.toFixed(1)}, foreground parallax verified`);
console.log('PASS: full-effects defaults and migration, persistent explicit choices, animated central birthday star');
