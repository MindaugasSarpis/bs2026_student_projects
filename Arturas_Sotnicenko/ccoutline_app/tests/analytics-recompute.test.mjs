import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

import {
  createCountryAnalyticsControlsState,
  createCountryAnalyticsState,
  formatNormalizationPolicySummary,
  resetCountryAnalyticsControlsState,
  setCountryAnalyticsIndicatorOverrideState,
  updateCountryAnalyticsGlobalControlsState,
  updateCountryAnalyticsIndicatorOverrideControlsState,
} from "../src/app/analytics/recompute.js";

function buildOverrideFixture() {
  return {
    country_code: "LT",
    display_name: "Lithuania",
    normalization: {
      mode: "static_baseline",
      baseline_start_year: 1999,
      limit_to_baseline_window: true,
      min_obs_for_zscore: 3,
      rolling_window_years: 10,
      exclude_current_from_window: true,
      indicator_overrides: [
        {
          indicator_id: "inflation_cpi_yoy",
          mode: "rolling_trailing",
          baseline_start_year: 1999,
          limit_to_baseline_window: true,
          min_obs_for_zscore: 2,
          rolling_window_years: 2,
          exclude_current_from_window: true,
        },
      ],
    },
    indicators: [
      {
        indicator_id: "inflation_cpi_yoy",
        indicator_label: "Inflation",
        normalization: {
          mode: "rolling_trailing",
          baseline_start_year: 1999,
          limit_to_baseline_window: true,
          min_obs_for_zscore: 2,
          rolling_window_years: 2,
          exclude_current_from_window: true,
        },
        points: [
          { year: 2020, value: 2, zscore: null, status: "no_eligible_window", is_projection: false },
          { year: 2021, value: 2, zscore: null, status: "insufficient_history", is_projection: false },
          { year: 2022, value: 3, zscore: null, status: "zero_variance", is_projection: false },
          { year: 2023, value: 4, zscore: null, status: "ok", is_projection: false },
        ],
      },
      {
        indicator_id: "real_gdp",
        indicator_label: "Real GDP",
        points: [
          { year: 2020, value: 100, zscore: null, status: "ok", is_projection: false },
          { year: 2021, value: 110, zscore: null, status: "ok", is_projection: false },
          { year: 2022, value: 120, zscore: null, status: "ok", is_projection: false },
        ],
      },
    ],
  };
}

function buildFullHistoryFixture() {
  return {
    country_code: "LT",
    display_name: "Lithuania",
    normalization: {
      mode: "static_baseline",
      baseline_start_year: 1999,
      limit_to_baseline_window: false,
      min_obs_for_zscore: 3,
      rolling_window_years: 10,
      exclude_current_from_window: true,
      summary_text: "Static baseline from 1999, full history shown, min obs 3",
      indicator_overrides: [],
    },
    indicators: [
      {
        indicator_id: "real_gdp",
        indicator_label: "Real GDP",
        points: [
          { year: 1995, value: 70, zscore: null, status: "ok", is_projection: false },
          { year: 1996, value: 72, zscore: null, status: "ok", is_projection: false },
          { year: 1997, value: 74, zscore: null, status: "ok", is_projection: false },
          { year: 1998, value: 76, zscore: null, status: "ok", is_projection: false },
          { year: 1999, value: 80, zscore: null, status: "ok", is_projection: false },
          { year: 2000, value: 84, zscore: null, status: "ok", is_projection: false },
          { year: 2001, value: 89, zscore: null, status: "ok", is_projection: false },
          { year: 2002, value: 94, zscore: null, status: "ok", is_projection: false },
          { year: 2003, value: 100, zscore: null, status: "ok", is_projection: false },
        ],
      },
    ],
  };
}

function loadShippedCountrySeries(countryCode) {
  const filePath = path.resolve("generated/ccoutline_site/data", countryCode, "normalized_series.json");
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

test("createCountryAnalyticsState recomputes static baseline rows from export-aligned defaults", () => {
  let controlsState = createCountryAnalyticsControlsState({
    country_code: "LT",
    display_name: "Lithuania",
    normalization: {
      mode: "static_baseline",
      baseline_start_year: 2000,
      limit_to_baseline_window: true,
      min_obs_for_zscore: 3,
      rolling_window_years: 10,
      exclude_current_from_window: true,
      summary_text: "Static baseline from 2000, min obs 3",
      indicator_overrides: [],
    },
    indicators: [
      {
        indicator_id: "real_gdp",
        indicator_label: "Real GDP",
        points: [
          { year: 1999, value: 90, zscore: null, status: "ok", is_projection: false },
          { year: 2000, value: 100, zscore: null, status: "ok", is_projection: false },
          { year: 2001, value: 110, zscore: null, status: "ok", is_projection: false },
          { year: 2002, value: 120, zscore: null, status: "ok", is_projection: false },
        ],
      },
    ],
  });
  controlsState = updateCountryAnalyticsGlobalControlsState(controlsState, {
    mode: "static_baseline",
    minObsForZscore: 3,
  });
  const analyticsState = createCountryAnalyticsState(
    {
      country_code: "LT",
      display_name: "Lithuania",
      normalization: {
        mode: "static_baseline",
        baseline_start_year: 2000,
        limit_to_baseline_window: true,
        min_obs_for_zscore: 3,
        rolling_window_years: 10,
        exclude_current_from_window: true,
        summary_text: "Static baseline from 2000, min obs 3",
        indicator_overrides: [],
      },
      indicators: [
        {
          indicator_id: "real_gdp",
          indicator_label: "Real GDP",
          points: [
            { year: 1999, value: 90, zscore: null, status: "ok", is_projection: false },
            { year: 2000, value: 100, zscore: null, status: "ok", is_projection: false },
            { year: 2001, value: 110, zscore: null, status: "ok", is_projection: false },
            { year: 2002, value: 120, zscore: null, status: "ok", is_projection: false },
          ],
        },
      ],
    },
    controlsState,
  );

  assert.equal(analyticsState.defaultSummaryText, "Static baseline from 2000");
  assert.equal(analyticsState.rowCount, 3);
  assert.deepEqual(
    analyticsState.rawTableRows.map((row) => row.year),
    [2000, 2001, 2002],
  );
  assert.ok(Math.abs(analyticsState.rawTableRows[0].recomputedZscore + 1) < 1e-9);
  assert.equal(analyticsState.rawTableRows[1].recomputedStatus, "ok");
  assert.ok(Math.abs(analyticsState.rawTableRows[2].recomputedZscore - 1) < 1e-9);
  assert.equal(analyticsState.sectionState, "ready");
  assert.equal(analyticsState.rawTable.columns[0].label, "Indicator");
  assert.equal(analyticsState.rawTable.renderableRowCount, 3);
});

test("createCountryAnalyticsState keeps pre-baseline rows when the export default shows full history", () => {
  let controlsState = createCountryAnalyticsControlsState(buildFullHistoryFixture());
  let analyticsState = createCountryAnalyticsState(buildFullHistoryFixture(), controlsState);

  assert.equal(analyticsState.exportDefaultSummaryText, "Static baseline from 1999, full history shown");
  assert.equal(analyticsState.defaultSummaryText, "Rolling trailing, 10y, exclude current, min obs 3");
  assert.deepEqual(
    analyticsState.rawTableRows.map((row) => row.year),
    [1995, 1996, 1997, 1998, 1999, 2000, 2001, 2002, 2003],
  );
  assert.equal(analyticsState.controls.hasChanges, true);
  assert.equal(analyticsState.rawTableRows[0].normalizationMode, "rolling_trailing");
  assert.equal(analyticsState.rawTableRows[0].recomputedStatus, "no_eligible_window");
  assert.equal(analyticsState.rawTableRows[1].recomputedStatus, "insufficient_history");

  controlsState = updateCountryAnalyticsGlobalControlsState(controlsState, {
    mode: "rolling_trailing",
    rollingWindowYears: 4,
    minObsForZscore: 4,
  });
  analyticsState = createCountryAnalyticsState(buildFullHistoryFixture(), controlsState);
  assert.equal(analyticsState.defaultSummaryText, "Rolling trailing, 4y, exclude current, min obs 4");

  controlsState = resetCountryAnalyticsControlsState(controlsState);
  analyticsState = createCountryAnalyticsState(buildFullHistoryFixture(), controlsState);

  assert.equal(analyticsState.controls.hasChanges, false);
  assert.equal(analyticsState.defaultSummaryText, "Static baseline from 1999, full history shown");
  assert.deepEqual(
    analyticsState.rawTableRows.map((row) => row.year),
    [1995, 1996, 1997, 1998, 1999, 2000, 2001, 2002, 2003],
  );
});

test("createCountryAnalyticsState carries explicit per-indicator overrides into recomputation", () => {
  const analyticsState = createCountryAnalyticsState(buildOverrideFixture());

  assert.equal(analyticsState.overrideCount, 1);
  assert.equal(analyticsState.controls.indicatorOverrides[0].indicatorId, "inflation_cpi_yoy");
  assert.equal(analyticsState.rawTableRows[0].recomputedStatus, "no_eligible_window");
  assert.equal(analyticsState.rawTableRows[1].recomputedStatus, "insufficient_history");
  assert.equal(analyticsState.rawTableRows[2].recomputedStatus, "zero_variance");
  assert.equal(analyticsState.rawTableRows[3].policySource, "indicator_override");
  assert.equal(analyticsState.rawTableRows[3].recomputedStatus, "ok");
  assert.ok(Math.abs(analyticsState.rawTableRows[3].recomputedZscore - 2.1213203435596424) < 1e-9);
  assert.equal(analyticsState.sectionState, "partial");
  assert.equal(analyticsState.statusSummary.okRowCount, 1);
  assert.equal(analyticsState.statusSummary.statusCounts[0].status, "insufficient_history");
  assert.equal(analyticsState.rawTableRows[4].policySource, "country_default");
  assert.equal(analyticsState.rawTableRows[4].recomputedStatus, "no_eligible_window");
  assert.ok(analyticsState.rendering.heatmap.hasRenderableCells);
  assert.ok(analyticsState.rendering.timelines.hasRenderableSeries);
  assert.deepEqual(analyticsState.rendering.heatmap.years, [2023]);
  assert.equal(analyticsState.rendering.heatmap.rows[0].indicatorId, "inflation_cpi_yoy");
  assert.equal(analyticsState.rendering.heatmap.rows[0].cells[0].hasValue, true);
  assert.equal(analyticsState.rendering.timelines.series[0].points[0].status, "no_eligible_window");
});

test("formatNormalizationPolicySummary describes rolling policy settings", () => {
  assert.equal(
    formatNormalizationPolicySummary({
      mode: "rolling_trailing",
      rollingWindowYears: 10,
      excludeCurrentFromWindow: true,
      minObsForZscore: 5,
    }),
    "Rolling trailing, 10y, exclude current, min obs 5",
  );
});

test("formatNormalizationPolicySummary omits min-obs wording for static-baseline visitor summaries", () => {
  assert.equal(
    formatNormalizationPolicySummary({
      mode: "static_baseline",
      baselineStartYear: 2000,
      limitToBaselineWindow: true,
      minObsForZscore: 7,
    }),
    "Static baseline from 2000",
  );
  assert.equal(
    formatNormalizationPolicySummary({
      mode: "static_baseline",
      baselineStartYear: 1999,
      limitToBaselineWindow: false,
      minObsForZscore: 9,
    }),
    "Static baseline from 1999, full history shown",
  );
});

test("shipped static-baseline payloads keep visitor-visible analytics outputs unchanged across the min-obs range", () => {
  for (const countryCode of ["LT", "LV", "EE", "DK"]) {
    const series = loadShippedCountrySeries(countryCode);
    let controlsState = createCountryAnalyticsControlsState(series);
    let baselineSnapshot = null;

    for (let minObs = 2; minObs <= 10; minObs += 1) {
      controlsState = updateCountryAnalyticsGlobalControlsState(controlsState, {
        mode: "static_baseline",
        minObsForZscore: minObs,
      });
      const analyticsState = createCountryAnalyticsState(series, controlsState);
      const snapshot = {
        rowCount: analyticsState.rowCount,
        renderableRowCount: analyticsState.rawTable.renderableRowCount,
        renderableCellCount: analyticsState.rendering.summary.renderableCellCount,
        sectionState: analyticsState.sectionState,
        statusCounts: analyticsState.statusSummary.statusCounts.map(({ status, count }) => ({ status, count })),
        zscoreSignature: analyticsState.rawTableRows
          .filter((row) => typeof row.recomputedZscore === "number")
          .slice(0, 12)
          .map((row) => `${row.indicatorId}:${row.year}:${row.recomputedZscore.toFixed(6)}`)
          .join("|"),
        defaultSummaryText: analyticsState.defaultSummaryText,
        exportDefaultSummaryText: analyticsState.exportDefaultSummaryText,
      };

      assert.ok(!analyticsState.defaultSummaryText.includes("min obs"));
      assert.ok(!analyticsState.exportDefaultSummaryText.includes("min obs"));

      if (!baselineSnapshot) {
        baselineSnapshot = snapshot;
      } else {
        assert.deepEqual(snapshot, baselineSnapshot, `${countryCode} changed at min obs ${minObs}`);
      }
    }
  }
});

test("analytics controls update global defaults and clear indicator overrides back to country defaults", () => {
  let controlsState = createCountryAnalyticsControlsState(buildOverrideFixture());
  controlsState = updateCountryAnalyticsGlobalControlsState(controlsState, {
    mode: "rolling_trailing",
    rollingWindowYears: 4,
    minObsForZscore: 4,
  });
  controlsState = setCountryAnalyticsIndicatorOverrideState(controlsState, "inflation_cpi_yoy", false);

  const analyticsState = createCountryAnalyticsState(buildOverrideFixture(), controlsState);
  const inflationRows = analyticsState.rawTableRows.filter((row) => row.indicatorId === "inflation_cpi_yoy");

  assert.equal(analyticsState.controls.global.isDirty, true);
  assert.equal(analyticsState.controls.indicatorOverrides[0].hasActiveOverride, false);
  assert.equal(inflationRows[0].policySource, "country_default");
  assert.equal(inflationRows[0].rollingWindowYears, 4);
  assert.equal(inflationRows[1].minObsForZscore, 4);
});

test("analytics controls can re-enable and edit an indicator override, then reset to export defaults", () => {
  let controlsState = createCountryAnalyticsControlsState(buildOverrideFixture());
  controlsState = setCountryAnalyticsIndicatorOverrideState(controlsState, "real_gdp", true);
  controlsState = updateCountryAnalyticsIndicatorOverrideControlsState(controlsState, "real_gdp", {
    mode: "rolling_trailing",
    rollingWindowYears: 3,
    minObsForZscore: 2,
  });

  let analyticsState = createCountryAnalyticsState(buildOverrideFixture(), controlsState);
  const gdpOverride = analyticsState.controls.indicatorOverrides.find((row) => row.indicatorId === "real_gdp");

  assert.equal(gdpOverride.hasActiveOverride, true);
  assert.equal(gdpOverride.currentValues.mode, "rolling_trailing");
  assert.equal(gdpOverride.currentValues.rollingWindowYears, 3);
  assert.equal(analyticsState.controls.hasChanges, true);

  controlsState = resetCountryAnalyticsControlsState(controlsState);
  analyticsState = createCountryAnalyticsState(buildOverrideFixture(), controlsState);

  assert.equal(analyticsState.controls.hasChanges, false);
  assert.equal(
    analyticsState.controls.indicatorOverrides.find((row) => row.indicatorId === "real_gdp").hasActiveOverride,
    false,
  );
  assert.equal(analyticsState.controls.global.values.mode, "static_baseline");
});

test("analytics state stays explicit when rows exist but no renderable z-scores are available", () => {
  const analyticsState = createCountryAnalyticsState({
    country_code: "LT",
    normalization: {
      mode: "rolling_trailing",
      rolling_window_years: 5,
      min_obs_for_zscore: 5,
      exclude_current_from_window: true,
    },
    indicators: [
      {
        indicator_id: "employment",
        indicator_label: "Employment",
        points: [
          { year: 2022, value: 10, zscore: null, status: "no_eligible_window", is_projection: false },
          { year: 2023, value: 11, zscore: null, status: "insufficient_history", is_projection: false },
        ],
      },
    ],
  });

  assert.equal(analyticsState.sectionState, "no_renderable_zscores");
  assert.equal(analyticsState.rawTable.rowCount, 2);
  assert.equal(analyticsState.rawTable.renderableRowCount, 0);
  assert.equal(analyticsState.rendering.heatmap.emptyReason, "no_renderable_zscores");
  assert.equal(analyticsState.rendering.timelines.emptyReason, "no_renderable_zscores");
});
