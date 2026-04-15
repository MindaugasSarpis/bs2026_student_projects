import test from "node:test";
import assert from "node:assert/strict";

import { fetchCountryModel, fetchGlobeWorldGeometry } from "../src/app/data/site-data-loader.js";

test("fetchGlobeWorldGeometry loads the committed globe geometry asset from the app path", async () => {
  const originalFetch = globalThis.fetch;
  const fetchCalls = [];

  globalThis.fetch = async (pathname) => {
    fetchCalls.push(pathname);

    if (pathname === "/app/globe/world-countries.geojson") {
      return {
        ok: true,
        async json() {
          return {
            type: "FeatureCollection",
            features: [],
          };
        },
      };
    }

    throw new Error(`Unexpected fetch path ${pathname}`);
  };

  try {
    const geometry = await fetchGlobeWorldGeometry();
    assert.deepEqual(fetchCalls, ["/app/globe/world-countries.geojson"]);
    assert.equal(geometry.type, "FeatureCollection");
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("fetchCountryModel loads normalized series and forecast payloads for a valid country entry", async () => {
  const originalFetch = globalThis.fetch;
  const fetchCalls = [];

  globalThis.fetch = async (pathname) => {
    fetchCalls.push(pathname);

    if (pathname === "/data/LT/normalized_series.json") {
      return {
        ok: true,
        async json() {
          return { country_code: "LT", indicators: [] };
        },
      };
    }

    if (pathname === "/data/LT/forecast.json") {
      return {
        ok: true,
        async json() {
          return { country_code: "LT", status: "ready", rows: [] };
        },
      };
    }

    throw new Error(`Unexpected fetch path ${pathname}`);
  };

  try {
    const model = await fetchCountryModel({
      country_code: "LT",
      payloads: {
        normalized_series: "LT/normalized_series.json",
        forecast: "LT/forecast.json",
      },
    });

    assert.deepEqual(fetchCalls, ["/data/LT/normalized_series.json", "/data/LT/forecast.json"]);
    assert.equal(model.countryCode, "LT");
    assert.equal(model.loadError, null);
    assert.equal(model.forecastLoadError, null);
    assert.deepEqual(model.normalizedSeries, {
      country_code: "LT",
      indicators: [],
    });
    assert.deepEqual(model.forecast, {
      country_code: "LT",
      status: "ready",
      rows: [],
    });
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("fetchCountryModel keeps normalized series available when forecast payload loading fails", async () => {
  const originalFetch = globalThis.fetch;

  globalThis.fetch = async (pathname) => {
    if (pathname === "/data/LT/normalized_series.json") {
      return {
        ok: true,
        async json() {
          return { country_code: "LT", indicators: [] };
        },
      };
    }

    if (pathname === "/data/LT/forecast.json") {
      return {
        ok: false,
        status: 404,
      };
    }

    throw new Error(`Unexpected fetch path ${pathname}`);
  };

  try {
    const model = await fetchCountryModel({
      country_code: "LT",
      payloads: {
        normalized_series: "LT/normalized_series.json",
        forecast: "LT/forecast.json",
      },
    });

    assert.equal(model.countryCode, "LT");
    assert.equal(model.loadError, null);
    assert.equal(model.normalizedSeries?.country_code, "LT");
    assert.equal(model.forecast, null);
    assert.equal(model.forecastLoadError, "Request failed for /data/LT/forecast.json with 404");
  } finally {
    globalThis.fetch = originalFetch;
  }
});
