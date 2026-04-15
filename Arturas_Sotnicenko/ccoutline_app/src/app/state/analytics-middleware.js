import {
  analyticsControlsReset,
  analyticsGlobalControlsUpdated,
  analyticsIndicatorOverrideControlsUpdated,
  analyticsIndicatorOverrideToggled,
} from "./analytics-slice.js";
import { consentAccepted, consentDeclined } from "./consent-slice.js";
import { uiDisclosureToggled, uiSelectedCountrySet } from "./ui-slice.js";
import { analyticsLegalLinkClicked, analyticsPageViewed } from "../analytics/tracking-actions.js";
import { selectConsentDecision, selectSelectedCountryCode } from "./selectors.js";

export function createAnalyticsMiddleware({ analyticsTracker }) {
  return (storeApi) => (next) => (action) => {
    const previousState = storeApi.getState();
    const result = next(action);
    const nextState = storeApi.getState();

    syncConsentState(analyticsTracker, previousState, nextState);

    if (selectConsentDecision(nextState) !== "accepted") {
      return result;
    }

    const trackedEvent = buildTrackedEvent(action, previousState, nextState);
    if (trackedEvent) {
      analyticsTracker.trackEvent(trackedEvent.name, trackedEvent.params);
    }

    return result;
  };
}

function syncConsentState(analyticsTracker, previousState, nextState) {
  const previousDecision = selectConsentDecision(previousState);
  const nextDecision = selectConsentDecision(nextState);
  if (previousDecision === nextDecision) {
    return;
  }

  analyticsTracker.syncConsentDecision(nextDecision);
  if (nextDecision === "accepted") {
    analyticsTracker.enable();
  }
}

function buildTrackedEvent(action, previousState, nextState) {
  if (action.type === analyticsPageViewed.type) {
    return {
      name: "page_view",
      params: {
        page_location: readCurrentLocation(),
        page_path: readCurrentPathname(),
        page_title: readCurrentPageTitle(),
        trigger: normalizeString(action.payload?.trigger) || "unknown",
      },
    };
  }

  if (action.type === uiSelectedCountrySet.type) {
    const selectedCountryCode = selectSelectedCountryCode(nextState);
    if (!selectedCountryCode) {
      return null;
    }

    return {
      name: "country_selected",
      params: {
        country_code: selectedCountryCode,
        selection_source: normalizeString(action.payload?.source) || "unknown",
        page_path: readCurrentPathname(),
      },
    };
  }

  if (action.type === uiDisclosureToggled.type) {
    const disclosureId = normalizeString(action.payload?.disclosureId || action.payload);
    if (!disclosureId) {
      return null;
    }

    return {
      name: "ui_disclosure_toggled",
      params: {
        disclosure_id: disclosureId,
        is_open: Boolean(nextState?.ui?.disclosuresById?.[disclosureId]),
        page_path: readCurrentPathname(),
      },
    };
  }

  if (action.type === analyticsControlsReset.type) {
    return {
      name: "analytics_controls_reset",
      params: {
        country_code: normalizeString(action.payload?.countryCode || action.payload),
        page_path: readCurrentPathname(),
      },
    };
  }

  if (action.type === analyticsGlobalControlsUpdated.type) {
    return {
      name: "analytics_global_control_updated",
      params: {
        country_code: normalizeString(action.payload?.countryCode),
        control_names: serializeControlNames(action.payload?.updates),
        page_path: readCurrentPathname(),
        ...serializePrimitiveUpdateValues(action.payload?.updates),
      },
    };
  }

  if (action.type === analyticsIndicatorOverrideToggled.type) {
    return {
      name: "analytics_indicator_override_toggled",
      params: {
        country_code: normalizeString(action.payload?.countryCode),
        indicator_id: normalizeString(action.payload?.indicatorId),
        enabled: action.payload?.enabled === true,
        page_path: readCurrentPathname(),
      },
    };
  }

  if (action.type === analyticsIndicatorOverrideControlsUpdated.type) {
    return {
      name: "analytics_indicator_override_control_updated",
      params: {
        country_code: normalizeString(action.payload?.countryCode),
        indicator_id: normalizeString(action.payload?.indicatorId),
        control_names: serializeControlNames(action.payload?.updates),
        page_path: readCurrentPathname(),
        ...serializePrimitiveUpdateValues(action.payload?.updates),
      },
    };
  }

  if (action.type === consentAccepted.type || action.type === consentDeclined.type) {
    return {
      name: "analytics_consent_updated",
      params: {
        decision: action.type === consentAccepted.type ? "accepted" : "declined",
        surface: normalizeString(action.payload?.surface) || "unknown",
        page_path: readCurrentPathname(),
      },
    };
  }

  if (action.type === analyticsLegalLinkClicked.type) {
    return {
      name: "legal_link_clicked",
      params: {
        link_key: normalizeString(action.payload?.linkKey),
        href: normalizeString(action.payload?.href),
        placement: normalizeString(action.payload?.placement) || "unknown",
        page_path: normalizeString(action.payload?.currentPathname) || readCurrentPathname(),
      },
    };
  }

  return null;
}

function serializeControlNames(updates) {
  return Object.keys(updates || {})
    .filter((key) => normalizeString(key))
    .sort()
    .join(",");
}

function serializePrimitiveUpdateValues(updates) {
  const serializedEntries = Object.entries(updates || {})
    .filter(([, value]) => typeof value === "string" || typeof value === "number" || typeof value === "boolean")
    .map(([key, value]) => [`update_${normalizeString(key)}`, value])
    .filter(([key]) => key !== "update_");

  return Object.fromEntries(serializedEntries);
}

function normalizeString(value) {
  return typeof value === "string" ? value.trim() : "";
}

function readCurrentPathname() {
  return normalizeString(globalThis.window?.location?.pathname) || "/";
}

function readCurrentLocation() {
  return normalizeString(globalThis.window?.location?.href);
}

function readCurrentPageTitle() {
  return normalizeString(globalThis.document?.title) || "CCOUTLINE";
}
