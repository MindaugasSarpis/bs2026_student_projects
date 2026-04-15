export function createChartRendererFacade({ indicatorChartRenderer, analyticsChartRenderer }) {
  if (!indicatorChartRenderer || typeof indicatorChartRenderer.renderIndicatorChart !== "function") {
    throw new Error("indicatorChartRenderer must expose renderIndicatorChart(...).");
  }
  if (
    !analyticsChartRenderer ||
    typeof analyticsChartRenderer.renderCountryAnalyticsHeatmap !== "function" ||
    typeof analyticsChartRenderer.renderCountryAnalyticsTimeline !== "function"
  ) {
    throw new Error(
      "analyticsChartRenderer must expose renderCountryAnalyticsHeatmap(...) and renderCountryAnalyticsTimeline(...).",
    );
  }

  return {
    renderIndicatorChart(context) {
      return indicatorChartRenderer.renderIndicatorChart(context);
    },
    renderCountryAnalyticsHeatmap(context) {
      return analyticsChartRenderer.renderCountryAnalyticsHeatmap(context);
    },
    renderCountryAnalyticsTimeline(context) {
      return analyticsChartRenderer.renderCountryAnalyticsTimeline(context);
    },
  };
}
