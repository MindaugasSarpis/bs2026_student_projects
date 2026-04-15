import * as d3 from "d3";

import { escapeAttribute, escapeHtml } from "../shared/html.js";

export function createD3IndicatorChartRenderer({ fallbackIndicatorChartRenderer } = {}) {
  const fallback =
    fallbackIndicatorChartRenderer && typeof fallbackIndicatorChartRenderer.renderIndicatorChart === "function"
      ? fallbackIndicatorChartRenderer
      : null;

  return {
    renderIndicatorChart(context) {
      try {
        return renderD3IndicatorChart(context);
      } catch (error) {
        if (fallback) {
          return fallback.renderIndicatorChart(context);
        }
        return "";
      }
    },
  };
}

function renderD3IndicatorChart({ indicatorViewModel, forecastOverlay: rawForecastOverlay }) {
  const numericPoints = Array.isArray(indicatorViewModel?.plottedPoints)
    ? [...indicatorViewModel.plottedPoints]
        .filter((point) => Number.isFinite(point?.year) && Number.isFinite(point?.value))
        .sort((left, right) => left.year - right.year)
    : [];
  if (numericPoints.length < 2) {
    return "";
  }
  const forecastOverlay = normalizeForecastOverlay(rawForecastOverlay);
  const forecastChartDisclosure = normalizeForecastChartDisclosure(arguments[0]?.forecastChartDisclosure);
  const domainPoints = forecastOverlay
    ? [...numericPoints, { year: forecastOverlay.forecastYear, value: forecastOverlay.forecastValue }]
    : numericPoints;
  const observedPoints = numericPoints.filter((point) => point?.is_projection !== true);
  const projectedPoints = numericPoints.filter((point) => point?.is_projection === true);
  const nonOkPoints = numericPoints.filter((point) => String(point?.status || "").toLowerCase() !== "ok");

  const chartWidth = 720;
  const chartHeight = 240;
  const margin = {
    top: 28,
    right: 20,
    bottom: 44,
    left: 60,
  };
  const plotWidth = chartWidth - margin.left - margin.right;
  const plotHeight = chartHeight - margin.top - margin.bottom;
  const xDomain = d3.extent(domainPoints, (point) => point.year);
  const yDomain = buildValueDomain(domainPoints);
  const xScale = d3.scaleLinear().domain(xDomain).range([margin.left, margin.left + plotWidth]);
  const yScale = d3.scaleLinear().domain(yDomain).range([margin.top + plotHeight, margin.top]);
  const yTicks = yScale.ticks(4);
  const xTickCount = Math.min(6, numericPoints.length);
  const xTicks = xScale.ticks(xTickCount).filter((tick) => Number.isInteger(tick));
  const line = d3
    .line()
    .defined((point) => Number.isFinite(point.year) && Number.isFinite(point.value))
    .x((point) => xScale(point.year))
    .y((point) => yScale(point.value));

  const figure = d3.create("figure").attr("class", "indicator-chart").attr("data-chart-adapter", "d3");
  const figureTitle = String(indicatorViewModel?.title || indicatorViewModel?.indicatorLabel || "Indicator chart");
  const svg = figure
    .append("svg")
    .attr("viewBox", `0 0 ${chartWidth} ${chartHeight}`)
    .attr("role", "img")
    .attr("aria-label", figureTitle)
    .attr("preserveAspectRatio", "xMidYMid meet");

  svg
    .append("rect")
    .attr("x", 0)
    .attr("y", 0)
    .attr("width", chartWidth)
    .attr("height", chartHeight)
    .attr("fill", "#fafafa")
    .attr("stroke", "#000000");

  svg
    .append("text")
    .attr("class", "indicator-chart__title")
    .attr("x", margin.left)
    .attr("y", 18)
    .attr("font-size", 13)
    .attr("font-weight", 700)
    .text(figureTitle);

  const gridGroup = svg.append("g").attr("class", "indicator-chart__grid");
  gridGroup
    .selectAll("line")
    .data(yTicks)
    .join("line")
    .attr("x1", margin.left)
    .attr("x2", margin.left + plotWidth)
    .attr("y1", (tick) => yScale(tick))
    .attr("y2", (tick) => yScale(tick))
    .attr("stroke", "#d5d5d5")
    .attr("stroke-width", 1);

  const xAxisGroup = svg.append("g").attr("class", "indicator-chart__x-axis");
  xAxisGroup
    .append("line")
    .attr("x1", margin.left)
    .attr("x2", margin.left + plotWidth)
    .attr("y1", margin.top + plotHeight)
    .attr("y2", margin.top + plotHeight)
    .attr("stroke", "#000000");

  xAxisGroup
    .selectAll("line.indicator-chart__x-tick")
    .data(xTicks)
    .join("line")
    .attr("class", "indicator-chart__x-tick")
    .attr("x1", (tick) => xScale(tick))
    .attr("x2", (tick) => xScale(tick))
    .attr("y1", margin.top + plotHeight)
    .attr("y2", margin.top + plotHeight + 6)
    .attr("stroke", "#000000");

  xAxisGroup
    .selectAll("text.indicator-chart__x-label")
    .data(xTicks)
    .join("text")
    .attr("class", "indicator-chart__x-label")
    .attr("x", (tick) => xScale(tick))
    .attr("y", margin.top + plotHeight + 20)
    .attr("font-size", 11)
    .attr("text-anchor", "middle")
    .text((tick) => String(tick));

  const yAxisGroup = svg.append("g").attr("class", "indicator-chart__y-axis");
  yAxisGroup
    .append("line")
    .attr("x1", margin.left)
    .attr("x2", margin.left)
    .attr("y1", margin.top)
    .attr("y2", margin.top + plotHeight)
    .attr("stroke", "#000000");

  yAxisGroup
    .selectAll("line.indicator-chart__y-tick")
    .data(yTicks)
    .join("line")
    .attr("class", "indicator-chart__y-tick")
    .attr("x1", margin.left - 6)
    .attr("x2", margin.left)
    .attr("y1", (tick) => yScale(tick))
    .attr("y2", (tick) => yScale(tick))
    .attr("stroke", "#000000");

  yAxisGroup
    .selectAll("text.indicator-chart__y-label")
    .data(yTicks)
    .join("text")
    .attr("class", "indicator-chart__y-label")
    .attr("x", margin.left - 10)
    .attr("y", (tick) => yScale(tick) + 4)
    .attr("font-size", 11)
    .attr("text-anchor", "end")
    .text((tick) => formatTickValue(tick));

  const observedLinePoints = observedPoints.length ? observedPoints : numericPoints;
  svg
    .append("path")
    .attr("d", line(observedLinePoints))
    .attr("fill", "none")
    .attr("stroke", "#000000")
    .attr("stroke-width", 2);

  if (projectedPoints.length) {
    const projectedLinePoints = [...observedPoints.slice(-1), ...projectedPoints].filter(Boolean);
    svg
      .append("path")
      .attr("d", line(projectedLinePoints))
      .attr("fill", "none")
      .attr("stroke", "#666666")
      .attr("stroke-dasharray", "6 4")
      .attr("stroke-width", 2);
  }

  if (forecastOverlay) {
    const forecastAnchorPoint = numericPoints[numericPoints.length - 1];
    const forecastLinePoints = [forecastAnchorPoint, { year: forecastOverlay.forecastYear, value: forecastOverlay.forecastValue }];
    const forecastGroup = svg.append("g").attr("class", "indicator-chart__forecast").attr("data-chart-forecast", "true");

    forecastGroup
      .append("path")
      .attr("class", "indicator-chart__forecast-line")
      .attr("d", line(forecastLinePoints))
      .attr("fill", "none")
      .attr("stroke", "#005a9c")
      .attr("stroke-dasharray", "3 4")
      .attr("stroke-width", 2);

    forecastGroup
      .append("rect")
      .attr("class", "indicator-chart__forecast-marker")
      .attr("x", xScale(forecastOverlay.forecastYear) - 4)
      .attr("y", yScale(forecastOverlay.forecastValue) - 4)
      .attr("width", 8)
      .attr("height", 8)
      .attr("fill", "#005a9c")
      .attr(
        "transform",
        `rotate(45 ${xScale(forecastOverlay.forecastYear)} ${yScale(forecastOverlay.forecastValue)})`,
      );
  }

  svg
    .append("g")
    .attr("class", "indicator-chart__points")
    .selectAll("circle")
    .data(numericPoints)
    .join("circle")
    .attr("cx", (point) => xScale(point.year))
    .attr("cy", (point) => yScale(point.value))
    .attr("r", 2.75)
    .attr("fill", (point) => (point?.is_projection === true ? "#ffffff" : "#000000"))
    .attr("stroke", (point) =>
      String(point?.status || "").toLowerCase() === "ok" ? "#000000" : "#b00020",
    )
    .attr("stroke-width", (point) => (point?.is_projection === true ? 1.5 : 1.25));

  if (projectedPoints.length || nonOkPoints.length || forecastOverlay) {
    const legendItems = buildLegendItems({ projectedPoints, nonOkPoints, forecastOverlay });
    const legendGroup = svg.append("g").attr("class", "indicator-chart__legend");
    const legendStartX = margin.left + plotWidth - legendItems.length * 92;
    const legendY = 18;

    legendItems.forEach((item, index) => {
      const itemX = legendStartX + index * 92;

      if (item.kind === "projection") {
        legendGroup
          .append("line")
          .attr("x1", itemX)
          .attr("x2", itemX + 20)
          .attr("y1", legendY)
          .attr("y2", legendY)
          .attr("stroke", "#666666")
          .attr("stroke-dasharray", "6 4")
          .attr("stroke-width", 2);

        legendGroup
          .append("circle")
          .attr("cx", itemX + 10)
          .attr("cy", legendY)
          .attr("r", 3)
          .attr("fill", "#ffffff")
          .attr("stroke", "#000000")
          .attr("stroke-width", 1.5);
      }

      if (item.kind === "status") {
        legendGroup
          .append("circle")
          .attr("cx", itemX + 10)
          .attr("cy", legendY)
          .attr("r", 3)
          .attr("fill", "#ffffff")
          .attr("stroke", "#b00020")
          .attr("stroke-width", 1.5);
      }

      if (item.kind === "forecast") {
        legendGroup
          .append("line")
          .attr("x1", itemX)
          .attr("x2", itemX + 20)
          .attr("y1", legendY)
          .attr("y2", legendY)
          .attr("stroke", "#005a9c")
          .attr("stroke-dasharray", "3 4")
          .attr("stroke-width", 2);

        legendGroup
          .append("rect")
          .attr("x", itemX + 6)
          .attr("y", legendY - 4)
          .attr("width", 8)
          .attr("height", 8)
          .attr("fill", "#005a9c")
          .attr("transform", `rotate(45 ${itemX + 10} ${legendY})`);
      }

      legendGroup
        .append("text")
        .attr("class", "indicator-chart__legend-label")
        .attr("x", itemX + 26)
        .attr("y", legendY + 4)
        .attr("font-size", 11)
        .text(item.label);
    });
  }

  svg
    .append("text")
    .attr("class", "indicator-chart__footer")
    .attr("x", margin.left)
    .attr("y", chartHeight - 8)
    .attr("font-size", 12)
    .text(`${numericPoints.length} plotted yearly points`);

  const unitText = String(indicatorViewModel?.unit || "Unit unavailable");
  const firstYear = numericPoints[0]?.year;
  const lastYear = numericPoints[numericPoints.length - 1]?.year;
  const contextLabels = buildChartContextLabels({ projectedPoints, nonOkPoints, forecastOverlay, forecastChartDisclosure });
  const subtitle = figure
    .append("figcaption")
    .attr("class", "indicator-chart__caption")
    .html(
      `${escapeHtml(unitText)} <span aria-hidden="true">&bull;</span> ${escapeHtml(
        `${firstYear}-${lastYear}`,
      )}${contextLabels.length ? ` <span aria-hidden="true">&bull;</span> ${escapeHtml(contextLabels.join(", "))}` : ""}`,
    );

  void subtitle;
  return figure.node().outerHTML;
}

function buildValueDomain(points) {
  const values = points.map((point) => point.value).filter((value) => Number.isFinite(value));
  const minValue = Math.min(...values);
  const maxValue = Math.max(...values);

  if (minValue === maxValue) {
    const padding = Math.abs(minValue || 1) * 0.05 || 1;
    return [minValue - padding, maxValue + padding];
  }

  const spread = maxValue - minValue;
  const padding = spread * 0.08;
  return [minValue - padding, maxValue + padding];
}

function formatTickValue(value) {
  if (!Number.isFinite(value)) {
    return "";
  }

  return new Intl.NumberFormat("en-US", {
    maximumFractionDigits: 2,
  }).format(value);
}

function buildLegendItems({ projectedPoints, nonOkPoints, forecastOverlay }) {
  const items = [];

  if (projectedPoints.length) {
    items.push({
      kind: "projection",
      label: "Projected",
    });
  }

  if (nonOkPoints.length) {
    items.push({
      kind: "status",
      label: "Status flag",
    });
  }

  if (forecastOverlay) {
    items.push({
      kind: "forecast",
      label: "CCOutline forecast",
    });
  }

  return items;
}

function buildChartContextLabels({ projectedPoints, nonOkPoints, forecastOverlay, forecastChartDisclosure }) {
  const contextLabels = [];

  if (projectedPoints.length) {
    contextLabels.push(`${projectedPoints.length} projected`);
  }
  if (nonOkPoints.length) {
    contextLabels.push(`${nonOkPoints.length} non-ok status`);
  }
  if (forecastOverlay) {
    contextLabels.push(`CCOutline forecast for ${forecastOverlay.forecastYear}`);
  }
  if (forecastChartDisclosure?.message) {
    contextLabels.push(forecastChartDisclosure.message);
  }

  return contextLabels;
}

function normalizeForecastOverlay(forecastOverlay) {
  if (!forecastOverlay || typeof forecastOverlay !== "object") {
    return null;
  }

  return Number.isFinite(forecastOverlay.forecastYear) && Number.isFinite(forecastOverlay.forecastValue)
    ? {
        forecastYear: forecastOverlay.forecastYear,
        forecastValue: forecastOverlay.forecastValue,
      }
    : null;
}

function normalizeForecastChartDisclosure(forecastChartDisclosure) {
  if (!forecastChartDisclosure || typeof forecastChartDisclosure !== "object") {
    return null;
  }

  const message = String(forecastChartDisclosure.message || "").trim();
  return message ? { message } : null;
}

export const __test__ = {
  buildChartContextLabels,
  buildLegendItems,
};
