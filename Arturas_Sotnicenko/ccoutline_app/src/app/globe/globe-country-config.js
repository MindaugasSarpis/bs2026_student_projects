import { normalizeCountryCode } from "../shared/formatters.js";

export const GLOBE_WORLD_GEOMETRY_PATH = "/app/globe/world-countries.geojson";

// Natural Earth 50m country geometry, regenerated locally with
// `npm run refresh:globe-geometry` and normalized to the runtime country-code
// and display-name contract used by the globe renderer.
export const GLOBE_SUPPORTED_COUNTRIES = Object.freeze([
  Object.freeze({
    countryCode: "LT",
    label: "Lithuania",
    geometryCountryCode: "LT",
  }),
  Object.freeze({
    countryCode: "LV",
    label: "Latvia",
    geometryCountryCode: "LV",
  }),
  Object.freeze({
    countryCode: "EE",
    label: "Estonia",
    geometryCountryCode: "EE",
  }),
  Object.freeze({
    countryCode: "DK",
    label: "Denmark",
    geometryCountryCode: "DK",
  }),
]);

export const GLOBE_FIXED_VIEW = Object.freeze({
  center: Object.freeze([18, 57.5]),
  rotation: Object.freeze([-18, -57.5, 0]),
  precision: 0.25,
});

const SUPPORTED_COUNTRY_BY_CODE = new Map(
  GLOBE_SUPPORTED_COUNTRIES.map((entry) => [entry.countryCode, entry]),
);
const SUPPORTED_COUNTRY_BY_GEOMETRY_CODE = new Map(
  GLOBE_SUPPORTED_COUNTRIES.map((entry) => [entry.geometryCountryCode, entry]),
);

export function getSupportedGlobeCountry(countryCode) {
  return SUPPORTED_COUNTRY_BY_CODE.get(normalizeCountryCode(countryCode)) || null;
}

export function resolveGlobeFeatureCountryCode(feature) {
  const propertyCountryCode = normalizeCountryCode(feature?.properties?.country_code);
  if (propertyCountryCode) {
    return propertyCountryCode;
  }

  return normalizeCountryCode(feature?.id);
}

export function getSupportedGlobeCountryForFeature(feature) {
  const featureCountryCode = resolveGlobeFeatureCountryCode(feature);
  if (!featureCountryCode) {
    return null;
  }

  return SUPPORTED_COUNTRY_BY_GEOMETRY_CODE.get(featureCountryCode) || null;
}

export function isSupportedGlobeCountryCode(countryCode) {
  return Boolean(getSupportedGlobeCountry(countryCode));
}

export function isSelectableGlobeFeature(feature) {
  return Boolean(getSupportedGlobeCountryForFeature(feature));
}
