"use strict";
// Development-only fixture generator: independently load upstream CommonJS.
// Usage: node scripts/reference_ziwei.cjs PATH_TO_IZTRO_PACKAGE OUTPUT_JSON
const path = require("node:path");
const fs = require("node:fs");
process.env.TZ = "Asia/Shanghai";
const upstream = require(path.resolve(process.argv[2]));
const version = require(path.resolve(process.argv[2], "package.json")).version;
if (version !== "2.6.2") throw new Error("expected iztro 2.6.2");
const cases = [
  { label: "official-example", date: "2000-8-16", time_index: 2, gender: "女", fix_leap: true, day_divide: "forward" },
  { label: "late-zi-forward", date: "2000-1-1", time_index: 12, gender: "男", fix_leap: true, day_divide: "forward" },
  { label: "late-zi-current", date: "2000-1-1", time_index: 12, gender: "男", fix_leap: true, day_divide: "current" },
  { label: "leap-month-adjusted", date: "2023-4-6", time_index: 6, gender: "女", fix_leap: true, day_divide: "forward" },
  { label: "leap-month-unadjusted", date: "2023-4-6", time_index: 6, gender: "女", fix_leap: false, day_divide: "forward" },
];
for (const item of cases) {
  upstream.astro.resetConfig();
  const chart = upstream.astro.withOptions({ type: "solar", dateStr: item.date,
    timeIndex: item.time_index, gender: item.gender, fixLeap: item.fix_leap, language: "zh-CN",
    config: { algorithm: "default", yearDivide: "normal", horoscopeDivide: "normal",
      ageDivide: "normal", dayDivide: item.day_divide } });
  item.expected = { natal: chart.toJSON(), decadals: chart.decadalList(),
    annual: chart.horoscope("2026-6-1", 6).yearly };
}
fs.writeFileSync(process.argv[3], JSON.stringify({ source: "iztro 2.6.2 CommonJS reference",
  url: "https://iztro.com/posts/astrolabe", annual_year: 2026, cases }, null, 2) + "\n");
