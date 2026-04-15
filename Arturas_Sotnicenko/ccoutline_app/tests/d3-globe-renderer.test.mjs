import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { JSDOM } from "jsdom";

import { __test__, createD3GlobeRenderer } from "../src/app/globe/d3-globe-renderer.js";

const TEST_DIR = path.dirname(fileURLToPath(import.meta.url));
const WORLD_GEOMETRY = JSON.parse(
  readFileSync(path.resolve(TEST_DIR, "../src/app/globe/world-countries.geojson"), "utf8"),
);

function withDom(testFn) {
  return async () => {
    const dom = new JSDOM("<!doctype html><div id='root'></div>", {
      pretendToBeVisual: true,
    });
    const previousWindow = globalThis.window;
    const previousDocument = globalThis.document;
    const previousElement = globalThis.Element;
    const previousHTMLElement = globalThis.HTMLElement;
    const previousSVGElement = globalThis.SVGElement;

    globalThis.window = dom.window;
    globalThis.document = dom.window.document;
    globalThis.Element = dom.window.Element;
    globalThis.HTMLElement = dom.window.HTMLElement;
    globalThis.SVGElement = dom.window.SVGElement;

    try {
      await testFn(dom);
    } finally {
      globalThis.window = previousWindow;
      globalThis.document = previousDocument;
      globalThis.Element = previousElement;
      globalThis.HTMLElement = previousHTMLElement;
      globalThis.SVGElement = previousSVGElement;
      dom.window.close();
    }
  };
}

test("globe renderer view models classify supported and disabled countries from the local geometry asset", () => {
  const featureViewModels = __test__.buildGlobeFeatureViewModels(WORLD_GEOMETRY, {
    selectedCountryCode: "LT",
  });

  const lithuania = featureViewModels.find((featureViewModel) => featureViewModel.countryCode === "LT");
  const sweden = featureViewModels.find((featureViewModel) => featureViewModel.countryCode === "SE");
  const australia = featureViewModels.find((featureViewModel) => featureViewModel.countryCode === "AU");

  assert.equal(lithuania?.isSelectable, true);
  assert.equal(lithuania?.isSelected, true);
  assert.equal(lithuania?.isVisible, true);
  assert.equal(lithuania?.displayName, "Lithuania");
  assert.match(__test__.buildCountryPathClassName(lithuania), /globe-nav__country--supported/);
  assert.match(__test__.buildCountryPathClassName(lithuania), /globe-nav__country--selected/);
  assert.match(__test__.buildCountryTitle(lithuania), /selected supported country/);

  assert.equal(sweden?.isSelectable, false);
  assert.equal(sweden?.isSelected, false);
  assert.equal(sweden?.isVisible, true);
  assert.match(__test__.buildCountryPathClassName(sweden), /globe-nav__country--disabled/);
  assert.match(__test__.buildCountryTitle(sweden), /regional context only/);
  assert.equal(australia?.isVisible, false);
});

test("globe renderer projection stays tied to the fixed Baltic-plus-Denmark framing", () => {
  const featureViewModels = __test__.buildGlobeFeatureViewModels(WORLD_GEOMETRY, {
    selectedCountryCode: null,
  });
  const projection = __test__.buildOrthographicProjection({
    featureViewModels,
    width: 520,
    height: 520,
    padding: 26,
  });

  assert.deepEqual(projection.rotate(), [-18, -57.5, 0]);
  assert.equal(projection.clipAngle(), 90);
});

test("globe renderer sorts selected and supported countries above disabled context features", () => {
  const featureViewModels = __test__.buildGlobeFeatureViewModels(WORLD_GEOMETRY, {
    selectedCountryCode: "DK",
  });
  const visibleFeatures = featureViewModels.filter((featureViewModel) => featureViewModel.isVisible);
  const sortedFeatures = __test__.sortGlobeFeatureViewModels(visibleFeatures);

  assert.equal(sortedFeatures.at(-1)?.countryCode, "DK");
  assert.equal(sortedFeatures.at(-1)?.isSelected, true);
  assert.equal(sortedFeatures.at(0)?.isSelectable, false);
  assert.deepEqual(
    __test__.buildLegendItems().map((item) => item.kind),
    ["selected", "supported", "disabled"],
  );
});

test("d3 globe renderer returns fixed-globe markup with graticule, legend, and visible country paths only", withDom((dom) => {
  const renderer = createD3GlobeRenderer();
  const root = dom.window.document.querySelector("#root");

  root.innerHTML = renderer.renderGlobe({
    worldGeometry: WORLD_GEOMETRY,
    selectedCountryCode: "EE",
  });

  const figure = root.querySelector("figure.globe-nav[data-globe-adapter='d3']");
  const svg = root.querySelector("svg.globe-nav__svg");
  const sphere = root.querySelector("path.globe-nav__sphere");
  const graticule = root.querySelector("path.globe-nav__graticule");
  const selectedCountry = root.querySelector("path[data-country-code='EE']");
  const disabledCountry = root.querySelector("path[data-country-code='SE']");
  const hiddenCountry = root.querySelector("path[data-country-code='AU']");
  const caption = root.querySelector("figcaption.globe-nav__caption");
  const legendLabels = Array.from(root.querySelectorAll(".globe-nav__legend-label")).map((node) => node.textContent?.trim());
  const selectedTitle = selectedCountry?.querySelector("title");

  assert.ok(figure);
  assert.ok(svg);
  assert.ok(sphere);
  assert.ok(graticule);
  assert.ok(selectedCountry);
  assert.ok(disabledCountry);
  assert.equal(hiddenCountry, null);
  assert.equal(svg.getAttribute("aria-label"), "CCOUTLINE country selection globe");
  assert.equal(figure.getAttribute("data-selected-country-code"), "EE");
  assert.equal(selectedCountry.getAttribute("data-globe-selectable"), "true");
  assert.equal(selectedCountry.getAttribute("data-globe-country-select"), "true");
  assert.equal(selectedCountry.getAttribute("data-country-selected"), "true");
  assert.equal(selectedCountry.getAttribute("data-globe-visibility"), "visible");
  assert.equal(selectedCountry.getAttribute("role"), "button");
  assert.equal(selectedCountry.getAttribute("tabindex"), "0");
  assert.equal(selectedCountry.getAttribute("focusable"), "true");
  assert.equal(selectedCountry.getAttribute("aria-pressed"), "true");
  assert.match(selectedCountry.getAttribute("class") || "", /globe-nav__country--selected/);
  assert.equal(disabledCountry.getAttribute("data-globe-selectable"), "false");
  assert.equal(disabledCountry.getAttribute("data-globe-country-select"), null);
  assert.equal(disabledCountry.getAttribute("data-globe-country-disabled"), "true");
  assert.equal(disabledCountry.getAttribute("role"), null);
  assert.equal(disabledCountry.getAttribute("tabindex"), null);
  assert.equal(disabledCountry.getAttribute("focusable"), "false");
  assert.match(disabledCountry.getAttribute("class") || "", /globe-nav__country--disabled/);
  assert.match(selectedTitle?.textContent || "", /selected supported country/);
  assert.deepEqual(legendLabels, ["Selected country", "Supported country", "Context only"]);
  assert.match(caption?.textContent || "", /Estonia is highlighted/);
  assert.match(caption?.textContent || "", /muted/);
}));
