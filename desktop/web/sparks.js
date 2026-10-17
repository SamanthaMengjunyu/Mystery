import * as THREE from 'three';

/** Decorative visual randomness, independent of every divination RNG. */
export function createSparks(parent,pixelRatio){
  const groups=[],MAX=36;
  let next=performance.now()/1000+1.5+Math.random()*2,total=0,quiet=false,low=false;
  const unit=()=>new THREE.Vector3(Math.random()-.5,Math.random()-.5,Math.random()-.5).normalize();
  for(let b=0;b<3;b++){
    const group=new THREE.Group();group.visible=false;parent.add(group);
    const positions=new Float32Array((MAX+3)*3),sizes=new Float32Array(MAX+3),alpha=new Float32Array(MAX+3),colors=new Float32Array((MAX+3)*3);
    const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.BufferAttribute(positions,3));geometry.setAttribute('aSize',new THREE.BufferAttribute(sizes,1));geometry.setAttribute('aAlpha',new THREE.BufferAttribute(alpha,1));geometry.setAttribute('color',new THREE.BufferAttribute(colors,3));
    for(let i=0;i<MAX+3;i++)new THREE.Color(i%3===0?'#d6e5ff':'#e6c89c').toArray(colors,i*3);
    const material=new THREE.ShaderMaterial({transparent:true,depthWrite:false,blending:THREE.AdditiveBlending,vertexColors:true,uniforms:{uPixel:{value:pixelRatio}},
      vertexShader:`attribute float aSize;attribute float aAlpha;varying vec3 vColor;varying float vAlpha;uniform float uPixel;void main(){vColor=color;vAlpha=aAlpha;vec4 p=modelViewMatrix*vec4(position,1.);gl_Position=projectionMatrix*p;gl_PointSize=clamp(aSize*380.*uPixel/max(.2,-p.z),1.,65.);}`,
      fragmentShader:`varying vec3 vColor;varying float vAlpha;void main(){float r=length(gl_PointCoord-.5)*2.;if(r>1.)discard;float soft=exp(-r*r*5.);gl_FragColor=vec4(vColor,vAlpha*soft);}`});
    group.add(new THREE.Points(geometry,material));
    const streaks=new Float32Array(MAX*6),streakGeo=new THREE.BufferGeometry();streakGeo.setAttribute('position',new THREE.BufferAttribute(streaks,3));
    const streakMat=new THREE.LineBasicMaterial({color:0xc6cce3,transparent:true,opacity:0,depthWrite:false,blending:THREE.AdditiveBlending});group.add(new THREE.LineSegments(streakGeo,streakMat));
    groups.push({group,geometry,material,positions,sizes,alpha,streaks,streakGeo,streakMat,directions:[],speeds:[],start:-100,count:MAX});
  }
  function spawn(now){
    const burst=groups.find(g=>!g.group.visible);if(!burst)return;
    burst.group.position.set((Math.random()-.5)*7,(Math.random()-.5)*2.5,1+Math.random()*1.4);
    burst.axis=unit();burst.start=now;burst.count=low?18:MAX;burst.directions=Array.from({length:MAX},unit);burst.speeds=Array.from({length:MAX},()=>.18+Math.random()*.65);burst.group.visible=true;total++;
  }
  return {
    preferences(p,ratio){quiet=!!p.reduced;low=p.quality==='low';for(const b of groups){b.material.uniforms.uPixel.value=ratio;if(quiet)b.group.visible=false;}next=performance.now()/1000+2+Math.random()*4;document.body.dataset.sparkReduced=String(quiet);if(quiet)document.body.dataset.sparkActive='0';},
    update(now,mode){
      if(quiet)return;
      if(now>=next){spawn(now);next=now+(mode==='home'?4.5:9)+Math.random()*(mode==='home'?6:9);}
      for(const b of groups){
        if(!b.group.visible)continue;
        const age=now-b.start,t=age-.65;
        if(t>1.75){b.group.visible=false;continue;}
        b.alpha.fill(0);b.sizes.fill(0);b.streaks.fill(0);
        const ambience=mode==='home'?1:.32;
        if(t<0){
          for(let side=0;side<2;side++){const sign=side===0?-1:1;b.axis.clone().multiplyScalar(sign*(-t)*1.2).toArray(b.positions,side*3);b.sizes[side]=.08;b.alpha[side]=ambience*.6;}
          b.streakMat.opacity=0;
        }else{
          b.positions.fill(0,0,9);b.sizes[0]=.65*Math.exp(-t*7);b.alpha[0]=Math.exp(-t*10)*ambience*.7;
          for(let i=0;i<b.count;i++){
            const fade=Math.max(0,1-t/(.85+(i%7)*.13));
            b.directions[i].clone().multiplyScalar(b.speeds[i]*t/(1+t*.7)).toArray(b.positions,(i+3)*3);
            b.sizes[i+3]=.035+(i%4)*.009;b.alpha[i+3]=fade*fade*.85*ambience;
            b.directions[i].clone().multiplyScalar(b.speeds[i]*Math.max(0,t-.065)/(1+t*.7)).toArray(b.streaks,i*6);
            b.directions[i].clone().multiplyScalar(b.speeds[i]*t/(1+t*.7)).toArray(b.streaks,i*6+3);
          }
          b.streakMat.opacity=Math.max(0,1-t/1.45)*.18*ambience;
        }
        for(const name of ['position','aSize','aAlpha'])b.geometry.attributes[name].needsUpdate=true;b.streakGeo.attributes.position.needsUpdate=true;
      }
      document.body.dataset.sparkBursts=String(total);document.body.dataset.sparkActive=String(groups.filter(g=>g.group.visible).length);
    },
    diagnostics(){return {total,active:groups.filter(g=>g.group.visible).length,reduced:quiet};}
  };
}
