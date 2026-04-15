export function createNoopIndicatorChartRenderer() {
  return {
    renderIndicatorChart({ indicatorViewModel }) {
      void indicatorViewModel;
      return "";
    },
  };
}
