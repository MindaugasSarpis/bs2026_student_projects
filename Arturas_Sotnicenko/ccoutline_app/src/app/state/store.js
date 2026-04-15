import { configureStore } from "@reduxjs/toolkit";

import { createGtagTracker } from "../analytics/gtag-tracker.js";
import { ANALYTICS_RUNTIME_CONFIG } from "../config/analytics-config.js";
import { analyticsReducer } from "./analytics-slice.js";
import { createAnalyticsMiddleware } from "./analytics-middleware.js";
import { appReducer } from "./app-slice.js";
import { consentReducer } from "./consent-slice.js";
import { countriesReducer } from "./countries-slice.js";
import { uiReducer } from "./ui-slice.js";

export function createAppStore({ preloadedState, analyticsConfig = ANALYTICS_RUNTIME_CONFIG, analyticsTracker } = {}) {
  const resolvedAnalyticsTracker =
    analyticsTracker ||
    createGtagTracker({
      analyticsConfig,
    });

  return configureStore({
    reducer: {
      analytics: analyticsReducer,
      app: appReducer,
      consent: consentReducer,
      countries: countriesReducer,
      ui: uiReducer,
    },
    preloadedState,
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware().concat(
        createAnalyticsMiddleware({
          analyticsTracker: resolvedAnalyticsTracker,
        }),
      ),
  });
}
