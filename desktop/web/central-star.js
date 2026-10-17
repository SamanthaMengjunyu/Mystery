import * as THREE from './vendor/three.module.js';

export function createBirthStar(parent){
  const radius=.62,uniforms={uTime:{value:0},uOpacity:{value:1},uHover:{value:0},uEye:{value:new THREE.Vector3()}};
  // Integrate density along the camera ray instead of drawing an opaque surface.
  const body=new THREE.Mesh(new THREE.BoxGeometry(2.8,2.8,2.8),new THREE.ShaderMaterial({uniforms,transparent:true,depthWrite:false,side:THREE.BackSide,
    vertexShader:`varying vec3 vPoint;void main(){vPoint=position;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}`,
    fragmentShader:`uniform vec3 uEye;uniform float uTime,uOpacity,uHover;varying vec3 vPoint;
      float hash(vec3 p){return fract(sin(dot(p,vec3(127.1,311.7,74.7)))*43758.5453);}
      float noise(vec3 p){vec3 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);return mix(mix(mix(hash(i),hash(i+vec3(1,0,0)),f.x),mix(hash(i+vec3(0,1,0)),hash(i+vec3(1,1,0)),f.x),f.y),mix(mix(hash(i+vec3(0,0,1)),hash(i+vec3(1,0,1)),f.x),mix(hash(i+vec3(0,1,1)),hash(i+vec3(1,1,1)),f.x),f.y),f.z);}
      void main(){vec3 rd=normalize(vPoint-uEye);float b=dot(uEye,rd),c=dot(uEye,uEye)-1.65,h=b*b-c;if(h<0.)discard;
        float root=sqrt(h),start=max(0.,-b-root),lengthRay=2.*root,stepSize=lengthRay/32.;vec4 sum=vec4(0.);
        for(int i=0;i<32;i++){vec3 p=uEye+rd*(start+(float(i)+.5)*stepSize);float r=length(p);
          float n=noise(p*5.+vec3(0,uTime*.055,uTime*.025)),core=exp(-r*r*7.5);
          float density=(core*3.5+exp(-r*r*2.8)*(.13+n*.22))*(1.-smoothstep(.75,1.28,r));
          float a=1.-exp(-density*stepSize*2.8);vec3 color=mix(vec3(.55,.63,.86),vec3(1.,.83,.50),smoothstep(.02,.8,core));
          color=mix(color,vec3(1.,.94,.78),core*.65);sum.rgb+=(1.-sum.a)*color*a;sum.a+=(1.-sum.a)*a;}
        gl_FragColor=vec4(sum.rgb/max(sum.a,.001)*(1.+uHover*.05),sum.a*uOpacity);}`
  }));
  body.renderOrder=2;body.onBeforeRender=(_r,_s,camera)=>{uniforms.uEye.value.setFromMatrixPosition(camera.matrixWorld);body.worldToLocal(uniforms.uEye.value);};parent.add(body);
  let reduced=false,hover=false,clock=0,previous=null,emphasis=0;
  document.body.dataset.centralStar='birthday-book';document.body.dataset.centralStarAppearance='volume-glow';
  return {body,radius,hover(value){hover=!!value;},update(now,mode,selected){
    const dt=previous===null?0:Math.max(0,Math.min(.1,now-previous));previous=now;if(!reduced)clock+=dt;
    const active=hover||selected==='birthdays',opacity=mode==='home'||active?1:.17;
    emphasis=reduced?Number(active):THREE.MathUtils.lerp(emphasis,Number(active),1-Math.exp(-dt*7));
    uniforms.uTime.value=clock;uniforms.uHover.value=emphasis;uniforms.uOpacity.value=reduced?opacity:THREE.MathUtils.lerp(uniforms.uOpacity.value,opacity,1-Math.exp(-dt*5));
    body.scale.setScalar(1+emphasis*.06+(!reduced?Math.sin(clock*.65)*.012:0));
  },preferences(p){reduced=!!p.reduced;document.body.dataset.centralStarMotion=reduced?'still':'flowing';}};
}
