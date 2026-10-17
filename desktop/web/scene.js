import * as THREE from 'three';
import { OrbitControls } from './vendor/OrbitControls.js';
import { createSparks } from './sparks.js';
import { createStarTrails } from './star-trails.js';
import { NODE_LAYOUT } from './node-layout.js';
import { createBirthStar } from './central-star.js';

export function createUniverse(onSelect, onExplore) {
  const canvas = document.querySelector('#universe');
  const renderer = new THREE.WebGLRenderer({canvas, antialias:true, alpha:false, powerPreference:'high-performance'});
  renderer.setClearColor(0x080b13);
  renderer.setPixelRatio(Math.min(devicePixelRatio, 1.6));
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(43, innerWidth/innerHeight, .1, 180);
  camera.position.set(0, 1.6, 21);
  const controls = new OrbitControls(camera, canvas);
  controls.enableDamping = true;
  controls.dampingFactor = .055;
  controls.minDistance = 5.5; controls.maxDistance = 30;
  controls.enablePan = false;
  controls.rotateSpeed = .45; controls.zoomSpeed = .6;
  controls.target.set(0,0,0);
  const cloud = new THREE.Group();
  cloud.rotation.set(.12,-.18,-.12);
  scene.add(cloud);
  let seed=48713;
  const rand=()=>{seed=(Math.imul(seed,1664525)+1013904223)|0;return (seed>>>0)/4294967296;};
  const normal=()=>Math.sqrt(-2*Math.log(Math.max(rand(),.00001)))*Math.cos(2*Math.PI*rand());
  const n=19000, positions=new Float32Array(n*3), colors=new Float32Array(n*3), sizes=new Float32Array(n);
  const cold=new THREE.Color('#718ab7'), warm=new THREE.Color('#b4a2ba'), pale=new THREE.Color('#c5cae2');
  for(let i=0;i<n;i++){
    // Overlapping density volumes form ONE continuous, asymmetric cloud.
    const t=rand()*Math.PI*2, r=Math.pow(rand(),.95)*5.7;
    const x=Math.cos(t)*r, y=Math.sin(t)*r*.50;
    const twist=.4*Math.sin(x*.65)+.22*x;
    const z=normal()*(1.5-.12*Math.abs(x));
    positions.set([x+normal()*.22,y+twist+normal()*.18,z],i*3);
    const c=cold.clone().lerp(warm,Math.max(0,Math.min(1,(x+3)/7))).lerp(pale,Math.exp(-r*r/5)*.5);
    c.multiplyScalar(.55+rand()*.55); colors.set(c.toArray(),i*3);
    sizes[i]=(rand()<.005 ? .09 : .35+rand()*.85)*(1-r/10);
  }
  const geo=new THREE.BufferGeometry();
  geo.setAttribute('position',new THREE.BufferAttribute(positions,3));
  geo.setAttribute('color',new THREE.BufferAttribute(colors,3));
  geo.setAttribute('aSize',new THREE.BufferAttribute(sizes,1));
  const mat=new THREE.ShaderMaterial({transparent:true,depthWrite:false,blending:THREE.AdditiveBlending,vertexColors:true,
    uniforms:{uPixel:{value:renderer.getPixelRatio()},uTime:{value:0}},
    vertexShader:`attribute float aSize; varying vec3 vColor; varying float vDepth; uniform float uPixel; uniform float uTime;
      void main(){vColor=color;vec3 p=position;p.y+=sin(p.x*.7+uTime*.07)*.055;vec4 mv=modelViewMatrix*vec4(p,1.);vDepth=-mv.z;
      gl_Position=projectionMatrix*mv;gl_PointSize=clamp(aSize*340.*uPixel/-mv.z,1.,110.);}`,
    fragmentShader:`varying vec3 vColor;varying float vDepth;void main(){vec2 q=gl_PointCoord-.5;float r=length(q)*2.;if(r>1.)discard;
      float density=exp(-r*r*5.5)*.018;gl_FragColor=vec4(vColor,density);}`});
  cloud.add(new THREE.Points(geo,mat));
  // Ray-marched 3D gas provides absorption and self-occlusion, with particles
  // only adding fine dust. Camera movement traverses a volume, not an image.
  const placeholder=new THREE.DataTexture(new Uint8Array([92,100,122,255]),1,1);placeholder.needsUpdate=true;
  const gasMaterial=new THREE.ShaderMaterial({transparent:true,depthWrite:false,side:THREE.BackSide,
    uniforms:{uCamera:{value:new THREE.Vector3()},uTime:{value:0},uSteps:{value:40},uArt:{value:placeholder},uArtReady:{value:0}},
    vertexShader:`varying vec3 vPosition;void main(){vPosition=position;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}`,
    fragmentShader:`precision highp float;varying vec3 vPosition;uniform vec3 uCamera;uniform float uTime;uniform int uSteps;uniform sampler2D uArt;uniform float uArtReady;
      float hash(vec3 p){p=fract(p*.3183099+vec3(.1,.2,.3));p*=17.;return fract(p.x*p.y*p.z*(p.x+p.y+p.z));}
      float noise(vec3 p){vec3 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);
        return mix(mix(mix(hash(i),hash(i+vec3(1,0,0)),f.x),mix(hash(i+vec3(0,1,0)),hash(i+vec3(1,1,0)),f.x),f.y),
        mix(mix(hash(i+vec3(0,0,1)),hash(i+vec3(1,0,1)),f.x),mix(hash(i+vec3(0,1,1)),hash(i+vec3(1,1,1)),f.x),f.y),f.z);}
      float fbm(vec3 p){return .57*noise(p)+.28*noise(p*2.07+3.)+.15*noise(p*4.13+7.);}
      vec3 artwork(vec3 p){return texture2D(uArt,fract(p.xy*.135+p.z*.047+vec2(.42,.47))).rgb;}
      float density(vec3 p){p.y-=.28*p.x+.35*sin(p.x*.8);vec3 q=p/vec3(6.2,2.7,2.9);
        float bound=max(0.,1.-dot(q,q));float n=fbm(p*.8+vec3(0.,uTime*.008,0.));
        float filaments=dot(artwork(p),vec3(.3,.5,.2));float textureDensity=mix(1.,.4+filaments*2.3,uArtReady);
        return bound*bound*smoothstep(.24,.77,n)*1.5*textureDensity;}
      void main(){vec3 ro=uCamera,rd=normalize(vPosition-ro),bounds=vec3(6.6,4.7,3.4);
        vec3 inv=1./rd,t0=(-bounds-ro)*inv,t1=(bounds-ro)*inv;
        vec3 mn=min(t0,t1),mx=max(t0,t1);float near=max(max(mn.x,mn.y),mn.z),far=min(min(mx.x,mx.y),mx.z);
        near=max(near,0.);if(far<=near)discard;float stepSize=(far-near)/float(uSteps);vec4 acc=vec4(0.);
        for(int i=0;i<40;i++){if(i>=uSteps)break;vec3 p=ro+rd*(near+(float(i)+.5)*stepSize);float d=density(p);
          float light=clamp(.65+(density(p)-density(p+vec3(-.45,.7,.6)))*2.,.25,1.25);
          float heart=exp(-dot(p/vec3(2.1,1.1,1.4),p/vec3(2.1,1.1,1.4)));
          vec3 cold=vec3(.24,.32,.46),warm=vec3(.46,.34,.38);vec3 color=mix(cold,warm,smoothstep(-3.,5.,p.x))*(.65+light*.6);
          color=mix(color,mix(color*.58,artwork(p)*1.3,.62),uArtReady*.65);
          color+=vec3(.2,.22,.32)*heart;float alpha=1.-exp(-d*stepSize*.75);
          acc.rgb+=(1.-acc.a)*color*alpha;acc.a+=(1.-acc.a)*alpha;if(acc.a>.97)break;}
        if(acc.a<.002)discard;gl_FragColor=vec4(acc.rgb/max(acc.a,.001),acc.a);}`});
  const gas=new THREE.Mesh(new THREE.BoxGeometry(13.2,9.4,6.8),gasMaterial);gas.renderOrder=-1;cloud.add(gas);
  new THREE.TextureLoader().load('/assets/nebula-dust-v1.png',texture=>{
    texture.wrapS=texture.wrapT=THREE.RepeatWrapping;texture.minFilter=THREE.LinearMipmapLinearFilter;
    gasMaterial.uniforms.uArt.value=texture;gasMaterial.uniforms.uArtReady.value=1;document.body.dataset.nebulaArt='loaded';
  },undefined,()=>{document.body.dataset.nebulaArt='procedural-fallback';});
  const sparks=createSparks(cloud,renderer.getPixelRatio());
  const starsG=new THREE.BufferGeometry(), starsP=[],starsC=[];
  for(let i=0;i<720;i++){starsP.push((rand()-.5)*95,(rand()-.5)*65,(rand()-.5)*80);const b=.15+rand()*.32;starsC.push(b*.8,b*.85,b);}
  starsG.setAttribute('position',new THREE.Float32BufferAttribute(starsP,3));starsG.setAttribute('color',new THREE.Float32BufferAttribute(starsC,3));
  const stars=new THREE.Points(starsG,new THREE.PointsMaterial({size:.026,vertexColors:true,transparent:true,opacity:.65,depthWrite:false}));scene.add(stars);
  // Each entry is a small planet on a bound orbit inside the shared nebula.
  const points=Object.fromEntries(Object.entries(NODE_LAYOUT).map(([id,item])=>[id,item.position]));
  const names={charts:['命盘','NATAL PATTERNS'],oracles:['问事','THE UNFOLDING'],quiet:['一页回响','A QUIET ANSWER'],bazi:['四柱八字','FOUR PILLARS'],ziwei:['紫微斗数','ZI WEI'],astro:['西方占星','ASTROLOGY'],jyotish:['印度占星','JYOTISH'],liuyao:['六爻','SIX LINES'],meihua:['梅花易数','PLUM BLOSSOM'],tarot:['塔罗','TAROT'],lenormand:['雷诺曼','LENORMAND'],answers:['答案之书','BOOK OF ANSWERS']};
  const labels=document.querySelector('#scene-labels');
  const nodes=Object.entries(points).map(([id,p])=>{
    const btn=document.createElement('button');btn.className='scene-node';btn.dataset.node=id;
    const hit=document.createElement('span');hit.className='planet-hit';hit.setAttribute('aria-hidden','true');
    const text=document.createElement('span'),b=document.createElement('b'),s=document.createElement('small');text.className='node-caption';b.textContent=names[id][0];s.textContent=names[id][1];text.append(b,s);btn.append(hit,text);labels.append(btn);
    btn.onclick=()=>{
      starTrails.activate(id);
      if(id==='charts'||id==='oracles'){region=id;explore(id);}
      else enterNode(id==='quiet'?'answers':id);
    };
    btn.onpointerenter=btn.onfocus=()=>starTrails.hover(id);
    btn.onpointerleave=btn.onblur=()=>starTrails.hover('');
    return {id,p:new THREE.Vector3(...p),radius:NODE_LAYOUT[id].radius,btn,caption:text};
  });
  const starTrails=createStarTrails(cloud,nodes);
  const birthStar=createBirthStar(cloud);
  const centerNode={id:'birthdays',central:true,p:new THREE.Vector3(),radius:birthStar.radius,body:birthStar.body,btn:document.querySelector('#central-birthday-star'),depthOpacity:1};
  centerNode.caption=centerNode.btn.querySelector('.node-caption');
  const entryNodes=[centerNode,...nodes];
  centerNode.btn.onclick=()=>enterNode('birthdays');
  centerNode.btn.onpointerenter=centerNode.btn.onfocus=()=>{birthStar.hover(true);starTrails.hover('');};
  centerNode.btn.onpointerleave=centerNode.btn.onblur=()=>birthStar.hover(false);
  // Hit-test the actual 3D bodies as well as their projected, keyboard-accessible labels.
  const raycaster=new THREE.Raycaster(),pointer=new THREE.Vector2();let pointerStart=null,pointerMoved=false;
  function planetAt(event){
    if(mode!=='home')return null;
    const r=canvas.getBoundingClientRect();pointer.set((event.clientX-r.left)/r.width*2-1,-(event.clientY-r.top)/r.height*2+1);
    raycaster.setFromCamera(pointer,camera);
    const hit=raycaster.intersectObjects(entryNodes.filter(n=>n.available&&n.body.visible).map(n=>n.body),false)[0];
    return hit?entryNodes.find(n=>n.body===hit.object):null;
  }
  canvas.addEventListener('pointermove',e=>{if(pointerStart&&Math.hypot(e.clientX-pointerStart[0],e.clientY-pointerStart[1])>=5)pointerMoved=true;const node=planetAt(e);canvas.style.cursor=node?'pointer':'';starTrails.hover(node?.central?'':node?.id||'');birthStar.hover(!!node?.central);});
  canvas.addEventListener('pointerleave',()=>{starTrails.hover('');birthStar.hover(false);canvas.style.cursor='';});
  canvas.addEventListener('pointerdown',e=>{pointerStart=e.button===0?[e.clientX,e.clientY]:null;pointerMoved=false;});
  canvas.addEventListener('pointerup',e=>{if(e.button===0&&pointerStart&&!pointerMoved&&Math.hypot(e.clientX-pointerStart[0],e.clientY-pointerStart[1])<5)planetAt(e)?.btn.click();pointerStart=null;});
  canvas.addEventListener('pointercancel',()=>{pointerStart=null;});
  let mode='home',region='',reduced=false,paused=false,low=false,selectedModule='',ambientKind='',ambientSnapshot=null;
  let tween=null,wheelTarget=null,lastProgress=-1;
  let entryTimer=null,entryTicket=0;
  function cancelEntry(){if(entryTimer!==null){clearTimeout(entryTimer);entryTimer=null;entryTicket++;mode='home';selectedModule='';starTrails.select('');document.body.dataset.nodeZoom='cancelled';}}
  function enterNode(id){
    cancelEntry();
    if(reduced){onSelect(id);return;}
    const p=entryNodes.find(n=>n.id===id).p.clone();cloud.localToWorld(p);
    const direction=camera.position.clone().sub(p).normalize();
    mode='entering';selectedModule=id;starTrails.select(id);starTrails.activate(id);
    document.body.dataset.nodeZoom='running';document.body.dataset.zoomTarget=id;
    fly(p.clone().addScaledVector(direction,6).toArray(),p.toArray(),560);
    const ticket=++entryTicket;
    entryTimer=setTimeout(()=>{if(ticket!==entryTicket)return;entryTimer=null;document.body.dataset.nodeZoom='complete';onSelect(id);},580);
  }
  function fly(position,target,duration=1200){wheelTarget=null;tween={from:camera.position.clone(),to:new THREE.Vector3(...position),a:controls.target.clone(),b:new THREE.Vector3(...target),start:performance.now(),duration:reduced?1:duration};}
  function explore(which='all'){
    cancelEntry();
    region=which;
    if(which==='charts'||which==='oracles'){
      const p=nodes.find(n=>n.id===which).p.clone();cloud.localToWorld(p);
      fly([p.x*.6,p.y*.5+1,13],[p.x*.5,p.y*.4,0]);
    }
    else fly([0,1,13],[0,0,0]);
  }
  controls.addEventListener('start',()=>{cancelEntry();tween=null;wheelTarget=null;});
  // Capture before OrbitControls: scrolling DOWN should unfold the home scene.
  document.addEventListener('wheel',event=>{
    if(mode!=='home'||ambientKind==='globe'||event.target.closest('#modal-root,#workspace,.focus-chrome'))return;
    event.preventDefault();event.stopImmediatePropagation();tween=null;
    const pixels=event.deltaY*(event.deltaMode===1?16:event.deltaMode===2?innerHeight:1);
    wheelTarget=THREE.MathUtils.clamp((wheelTarget??camera.position.distanceTo(controls.target))-THREE.MathUtils.clamp(pixels,-180,180)*.018,8.5,30);
    if(reduced){camera.position.sub(controls.target).setLength(wheelTarget).add(controls.target);wheelTarget=null;}
  },{passive:false,capture:true});
  const v=new THREE.Vector3();
  let last=0;
  function frame(now){
    requestAnimationFrame(frame);
    if(document.hidden||paused)return;
    if(low&&now-last<32)return;const dt=Math.min(.1,(now-last)/1000||.016);last=now;
    if(tween){let t=Math.min(1,(now-tween.start)/tween.duration);t=1-Math.pow(1-t,3);camera.position.lerpVectors(tween.from,tween.to,t);controls.target.lerpVectors(tween.a,tween.b,t);if(t>=1)tween=null;}
    controls.update();
    if(wheelTarget!==null){const distance=camera.position.distanceTo(controls.target),next=THREE.MathUtils.lerp(distance,wheelTarget,1-Math.exp(-dt*10));camera.position.sub(controls.target).setLength(next).add(controls.target);if(Math.abs(next-wheelTarget)<.01)wheelTarget=null;}
    if(!reduced){if(mode==='home'&&!starTrails.interacting)cloud.rotation.y+=dt*(ambientKind==='nebula'?.028:.007);mat.uniforms.uTime.value=now/1000;}
    gasMaterial.uniforms.uCamera.value.copy(camera.position);cloud.worldToLocal(gasMaterial.uniforms.uCamera.value);
    const dist=camera.position.distanceTo(controls.target),near=dist<15.5,progress=THREE.MathUtils.clamp((21.06-dist)/8.56,0,1);
    starTrails.update(now/1000,mode,gasMaterial.uniforms.uCamera.value,{progress,near,region});
    centerNode.available=mode==='home';birthStar.update(now/1000,mode,selectedModule);
    if(!reduced)gasMaterial.uniforms.uTime.value=now/1000;
    sparks.update(now/1000,mode);renderer.render(scene,camera);
    if(mode==='home'&&Math.abs(progress-lastProgress)>.002){lastProgress=progress;onExplore({progress});document.body.dataset.exploreProgress=progress.toFixed(3);}
    const occupied=[];
    if(mode==='home')for(const selector of [...(progress<=.7?['#scroll-invitation']:[]),...(progress<=.26?['.home-heading']:[])]){
      const r=document.querySelector(selector).getBoundingClientRect();occupied.push({left:r.left-10,right:r.right+10,top:r.top-8,bottom:r.bottom+8});
    }
    const projected=entryNodes.map(node=>{
      v.copy(node.p);cloud.localToWorld(v);
      const viewDepth=-v.clone().applyMatrix4(camera.matrixWorldInverse).z;
      const radius=node.body.scale.x*innerHeight/(2*Math.tan(THREE.MathUtils.degToRad(camera.fov/2))*Math.max(.1,viewDepth));
      v.project(camera);
      node.btn.dataset.depth=viewDepth.toFixed(2);node.btn.dataset.radius=radius.toFixed(2);
      return {node,x:(v.x*.5+.5)*innerWidth,y:(-v.y*.5+.5)*innerHeight,z:v.z,viewDepth,radius,inView:v.z<1&&Math.abs(v.x)<.95&&Math.abs(v.y)<.9};
    });
    // Give the focused entry first choice, then place the other captions around their bodies.
    projected.sort((a,b)=>Number(b.node.btn.classList.contains('orbit-hover'))-Number(a.node.btn.classList.contains('orbit-hover')));
    const intersects=(a,b)=>a.left<b.right&&a.right>b.left&&a.top<b.bottom&&a.bottom>b.top;
    for(const {node,x,y,viewDepth,radius,inView} of projected){
      let visible=node.available&&(node.central||progress>.12);
      visible=visible&&inView;
      if(visible){
        const captionScale=node.central?1:THREE.MathUtils.clamp(13/viewDepth,.82,1.06);
        node.btn.style.setProperty('--caption-scale',captionScale);
        node.btn.style.setProperty('--hit-size',`${Math.max(36,radius*2+12)}px`);
        const half=Math.max(44,node.caption.offsetWidth*captionScale/2+6),height=34;
        const below=22+radius+12,above=-radius-24,side=radius+72;
        const candidates=[[0,below],[0,above],[side,5],[-side,5],[0,below+30],[0,above-30]];
        let choice=null,best=Infinity;
        for(const [dx,top] of candidates){
          const box={left:x+dx-half,right:x+dx+half,top:y-22+top,bottom:y-22+top+height};
          const overlaps=occupied.filter(o=>intersects(box,o)).length+projected.filter(o=>o.node!==node&&o.node.available&&o.inView&&intersects(box,{left:o.x-o.radius-5,right:o.x+o.radius+5,top:o.y-o.radius-5,bottom:o.y+o.radius+5})).length;
          const score=overlaps+(box.left<20||box.right>innerWidth-20||box.top<110||box.bottom>innerHeight-85?10:0);
          if(score<best){best=score;choice={dx,top,box};}if(score===0)break;
        }
        node.btn.style.setProperty('--caption-left',`${choice.dx}px`);node.btn.style.setProperty('--caption-top',`${choice.top}px`);occupied.push(choice.box);
      }
      const active=node.btn.classList.contains('orbit-hover'),depthAlpha=active?1:THREE.MathUtils.clamp(.3+node.depthOpacity*.65,.4,.95);
      node.btn.style.opacity=visible?String((node.central||near?1:Math.min(.85,(progress-.12)*3))*depthAlpha):'0';node.btn.style.pointerEvents=visible?'auto':'none';node.btn.tabIndex=visible?0:-1;node.btn.setAttribute('aria-hidden',String(!visible));
      node.btn.style.left=`${x}px`;node.btn.style.top=`${y}px`;
      node.btn.style.filter=`blur(${active||node.central?0:THREE.MathUtils.clamp((viewDepth-14)*.045,0,.5)}px)`;
    }
    document.querySelector('#scene-coordinate').textContent=`NEBULA / ${dist.toFixed(1).padStart(4,'0')}`;
  }
  requestAnimationFrame(frame);
  function resize(){renderer.setSize(innerWidth,innerHeight,false);camera.aspect=innerWidth/innerHeight;camera.updateProjectionMatrix();}
  addEventListener('resize',resize);resize();
  return {
    explore,
    cancelEntry,
    reset(){cancelEntry();mode='home';selectedModule='';region='';lastProgress=-1;document.body.dataset.nodeZoom='idle';starTrails.select('');birthStar.hover(false);fly([0,1.6,21],[0,0,0]);},
    setMode(next,module){cancelEntry();mode=next;selectedModule=module||'';if(next==='home'){this.reset();}else{region='';starTrails.select(module);const p=entryNodes.find(n=>n.id===module)?.p.clone()||new THREE.Vector3();cloud.localToWorld(p);if(next!=='module'&&module!=='birthdays')fly([p.x+2,p.y+1,p.z+12],p.toArray(),850);else if(controls.target.distanceTo(p)>.15||camera.position.distanceTo(p)>7)fly([p.x+1.2,p.y+.6,p.z+6.2],p.toArray(),650);}},
    preferences(p){reduced=!!p.reduced;controls.autoRotate=ambientKind==='nebula'&&!reduced;low=p.quality==='low';renderer.setPixelRatio(low?1:Math.min(devicePixelRatio,1.6));geo.setDrawRange(0,low?9000:n);document.body.dataset.sceneQuality=low?'low':'high';document.body.dataset.dustParticles=String(low?9000:n);gasMaterial.uniforms.uSteps.value=low?24:40;mat.uniforms.uPixel.value=renderer.getPixelRatio();sparks.preferences(p,renderer.getPixelRatio());starTrails.preferences(p,renderer.getPixelRatio());birthStar.preferences(p);resize();},
    focus(kind){
      if(!kind){controls.autoRotate=false;ambientKind='';if(ambientSnapshot){({mode,region,selectedModule,paused}=ambientSnapshot);camera.position.copy(ambientSnapshot.position);controls.target.copy(ambientSnapshot.target);ambientSnapshot=null;tween=null;wheelTarget=null;controls.update();}return;}
      if(!ambientSnapshot)ambientSnapshot={mode,region,selectedModule,paused,position:camera.position.clone(),target:controls.target.clone()};
      cancelEntry();const previous=ambientKind;ambientKind=kind;paused=kind==='globe';controls.autoRotate=kind==='nebula'&&!reduced;controls.autoRotateSpeed=.22;
      if(kind==='nebula'){mode='home';region='';selectedModule='';if(previous!==kind)fly([0,1.2,13],[0,0,0],1100);}
    },
    pause(value){paused=value;},
    diagnostics(){return {camera:camera.position.toArray(),target:controls.target.toArray(),particles:n,webgl:renderer.capabilities.isWebGL2,mode,sparks:sparks.diagnostics(),starTrails:starTrails.diagnostics()};}
  };
}
