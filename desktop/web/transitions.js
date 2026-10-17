/** Cursor-origin faceted ripple. Cancelling a route never leaves a stale swap. */
export function createTransitions(canvas) {
  const ctx=canvas.getContext('2d');
  if(!ctx)return {run:swap=>swap()};
  let origin=null,animation=0,pending=0,cells=[],width=0,height=0,sequence=0;
  document.addEventListener('pointerdown',e=>{origin={x:e.clientX,y:e.clientY};},true);
  document.addEventListener('keydown',()=>{origin=null;},true);
  function resize(){
    width=innerWidth;height=innerHeight;
    const ratio=Math.min(devicePixelRatio,1.5);canvas.width=Math.round(width*ratio);canvas.height=Math.round(height*ratio);
    ctx.setTransform(ratio,0,0,ratio,0,0);cells=[];
    const radius=36,dx=Math.sqrt(3)*radius,dy=1.5*radius;
    for(let row=-1;row<height/dy+2;row++)for(let col=-1;col<width/dx+2;col++){
      const x=col*dx+(row%2)*dx/2,y=row*dy;
      cells.push({x,y,r:radius,shade:.35+Math.random()*.65,facet:Math.random()>.6});
    }
  }
  addEventListener('resize',resize);resize();
  function clear(){ctx.clearRect(0,0,width,height);canvas.classList.remove('active');document.body.classList.remove('route-leaving');document.body.dataset.transitionState='idle';}
  function polygon(cell){
    ctx.beginPath();for(let i=0;i<6;i++){const a=(i*60-30)*Math.PI/180,x=cell.x+Math.cos(a)*cell.r,y=cell.y+Math.sin(a)*cell.r;if(i===0)ctx.moveTo(x,y);else ctx.lineTo(x,y);}ctx.closePath();
  }
  return {
    run(swap,{reduced=false,returning=false}={}){
      cancelAnimationFrame(animation);clearTimeout(pending);clear();const ticket=++sequence;
      if(reduced||!ctx){swap();return;}
      const focus=document.activeElement?.getBoundingClientRect();
      const start=origin||{x:focus?.width?focus.left+focus.width/2:width/2,y:focus?.height?focus.top+focus.height/2:height/2};
      const reach=Math.max(...[[0,0],[width,0],[0,height],[width,height]].map(([x,y])=>Math.hypot(x-start.x,y-start.y)));
      canvas.classList.add('active');document.body.classList.add('route-leaving');document.body.dataset.transitionState='running';
      document.body.dataset.transitionOrigin=`${Math.round(start.x)},${Math.round(start.y)}`;
      pending=setTimeout(()=>{if(ticket!==sequence)return;swap();document.body.classList.remove('route-leaving');},110);
      const begin=performance.now(),duration=880;
      function draw(now){
        if(ticket!==sequence)return;
        const progress=Math.min(1,(now-begin)/duration),wave=progress*1.32;
        ctx.clearRect(0,0,width,height);
        for(const cell of cells){
          const distance=Math.hypot(cell.x-start.x,cell.y-start.y)/reach;
          const phase=(wave-distance)/.34;
          if(phase<=0||phase>=1)continue;
          const envelope=Math.sin(phase*Math.PI)**1.4,opacity=envelope*cell.shade;
          polygon(cell);ctx.fillStyle=`rgba(17,25,44,${opacity*.58})`;ctx.fill();
          ctx.strokeStyle=`rgba(${returning?'185,170,218':'148,180,231'},${opacity*.23})`;ctx.lineWidth=.6;ctx.stroke();
          if(cell.facet){ctx.beginPath();ctx.moveTo(cell.x,cell.y);ctx.lineTo(cell.x+cell.r*.866,cell.y-cell.r*.5);ctx.lineTo(cell.x+cell.r*.866,cell.y+cell.r*.5);ctx.closePath();ctx.fillStyle=`rgba(172,187,225,${opacity*.11})`;ctx.fill();}
        }
        if(progress<1)animation=requestAnimationFrame(draw);else clear();
      }
      animation=requestAnimationFrame(draw);
    }
  };
}
