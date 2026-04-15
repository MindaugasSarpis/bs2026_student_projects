import test from "node:test";
import assert from "node:assert/strict";

import {
  analyticsControlsReset,
  analyticsCountryStateHydrated,
  analyticsGlobalControlsUpdated,
  analyticsIndicatorOverrideControlsUpdated,
  analyticsIndicatorOverrideToggled,
  analyticsStateReset,
} from "../src/app/state/analytics-slice.js";
import { countriesPayloadReceived, countryPayloadLoadFinished } from "../src/app/state/countries-slice.js";
import {
  createSelectCountryAnalyticsState,
  selectCountryAnalyticsControlsStateByCode,
} from "../src/app/state/selectors.js";
import { createAppStore } from "../src/app/state/store.js";

function buildCountryModel() {
  return {
    countryCode: "LT",
    countryEntry: {
      country_code: "LT",
      display_name: "Lithuania",
    },
    loadError: null,
    normalizedSeries: {
      country_code: "LT",
      display_name: "Lithuania",
      normalization: {
        mode: "static_baseline",
        baseline_start_year: 2020,
        limit_to_baseline_window: true,
        min_obs_for_zscore: 3,
        rolling_window_years: 10,
        exclude_current_from_window: true,
        summary_text: "Static baseline from 2020, min obs 3",
        indicator_overrides: [],
      },
      indicators: [
        {
          indicator_id: "inflation",
          indicator_label: "Inflation",
          points: [
            { year: 2020, value: 2, zscore: null, status: "ok", is_projection: false },
            { year: 2021, value: 4, zscore: null, status: "ok", is_projection: false },
            { year: 2022, value: 6, zscore: null, status: "ok", is_projection: false },
            { year: 2023, value: 8, zscore: null, status: "ok", is_projection: false },
          ],
        },
      ],
    },
  };
}

test("analytics slice hydrates controls from country payloads and selectors derive analytics state", () => {
  const store = createAppStore();
  const selectCountryAnalyticsState = createSelectCountryAnalyticsState();
  const countryModel = buildCountryModel();

  store.dispatch(
    countriesPayloadReceived({
      contract_version: "ccoutline_site.v1",
      active_country_codes: ["LT"],
      countries: [countryModel.countryEntry],
    }),
  );
  store.dispatch(countryPayloadLoadFinished(countryModel));
  store.dispatch(analyticsCountryStateHydrated(countryModel));

  const controlsState = selectCountryAnalyticsControlsStateByCode(store.getState(), "LT");
  const analyticsState = selectCountryAnalyticsState(store.getState(), "LT");

  assert.equal(controlsState.globalControls.mode, "rolling_trailing");
  assert.equal(controlsState.globalControls.rollingWindowYears, 10);
  assert.equal(controlsState.globalControls.minObsForZscore, 3);
  assert.equal(analyticsState.rawTable.renderableRowCount, 1);
  assert.equal(analyticsState.controls.hasChanges, true);
  assert.equal(analyticsState.defaultSummaryText, "Rolling trailing, 10y, exclude current, min obs 3");
});

test("analytics slice actions update selector-derived country analytics state and reset back to export defaults", () => {
  const store = createAppStore();
  const selectCountryAnalyticsState = createSelectCountryAnalyticsState();
  const countryModel = buildCountryModel();

  store.dispatch(
    countriesPayloadReceived({
      contract_version: "ccoutline_site.v1",
      active_country_codes: ["LT"],
      countries: [countryModel.countryEntry],
    }),
  );
  store.dispatch(countryPayloadLoadFinished(countryModel));
  store.dispatch(analyticsCountryStateHydrated(countryModel));

  store.dispatch(
    analyticsGlobalControlsUpdated({
      countryCode: "LT",
      updates: {
        mode: "rolling_trailing",
        rollingWindowYears: 2,
        minObsForZscore: 2,
      },
    }),
  );
  store.dispatch(
    analyticsIndicatorOverrideToggled({
      countryCode: "LT",
      indicatorId: "inflation",
      enabled: true,
    }),
  );
  store.dispatch(
    analyticsIndicatorOverrideControlsUpdated({
      countryCode: "LT",
      indicatorId: "inflation",
      updates: {
        rollingWindowYears: 3,
      },
    }),
  );

  let analyticsState = selectCountryAnalyticsState(store.getState(), "LT");

  assert.equal(analyticsState.controls.hasChanges, true);
  assert.equal(analyticsState.controls.global.values.mode, "rolling_trailing");
  assert.equal(analyticsState.controls.indicatorOverrides[0].hasActiveOverride, true);
  assert.equal(analyticsState.controls.indicatorOverrides[0].currentValues.rollingWindowYears, 3);

  store.dispatch(analyticsControlsReset({ countryCode: "LT" }));
  analyticsState = selectCountryAnalyticsState(store.getState(), "LT");

  assert.equal(analyticsState.controls.hasChanges, false);
  assert.equal(analyticsState.controls.global.values.mode, "static_baseline");
  assert.equal(analyticsState.controls.indicatorOverrides[0].hasActiveOverride, false);
});

test("country analytics selectors memoize stable results and invalidate when controls change", () => {
  const store = createAppStore();
  const selectCountryAnalyticsState = createSelectCountryAnalyticsState();
  const countryModel = buildCountryModel();

  store.dispatch(
    countriesPayloadReceived({
      contract_version: "ccoutline_site.v1",
      active_country_codes: ["LT"],
      countries: [countryModel.countryEntry],
    }),
  );
  store.dispatch(countryPayloadLoadFinished(countryModel));
  store.dispatch(analyticsCountryStateHydrated(countryModel));

  const firstAnalyticsState = selectCountryAnalyticsState(store.getState(), "LT");
  const secondAnalyticsState = selectCountryAnalyticsState(store.getState(), "LT");

  assert.equal(firstAnalyticsState, secondAnalyticsState);

  store.dispatch(
    analyticsGlobalControlsUpdated({
      countryCode: "LT",
      updates: {
        mode: "rolling_trailing",
      },
    }),
  );

  const updatedAnalyticsState = selectCountryAnalyticsState(store.getState(), "LT");
  assert.notEqual(updatedAnalyticsState, firstAnalyticsState);
  assert.equal(updatedAnalyticsState.controls.global.values.mode, "rolling_trailing");
});

test("analytics state reset clears hydrated per-country controls", () => {
  const store = createAppStore();
  const countryModel = buildCountryModel();

  store.dispatch(
    countriesPayloadReceived({
      contract_version: "ccoutline_site.v1",
      active_country_codes: ["LT"],
      countries: [countryModel.countryEntry],
    }),
  );
  store.dispatch(countryPayloadLoadFinished(countryModel));
  store.dispatch(analyticsCountryStateHydrated(countryModel));

  assert.ok(selectCountryAnalyticsControlsStateByCode(store.getState(), "LT"));

  store.dispatch(analyticsStateReset());

  assert.equal(selectCountryAnalyticsControlsStateByCode(store.getState(), "LT"), null);
});
