import test from "node:test";
import assert from "node:assert/strict";

import { appBootstrapFailed, appBootstrapStarted, appBootstrapSucceeded } from "../src/app/state/app-slice.js";
import {
  countriesPayloadReceived,
  countriesStateReset,
  countryPayloadLoadFinished,
  countryPayloadLoadStarted,
} from "../src/app/state/countries-slice.js";
import {
  selectAppRenderState,
  selectBootstrapStatus,
  selectConsentDecision,
  selectCountryLoadStateByCode,
  selectCountryModelByCode,
  selectCountryModels,
  selectIsConsentHydrated,
  selectOrderedCountryEntries,
  selectSelectedCountryCode,
  selectSelectedCountryModel,
} from "../src/app/state/selectors.js";
import { createAppStore } from "../src/app/state/store.js";
import { uiSelectedCountrySet } from "../src/app/state/ui-slice.js";

test("createAppStore exposes idle bootstrap state and empty staged country data by default", () => {
  const store = createAppStore();

  assert.equal(selectBootstrapStatus(store.getState()), "idle");
  assert.deepEqual(selectCountryModels(store.getState()), []);
  assert.equal(selectSelectedCountryCode(store.getState()), null);
  assert.equal(selectSelectedCountryModel(store.getState()), null);
  assert.deepEqual(selectAppRenderState(store.getState()), {
    countriesError: null,
    consentState: {
      decision: null,
      hydrated: false,
      updatedAt: null,
    },
    countriesPayload: {
      contract_version: "ccoutline_site.v1",
      active_country_codes: [],
      countries: [],
    },
    countryModels: [],
  });
  assert.equal(selectConsentDecision(store.getState()), null);
  assert.equal(selectIsConsentHydrated(store.getState()), false);
});

test("store selectors preserve export ordering across payload and country-model staging", () => {
  const store = createAppStore();

  store.dispatch(appBootstrapStarted());
  store.dispatch(
    countriesPayloadReceived({
      contract_version: "ccoutline_site.v1",
      active_country_codes: ["LT", "EE"],
      countries: [
        {
          country_code: "EE",
          display_name: "Estonia",
          payloads: {
            normalized_series: "EE/normalized_series.json",
          },
        },
        {
          country_code: "LT",
          display_name: "Lithuania",
          payloads: {
            normalized_series: "LT/normalized_series.json",
          },
        },
      ],
    }),
  );

  assert.deepEqual(
    selectOrderedCountryEntries(store.getState()).map((entry) => entry.country_code),
    ["LT", "EE"],
  );
  assert.deepEqual(selectCountryLoadStateByCode(store.getState(), "LT"), {
    forecastError: null,
    status: "idle",
    error: null,
  });

  store.dispatch(countryPayloadLoadStarted({ countryCode: "LT" }));
  store.dispatch(
    countryPayloadLoadFinished({
      countryCode: "LT",
      countryEntry: {
        country_code: "LT",
        display_name: "Lithuania",
      },
      forecast: {
        country_code: "LT",
        status: "ready",
        rows: [],
      },
      forecastLoadError: null,
      loadError: null,
      normalizedSeries: {
        country_code: "LT",
      },
    }),
  );
  store.dispatch(countryPayloadLoadStarted({ countryCode: "EE" }));
  store.dispatch(
    countryPayloadLoadFinished({
      countryCode: "EE",
      countryEntry: {
        country_code: "EE",
        display_name: "Estonia",
      },
      forecast: null,
      forecastLoadError: "Request failed for /data/EE/forecast.json with 404",
      loadError: "Request failed for /data/EE/normalized_series.json with 404",
      normalizedSeries: null,
    }),
  );
  store.dispatch(appBootstrapSucceeded());

  assert.equal(selectBootstrapStatus(store.getState()), "ready");
  assert.deepEqual(
    selectCountryModels(store.getState()).map((model) => model.countryCode),
    ["LT", "EE"],
  );
  assert.equal(selectCountryModelByCode(store.getState(), "lt")?.countryEntry?.display_name, "Lithuania");
  store.dispatch(uiSelectedCountrySet({ countryCode: "LT" }));
  assert.deepEqual(selectCountryLoadStateByCode(store.getState(), "LT"), {
    forecastError: null,
    status: "ready",
    error: null,
  });
  assert.deepEqual(selectCountryLoadStateByCode(store.getState(), "EE"), {
    forecastError: "Request failed for /data/EE/forecast.json with 404",
    status: "error",
    error: "Request failed for /data/EE/normalized_series.json with 404",
  });
  assert.deepEqual(selectCountryModelByCode(store.getState(), "LT")?.forecast, {
    country_code: "LT",
    status: "ready",
    rows: [],
  });
  assert.equal(
    selectCountryModelByCode(store.getState(), "EE")?.forecastLoadError,
    "Request failed for /data/EE/forecast.json with 404",
  );
  assert.equal(
    selectAppRenderState(store.getState()).countryModels[1]?.loadError,
    "Request failed for /data/EE/normalized_series.json with 404",
  );
  assert.equal(selectSelectedCountryCode(store.getState()), "LT");
  assert.equal(selectSelectedCountryModel(store.getState())?.countryCode, "LT");
});

test("countries payload refresh resets previously staged country payloads and load state", () => {
  const store = createAppStore();

  store.dispatch(
    countriesPayloadReceived({
      contract_version: "ccoutline_site.v1",
      active_country_codes: ["LT", "EE"],
      countries: [
        { country_code: "LT", display_name: "Lithuania" },
        { country_code: "EE", display_name: "Estonia" },
      ],
    }),
  );
  store.dispatch(
    countryPayloadLoadFinished({
      countryCode: "LT",
      countryEntry: {
        country_code: "LT",
        display_name: "Lithuania",
      },
      forecast: {
        country_code: "LT",
        status: "ready",
        rows: [],
      },
      forecastLoadError: null,
      loadError: null,
      normalizedSeries: {
        country_code: "LT",
      },
    }),
  );

  store.dispatch(
    countriesPayloadReceived({
      contract_version: "ccoutline_site.v1",
      active_country_codes: ["LV"],
      countries: [{ country_code: "LV", display_name: "Latvia" }],
    }),
  );

  assert.deepEqual(
    selectOrderedCountryEntries(store.getState()).map((entry) => entry.country_code),
    ["LV"],
  );
  assert.equal(selectCountryLoadStateByCode(store.getState(), "LT"), null);
  assert.equal(selectCountryModels(store.getState()).length, 1);
  assert.equal(selectCountryModelByCode(store.getState(), "LT")?.normalizedSeries, null);
  assert.equal(selectCountryModelByCode(store.getState(), "LT")?.forecast, null);
  assert.equal(selectCountryModelByCode(store.getState(), "LV")?.loadStatus, "idle");
});

test("root bootstrap failure clears staged payload state and exposes the error through render selectors", () => {
  const store = createAppStore();

  store.dispatch(
    countriesPayloadReceived({
      contract_version: "ccoutline_site.v1",
      active_country_codes: ["LT"],
      countries: [{ country_code: "LT", display_name: "Lithuania" }],
    }),
  );
  store.dispatch(
    countryPayloadLoadFinished({
      countryCode: "LT",
      countryEntry: {
        country_code: "LT",
        display_name: "Lithuania",
      },
      forecast: {
        country_code: "LT",
        status: "ready",
        rows: [],
      },
      forecastLoadError: null,
      loadError: null,
      normalizedSeries: {
        country_code: "LT",
      },
    }),
  );

  store.dispatch(countriesStateReset());
  store.dispatch(appBootstrapFailed("Unable to load countries.json"));

  assert.equal(selectBootstrapStatus(store.getState()), "error");
  assert.deepEqual(selectCountryModels(store.getState()), []);
  assert.equal(selectAppRenderState(store.getState()).countriesError, "Unable to load countries.json");
});

test("app render selectors stay memoized for unchanged state and track bootstrap lifecycle", () => {
  const store = createAppStore();

  store.dispatch(appBootstrapFailed("Temporary bootstrap failure"));
  const firstRenderState = selectAppRenderState(store.getState());
  const secondRenderState = selectAppRenderState(store.getState());

  assert.equal(firstRenderState, secondRenderState);
  assert.equal(firstRenderState.countriesError, "Temporary bootstrap failure");

  store.dispatch(appBootstrapStarted());
  store.dispatch(appBootstrapSucceeded());

  const readyRenderState = selectAppRenderState(store.getState());
  assert.equal(selectBootstrapStatus(store.getState()), "ready");
  assert.equal(readyRenderState.countriesError, null);
});
