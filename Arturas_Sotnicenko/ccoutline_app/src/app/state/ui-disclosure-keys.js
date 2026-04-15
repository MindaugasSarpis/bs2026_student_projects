import { normalizeCountryCode } from "../shared/formatters.js";

export function createCountrySectionDisclosureId(countryCode, sectionKey) {
  return `${normalizeCountryCode(countryCode)}::country-section::${normalizeDisclosureKey(sectionKey)}`;
}

export function createAnalyticsDisclosureId(countryCode, sectionKey) {
  return `${normalizeCountryCode(countryCode)}::analytics-section::${normalizeDisclosureKey(sectionKey)}`;
}

export function createIndicatorDisclosureId(countryCode, indicatorKey) {
  return `${normalizeCountryCode(countryCode)}::indicator::${normalizeDisclosureKey(indicatorKey)}`;
}

export function createIndicatorRawDataDisclosureId(countryCode, indicatorKey) {
  return `${normalizeCountryCode(countryCode)}::indicator-raw-data::${normalizeDisclosureKey(indicatorKey)}`;
}

export function buildIndicatorDisclosureKey(indicatorId, index = 0) {
  const safeIndicatorId = normalizeDisclosureKey(indicatorId);
  return safeIndicatorId || `indicator-${index}`;
}

export function buildCountryDisclosureDefaults({ countryCode, normalizedSeries }) {
  const safeCountryCode = normalizeCountryCode(countryCode);
  if (!safeCountryCode) {
    return {};
  }

  const disclosures = {
    [createCountrySectionDisclosureId(safeCountryCode, "glossary")]: false,
    [createCountrySectionDisclosureId(safeCountryCode, "analytics")]: false,
    [createCountrySectionDisclosureId(safeCountryCode, "forecast")]: false,
    [createCountrySectionDisclosureId(safeCountryCode, "charts")]: false,
    [createAnalyticsDisclosureId(safeCountryCode, "summary")]: false,
    [createAnalyticsDisclosureId(safeCountryCode, "overrides")]: false,
    [createAnalyticsDisclosureId(safeCountryCode, "raw-table")]: false,
  };

  const indicators = Array.isArray(normalizedSeries?.indicators) ? normalizedSeries.indicators : [];
  indicators.forEach((indicator, index) => {
    const indicatorKey = buildIndicatorDisclosureKey(indicator?.indicator_id, index);
    disclosures[createIndicatorDisclosureId(safeCountryCode, indicatorKey)] = false;
    disclosures[createIndicatorRawDataDisclosureId(safeCountryCode, indicatorKey)] = false;
  });

  return disclosures;
}

function normalizeDisclosureKey(value) {
  return typeof value === "string" ? value.trim().toLowerCase() : "";
}
