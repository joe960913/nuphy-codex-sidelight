import test from "node:test";
import assert from "node:assert/strict";
import { messages, translator, STATE_IDS, EFFECT_IDS } from "./i18n.js";

test("both languages cover every message and preserve interpolation fields", () => {
  for (const [key, values] of Object.entries(messages)) {
    assert.equal(values.length, 2, key);
    assert.ok(
      values.every((value) => typeof value === "string" && value.trim()),
      key,
    );
    assert.deepEqual(
      [...values[0].matchAll(/\{(\w+)\}/g)].map((match) => match[1]).sort(),
      [...values[1].matchAll(/\{(\w+)\}/g)].map((match) => match[1]).sort(),
      key,
    );
  }
  for (const state of STATE_IDS)
    assert.ok(messages[state] && messages[`desc_${state}`]);
  for (const effect of EFFECT_IDS) assert.ok(messages[`effect_${effect}`]);
});

test("dynamic status is formatted in the selected language", () => {
  assert.equal(
    translator("en")("live_detail", { state: "Working", count: 2 }),
    "Working · 2 connected session(s)",
  );
  assert.equal(
    translator("zh-CN")("last_check", { time: "12:00:00" }),
    "最近检测 12:00:00",
  );
});
