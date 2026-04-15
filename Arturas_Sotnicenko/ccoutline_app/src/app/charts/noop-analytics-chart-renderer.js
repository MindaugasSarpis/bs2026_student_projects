export function createNoopAnalyticsChartRenderer() {
  return {
    renderCountryAnalyticsHeatmap() {
      return "";
    },
    renderCountryAnalyticsTimeline() {
      return "";
    },
  };
}
