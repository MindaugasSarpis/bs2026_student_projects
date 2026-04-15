import { normalizeCountryCode } from "../shared/formatters.js";
import { GLOBE_WORLD_GEOMETRY_PATH } from "../globe/globe-country-config.js";

export async function fetchCountriesPayload() {
  return fetchJson("/data/countries.json");
}

export async function fetchGlobeWorldGeometry() {
  return fetchJson(GLOBE_WORLD_GEOMETRY_PATH);
}

export async function fetchCountryModel(countryEntry) {
  const countryCode = normalizeCountryCode(countryEntry.country_code);
  const normalizedSeriesPayloadPath = countryEntry?.payloads?.normalized_series;
  const forecastPayloadPath = countryEntry?.payloads?.forecast;

  if (!countryCode) {
    return {
      countryCode: "",
      countryEntry,
      loadError: "Country entry is missing a country code.",
      forecast: null,
      forecastLoadError: null,
      normalizedSeries: null,
    };
  }

  if (!normalizedSeriesPayloadPath || typeof normalizedSeriesPayloadPath !== "string") {
    return {
      countryCode,
      countryEntry,
      loadError: `normalized_series payload path is missing for ${countryCode}.`,
      forecast: null,
      forecastLoadError: null,
      normalizedSeries: null,
    };
  }

  try {
    const normalizedSeries = await fetchJson(`/data/${normalizedSeriesPayloadPath}`);
    const { forecast, forecastLoadError } = await fetchForecastPayload({
      countryCode,
      forecastPayloadPath,
    });

    return {
      countryCode,
      countryEntry,
      forecast,
      forecastLoadError,
      loadError: null,
      normalizedSeries,
    };
  } catch (error) {
    return {
      countryCode,
      countryEntry,
      forecast: null,
      forecastLoadError: null,
      loadError: error instanceof Error ? error.message : `Unable to load normalized_series for ${countryCode}.`,
      normalizedSeries: null,
    };
  }
}

async function fetchForecastPayload({ countryCode, forecastPayloadPath }) {
  if (!forecastPayloadPath || typeof forecastPayloadPath !== "string") {
    return {
      forecast: null,
      forecastLoadError: `forecast payload path is missing for ${countryCode}.`,
    };
  }

  try {
    return {
      forecast: await fetchJson(`/data/${forecastPayloadPath}`),
      forecastLoadError: null,
    };
  } catch (error) {
    return {
      forecast: null,
      forecastLoadError:
        error instanceof Error ? error.message : `Unable to load forecast for ${countryCode}.`,
    };
  }
}

async function fetchJson(pathname) {
  const response = await fetch(pathname, { headers: { Accept: "application/json" } });
  if (!response.ok) {
    throw new Error(`Request failed for ${pathname} with ${response.status}`);
  }
  return response.json();
}
