const ANALYTICS_PROVIDER = "ga4_via_gtag";
const CONSENT_STORAGE_KEY_VERSION = "v1";

function createFrozenConfig() {
  const ga4 = Object.freeze({
    accountResource: "accounts/389778361",
    accountId: "389778361",
    propertyResource: "properties/531253273",
    propertyId: "531253273",
    webStreamResource: "properties/531253273/dataStreams/14356295354",
    webStreamId: "14356295354",
    measurementId: "G-VWEM25PMN0",
  });

  const consent = Object.freeze({
    storageKeyVersion: CONSENT_STORAGE_KEY_VERSION,
    decisionStorageKey: `ccoutline.analytics.consent.decision.${CONSENT_STORAGE_KEY_VERSION}`,
    updatedAtStorageKey: `ccoutline.analytics.consent.updated_at.${CONSENT_STORAGE_KEY_VERSION}`,
  });

  return Object.freeze({
    provider: ANALYTICS_PROVIDER,
    ga4,
    consent,
  });
}

export const ANALYTICS_RUNTIME_CONFIG = createFrozenConfig();

export function getAnalyticsRuntimeConfig() {
  return ANALYTICS_RUNTIME_CONFIG;
}

