import test from "node:test";
import assert from "node:assert/strict";

import { countriesPayloadReceived, countryPayloadLoadFinished } from "../src/app/state/countries-slice.js";
import { createSelectCountryUiState, selectSelectedCountryCode } from "../src/app/state/selectors.js";
import { createAppStore } from "../src/app/state/store.js";
import { uiCountryStateHydrated, uiDisclosureToggled, uiSelectedCountrySet, uiStateReset } from "../src/app/state/ui-slice.js";

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
      indicators: [
        { indicator_id: "inflation" },
        { indicator_id: "gdp" },
      ],
    },
  };
}

test("ui slice hydrates collapsed country disclosure defaults while keeping nested and indicator sections collapsed", () => {
  const store = createAppStore();
  const selectCountryUiState = createSelectCountryUiState();
  const countryModel = buildCountryModel();

  store.dispatch(
    countriesPayloadReceived({
      contract_version: "ccoutline_site.v1",
      active_country_codes: ["LT"],
      countries: [countryModel.countryEntry],
    }),
  );
  store.dispatch(countryPayloadLoadFinished(countryModel));
  store.dispatch(uiCountryStateHydrated(countryModel));

  const uiState = selectCountryUiState(store.getState(), "LT");

  assert.equal(uiState.countrySections.glossary.open, false);
  assert.equal(uiState.countrySections.analytics.open, false);
  assert.equal(uiState.countrySections.forecast.open, false);
  assert.equal(uiState.countrySections.charts.open, false);
  assert.equal(uiState.analyticsSections.summary.open, false);
  assert.equal(uiState.analyticsSections.overrides.open, false);
  assert.equal(uiState.analyticsSections.rawTable.open, false);
  assert.equal(uiState.indicatorDisclosures.inflation.open, false);
  assert.equal(uiState.indicatorDisclosures.inflation.rawDataOpen, false);
});

test("ui slice toggles disclosure state without losing other country-local defaults", () => {
  const store = createAppStore();
  const selectCountryUiState = createSelectCountryUiState();
  const countryModel = buildCountryModel();

  store.dispatch(
    countriesPayloadReceived({
      contract_version: "ccoutline_site.v1",
      active_country_codes: ["LT"],
      countries: [countryModel.countryEntry],
    }),
  );
  store.dispatch(countryPayloadLoadFinished(countryModel));
  store.dispatch(uiCountryStateHydrated(countryModel));

  const initialUiState = selectCountryUiState(store.getState(), "LT");
  store.dispatch(uiDisclosureToggled(initialUiState.analyticsSections.summary.disclosureId));
  store.dispatch(uiDisclosureToggled(initialUiState.indicatorDisclosures.inflation.disclosureId));
  store.dispatch(uiDisclosureToggled(initialUiState.indicatorDisclosures.inflation.rawDataDisclosureId));

  const toggledUiState = selectCountryUiState(store.getState(), "LT");

  assert.equal(toggledUiState.analyticsSections.summary.open, true);
  assert.equal(toggledUiState.indicatorDisclosures.inflation.open, true);
  assert.equal(toggledUiState.indicatorDisclosures.inflation.rawDataOpen, true);
  assert.equal(toggledUiState.countrySections.glossary.open, false);
  assert.equal(toggledUiState.indicatorDisclosures.gdp.open, false);
});

test("ui slice stores the selected country independently from disclosure state", () => {
  const store = createAppStore();
  const selectCountryUiState = createSelectCountryUiState();
  const countryModel = buildCountryModel();

  store.dispatch(
    countriesPayloadReceived({
      contract_version: "ccoutline_site.v1",
      active_country_codes: ["LT"],
      countries: [countryModel.countryEntry],
    }),
  );
  store.dispatch(countryPayloadLoadFinished(countryModel));
  store.dispatch(uiCountryStateHydrated(countryModel));

  const initialUiState = selectCountryUiState(store.getState(), "LT");

  store.dispatch(uiSelectedCountrySet({ countryCode: "lt" }));
  store.dispatch(uiDisclosureToggled(initialUiState.countrySections.glossary.disclosureId));

  assert.equal(selectSelectedCountryCode(store.getState()), "LT");
  assert.equal(selectCountryUiState(store.getState(), "LT").countrySections.glossary.open, true);
});

test("ui slice clears the selected country on blank input without disturbing disclosure state", () => {
  const store = createAppStore();
  const selectCountryUiState = createSelectCountryUiState();
  const countryModel = buildCountryModel();

  store.dispatch(
    countriesPayloadReceived({
      contract_version: "ccoutline_site.v1",
      active_country_codes: ["LT"],
      countries: [countryModel.countryEntry],
    }),
  );
  store.dispatch(countryPayloadLoadFinished(countryModel));
  store.dispatch(uiCountryStateHydrated(countryModel));

  const initialUiState = selectCountryUiState(store.getState(), "LT");
  store.dispatch(uiDisclosureToggled(initialUiState.countrySections.glossary.disclosureId));
  store.dispatch(uiSelectedCountrySet({ countryCode: "LT" }));
  store.dispatch(uiSelectedCountrySet({ countryCode: "   " }));

  assert.equal(selectSelectedCountryCode(store.getState()), null);
  assert.equal(selectCountryUiState(store.getState(), "LT").countrySections.glossary.open, true);
});

test("country ui selector memoizes stable output and invalidates on disclosure toggle", () => {
  const store = createAppStore();
  const selectCountryUiState = createSelectCountryUiState();
  const countryModel = buildCountryModel();

  store.dispatch(
    countriesPayloadReceived({
      contract_version: "ccoutline_site.v1",
      active_country_codes: ["LT"],
      countries: [countryModel.countryEntry],
    }),
  );
  store.dispatch(countryPayloadLoadFinished(countryModel));
  store.dispatch(uiCountryStateHydrated(countryModel));

  const firstUiState = selectCountryUiState(store.getState(), "LT");
  const secondUiState = selectCountryUiState(store.getState(), "LT");

  assert.equal(firstUiState, secondUiState);

  store.dispatch(uiDisclosureToggled(firstUiState.countrySections.glossary.disclosureId));

  const toggledUiState = selectCountryUiState(store.getState(), "LT");
  assert.notEqual(toggledUiState, firstUiState);
  assert.equal(toggledUiState.countrySections.glossary.open, true);
});

test("ui state reset clears disclosure persistence until hydration runs again", () => {
  const store = createAppStore();
  const selectCountryUiState = createSelectCountryUiState();
  const countryModel = buildCountryModel();

  store.dispatch(
    countriesPayloadReceived({
      contract_version: "ccoutline_site.v1",
      active_country_codes: ["LT"],
      countries: [countryModel.countryEntry],
    }),
  );
  store.dispatch(countryPayloadLoadFinished(countryModel));
  store.dispatch(uiCountryStateHydrated(countryModel));

  const initialUiState = selectCountryUiState(store.getState(), "LT");
  store.dispatch(uiDisclosureToggled(initialUiState.countrySections.glossary.disclosureId));
  store.dispatch(uiSelectedCountrySet({ countryCode: "LT" }));
  store.dispatch(uiStateReset());

  assert.equal(selectCountryUiState(store.getState(), "LT").countrySections.glossary.open, false);
  assert.equal(selectSelectedCountryCode(store.getState()), null);
});
