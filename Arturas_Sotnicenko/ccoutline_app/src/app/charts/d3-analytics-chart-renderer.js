import * as d3 from "d3";

import { escapeHtml } from "../shared/html.js";

const HEATMAP_CELL_WIDTH = 28;
const HEATMAP_CELL_HEIGHT = 24;
const HEATMAP_MAX_VISIBLE_YEAR_LABELS = 24;
const TIMELINE_DEFAULT_HIGHLIGHT_COUNT = 3;
const TIMELINE_ACCENT_PALETTE = Object.freeze([
  "#0b7285",
  "#b02a37",
  "#2b8a3e",
  "#6c5ce7",
  "#c77d08",
  "#1c7ed6",
  "#d9480f",
  "#5f3dc4",
  "#2f9e44",
  "#a61e4d",
]);

export function createD3AnalyticsChartRenderer({ fallbackAnalyticsChartRenderer } = {}) {
  const fallback =
    fallbackAnalyticsChartRenderer &&
    typeof fallbackAnalyticsChartRenderer.renderCountryAnalyticsHeatmap === "function" &&
    typeof fallbackAnalyticsChartRenderer.renderCountryAnalyticsTimeline === "function"
      ? fallbackAnalyticsChartRenderer
      : null;

  return {
    renderCountryAnalyticsHeatmap(context) {
      try {
        return renderCountryAnalyticsHeatmap(context);
      } catch (error) {
        if (fallback) {
          return fallback.renderCountryAnalyticsHeatmap(context);
        }
        return "";
      }
    },
    renderCountryAnalyticsTimeline(context) {
      try {
        return renderCountryAnalyticsTimeline(context);
      } catch (error) {
        if (fallback) {
          return fallback.renderCountryAnalyticsTimeline(context);
        }
        return "";
      }
    },
  };
}

function renderCountryAnalyticsHeatmap({ analyticsState }) {
  const heatmap = analyticsState?.rendering?.heatmap;
  const years = Array.isArray(heatmap?.years) ? heatmap.years.filter((year) => Number.isFinite(year)) : [];
  const rows = Array.isArray(heatmap?.rows) ? heatmap.rows.filter((row) => row && typeof row === "object") : [];

  if (!heatmap?.hasRenderableCells || !years.length || !rows.length) {
    return "";
  }

  const renderableValues = rows.flatMap((row) =>
    Array.isArray(row.cells) ? row.cells.map((cell) => cell?.zscore).filter((value) => Number.isFinite(value)) : [],
  );
  const maxAbsZscore = Math.max(1, ...renderableValues.map((value) => Math.abs(value)));
  const colorScale = d3
    .scaleDiverging()
    .domain([-maxAbsZscore, 0, maxAbsZscore])
    .interpolator(d3.interpolateRgbBasis(["#2166ac", "#f7f3eb", "#b2182b"]));

  const layout = buildHeatmapLayoutModel({ yearCount: years.length, rowCount: rows.length });
  const chartWidth = layout.chartWidth;
  const chartHeight = layout.chartHeight;
  const figureIdPrefix = String(analyticsState?.countryCode || "country").toLowerCase();
  const titleId = `${figureIdPrefix}-analytics-heatmap-title`;
  const descId = `${figureIdPrefix}-analytics-heatmap-desc`;

  const figure = d3
    .create("figure")
    .attr("class", "analytics-chart analytics-chart--heatmap")
    .attr("data-chart-adapter", "d3")
    .attr("data-analytics-heatmap", "true")
    .attr("data-year-label-step", String(layout.yearLabelStep))
    .attr("data-grid-start-y", String(layout.gridStartY));
  const svg = figure
    .append("svg")
    .attr("viewBox", `0 0 ${chartWidth} ${chartHeight}`)
    .attr("role", "img")
    .attr("aria-labelledby", titleId)
    .attr("aria-describedby", descId)
    .attr("preserveAspectRatio", "xMidYMid meet");

  svg
    .append("rect")
    .attr("x", 0)
    .attr("y", 0)
    .attr("width", chartWidth)
    .attr("height", chartHeight)
    .attr("fill", "#ffffff")
    .attr("stroke", "#d9d9d9");

  svg
    .append("text")
    .attr("id", titleId)
    .attr("class", "analytics-chart__title")
    .attr("x", layout.margin.left)
    .attr("y", 24)
    .attr("font-size", 16)
    .attr("font-weight", 700)
    .text("Country z-score heatmap");

  svg
    .append("desc")
    .attr("id", descId)
    .text(
      `${analyticsState?.displayName || analyticsState?.countryCode || "Country"} heatmap with ${rows.length} indicators across ${years.length} years. Color shows z-score intensity and gray cells indicate no numeric z-score under the current settings.`,
    );

  svg
    .append("text")
    .attr("class", "analytics-chart__subtitle")
    .attr("x", layout.margin.left)
    .attr("y", 46)
    .attr("font-size", 12)
    .text(`${heatmap.rows.length} indicators x ${years.length} years`);

  const legend = svg.append("g").attr("class", "analytics-chart__legend");
  const legendValues = [-maxAbsZscore, -maxAbsZscore / 2, 0, maxAbsZscore / 2, maxAbsZscore];
  legendValues.forEach((value, index) => {
    const offsetX = layout.margin.left + index * 70;
    legend
      .append("rect")
      .attr("x", offsetX)
      .attr("y", 58)
      .attr("width", 24)
      .attr("height", 12)
      .attr("fill", colorScale(value))
      .attr("stroke", "#999999");
    legend
      .append("text")
      .attr("class", "analytics-chart__legend-label")
      .attr("x", offsetX + 30)
      .attr("y", 68)
      .attr("font-size", 11)
      .text(formatSignedTick(value));
  });

  svg
    .append("line")
    .attr("class", "analytics-chart__heatmap-axis")
    .attr("x1", layout.margin.left)
    .attr("x2", layout.margin.left + layout.plotWidth)
    .attr("y1", layout.gridStartY - 6)
    .attr("y2", layout.gridStartY - 6)
    .attr("stroke", "#b8b8b8");

  years.forEach((year, index) => {
    if (!shouldRenderHeatmapYearLabel(index, years.length, layout.yearLabelStep)) {
      return;
    }

    const cellX = layout.margin.left + index * HEATMAP_CELL_WIDTH;
    svg
      .append("text")
      .attr("class", "analytics-chart__x-label")
      .attr("x", cellX + HEATMAP_CELL_WIDTH / 2)
      .attr("y", layout.yearLabelBaselineY)
      .attr("font-size", 11)
      .attr("text-anchor", "end")
      .attr("transform", `rotate(-45, ${cellX + HEATMAP_CELL_WIDTH / 2}, ${layout.yearLabelBaselineY})`)
      .text(String(year));
  });

  rows.forEach((row, rowIndex) => {
    const rowY = layout.gridStartY + rowIndex * HEATMAP_CELL_HEIGHT;
    svg
      .append("text")
      .attr("class", "analytics-chart__y-label")
      .attr("x", layout.margin.left - 10)
      .attr("y", rowY + HEATMAP_CELL_HEIGHT / 2 + 4)
      .attr("font-size", 11)
      .attr("text-anchor", "end")
      .text(truncateLabel(row.indicatorLabel, 28));

    row.cells.forEach((cell, cellIndex) => {
      const cellX = layout.margin.left + cellIndex * HEATMAP_CELL_WIDTH;
      const fill = cell?.hasValue ? colorScale(cell.zscore) : "#f1f1f1";
      const rect = svg
        .append("rect")
        .attr("x", cellX)
        .attr("y", rowY)
        .attr("width", HEATMAP_CELL_WIDTH - 2)
        .attr("height", HEATMAP_CELL_HEIGHT - 2)
        .attr("fill", fill)
        .attr("stroke", cell?.hasValue ? "#ffffff" : "#cccccc")
        .attr("stroke-width", 1);

      if (cell?.isProjection) {
        rect.attr("stroke", "#555555").attr("stroke-dasharray", "3 2");
      }

      const title = [
        row.indicatorLabel || "Indicator",
        String(cell?.year || ""),
        cell?.hasValue ? `z-score ${formatSignedTick(cell.zscore)}` : "Unavailable under current settings",
        cell?.isProjection ? "Projected value" : "",
      ]
        .filter((part) => Boolean(part))
        .join(" | ");

      rect.append("title").text(title);
    });
  });

  figure
    .append("figcaption")
    .attr("class", "analytics-chart__caption")
    .html(
      `${escapeHtml(`Current analytics setting: ${analyticsState?.defaultSummaryText || "Unavailable"}.`)} <span aria-hidden="true">&bull;</span> Cooler colors mark lower z-scores and warmer colors mark higher z-scores. <span aria-hidden="true">&bull;</span> Gray cells mean no numeric z-score under the current settings.`,
    );

  return figure.node().outerHTML;
}

function buildHeatmapLayoutModel({ yearCount, rowCount }) {
  const margin = {
    top: 98,
    right: 24,
    bottom: 32,
    left: 220,
  };
  const yearLabelStep = deriveHeatmapYearLabelStep(yearCount);
  const plotWidth = yearCount * HEATMAP_CELL_WIDTH;
  const gridStartY = margin.top;
  const yearLabelBaselineY = gridStartY - 18;

  return {
    margin,
    chartWidth: margin.left + plotWidth + margin.right,
    chartHeight: margin.top + rowCount * HEATMAP_CELL_HEIGHT + margin.bottom,
    gridStartY,
    plotWidth,
    yearLabelBaselineY,
    yearLabelStep,
  };
}

function deriveHeatmapYearLabelStep(yearCount) {
  if (!Number.isFinite(yearCount) || yearCount <= 0) {
    return 1;
  }

  return Math.max(1, Math.ceil(yearCount / HEATMAP_MAX_VISIBLE_YEAR_LABELS));
}

function shouldRenderHeatmapYearLabel(index, yearCount, yearLabelStep) {
  if (!Number.isFinite(index) || index < 0 || !Number.isFinite(yearCount) || yearCount <= 0) {
    return false;
  }

  if (index === 0 || index === yearCount - 1) {
    return true;
  }

  return index % Math.max(1, yearLabelStep) === 0;
}

function renderCountryAnalyticsTimeline({ analyticsState }) {
  const timelines = analyticsState?.rendering?.timelines;
  const renderableSeries = Array.isArray(timelines?.series)
    ? timelines.series
        .map((series) => ({
          indicatorId: series?.indicatorId || "",
          indicatorLabel: series?.indicatorLabel || series?.indicatorId || "Indicator",
          points: Array.isArray(series?.points)
            ? series.points.filter((point) => Number.isFinite(point?.year) && Number.isFinite(point?.zscore))
            : [],
        }))
        .filter((series) => series.points.length > 0)
    : [];

  if (!timelines?.hasRenderableSeries || !renderableSeries.length) {
    return "";
  }

  const seriesModels = buildTimelineSeriesModels(renderableSeries);
  const defaultHighlightedIds = deriveTimelinePersistentSeriesIds(seriesModels);
  const allPoints = seriesModels.flatMap((series) => series.points);
  const xDomain = d3.extent(allPoints, (point) => point.year);
  const maxAbsZscore = Math.max(1, ...allPoints.map((point) => Math.abs(point.zscore)));

  const chartWidth = 860;
  const chartHeight = 320;
  const figureIdPrefix = String(analyticsState?.countryCode || "country").toLowerCase();
  const titleId = `${figureIdPrefix}-analytics-timeline-title`;
  const descId = `${figureIdPrefix}-analytics-timeline-desc`;
  const tooltipId = `${figureIdPrefix}-analytics-timeline-tooltip`;
  const margin = {
    top: 44,
    right: 24,
    bottom: 44,
    left: 56,
  };
  const plotWidth = chartWidth - margin.left - margin.right;
  const plotHeight = chartHeight - margin.top - margin.bottom;
  const xScale = d3.scaleLinear().domain(xDomain).range([margin.left, margin.left + plotWidth]);
  const yScale = d3.scaleLinear().domain([-maxAbsZscore, maxAbsZscore]).range([margin.top + plotHeight, margin.top]);
  const xTicks = xScale.ticks(Math.min(8, allPoints.length)).filter((tick) => Number.isInteger(tick));
  const yTicks = yScale.ticks(5);
  const line = d3
    .line()
    .defined((point) => Number.isFinite(point.year) && Number.isFinite(point.zscore))
    .x((point) => xScale(point.year))
    .y((point) => yScale(point.zscore));

  const figure = d3
    .create("figure")
    .attr("class", "analytics-chart analytics-chart--timeline")
    .attr("data-chart-adapter", "d3")
    .attr("data-analytics-timeline", "true")
    .attr("data-country-code", analyticsState?.countryCode || "")
    .attr("data-default-highlight-count", String(defaultHighlightedIds.size))
    .attr("data-year-min", String(xDomain[0]))
    .attr("data-year-max", String(xDomain[1]))
    .attr("data-plot-left", String(margin.left))
    .attr("data-plot-width", String(plotWidth))
    .attr("data-tooltip-id", tooltipId);
  const svg = figure
    .append("svg")
    .attr("viewBox", `0 0 ${chartWidth} ${chartHeight}`)
    .attr("role", "img")
    .attr("aria-labelledby", titleId)
    .attr("aria-describedby", descId)
    .attr("preserveAspectRatio", "xMidYMid meet");

  svg
    .append("rect")
    .attr("x", 0)
    .attr("y", 0)
    .attr("width", chartWidth)
    .attr("height", chartHeight)
    .attr("fill", "#ffffff")
    .attr("stroke", "#d9d9d9");

  svg
    .append("text")
    .attr("id", titleId)
    .attr("class", "analytics-chart__title")
    .attr("x", margin.left)
    .attr("y", 22)
    .attr("font-size", 16)
    .attr("font-weight", 700)
    .text("Anomaly timelines");

  svg
    .append("desc")
    .attr("id", descId)
    .text(
      `${analyticsState?.displayName || analyticsState?.countryCode || "Country"} anomaly timeline with ${renderableSeries.length} renderable indicator series. The strongest trajectories are emphasized and open circles mark excursions at or above absolute z-score 2.`,
    );

  const gridGroup = svg.append("g").attr("class", "analytics-chart__grid");
  gridGroup
    .selectAll("line")
    .data(yTicks)
    .join("line")
    .attr("x1", margin.left)
    .attr("x2", margin.left + plotWidth)
    .attr("y1", (tick) => yScale(tick))
    .attr("y2", (tick) => yScale(tick))
    .attr("stroke", (tick) => (tick === 0 ? "#888888" : "#e0e0e0"))
    .attr("stroke-dasharray", (tick) => (tick === 0 ? "0" : "3 3"));

  const xAxisGroup = svg.append("g").attr("class", "analytics-chart__x-axis");
  xAxisGroup
    .append("line")
    .attr("x1", margin.left)
    .attr("x2", margin.left + plotWidth)
    .attr("y1", margin.top + plotHeight)
    .attr("y2", margin.top + plotHeight)
    .attr("stroke", "#000000");

  xAxisGroup
    .selectAll("line.analytics-chart__x-tick")
    .data(xTicks)
    .join("line")
    .attr("class", "analytics-chart__x-tick")
    .attr("x1", (tick) => xScale(tick))
    .attr("x2", (tick) => xScale(tick))
    .attr("y1", margin.top + plotHeight)
    .attr("y2", margin.top + plotHeight + 6)
    .attr("stroke", "#000000");

  xAxisGroup
    .selectAll("text.analytics-chart__x-label")
    .data(xTicks)
    .join("text")
    .attr("class", "analytics-chart__x-label")
    .attr("x", (tick) => xScale(tick))
    .attr("y", margin.top + plotHeight + 22)
    .attr("font-size", 11)
    .attr("text-anchor", "middle")
    .text((tick) => String(tick));

  const yAxisGroup = svg.append("g").attr("class", "analytics-chart__y-axis");
  yAxisGroup
    .append("line")
    .attr("x1", margin.left)
    .attr("x2", margin.left)
    .attr("y1", margin.top)
    .attr("y2", margin.top + plotHeight)
    .attr("stroke", "#000000");

  yAxisGroup
    .selectAll("line.analytics-chart__y-tick")
    .data(yTicks)
    .join("line")
    .attr("class", "analytics-chart__y-tick")
    .attr("x1", margin.left - 6)
    .attr("x2", margin.left)
    .attr("y1", (tick) => yScale(tick))
    .attr("y2", (tick) => yScale(tick))
    .attr("stroke", "#000000");

  yAxisGroup
    .selectAll("text.analytics-chart__y-label")
    .data(yTicks)
    .join("text")
    .attr("class", "analytics-chart__y-label")
    .attr("x", margin.left - 10)
    .attr("y", (tick) => yScale(tick) + 4)
    .attr("font-size", 11)
    .attr("text-anchor", "end")
    .text((tick) => formatSignedTick(tick));

  const seriesLayer = svg.append("g").attr("class", "analytics-chart__timeline-series-layer");
  seriesModels.forEach((series) => {
    const pointsPayload = JSON.stringify(series.points.map((point) => ({ year: point.year, zscore: point.zscore })));
    const isDefaultHighlighted = defaultHighlightedIds.has(series.indicatorId);
    const seriesGroup = seriesLayer
      .append("g")
      .attr("class", "analytics-chart__timeline-series-group")
      .attr("data-series-id", series.indicatorId);

    seriesGroup
      .append("path")
      .attr("class", "analytics-chart__timeline-series")
      .attr("data-series-id", series.indicatorId)
      .attr("data-series-label", series.indicatorLabel)
      .attr("data-accent-color", series.accentColor)
      .attr("data-default-emphasis", isDefaultHighlighted ? "true" : "false")
      .attr("data-series-points", pointsPayload)
      .attr("d", line(series.points))
      .attr("fill", "none")
      .attr("stroke", isDefaultHighlighted ? series.accentColor : "#b8c0c8")
      .attr("stroke-linejoin", "round")
      .attr("stroke-linecap", "round")
      .attr("stroke-opacity", isDefaultHighlighted ? 0.95 : 0.55)
      .attr("stroke-width", isDefaultHighlighted ? 2.4 : 1.1);

    seriesGroup
      .append("path")
      .attr("class", "analytics-chart__timeline-series-hit")
      .attr("data-series-id", series.indicatorId)
      .attr("data-series-label", series.indicatorLabel)
      .attr("data-accent-color", series.accentColor)
      .attr("data-default-emphasis", isDefaultHighlighted ? "true" : "false")
      .attr("data-series-points", pointsPayload)
      .attr("d", line(series.points))
      .attr("fill", "none")
      .attr("stroke", "transparent")
      .attr("stroke-linejoin", "round")
      .attr("stroke-linecap", "round")
      .attr("stroke-width", 10);

    const pointsGroup = seriesGroup
      .append("g")
      .attr("class", "analytics-chart__timeline-points")
      .attr("data-series-id", series.indicatorId)
      .attr("display", isDefaultHighlighted ? null : "none");

    pointsGroup
      .selectAll(`circle.analytics-chart__timeline-point-${series.indicatorId}`)
      .data(series.anomalyPoints)
      .join("circle")
      .attr("class", "analytics-chart__timeline-point")
      .attr("data-series-id", series.indicatorId)
      .attr("cx", (point) => xScale(point.year))
      .attr("cy", (point) => yScale(point.zscore))
      .attr("r", 3)
      .attr("fill", "#ffffff")
      .attr("stroke", series.accentColor)
      .attr("stroke-width", 1.5);
  });

  const legend = figure.append("div").attr("class", "analytics-chart__timeline-legend").attr("role", "list");
  seriesModels.forEach((series) => {
    const isDefaultHighlighted = defaultHighlightedIds.has(series.indicatorId);
    const pointsPayload = JSON.stringify(series.points.map((point) => ({ year: point.year, zscore: point.zscore })));
    const button = legend
      .append("button")
      .attr("type", "button")
      .attr("class", "analytics-chart__timeline-legend-item")
      .attr("role", "listitem")
      .attr("data-series-id", series.indicatorId)
      .attr("data-series-label", series.indicatorLabel)
      .attr("data-accent-color", series.accentColor)
      .attr("data-default-emphasis", isDefaultHighlighted ? "true" : "false")
      .attr("data-series-points", pointsPayload)
      .attr("data-active-state", isDefaultHighlighted ? "default" : "inactive")
      .attr("aria-pressed", "false")
      .style("--analytics-series-color", series.accentColor);

    button.append("span").attr("class", "analytics-chart__timeline-legend-swatch").attr("aria-hidden", "true");
    button.append("span").attr("class", "analytics-chart__timeline-legend-text").text(series.indicatorLabel);
  });

  figure.append("div").attr("id", tooltipId).attr("class", "analytics-chart__timeline-tooltip").attr("hidden", "hidden");

  figure
    .append("figcaption")
    .attr("class", "analytics-chart__caption")
    .html(
      `${escapeHtml(`Showing ${renderableSeries.length} indicator histories.`)} <span aria-hidden="true">&bull;</span> ${escapeHtml(
        `${defaultHighlightedIds.size} strongest swings are emphasized by default`,
      )} <span aria-hidden="true">&bull;</span> Open circles mark excursions at or above |z| 2.`,
    );

  return figure.node().outerHTML;
}

function buildTimelineSeriesModels(renderableSeries) {
  const defaultHighlightedIds = new Set(
    [...renderableSeries]
      .sort((left, right) => maxSeriesAbsZscore(right) - maxSeriesAbsZscore(left))
      .slice(0, Math.min(TIMELINE_DEFAULT_HIGHLIGHT_COUNT, renderableSeries.length))
      .map((series) => series.indicatorId),
  );

  return renderableSeries.map((series, index) => ({
    ...series,
    accentColor: TIMELINE_ACCENT_PALETTE[index % TIMELINE_ACCENT_PALETTE.length],
    anomalyPoints: series.points.filter((point) => Math.abs(point.zscore) >= 2),
    defaultHighlightRank: defaultHighlightedIds.has(series.indicatorId)
      ? [...defaultHighlightedIds].indexOf(series.indicatorId)
      : -1,
  }));
}

function deriveTimelinePersistentSeriesIds(seriesModels, selectedIds = new Set()) {
  const normalizedSelectedIds = selectedIds instanceof Set ? selectedIds : new Set(selectedIds || []);
  const renderableIds = new Set(seriesModels.map((series) => series.indicatorId));
  const survivingSelectedIds = new Set([...normalizedSelectedIds].filter((indicatorId) => renderableIds.has(indicatorId)));
  if (survivingSelectedIds.size > 0) {
    return survivingSelectedIds;
  }

  return new Set(
    seriesModels
      .filter((series) => series.defaultHighlightRank >= 0)
      .sort((left, right) => left.defaultHighlightRank - right.defaultHighlightRank)
      .map((series) => series.indicatorId),
  );
}

function maxSeriesAbsZscore(series) {
  return Math.max(...series.points.map((point) => Math.abs(point.zscore)));
}

function formatSignedTick(value) {
  if (!Number.isFinite(value)) {
    return "";
  }

  const absoluteValue = Math.abs(value);
  const formatted = new Intl.NumberFormat("en-US", {
    minimumFractionDigits: absoluteValue < 10 ? 1 : 0,
    maximumFractionDigits: 1,
  }).format(absoluteValue);

  if (value === 0) {
    return "0.0";
  }

  return `${value > 0 ? "+" : "-"}${formatted}`;
}

function truncateLabel(value, maxLength) {
  const label = String(value || "").trim();
  if (label.length <= maxLength) {
    return label;
  }
  return `${label.slice(0, Math.max(0, maxLength - 3)).trimEnd()}...`;
}

export const __test__ = {
  buildHeatmapLayoutModel,
  buildTimelineSeriesModels,
  deriveTimelinePersistentSeriesIds,
  deriveHeatmapYearLabelStep,
  formatSignedTick,
  shouldRenderHeatmapYearLabel,
  truncateLabel,
};
