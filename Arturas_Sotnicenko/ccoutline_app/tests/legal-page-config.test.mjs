import test from "node:test";
import assert from "node:assert/strict";

import { normalizeAppPathname, resolveLegalPage } from "../src/app/legal/legal-page-config.js";

test("normalizeAppPathname keeps root stable and normalizes trailing slashes", () => {
  assert.equal(normalizeAppPathname("/"), "/");
  assert.equal(normalizeAppPathname("/privacy"), "/privacy/");
  assert.equal(normalizeAppPathname("/privacy/"), "/privacy/");
  assert.equal(normalizeAppPathname("manage-cookies"), "/manage-cookies/");
});

test("resolveLegalPage matches each standalone legal route", () => {
  assert.equal(resolveLegalPage("/privacy")?.key, "privacy");
  assert.equal(resolveLegalPage("/cookies/")?.key, "cookies");
  assert.equal(resolveLegalPage("/manage-cookies")?.key, "manage-cookies");
  assert.equal(resolveLegalPage("/country/LT/"), null);
});

