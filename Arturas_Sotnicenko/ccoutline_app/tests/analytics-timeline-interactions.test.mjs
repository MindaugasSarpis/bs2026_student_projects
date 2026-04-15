import test from "node:test";
import assert from "node:assert/strict";
import { JSDOM } from "jsdom";

import { syncAnalyticsTimelineInteractions } from "../src/app/charts/analytics-timeline-interactions.js";
import { createD3AnalyticsChartRenderer } from "../src/app/charts/d3-analytics-chart-renderer.js";

function buildAnalyticsState({ includeEmployment = true } = {}) {
  const series = [
    {
      indicatorId: "inflation",
      indicatorLabel: "Inflation",
      points: [
        { year: 2020, zscore: -0.2 },
        { year: 2021, zscore: 3.1 },
        { year: 2022, zscore: 0.9 },
        { year: 2023, zscore: 0.2 },
      ],
    },
    {
      indicatorId: "interest_rate",
      indicatorLabel: "Interest rate",
      points: [
        { year: 2020, zscore: 0.1 },
        { year: 2021, zscore: 2.8 },
        { year: 2022, zscore: 0.6 },
        { year: 2023, zscore: -0.1 },
      ],
    },
    {
      indicatorId: "government_balance",
      indicatorLabel: "Government balance",
      points: [
        { year: 2020, zscore: -2.4 },
        { year: 2021, zscore: -1.1 },
        { year: 2022, zscore: 0.3 },
        { year: 2023, zscore: 0.6 },
      ],
    },
  ];

  if (includeEmployment) {
    series.push({
      indicatorId: "employment",
      indicatorLabel: "Employment",
      points: [
        { year: 2020, zscore: 0.4 },
        { year: 2021, zscore: 0.8 },
        { year: 2022, zscore: 1.0 },
        { year: 2023, zscore: 1.2 },
      ],
    });
  }

  return {
    countryCode: "LT",
    displayName: "Lithuania",
    rendering: {
      timelines: {
        hasRenderableSeries: true,
        series,
      },
    },
  };
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
    const previousHTMLButtonElement = globalThis.HTMLButtonElement;
    const previousMouseEvent = globalThis.MouseEvent;

    globalThis.window = dom.window;
    globalThis.document = dom.window.document;
    globalThis.Element = dom.window.Element;
    globalThis.HTMLElement = dom.window.HTMLElement;
    globalThis.SVGElement = dom.window.SVGElement;
    globalThis.HTMLButtonElement = dom.window.HTMLButtonElement;
    globalThis.MouseEvent = dom.window.MouseEvent;

    try {
      await testFn(dom);
    } finally {
      globalThis.window = previousWindow;
      globalThis.document = previousDocument;
      globalThis.Element = previousElement;
      globalThis.HTMLElement = previousHTMLElement;
      globalThis.SVGElement = previousSVGElement;
      globalThis.HTMLButtonElement = previousHTMLButtonElement;
      globalThis.MouseEvent = previousMouseEvent;
      dom.window.close();
    }
  };
}

function renderTimeline(dom, analyticsState) {
  const renderer = createD3AnalyticsChartRenderer();
  const root = dom.window.document.querySelector("#root");
  root.innerHTML = renderer.renderCountryAnalyticsTimeline({ analyticsState });

  const figure = root.querySelector("[data-analytics-timeline='true']");
  const svg = figure.querySelector("svg");
  const defaultRect = { left: 0, top: 0, width: 860, height: 320, right: 860, bottom: 320 };
  figure.getBoundingClientRect = () => ({ ...defaultRect, height: 420, bottom: 420 });
  svg.getBoundingClientRect = () => ({ ...defaultRect });

  figure.querySelectorAll(".analytics-chart__timeline-series-hit, .analytics-chart__timeline-legend-item").forEach((element, index) => {
    element.getBoundingClientRect = () => ({
      left: 100 + index * 12,
      top: 80 + index * 10,
      width: 22,
      height: 16,
      right: 122 + index * 12,
      bottom: 96 + index * 10,
    });
  });

  return { root, figure };
}

test(
  "analytics timeline sync exposes all series in the legend and preserves default top-three emphasis",
  withDom(async (dom) => {
    const selectionStateByCountry = new Map();
    const { figure } = renderTimeline(dom, buildAnalyticsState());

    syncAnalyticsTimelineInteractions(figure.parentElement, { selectionStateByCountry });

    const legendItems = Array.from(figure.querySelectorAll(".analytics-chart__timeline-legend-item"));
    assert.equal(legendItems.length, 4);
    assert.deepEqual(
      legendItems.map((item) => item.querySelector(".analytics-chart__timeline-legend-text")?.textContent),
      ["Inflation", "Interest rate", "Government balance", "Employment"],
    );

    const defaultItems = legendItems.filter((item) => item.getAttribute("data-active-state") === "default");
    assert.equal(defaultItems.length, 3);
    assert.equal(
      figure.querySelector(".analytics-chart__timeline-series[data-series-id='employment']")?.getAttribute("stroke"),
      "#b8c0c8",
    );
  }),
);

test(
  "analytics timeline hover highlights a muted series and updates the tooltip",
  withDom(async (dom) => {
    const selectionStateByCountry = new Map();
    const { figure } = renderTimeline(dom, buildAnalyticsState());

    syncAnalyticsTimelineInteractions(figure.parentElement, { selectionStateByCountry });

    const employmentHit = figure.querySelector(".analytics-chart__timeline-series-hit[data-series-id='employment']");
    employmentHit.dispatchEvent(
      new dom.window.MouseEvent("mousemove", {
        bubbles: true,
        clientX: 790,
        clientY: 180,
      }),
    );

    const employmentPath = figure.querySelector(".analytics-chart__timeline-series[data-series-id='employment']");
    const tooltip = figure.querySelector(".analytics-chart__timeline-tooltip");
    assert.equal(employmentPath.getAttribute("stroke-width"), "3.2");
    assert.equal(tooltip.hidden, false);
    assert.match(tooltip.textContent, /Employment/);
    assert.match(tooltip.textContent, /2023/);
    assert.match(tooltip.textContent, /\+1\.2/);

    employmentHit.dispatchEvent(new dom.window.MouseEvent("mouseleave", { bubbles: true }));
    assert.equal(tooltip.hidden, true);
    assert.equal(employmentPath.getAttribute("stroke"), "#b8c0c8");
  }),
);

test(
  "analytics timeline legend clicks support multi-select and fall back to default emphasis when cleared",
  withDom(async (dom) => {
    const selectionStateByCountry = new Map();
    const { figure } = renderTimeline(dom, buildAnalyticsState());

    syncAnalyticsTimelineInteractions(figure.parentElement, { selectionStateByCountry });

    const employmentButton = figure.querySelector(".analytics-chart__timeline-legend-item[data-series-id='employment']");
    const inflationButton = figure.querySelector(".analytics-chart__timeline-legend-item[data-series-id='inflation']");

    employmentButton.dispatchEvent(new dom.window.MouseEvent("click", { bubbles: true }));
    assert.equal(employmentButton.getAttribute("aria-pressed"), "true");
    assert.equal(employmentButton.getAttribute("data-active-state"), "selected");
    assert.equal(inflationButton.getAttribute("data-active-state"), "inactive");

    inflationButton.dispatchEvent(new dom.window.MouseEvent("click", { bubbles: true }));
    assert.equal(inflationButton.getAttribute("aria-pressed"), "true");
    assert.equal(employmentButton.getAttribute("data-active-state"), "selected");
    assert.equal(inflationButton.getAttribute("data-active-state"), "selected");

    employmentButton.dispatchEvent(new dom.window.MouseEvent("click", { bubbles: true }));
    inflationButton.dispatchEvent(new dom.window.MouseEvent("click", { bubbles: true }));
    assert.equal(employmentButton.getAttribute("aria-pressed"), "false");
    assert.equal(inflationButton.getAttribute("aria-pressed"), "false");
    assert.equal(inflationButton.getAttribute("data-active-state"), "default");
    assert.equal(employmentButton.getAttribute("data-active-state"), "inactive");
  }),
);

test(
  "analytics timeline selection state is pruned safely after rerender",
  withDom(async (dom) => {
    const selectionStateByCountry = new Map();
    let rendered = renderTimeline(dom, buildAnalyticsState());

    syncAnalyticsTimelineInteractions(rendered.figure.parentElement, { selectionStateByCountry });
    rendered.figure
      .querySelector(".analytics-chart__timeline-legend-item[data-series-id='employment']")
      .dispatchEvent(new dom.window.MouseEvent("click", { bubbles: true }));
    assert.deepEqual([...selectionStateByCountry.get("LT")], ["employment"]);

    rendered = renderTimeline(dom, buildAnalyticsState({ includeEmployment: false }));
    syncAnalyticsTimelineInteractions(rendered.figure.parentElement, { selectionStateByCountry });

    assert.equal(selectionStateByCountry.has("LT"), false);
    const defaultItems = rendered.figure.querySelectorAll(".analytics-chart__timeline-legend-item[data-active-state='default']");
    assert.equal(defaultItems.length, 3);
  }),
);
