import test from "node:test";
import assert from "node:assert/strict";

import { analyticsLegalLinkClicked, analyticsPageViewed } from "../src/app/analytics/tracking-actions.js";
import {
  analyticsCountryStateHydrated,
  analyticsGlobalControlsUpdated,
} from "../src/app/state/analytics-slice.js";
import { consentAccepted, consentDeclined, consentStateHydrated } from "../src/app/state/consent-slice.js";
import { createAppStore } from "../src/app/state/store.js";
import { uiSelectedCountrySet } from "../src/app/state/ui-slice.js";

function createStubTracker() {
  return {
    enableCalls: 0,
    syncConsentCalls: [],
    trackedEvents: [],
    enable() {
      this.enableCalls += 1;
      return true;
    },
    syncConsentDecision(decision) {
      this.syncConsentCalls.push(decision);
      return true;
    },
    trackEvent(name, params) {
      this.trackedEvents.push({ name, params });
      return true;
    },
  };
}

function createCountryModel() {
  return {
    countryCode: "LT",
    countryEntry: {
      country_code: "LT",
      display_name: "Lithuania",
    },
    normalizedSeries: {
      country_code: "LT",
      normalization: {
        mode: "static_baseline",
        baseline_start_year: 2020,
        limit_to_baseline_window: true,
        min_obs_for_zscore: 3,
        rolling_window_years: 10,
        exclude_current_from_window: true,
        indicator_overrides: [],
      },
      indicators: [],
    },
    forecast: {
      country_code: "LT",
      status: "ready",
      rows: [],
    },
    loadError: null,
    forecastLoadError: null,
  };
}

test("analytics middleware gates events by consent and maps Redux plus legal-link actions to GA-friendly payloads", () => {
  const analyticsTracker = createStubTracker();
  const store = createAppStore({ analyticsTracker });

  store.dispatch(uiSelectedCountrySet({ countryCode: "LT", source: "country_button" }));
  assert.deepEqual(analyticsTracker.trackedEvents, []);

  store.dispatch(consentStateHydrated({ decision: null, updatedAt: null }));
  store.dispatch(consentAccepted({ surface: "banner", updatedAt: "2026-04-12T19:00:00.000Z" }));

  assert.deepEqual(analyticsTracker.syncConsentCalls, ["accepted"]);
  assert.equal(analyticsTracker.enableCalls, 1);
  assert.deepEqual(analyticsTracker.trackedEvents[0], {
    name: "analytics_consent_updated",
    params: {
      decision: "accepted",
      page_path: "/",
      surface: "banner",
    },
  });

  store.dispatch(uiSelectedCountrySet({ countryCode: "LT", source: "country_button" }));
  store.dispatch(analyticsCountryStateHydrated(createCountryModel()));
  store.dispatch(
    analyticsGlobalControlsUpdated({
      countryCode: "LT",
      updates: {
        mode: "rolling_trailing",
        rollingWindowYears: 8,
      },
    }),
  );
  store.dispatch(
    analyticsLegalLinkClicked({
      currentPathname: "/",
      href: "/privacy/",
      linkKey: "privacy",
      placement: "site_footer",
    }),
  );

  assert.deepEqual(analyticsTracker.trackedEvents[1], {
    name: "country_selected",
    params: {
      country_code: "LT",
      page_path: "/",
      selection_source: "country_button",
    },
  });
  assert.deepEqual(analyticsTracker.trackedEvents[2], {
    name: "analytics_global_control_updated",
    params: {
      control_names: "mode,rollingWindowYears",
      country_code: "LT",
      page_path: "/",
      update_mode: "rolling_trailing",
      update_rollingWindowYears: 8,
    },
  });
  assert.deepEqual(analyticsTracker.trackedEvents[3], {
    name: "legal_link_clicked",
    params: {
      href: "/privacy/",
      link_key: "privacy",
      page_path: "/",
      placement: "site_footer",
    },
  });

  store.dispatch(consentDeclined({ surface: "manage_cookies_page", updatedAt: "2026-04-12T19:01:00.000Z" }));
  assert.deepEqual(analyticsTracker.syncConsentCalls, ["accepted", "declined"]);
  assert.equal(analyticsTracker.trackedEvents.length, 4);
});

test("analytics middleware maps explicit page-view actions into GA page_view payloads after accepted consent", () => {
  const previousWindow = globalThis.window;
  const previousDocument = globalThis.document;

  globalThis.window = {
    location: {
      href: "https://ccoutline.test/manage-cookies/",
      pathname: "/manage-cookies/",
    },
  };
  globalThis.document = {
    title: "Manage Cookies | CCOUTLINE",
  };

  try {
    const analyticsTracker = createStubTracker();
    const store = createAppStore({ analyticsTracker });

    store.dispatch(consentStateHydrated({ decision: "accepted", updatedAt: "2026-04-12T19:05:00.000Z" }));
    store.dispatch(analyticsPageViewed({ trigger: "initial_load" }));

    assert.deepEqual(analyticsTracker.syncConsentCalls, ["accepted"]);
    assert.equal(analyticsTracker.enableCalls, 1);
    assert.deepEqual(analyticsTracker.trackedEvents[0], {
      name: "page_view",
      params: {
        page_location: "https://ccoutline.test/manage-cookies/",
        page_path: "/manage-cookies/",
        page_title: "Manage Cookies | CCOUTLINE",
        trigger: "initial_load",
      },
    });
  } finally {
    globalThis.window = previousWindow;
    globalThis.document = previousDocument;
  }
});
