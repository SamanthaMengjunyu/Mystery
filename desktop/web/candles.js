import * as THREE from './vendor/three.module.js';

export function createCandleCenter(parent){
  const group=new THREE.Group();group.name='candle-center';parent.add(group);
  const wax=new THREE.MeshStandardMaterial({color:0xd7c7a5,roughness:.83}),metal=new THREE.MeshStandardMaterial({color:0x645039,metalness:.8,roughness:.4}),wick=new THREE.MeshStandardMaterial({color:0x252019,roughness:1});
  const flames=[],lights=[];
  for(const [x,z,height,radius] of [[0,-.18,1.45,.2],[-.43,.22,.95,.18],[.4,.25,.7,.16]]){
    const candle=new THREE.Group();candle.position.set(x,-.08,z);group.add(candle);
    const holder=new THREE.Mesh(new THREE.CylinderGeometry(radius+.1,radius+.13,.07,40),metal);holder.position.y=.035;holder.receiveShadow=true;candle.add(holder);
    const body=new THREE.Mesh(new THREE.CylinderGeometry(radius*.94,radius,height,48),wax);body.position.y=.07+height/2;body.castShadow=true;body.receiveShadow=true;candle.add(body);
    const pool=new THREE.Mesh(new THREE.CylinderGeometry(radius*.62,radius*.62,.012,32),new THREE.MeshStandardMaterial({color:0x8e7954,roughness:.33}));pool.position.y=height+.077;candle.add(pool);
    for(let d=0;d<4;d++){const angle=d*1.7+.4,drip=new THREE.Mesh(new THREE.SphereGeometry(1,12,12),wax),length=.07+(d%3)*.045;drip.scale.set(.025,length,.025);drip.position.set(Math.sin(angle)*radius*.96,height+.07-length,Math.cos(angle)*radius*.96);candle.add(drip);}
    const stem=new THREE.Mesh(new THREE.CylinderGeometry(.012,.014,.065,8),wick);stem.position.y=height+.1;candle.add(stem);
    const uniforms={uTime:{value:0},uPhase:{value:x*7+z*11}};
    const flame=new THREE.Mesh(new THREE.SphereGeometry(1,20,28),new THREE.ShaderMaterial({uniforms,transparent:true,depthWrite:false,side:THREE.DoubleSide,
      vertexShader:`uniform float uTime,uPhase;varying float vHeight;varying vec3 vNormal,vView;
        void main(){float h=position.y*.5+.5;vHeight=h;vec3 p=position;p.xz*=.095*mix(1.,.04,pow(h,1.4));p.y=(position.y+1.)*.22;p.x+=sin(uTime*2.4+uPhase)*h*h*.026;p.z+=sin(uTime*1.7+uPhase)*h*h*.016;vec4 mv=modelViewMatrix*vec4(p,1.);vNormal=normalMatrix*normal;vView=-mv.xyz;gl_Position=projectionMatrix*mv;}`,
      fragmentShader:`varying float vHeight;varying vec3 vNormal,vView;
        void main(){float core=pow(abs(dot(normalize(vNormal),normalize(vView))),1.5);vec3 color=mix(vec3(1.,.34,.055),vec3(1.,.94,.68),core*.9);color=mix(vec3(.32,.42,.95),color,smoothstep(0.,.13,vHeight));float alpha=(.48+core*.52)*(1.-smoothstep(.88,1.,vHeight));gl_FragColor=vec4(color,alpha);}`
    }));flame.position.y=height+.12;flame.renderOrder=3;candle.add(flame);flames.push(flame);
    const light=new THREE.PointLight(0xffbd70,7,12,2);light.position.set(x,height+.24,z);group.add(light);lights.push(light);
  }
  const glow=new THREE.Mesh(new THREE.PlaneGeometry(5.5,5.5),new THREE.ShaderMaterial({transparent:true,depthWrite:false,blending:THREE.AdditiveBlending,
    vertexShader:'varying vec2 vUv;void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}',
    fragmentShader:'varying vec2 vUv;void main(){float r=length(vUv-.5)*2.;float a=exp(-r*r*5.)*.13*(1.-smoothstep(.65,1.,r));gl_FragColor=vec4(.95,.47,.16,a);}'
  }));glow.rotation.x=-Math.PI/2;glow.position.y=-.125;group.add(glow);
  let previous=null,time=0;
  return {group,flames,lights,update(now,reduced=false){const dt=previous===null?0:Math.max(0,Math.min(.1,now-previous));previous=now;if(!reduced)time+=dt;for(let i=0;i<flames.length;i++){flames[i].material.uniforms.uTime.value=time;lights[i].intensity=7+(reduced?0:.22*Math.sin(time*2.4+i)+.1*Math.sin(time*5.7+i*2));}},reset(){group.position.z=0;}};
}
