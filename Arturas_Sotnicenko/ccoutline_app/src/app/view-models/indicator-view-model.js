export function createIndicatorViewModels(indicators) {
  const safeIndicators = Array.isArray(indicators) ? indicators : [];

  return safeIndicators
    .filter((indicator) => indicator && typeof indicator === "object")
    .map((indicator) => createIndicatorViewModel(indicator));
}

export function createIndicatorViewModel(indicator) {
  const points = Array.isArray(indicator?.points)
    ? indicator.points.filter((point) => point && typeof point === "object")
    : [];
  const plottedPoints = points.filter((point) => Number.isFinite(point?.year) && Number.isFinite(point?.value));

  const indicatorId = indicator?.indicator_id || "";
  const indicatorLabel = indicator?.indicator_label || indicator?.indicator_name || indicatorId || "";
  const sourceLabel = indicator?.source_label || indicator?.source_name || indicator?.source_id || "";
  const title = indicator?.indicator_source_label || indicatorLabel || indicatorId || "Indicator";
  const hasPoints = points.length > 0;
  const hasRenderableChart = plottedPoints.length >= 2;
  const summaryItems = buildSummaryItems({
    sourceLabel,
    unit: indicator?.unit || "n/a",
    observationCount: indicator?.observation_count ?? 0,
    yearRange: indicator?.year_range || null,
  });

  return {
    indicatorId,
    indicatorLabel,
    sourceLabel,
    unit: indicator?.unit || "n/a",
    observationCount: indicator?.observation_count ?? 0,
    yearRange: indicator?.year_range || null,
    title,
    rawIndicator: indicator,
    points,
    plottedPoints,
    rawPointCount: points.length,
    plottedPointCount: plottedPoints.length,
    hasPoints,
    hasRenderableChart,
    summaryItems,
    summaryText: summaryItems.join(" • "),
    missingDataMessage: buildMissingDataMessage({ hasPoints, plottedPoints, points }),
    chartAvailabilityMessage: buildChartAvailabilityMessage({ hasPoints, plottedPoints, points }),
  };
}

function buildSummaryItems({ sourceLabel, unit, observationCount, yearRange }) {
  const items = [];

  if (sourceLabel) {
    items.push(sourceLabel);
  }

  items.push(unit || "n/a");
  items.push(`${observationCount} obs`);

  if (yearRange?.min_year && yearRange?.max_year) {
    items.push(
      yearRange.min_year === yearRange.max_year
        ? String(yearRange.min_year)
        : `${yearRange.min_year}-${yearRange.max_year}`,
    );
  } else {
    items.push("Range unavailable");
  }

  return items;
}

function buildMissingDataMessage({ hasPoints, plottedPoints, points }) {
  if (!hasPoints) {
    return "No points were exported for this indicator.";
  }

  if (!plottedPoints.length) {
    return "Points were exported for this indicator, but none include both a year and a numeric value yet.";
  }

  if (plottedPoints.length < points.length) {
    return "Some exported rows are incomplete and are omitted from chart rendering.";
  }

  return "";
}

function buildChartAvailabilityMessage({ hasPoints, plottedPoints, points }) {
  if (!hasPoints) {
    return "No chart is shown because this indicator has no exported yearly points yet.";
  }

  if (!plottedPoints.length) {
    return "No chart is shown because the exported rows do not yet include plottable year-and-value pairs.";
  }

  if (plottedPoints.length === 1) {
    return "No chart is shown yet because only one complete yearly point is available.";
  }

  if (plottedPoints.length < points.length) {
    return "The chart uses only the complete exported rows that include both a year and a numeric value.";
  }

  return "";
}
