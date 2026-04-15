import test from "node:test";
import assert from "node:assert/strict";

import { createIndicatorViewModel } from "../src/app/view-models/indicator-view-model.js";
import {
  findCompatibleForecastOverlay,
  findForecastChartDisclosure,
} from "../src/app/view-models/forecast-overlay-model.js";

function buildIndicatorViewModel() {
  return createIndicatorViewModel({
    indicator_id: "inflation",
    indicator_label: "Inflation",
    unit: "percent",
    observation_count: 4,
    year_range: {
      min_year: 2020,
      max_year: 2023,
    },
    points: [
      { year: 2020, value: 2, zscore: null, status: "ok", is_projection: false },
      { year: 2021, value: 4, zscore: null, status: "ok", is_projection: false },
      { year: 2022, value: 6, zscore: null, status: "ok", is_projection: false },
      { year: 2023, value: 8, zscore: null, status: "ok", is_projection: false },
    ],
  });
}

test("findCompatibleForecastOverlay returns a chart overlay only for matching raw-level forecast rows", () => {
  const indicatorViewModel = buildIndicatorViewModel();

  const overlay = findCompatibleForecastOverlay({
    indicatorViewModel,
    forecast: {
      rows: [
        {
          indicator_id: "inflation",
          indicator_label: "Inflation | Test source",
          forecast_year: 2024,
          forecast_value: 3.5,
          forecast_unit: "percent",
          selected_candidate: "inflation__none__lag1",
        },
      ],
    },
  });

  assert.deepEqual(overlay, {
    forecastYear: 2024,
    forecastValue: 3.5,
    forecastUnit: "percent",
    indicatorId: "inflation",
    indicatorLabel: "Inflation | Test source",
    selectedCandidate: "inflation__none__lag1",
    transformMethod: "none",
  });
});

test("findCompatibleForecastOverlay excludes transformed or unit-incompatible forecast rows", () => {
  const indicatorViewModel = buildIndicatorViewModel();

  const overlay = findCompatibleForecastOverlay({
    indicatorViewModel,
    forecast: {
      rows: [
        {
          indicator_id: "inflation",
          indicator_label: "Inflation | Test source",
          forecast_year: 2024,
          forecast_value: 0.5,
          forecast_unit: "pp",
          selected_candidate: "inflation__pp_change_lag1__lag1",
        },
      ],
    },
  });

  assert.equal(overlay, null);
});

test("findForecastChartDisclosure returns a transformed-forecast notice for matching non-plotted rows", () => {
  const indicatorViewModel = buildIndicatorViewModel();

  const disclosure = findForecastChartDisclosure({
    indicatorViewModel,
    forecast: {
      rows: [
        {
          indicator_id: "inflation",
          indicator_label: "Inflation | Test source",
          forecast_year: 2024,
          forecast_value: 0.5,
          forecast_unit: "pp",
          selected_candidate: "inflation__pp_change_lag1__lag1",
        },
      ],
    },
  });

  assert.deepEqual(disclosure, {
    indicatorId: "inflation",
    indicatorLabel: "Inflation | Test source",
    forecastYear: 2024,
    forecastUnit: "pp",
    transformMethod: "pp_change_lag1",
    message:
      "CCOutline forecast available in Forecast section and not plotted here because it is shown as a percentage-point change rather than in the chart's raw units.",
  });
});

test("findForecastChartDisclosure keeps yearly-change notices plain-language", () => {
  const indicatorViewModel = buildIndicatorViewModel();

  const disclosure = findForecastChartDisclosure({
    indicatorViewModel,
    forecast: {
      rows: [
        {
          indicator_id: "inflation",
          indicator_label: "Inflation | Test source",
          forecast_year: 2024,
          forecast_value: 1.2,
          forecast_unit: "pct",
          selected_candidate: "inflation__log_diff_yoy__lag1",
        },
      ],
    },
  });

  assert.deepEqual(disclosure, {
    indicatorId: "inflation",
    indicatorLabel: "Inflation | Test source",
    forecastYear: 2024,
    forecastUnit: "pct",
    transformMethod: "log_diff_yoy",
    message:
      "CCOutline forecast available in Forecast section and not plotted here because it is shown as a yearly change rather than in the chart's raw units.",
  });

  assert.doesNotMatch(disclosure.message, /pct_change_yoy/);
  assert.doesNotMatch(disclosure.message, /log_diff_yoy/);
  assert.doesNotMatch(disclosure.message, /pp_change_lag1/);
});
