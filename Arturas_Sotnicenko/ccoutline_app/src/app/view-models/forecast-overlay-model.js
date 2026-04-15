export function findCompatibleForecastOverlay({ indicatorViewModel, forecast }) {
  const indicatorId = String(indicatorViewModel?.indicatorId || "").trim();
  const indicatorUnit = normalizeToken(indicatorViewModel?.unit);
  const plottedPoints = Array.isArray(indicatorViewModel?.plottedPoints)
    ? indicatorViewModel.plottedPoints.filter((point) => Number.isFinite(point?.year) && Number.isFinite(point?.value))
    : [];
  const lastPlottedPoint = plottedPoints.length ? plottedPoints[plottedPoints.length - 1] : null;
  const lastPlottedYear = lastPlottedPoint?.year;
  const rows = Array.isArray(forecast?.rows) ? forecast.rows.filter((row) => row && typeof row === "object") : [];

  if (!indicatorId || !indicatorUnit || !Number.isFinite(lastPlottedYear) || !rows.length) {
    return null;
  }

  const compatibleRow = rows.find((row) => {
    const rowIndicatorId = String(row?.indicator_id || row?.target_indicator_id || "").trim();
    const forecastYear = row?.forecast_year;
    const forecastValue = row?.forecast_value;
    const forecastUnit = normalizeToken(row?.forecast_unit);
    const transformMethod = resolveForecastTransformMethod(row);

    return (
      rowIndicatorId === indicatorId &&
      Number.isFinite(forecastYear) &&
      Number.isFinite(forecastValue) &&
      forecastYear > lastPlottedYear &&
      forecastUnit === indicatorUnit &&
      transformMethod === "none"
    );
  });

  if (!compatibleRow) {
    return null;
  }

  return {
    forecastYear: compatibleRow.forecast_year,
    forecastValue: compatibleRow.forecast_value,
    forecastUnit: String(compatibleRow.forecast_unit || "").trim(),
    indicatorId,
    indicatorLabel: String(
      compatibleRow?.indicator_label || compatibleRow?.target_indicator_name || compatibleRow?.indicator_name || indicatorId,
    ).trim(),
    selectedCandidate: String(compatibleRow?.selected_candidate || "").trim(),
    transformMethod: "none",
  };
}

export function findForecastChartDisclosure({ indicatorViewModel, forecast }) {
  const indicatorId = String(indicatorViewModel?.indicatorId || "").trim();
  const indicatorUnit = normalizeToken(indicatorViewModel?.unit);
  const plottedPoints = Array.isArray(indicatorViewModel?.plottedPoints)
    ? indicatorViewModel.plottedPoints.filter((point) => Number.isFinite(point?.year) && Number.isFinite(point?.value))
    : [];
  const lastPlottedPoint = plottedPoints.length ? plottedPoints[plottedPoints.length - 1] : null;
  const lastPlottedYear = lastPlottedPoint?.year;
  const rows = Array.isArray(forecast?.rows) ? forecast.rows.filter((row) => row && typeof row === "object") : [];

  if (!indicatorId || !indicatorUnit || !Number.isFinite(lastPlottedYear) || !rows.length) {
    return null;
  }

  const matchingRow = rows.find((row) => {
    const rowIndicatorId = String(row?.indicator_id || row?.target_indicator_id || "").trim();
    const forecastYear = row?.forecast_year;
    const forecastValue = row?.forecast_value;
    const forecastUnit = normalizeToken(row?.forecast_unit);
    const transformMethod = resolveForecastTransformMethod(row);

    return (
      rowIndicatorId === indicatorId &&
      Number.isFinite(forecastYear) &&
      Number.isFinite(forecastValue) &&
      forecastYear > lastPlottedYear &&
      (transformMethod !== "none" || forecastUnit !== indicatorUnit)
    );
  });

  if (!matchingRow) {
    return null;
  }

  const transformMethod = resolveForecastTransformMethod(matchingRow);
  const forecastUnit = String(matchingRow?.forecast_unit || "").trim();
  const reason =
    transformMethod && transformMethod !== "none"
      ? describeTransformedForecastUnits(transformMethod)
      : "reported in units that do not match the raw chart units";

  return {
    indicatorId,
    indicatorLabel: String(
      matchingRow?.indicator_label || matchingRow?.target_indicator_name || matchingRow?.indicator_name || indicatorId,
    ).trim(),
    forecastYear: matchingRow.forecast_year,
    forecastUnit,
    transformMethod,
    message: `CCOutline forecast available in Forecast section and not plotted here because it is ${reason}.`,
  };
}

function resolveForecastTransformMethod(row) {
  const exportedMethod = normalizeToken(row?.transform_method);
  if (exportedMethod) {
    return exportedMethod;
  }

  return parseForecastTransformMethod(row?.selected_candidate);
}

function parseForecastTransformMethod(selectedCandidate) {
  const candidateKey = String(selectedCandidate || "").trim();
  if (!candidateKey.includes("__")) {
    return "";
  }

  const parts = candidateKey.split("__");
  return normalizeToken(parts.length >= 2 ? parts[1] : "");
}

function describeTransformedForecastUnits(transformMethod) {
  switch (normalizeToken(transformMethod)) {
    case "pct_change_yoy":
    case "log_diff_yoy":
      return "shown as a yearly change rather than in the chart's raw units";
    case "pp_change_lag1":
      return "shown as a percentage-point change rather than in the chart's raw units";
    default:
      return "shown in transformed units rather than in the chart's raw units";
  }
}

function normalizeToken(value) {
  return typeof value === "string" ? value.trim().toLowerCase() : "";
}
