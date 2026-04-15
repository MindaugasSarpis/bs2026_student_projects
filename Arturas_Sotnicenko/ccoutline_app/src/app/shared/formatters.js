export function normalizeCountryCode(value) {
  const normalized = String(value || "").trim().toUpperCase();
  return normalized || "";
}

export function buildCountryAnchor(countryCode) {
  return `country-${String(countryCode || "").trim().toLowerCase()}`;
}

export function formatYearRange(yearRange) {
  const minYear = yearRange?.min_year;
  const maxYear = yearRange?.max_year;
  if (Number.isFinite(minYear) && Number.isFinite(maxYear)) {
    return minYear === maxYear ? String(minYear) : `${minYear}-${maxYear}`;
  }
  return "Range unavailable";
}

export function deriveYearRangeFromIndicatorPoints(indicators) {
  const safeIndicators = Array.isArray(indicators) ? indicators : [];
  const yearValues = [];

  for (const indicator of safeIndicators) {
    const points = Array.isArray(indicator?.points) ? indicator.points : [];
    for (const point of points) {
      if (Number.isFinite(point?.year)) {
        yearValues.push(point.year);
      }
    }
  }

  if (!yearValues.length) {
    return null;
  }

  return {
    min_year: Math.min(...yearValues),
    max_year: Math.max(...yearValues),
  };
}

export function resolveCountrySummaryYearRange(normalizedSeries) {
  const topLevelRange = normalizeFiniteYearRange(normalizedSeries?.year_range);
  const pointDerivedRange = deriveYearRangeFromIndicatorPoints(normalizedSeries?.indicators);

  if (topLevelRange && pointDerivedRange) {
    return areYearRangesEqual(topLevelRange, pointDerivedRange) ? topLevelRange : pointDerivedRange;
  }

  return topLevelRange || pointDerivedRange || null;
}

function normalizeFiniteYearRange(yearRange) {
  const minYear = yearRange?.min_year;
  const maxYear = yearRange?.max_year;
  if (!Number.isFinite(minYear) || !Number.isFinite(maxYear)) {
    return null;
  }
  return {
    min_year: minYear,
    max_year: maxYear,
  };
}

function areYearRangesEqual(left, right) {
  return left.min_year === right.min_year && left.max_year === right.max_year;
}

export function formatProjectionFlag(value) {
  if (value === true) {
    return "yes";
  }
  if (value === false) {
    return "no";
  }
  return "";
}

export function formatScalar(value) {
  if (value === null || value === undefined || value === "") {
    return "";
  }
  if (typeof value === "number" && Number.isFinite(value)) {
    return new Intl.NumberFormat("en-US", {
      maximumFractionDigits: 3,
    }).format(value);
  }
  return String(value);
}
