const DEFAULT_NORMALIZATION_POLICY = Object.freeze({
  mode: "static_baseline",
  baselineStartYear: 1999,
  limitToBaselineWindow: true,
  minObsForZscore: 3,
  rollingWindowYears: 10,
  excludeCurrentFromWindow: true,
});

const DEFAULT_GLOBAL_ANALYTICS_CONTROLS = Object.freeze({
  mode: "rolling_trailing",
  rollingWindowYears: 10,
  minObsForZscore: 3,
});

const NORMALIZATION_MODES = new Set(["static_baseline", "rolling_trailing"]);
const POLICY_FIELDS = Object.freeze([
  "mode",
  "baselineStartYear",
  "limitToBaselineWindow",
  "minObsForZscore",
  "rollingWindowYears",
  "excludeCurrentFromWindow",
]);
const VISIBLE_CONTROL_FIELDS = Object.freeze(["mode", "rollingWindowYears", "minObsForZscore"]);

export const ANALYTICS_CONTROL_BOUNDS = Object.freeze({
  rollingWindowYears: Object.freeze({ min: 2, max: 20 }),
  minObsForZscore: Object.freeze({ min: 2, max: 10 }),
});

const STATUS_LABELS = Object.freeze({
  ok: "OK",
  no_eligible_window: "No eligible window",
  insufficient_history: "Insufficient history",
  zero_variance: "Zero variance",
  insufficient_variance_or_obs: "Insufficient variance or observations",
});

const RAW_TABLE_COLUMNS = Object.freeze([
  Object.freeze({ key: "indicatorLabel", label: "Indicator" }),
  Object.freeze({ key: "year", label: "Year" }),
  Object.freeze({ key: "value", label: "Value" }),
  Object.freeze({ key: "recomputedZscore", label: "Recomputed z-score" }),
  Object.freeze({ key: "recomputedStatus", label: "Status" }),
  Object.freeze({ key: "normalizationObs", label: "Normalization obs" }),
  Object.freeze({ key: "policySummaryText", label: "Active policy" }),
  Object.freeze({ key: "policySourceLabel", label: "Policy source" }),
  Object.freeze({ key: "isProjection", label: "Projection" }),
]);

export function createCountryAnalyticsControlsState(normalizedSeries) {
  const context = buildAnalyticsContext(normalizedSeries);
  const exportGlobalControls = selectVisibleControls(context.exportCountryDefaultPolicy);
  const exportIndicatorOverrides = buildExportIndicatorVisibleOverrides(context);

  return {
    exportGlobalControls,
    globalControls: normalizeVisibleControls(DEFAULT_GLOBAL_ANALYTICS_CONTROLS, exportGlobalControls),
    exportIndicatorOverrides,
    indicatorOverrides: cloneVisibleControlLookup(exportIndicatorOverrides),
  };
}

export function updateCountryAnalyticsGlobalControlsState(controlsState, updates) {
  const safeState = normalizeControlsState(controlsState);
  return {
    ...safeState,
    globalControls: normalizeVisibleControls(
      {
        ...safeState.globalControls,
        ...updates,
      },
      safeState.exportGlobalControls,
    ),
  };
}

export function setCountryAnalyticsIndicatorOverrideState(controlsState, indicatorId, enabled) {
  const safeState = normalizeControlsState(controlsState);
  const normalizedIndicatorId = normalizeText(indicatorId);
  if (!normalizedIndicatorId) {
    return safeState;
  }

  const nextOverrides = cloneVisibleControlLookup(safeState.indicatorOverrides);
  if (enabled) {
    const exportOverride = safeState.exportIndicatorOverrides[normalizedIndicatorId];
    nextOverrides[normalizedIndicatorId] = normalizeVisibleControls(
      exportOverride || safeState.globalControls,
      safeState.exportGlobalControls,
    );
  } else {
    delete nextOverrides[normalizedIndicatorId];
  }

  return {
    ...safeState,
    indicatorOverrides: nextOverrides,
  };
}

export function updateCountryAnalyticsIndicatorOverrideControlsState(controlsState, indicatorId, updates) {
  const safeState = normalizeControlsState(controlsState);
  const normalizedIndicatorId = normalizeText(indicatorId);
  if (!normalizedIndicatorId) {
    return safeState;
  }

  const currentVisibleControls =
    safeState.indicatorOverrides[normalizedIndicatorId] ||
    safeState.exportIndicatorOverrides[normalizedIndicatorId] ||
    safeState.globalControls;
  const nextOverrides = cloneVisibleControlLookup(safeState.indicatorOverrides);
  nextOverrides[normalizedIndicatorId] = normalizeVisibleControls(
    {
      ...currentVisibleControls,
      ...updates,
    },
    safeState.exportGlobalControls,
  );

  return {
    ...safeState,
    indicatorOverrides: nextOverrides,
  };
}

export function resetCountryAnalyticsControlsState(controlsState) {
  const safeState = normalizeControlsState(controlsState);
  return {
    exportGlobalControls: { ...safeState.exportGlobalControls },
    globalControls: { ...safeState.exportGlobalControls },
    exportIndicatorOverrides: cloneVisibleControlLookup(safeState.exportIndicatorOverrides),
    indicatorOverrides: cloneVisibleControlLookup(safeState.exportIndicatorOverrides),
  };
}

export function createCountryAnalyticsState(normalizedSeries, controlsState = null) {
  const context = buildAnalyticsContext(normalizedSeries);
  const activeControlsState = controlsState || createCountryAnalyticsControlsState(normalizedSeries);
  const safeControlsState = normalizeControlsState(activeControlsState);
  const exportDefaultSummaryText = formatNormalizationPolicySummary(context.exportCountryDefaultPolicy);
  const activeCountryDefaultPolicy = applyVisibleControls(
    context.exportCountryDefaultPolicy,
    safeControlsState.globalControls,
  );

  const indicatorAnalytics = context.indicators.map((indicator) => {
    const indicatorId = normalizeText(indicator.indicator_id);
    const activeOverrideControls = indicatorId ? safeControlsState.indicatorOverrides[indicatorId] || null : null;
    const exportIndicatorPolicy = indicatorId
      ? context.exportIndicatorPolicies.get(indicatorId) || context.exportCountryDefaultPolicy
      : context.exportCountryDefaultPolicy;
    const effectivePolicy = activeOverrideControls
      ? applyVisibleControls(exportIndicatorPolicy, activeOverrideControls)
      : { ...activeCountryDefaultPolicy };
    const policySource = activeOverrideControls ? "indicator_override" : "country_default";
    const rows = recomputeIndicatorRows({
      indicator,
      policy: effectivePolicy,
      policySource,
    });

    return {
      indicatorId,
      indicatorLabel: normalizeText(indicator.indicator_label || indicator.indicator_name || indicatorId || "Indicator"),
      indicatorSourceLabel: normalizeText(
        indicator.indicator_source_label || indicator.indicator_label || indicator.indicator_name || indicatorId || "Indicator",
      ),
      policySource,
      effectivePolicy,
      policySummaryText: formatNormalizationPolicySummary(effectivePolicy),
      rowCount: rows.length,
      rows,
    };
  });

  const rawTableRows = indicatorAnalytics
    .flatMap((indicatorAnalyticsModel) => indicatorAnalyticsModel.rows)
    .sort((left, right) => {
      const labelComparison = left.indicatorLabel.localeCompare(right.indicatorLabel);
      if (labelComparison !== 0) {
        return labelComparison;
      }
      return Number(left.year) - Number(right.year);
    });
  const rawTable = buildRawTableModel(rawTableRows);
  const statusSummary = buildStatusSummary(rawTableRows);
  const sectionState = determineAnalyticsSectionState({
    rowCount: rawTable.rowCount,
    renderableRowCount: rawTable.renderableRowCount,
  });
  const rendering = buildAnalyticsRenderingModel({
    indicatorAnalytics,
    rawTableRows,
    sectionState,
    statusSummary,
  });

  const controls = buildControlsViewModel({
    context,
    controlsState: safeControlsState,
    activeCountryDefaultPolicy,
  });

  return {
    countryCode: normalizeText(context.safeSeries.country_code).toUpperCase(),
    displayName: normalizeText(context.safeSeries.display_name),
    exportDefaultPolicy: context.exportCountryDefaultPolicy,
    defaultPolicy: activeCountryDefaultPolicy,
    exportDefaultSummaryText,
    defaultSummaryText: formatNormalizationPolicySummary(activeCountryDefaultPolicy),
    overrideCount: controls.activeOverrideCount,
    indicatorCount: context.indicators.length,
    indicatorAnalytics,
    sectionState,
    statusSummary,
    rawTable,
    rendering,
    rawTableRows,
    rowCount: rawTable.rowCount,
    hasRows: rawTable.rowCount > 0,
    controls,
  };
}

export function formatNormalizationPolicySummary(policy) {
  const mode = normalizeMode(policy?.mode, DEFAULT_NORMALIZATION_POLICY.mode);
  if (mode === "rolling_trailing") {
    const currentWindowLabel = normalizeBoolean(
      policy?.excludeCurrentFromWindow,
      DEFAULT_NORMALIZATION_POLICY.excludeCurrentFromWindow,
    )
      ? "exclude current"
      : "include current";
    return [
      "Rolling trailing",
      `${clampInt(
        policy?.rollingWindowYears,
        ANALYTICS_CONTROL_BOUNDS.rollingWindowYears.min,
        ANALYTICS_CONTROL_BOUNDS.rollingWindowYears.max,
        DEFAULT_NORMALIZATION_POLICY.rollingWindowYears,
      )}y`,
      currentWindowLabel,
      `min obs ${clampInt(
        policy?.minObsForZscore,
        ANALYTICS_CONTROL_BOUNDS.minObsForZscore.min,
        ANALYTICS_CONTROL_BOUNDS.minObsForZscore.max,
        DEFAULT_NORMALIZATION_POLICY.minObsForZscore,
      )}`,
    ].join(", ");
  }

  const baselineStartYear = normalizePositiveInt(
    policy?.baselineStartYear,
    DEFAULT_NORMALIZATION_POLICY.baselineStartYear,
  );
  const limitToBaselineWindow = normalizeBoolean(
    policy?.limitToBaselineWindow,
    DEFAULT_NORMALIZATION_POLICY.limitToBaselineWindow,
  );

  if (!limitToBaselineWindow) {
    return `Static baseline from ${baselineStartYear}, full history shown`;
  }

  return `Static baseline from ${baselineStartYear}`;
}

export function recomputeIndicatorRows({ indicator, policy, policySource }) {
  const indicatorLabel = normalizeText(
    indicator?.indicator_label || indicator?.indicator_name || indicator?.indicator_id || "Indicator",
  );
  const indicatorId = normalizeText(indicator?.indicator_id);
  const sortedPoints = prepareComparablePoints(indicator?.points);

  if (policy.mode === "rolling_trailing") {
    return recomputeRollingTrailingRows({
      indicatorId,
      indicatorLabel,
      points: sortedPoints,
      policy,
      policySource,
    });
  }

  return recomputeStaticBaselineRows({
    indicatorId,
    indicatorLabel,
    points: sortedPoints,
    policy,
    policySource,
  });
}

function buildAnalyticsContext(normalizedSeries) {
  const safeSeries = isRecord(normalizedSeries) ? normalizedSeries : {};
  const indicators = Array.isArray(safeSeries.indicators)
    ? safeSeries.indicators.filter((indicator) => isRecord(indicator))
    : [];
  const exportCountryDefaultPolicy = deriveDefaultPolicy(safeSeries, indicators);
  const indicatorDefaultPolicies = buildIndicatorDefaultPolicyLookup(indicators, exportCountryDefaultPolicy);
  const exportIndicatorPolicies = buildOverrideLookup(
    safeSeries,
    indicators,
    exportCountryDefaultPolicy,
    indicatorDefaultPolicies,
  );

  return {
    safeSeries,
    indicators,
    exportCountryDefaultPolicy,
    indicatorDefaultPolicies,
    exportIndicatorPolicies,
  };
}

function buildControlsViewModel({ context, controlsState, activeCountryDefaultPolicy }) {
  const exportGlobalControls = controlsState.exportGlobalControls;
  const globalControls = controlsState.globalControls;
  const globalIsDirty = visibleControlsDiffer(globalControls, exportGlobalControls);
  const indicatorOverrideRows = context.indicators
    .map((indicator) => {
      const indicatorId = normalizeText(indicator.indicator_id);
      const indicatorLabel = normalizeText(
        indicator.indicator_label || indicator.indicator_name || indicatorId || "Indicator",
      );
      const exportOverrideValues = controlsState.exportIndicatorOverrides[indicatorId] || null;
      const activeOverrideValues = controlsState.indicatorOverrides[indicatorId] || null;
      const hasExportOverride = exportOverrideValues !== null;
      const hasActiveOverride = activeOverrideValues !== null;
      const currentValues = activeOverrideValues || globalControls;
      const effectivePolicy = hasActiveOverride
        ? applyVisibleControls(
            context.exportIndicatorPolicies.get(indicatorId) || context.exportCountryDefaultPolicy,
            currentValues,
          )
        : activeCountryDefaultPolicy;
      const isDirty =
        hasActiveOverride !== hasExportOverride ||
        (hasActiveOverride &&
          hasExportOverride &&
          visibleControlsDiffer(activeOverrideValues, exportOverrideValues));

      return {
        indicatorId,
        indicatorLabel,
        hasExportOverride,
        hasActiveOverride,
        currentValues,
        exportValues: exportOverrideValues,
        isDirty,
        policySummaryText: formatNormalizationPolicySummary(effectivePolicy),
      };
    })
    .sort((left, right) => left.indicatorLabel.localeCompare(right.indicatorLabel));
  const activeOverrideCount = indicatorOverrideRows.filter((row) => row.hasActiveOverride).length;
  const exportOverrideCount = indicatorOverrideRows.filter((row) => row.hasExportOverride).length;
  const hasChanges = globalIsDirty || indicatorOverrideRows.some((row) => row.isDirty);

  return {
    bounds: ANALYTICS_CONTROL_BOUNDS,
    global: {
      values: globalControls,
      exportValues: exportGlobalControls,
      isDirty: globalIsDirty,
      summaryText: formatNormalizationPolicySummary(activeCountryDefaultPolicy),
    },
    indicatorOverrides: indicatorOverrideRows,
    activeOverrideCount,
    exportOverrideCount,
    hasChanges,
  };
}

function buildRawTableModel(rawTableRows) {
  const renderableRowCount = rawTableRows.filter((row) => Number.isFinite(row.recomputedZscore)).length;
  return {
    columns: RAW_TABLE_COLUMNS,
    rows: rawTableRows,
    rowCount: rawTableRows.length,
    renderableRowCount,
    unavailableRowCount: rawTableRows.length - renderableRowCount,
  };
}

function buildStatusSummary(rawTableRows) {
  const counts = new Map();
  let projectedRowCount = 0;

  for (const row of rawTableRows) {
    const status = normalizeText(row.recomputedStatus) || "unknown";
    counts.set(status, (counts.get(status) || 0) + 1);
    if (row.isProjection) {
      projectedRowCount += 1;
    }
  }

  const statusCounts = Array.from(counts.entries())
    .map(([status, count]) => ({
      status,
      label: STATUS_LABELS[status] || status,
      count,
    }))
    .sort((left, right) => right.count - left.count || left.label.localeCompare(right.label));
  const okRowCount = counts.get("ok") || 0;

  return {
    totalRowCount: rawTableRows.length,
    okRowCount,
    unavailableRowCount: rawTableRows.length - okRowCount,
    projectedRowCount,
    statusCounts,
  };
}

function determineAnalyticsSectionState({ rowCount, renderableRowCount }) {
  if (!rowCount) {
    return "no_rows";
  }
  if (!renderableRowCount) {
    return "no_renderable_zscores";
  }
  if (renderableRowCount < rowCount) {
    return "partial";
  }
  return "ready";
}

function buildAnalyticsRenderingModel({ indicatorAnalytics, rawTableRows, sectionState, statusSummary }) {
  const renderableRows = rawTableRows.filter((row) => Number.isFinite(row.recomputedZscore));
  const years = Array.from(new Set(renderableRows.map((row) => row.year))).sort((left, right) => left - right);
  const heatmapRows = indicatorAnalytics.map((indicator) => {
    const renderableByYear = new Map(
      indicator.rows
        .filter((row) => Number.isFinite(row.recomputedZscore))
        .map((row) => [row.year, row]),
    );
    const cells = years.map((year) => {
      const matchingRow = renderableByYear.get(year) || null;
      return {
        year,
        hasValue: Boolean(matchingRow),
        zscore: matchingRow?.recomputedZscore ?? null,
        status: matchingRow?.recomputedStatus || "unavailable",
        policySource: matchingRow?.policySource || indicator.policySource,
        isProjection: matchingRow?.isProjection === true,
      };
    });

    return {
      indicatorId: indicator.indicatorId,
      indicatorLabel: indicator.indicatorLabel,
      renderableCellCount: cells.filter((cell) => cell.hasValue).length,
      cells,
    };
  });
  const timelineSeries = indicatorAnalytics.map((indicator) => ({
    indicatorId: indicator.indicatorId,
    indicatorLabel: indicator.indicatorLabel,
    renderablePointCount: indicator.rows.filter((row) => Number.isFinite(row.recomputedZscore)).length,
    points: indicator.rows.map((row) => ({
      year: row.year,
      zscore: row.recomputedZscore,
      status: row.recomputedStatus,
      isProjection: row.isProjection,
      policySource: row.policySource,
    })),
  }));

  return {
    sectionState,
    summary: {
      indicatorCount: indicatorAnalytics.length,
      yearCount: years.length,
      renderableCellCount: renderableRows.length,
      okRowCount: statusSummary.okRowCount,
    },
    heatmap: {
      years,
      rows: heatmapRows,
      hasRenderableCells: renderableRows.length > 0,
      emptyReason: sectionState === "ready" || sectionState === "partial" ? "" : sectionState,
    },
    timelines: {
      series: timelineSeries,
      hasRenderableSeries: timelineSeries.some((series) => series.renderablePointCount > 0),
      emptyReason: sectionState === "ready" || sectionState === "partial" ? "" : sectionState,
    },
  };
}

function buildExportIndicatorVisibleOverrides(context) {
  const visibleOverrides = {};
  for (const [indicatorId, policy] of context.exportIndicatorPolicies.entries()) {
    visibleOverrides[indicatorId] = selectVisibleControls(policy);
  }
  return visibleOverrides;
}

function deriveDefaultPolicy(normalizedSeries, indicators) {
  const topLevelNormalization = isRecord(normalizedSeries.normalization) ? normalizedSeries.normalization : {};
  const firstIndicatorNormalization = indicators
    .map((indicator) => (isRecord(indicator.normalization) ? indicator.normalization : null))
    .find((value) => Boolean(value));

  return normalizePolicy(
    topLevelNormalization,
    normalizePolicy(firstIndicatorNormalization, DEFAULT_NORMALIZATION_POLICY),
  );
}

function buildIndicatorDefaultPolicyLookup(indicators, defaultPolicy) {
  const lookup = new Map();
  for (const indicator of indicators) {
    const indicatorId = normalizeText(indicator.indicator_id);
    if (!indicatorId) {
      continue;
    }
    lookup.set(
      indicatorId,
      normalizePolicy(isRecord(indicator.normalization) ? indicator.normalization : {}, defaultPolicy),
    );
  }
  return lookup;
}

function buildOverrideLookup(normalizedSeries, indicators, defaultPolicy, indicatorDefaultPolicies) {
  const lookup = new Map();
  const overrideEntries = Array.isArray(normalizedSeries.normalization?.indicator_overrides)
    ? normalizedSeries.normalization.indicator_overrides.filter((entry) => isRecord(entry))
    : [];

  for (const entry of overrideEntries) {
    const indicatorId = normalizeText(entry.indicator_id);
    if (!indicatorId) {
      continue;
    }
    const inheritedPolicy = indicatorDefaultPolicies.get(indicatorId) || defaultPolicy;
    lookup.set(indicatorId, normalizePolicy(entry, inheritedPolicy));
  }

  for (const indicator of indicators) {
    const indicatorId = normalizeText(indicator.indicator_id);
    if (!indicatorId || lookup.has(indicatorId)) {
      continue;
    }

    const indicatorPolicy = indicatorDefaultPolicies.get(indicatorId) || defaultPolicy;
    if (policiesDiffer(indicatorPolicy, defaultPolicy)) {
      lookup.set(indicatorId, indicatorPolicy);
    }
  }

  return lookup;
}

function recomputeStaticBaselineRows({ indicatorId, indicatorLabel, points, policy, policySource }) {
  const baselinePoints = points.filter((point) => point.year >= policy.baselineStartYear);
  const baselineValues = baselinePoints.map((point) => point.value);
  const normalizationObs = baselineValues.length;
  const normalizationMean = baselineValues.length ? arithmeticMean(baselineValues) : null;
  const normalizationStd = sampleStandardDeviation(baselineValues);
  const canCompute =
    normalizationObs >= policy.minObsForZscore &&
    normalizationMean !== null &&
    normalizationStd !== null &&
    normalizationStd !== 0;

  return points
    .filter((point) => !(policy.limitToBaselineWindow && point.year < policy.baselineStartYear))
    .map((point) => {
      const recomputedZscore =
        canCompute && normalizationMean !== null && normalizationStd !== null
          ? (point.value - normalizationMean) / normalizationStd
          : null;
      return buildAnalyticsRow({
        indicatorId,
        indicatorLabel,
        point,
        policy,
        policySource,
        recomputedZscore,
        recomputedStatus: canCompute ? "ok" : "insufficient_variance_or_obs",
        normalizationObs,
        normalizationMean,
        normalizationStd,
      });
    });
}

function recomputeRollingTrailingRows({ indicatorId, indicatorLabel, points, policy, policySource }) {
  return points.map((point) => {
    const windowStartYear = policy.excludeCurrentFromWindow
      ? point.year - policy.rollingWindowYears
      : point.year - policy.rollingWindowYears + 1;
    const windowEndYear = policy.excludeCurrentFromWindow ? point.year - 1 : point.year;
    const windowPoints = points.filter((candidate) => candidate.year >= windowStartYear && candidate.year <= windowEndYear);
    const windowValues = windowPoints.map((candidate) => candidate.value);
    const normalizationObs = windowValues.length;
    const normalizationMean = windowValues.length ? arithmeticMean(windowValues) : null;
    const normalizationStd = sampleStandardDeviation(windowValues);

    let recomputedStatus = "ok";
    let recomputedZscore = null;
    if (normalizationObs === 0) {
      recomputedStatus = "no_eligible_window";
    } else if (normalizationObs < policy.minObsForZscore) {
      recomputedStatus = "insufficient_history";
    } else if (normalizationStd === null || normalizationStd === 0 || normalizationMean === null) {
      recomputedStatus = "zero_variance";
    } else {
      recomputedZscore = (point.value - normalizationMean) / normalizationStd;
    }

    return buildAnalyticsRow({
      indicatorId,
      indicatorLabel,
      point,
      policy,
      policySource,
      recomputedZscore,
      recomputedStatus,
      normalizationObs,
      normalizationMean,
      normalizationStd,
    });
  });
}

function buildAnalyticsRow({
  indicatorId,
  indicatorLabel,
  point,
  policy,
  policySource,
  recomputedZscore,
  recomputedStatus,
  normalizationObs,
  normalizationMean,
  normalizationStd,
}) {
  return {
    indicatorId,
    indicatorLabel,
    year: point.year,
    value: point.value,
    publishedZscore: point.zscore,
    publishedStatus: point.status,
    recomputedZscore,
    recomputedStatus,
    normalizationMode: policy.mode,
    baselineStartYear: policy.baselineStartYear,
    limitToBaselineWindow: policy.limitToBaselineWindow,
    minObsForZscore: policy.minObsForZscore,
    rollingWindowYears: policy.rollingWindowYears,
    excludeCurrentFromWindow: policy.excludeCurrentFromWindow,
    normalizationObs,
    normalizationMean,
    normalizationStd,
    policySource,
    policySourceLabel: policySource === "indicator_override" ? "indicator override" : "country default",
    policySummaryText: formatNormalizationPolicySummary(policy),
    isProjection: point.isProjection,
  };
}

function applyVisibleControls(policy, visibleControls) {
  const fullPolicy = isRecord(policy) ? policy : DEFAULT_NORMALIZATION_POLICY;
  const controls = normalizeVisibleControls(visibleControls, selectVisibleControls(fullPolicy));

  return {
    ...fullPolicy,
    mode: controls.mode,
    rollingWindowYears: controls.rollingWindowYears,
    minObsForZscore: controls.minObsForZscore,
  };
}

function normalizeControlsState(controlsState) {
  const safeState = isRecord(controlsState) ? controlsState : {};
  const exportGlobalControls = normalizeVisibleControls(
    safeState.exportGlobalControls,
    selectVisibleControls(DEFAULT_NORMALIZATION_POLICY),
  );
  const exportIndicatorOverrides = normalizeVisibleControlLookup(
    safeState.exportIndicatorOverrides,
    exportGlobalControls,
  );

  return {
    exportGlobalControls,
    globalControls: normalizeVisibleControls(safeState.globalControls, exportGlobalControls),
    exportIndicatorOverrides,
    indicatorOverrides: normalizeVisibleControlLookup(
      safeState.indicatorOverrides,
      exportGlobalControls,
    ),
  };
}

function normalizePolicy(candidate, fallback) {
  const safeFallback = isRecord(fallback) ? fallback : DEFAULT_NORMALIZATION_POLICY;
  const safeCandidate = isRecord(candidate) ? candidate : {};

  return {
    mode: normalizeMode(safeCandidate.mode, safeFallback.mode),
    baselineStartYear: normalizePositiveInt(
      safeCandidate.baseline_start_year ?? safeCandidate.baselineStartYear,
      safeFallback.baselineStartYear,
    ),
    limitToBaselineWindow: normalizeBoolean(
      safeCandidate.limit_to_baseline_window ?? safeCandidate.limitToBaselineWindow,
      safeFallback.limitToBaselineWindow,
    ),
    minObsForZscore: clampInt(
      safeCandidate.min_obs_for_zscore ?? safeCandidate.minObsForZscore,
      ANALYTICS_CONTROL_BOUNDS.minObsForZscore.min,
      ANALYTICS_CONTROL_BOUNDS.minObsForZscore.max,
      safeFallback.minObsForZscore,
    ),
    rollingWindowYears: clampInt(
      safeCandidate.rolling_window_years ?? safeCandidate.rollingWindowYears,
      ANALYTICS_CONTROL_BOUNDS.rollingWindowYears.min,
      ANALYTICS_CONTROL_BOUNDS.rollingWindowYears.max,
      safeFallback.rollingWindowYears,
    ),
    excludeCurrentFromWindow: normalizeBoolean(
      safeCandidate.exclude_current_from_window ?? safeCandidate.excludeCurrentFromWindow,
      safeFallback.excludeCurrentFromWindow,
    ),
  };
}

function normalizeVisibleControls(candidate, fallback) {
  const safeCandidate = isRecord(candidate) ? candidate : {};
  const safeFallback = isRecord(fallback) ? fallback : selectVisibleControls(DEFAULT_NORMALIZATION_POLICY);

  return {
    mode: normalizeMode(safeCandidate.mode, safeFallback.mode),
    rollingWindowYears: clampInt(
      safeCandidate.rolling_window_years ?? safeCandidate.rollingWindowYears,
      ANALYTICS_CONTROL_BOUNDS.rollingWindowYears.min,
      ANALYTICS_CONTROL_BOUNDS.rollingWindowYears.max,
      safeFallback.rollingWindowYears,
    ),
    minObsForZscore: clampInt(
      safeCandidate.min_obs_for_zscore ?? safeCandidate.minObsForZscore,
      ANALYTICS_CONTROL_BOUNDS.minObsForZscore.min,
      ANALYTICS_CONTROL_BOUNDS.minObsForZscore.max,
      safeFallback.minObsForZscore,
    ),
  };
}

function normalizeVisibleControlLookup(lookup, fallback) {
  if (!isRecord(lookup)) {
    return {};
  }

  const normalizedLookup = {};
  for (const [indicatorId, value] of Object.entries(lookup)) {
    const normalizedIndicatorId = normalizeText(indicatorId);
    if (!normalizedIndicatorId) {
      continue;
    }
    normalizedLookup[normalizedIndicatorId] = normalizeVisibleControls(value, fallback);
  }
  return normalizedLookup;
}

function cloneVisibleControlLookup(lookup) {
  const clone = {};
  for (const [indicatorId, controls] of Object.entries(lookup || {})) {
    clone[indicatorId] = { ...controls };
  }
  return clone;
}

function selectVisibleControls(policy) {
  return {
    mode: policy.mode,
    rollingWindowYears: policy.rollingWindowYears,
    minObsForZscore: policy.minObsForZscore,
  };
}

function visibleControlsDiffer(left, right) {
  return VISIBLE_CONTROL_FIELDS.some((field) => left?.[field] !== right?.[field]);
}

function policiesDiffer(left, right) {
  return POLICY_FIELDS.some((field) => left[field] !== right[field]);
}

function prepareComparablePoints(points) {
  const safePoints = Array.isArray(points) ? points.filter((point) => isRecord(point)) : [];
  return safePoints
    .map((point) => ({
      year: Number(point.year),
      value: Number(point.value),
      zscore: typeof point.zscore === "number" && Number.isFinite(point.zscore) ? point.zscore : null,
      status: normalizeText(point.status),
      isProjection: point.is_projection === true,
    }))
    .filter((point) => Number.isFinite(point.year) && Number.isFinite(point.value))
    .sort((left, right) => left.year - right.year);
}

function arithmeticMean(values) {
  if (!values.length) {
    return null;
  }
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function sampleStandardDeviation(values) {
  if (values.length < 2) {
    return null;
  }
  const mean = arithmeticMean(values);
  if (mean === null) {
    return null;
  }
  const variance = values.reduce((sum, value) => sum + (value - mean) ** 2, 0) / (values.length - 1);
  return Math.sqrt(variance);
}

function normalizeMode(value, fallback) {
  const normalized = normalizeText(value).toLowerCase();
  return NORMALIZATION_MODES.has(normalized) ? normalized : fallback;
}

function normalizePositiveInt(value, fallback) {
  const normalized = Number(value);
  return Number.isInteger(normalized) && normalized > 0 ? normalized : fallback;
}

function clampInt(value, min, max, fallback) {
  const normalized = Number(value);
  if (!Number.isInteger(normalized)) {
    return fallback;
  }
  return Math.min(max, Math.max(min, normalized));
}

function normalizeBoolean(value, fallback) {
  if (typeof value === "boolean") {
    return value;
  }
  return fallback;
}

function normalizeText(value) {
  return String(value || "").trim();
}

function isRecord(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}
