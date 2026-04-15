import { createSlice } from "@reduxjs/toolkit";

import { createEmptyCountriesPayload, orderedCountryEntries } from "../view-models/page-model.js";
import { normalizeCountryCode } from "../shared/formatters.js";

const EMPTY_COUNTRIES_PAYLOAD = createEmptyCountriesPayload();

const initialState = Object.freeze({
  countriesPayload: EMPTY_COUNTRIES_PAYLOAD,
  countryOrder: [],
  countryEntriesByCode: {},
  forecastByCode: {},
  normalizedSeriesByCode: {},
  countryLoadByCode: {},
});

const countriesSlice = createSlice({
  name: "countries",
  initialState,
  reducers: {
    countriesPayloadReceived(state, action) {
      state.countriesPayload = normalizeCountriesPayload(action.payload);
      state.countryOrder = [];
      state.countryEntriesByCode = {};
      state.forecastByCode = {};
      state.normalizedSeriesByCode = {};
      state.countryLoadByCode = {};

      for (const countryEntry of orderedCountryEntries({ countriesPayload: state.countriesPayload })) {
        const countryCode = normalizeCountryCode(countryEntry?.country_code);
        if (!countryCode) {
          continue;
        }

        state.countryOrder.push(countryCode);
        state.countryEntriesByCode[countryCode] = countryEntry;
        state.countryLoadByCode[countryCode] = {
          forecastError: null,
          status: "idle",
          error: null,
        };
      }
    },
    countryPayloadLoadStarted(state, action) {
      const countryCode = normalizeCountryCode(action.payload?.countryCode || action.payload);
      if (!countryCode) {
        return;
      }

      state.countryLoadByCode[countryCode] = {
        forecastError: null,
        status: "loading",
        error: null,
      };
    },
    countryPayloadLoadFinished(state, action) {
      const model = action.payload;
      const countryCode = normalizeCountryCode(model?.countryCode);
      if (!countryCode) {
        return;
      }

      if (!state.countryOrder.includes(countryCode)) {
        state.countryOrder.push(countryCode);
      }

      if (model?.countryEntry && typeof model.countryEntry === "object") {
        state.countryEntriesByCode[countryCode] = model.countryEntry;
      }

      if (model?.normalizedSeries && typeof model.normalizedSeries === "object") {
        state.normalizedSeriesByCode[countryCode] = model.normalizedSeries;
      } else {
        delete state.normalizedSeriesByCode[countryCode];
      }

      if (model?.forecast && typeof model.forecast === "object") {
        state.forecastByCode[countryCode] = model.forecast;
      } else {
        delete state.forecastByCode[countryCode];
      }

      state.countryLoadByCode[countryCode] = {
        forecastError: normalizeLoadError(model?.forecastLoadError),
        status: model?.loadError ? "error" : "ready",
        error: normalizeLoadError(model?.loadError),
      };
    },
    countriesStateReset() {
      return initialState;
    },
  },
});

export const {
  countriesPayloadReceived,
  countriesStateReset,
  countryPayloadLoadFinished,
  countryPayloadLoadStarted,
} = countriesSlice.actions;
export const countriesReducer = countriesSlice.reducer;

function normalizeCountriesPayload(value) {
  return value && typeof value === "object" ? value : EMPTY_COUNTRIES_PAYLOAD;
}

function normalizeLoadError(value) {
  return typeof value === "string" && value.trim().length > 0 ? value.trim() : null;
}
