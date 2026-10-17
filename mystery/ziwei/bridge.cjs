"use strict";
// Local stdin/stdout JSON bridge. Never executes caller-supplied code or loads a URL.
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
try {
  const input = JSON.parse(fs.readFileSync(0, "utf8"));
  const sandbox = {};
  sandbox.self = sandbox;
  const bundle = fs.readFileSync(path.join(__dirname, "vendor", "iztro-2.6.2.min.js"), "utf8");
  vm.runInNewContext(bundle, sandbox, { timeout: 3000 });
  const chart = sandbox.iztro.astro.withOptions({
    type: "solar", dateStr: input.date, timeIndex: input.time_index,
    gender: input.gender, fixLeap: input.fix_leap, language: "zh-CN",
    config: input.config,
  });
  const annual = input.target_year === null ? null :
    chart.horoscope(`${input.target_year}-6-1`, 6).yearly;
  process.stdout.write(JSON.stringify({
    schema: "iztro-bridge-v1", natal: chart.toJSON(),
    decadals: chart.decadalList(), annual,
  }));
} catch (error) {
  process.stderr.write(String(error.message));
  process.exitCode = 1;
}
