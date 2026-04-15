import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import shp from "shpjs";

const NATURAL_EARTH_50M_COUNTRIES_URL =
  "https://naturalearth.s3.amazonaws.com/50m_cultural/ne_50m_admin_0_countries.zip";

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const APP_DIR = path.resolve(SCRIPT_DIR, "..");
const OUTPUT_FILE = path.resolve(APP_DIR, "src/app/globe/world-countries.geojson");

async function main() {
  // Source: Natural Earth Admin 0 - Countries 1:50m. Keep the runtime seam
  // local by regenerating the committed GeoJSON asset from the official zip.
  const sourceArchive = await downloadSourceArchive(NATURAL_EARTH_50M_COUNTRIES_URL);
  const sourceGeoJson = await shp(sourceArchive);
  const normalizedFeatureCollection = normalizeFeatureCollection(sourceGeoJson);

  await mkdir(path.dirname(OUTPUT_FILE), { recursive: true });
  await writeFile(OUTPUT_FILE, `${JSON.stringify(normalizedFeatureCollection, null, 2)}\n`, "utf8");

  console.log(
    `Wrote ${normalizedFeatureCollection.features.length} globe features to ${path.relative(APP_DIR, OUTPUT_FILE)}`,
  );
}

async function downloadSourceArchive(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to download Natural Earth countries archive: ${response.status} ${response.statusText}`);
  }

  return Buffer.from(await response.arrayBuffer());
}

function normalizeFeatureCollection(sourceGeoJson) {
  const sourceFeatures = Array.isArray(sourceGeoJson?.features) ? sourceGeoJson.features : [];

  return {
    type: "FeatureCollection",
    features: sourceFeatures
      .filter((feature) => feature && typeof feature === "object" && feature.geometry)
      .map(normalizeFeature)
      .sort(compareNormalizedFeatures),
  };
}

function normalizeFeature(feature) {
  const properties = feature?.properties || {};
  const countryCode = resolveCountryCode(properties);
  const displayName = resolveDisplayName(properties);
  const normalizedProperties = {
    display_name: displayName,
  };

  if (countryCode) {
    normalizedProperties.country_code = countryCode;
  }

  return {
    type: "Feature",
    properties: normalizedProperties,
    geometry: feature.geometry,
  };
}

function resolveCountryCode(properties) {
  const countryCode = normalizeTwoLetterCode(properties?.ISO_A2_EH);
  return countryCode || null;
}

function resolveDisplayName(properties) {
  const displayNameCandidates = [properties?.NAME_EN, properties?.NAME, properties?.ADMIN, properties?.NAME_LONG];

  for (const value of displayNameCandidates) {
    if (typeof value === "string" && value.trim().length > 0) {
      return value.trim();
    }
  }

  return "Country";
}

function normalizeTwoLetterCode(value) {
  if (typeof value !== "string") {
    return "";
  }

  const normalized = value.trim().toUpperCase();
  return /^[A-Z]{2}$/.test(normalized) ? normalized : "";
}

function compareNormalizedFeatures(left, right) {
  const leftName = String(left?.properties?.display_name || "");
  const rightName = String(right?.properties?.display_name || "");
  const leftCountryCode = String(left?.properties?.country_code || "");
  const rightCountryCode = String(right?.properties?.country_code || "");
  const displayNameComparison = leftName.localeCompare(rightName);

  if (displayNameComparison !== 0) {
    return displayNameComparison;
  }

  return leftCountryCode.localeCompare(rightCountryCode);
}

await main();
