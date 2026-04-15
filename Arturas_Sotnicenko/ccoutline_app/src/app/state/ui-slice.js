import { createSlice } from "@reduxjs/toolkit";

import { buildCountryDisclosureDefaults } from "./ui-disclosure-keys.js";
import { normalizeCountryCode } from "../shared/formatters.js";

const initialState = Object.freeze({
  disclosuresById: {},
  selectedCountryCode: null,
});

const uiSlice = createSlice({
  name: "ui",
  initialState,
  reducers: {
    uiStateReset() {
      return initialState;
    },
    uiCountryStateHydrated(state, action) {
      const model = action.payload;
      const countryCode = normalizeCountryCode(model?.countryCode);
      if (!countryCode || model?.loadError) {
        return;
      }

      const defaults = buildCountryDisclosureDefaults({
        countryCode,
        normalizedSeries: model?.normalizedSeries,
      });

      for (const [disclosureId, open] of Object.entries(defaults)) {
        if (!(disclosureId in state.disclosuresById)) {
          state.disclosuresById[disclosureId] = open;
        }
      }
    },
    uiDisclosureToggled(state, action) {
      const disclosureId = normalizeDisclosureId(action.payload?.disclosureId || action.payload);
      if (!disclosureId) {
        return;
      }

      state.disclosuresById[disclosureId] = !Boolean(state.disclosuresById[disclosureId]);
    },
    uiSelectedCountrySet(state, action) {
      const countryCode = normalizeCountryCode(action.payload?.countryCode || action.payload);
      state.selectedCountryCode = countryCode || null;
    },
  },
});

export const { uiCountryStateHydrated, uiDisclosureToggled, uiSelectedCountrySet, uiStateReset } = uiSlice.actions;
export const uiReducer = uiSlice.reducer;

function normalizeDisclosureId(value) {
  return typeof value === "string" ? value.trim() : "";
}
