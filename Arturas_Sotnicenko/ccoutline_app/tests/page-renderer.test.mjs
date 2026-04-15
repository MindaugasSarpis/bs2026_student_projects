import test from "node:test";
import assert from "node:assert/strict";

import { createCountryAnalyticsState } from "../src/app/analytics/recompute.js";
import {
  renderCountryPanelRegionMarkup,
  renderGlobeNavigationMarkup,
  renderPage,
  renderStandaloneLegalPage,
} from "../src/app/rendering/page-renderer.js";

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function assertSectionDisclosureState(html, { title, variant, open }) {
  const pattern = new RegExp(
    `<details class="section-disclosure section-disclosure--${escapeRegExp(variant)}"${open ? " open" : ""}>[\\s\\S]*?<summary[\\s\\S]*?class="section-disclosure__summary"[\\s\\S]*?aria-label="Toggle ${escapeRegExp(title)} section"[\\s\\S]*?>`,
  );

  assert.match(html, pattern);
}

function assertIndicatorDisclosureState(html, { title, open }) {
  const pattern = new RegExp(
    `<details class="indicator-disclosure"${open ? " open" : ""}>[\\s\\S]*?<summary[\\s\\S]*?class="indicator-disclosure__summary"[\\s\\S]*?aria-label="Toggle indicator details"[\\s\\S]*?>[\\s\\S]*?<span class="indicator-disclosure__title">${escapeRegExp(title)}</span>`,
  );

  assert.match(html, pattern);
}

function buildRenderableCountrySeries() {
  return {
    country_code: "LT",
    display_name: "Lithuania",
    year_range: {
      min_year: 2020,
      max_year: 2023,
    },
    normalization: {
      mode: "static_baseline",
      baseline_start_year: 2020,
      limit_to_baseline_window: true,
      min_obs_for_zscore: 3,
      rolling_window_years: 10,
      exclude_current_from_window: true,
      summary_text: "Static baseline from 2020, min obs 3",
      indicator_overrides: [],
    },
    indicators: [
      {
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
      },
      {
        indicator_id: "gdp",
        indicator_label: "GDP",
        unit: "usd",
        observation_count: 4,
        year_range: {
          min_year: 2020,
          max_year: 2023,
        },
        points: [
          { year: 2020, value: 100, zscore: null, status: "ok", is_projection: false },
          { year: 2021, value: 110, zscore: null, status: "ok", is_projection: false },
          { year: 2022, value: 120, zscore: null, status: "ok", is_projection: false },
          { year: 2023, value: 140, zscore: null, status: "ok", is_projection: false },
        ],
      },
    ],
  };
}

function buildSparseCountrySeries() {
  return {
    country_code: "LT",
    display_name: "Lithuania",
    year_range: {
      min_year: 2022,
      max_year: 2023,
    },
    normalization: {
      mode: "rolling_trailing",
      baseline_start_year: 1999,
      limit_to_baseline_window: true,
      min_obs_for_zscore: 5,
      rolling_window_years: 5,
      exclude_current_from_window: true,
      summary_text: "Rolling trailing, 5y, exclude current, min obs 5",
      indicator_overrides: [],
    },
    indicators: [
      {
        indicator_id: "employment",
        indicator_label: "Employment",
        observation_count: 2,
        year_range: {
          min_year: 2022,
          max_year: 2023,
        },
        points: [
          { year: 2022, value: 10, zscore: null, status: "no_eligible_window", is_projection: false },
          { year: 2023, value: 11, zscore: null, status: "insufficient_history", is_projection: false },
        ],
      },
    ],
  };
}

function buildRenderableCountrySeriesWithOverride(overrideValues = {}) {
  const series = buildRenderableCountrySeries();
  series.normalization.indicator_overrides = [
    {
      indicator_id: "inflation",
      mode: "static_baseline",
      rolling_window_years: 8,
      min_obs_for_zscore: 4,
      ...overrideValues,
    },
  ];
  return series;
}

function buildAppState(normalizedSeries) {
  const countryModel = {
    countryCode: "LT",
    countryEntry: {
      country_code: "LT",
      display_name: "Lithuania",
    },
    forecast: {
      country_code: "LT",
      status: "ready",
      row_count: 1,
      notes: [
        "These CCOutline forecasts extend each indicator beyond the latest published value shown on the page.",
      ],
      rows: [
        {
          indicator_id: "inflation",
          indicator_label: "Inflation | World Bank",
          forecast_year: 2024,
          forecast_value: 3.25,
          forecast_unit: "pp",
          latest_observed_year: 2023,
          selected_candidate: "inflation__pp_change_lag1__lag1",
          metric_summary: {
            split_count: 12,
          },
          interpretation: "CCOutline forecast for Inflation in 2024, shown in pp.",
          limitations:
            "This value is shown in transformed units rather than the raw indicator level, so compare it as a model output rather than as a direct raw-value estimate. Supported by 12 validation checks.",
        },
      ],
    },
    forecastLoadError: null,
    normalizedSeries,
    analyticsState: createCountryAnalyticsState(normalizedSeries),
    uiState: buildCountryUiState(normalizedSeries),
  };

  return {
    countriesError: null,
    consentState: {
      decision: null,
      hydrated: true,
      updatedAt: null,
    },
    countriesPayload: {
      active_country_codes: ["LT"],
      countries: [
        {
          country_code: "LT",
          display_name: "Lithuania",
        },
      ],
    },
    selectedCountryCode: "LT",
    selectedCountryModel: countryModel,
    countryModels: [countryModel],
  };
}

function buildCountryUiState(normalizedSeries) {
  const indicatorIds = Array.isArray(normalizedSeries?.indicators)
    ? normalizedSeries.indicators.map((indicator) => indicator.indicator_id)
    : [];
  const indicatorDisclosures = Object.fromEntries(
    indicatorIds.map((indicatorId) => [
      indicatorId,
      {
        disclosureId: `${indicatorId}-disclosure`,
        open: false,
        rawDataDisclosureId: `${indicatorId}-raw-data`,
        rawDataOpen: false,
      },
    ]),
  );

  return {
    countrySections: {
      glossary: { disclosureId: "glossary", open: false },
      analytics: { disclosureId: "analytics", open: false },
      forecast: { disclosureId: "forecast", open: false },
      charts: { disclosureId: "charts", open: false },
    },
    analyticsSections: {
      summary: { disclosureId: "analytics-summary", open: false },
      overrides: { disclosureId: "analytics-overrides", open: false },
      rawTable: { disclosureId: "analytics-raw-table", open: false },
    },
    indicatorDisclosures,
  };
}

test("renderPage injects analytics heatmap and timeline surfaces through the chart seam", () => {
  const appRoot = { innerHTML: "" };
  const heatmapCalls = [];
  const timelineCalls = [];

  renderPage(appRoot, buildAppState(buildRenderableCountrySeries()), {
    chartRenderer: {
      renderIndicatorChart() {
        return "<div data-indicator-chart>Indicator chart</div>";
      },
      renderCountryAnalyticsHeatmap(context) {
        heatmapCalls.push(context);
        return `<div data-analytics-heatmap>${context.analyticsState.rendering.summary.renderableCellCount}</div>`;
      },
      renderCountryAnalyticsTimeline(context) {
        timelineCalls.push(context);
        return `<div data-analytics-timeline>${context.analyticsState.rendering.timelines.series.length}</div>`;
      },
    },
  });

  assert.equal(heatmapCalls.length, 1);
  assert.equal(timelineCalls.length, 1);
  assert.match(appRoot.innerHTML, /data-consent-banner="true"/);
  assert.match(appRoot.innerHTML, /data-consent-backdrop="true"/);
  assert.match(appRoot.innerHTML, /data-consent-dialog="true"/);
  assert.match(appRoot.innerHTML, /role="dialog"/);
  assert.match(appRoot.innerHTML, /aria-modal="true"/);
  assert.match(appRoot.innerHTML, /aria-labelledby="consent-dialog-title"/);
  assert.match(appRoot.innerHTML, /aria-describedby="consent-dialog-description consent-dialog-links"/);
  assert.match(appRoot.innerHTML, /tabindex="-1"/);
  assert.match(appRoot.innerHTML, /id="consent-dialog-title"/);
  assert.match(appRoot.innerHTML, /id="consent-dialog-description"/);
  assert.match(appRoot.innerHTML, /id="consent-dialog-links"/);
  assert.match(appRoot.innerHTML, /Choose whether CCOUTLINE may load analytics\./);
  assert.match(appRoot.innerHTML, /data-consent-action="accepted"/);
  assert.match(appRoot.innerHTML, /data-consent-action="declined"/);
  assert.match(appRoot.innerHTML, /href="\/privacy\/" data-legal-link="privacy"/);
  assert.match(appRoot.innerHTML, /href="\/cookies\/" data-legal-link="cookies"/);
  assert.match(appRoot.innerHTML, /href="\/manage-cookies\/" data-legal-link="manage-cookies"/);
  assert.equal(heatmapCalls[0].analyticsState.rendering.heatmap.hasRenderableCells, true);
  assert.equal(timelineCalls[0].analyticsState.rendering.timelines.hasRenderableSeries, true);
  assertSectionDisclosureState(appRoot.innerHTML, { title: "Indicator glossary", variant: "country", open: false });
  assertSectionDisclosureState(appRoot.innerHTML, { title: "Data analytics", variant: "country", open: false });
  assertSectionDisclosureState(appRoot.innerHTML, { title: "Forecast", variant: "country", open: false });
  assertSectionDisclosureState(appRoot.innerHTML, { title: "Indicator charts", variant: "country", open: false });
  assertSectionDisclosureState(appRoot.innerHTML, { title: "Analytics state summary", variant: "nested", open: false });
  assertSectionDisclosureState(appRoot.innerHTML, { title: "Per-indicator overrides", variant: "nested", open: false });
  assertSectionDisclosureState(appRoot.innerHTML, { title: "Raw z-score table", variant: "nested", open: false });
  assert.match(appRoot.innerHTML, /These analytics views help visitors compare the published yearly values under the current settings\./);
  assert.match(
    appRoot.innerHTML,
    /Use these controls to review how the analytics views change under the available settings\./,
  );
  assert.match(appRoot.innerHTML, /Modified from published settings/);
  assert.match(appRoot.innerHTML, /Matches export baseline\./);
  assert.match(appRoot.innerHTML, /Published setting/);
  assert.match(appRoot.innerHTML, /Reset to published settings/);
  assert.match(appRoot.innerHTML, /Analytics heatmap/);
  assert.match(appRoot.innerHTML, /The heatmap shows how each indicator's z-scores change over time under the current settings:/);
  assert.match(appRoot.innerHTML, /cooler colors\s+mark lower/);
  assert.match(appRoot.innerHTML, /warmer colors mark higher z-scores/);
  assert.match(appRoot.innerHTML, /gray cells stay visible/);
  assert.match(appRoot.innerHTML, /no numeric\s+z-score is/);
  assert.match(appRoot.innerHTML, /Timeline and anomaly view/);
  assert.match(
    appRoot.innerHTML,
    /The timeline view uses the same z-scores and highlights the strongest swings without hiding the rest of the\s+indicator history\./,
  );
  assert.match(appRoot.innerHTML, /These visuals and the raw z-score table below reflect the same current analytics settings/);
  assert.match(appRoot.innerHTML, /data-analytics-heatmap/);
  assert.match(appRoot.innerHTML, /data-analytics-timeline/);
  assert.doesNotMatch(appRoot.innerHTML, /export defaults/);
  assert.match(appRoot.innerHTML, /CCOUTLINE brings together published macroeconomic indicators/);
  assert.match(
    appRoot.innerHTML,
    /Explore definitions, yearly data, analytical views,\s+and forecast series with the context needed to read them clearly\./,
  );
  assert.match(
    appRoot.innerHTML,
    /Browse each country to see which indicators are covered and how far the yearly series runs\./,
  );
  assert.match(
    appRoot.innerHTML,
    /Use analytics views and indicator charts to spot patterns, unusual years, and contrasts across indicators\./,
  );
  assert.match(
    appRoot.innerHTML,
    /Check the forecast section to distinguish observed history from CCOUTLINE forecasts\./,
  );
  assert.doesNotMatch(appRoot.innerHTML, /Use it to see which indicators are included for each country\./);
  assert.doesNotMatch(appRoot.innerHTML, /review labels, units, and source names/);
  assert.doesNotMatch(appRoot.innerHTML, /Use it to compare the analytics views and chart disclosures with the underlying country data\./);
  assert.doesNotMatch(appRoot.innerHTML, /browser-recomputed z-scores/);
  assert.match(appRoot.innerHTML, /2 indicators/);
  assert.match(appRoot.innerHTML, /1 forecast row/);
  assert.match(
    appRoot.innerHTML,
    /These CCOutline forecasts are educational projections based on the latest published data shown for\s+each indicator\./,
  );
  assert.match(
    appRoot.innerHTML,
    /They are not observed history and should be read together with the interpretation\s+and limitation notes below\./,
  );
  assert.match(appRoot.innerHTML, /Forecast status: ready • 1 forecast row shown\./);
  assert.doesNotMatch(appRoot.innerHTML, /offline forecasting pipeline/);
  assert.match(
    appRoot.innerHTML,
    /These CCOutline forecasts extend each indicator beyond the latest published value shown on the page\./,
  );
  assert.match(appRoot.innerHTML, /CCOutline forecast: 2024/);
  assert.match(appRoot.innerHTML, /Selected source through 2023/);
  assert.match(appRoot.innerHTML, /CCOutline forecast for Inflation in 2024, shown in pp\./);
  assert.match(appRoot.innerHTML, /Shown as percentage-point change/);
  assert.match(
    appRoot.innerHTML,
    /This forecast is shown in transformed units rather than the raw indicator level, so compare it as a\s+model output rather than as a direct raw-value estimate\./,
  );
  assert.match(appRoot.innerHTML, /Supported by 12 validation checks\./);
  assert.doesNotMatch(appRoot.innerHTML, /Selected candidate:/);
  assert.doesNotMatch(appRoot.innerHTML, /pp_change_lag1/);
  assert.doesNotMatch(appRoot.innerHTML, /One-step CCOutline offline forecast/);
  assert.doesNotMatch(appRoot.innerHTML, /selected preprocessing winner uses/);
  assert.match(appRoot.innerHTML, /2 chart-backed disclosures/);
  assert.match(appRoot.innerHTML, /class="analytics-chart-scroller"/);
  assert.doesNotMatch(appRoot.innerHTML, /future heatmap\/timeline rendering/);
  assert.doesNotMatch(appRoot.innerHTML, /keeps the country-wide z-score matrix visible under the current controls/);
});

test("renderPage hides the consent banner once a decision has already been stored", () => {
  const appRoot = { innerHTML: "" };
  const appState = buildAppState(buildRenderableCountrySeries());
  appState.consentState = {
    decision: "accepted",
    hydrated: true,
    updatedAt: "2026-04-12T18:00:00.000Z",
  };

  renderPage(appRoot, appState, {
    chartRenderer: {
      renderIndicatorChart() {
        return "<div data-indicator-chart>Indicator chart</div>";
      },
      renderCountryAnalyticsHeatmap() {
        return "<div data-analytics-heatmap>heatmap</div>";
      },
      renderCountryAnalyticsTimeline() {
        return "<div data-analytics-timeline>timeline</div>";
      },
    },
  });

  assert.doesNotMatch(appRoot.innerHTML, /data-consent-banner="true"/);
});

test("renderStandaloneLegalPage renders the shared footer and manage-cookies controls", () => {
  const appRoot = { innerHTML: "" };

  renderStandaloneLegalPage(
    appRoot,
    {
      key: "manage-cookies",
      pathname: "/manage-cookies/",
      kicker: "CCOUTLINE legal",
      title: "Manage Cookies",
      lead: "Use this page to review the browser choice.",
      sections: [
        {
          heading: "How this control works",
          paragraphs: ["Buttons on this page update the current browser choice."],
        },
      ],
    },
    {
      decision: "declined",
      hydrated: true,
      updatedAt: "2026-04-12T18:30:00.000Z",
    },
  );

  assert.match(appRoot.innerHTML, /data-legal-page="manage-cookies"/);
  assert.match(appRoot.innerHTML, /data-manage-cookies-panel="true"/);
  assert.match(appRoot.innerHTML, /data-manage-cookies-status="true">Current analytics choice: Declined</);
  assert.match(appRoot.innerHTML, /Stored choice updated:/);
  assert.match(appRoot.innerHTML, /href="\/privacy\/" data-legal-link="privacy"/);
  assert.match(appRoot.innerHTML, /href="\/manage-cookies\/" data-legal-link="manage-cookies" aria-current="page"/);
});

test("renderGlobeNavigationMarkup renders a synchronized fallback country button row next to the globe surface", () => {
  const markup = renderGlobeNavigationMarkup({
    countryModels: [
      {
        countryCode: "LT",
        countryEntry: { country_code: "LT", display_name: "Lithuania" },
      },
      {
        countryCode: "LV",
        countryEntry: { country_code: "LV", display_name: "Latvia" },
      },
    ],
    globeMarkup: "<figure class='globe-nav' data-globe-adapter='d3'></figure>",
    selectedCountryCode: "LV",
  });

  assert.match(markup, /data-globe-navigation-block="true"/);
  assert.match(markup, /Choose a country from the globe/);
  assert.match(markup, /data-country-select-control="true"/);
  assert.match(markup, /data-country-code="LT"/);
  assert.match(markup, /data-country-code="LV"/);
  assert.match(markup, /aria-pressed="true"[\s\S]*?>\s*Latvia\s*</);
  assert.match(markup, /Use the globe to focus on country panel, or use the\s+country buttons below if standard controls are more convenient\./);
  assert.match(markup, /data-globe-adapter='d3'/);
});

test("renderCountryPanelRegionMarkup renders a dedicated selected-country panel seam", () => {
  const normalizedSeries = buildRenderableCountrySeries();
  const appState = buildAppState(normalizedSeries);
  const markup = renderCountryPanelRegionMarkup({
    selectedCountryCode: "LT",
    selectedCountryModel: appState.selectedCountryModel,
    chartRenderer: {
      renderIndicatorChart() {
        return "<div data-indicator-chart>Indicator chart</div>";
      },
      renderCountryAnalyticsHeatmap() {
        return "<div data-analytics-heatmap>heatmap</div>";
      },
      renderCountryAnalyticsTimeline() {
        return "<div data-analytics-timeline>timeline</div>";
      },
    },
  });

  assert.match(markup, /data-country-panel-region="true"/);
  assert.match(markup, /data-selected-country-code="LT"/);
  assert.match(markup, /data-country-code="LT"/);
  assert.match(markup, /Lithuania \(LT\)/);
  assert.match(markup, /Indicator glossary/);
  assert.match(markup, /Data analytics/);
  assert.match(markup, /Forecast/);
  assert.match(markup, /Indicator charts/);
  assert.doesNotMatch(markup, /data-country-panel-empty-state="true"/);
});

test("renderCountryPanelRegionMarkup renders an explicit empty prompt before first country selection", () => {
  const markup = renderCountryPanelRegionMarkup({
    selectedCountryCode: null,
    selectedCountryModel: null,
    chartRenderer: {
      renderIndicatorChart() {
        return "";
      },
      renderCountryAnalyticsHeatmap() {
        return "";
      },
      renderCountryAnalyticsTimeline() {
        return "";
      },
    },
  });

  assert.match(markup, /data-country-panel-region="true"/);
  assert.match(markup, /data-selected-country-code=""/);
  assert.match(markup, /data-country-panel-empty-state="true"/);
  assert.match(markup, /Select a supported country to begin\./);
  assert.match(markup, /Choose Lithuania, Latvia, Estonia, or Denmark/);
});

test("renderPage includes the globe navigation block when globe markup is provided", () => {
  const appRoot = { innerHTML: "" };
  const appState = {
    ...buildAppState(buildRenderableCountrySeries()),
    globeMarkup: "<figure class='globe-nav' data-globe-adapter='d3'></figure>",
    selectedCountryCode: "LT",
  };

  renderPage(appRoot, appState, {
    chartRenderer: {
      renderIndicatorChart() {
        return "<div data-indicator-chart>Indicator chart</div>";
      },
      renderCountryAnalyticsHeatmap() {
        return "<div data-analytics-heatmap>heatmap</div>";
      },
      renderCountryAnalyticsTimeline() {
        return "<div data-analytics-timeline>timeline</div>";
      },
    },
  });

  assert.match(appRoot.innerHTML, /data-globe-navigation-block="true"/);
  assert.match(appRoot.innerHTML, /data-country-panel-region="true"/);
  assert.match(appRoot.innerHTML, /data-selected-country-code="LT"/);
  assert.match(appRoot.innerHTML, /data-country-select-control="true"/);
  assert.match(appRoot.innerHTML, /aria-pressed="true"/);
  assert.match(appRoot.innerHTML, /data-globe-adapter='d3'/);
});

test("renderPage renders only the selected country panel instead of every country section", () => {
  const appRoot = { innerHTML: "" };
  const lithuaniaState = buildAppState(buildRenderableCountrySeries());
  const latviaSeries = {
    ...buildRenderableCountrySeries(),
    country_code: "LV",
    display_name: "Latvia",
  };
  const latviaModel = {
    ...lithuaniaState.countryModels[0],
    countryCode: "LV",
    countryEntry: {
      country_code: "LV",
      display_name: "Latvia",
    },
    normalizedSeries: latviaSeries,
    analyticsState: createCountryAnalyticsState(latviaSeries),
    uiState: buildCountryUiState(latviaSeries),
  };
  const appState = {
    ...lithuaniaState,
    countriesPayload: {
      active_country_codes: ["LT", "LV"],
      countries: [
        { country_code: "LT", display_name: "Lithuania" },
        { country_code: "LV", display_name: "Latvia" },
      ],
    },
    selectedCountryCode: "LV",
    selectedCountryModel: latviaModel,
    countryModels: [lithuaniaState.countryModels[0], latviaModel],
  };

  renderPage(appRoot, appState, {
    chartRenderer: {
      renderIndicatorChart() {
        return "<div data-indicator-chart>Indicator chart</div>";
      },
      renderCountryAnalyticsHeatmap() {
        return "<div data-analytics-heatmap>heatmap</div>";
      },
      renderCountryAnalyticsTimeline() {
        return "<div data-analytics-timeline>timeline</div>";
      },
    },
  });

  assert.match(appRoot.innerHTML, /data-country-panel-region="true"/);
  assert.match(appRoot.innerHTML, /data-selected-country-code="LV"/);
  assert.match(appRoot.innerHTML, /Latvia \(LV\)/);
  assert.doesNotMatch(appRoot.innerHTML, /Lithuania \(LT\)/);
  assert.equal((appRoot.innerHTML.match(/data-country-code=/g) || []).length, 1);
});

test("renderPage shows the selected-country prompt when no country has been chosen yet", () => {
  const appRoot = { innerHTML: "" };
  const appState = {
    ...buildAppState(buildRenderableCountrySeries()),
    globeMarkup: "<figure class='globe-nav' data-globe-adapter='d3'></figure>",
    selectedCountryCode: null,
    selectedCountryModel: null,
  };

  renderPage(appRoot, appState, {
    chartRenderer: {
      renderIndicatorChart() {
        return "<div data-indicator-chart>Indicator chart</div>";
      },
      renderCountryAnalyticsHeatmap() {
        return "<div data-analytics-heatmap>heatmap</div>";
      },
      renderCountryAnalyticsTimeline() {
        return "<div data-analytics-timeline>timeline</div>";
      },
    },
  });

  assert.match(appRoot.innerHTML, /data-country-panel-region="true"/);
  assert.match(appRoot.innerHTML, /data-country-panel-empty-state="true"/);
  assert.match(appRoot.innerHTML, /Select a supported country to begin\./);
  assert.doesNotMatch(appRoot.innerHTML, /<section class="section-panel" id="country-lt" data-country-code="LT">/);
});

test("renderPage keeps forecast rows and root intro bullets visitor-facing", () => {
  const appRoot = { innerHTML: "" };
  const appState = buildAppState(buildRenderableCountrySeries());

  appState.countryModels[0].forecast = {
    country_code: "LT",
    status: "ready",
    row_count: 1,
    notes: [
      "These CCOutline forecasts extend each indicator beyond the latest published value shown on the page.",
    ],
    rows: [
      {
        indicator_id: "gdp",
        indicator_label: "GDP | Test source",
        forecast_year: 2024,
        forecast_value: 2.5,
        forecast_unit: "pct",
        latest_observed_year: 2023,
        selected_candidate: "gdp__log_diff_yoy__lag1",
        metric_summary: {
          split_count: 8,
        },
        interpretation: "CCOutline forecast for GDP in 2024, shown in pct.",
        limitations:
          "This value is shown in transformed units rather than the raw indicator level, so compare it as a model output rather than as a direct raw-value estimate. Supported by 8 validation checks.",
      },
    ],
  };

  renderPage(appRoot, appState, {
    chartRenderer: {
      renderIndicatorChart() {
        return "<div data-indicator-chart>Indicator chart</div>";
      },
      renderCountryAnalyticsHeatmap() {
        return "<div data-analytics-heatmap>heatmap</div>";
      },
      renderCountryAnalyticsTimeline() {
        return "<div data-analytics-timeline>timeline</div>";
      },
    },
  });

  assert.match(appRoot.innerHTML, /Browse each country to see which indicators are covered and how far the yearly series runs\./);
  assert.match(
    appRoot.innerHTML,
    /Use analytics views and indicator charts to spot patterns, unusual years, and contrasts across indicators\./,
  );
  assert.match(
    appRoot.innerHTML,
    /Check the forecast section to distinguish observed history from CCOUTLINE forecasts\./,
  );
  assert.doesNotMatch(appRoot.innerHTML, /Use it to see which indicators are included for each country\./);
  assert.doesNotMatch(appRoot.innerHTML, /review labels, units, and source names/);
  assert.doesNotMatch(appRoot.innerHTML, /Use it to compare the analytics views and chart disclosures with the underlying country data\./);

  assert.match(appRoot.innerHTML, /CCOutline forecast for GDP in 2024, shown in pct\./);
  assert.match(appRoot.innerHTML, /Shown as yearly change/);
  assert.match(appRoot.innerHTML, /Supported by 8 validation checks\./);
  assert.doesNotMatch(appRoot.innerHTML, /Selected candidate:/);
  assert.doesNotMatch(appRoot.innerHTML, /pct_change_yoy/);
  assert.doesNotMatch(appRoot.innerHTML, /log_diff_yoy/);
  assert.doesNotMatch(appRoot.innerHTML, /pp_change_lag1/);
});

test("renderPage keeps analytics visuals explicit when no numeric z-scores can be drawn", () => {
  const appRoot = { innerHTML: "" };
  let heatmapCallCount = 0;
  let timelineCallCount = 0;

  renderPage(appRoot, buildAppState(buildSparseCountrySeries()), {
    chartRenderer: {
      renderIndicatorChart() {
        return "";
      },
      renderCountryAnalyticsHeatmap() {
        heatmapCallCount += 1;
        return "<div>unexpected heatmap</div>";
      },
      renderCountryAnalyticsTimeline() {
        timelineCallCount += 1;
        return "<div>unexpected timeline</div>";
      },
    },
  });

  assert.equal(heatmapCallCount, 0);
  assert.equal(timelineCallCount, 0);
  assertSectionDisclosureState(appRoot.innerHTML, { title: "Data analytics", variant: "country", open: false });
  assertSectionDisclosureState(appRoot.innerHTML, { title: "Forecast", variant: "country", open: false });
  assertSectionDisclosureState(appRoot.innerHTML, { title: "Analytics state summary", variant: "nested", open: false });
  assertSectionDisclosureState(appRoot.innerHTML, { title: "Per-indicator overrides", variant: "nested", open: false });
  assertSectionDisclosureState(appRoot.innerHTML, { title: "Raw z-score table", variant: "nested", open: false });
  assert.match(
    appRoot.innerHTML,
    /The current settings do not produce any numeric z-scores, so this heatmap is hidden instead of\s+showing an empty visual\./,
  );
  assert.match(
    appRoot.innerHTML,
    /The current settings do not produce any numeric z-scores, so this timeline is hidden instead of\s+showing an empty visual\./,
  );
  assert.doesNotMatch(appRoot.innerHTML, /browser recomputation/);
  assert.doesNotMatch(appRoot.innerHTML, /current controls/);
});

test("renderPage respects selector-provided disclosure open state for country analytics and indicators", () => {
  const appRoot = { innerHTML: "" };
  const appState = buildAppState(buildRenderableCountrySeries());
  appState.countryModels[0].uiState.countrySections.glossary.open = false;
  appState.countryModels[0].uiState.countrySections.forecast.open = false;
  appState.countryModels[0].uiState.analyticsSections.summary.open = true;
  appState.countryModels[0].uiState.indicatorDisclosures.inflation.open = true;
  appState.countryModels[0].uiState.indicatorDisclosures.inflation.rawDataOpen = true;

  renderPage(appRoot, appState, {
    chartRenderer: {
      renderIndicatorChart() {
        return "<div data-indicator-chart>Indicator chart</div>";
      },
      renderCountryAnalyticsHeatmap() {
        return "<div data-analytics-heatmap>heatmap</div>";
      },
      renderCountryAnalyticsTimeline() {
        return "<div data-analytics-timeline>timeline</div>";
      },
    },
  });

  assertSectionDisclosureState(appRoot.innerHTML, { title: "Indicator glossary", variant: "country", open: false });
  assertSectionDisclosureState(appRoot.innerHTML, { title: "Forecast", variant: "country", open: false });
  assertSectionDisclosureState(appRoot.innerHTML, { title: "Analytics state summary", variant: "nested", open: true });
  assertIndicatorDisclosureState(appRoot.innerHTML, { title: "Inflation", open: true });
  assert.match(
    appRoot.innerHTML,
    /<details class="indicator-raw-data" open>[\s\S]*?<summary[\s\S]*?class="indicator-raw-data__summary"[\s\S]*?aria-label="Toggle raw yearly rows"[\s\S]*?>/,
  );
});

test("renderPage fallback ui state keeps top-level country sections collapsed when selector state is absent", () => {
  const appRoot = { innerHTML: "" };
  const appState = buildAppState(buildRenderableCountrySeries());
  appState.countryModels[0].uiState = null;

  renderPage(appRoot, appState, {
    chartRenderer: {
      renderIndicatorChart() {
        return "<div data-indicator-chart>Indicator chart</div>";
      },
      renderCountryAnalyticsHeatmap() {
        return "<div data-analytics-heatmap>heatmap</div>";
      },
      renderCountryAnalyticsTimeline() {
        return "<div data-analytics-timeline>timeline</div>";
      },
    },
  });

  assertSectionDisclosureState(appRoot.innerHTML, { title: "Indicator glossary", variant: "country", open: false });
  assertSectionDisclosureState(appRoot.innerHTML, { title: "Data analytics", variant: "country", open: false });
  assertSectionDisclosureState(appRoot.innerHTML, { title: "Forecast", variant: "country", open: false });
  assertSectionDisclosureState(appRoot.innerHTML, { title: "Indicator charts", variant: "country", open: false });
  assertSectionDisclosureState(appRoot.innerHTML, { title: "Analytics state summary", variant: "nested", open: false });
});

test("renderPage derives the country header year range from emitted points when the top-level range is missing", () => {
  const appRoot = { innerHTML: "" };
  const appState = buildAppState(buildRenderableCountrySeries());
  appState.countryModels[0].normalizedSeries.year_range = null;

  renderPage(appRoot, appState, {
    chartRenderer: {
      renderIndicatorChart() {
        return "<div data-indicator-chart>Indicator chart</div>";
      },
      renderCountryAnalyticsHeatmap() {
        return "<div data-analytics-heatmap>heatmap</div>";
      },
      renderCountryAnalyticsTimeline() {
        return "<div data-analytics-timeline>timeline</div>";
      },
    },
  });

  assert.match(appRoot.innerHTML, /2 indicators • 2020-2023/);
  assert.doesNotMatch(appRoot.innerHTML, /Range unavailable/);
});

test("renderPage prefers emitted point coverage when the top-level country year range is inconsistent", () => {
  const appRoot = { innerHTML: "" };
  const appState = buildAppState(buildRenderableCountrySeries());
  appState.countryModels[0].normalizedSeries.year_range = {
    min_year: 1971,
    max_year: 2030,
  };

  renderPage(appRoot, appState, {
    chartRenderer: {
      renderIndicatorChart() {
        return "<div data-indicator-chart>Indicator chart</div>";
      },
      renderCountryAnalyticsHeatmap() {
        return "<div data-analytics-heatmap>heatmap</div>";
      },
      renderCountryAnalyticsTimeline() {
        return "<div data-analytics-timeline>timeline</div>";
      },
    },
  });

  assert.match(appRoot.innerHTML, /2 indicators • 2020-2023/);
  assert.doesNotMatch(appRoot.innerHTML, /2 indicators • 1971-2030/);
});

test("renderPage keeps forecast states honest when forecast payload loading failed", () => {
  const appRoot = { innerHTML: "" };
  const appState = buildAppState(buildRenderableCountrySeries());
  appState.countryModels[0].forecast = null;
  appState.countryModels[0].forecastLoadError = "Request failed for /data/LT/forecast.json with 404";

  renderPage(appRoot, appState, {
    chartRenderer: {
      renderIndicatorChart() {
        return "<div data-indicator-chart>Indicator chart</div>";
      },
      renderCountryAnalyticsHeatmap() {
        return "<div data-analytics-heatmap>heatmap</div>";
      },
      renderCountryAnalyticsTimeline() {
        return "<div data-analytics-timeline>timeline</div>";
      },
    },
  });

  assertSectionDisclosureState(appRoot.innerHTML, { title: "Forecast", variant: "country", open: false });
  assert.match(appRoot.innerHTML, /Forecast unavailable/);
  assert.match(appRoot.innerHTML, /Forecast data is temporarily unavailable for this country/);
  assert.match(appRoot.innerHTML, /Indicator charts/);
});

test("renderPage passes only unit-compatible raw-level forecasts into the indicator chart seam", () => {
  const appRoot = { innerHTML: "" };
  const appState = buildAppState(buildRenderableCountrySeries());
  const chartCalls = [];

  appState.countryModels[0].forecast = {
    country_code: "LT",
    status: "ready",
    row_count: 2,
    rows: [
      {
        indicator_id: "inflation",
        indicator_label: "Inflation | Test source",
        forecast_year: 2024,
        forecast_value: 3.5,
        forecast_unit: "percent",
        selected_candidate: "inflation__none__lag1",
      },
      {
        indicator_id: "gdp",
        indicator_label: "GDP | Test source",
        forecast_year: 2024,
        forecast_value: 2.5,
        forecast_unit: "pct",
        selected_candidate: "gdp__pct_change_yoy__lag1",
      },
    ],
  };

  renderPage(appRoot, appState, {
    chartRenderer: {
      renderIndicatorChart(context) {
        chartCalls.push(context);
        return `<div data-indicator-chart="${context.indicatorViewModel.indicatorId}">Indicator chart</div>`;
      },
      renderCountryAnalyticsHeatmap() {
        return "<div data-analytics-heatmap>heatmap</div>";
      },
      renderCountryAnalyticsTimeline() {
        return "<div data-analytics-timeline>timeline</div>";
      },
    },
  });

  assert.equal(chartCalls.length, 2);
  assert.deepEqual(chartCalls[0].forecastOverlay, {
    forecastYear: 2024,
    forecastValue: 3.5,
    forecastUnit: "percent",
    indicatorId: "inflation",
    indicatorLabel: "Inflation | Test source",
    selectedCandidate: "inflation__none__lag1",
    transformMethod: "none",
  });
  assert.equal(chartCalls[1].forecastOverlay, null);
  assert.equal(chartCalls[0].forecastChartDisclosure, null);
  assert.deepEqual(chartCalls[1].forecastChartDisclosure, {
    indicatorId: "gdp",
    indicatorLabel: "GDP | Test source",
    forecastYear: 2024,
    forecastUnit: "pct",
    transformMethod: "pct_change_yoy",
    message:
      "CCOutline forecast available in Forecast section and not plotted here because it is shown as a yearly change rather than in the chart's raw units.",
  });
});

test("renderPage keeps the active global controls aligned to the current analytics state while still showing the published baseline", () => {
  const appRoot = { innerHTML: "" };

  renderPage(appRoot, buildAppState(buildRenderableCountrySeries()), {
    chartRenderer: {
      renderIndicatorChart() {
        return "<div data-indicator-chart>Indicator chart</div>";
      },
      renderCountryAnalyticsHeatmap() {
        return "<div data-analytics-heatmap>heatmap</div>";
      },
      renderCountryAnalyticsTimeline() {
        return "<div data-analytics-timeline>timeline</div>";
      },
    },
  });

  assert.doesNotMatch(
    appRoot.innerHTML,
    /<input[^>]*id="LT-global-rollingWindowYears"[^>]*data-analytics-global-control="rollingWindowYears"[^>]*disabled[^>]*\/>/,
  );
  assert.doesNotMatch(
    appRoot.innerHTML,
    /<input[^>]*id="LT-global-minObsForZscore"[^>]*data-analytics-global-control="minObsForZscore"[^>]*disabled[^>]*\/>/,
  );
  assert.match(appRoot.innerHTML, /minimum observations stays visible but disabled/i);
  assert.match(appRoot.innerHTML, /Modified from published settings/);
  assert.match(appRoot.innerHTML, /Rolling trailing, 10y, exclude current, min obs 3/);
  assert.match(appRoot.innerHTML, /Static baseline from 2020<\/td>/);
  assert.doesNotMatch(appRoot.innerHTML, /Static baseline from 2020, min obs/);
});

test("renderPage keeps the global rolling-window control enabled in rolling-trailing mode", () => {
  const appRoot = { innerHTML: "" };
  const series = buildRenderableCountrySeries();
  series.normalization.mode = "rolling_trailing";
  series.normalization.summary_text = "Rolling trailing, 10y, exclude current, min obs 3";

  renderPage(appRoot, buildAppState(series), {
    chartRenderer: {
      renderIndicatorChart() {
        return "<div data-indicator-chart>Indicator chart</div>";
      },
      renderCountryAnalyticsHeatmap() {
        return "<div data-analytics-heatmap>heatmap</div>";
      },
      renderCountryAnalyticsTimeline() {
        return "<div data-analytics-timeline>timeline</div>";
      },
    },
  });

  assert.doesNotMatch(
    appRoot.innerHTML,
    /<input[^>]*id="LT-global-rollingWindowYears"[^>]*data-analytics-global-control="rollingWindowYears"[^>]*disabled[^>]*\/>/,
  );
  assert.doesNotMatch(
    appRoot.innerHTML,
    /<input[^>]*id="LT-global-minObsForZscore"[^>]*data-analytics-global-control="minObsForZscore"[^>]*disabled[^>]*\/>/,
  );
});

test("renderPage applies the same mode-aware disablement rule to override controls", () => {
  const appRoot = { innerHTML: "" };

  renderPage(appRoot, buildAppState(buildRenderableCountrySeriesWithOverride()), {
    chartRenderer: {
      renderIndicatorChart() {
        return "<div data-indicator-chart>Indicator chart</div>";
      },
      renderCountryAnalyticsHeatmap() {
        return "<div data-analytics-heatmap>heatmap</div>";
      },
      renderCountryAnalyticsTimeline() {
        return "<div data-analytics-timeline>timeline</div>";
      },
    },
  });

  assert.match(
    appRoot.innerHTML,
    /<input[^>]*id="LT-inflation-rollingWindowYears"[^>]*data-analytics-override-control="rollingWindowYears"[^>]*data-indicator-id="inflation"[^>]*disabled[^>]*\/>/,
  );
  assert.match(
    appRoot.innerHTML,
    /<input[^>]*id="LT-inflation-minObsForZscore"[^>]*data-analytics-override-control="minObsForZscore"[^>]*data-indicator-id="inflation"[^>]*disabled[^>]*\/>/,
  );

  const rollingOverrideRoot = { innerHTML: "" };
  renderPage(
    rollingOverrideRoot,
    buildAppState(buildRenderableCountrySeriesWithOverride({ mode: "rolling_trailing" })),
    {
      chartRenderer: {
        renderIndicatorChart() {
          return "<div data-indicator-chart>Indicator chart</div>";
        },
        renderCountryAnalyticsHeatmap() {
          return "<div data-analytics-heatmap>heatmap</div>";
        },
        renderCountryAnalyticsTimeline() {
          return "<div data-analytics-timeline>timeline</div>";
        },
      },
    },
  );

  assert.doesNotMatch(
    rollingOverrideRoot.innerHTML,
    /<input[^>]*id="LT-inflation-rollingWindowYears"[^>]*data-analytics-override-control="rollingWindowYears"[^>]*data-indicator-id="inflation"[^>]*disabled[^>]*\/>/,
  );
  assert.doesNotMatch(
    rollingOverrideRoot.innerHTML,
    /<input[^>]*id="LT-inflation-minObsForZscore"[^>]*data-analytics-override-control="minObsForZscore"[^>]*data-indicator-id="inflation"[^>]*disabled[^>]*\/>/,
  );
});
