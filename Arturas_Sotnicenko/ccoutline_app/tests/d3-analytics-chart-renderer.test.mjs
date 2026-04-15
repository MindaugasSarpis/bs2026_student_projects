import test from "node:test";
import assert from "node:assert/strict";
import { JSDOM } from "jsdom";

import { __test__, createD3AnalyticsChartRenderer } from "../src/app/charts/d3-analytics-chart-renderer.js";

function buildHeatmapAnalyticsState({ yearStart = 1986, yearCount = 38, rowCount = 2 } = {}) {
  const years = Array.from({ length: yearCount }, (_, index) => yearStart + index);
  const rows = Array.from({ length: rowCount }, (_, rowIndex) => ({
    indicatorId: `indicator_${rowIndex + 1}`,
    indicatorLabel: `Indicator ${rowIndex + 1}`,
    cells: years.map((year, yearIndex) => ({
      year,
      hasValue: true,
      zscore: (yearIndex % 7) - 3 + rowIndex * 0.25,
      isProjection: false,
    })),
  }));

  return {
    countryCode: "LT",
    displayName: "Lithuania",
    defaultSummaryText: "Rolling trailing, 10y, exclude current, min obs 5",
    rendering: {
      heatmap: {
        hasRenderableCells: true,
        years,
        rows,
      },
    },
  };
}

function buildSeriesFixtures() {
  return [
    {
      indicatorId: "inflation",
      indicatorLabel: "Inflation",
      points: [
        { year: 2020, zscore: 0.2 },
        { year: 2021, zscore: 3.1 },
        { year: 2022, zscore: 1.3 },
      ],
    },
    {
      indicatorId: "interest_rate",
      indicatorLabel: "Interest rate",
      points: [
        { year: 2020, zscore: 0.1 },
        { year: 2021, zscore: 2.7 },
        { year: 2022, zscore: 0.8 },
      ],
    },
    {
      indicatorId: "government_balance",
      indicatorLabel: "Government balance",
      points: [
        { year: 2020, zscore: -2.2 },
        { year: 2021, zscore: -1.6 },
        { year: 2022, zscore: -0.3 },
      ],
    },
    {
      indicatorId: "employment",
      indicatorLabel: "Employment",
      points: [
        { year: 2020, zscore: 0.4 },
        { year: 2021, zscore: 1.2 },
        { year: 2022, zscore: 0.7 },
      ],
    },
  ];
}

function withDom(testFn) {
  return async () => {
    const dom = new JSDOM("<!doctype html><div id='root'></div>", {
      pretendToBeVisual: true,
    });
    const previousWindow = globalThis.window;
    const previousDocument = globalThis.document;
    const previousElement = globalThis.Element;
    const previousHTMLElement = globalThis.HTMLElement;
    const previousSVGElement = globalThis.SVGElement;

    globalThis.window = dom.window;
    globalThis.document = dom.window.document;
    globalThis.Element = dom.window.Element;
    globalThis.HTMLElement = dom.window.HTMLElement;
    globalThis.SVGElement = dom.window.SVGElement;

    try {
      await testFn(dom);
    } finally {
      globalThis.window = previousWindow;
      globalThis.document = previousDocument;
      globalThis.Element = previousElement;
      globalThis.HTMLElement = previousHTMLElement;
      globalThis.SVGElement = previousSVGElement;
      dom.window.close();
    }
  };
}

test("analytics timeline render model assigns deterministic accent colors and anomaly points", () => {
  const seriesModels = __test__.buildTimelineSeriesModels(buildSeriesFixtures());

  assert.equal(seriesModels.length, 4);
  assert.ok(seriesModels.every((series) => typeof series.accentColor === "string" && series.accentColor.startsWith("#")));
  assert.deepEqual(
    seriesModels.find((series) => series.indicatorId === "inflation")?.anomalyPoints,
    [{ year: 2021, zscore: 3.1 }],
  );
  assert.deepEqual(
    seriesModels.find((series) => series.indicatorId === "employment")?.anomalyPoints,
    [],
  );
});

test("analytics timeline persistent ids fall back to the top three strongest series", () => {
  const seriesModels = __test__.buildTimelineSeriesModels(buildSeriesFixtures());

  const persistentIds = __test__.deriveTimelinePersistentSeriesIds(seriesModels);

  assert.deepEqual([...persistentIds].sort(), ["government_balance", "inflation", "interest_rate"]);
});

test("analytics timeline persistent ids preserve surviving manual selections", () => {
  const seriesModels = __test__.buildTimelineSeriesModels(buildSeriesFixtures());

  const persistentIds = __test__.deriveTimelinePersistentSeriesIds(seriesModels, new Set(["employment", "inflation"]));

  assert.deepEqual([...persistentIds].sort(), ["employment", "inflation"]);
});

test("heatmap layout model keeps a dedicated year-label rail and only thins labels for dense ranges", () => {
  const shortRangeLayout = __test__.buildHeatmapLayoutModel({ yearCount: 8, rowCount: 2 });
  const denseRangeLayout = __test__.buildHeatmapLayoutModel({ yearCount: 38, rowCount: 2 });

  assert.equal(shortRangeLayout.yearLabelStep, 1);
  assert.equal(denseRangeLayout.yearLabelStep, 2);
  assert.ok(denseRangeLayout.yearLabelBaselineY < denseRangeLayout.gridStartY - 6);
  assert.equal(__test__.shouldRenderHeatmapYearLabel(0, 38, denseRangeLayout.yearLabelStep), true);
  assert.equal(__test__.shouldRenderHeatmapYearLabel(1, 38, denseRangeLayout.yearLabelStep), false);
  assert.equal(__test__.shouldRenderHeatmapYearLabel(2, 38, denseRangeLayout.yearLabelStep), true);
  assert.equal(__test__.shouldRenderHeatmapYearLabel(37, 38, denseRangeLayout.yearLabelStep), true);
});

test("analytics heatmap renderer preserves the full matrix while separating dense year labels from the grid", withDom((dom) => {
  const analyticsState = buildHeatmapAnalyticsState();
  const renderer = createD3AnalyticsChartRenderer();
  const layout = __test__.buildHeatmapLayoutModel({
    yearCount: analyticsState.rendering.heatmap.years.length,
    rowCount: analyticsState.rendering.heatmap.rows.length,
  });

  const root = dom.window.document.querySelector("#root");
  root.innerHTML = renderer.renderCountryAnalyticsHeatmap({ analyticsState });
  const markup = root.innerHTML;

  assert.match(markup, /data-analytics-heatmap="true"/);
  assert.match(markup, new RegExp(`data-year-label-step="${layout.yearLabelStep}"`));
  assert.match(markup, new RegExp(`data-grid-start-y="${layout.gridStartY}"`));
  assert.match(markup, new RegExp(`class="analytics-chart__heatmap-axis"[^>]*y1="${layout.gridStartY - 6}"`));
  assert.match(markup, new RegExp(`class="analytics-chart__x-label"[^>]*y="${layout.yearLabelBaselineY}"`));
  assert.equal((markup.match(/class="analytics-chart__x-label"/g) || []).length, 20);
  assert.equal((markup.match(/<title>/g) || []).length, 76);
  assert.match(markup, />1986</);
  assert.match(markup, />2023</);
  assert.match(markup, /Current analytics setting: Rolling trailing, 10y, exclude current, min obs 5\./);
  assert.match(markup, /Cooler colors mark lower z-scores and warmer colors mark higher z-scores\./);
  assert.match(markup, /Gray cells mean no numeric z-score under the current settings\./);
  assert.doesNotMatch(markup, />1987</);
  assert.doesNotMatch(markup, /Rendered through the D3 analytics adapter/);
}));
