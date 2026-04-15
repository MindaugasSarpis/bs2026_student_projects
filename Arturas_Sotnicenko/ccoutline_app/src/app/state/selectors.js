import { createSelector } from "@reduxjs/toolkit";

import { createCountryAnalyticsState } from "../analytics/recompute.js";
import { createEmptyCountriesPayload, orderedCountryEntries } from "../view-models/page-model.js";
import {
  buildIndicatorDisclosureKey,
  createAnalyticsDisclosureId,
  createCountrySectionDisclosureId,
  createIndicatorDisclosureId,
  createIndicatorRawDataDisclosureId,
} from "./ui-disclosure-keys.js";

const EMPTY_COUNTRIES_PAYLOAD = createEmptyCountriesPayload();
const EMPTY_COUNTRY_MODELS = Object.freeze([]);

export const selectAppState = (state) => state?.app || null;
export const selectAnalyticsState = (state) => state?.analytics || null;
export const selectConsentState = (state) => state?.consent || null;
export const selectCountriesState = (state) => state?.countries || null;
export const selectUiState = (state) => state?.ui || null;

export const selectBootstrapStatus = createSelector([selectAppState], (appState) => appState?.bootstrapStatus || "idle");

export const selectRootLoadError = createSelector([selectAppState], (appState) => {
  return typeof appState?.rootLoadError === "string" && appState.rootLoadError.trim().length > 0
    ? appState.rootLoadError
    : null;
});

export const selectCountriesPayload = createSelector([selectCountriesState], (countriesState) => {
  return countriesState?.countriesPayload || EMPTY_COUNTRIES_PAYLOAD;
});

export const selectOrderedCountryEntries = createSelector([selectCountriesPayload], (countriesPayload) => {
  return orderedCountryEntries({ countriesPayload });
});

export function selectCountryEntryByCode(state, countryCode) {
  const normalizedCountryCode = typeof countryCode === "string" ? countryCode.trim().toUpperCase() : "";
  if (!normalizedCountryCode) {
    return null;
  }

  return selectCountriesState(state)?.countryEntriesByCode?.[normalizedCountryCode] || null;
}

export function selectCountryLoadStateByCode(state, countryCode) {
  const normalizedCountryCode = typeof countryCode === "string" ? countryCode.trim().toUpperCase() : "";
  if (!normalizedCountryCode) {
    return null;
  }

  return selectCountriesState(state)?.countryLoadByCode?.[normalizedCountryCode] || null;
}

export function selectCountryAnalyticsControlsStateByCode(state, countryCode) {
  const normalizedCountryCode = typeof countryCode === "string" ? countryCode.trim().toUpperCase() : "";
  if (!normalizedCountryCode) {
    return null;
  }

  return selectAnalyticsState(state)?.controlsByCountry?.[normalizedCountryCode] || null;
}

export function selectDisclosureOpenById(state, disclosureId) {
  return Boolean(selectUiState(state)?.disclosuresById?.[disclosureId]);
}

export const selectSelectedCountryCode = createSelector([selectUiState], (uiState) => {
  const selectedCountryCode = typeof uiState?.selectedCountryCode === "string" ? uiState.selectedCountryCode : "";
  return selectedCountryCode || null;
});

export const selectConsentDecision = createSelector([selectConsentState], (consentState) => {
  return consentState?.decision === "accepted" || consentState?.decision === "declined" ? consentState.decision : null;
});

export const selectIsConsentHydrated = createSelector([selectConsentState], (consentState) => {
  return consentState?.hydrated === true;
});

export const selectCountryModels = createSelector([selectCountriesState], (countriesState) => {
  if (!countriesState) {
    return EMPTY_COUNTRY_MODELS;
  }

  const countryOrder = Array.isArray(countriesState.countryOrder) ? countriesState.countryOrder : EMPTY_COUNTRY_MODELS;
  const countryEntriesByCode =
    countriesState.countryEntriesByCode && typeof countriesState.countryEntriesByCode === "object"
      ? countriesState.countryEntriesByCode
      : {};
  const forecastByCode =
    countriesState.forecastByCode && typeof countriesState.forecastByCode === "object"
      ? countriesState.forecastByCode
      : {};
  const normalizedSeriesByCode =
    countriesState.normalizedSeriesByCode && typeof countriesState.normalizedSeriesByCode === "object"
      ? countriesState.normalizedSeriesByCode
      : {};
  const countryLoadByCode =
    countriesState.countryLoadByCode && typeof countriesState.countryLoadByCode === "object"
      ? countriesState.countryLoadByCode
      : {};

  return countryOrder.map((countryCode) =>
    buildCountryModel({
      countryCode,
      countryEntry: countryEntriesByCode[countryCode] || null,
      forecast: forecastByCode[countryCode] || null,
      normalizedSeries: normalizedSeriesByCode[countryCode] || null,
      loadState: countryLoadByCode[countryCode] || null,
    }),
  );
});

export function selectCountryModelByCode(state, countryCode) {
  const normalizedCountryCode = typeof countryCode === "string" ? countryCode.trim().toUpperCase() : "";
  if (!normalizedCountryCode) {
    return null;
  }

  const countriesState = selectCountriesState(state);
  const countryEntriesByCode =
    countriesState?.countryEntriesByCode && typeof countriesState.countryEntriesByCode === "object"
      ? countriesState.countryEntriesByCode
      : {};
  const forecastByCode =
    countriesState?.forecastByCode && typeof countriesState.forecastByCode === "object"
      ? countriesState.forecastByCode
      : {};
  const normalizedSeriesByCode =
    countriesState?.normalizedSeriesByCode && typeof countriesState.normalizedSeriesByCode === "object"
      ? countriesState.normalizedSeriesByCode
      : {};
  const countryLoadByCode =
    countriesState?.countryLoadByCode && typeof countriesState.countryLoadByCode === "object"
      ? countriesState.countryLoadByCode
      : {};

  return buildCountryModel({
    countryCode: normalizedCountryCode,
    countryEntry: countryEntriesByCode[normalizedCountryCode] || null,
    forecast: forecastByCode[normalizedCountryCode] || null,
    normalizedSeries: normalizedSeriesByCode[normalizedCountryCode] || null,
    loadState: countryLoadByCode[normalizedCountryCode] || null,
  });
}

export const selectSelectedCountryModel = createSelector(
  [selectCountryModels, selectSelectedCountryCode],
  (countryModels, selectedCountryCode) => {
    if (!selectedCountryCode) {
      return null;
    }

    return countryModels.find((model) => model.countryCode === selectedCountryCode) || null;
  },
);

export const selectAppRenderState = createSelector(
  [selectRootLoadError, selectCountriesPayload, selectCountryModels, selectConsentState],
  (rootLoadError, countriesPayload, countryModels, consentState) => ({
    countriesError: rootLoadError,
    consentState: consentState || {
      decision: null,
      hydrated: false,
      updatedAt: null,
    },
    countriesPayload,
    countryModels,
  }),
);

export function createSelectCountryAnalyticsState() {
  return createSelector(
    [
      (state, countryCode) => {
        const normalizedCountryCode = typeof countryCode === "string" ? countryCode.trim().toUpperCase() : "";
        return normalizedCountryCode ? selectCountriesState(state)?.normalizedSeriesByCode?.[normalizedCountryCode] || null : null;
      },
      (state, countryCode) => selectCountryAnalyticsControlsStateByCode(state, countryCode),
    ],
    (normalizedSeries, controlsState) => {
      if (!normalizedSeries) {
        return null;
      }

      return createCountryAnalyticsState(normalizedSeries, controlsState);
    },
  );
}

export function createSelectCountryUiState() {
  return createSelector(
    [
      (_state, countryCode) => (typeof countryCode === "string" ? countryCode.trim().toUpperCase() : ""),
      (state, countryCode) => {
        const normalizedCountryCode = typeof countryCode === "string" ? countryCode.trim().toUpperCase() : "";
        return normalizedCountryCode ? selectCountriesState(state)?.normalizedSeriesByCode?.[normalizedCountryCode] || null : null;
      },
      (state) => selectUiState(state)?.disclosuresById || {},
    ],
    (countryCode, normalizedSeries, disclosuresById) => {
      if (!countryCode) {
        return null;
      }

      const indicators = Array.isArray(normalizedSeries?.indicators) ? normalizedSeries.indicators : [];
      const indicatorDisclosures = {};

      indicators.forEach((indicator, index) => {
        const indicatorKey = buildIndicatorDisclosureKey(indicator?.indicator_id, index);
        const disclosureId = createIndicatorDisclosureId(countryCode, indicatorKey);
        const rawDataDisclosureId = createIndicatorRawDataDisclosureId(countryCode, indicatorKey);
        indicatorDisclosures[indicatorKey] = {
          disclosureId,
          open: readDisclosureState(disclosuresById, disclosureId, false),
          rawDataDisclosureId,
          rawDataOpen: readDisclosureState(disclosuresById, rawDataDisclosureId, false),
        };
      });

      const glossaryDisclosureId = createCountrySectionDisclosureId(countryCode, "glossary");
      const analyticsDisclosureId = createCountrySectionDisclosureId(countryCode, "analytics");
      const forecastDisclosureId = createCountrySectionDisclosureId(countryCode, "forecast");
      const chartsDisclosureId = createCountrySectionDisclosureId(countryCode, "charts");
      const analyticsSummaryDisclosureId = createAnalyticsDisclosureId(countryCode, "summary");
      const analyticsOverridesDisclosureId = createAnalyticsDisclosureId(countryCode, "overrides");
      const analyticsRawTableDisclosureId = createAnalyticsDisclosureId(countryCode, "raw-table");

      return {
        countrySections: {
          glossary: {
            disclosureId: glossaryDisclosureId,
            open: readDisclosureState(disclosuresById, glossaryDisclosureId, false),
          },
          analytics: {
            disclosureId: analyticsDisclosureId,
            open: readDisclosureState(disclosuresById, analyticsDisclosureId, false),
          },
          forecast: {
            disclosureId: forecastDisclosureId,
            open: readDisclosureState(disclosuresById, forecastDisclosureId, false),
          },
          charts: {
            disclosureId: chartsDisclosureId,
            open: readDisclosureState(disclosuresById, chartsDisclosureId, false),
          },
        },
        analyticsSections: {
          summary: {
            disclosureId: analyticsSummaryDisclosureId,
            open: readDisclosureState(disclosuresById, analyticsSummaryDisclosureId, false),
          },
          overrides: {
            disclosureId: analyticsOverridesDisclosureId,
            open: readDisclosureState(disclosuresById, analyticsOverridesDisclosureId, false),
          },
          rawTable: {
            disclosureId: analyticsRawTableDisclosureId,
            open: readDisclosureState(disclosuresById, analyticsRawTableDisclosureId, false),
          },
        },
        indicatorDisclosures,
      };
    },
  );
}

function buildCountryModel({ countryCode, countryEntry, forecast, normalizedSeries, loadState }) {
  return {
    countryCode,
    countryEntry,
    forecast,
    forecastLoadError: typeof loadState?.forecastError === "string" ? loadState.forecastError : null,
    normalizedSeries,
    loadError: typeof loadState?.error === "string" ? loadState.error : null,
    loadStatus: typeof loadState?.status === "string" ? loadState.status : "idle",
  };
}

function readDisclosureState(disclosuresById, disclosureId, defaultOpen) {
  return disclosureId in disclosuresById ? Boolean(disclosuresById[disclosureId]) : defaultOpen;
}
