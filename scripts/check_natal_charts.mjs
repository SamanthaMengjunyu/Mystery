// Geometry and saved-result invariants for the four presentation adapters.
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {renderNatalChart,placePlanetLabels} from '../desktop/web/natal-charts.js';
const fixtures=JSON.parse(execFileSync(process.argv[2]||'python',['-c',`
import json,tempfile
from pathlib import Path
from desktop.backend import Backend
with tempfile.TemporaryDirectory() as folder:
 b=Backend(Path(folder))
 print(json.dumps({m:b.calculate({'module':m,'datetime':'2000-08-16T04:00','longitude':116.41,'latitude':39.90})['result'] for m in ['bazi','astro','ziwei','jyotish']},ensure_ascii=False))
`],{cwd:fileURLToPath(new URL('../',import.meta.url)),encoding:'utf8',env:{...process.env,PYTHONIOENCODING:'utf-8'},maxBuffer:4_000_000}));
for(const module of ['bazi','astro','ziwei','jyotish']){
  const result=fixtures[module],before=JSON.stringify(result);
  const html=renderNatalChart({module,result},{section:(title)=>`<details><summary>${title}</summary></details>`});
  assert(html.includes(`natal-${module}`));
  assert(!html.includes('NaN')&&!html.includes('undefined'));
  assert.equal(JSON.stringify(result),before,'Rendering must never change the stored facts');
  if(module==='astro'){
    assert.equal((html.match(/class="zodiac-glyph"/g)||[]).length,12);
    assert.equal((html.match(/class="natal-aspect"/g)||[]).length,result.aspects.length);
    assert.equal((html.match(/class="natal-svg-control natal-planet"/g)||[]).length,Object.keys(result.points).length);
  }
  if(module==='ziwei')assert.equal((html.match(/class="natal-palace /g)||[]).length,12);
  if(module==='jyotish')assert(html.includes('data-natal-varga="d9"'));
}
for(const asc of [0,125.265,359.9]){
  // Tight conjunctions across 0 degrees must keep their true anchor and avoid overlapping labels.
  const source=[359,359.1,359.2,.1,.2,.3,1,1.1,1.2,2,2.1,2.2,3].map((lon,i)=>['p'+i,{lon}]);
  const before=JSON.stringify(source),placed=placePlanetLabels(source,asc);
  assert.equal(placed.length,source.length);
  for(let i=1;i<placed.length;i++)assert(placed[i].labelAngle-placed[i-1].labelAngle>=9.999);
  assert.equal(JSON.stringify(source),before);
  assert(placed.every(p=>Math.abs(p.angle-((p.p.lon-asc+360)%360))<1e-9));
}
const unsafe=structuredClone(fixtures.ziwei);unsafe.palaces[0].majorStars[0]={name:'<img src=x onerror=alert(1)>',mutagen:''};
const html=renderNatalChart({module:'ziwei',result:unsafe},{section:()=>''});
assert(!html.includes('<img src=x'));
assert(html.includes('&lt;img'));
console.log('Four natal renderers, unchanged facts, 12 signs/palaces, real aspect edges, conjunction labels and escaped data: passed.');
