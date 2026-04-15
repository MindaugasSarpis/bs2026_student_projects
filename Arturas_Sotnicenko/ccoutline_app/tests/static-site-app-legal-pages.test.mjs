import test from "node:test";
import assert from "node:assert/strict";
import { JSDOM } from "jsdom";

import { ANALYTICS_RUNTIME_CONFIG } from "../src/app/config/analytics-config.js";
import { createAppStore } from "../src/app/state/store.js";
import { startStaticSiteApp } from "../src/app/static-site-app.js";

function createStubTracker() {
  return {
    enableCalls: 0,
    syncConsentCalls: [],
    trackedEvents: [],
    enable() {
      this.enableCalls += 1;
      return true;
    },
    syncConsentDecision(decision) {
      this.syncConsentCalls.push(decision);
      return true;
    },
    trackEvent(name, params) {
      this.trackedEvents.push({ name, params });
      return true;
    },
  };
}

function withDom(url, testFn) {
  return async () => {
    const dom = new JSDOM("<!doctype html><div id='root'></div>", {
      pretendToBeVisual: true,
      url,
    });
    const previousWindow = globalThis.window;
    const previousDocument = globalThis.document;
    const previousElement = globalThis.Element;
    const previousHTMLElement = globalThis.HTMLElement;
    const previousHTMLInputElement = globalThis.HTMLInputElement;
    const previousSVGElement = globalThis.SVGElement;
    const previousMouseEvent = globalThis.MouseEvent;
    const previousKeyboardEvent = globalThis.KeyboardEvent;
    const previousEvent = globalThis.Event;
    const previousFetch = globalThis.fetch;

    globalThis.window = dom.window;
    globalThis.document = dom.window.document;
    globalThis.Element = dom.window.Element;
    globalThis.HTMLElement = dom.window.HTMLElement;
    globalThis.HTMLInputElement = dom.window.HTMLInputElement;
    globalThis.SVGElement = dom.window.SVGElement;
    globalThis.MouseEvent = dom.window.MouseEvent;
    globalThis.KeyboardEvent = dom.window.KeyboardEvent;
    globalThis.Event = dom.window.Event;

    try {
      await testFn(dom);
    } finally {
      globalThis.window = previousWindow;
      globalThis.document = previousDocument;
      globalThis.Element = previousElement;
      globalThis.HTMLElement = previousHTMLElement;
      globalThis.HTMLInputElement = previousHTMLInputElement;
      globalThis.SVGElement = previousSVGElement;
      globalThis.MouseEvent = previousMouseEvent;
      globalThis.KeyboardEvent = previousKeyboardEvent;
      globalThis.Event = previousEvent;
      globalThis.fetch = previousFetch;
      dom.window.close();
    }
  };
}

async function waitForPaint() {
  await new Promise((resolve) => setTimeout(resolve, 0));
}

test(
  "static-site app renders the privacy page without bootstrapping country data",
  withDom("https://ccoutline.test/privacy/", async (dom) => {
    const fetchCalls = [];
    globalThis.fetch = async (pathname) => {
      fetchCalls.push(pathname);
      throw new Error(`Legal routes should not fetch staged country data: ${pathname}`);
    };

    const store = createAppStore();
    const appRoot = dom.window.document.querySelector("#root");
    startStaticSiteApp({ appRoot, store });
    await waitForPaint();

    assert.equal(fetchCalls.length, 0);
    assert.match(appRoot.innerHTML, /data-legal-page="privacy"/);
    assert.match(appRoot.innerHTML, /Privacy Notice/);
    assert.match(appRoot.innerHTML, /href="\/cookies\/" data-legal-link="cookies"/);
    assert.match(appRoot.innerHTML, /href="\/privacy\/" data-legal-link="privacy" aria-current="page"/);
    assert.doesNotMatch(appRoot.innerHTML, /Country intelligence in one place/);
  }),
);

test(
  "static-site app renders manage-cookies and persists updated consent from that route",
  withDom("https://ccoutline.test/manage-cookies/", async (dom) => {
    dom.window.localStorage.setItem(ANALYTICS_RUNTIME_CONFIG.consent.decisionStorageKey, "accepted");
    dom.window.localStorage.setItem(ANALYTICS_RUNTIME_CONFIG.consent.updatedAtStorageKey, "2026-04-12T18:45:00.000Z");
    globalThis.fetch = async (pathname) => {
      throw new Error(`Manage-cookies route should not fetch staged country data: ${pathname}`);
    };

    const store = createAppStore();
    const appRoot = dom.window.document.querySelector("#root");
    startStaticSiteApp({ appRoot, store });
    await waitForPaint();

    assert.equal(store.getState().consent.decision, "accepted");
    assert.match(appRoot.innerHTML, /data-legal-page="manage-cookies"/);
    assert.match(appRoot.innerHTML, /Current analytics choice: Accepted/);
    assert.doesNotMatch(appRoot.innerHTML, /data-consent-banner="true"/);

    const declineButton = appRoot.querySelector("[data-manage-cookies-panel='true'] [data-consent-action='declined']");
    assert.ok(declineButton);
    declineButton.dispatchEvent(new dom.window.MouseEvent("click", { bubbles: true }));
    await waitForPaint();

    assert.equal(store.getState().consent.decision, "declined");
    assert.equal(dom.window.localStorage.getItem(ANALYTICS_RUNTIME_CONFIG.consent.decisionStorageKey), "declined");
    assert.match(appRoot.innerHTML, /Current analytics choice: Declined/);
  }),
);

test(
  "static-site app keeps the GA loader disabled until analytics consent is accepted",
  withDom("https://ccoutline.test/manage-cookies/", async (dom) => {
    globalThis.fetch = async (pathname) => {
      throw new Error(`Manage-cookies route should not fetch staged country data: ${pathname}`);
    };

    const store = createAppStore();
    const appRoot = dom.window.document.querySelector("#root");
    startStaticSiteApp({ appRoot, store });
    await waitForPaint();

    assert.equal(dom.window.document.querySelector('script[src*="googletagmanager.com/gtag/js"]'), null);

    const acceptButton = appRoot.querySelector("[data-manage-cookies-panel='true'] [data-consent-action='accepted']");
    assert.ok(acceptButton);
    acceptButton.dispatchEvent(new dom.window.MouseEvent("click", { bubbles: true }));
    await waitForPaint();

    const gaScript = dom.window.document.querySelector('script[src*="googletagmanager.com/gtag/js?id=G-VWEM25PMN0"]');
    assert.ok(gaScript);
  }),
);

test(
  "static-site app emits an explicit initial-load page_view when an accepted session opens on a legal route",
  withDom("https://ccoutline.test/manage-cookies/", async (dom) => {
    dom.window.localStorage.setItem(ANALYTICS_RUNTIME_CONFIG.consent.decisionStorageKey, "accepted");
    dom.window.localStorage.setItem(ANALYTICS_RUNTIME_CONFIG.consent.updatedAtStorageKey, "2026-04-12T18:45:00.000Z");
    globalThis.fetch = async (pathname) => {
      throw new Error(`Manage-cookies route should not fetch staged country data: ${pathname}`);
    };

    const analyticsTracker = createStubTracker();
    const store = createAppStore({ analyticsTracker });
    const appRoot = dom.window.document.querySelector("#root");
    startStaticSiteApp({ appRoot, store });
    await waitForPaint();

    assert.deepEqual(analyticsTracker.syncConsentCalls, ["accepted"]);
    assert.equal(analyticsTracker.enableCalls, 1);
    assert.deepEqual(analyticsTracker.trackedEvents, [
      {
        name: "page_view",
        params: {
          page_location: "https://ccoutline.test/manage-cookies/",
          page_path: "/manage-cookies/",
          page_title: "CCOUTLINE",
          trigger: "initial_load",
        },
      },
    ]);
  }),
);

test(
  "static-site app emits an explicit page_view after consent is accepted on manage-cookies",
  withDom("https://ccoutline.test/manage-cookies/", async (dom) => {
    globalThis.fetch = async (pathname) => {
      throw new Error(`Manage-cookies route should not fetch staged country data: ${pathname}`);
    };

    const analyticsTracker = createStubTracker();
    const store = createAppStore({ analyticsTracker });
    const appRoot = dom.window.document.querySelector("#root");
    startStaticSiteApp({ appRoot, store });
    await waitForPaint();

    const acceptButton = appRoot.querySelector("[data-manage-cookies-panel='true'] [data-consent-action='accepted']");
    assert.ok(acceptButton);
    acceptButton.dispatchEvent(new dom.window.MouseEvent("click", { bubbles: true }));
    await waitForPaint();

    assert.deepEqual(analyticsTracker.syncConsentCalls, ["accepted"]);
    assert.equal(analyticsTracker.enableCalls, 1);
    assert.deepEqual(analyticsTracker.trackedEvents, [
      {
        name: "analytics_consent_updated",
        params: {
          decision: "accepted",
          page_path: "/manage-cookies/",
          surface: "manage_cookies_page",
        },
      },
      {
        name: "page_view",
        params: {
          page_location: "https://ccoutline.test/manage-cookies/",
          page_path: "/manage-cookies/",
          page_title: "CCOUTLINE",
          trigger: "consent_accept",
        },
      },
    ]);
  }),
);
