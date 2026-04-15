import test from "node:test";
import assert from "node:assert/strict";
import { JSDOM } from "jsdom";

import { ANALYTICS_RUNTIME_CONFIG } from "../src/app/config/analytics-config.js";
import { readStoredConsentState, writeStoredConsentDecision } from "../src/app/consent/consent-storage.js";
import { consentAccepted, consentDeclined, consentStateHydrated } from "../src/app/state/consent-slice.js";
import { selectConsentDecision, selectIsConsentHydrated } from "../src/app/state/selectors.js";
import { createAppStore } from "../src/app/state/store.js";

function withDom(testFn) {
  return async () => {
    const dom = new JSDOM("<!doctype html><div id='root'></div>", {
      pretendToBeVisual: true,
      url: "https://ccoutline.test/",
    });
    const previousWindow = globalThis.window;

    globalThis.window = dom.window;

    try {
      await testFn();
    } finally {
      globalThis.window = previousWindow;
      dom.window.close();
    }
  };
}

test("consent slice starts unhydrated and records hydrated accept or decline decisions", () => {
  const store = createAppStore();

  assert.equal(selectIsConsentHydrated(store.getState()), false);
  assert.equal(selectConsentDecision(store.getState()), null);

  store.dispatch(consentStateHydrated({ decision: "accepted", updatedAt: "2026-04-12T18:10:00.000Z" }));
  assert.equal(selectIsConsentHydrated(store.getState()), true);
  assert.equal(selectConsentDecision(store.getState()), "accepted");

  store.dispatch(consentDeclined({ updatedAt: "2026-04-12T18:11:00.000Z" }));
  assert.equal(selectConsentDecision(store.getState()), "declined");

  store.dispatch(consentAccepted({ updatedAt: "2026-04-12T18:12:00.000Z" }));
  assert.equal(selectConsentDecision(store.getState()), "accepted");
});

test(
  "consent storage reads and writes versioned browser-local decisions",
  withDom(async () => {
    assert.deepEqual(readStoredConsentState(ANALYTICS_RUNTIME_CONFIG), {
      decision: null,
      updatedAt: null,
    });

    const storedDecision = writeStoredConsentDecision(
      ANALYTICS_RUNTIME_CONFIG,
      "accepted",
      "2026-04-12T18:15:00.000Z",
    );

    assert.deepEqual(storedDecision, {
      decision: "accepted",
      updatedAt: "2026-04-12T18:15:00.000Z",
    });
    assert.deepEqual(readStoredConsentState(ANALYTICS_RUNTIME_CONFIG), storedDecision);
  }),
);
