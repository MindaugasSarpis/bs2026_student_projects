const MUTED_SERIES_COLOR = "#b8c0c8";
const MUTED_SERIES_OPACITY = "0.55";
const MUTED_SERIES_WIDTH = "1.1";
const ACTIVE_SERIES_OPACITY = "0.95";
const ACTIVE_SERIES_WIDTH = "2.4";
const HOVER_SERIES_OPACITY = "1";
const HOVER_SERIES_WIDTH = "3.2";

export function syncAnalyticsTimelineInteractions(root, { selectionStateByCountry = new Map() } = {}) {
  if (!(root instanceof Element)) {
    return;
  }

  const figures = root.querySelectorAll("[data-analytics-timeline='true']");
  figures.forEach((figure) => {
    if (!(figure instanceof HTMLElement)) {
      return;
    }

    bindTimelineFigureInteractions(figure, selectionStateByCountry);
    pruneTimelineSelectionState(figure, selectionStateByCountry);
    applyTimelineInteractionState(figure, selectionStateByCountry);
  });
}

function bindTimelineFigureInteractions(figure, selectionStateByCountry) {
  if (figure.dataset.timelineInteractiveBound === "true") {
    return;
  }

  figure.dataset.timelineInteractiveBound = "true";
  figure.__timelineHoveredSeriesId = "";

  const bindHoverEvents = (element, { pointStrategy }) => {
    element.addEventListener("mouseenter", (event) => {
      handleTimelineHoverEvent(event.currentTarget, figure, selectionStateByCountry, { pointStrategy, event });
    });
    element.addEventListener("mousemove", (event) => {
      handleTimelineHoverEvent(event.currentTarget, figure, selectionStateByCountry, { pointStrategy, event });
    });
    element.addEventListener("mouseleave", () => {
      clearTimelineHoverState(figure, selectionStateByCountry);
    });
  };

  figure.querySelectorAll(".analytics-chart__timeline-series-hit").forEach((element) => {
    if (element instanceof SVGElement) {
      bindHoverEvents(element, { pointStrategy: "pointer" });
    }
  });

  figure.querySelectorAll(".analytics-chart__timeline-legend-item").forEach((element) => {
    if (!(element instanceof HTMLButtonElement)) {
      return;
    }

    bindHoverEvents(element, { pointStrategy: "latest" });
    element.addEventListener("click", (event) => {
      event.preventDefault();
      const seriesId = element.getAttribute("data-series-id") || "";
      if (!seriesId) {
        return;
      }
      toggleTimelineLegendSelection(figure, selectionStateByCountry, seriesId);
    });
  });

  figure.addEventListener("mouseleave", () => {
    clearTimelineHoverState(figure, selectionStateByCountry);
  });
}

function handleTimelineHoverEvent(target, figure, selectionStateByCountry, { pointStrategy, event }) {
  const seriesId = target.getAttribute("data-series-id") || "";
  if (!seriesId) {
    return;
  }

  figure.__timelineHoveredSeriesId = seriesId;
  const points = readSeriesPoints(target);
  const point =
    pointStrategy === "pointer" ? selectNearestSeriesPoint(figure, points, event?.clientX ?? null) : selectLatestSeriesPoint(points);
  updateTimelineTooltip(figure, target, point, event);
  applyTimelineInteractionState(figure, selectionStateByCountry);
}

function clearTimelineHoverState(figure, selectionStateByCountry) {
  figure.__timelineHoveredSeriesId = "";
  hideTimelineTooltip(figure);
  applyTimelineInteractionState(figure, selectionStateByCountry);
}

function toggleTimelineLegendSelection(figure, selectionStateByCountry, seriesId) {
  const countryCode = figure.getAttribute("data-country-code") || "";
  const nextSelectedIds = new Set(selectionStateByCountry.get(countryCode) || []);
  if (nextSelectedIds.has(seriesId)) {
    nextSelectedIds.delete(seriesId);
  } else {
    nextSelectedIds.add(seriesId);
  }

  if (nextSelectedIds.size > 0) {
    selectionStateByCountry.set(countryCode, nextSelectedIds);
  } else {
    selectionStateByCountry.delete(countryCode);
  }

  applyTimelineInteractionState(figure, selectionStateByCountry);
}

function applyTimelineInteractionState(figure, selectionStateByCountry) {
  const countryCode = figure.getAttribute("data-country-code") || "";
  const hoveredSeriesId = String(figure.__timelineHoveredSeriesId || "");
  const selectedIds = new Set(selectionStateByCountry.get(countryCode) || []);
  const defaultIds = readDefaultTimelineSeriesIds(figure);
  const persistentIds = selectedIds.size > 0 ? selectedIds : defaultIds;
  const hasManualSelection = selectedIds.size > 0;

  const seriesElementsById = collectTimelineSeriesElements(figure);
  for (const [seriesId, seriesElements] of seriesElementsById.entries()) {
    const isHovered = hoveredSeriesId === seriesId;
    const isSelected = selectedIds.has(seriesId);
    const isPersistent = persistentIds.has(seriesId);
    const accentColor = seriesElements.accentColor;
    const isActive = isHovered || isPersistent;

    if (seriesElements.path) {
      seriesElements.path.setAttribute("stroke", isActive ? accentColor : MUTED_SERIES_COLOR);
      seriesElements.path.setAttribute(
        "stroke-opacity",
        isHovered ? HOVER_SERIES_OPACITY : isPersistent ? ACTIVE_SERIES_OPACITY : MUTED_SERIES_OPACITY,
      );
      seriesElements.path.setAttribute(
        "stroke-width",
        isHovered ? HOVER_SERIES_WIDTH : isPersistent ? ACTIVE_SERIES_WIDTH : MUTED_SERIES_WIDTH,
      );
    }

    if (seriesElements.pointsGroup) {
      seriesElements.pointsGroup.setAttribute("display", isActive ? "inline" : "none");
    }

    if (seriesElements.legendItem) {
      const activeState = isSelected ? "selected" : isPersistent ? "default" : "inactive";
      seriesElements.legendItem.setAttribute("data-active-state", activeState);
      seriesElements.legendItem.setAttribute("data-hovered", isHovered ? "true" : "false");
      seriesElements.legendItem.setAttribute("aria-pressed", hasManualSelection && isSelected ? "true" : "false");
    }
  }
}

function pruneTimelineSelectionState(figure, selectionStateByCountry) {
  const countryCode = figure.getAttribute("data-country-code") || "";
  if (!selectionStateByCountry.has(countryCode)) {
    return;
  }

  const renderableSeriesIds = new Set(
    Array.from(figure.querySelectorAll(".analytics-chart__timeline-legend-item")).map(
      (element) => element.getAttribute("data-series-id") || "",
    ),
  );
  const nextSelectedIds = new Set(
    [...(selectionStateByCountry.get(countryCode) || [])].filter((seriesId) => renderableSeriesIds.has(seriesId)),
  );
  if (nextSelectedIds.size > 0) {
    selectionStateByCountry.set(countryCode, nextSelectedIds);
  } else {
    selectionStateByCountry.delete(countryCode);
  }
}

function collectTimelineSeriesElements(figure) {
  const seriesElementsById = new Map();

  figure.querySelectorAll(".analytics-chart__timeline-series").forEach((element) => {
    const seriesId = element.getAttribute("data-series-id") || "";
    if (!seriesId) {
      return;
    }
    const entry = seriesElementsById.get(seriesId) || {};
    entry.path = element;
    entry.accentColor = element.getAttribute("data-accent-color") || "#0b7285";
    seriesElementsById.set(seriesId, entry);
  });

  figure.querySelectorAll(".analytics-chart__timeline-points").forEach((element) => {
    const seriesId = element.getAttribute("data-series-id") || "";
    if (!seriesId) {
      return;
    }
    const entry = seriesElementsById.get(seriesId) || {};
    entry.pointsGroup = element;
    entry.accentColor = entry.accentColor || "#0b7285";
    seriesElementsById.set(seriesId, entry);
  });

  figure.querySelectorAll(".analytics-chart__timeline-legend-item").forEach((element) => {
    const seriesId = element.getAttribute("data-series-id") || "";
    if (!seriesId) {
      return;
    }
    const entry = seriesElementsById.get(seriesId) || {};
    entry.legendItem = element;
    entry.accentColor = entry.accentColor || element.getAttribute("data-accent-color") || "#0b7285";
    seriesElementsById.set(seriesId, entry);
  });

  return seriesElementsById;
}

function readDefaultTimelineSeriesIds(figure) {
  return new Set(
    Array.from(figure.querySelectorAll(".analytics-chart__timeline-series[data-default-emphasis='true']")).map(
      (element) => element.getAttribute("data-series-id") || "",
    ),
  );
}

function readSeriesPoints(element) {
  const pointsPayload = element.getAttribute("data-series-points") || "[]";
  try {
    const parsed = JSON.parse(pointsPayload);
    return Array.isArray(parsed)
      ? parsed.filter((point) => Number.isFinite(point?.year) && Number.isFinite(point?.zscore))
      : [];
  } catch {
    return [];
  }
}

function selectLatestSeriesPoint(points) {
  if (!Array.isArray(points) || points.length === 0) {
    return null;
  }
  return points[points.length - 1];
}

function selectNearestSeriesPoint(figure, points, clientX) {
  if (!Array.isArray(points) || points.length === 0) {
    return null;
  }

  if (!Number.isFinite(clientX)) {
    return selectLatestSeriesPoint(points);
  }

  const svg = figure.querySelector("svg");
  const figureRect = svg?.getBoundingClientRect?.();
  const yearMin = Number(figure.getAttribute("data-year-min"));
  const yearMax = Number(figure.getAttribute("data-year-max"));
  const plotLeft = Number(figure.getAttribute("data-plot-left"));
  const plotWidth = Number(figure.getAttribute("data-plot-width"));
  if (!figureRect || !Number.isFinite(figureRect.width) || figureRect.width <= 0 || !Number.isFinite(yearMin) || !Number.isFinite(yearMax)) {
    return selectLatestSeriesPoint(points);
  }

  const plotLeftPx = (plotLeft / 860) * figureRect.width;
  const plotWidthPx = (plotWidth / 860) * figureRect.width;
  const boundedClientX = clamp(clientX - figureRect.left - plotLeftPx, 0, plotWidthPx);
  const impliedYear = yearMin + (boundedClientX / Math.max(plotWidthPx, 1)) * (yearMax - yearMin);

  return points.reduce((closest, current) => {
    if (!closest) {
      return current;
    }
    return Math.abs(current.year - impliedYear) < Math.abs(closest.year - impliedYear) ? current : closest;
  }, null);
}

function updateTimelineTooltip(figure, target, point, event) {
  const tooltipId = figure.getAttribute("data-tooltip-id") || "";
  const tooltip = tooltipId ? figure.querySelector(`#${tooltipId}`) : figure.querySelector(".analytics-chart__timeline-tooltip");
  if (!(tooltip instanceof HTMLElement) || !point) {
    hideTimelineTooltip(figure);
    return;
  }

  const label = target.getAttribute("data-series-label") || "Indicator";
  tooltip.textContent = `${label} | ${point.year} | z-score ${formatSignedTick(point.zscore)}`;
  tooltip.hidden = false;

  const figureRect = figure.getBoundingClientRect();
  const targetRect = target.getBoundingClientRect();
  const offsetX = Number.isFinite(event?.clientX) ? event.clientX - figureRect.left : targetRect.left - figureRect.left + targetRect.width / 2;
  const offsetY = Number.isFinite(event?.clientY) ? event.clientY - figureRect.top : targetRect.top - figureRect.top;
  tooltip.style.left = `${clamp(offsetX + 12, 12, Math.max(12, figureRect.width - 12))}px`;
  tooltip.style.top = `${clamp(offsetY - 12, 12, Math.max(12, figureRect.height - 12))}px`;
}

function hideTimelineTooltip(figure) {
  const tooltipId = figure.getAttribute("data-tooltip-id") || "";
  const tooltip = tooltipId ? figure.querySelector(`#${tooltipId}`) : figure.querySelector(".analytics-chart__timeline-tooltip");
  if (tooltip instanceof HTMLElement) {
    tooltip.hidden = true;
  }
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
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

export const __test__ = {
  applyTimelineInteractionState,
  pruneTimelineSelectionState,
  readSeriesPoints,
  selectLatestSeriesPoint,
  selectNearestSeriesPoint,
  formatSignedTick,
};
