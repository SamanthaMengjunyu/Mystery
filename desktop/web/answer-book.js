import * as THREE from './vendor/three.module.js';

export function createAnswerBook(parent,makeTexture){
  const root=new THREE.Group();root.name='answer-book';root.position.y=-.1;parent.add(root);
  const width=2.6,depth=3.65,leather=new THREE.MeshStandardMaterial({color:0x1c2b3d,roughness:.78}),gold=new THREE.MeshStandardMaterial({color:0xa58a54,metalness:.7,roughness:.5}),paper=new THREE.MeshStandardMaterial({color:0xd6c9a8,roughness:.98});
  function box(w,h,d,material,x,y,z=0,group=root){const m=new THREE.Mesh(new THREE.BoxGeometry(w,h,d),material);m.position.set(x,y,z);m.castShadow=true;m.receiveShadow=true;group.add(m);return m;}
  box(width+.12,.065,depth+.12,leather,width/2,.015);
  box(width-.1,.25,depth-.15,paper,width/2,.17);
  for(let i=0;i<10;i++)box(width-.11,.005,depth-.13,new THREE.MeshStandardMaterial({color:i%2?0xb9ae91:0xe0d3b3,roughness:1}),width/2,.06+i*.023);
  const spine=new THREE.Mesh(new THREE.CylinderGeometry(.18,.18,depth+.04,32),leather);spine.rotation.x=Math.PI/2;spine.position.set(.02,.17,0);root.add(spine);
  for(const z of [-1.3,-1.1,1.1,1.3])box(.13,.02,.035,gold,.01,.32,z);
  const flap=new THREE.Group();flap.position.y=.36;root.add(flap);box(width+.12,.065,depth+.12,leather,width/2,0,0,flap);
  const coverArt=makeTexture((c,w,h)=>{c.fillStyle='#17273b';c.fillRect(0,0,w,h);c.strokeStyle='#a48b5b';c.lineWidth=3;c.strokeRect(44,44,w-88,h-88);c.strokeRect(57,57,w-114,h-114);c.textAlign='center';c.fillStyle='#d1bb8a';c.font='56px "Microsoft YaHei"';c.fillText('答案之书',w/2,h*.46);c.font='17px Georgia';c.fillText('THE BOOK OF ANSWERS',w/2,h*.52);c.font='48px Georgia';c.fillText('✦',w/2,h*.32);c.font='18px "Microsoft YaHei"';c.fillText('带着问题，停在此刻',w/2,h*.72);},768,1076);
  const coverFace=new THREE.Mesh(new THREE.PlaneGeometry(width-.04,depth-.03),new THREE.MeshStandardMaterial({map:coverArt,roughness:.82}));coverFace.rotation.x=-Math.PI/2;coverFace.position.set(width/2,.034,0);flap.add(coverFace);
  function page(side,map){const g=new THREE.PlaneGeometry(width-.15,depth-.22,32,24);g.rotateX(-Math.PI/2);const p=g.attributes.position;for(let i=0;i<p.count;i++){const u=(p.getX(i)+(width-.15)/2)/(width-.15);p.setX(i,side*(.07+u*(width-.15)));p.setY(i,.3+.105*Math.exp(-u*7)+.018*Math.sin(u*Math.PI));}if(side<0){const uv=g.attributes.uv;for(let i=0;i<uv.count;i++)uv.setX(i,1-uv.getX(i));}g.computeVertexNormals();const mesh=new THREE.Mesh(g,new THREE.MeshStandardMaterial({map,color:0xffffff,roughness:.98,side:THREE.DoubleSide}));mesh.receiveShadow=true;root.add(mesh);return mesh;}
  const leftMap=makeTexture((c,w,h)=>{c.fillStyle='#e5d9b9';c.fillRect(0,0,w,h);c.textAlign='center';c.fillStyle='#a3936f';c.font='100px Georgia';c.fillText('✦',w/2,h*.36);c.font='28px "Microsoft YaHei"';c.fillText('把问题留在心里',w/2,h*.51);c.fillText('在这一页里停留',w/2,h*.56);c.font='16px Georgia';c.fillText('A MOMENT FOR YOURSELF',w/2,h*.76);},768,1076);
  const left=page(-1,leftMap),right=page(1,null);left.visible=right.visible=false;
  const leftStack=box(width-.1,.24,depth-.15,paper,-width/2,.17);leftStack.visible=false;
  function setOpen(t){const u=THREE.MathUtils.clamp(t,0,1);root.position.x=-width/2*(1-u);flap.rotation.z=u*Math.PI;flap.position.y=THREE.MathUtils.lerp(.36,.015,u);left.visible=right.visible=leftStack.visible=u>.55;left.scale.x=leftStack.scale.x=Math.max(.001,(u-.55)/.45);leftStack.position.x=-width/2*leftStack.scale.x;root.userData.open=u;}
  function setAnswer(pageNumber,answer){const map=makeTexture((c,w,h)=>{c.fillStyle='#eadfc4';c.fillRect(0,0,w,h);c.textAlign='center';c.fillStyle='#9e8d66';c.font='23px Georgia';c.fillText(`PAGE ${String(pageNumber).padStart(3,'0')}`,w/2,h*.2);c.fillStyle='#453f32';c.font='58px "Microsoft YaHei"';let lines=[''];for(const ch of answer){if(c.measureText(lines.at(-1)+ch).width>w*.74)lines.push('');lines[lines.length-1]+=ch;}const lineHeight=88,start=h*.48-(lines.length-1)*lineHeight/2;lines.forEach((line,i)=>c.fillText(line,w/2,start+i*lineHeight));c.fillStyle='#a3936f';c.font='22px Georgia';c.fillText('✦',w/2,h*.78);},768,1076);right.material.map=map;right.material.needsUpdate=true;}
  setOpen(0);return {root,setOpen,setAnswer};
}
