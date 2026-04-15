import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import {
  GLOBE_FIXED_VIEW,
  GLOBE_SUPPORTED_COUNTRIES,
  GLOBE_WORLD_GEOMETRY_PATH,
  getSupportedGlobeCountry,
  getSupportedGlobeCountryForFeature,
  isSelectableGlobeFeature,
  isSupportedGlobeCountryCode,
  resolveGlobeFeatureCountryCode,
} from "../src/app/globe/globe-country-config.js";

const TEST_DIR = path.dirname(fileURLToPath(import.meta.url));
const WORLD_GEOMETRY_FILE = path.resolve(TEST_DIR, "../src/app/globe/world-countries.geojson");
const GLOBE_FIDELITY_BASELINE_VERTICES = Object.freeze({
  LT: 19,
  LV: 22,
  EE: 19,
  DK: 24,
});

function readWorldGeometry() {
  return JSON.parse(readFileSync(WORLD_GEOMETRY_FILE, "utf8"));
}

function countGeometryVertices(geometry) {
  function walkCoordinates(coordinates) {
    if (!Array.isArray(coordinates)) {
      return 0;
    }

    if (typeof coordinates[0] === "number") {
      return 1;
    }

    return coordinates.reduce((total, childCoordinates) => total + walkCoordinates(childCoordinates), 0);
  }

  return walkCoordinates(geometry?.coordinates);
}

test("globe country config exposes the frozen supported-country mapping and fixed view", () => {
  assert.equal(GLOBE_WORLD_GEOMETRY_PATH, "/app/globe/world-countries.geojson");
  assert.deepEqual(
    GLOBE_SUPPORTED_COUNTRIES.map((entry) => entry.countryCode),
    ["LT", "LV", "EE", "DK"],
  );
  assert.deepEqual(GLOBE_FIXED_VIEW.center, [18, 57.5]);
  assert.deepEqual(GLOBE_FIXED_VIEW.rotation, [-18, -57.5, 0]);
  assert.equal(GLOBE_FIXED_VIEW.precision, 0.25);
  assert.equal(getSupportedGlobeCountry("lt")?.label, "Lithuania");
  assert.equal(isSupportedGlobeCountryCode("EE"), true);
  assert.equal(isSupportedGlobeCountryCode("SE"), false);
});

test("globe geometry asset includes the supported countries and resolves selectable features through config helpers", () => {
  const worldGeometry = readWorldGeometry();

  assert.equal(worldGeometry.type, "FeatureCollection");
  assert.ok(Array.isArray(worldGeometry.features));
  assert.ok(worldGeometry.features.length > 150);

  const lithuaniaFeature = worldGeometry.features.find((feature) => feature?.properties?.country_code === "LT");
  const swedenFeature = worldGeometry.features.find((feature) => feature?.properties?.country_code === "SE");

  assert.equal(resolveGlobeFeatureCountryCode(lithuaniaFeature), "LT");
  assert.equal(getSupportedGlobeCountryForFeature(lithuaniaFeature)?.countryCode, "LT");
  assert.equal(isSelectableGlobeFeature(lithuaniaFeature), true);

  assert.equal(resolveGlobeFeatureCountryCode(swedenFeature), "SE");
  assert.equal(getSupportedGlobeCountryForFeature(swedenFeature), null);
  assert.equal(isSelectableGlobeFeature(swedenFeature), false);
});

test("globe geometry asset keeps higher-detail supported-country shapes above the old 110m baselines", () => {
  const worldGeometry = readWorldGeometry();

  for (const [countryCode, baselineVertexCount] of Object.entries(GLOBE_FIDELITY_BASELINE_VERTICES)) {
    const supportedFeature = worldGeometry.features.find((feature) => feature?.properties?.country_code === countryCode);
    const vertexCount = countGeometryVertices(supportedFeature?.geometry);

    assert.ok(
      vertexCount > baselineVertexCount,
      `${countryCode} should stay above ${baselineVertexCount} vertices, received ${vertexCount}`,
    );
  }
});
