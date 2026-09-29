'use strict';
const rooms = JSON.parse(document.getElementById('room-data').textContent);
const canvas = document.getElementById('room-canvas');
const ctx = canvas.getContext('2d');
const picker = document.getElementById('room-picker');
const reference = document.getElementById('reference');
let yaw = -.65, pitch = .5, zoom = 48, drag = null;
function boxEdges(b) {
  const [xl,xh,yl,yh,zl,zh] = b, xy = [[xl,yl],[xh,yl],[xh,yh],[xl,yh]], result = [];
  xy.forEach((p,i) => {const q = xy[(i+1)%4]; result.push([[...p,zl],[...p,zh]],[[...p,zl],[...q,zl]],[[...p,zh],[...q,zh]]);});
  return result;
}
function draw() {
  const room = rooms[Number(picker.value)];
  const w = canvas.clientWidth, h = canvas.clientHeight, dpr = devicePixelRatio || 1;
  canvas.width=w*dpr;canvas.height=h*dpr;ctx.scale(dpr,dpr);
  const scale=zoom*Math.min(w/700,h/500,1.2);
  function project(p) {
    const x=p[0], y=p[1], z=p[2]-1.5;
    const u=Math.cos(yaw)*x-Math.sin(yaw)*y, v=Math.sin(yaw)*x+Math.cos(yaw)*y;
    return [w/2+scale*u,h/2-scale*(Math.cos(pitch)*z-Math.sin(pitch)*v)];
  }
  function line(a,b,color,dashed=false,width=2) {
    const p=project(a),q=project(b);ctx.strokeStyle=color;ctx.lineWidth=width;ctx.setLineDash(dashed?[5,5]:[]);
    ctx.beginPath();ctx.moveTo(...p);ctx.lineTo(...q);ctx.stroke();
  }
  for(let i=-5;i<=5;i++){line([i,-5,0],[i,5,0],'#293a46',false,1);line([-5,i,0],[5,i,0],'#293a46',false,1);}
  if(reference.checked)boxEdges(room.reconstruction.truth_bounds_m).forEach(e=>line(e[0],e[1],'#80baf0',true));
  room.reconstruction.prediction.edges.forEach(e=>line(e.start,e.end,e.status==='supported'?'#62edc1':'#ffbd66',e.status!=='supported',2.5));
  room.camera_positions.forEach(m=>{
    const p=m.slice(0,3).map(row=>row[3]), q=p.map((v,j)=>v+m[j][2]*.4);
    line(p,q,'#f8e5b3',false,1.5);const uv=project(p);ctx.fillStyle='#f8e5b3';ctx.beginPath();ctx.arc(...uv,3,0,Math.PI*2);ctx.fill();
  });
  const dims=room.reconstruction.prediction.dimensions_m.map(v=>v.toFixed(2)).join(' × ');
  document.getElementById('room-stats').textContent=`${room.room}: estimated ${dims} m · dimension MAE ${room.reconstruction.metrics.dimension_mae_m.toFixed(3)} m · 8 calibrated views`;
  document.getElementById('room-download').href=`../media/roomgraph-perception/${room.room}/room.obj`;
}
canvas.addEventListener('pointerdown',e=>{drag=[e.clientX,e.clientY];canvas.setPointerCapture(e.pointerId);});
canvas.addEventListener('pointermove',e=>{if(!drag)return;yaw+=(e.clientX-drag[0])*.008;pitch=Math.max(-1.4,Math.min(1.4,pitch+(e.clientY-drag[1])*.008));drag=[e.clientX,e.clientY];draw();});
canvas.addEventListener('pointerup',()=>drag=null);canvas.addEventListener('pointercancel',()=>drag=null);
canvas.addEventListener('wheel',e=>{e.preventDefault();zoom=Math.max(20,Math.min(100,zoom*Math.exp(-e.deltaY*.001)));draw();},{passive:false});
canvas.addEventListener('keydown',e=>{let handled=true;if(e.key==='ArrowLeft')yaw-=.1;else if(e.key==='ArrowRight')yaw+=.1;else if(e.key==='ArrowUp')pitch=Math.min(1.4,pitch+.1);else if(e.key==='ArrowDown')pitch=Math.max(-1.4,pitch-.1);else if(e.key==='+'||e.key==='=')zoom=Math.min(100,zoom*1.1);else if(e.key==='-')zoom=Math.max(20,zoom/1.1);else handled=false;if(handled){e.preventDefault();draw();}});
picker.addEventListener('change',draw);reference.addEventListener('change',draw);
document.getElementById('reset').addEventListener('click',()=>{yaw=-.65;pitch=.5;zoom=48;draw();});
window.addEventListener('resize',draw);draw();
