import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {prepareCountries,countryAt,countryBorders,raisedCountry} from '../desktop/web/country-geometry.js';
const data=JSON.parse(await readFile(new URL('../desktop/web/assets/geography/countries-110m.json',import.meta.url),'utf8')),countries=prepareCountries(data);
assert.equal(countries.length,177);assert.equal(new Set(countries.map(c=>c.id)).size,177);
for(const [lat,lon,id] of [[31.22,121.46,'CHN'],[35.68,139.69,'JPN'],[48.86,2.35,'FRA'],[40.71,-74,'USA'],[61.22,-149.9,'USA'],[55.75,37.62,'RUS'],[-29.31,27.48,'LSO'],[-18.14,178.44,'FJI'],[-89,0,'ATA']])assert.equal(countryAt(countries,lat,lon)?.id,id,`${lat},${lon}`);
assert.equal(countryAt(countries,0,-140),null);
const synthetic=prepareCountries({features:[{properties:{id:'TEST',name:'Test'},geometry:{type:'Polygon',coordinates:[[[170,-10],[-170,-10],[-170,10],[170,10],[170,-10]],[[175,-5],[-175,-5],[-175,5],[175,5],[175,-5]]]}}]});
assert.equal(countryAt(synthetic,8,179)?.id,'TEST');assert.equal(countryAt(synthetic,8,-179)?.id,'TEST');assert.equal(countryAt(synthetic,0,179),null);assert.equal(countryAt(synthetic,0,0),null);
let vertices=0,minCenter=Infinity;
for(const c of countries){const shapes=raisedCountry(c);for(const g of Object.values(shapes)){for(const attribute of Object.values(g.attributes))for(const value of attribute.array)assert(Number.isFinite(value),`${c.id} nonfinite`);}const p=shapes.surface.getAttribute('position');vertices+=p.count;assert(p.count>0,c.id);for(let i=0;i<p.count;i+=3){const radius=Math.hypot((p.getX(i)+p.getX(i+1)+p.getX(i+2))/3,(p.getY(i)+p.getY(i+1)+p.getY(i+2))/3,(p.getZ(i)+p.getZ(i+1)+p.getZ(i+2))/3);minCenter=Math.min(minCenter,radius);assert(radius>2.5,`${c.id} triangle clips sphere: ${radius}`);}const weights=shapes.walls.getAttribute('countryLift').array;assert(weights.includes(0)&&weights.includes(1));for(const g of Object.values(shapes))g.dispose();}
const borders=countryBorders(countries);for(const n of borders.getAttribute('position').array)assert(Number.isFinite(n));borders.dispose();
console.log(`PASS: ${countries.length} country/region polygons, ocean and enclave picking, dateline/hole handling, ${vertices} surface vertices, finite walls/outlines, minimum triangle radius ${minCenter.toFixed(5)} above globe.`);
