import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { JSDOM } from "jsdom";

import { createD3GlobeRenderer } from "../src/app/globe/d3-globe-renderer.js";
import { selectBootstrapStatus, selectSelectedCountryCode } from "../src/app/state/selectors.js";
import { createAppStore } from "../src/app/state/store.js";
import { uiSelectedCountrySet } from "../src/app/state/ui-slice.js";
import { __test__, startStaticSiteApp } from "../src/app/static-site-app.js";

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
      await testFn(dom, previousFetch);
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
    if (selectBootstrapStatus(store.getState()) === "ready") {
      return;
    }

    await new Promise((resolve) => setTimeout(resolve, 0));
  }

  throw new Error("Timed out waiting for static-site bootstrap to finish.");
}

function stubBootstrapFetch({ activeCountryCodes = ["LT"] } = {}) {
  const displayNamesByCode = {
    LT: "Lithuania",
    LV: "Latvia",
    EE: "Estonia",
    DK: "Denmark",
  };

  const countries = activeCountryCodes.map((countryCode) => ({
    country_code: countryCode,
    display_name: displayNamesByCode[countryCode] || countryCode,
    payloads: {
      normalized_series: `${countryCode}/normalized_series.json`,
      forecast: `${countryCode}/forecast.json`,
    },
  }));

  globalThis.fetch = async (pathname) => {
    if (pathname === "/data/countries.json") {
      return {
        ok: true,
        async json() {
          return {
            contract_version: "ccoutline_site.v1",
            active_country_codes: activeCountryCodes,
            countries,
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

    const normalizedSeriesMatch = pathname.match(/^\/data\/([A-Z]{2})\/normalized_series\.json$/);
    if (normalizedSeriesMatch) {
      const [, countryCode] = normalizedSeriesMatch;
      return {
        ok: true,
        async json() {
          return {
            country_code: countryCode,
            display_name: displayNamesByCode[countryCode] || countryCode,
            indicators: [],
          };
        },
      };
    }

    const forecastMatch = pathname.match(/^\/data\/([A-Z]{2})\/forecast\.json$/);
    if (forecastMatch) {
      const [, countryCode] = forecastMatch;
      return {
        ok: true,
        async json() {
          return {
            country_code: countryCode,
            status: "ready",
            rows: [],
          };
        },
      };
    }

    throw new Error(`Unexpected fetch path ${pathname}`);
  };
}

test("static-site app helper treats Enter and Space as globe activation keys", () => {
  assert.equal(__test__.isGlobeKeyboardActivation({ key: "Enter" }), true);
  assert.equal(__test__.isGlobeKeyboardActivation({ key: " " }), true);
  assert.equal(__test__.isGlobeKeyboardActivation({ key: "Spacebar" }), true);
  assert.equal(__test__.isGlobeKeyboardActivation({ key: "Escape" }), false);
});

test(
  "static-site app dispatches globe selection only for supported country paths",
  withDom(async (dom) => {
    stubBootstrapFetch();
    const store = createAppStore();
    const appRoot = dom.window.document.querySelector("#root");

    startStaticSiteApp({ appRoot, store });
    await waitForBootstrapReady(store);

    appRoot.innerHTML = createD3GlobeRenderer().renderGlobe({
      worldGeometry: WORLD_GEOMETRY,
      selectedCountryCode: null,
    });

    const supportedCountry = appRoot.querySelector("path[data-country-code='LT']");
    const disabledCountry = appRoot.querySelector("path[data-country-code='SE']");

    supportedCountry.dispatchEvent(new dom.window.MouseEvent("click", { bubbles: true }));
    assert.equal(selectSelectedCountryCode(store.getState()), "LT");

    store.dispatch(uiSelectedCountrySet(null));
    disabledCountry.dispatchEvent(new dom.window.MouseEvent("click", { bubbles: true }));
    assert.equal(selectSelectedCountryCode(store.getState()), null);
  }),
);

test(
  "static-site app dispatches fallback country-button selection through the same store state",
  withDom(async (dom) => {
    stubBootstrapFetch();
    const store = createAppStore();
    const appRoot = dom.window.document.querySelector("#root");

    startStaticSiteApp({ appRoot, store });
    await waitForBootstrapReady(store);

    const countryButton = appRoot.querySelector("button[data-country-select-control='true'][data-country-code='LT']");
    assert.ok(countryButton);

    countryButton.dispatchEvent(new dom.window.MouseEvent("click", { bubbles: true }));
    assert.equal(selectSelectedCountryCode(store.getState()), "LT");
  }),
);

test(
  "static-site app patches globe navigation and the dedicated panel region when the selected country changes",
  withDom(async (dom) => {
    stubBootstrapFetch({ activeCountryCodes: ["LT", "LV"] });
    const store = createAppStore();
    const appRoot = dom.window.document.querySelector("#root");

    startStaticSiteApp({ appRoot, store });
    await waitForBootstrapReady(store);

    const heroSection = appRoot.querySelector("main.page-shell > section.section-panel:not([data-globe-navigation-block='true'])");
    assert.ok(heroSection);
    assert.match(appRoot.innerHTML, /data-country-panel-empty-state="true"/);

    const lithuaniaButton = appRoot.querySelector("button[data-country-select-control='true'][data-country-code='LT']");
    assert.ok(lithuaniaButton);
    lithuaniaButton.dispatchEvent(new dom.window.MouseEvent("click", { bubbles: true }));

    assert.equal(selectSelectedCountryCode(store.getState()), "LT");
    assert.strictEqual(
      appRoot.querySelector("main.page-shell > section.section-panel:not([data-globe-navigation-block='true'])"),
      heroSection,
    );
    assert.equal(appRoot.querySelector("[data-country-panel-region='true']")?.getAttribute("data-selected-country-code"), "LT");
    assert.ok(appRoot.querySelector("section[data-country-code='LT']"));
    assert.equal(appRoot.querySelector("button[data-country-code='LT']")?.getAttribute("aria-pressed"), "true");
    assert.equal(appRoot.querySelector("button[data-country-code='LV']")?.getAttribute("aria-pressed"), "false");

    const latviaButton = appRoot.querySelector("button[data-country-select-control='true'][data-country-code='LV']");
    assert.ok(latviaButton);
    latviaButton.dispatchEvent(new dom.window.MouseEvent("click", { bubbles: true }));

    assert.equal(selectSelectedCountryCode(store.getState()), "LV");
    assert.strictEqual(
      appRoot.querySelector("main.page-shell > section.section-panel:not([data-globe-navigation-block='true'])"),
      heroSection,
    );
    assert.equal(appRoot.querySelector("[data-country-panel-region='true']")?.getAttribute("data-selected-country-code"), "LV");
    assert.ok(appRoot.querySelector("section[data-country-code='LV']"));
    assert.equal(appRoot.querySelectorAll("section[data-country-code]").length, 1);
    assert.equal(appRoot.querySelector("button[data-country-code='LT']")?.getAttribute("aria-pressed"), "false");
    assert.equal(appRoot.querySelector("button[data-country-code='LV']")?.getAttribute("aria-pressed"), "true");
  }),
);

test(
  "static-site app supports keyboard globe activation and ignores non-activation keys",
  withDom(async (dom) => {
    stubBootstrapFetch();
    const store = createAppStore();
    const appRoot = dom.window.document.querySelector("#root");

    startStaticSiteApp({ appRoot, store });
    await waitForBootstrapReady(store);

    appRoot.innerHTML = createD3GlobeRenderer().renderGlobe({
      worldGeometry: WORLD_GEOMETRY,
      selectedCountryCode: null,
    });

    const supportedCountry = appRoot.querySelector("path[data-country-code='LT']");
    const enterEvent = new dom.window.KeyboardEvent("keydown", {
      bubbles: true,
      key: "Enter",
      cancelable: true,
    });
    supportedCountry.dispatchEvent(enterEvent);

    assert.equal(selectSelectedCountryCode(store.getState()), "LT");
    assert.equal(enterEvent.defaultPrevented, true);

    store.dispatch(uiSelectedCountrySet(null));
    const escapeEvent = new dom.window.KeyboardEvent("keydown", {
      bubbles: true,
      key: "Escape",
      cancelable: true,
    });
    supportedCountry.dispatchEvent(escapeEvent);

    assert.equal(selectSelectedCountryCode(store.getState()), null);
    assert.equal(escapeEvent.defaultPrevented, false);
  }),
);

test(
  "static-site app ignores keyboard activation on disabled globe countries",
  withDom(async (dom) => {
    stubBootstrapFetch();
    const store = createAppStore();
    const appRoot = dom.window.document.querySelector("#root");

    startStaticSiteApp({ appRoot, store });
    await waitForBootstrapReady(store);

    appRoot.innerHTML = createD3GlobeRenderer().renderGlobe({
      worldGeometry: WORLD_GEOMETRY,
      selectedCountryCode: null,
    });

    const disabledCountry = appRoot.querySelector("path[data-country-code='SE']");
    const enterEvent = new dom.window.KeyboardEvent("keydown", {
      bubbles: true,
      key: "Enter",
      cancelable: true,
    });
    disabledCountry.dispatchEvent(enterEvent);

    assert.equal(selectSelectedCountryCode(store.getState()), null);
    assert.equal(enterEvent.defaultPrevented, false);
  }),
);
