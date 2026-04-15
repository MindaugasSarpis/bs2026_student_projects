import { createSlice } from "@reduxjs/toolkit";

const initialState = Object.freeze({
  decision: null,
  hydrated: false,
  updatedAt: null,
});

const consentSlice = createSlice({
  name: "consent",
  initialState,
  reducers: {
    consentStateReset() {
      return initialState;
    },
    consentStateHydrated(_state, action) {
      return buildConsentState({
        decision: action.payload?.decision,
        hydrated: true,
        updatedAt: action.payload?.updatedAt,
      });
    },
    consentAccepted(_state, action) {
      return buildConsentState({
        decision: "accepted",
        hydrated: true,
        updatedAt: action.payload?.updatedAt,
      });
    },
    consentDeclined(_state, action) {
      return buildConsentState({
        decision: "declined",
        hydrated: true,
        updatedAt: action.payload?.updatedAt,
      });
    },
  },
});

export const { consentAccepted, consentDeclined, consentStateHydrated, consentStateReset } = consentSlice.actions;
export const consentReducer = consentSlice.reducer;

function buildConsentState({ decision, hydrated, updatedAt }) {
  return {
    decision: normalizeDecision(decision),
    hydrated: hydrated === true,
    updatedAt: normalizeUpdatedAt(updatedAt),
  };
}

function normalizeDecision(value) {
  if (value === "accepted" || value === "declined") {
    return value;
  }

  return null;
}

function normalizeUpdatedAt(value) {
  return typeof value === "string" && value.trim().length > 0 ? value.trim() : null;
}

