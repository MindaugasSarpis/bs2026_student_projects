import test from "node:test";
import assert from "node:assert/strict";
import { JSDOM } from "jsdom";

import { __test__, createD3IndicatorChartRenderer } from "../src/app/charts/d3-indicator-chart-renderer.js";

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

test("d3 indicator chart legend labels CCOutline forecast cues explicitly", () => {
  const items = __test__.buildLegendItems({
    projectedPoints: [],
    nonOkPoints: [],
    forecastOverlay: { forecastYear: 2025, forecastValue: 3.5 },
  });

  assert.deepEqual(items, [
    {
      kind: "forecast",
      label: "CCOutline forecast",
    },
  ]);
});

test("d3 indicator chart caption context labels CCOutline forecast cues explicitly", () => {
  const labels = __test__.buildChartContextLabels({
    projectedPoints: [],
    nonOkPoints: [],
    forecastOverlay: { forecastYear: 2025, forecastValue: 3.5 },
    forecastChartDisclosure: null,
  });

  assert.deepEqual(labels, ["CCOutline forecast for 2025"]);
});

test("d3 indicator chart caption context includes non-plotted CCOutline forecast notices", () => {
  const message =
    "CCOutline forecast available in Forecast section and not plotted here because it is shown as a yearly change rather than in the chart's raw units.";
  const labels = __test__.buildChartContextLabels({
    projectedPoints: [],
    nonOkPoints: [],
    forecastOverlay: null,
    forecastChartDisclosure: {
      message,
    },
  });

  assert.deepEqual(labels, [message]);
  assert.doesNotMatch(labels[0], /pct_change_yoy/);
  assert.doesNotMatch(labels[0], /log_diff_yoy/);
  assert.doesNotMatch(labels[0], /pp_change_lag1/);
});

test("d3 indicator chart caption stays visitor-facing and omits adapter wording", withDom((dom) => {
  const renderer = createD3IndicatorChartRenderer();
  const root = dom.window.document.querySelector("#root");

  root.innerHTML = renderer.renderIndicatorChart({
    indicatorViewModel: {
      indicatorId: "inflation",
      indicatorLabel: "Inflation",
      title: "Inflation",
      unit: "percent",
      plottedPoints: [
        { year: 2020, value: 2.1, status: "ok", is_projection: false },
        { year: 2021, value: 3.4, status: "ok", is_projection: false },
        { year: 2022, value: 4.2, status: "ok", is_projection: false },
      ],
    },
    forecastOverlay: { forecastYear: 2023, forecastValue: 4.8 },
    forecastChartDisclosure: null,
  });

  const markup = root.innerHTML;
  assert.match(markup, /percent/);
  assert.match(markup, /2020-2022/);
  assert.match(markup, /CCOutline forecast for 2023/);
  assert.doesNotMatch(markup, /Rendered through the D3 chart adapter/);
  assert.doesNotMatch(markup, /forecast cue/);
}));
