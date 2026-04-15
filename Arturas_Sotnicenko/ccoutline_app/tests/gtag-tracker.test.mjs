import test from "node:test";
import assert from "node:assert/strict";
import { JSDOM } from "jsdom";

import { ANALYTICS_RUNTIME_CONFIG } from "../src/app/config/analytics-config.js";
import { createGtagTracker } from "../src/app/analytics/gtag-tracker.js";

function toQueuedCalls(dataLayer) {
  return Array.from(dataLayer || []).map((entry) => Array.from(entry || []));
}

function withDom(testFn) {
  return async () => {
    const dom = new JSDOM("<!doctype html><html><head></head><body></body></html>", {
      pretendToBeVisual: true,
      url: "https://ccoutline.test/",
    });
    const previousWindow = globalThis.window;
    const previousDocument = globalThis.document;

    globalThis.window = dom.window;
    globalThis.document = dom.window.document;

    try {
      await testFn(dom);
    } finally {
      globalThis.window = previousWindow;
      globalThis.document = previousDocument;
      dom.window.close();
    }
  };
}

test(
  "gtag tracker queues consent safely, injects the GA script only after acceptance, and emits serializable events",
  withDom(async (dom) => {
    const tracker = createGtagTracker({
      analyticsConfig: ANALYTICS_RUNTIME_CONFIG,
      documentRef: dom.window.document,
      windowRef: dom.window,
    });

    assert.equal(dom.window.document.querySelector('script[src*="googletagmanager.com/gtag/js"]'), null);

    tracker.syncConsentDecision("declined");
    assert.equal(tracker.trackEvent("country_selected", { country_code: "LT" }), false);
    assert.equal(dom.window.document.querySelector('script[src*="googletagmanager.com/gtag/js"]'), null);

    tracker.syncConsentDecision("accepted");
    assert.equal(Array.isArray(dom.window.dataLayer), true);
    assert.equal(dom.window.document.querySelector('script[src*="googletagmanager.com/gtag/js"]'), null);
    const queuedCallsBeforeEnable = toQueuedCalls(dom.window.dataLayer);
    assert.deepEqual(queuedCallsBeforeEnable[0], [
      "consent",
      "default",
      {
        analytics_storage: "denied",
      },
    ]);
    assert.deepEqual(queuedCallsBeforeEnable[1], [
      "consent",
      "update",
      {
        analytics_storage: "denied",
      },
    ]);
    assert.deepEqual(queuedCallsBeforeEnable[2], [
      "consent",
      "update",
      {
        analytics_storage: "granted",
      },
    ]);
    assert.equal(tracker.enable(), true);

    const injectedScript = dom.window.document.querySelector('script[src*="googletagmanager.com/gtag/js?id=G-VWEM25PMN0"]');
    assert.ok(injectedScript);
    assert.equal(tracker.trackEvent("page_view", { page_path: "/manage-cookies/", ignored: { nested: true } }), true);
    assert.equal(tracker.trackEvent("country_selected", { country_code: "LT", ignored: { nested: true } }), true);

    const queuedCalls = toQueuedCalls(dom.window.dataLayer);
    const eventCalls = queuedCalls.filter((entry) => entry[0] === "event");
    const consentCalls = queuedCalls.filter((entry) => entry[0] === "consent");
    const configCalls = queuedCalls.filter((entry) => entry[0] === "config");

    assert.equal(configCalls.length, 1);
    assert.equal(configCalls[0][1], "G-VWEM25PMN0");
    assert.deepEqual(configCalls[0][2], { send_page_view: false });
    assert.equal(consentCalls.at(-1)[2].analytics_storage, "granted");
    assert.equal(consentCalls.length, 3);
    assert.equal(eventCalls.length, 2);
    assert.equal(eventCalls[0][1], "page_view");
    assert.deepEqual(eventCalls[0][2], { page_path: "/manage-cookies/" });
    assert.equal(eventCalls[1][1], "country_selected");
    assert.deepEqual(eventCalls[1][2], { country_code: "LT" });

    tracker.syncConsentDecision("declined");
    const deniedConsentCalls = toQueuedCalls(dom.window.dataLayer).filter(
      (entry) => entry[0] === "consent" && entry[2]?.analytics_storage === "denied",
    );
    const deniedConsentUpdateCalls = deniedConsentCalls.filter((entry) => entry[1] === "update");
    assert.equal(deniedConsentCalls.length, 3);
    assert.equal(deniedConsentUpdateCalls.length, 2);
    assert.equal(tracker.trackEvent("after_decline", { country_code: "LT" }), false);
  }),
);
