import * as THREE from './vendor/three.module.js';

/** Hollow white globes and their bound orbits share one genuinely three-dimensional model. */
export function createStarTrails(parent,nodes){
  const STEPS=160,states=[],indices=[];
  const sphere=new THREE.SphereGeometry(1,24,16);
  const sphereLow=new THREE.SphereGeometry(1,12,8);
  const greatCircle=new THREE.TorusGeometry(1,.009,5,128),greatCircleLow=new THREE.TorusGeometry(1,.009,4,64);
  const contour=new THREE.PlaneGeometry(2.16,2.16);
  const orbitUniforms={uStates:{value:nodes.map(()=>new THREE.Vector4())},uCamera:{value:new THREE.Vector3()}};
  const field={position:[],aAxisX:[],aAxisY:[],aOrbit:[],aNode:[],aAlong:[],aSide:[],color:[]};
  const contourVertex=`varying vec2 vDisc;varying float vDepth;
    void main(){vec4 center=modelViewMatrix*vec4(0.,0.,0.,1.);vDepth=-center.z;vDisc=position.xy;
      vec2 scale=vec2(length(modelMatrix[0].xyz),length(modelMatrix[1].xyz));center.xy+=position.xy*scale;gl_Position=projectionMatrix*center;}`;
  const contourFragment=`uniform float uOpacity;uniform float uEmphasis;uniform float uTransmission;varying vec2 vDisc;varying float vDepth;
    void main(){float radius=length(vDisc),aa=fwidth(radius),width=max(.006,aa*(.52+uEmphasis*.18));
      float line=1.-smoothstep(width-aa*.45,width+aa*.55,abs(radius-1.));
      float depthFade=.55+.45*exp(-max(0.,vDepth-8.)*.06);
      float alpha=line*uOpacity*uTransmission*depthFade*(.9+uEmphasis*.1);
      if(alpha<.002)discard;gl_FragColor=vec4(vec3(.96,.975,1.),alpha);}`;
  const circleVertex=`varying float vFront;
    void main(){vec4 center=modelViewMatrix*vec4(0.,0.,0.,1.),mv=modelViewMatrix*vec4(position,1.);vFront=mv.z-center.z;gl_Position=projectionMatrix*mv;}`;
  const circleFragment=`uniform float uOpacity;uniform float uEmphasis;uniform float uTransmission;varying float vFront;
    void main(){float front=mix(.12,.46+uEmphasis*.12,smoothstep(-.045,.045,vFront));
      gl_FragColor=vec4(vec3(.96,.975,1.),front*uOpacity*uTransmission);}`;

  nodes.forEach((node,i)=>{
    const radius=node.p.length(),axisX=node.p.clone().normalize();
    const normal=new THREE.Vector3(.1+(i%3)*.12,1,.3+(i%4)*.16).normalize();
    const axisY=new THREE.Vector3().crossVectors(normal,axisX).normalize();
    const ratio=.72+(i%3)*.09,color=new THREE.Color('#edf1fa');
    const uniforms={uOpacity:{value:0},uEmphasis:{value:0},uTransmission:{value:1}};
    // The invisible sphere supplies solid hit-testing; only white contours are rendered.
    const body=new THREE.Mesh(sphere,new THREE.MeshBasicMaterial({visible:false}));parent.add(body);
    const visual=new THREE.Group();parent.add(visual);
    const silhouette=new THREE.Mesh(contour,new THREE.ShaderMaterial({uniforms,vertexShader:contourVertex,fragmentShader:contourFragment,transparent:true,depthWrite:false}));
    silhouette.renderOrder=2;visual.add(silhouette);
    const circleMaterial=new THREE.ShaderMaterial({uniforms,vertexShader:circleVertex,fragmentShader:circleFragment,transparent:true,depthWrite:false});
    const circles=Array.from({length:3},(_,index)=>{const line=new THREE.Mesh(greatCircle,circleMaterial);if(index===1)line.rotation.y=Math.PI/2;if(index===2)line.rotation.x=Math.PI/2;line.renderOrder=1;visual.add(line);return line;});
    const grouped=['charts','oracles','quiet'].includes(node.id),size=node.radius;
    const state={node,axisX,axisY,radius,ratio,body,visual,circles,uniforms,size,angle:0,fade:0,emphasis:0,pulse:0,zoom:1,speed:(i%2?1:-1)*(.003+(i%4)*.0004)};
    states.push(state);node.body=body;node.grouped=grouped;
    node.btn.style.setProperty('--planet-color','#edf1fa');
    for(let j=0;j<=STEPS;j++)for(const side of [-1,1]){
      field.position.push(0,0,0);field.aAxisX.push(...axisX.toArray());field.aAxisY.push(...axisY.toArray());
      field.aOrbit.push(radius,ratio);field.aNode.push(i);field.aAlong.push(j/STEPS);field.aSide.push(side);field.color.push(...color.toArray());
    }
    const base=i*(STEPS+1)*2;
    for(let j=0;j<STEPS;j++){const k=base+j*2;indices.push(k,k+1,k+2,k+1,k+3,k+2);}
  });
  const geometry=new THREE.BufferGeometry();
  for(const [name,data] of Object.entries(field))geometry.setAttribute(name,new THREE.Float32BufferAttribute(data,{position:3,aAxisX:3,aAxisY:3,aOrbit:2,aNode:1,aAlong:1,aSide:1,color:3}[name]));
  geometry.setIndex(indices);
  const material=new THREE.ShaderMaterial({uniforms:orbitUniforms,transparent:true,depthWrite:false,side:THREE.DoubleSide,blending:THREE.AdditiveBlending,vertexColors:true,
    vertexShader:`attribute vec3 aAxisX;attribute vec3 aAxisY;attribute vec2 aOrbit;attribute float aNode;attribute float aAlong;attribute float aSide;
      uniform vec4 uStates[${nodes.length}];uniform vec3 uCamera;
      varying vec3 vColor;varying float vAlong;varying float vAcross;varying vec4 vState;varying float vTransmission;
      float transmission(vec3 p){
        vec3 ro=vec3(uCamera.x,uCamera.y-.28*uCamera.x,uCamera.z)/vec3(6.2,2.7,2.9);
        vec3 end=vec3(p.x,p.y-.28*p.x,p.z)/vec3(6.2,2.7,2.9),ray=end-ro;
        float a=dot(ray,ray),b=dot(ro,ray),disc=b*b-a*(dot(ro,ro)-1.);
        if(disc<=0.||a<.0001)return 1.;float root=sqrt(disc);
        float entry=max(0.,(-b-root)/a),exit=min(1.,(-b+root)/a);
        return .22+.78*exp(-max(0.,exit-entry)*sqrt(a)*1.8);
      }
      void main(){vec4 state=uStates[int(aNode)];float angle=state.x-6.2831853*(1.-aAlong);
        vec3 p=aOrbit.x*(cos(angle)*aAxisX+sin(angle)*aOrbit.y*aAxisY);
        vec3 tangent=normalize(-sin(angle)*aAxisX+cos(angle)*aOrbit.y*aAxisY);
        vec3 facing=normalize(cross(tangent,normalize(uCamera-p)));
        vColor=color;vAlong=aAlong;vAcross=aSide;vState=state;vTransmission=transmission(p);
        gl_Position=projectionMatrix*modelViewMatrix*vec4(p+facing*aSide*(.024+state.z*.012+state.w*.015),1.);}`,
    fragmentShader:`varying vec3 vColor;varying float vAlong;varying float vAcross;varying vec4 vState;varying float vTransmission;
      void main(){float tail=exp(-(1.-vAlong)*(15.-vState.z*5.));
        float core=exp(-vAcross*vAcross*8.);
        float alpha=core*vState.y*vTransmission*(.025+vState.z*.1+tail*(.32+vState.z*.3)+vState.w*.14);
        gl_FragColor=vec4(vColor,alpha);}`});
  const ribbons=new THREE.Mesh(geometry,material);ribbons.frustumCulled=false;parent.add(ribbons);
  let reduced=false,hovered='',selected='',previous=null;
  document.body.dataset.planetNodes=String(nodes.length);
  document.body.dataset.boundOrbits=String(nodes.length);
  document.body.dataset.starTrails=String(nodes.length);
  document.body.dataset.nodeAppearance='white-hollow';
  // Optical depth through the same ellipsoid used by the cloud. Far globes recede into it.
  function transmission(camera,p){
    const ro=new THREE.Vector3(camera.x/6.2,(camera.y-.28*camera.x)/2.7,camera.z/2.9);
    const ray=new THREE.Vector3(p.x/6.2,(p.y-.28*p.x)/2.7,p.z/2.9).sub(ro);
    const a=ray.lengthSq(),b=ro.dot(ray),disc=b*b-a*(ro.lengthSq()-1);
    if(disc<=0||a<.0001)return 1;
    const root=Math.sqrt(disc),entry=Math.max(0,(-b-root)/a),exit=Math.min(1,(-b+root)/a);
    return .27+.73*Math.exp(-Math.max(0,exit-entry)*Math.sqrt(a)*1.4);
  }
  const setHover=id=>{
    hovered=id;document.body.dataset.hoveredNode=id;document.body.dataset.highlightedOrbit=id;
    for(const s of states)s.node.btn.classList.toggle('orbit-hover',s.node.id===id);
  };
  return {
    get interacting(){return !!(hovered||selected);},
    hover:setHover,
    activate(id){const s=states.find(s=>s.node.id===id);if(s)s.pulse=1;document.body.dataset.activatedPlanet=id;},
    select(id){selected=id||'';setHover('');document.body.dataset.selectedPlanet=selected;},
    update(now,mode,camera,{progress,near,region}){
      const dt=previous===null?0:Math.max(0,Math.min(.1,now-previous));previous=now;orbitUniforms.uCamera.value.copy(camera);
      if(hovered&&!nodes.find(n=>n.id===hovered)?.available)setHover('');
      let visible=0;
      for(let i=0;i<states.length;i++){
        const s=states[i],node=s.node;
        node.available=mode==='home'&&(near?!node.grouped&&(region==='charts'?['bazi','ziwei','astro','jyotish'].includes(node.id):region==='oracles'?['liuyao','meihua','tarot','lenormand'].includes(node.id):true):node.grouped);
        const target=node.available?(near?1:.6+progress*.4):(mode!=='home'&&node.id===selected ? (mode==='entering'?1:.6) : 0);
        const active=hovered===node.id||selected===node.id;
        s.fade=reduced?target:THREE.MathUtils.lerp(s.fade,target,1-Math.exp(-dt*7));
        s.emphasis=reduced?Number(active):THREE.MathUtils.lerp(s.emphasis,Number(active),1-Math.exp(-dt*10));
        // A hovered or selected entry stays still so it remains easy to click.
        if(!reduced&&!active&&mode==='home')s.angle+=dt*s.speed;
        s.pulse=reduced?0:Math.max(0,s.pulse-dt*1.6);
        node.p.copy(s.axisX).multiplyScalar(Math.cos(s.angle)*s.radius).addScaledVector(s.axisY,Math.sin(s.angle)*s.radius*s.ratio);
        s.body.position.copy(node.p);s.visual.position.copy(node.p);
        const zoomTarget=node.id===selected&&['entering','module'].includes(mode)?1.45:1;
        s.zoom=reduced?zoomTarget:THREE.MathUtils.lerp(s.zoom,zoomTarget,1-Math.exp(-dt*9));
        const scale=s.size*s.zoom*(1+s.emphasis*.06+s.pulse*.1);s.body.scale.setScalar(scale);s.visual.scale.setScalar(scale);
        s.body.visible=s.visual.visible=s.fade>.006;s.visual.rotation.set(.3+(i%3)*.2,s.angle*2,.2+(i%4)*.3);
        s.uniforms.uOpacity.value=s.fade;s.uniforms.uEmphasis.value=s.emphasis+s.pulse*.6;
        node.depthOpacity=transmission(camera,node.p);s.uniforms.uTransmission.value=node.depthOpacity;
        orbitUniforms.uStates.value[i].set(s.angle,s.fade*(mode==='home'?1:.38),s.emphasis,s.pulse);
        if(node.available)visible++;
      }
      document.body.dataset.visiblePlanets=String(visible);
    },
    preferences(p){reduced=!!p.reduced;for(const s of states){s.body.geometry=p.quality==='low'?sphereLow:sphere;for(const circle of s.circles)circle.geometry=p.quality==='low'?greatCircleLow:greatCircle;}document.body.dataset.starTrailsMotion=reduced?'still':'flowing';},
    diagnostics(){return {count:states.length,planets:states.length,motion:!reduced,hovered,selected};}
  };
}
