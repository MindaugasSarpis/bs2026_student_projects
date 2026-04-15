import test from "node:test";
import assert from "node:assert/strict";

import { ANALYTICS_RUNTIME_CONFIG, getAnalyticsRuntimeConfig } from "../src/app/config/analytics-config.js";
import { __test__ } from "../src/app/static-site-app.js";

test("analytics runtime config exposes the live GA4 identifiers and versioned consent storage keys", () => {
  const config = getAnalyticsRuntimeConfig();

  assert.equal(config, ANALYTICS_RUNTIME_CONFIG);
  assert.equal(config.provider, "ga4_via_gtag");
  assert.deepEqual(config.ga4, {
    accountResource: "accounts/389778361",
    accountId: "389778361",
    propertyResource: "properties/531253273",
    propertyId: "531253273",
    webStreamResource: "properties/531253273/dataStreams/14356295354",
    webStreamId: "14356295354",
    measurementId: "G-VWEM25PMN0",
  });
  assert.deepEqual(config.consent, {
    storageKeyVersion: "v1",
    decisionStorageKey: "ccoutline.analytics.consent.decision.v1",
    updatedAtStorageKey: "ccoutline.analytics.consent.updated_at.v1",
  });
});

test("analytics runtime config is frozen and matches the static-site app default seam", () => {
  assert.equal(Object.isFrozen(ANALYTICS_RUNTIME_CONFIG), true);
  assert.equal(Object.isFrozen(ANALYTICS_RUNTIME_CONFIG.ga4), true);
  assert.equal(Object.isFrozen(ANALYTICS_RUNTIME_CONFIG.consent), true);
  assert.equal(__test__.analyticsConfig, ANALYTICS_RUNTIME_CONFIG);
});
