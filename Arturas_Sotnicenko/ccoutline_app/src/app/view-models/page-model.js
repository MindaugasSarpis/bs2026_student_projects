import { normalizeCountryCode } from "../shared/formatters.js";

export function createEmptyCountriesPayload() {
  return {
    contract_version: "ccoutline_site.v1",
    active_country_codes: [],
    countries: [],
  };
}

export function orderedCountryEntries(appState) {
  const countries = Array.isArray(appState.countriesPayload?.countries)
    ? appState.countriesPayload.countries.filter((entry) => entry && typeof entry === "object")
    : [];

  const entryByCode = new Map(
    countries
      .map((entry) => [normalizeCountryCode(entry.country_code), entry])
      .filter(([countryCode]) => Boolean(countryCode)),
  );

  const orderedCodes = supportedCountryCodes(appState);
  const orderedEntries = [];

  for (const countryCode of orderedCodes) {
    const entry = entryByCode.get(countryCode);
    if (entry) {
      orderedEntries.push(entry);
    }
  }

  for (const entry of countries) {
    const countryCode = normalizeCountryCode(entry.country_code);
    if (countryCode && !orderedCodes.includes(countryCode)) {
      orderedEntries.push(entry);
    }
  }

  return orderedEntries;
}

export function summarizeCountryCoverage(appState) {
  const entries = orderedCountryEntries(appState);
  const names = entries
    .map((entry) => String(entry?.display_name || normalizeCountryCode(entry?.country_code) || "").trim())
    .filter((name) => Boolean(name));

  return names.length ? names.join(", ") : supportedCountryCodes(appState).join(", ");
}

export function supportedCountryCodes(appState) {
  return Array.isArray(appState.countriesPayload?.active_country_codes)
    ? appState.countriesPayload.active_country_codes
        .map((countryCode) => normalizeCountryCode(countryCode))
        .filter((countryCode) => Boolean(countryCode))
    : [];
}
