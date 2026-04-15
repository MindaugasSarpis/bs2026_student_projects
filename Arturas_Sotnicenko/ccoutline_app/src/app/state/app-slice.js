import { createSlice } from "@reduxjs/toolkit";

const initialState = Object.freeze({
  bootstrapStatus: "idle",
  rootLoadError: null,
});

const appSlice = createSlice({
  name: "app",
  initialState,
  reducers: {
    appBootstrapStarted(state) {
      state.bootstrapStatus = "loading";
      state.rootLoadError = null;
    },
    appBootstrapSucceeded(state) {
      state.bootstrapStatus = "ready";
      state.rootLoadError = null;
    },
    appBootstrapFailed(state, action) {
      state.bootstrapStatus = "error";
      state.rootLoadError = normalizeErrorMessage(action.payload);
    },
  },
});

export const { appBootstrapFailed, appBootstrapStarted, appBootstrapSucceeded } = appSlice.actions;
export const appReducer = appSlice.reducer;

function normalizeErrorMessage(value) {
  if (typeof value === "string" && value.trim().length > 0) {
    return value.trim();
  }
  return "Unexpected application failure.";
}
