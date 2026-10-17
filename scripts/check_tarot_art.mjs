import assert from 'node:assert/strict';
import {readFileSync,readdirSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {tarotImagePath} from '../desktop/web/tarot-art.js';
const base=new URL('../desktop/web/assets/tarot-rws/',import.meta.url);
const manifest=JSON.parse(readFileSync(new URL('manifest.json',base)));
const paths=[];
for(const suit of ['major','wands','cups','swords','pentacles'])for(let n=suit==='major'?0:1;n<=(suit==='major'?21:14);n++){
  const path=tarotImagePath({id:`${suit}_${String(n).padStart(2,'0')}`});
  assert(path);const name=path.split('/').at(-1),file=readFileSync(new URL(name,base)),entry=manifest.files.find(f=>f.file===name);
  assert.equal(file.readUInt16BE(0),0xffd8,'Card face must be a JPEG');
  assert.equal(createHash('sha256').update(file).digest('hex'),entry.sha256);
  paths.push(path);
}
assert.equal(new Set(paths).size,78);assert.equal(readdirSync(base).filter(n=>n.endsWith('.jpg')).length,78);
assert.equal(tarotImagePath({id:'major_00'}),'/assets/tarot-rws/m00.jpg');
assert.equal(tarotImagePath({id:'pentacles_14'}),'/assets/tarot-rws/p14.jpg');
for(const id of ['major_22','wands_00','cups_15','../../private','m00.jpg','major_0'])assert.equal(tarotImagePath({id}),null);
assert.equal(tarotImagePath({id:'major_00',img:'https://example.test/tracker'}),paths[0]);
console.log('PASS: all 78 immutable card IDs map to unique bundled RWS JPEGs, hashes match provenance, invalid paths rejected.');
