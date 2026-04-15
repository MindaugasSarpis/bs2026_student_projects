import { createSlice } from "@reduxjs/toolkit";

import {
  createCountryAnalyticsControlsState,
  resetCountryAnalyticsControlsState,
  setCountryAnalyticsIndicatorOverrideState,
  updateCountryAnalyticsGlobalControlsState,
  updateCountryAnalyticsIndicatorOverrideControlsState,
} from "../analytics/recompute.js";
import { normalizeCountryCode } from "../shared/formatters.js";

const initialState = Object.freeze({
  controlsByCountry: {},
});

const analyticsSlice = createSlice({
  name: "analytics",
  initialState,
  reducers: {
    analyticsStateReset() {
      return initialState;
    },
    analyticsCountryStateHydrated(state, action) {
      const model = action.payload;
      const countryCode = normalizeCountryCode(model?.countryCode);
      if (!countryCode) {
        return;
      }

      if (model?.normalizedSeries && !model?.loadError) {
        state.controlsByCountry[countryCode] = createCountryAnalyticsControlsState(model.normalizedSeries);
        return;
      }

      delete state.controlsByCountry[countryCode];
    },
    analyticsGlobalControlsUpdated(state, action) {
      const countryCode = normalizeCountryCode(action.payload?.countryCode);
      if (!countryCode || !state.controlsByCountry[countryCode]) {
        return;
      }

      state.controlsByCountry[countryCode] = updateCountryAnalyticsGlobalControlsState(
        state.controlsByCountry[countryCode],
        action.payload?.updates,
      );
    },
    analyticsIndicatorOverrideToggled(state, action) {
      const countryCode = normalizeCountryCode(action.payload?.countryCode);
      if (!countryCode || !state.controlsByCountry[countryCode]) {
        return;
      }

      state.controlsByCountry[countryCode] = setCountryAnalyticsIndicatorOverrideState(
        state.controlsByCountry[countryCode],
        action.payload?.indicatorId,
        action.payload?.enabled === true,
      );
    },
    analyticsIndicatorOverrideControlsUpdated(state, action) {
      const countryCode = normalizeCountryCode(action.payload?.countryCode);
      if (!countryCode || !state.controlsByCountry[countryCode]) {
        return;
      }

      state.controlsByCountry[countryCode] = updateCountryAnalyticsIndicatorOverrideControlsState(
        state.controlsByCountry[countryCode],
        action.payload?.indicatorId,
        action.payload?.updates,
      );
    },
    analyticsControlsReset(state, action) {
      const countryCode = normalizeCountryCode(action.payload?.countryCode || action.payload);
      if (!countryCode || !state.controlsByCountry[countryCode]) {
        return;
      }

      state.controlsByCountry[countryCode] = resetCountryAnalyticsControlsState(state.controlsByCountry[countryCode]);
    },
  },
});

export const {
  analyticsControlsReset,
  analyticsCountryStateHydrated,
  analyticsGlobalControlsUpdated,
  analyticsIndicatorOverrideControlsUpdated,
  analyticsIndicatorOverrideToggled,
  analyticsStateReset,
} = analyticsSlice.actions;
export const analyticsReducer = analyticsSlice.reducer;
