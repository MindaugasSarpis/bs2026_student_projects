import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { JSDOM } from "jsdom";

import { ANALYTICS_RUNTIME_CONFIG } from "../src/app/config/analytics-config.js";
import { createAppStore } from "../src/app/state/store.js";
import { startStaticSiteApp } from "../src/app/static-site-app.js";

const TEST_DIR = path.dirname(fileURLToPath(import.meta.url));
const WORLD_GEOMETRY = JSON.parse(
  readFileSync(path.resolve(TEST_DIR, "../src/app/globe/world-countries.geojson"), "utf8"),
);

function withDom(testFn) {
  return async () => {
    const dom = new JSDOM("<!doctype html><div id='root'></div>", {
      pretendToBeVisual: true,
      url: "https://ccoutline.test/",
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

async function waitForBootstrapReady(store) {
  for (let attempt = 0; attempt < 20; attempt += 1) {
    if (store.getState().app.bootstrapStatus === "ready") {
      return;
    }

    await new Promise((resolve) => setTimeout(resolve, 0));
  }

  throw new Error("Timed out waiting for static-site bootstrap to finish.");
}

function stubBootstrapFetch() {
  globalThis.fetch = async (pathname) => {
    if (pathname === "/data/countries.json") {
      return {
        ok: true,
        async json() {
          return {
            contract_version: "ccoutline_site.v1",
            active_country_codes: ["LT"],
            countries: [
              {
                country_code: "LT",
                display_name: "Lithuania",
                payloads: {
                  normalized_series: "LT/normalized_series.json",
                  forecast: "LT/forecast.json",
                },
              },
            ],
          };
        },
      };
    }

    if (pathname === "/app/globe/world-countries.geojson") {
      return {
        ok: true,
        async json() {
          return WORLD_GEOMETRY;
        },
      };
    }

    if (pathname === "/data/LT/normalized_series.json") {
      return {
        ok: true,
        async json() {
          return {
            country_code: "LT",
            display_name: "Lithuania",
            indicators: [],
          };
        },
      };
    }

    if (pathname === "/data/LT/forecast.json") {
      return {
        ok: true,
        async json() {
          return {
            country_code: "LT",
            status: "ready",
            rows: [],
          };
        },
      };
    }

    throw new Error(`Unexpected fetch path ${pathname}`);
  };
}

test(
  "static-site app hydrates consent from localStorage and persists accept or decline actions through the banner",
  withDom(async (dom) => {
    stubBootstrapFetch();
    const appRoot = dom.window.document.querySelector("#root");
    const store = createAppStore();

    startStaticSiteApp({ appRoot, store });
    await waitForBootstrapReady(store);

    const initialBanner = appRoot.querySelector("[data-consent-banner='true']");
    assert.ok(initialBanner);
    assert.equal(store.getState().consent.decision, null);

    const declineButton = appRoot.querySelector("[data-consent-action='declined']");
    assert.ok(declineButton);
    declineButton.dispatchEvent(new dom.window.MouseEvent("click", { bubbles: true }));

    assert.equal(store.getState().consent.decision, "declined");
    assert.equal(dom.window.localStorage.getItem(ANALYTICS_RUNTIME_CONFIG.consent.decisionStorageKey), "declined");
    assert.equal(appRoot.querySelector("[data-consent-banner='true']"), null);

    const secondRoot = dom.window.document.createElement("div");
    dom.window.document.body.append(secondRoot);
    const secondStore = createAppStore();
    startStaticSiteApp({ appRoot: secondRoot, store: secondStore });
    await waitForBootstrapReady(secondStore);

    assert.equal(secondStore.getState().consent.decision, "declined");
    assert.equal(secondRoot.querySelector("[data-consent-banner='true']"), null);
  }),
);

test(
  "static-site app treats the undecided consent surface as a blocking modal with focus trap and scroll lock",
  withDom(async (dom) => {
    stubBootstrapFetch();
    const appRoot = dom.window.document.querySelector("#root");
    const store = createAppStore();

    startStaticSiteApp({ appRoot, store });
    await waitForBootstrapReady(store);

    const consentBanner = appRoot.querySelector("[data-consent-banner='true']");
    const consentDialog = appRoot.querySelector("[data-consent-dialog='true']");
    const pageShell = appRoot.querySelector("main.page-shell");
    const siteFooter = appRoot.querySelector("footer.site-footer");
    const firstLegalLink = appRoot.querySelector("[data-consent-dialog='true'] a[data-legal-link='privacy']");
    const acceptButton = appRoot.querySelector("[data-consent-dialog='true'] [data-consent-action='accepted']");
    const declineButton = appRoot.querySelector("[data-consent-dialog='true'] [data-consent-action='declined']");

    assert.ok(consentBanner);
    assert.ok(consentDialog);
    assert.equal(consentDialog.getAttribute("role"), "dialog");
    assert.equal(consentDialog.getAttribute("aria-modal"), "true");
    assert.equal(dom.window.document.activeElement, consentDialog);
    assert.equal(dom.window.document.body.style.overflow, "hidden");
    assert.equal(dom.window.document.documentElement.style.overflow, "hidden");
    assert.equal(pageShell?.getAttribute("inert"), "");
    assert.equal(pageShell?.getAttribute("aria-hidden"), "true");
    assert.equal(siteFooter?.getAttribute("inert"), "");
    assert.equal(siteFooter?.getAttribute("aria-hidden"), "true");

    consentDialog.dispatchEvent(new dom.window.KeyboardEvent("keydown", { key: "Tab", bubbles: true, cancelable: true }));
    assert.equal(dom.window.document.activeElement, firstLegalLink);

    firstLegalLink.dispatchEvent(
      new dom.window.KeyboardEvent("keydown", { key: "Tab", shiftKey: true, bubbles: true, cancelable: true }),
    );
    assert.equal(dom.window.document.activeElement, declineButton);

    declineButton.dispatchEvent(
      new dom.window.KeyboardEvent("keydown", { key: "Tab", bubbles: true, cancelable: true }),
    );
    assert.equal(dom.window.document.activeElement, firstLegalLink);

    const escapeEvent = new dom.window.KeyboardEvent("keydown", {
      key: "Escape",
      bubbles: true,
      cancelable: true,
    });
    const escapeDispatchResult = consentDialog.dispatchEvent(escapeEvent);
    assert.equal(escapeDispatchResult, false);
    assert.ok(appRoot.querySelector("[data-consent-banner='true']"));

    acceptButton.dispatchEvent(new dom.window.MouseEvent("click", { bubbles: true }));

    assert.equal(store.getState().consent.decision, "accepted");
    assert.equal(appRoot.querySelector("[data-consent-banner='true']"), null);
    assert.equal(dom.window.document.body.style.overflow, "");
    assert.equal(dom.window.document.documentElement.style.overflow, "");
    const updatedPageShell = appRoot.querySelector("main.page-shell");
    const updatedSiteFooter = appRoot.querySelector("footer.site-footer");
    assert.equal(updatedPageShell?.hasAttribute("inert"), false);
    assert.equal(updatedPageShell?.getAttribute("aria-hidden"), null);
    assert.equal(updatedSiteFooter?.hasAttribute("inert"), false);
    assert.equal(updatedSiteFooter?.getAttribute("aria-hidden"), null);
  }),
);

test(
  "static-site app restores scroll and background interactivity after declining from the consent modal",
  withDom(async (dom) => {
    stubBootstrapFetch();
    const appRoot = dom.window.document.querySelector("#root");
    const store = createAppStore();

    startStaticSiteApp({ appRoot, store });
    await waitForBootstrapReady(store);

    const declineButton = appRoot.querySelector("[data-consent-dialog='true'] [data-consent-action='declined']");
    assert.ok(declineButton);
    assert.equal(dom.window.document.body.style.overflow, "hidden");
    assert.equal(dom.window.document.documentElement.style.overflow, "hidden");
    assert.equal(appRoot.querySelector("main.page-shell")?.getAttribute("inert"), "");
    assert.equal(appRoot.querySelector("footer.site-footer")?.getAttribute("inert"), "");

    declineButton.dispatchEvent(new dom.window.MouseEvent("click", { bubbles: true }));

    assert.equal(store.getState().consent.decision, "declined");
    assert.equal(appRoot.querySelector("[data-consent-banner='true']"), null);
    assert.equal(dom.window.document.body.style.overflow, "");
    assert.equal(dom.window.document.documentElement.style.overflow, "");
    assert.equal(appRoot.querySelector("main.page-shell")?.hasAttribute("inert"), false);
    assert.equal(appRoot.querySelector("main.page-shell")?.getAttribute("aria-hidden"), null);
    assert.equal(appRoot.querySelector("footer.site-footer")?.hasAttribute("inert"), false);
    assert.equal(appRoot.querySelector("footer.site-footer")?.getAttribute("aria-hidden"), null);
  }),
);
