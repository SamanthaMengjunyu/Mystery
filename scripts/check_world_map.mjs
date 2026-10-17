import assert from 'node:assert/strict';
import {geoVector,vectorGeo,groupPlaces,graticuleGeometry,globeFocusStep} from '../desktop/web/geo-models.js';
import {personColor,personPalette} from '../desktop/web/person-colors.js';
for(const [lat,lon] of [[0,0],[31.22,121.46],[40.71,-74.006],[-33.87,151.21],[80,179],[-50,-179]]){
  const p=vectorGeo(geoVector(lat,lon,2.5));assert(Math.abs(p.latitude-lat)<1e-8);assert(Math.abs(p.longitude-lon)<1e-8);
}
const people=[{id:'a',kind:'birth',latitude:31.22,longitude:121.46},{id:'b',kind:'birth',latitude:31.22,longitude:121.46},{id:'a',kind:'current',latitude:40.71,longitude:-74},{id:'c',latitude:null,longitude:null},{id:'d',latitude:95,longitude:1}];
const groups=groupPlaces(people);assert.equal(groups.length,2);assert.equal(groups[0].items.length,2);assert.equal(groups[1].items[0].kind,'current');
console.log('PASS: geographic sphere round-trips, dateline, friend clustering, distinct residence markers, invalid/unlocated places omitted.');
const grid=graticuleGeometry(),positions=grid.getAttribute('position');assert(positions.count>5000);for(let i=0;i<positions.count;i++){const length=Math.hypot(positions.getX(i),positions.getY(i),positions.getZ(i));assert(Math.abs(length-2.516)<1e-6);assert(length>2.5);}grid.dispose();
assert.equal(personColor({color:'#8EDBCB'}),'#8edbcb');assert.equal(personColor({id:'legacy'}),personColor({id:'legacy',name:'renamed'}));assert(personPalette.includes(personColor({color:'var(--bad)',id:'legacy'})));
console.log('PASS: globe graticule stays above land at all longitudes/latitudes; custom and legacy person colors stay valid and stable.');

const focusTarget=geoVector(0,180,8.5);let focusPosition=geoVector(0,0,8.8);for(let i=0;i<150;i++){focusPosition=globeFocusStep(focusPosition,focusTarget,.08);assert(focusPosition.length()>=8.49);}assert(focusPosition.distanceTo(focusTarget)<.01);assert(globeFocusStep(geoVector(30,120,6),focusTarget,1).distanceTo(focusTarget)<1e-8);
console.log('PASS: focus travels around the globe, including antipodes, while preserving safe camera distance.');
