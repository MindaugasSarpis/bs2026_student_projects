import * as d3 from "d3";

import {
  GLOBE_FIXED_VIEW,
  getSupportedGlobeCountryForFeature,
  resolveGlobeFeatureCountryCode,
} from "./globe-country-config.js";
import { normalizeCountryCode } from "../shared/formatters.js";

const DEFAULT_GLOBE_DIMENSIONS = Object.freeze({
  width: 520,
  height: 520,
  padding: 26,
});
const VISIBLE_HEMISPHERE_EPSILON = 1e-6;

export function createD3GlobeRenderer() {
  return {
    renderGlobe(context) {
      return renderD3Globe(context);
    },
  };
}

function renderD3Globe(context) {
  const globeContext = normalizeGlobeRenderContext(context);
  const featureViewModels = buildGlobeFeatureViewModels(globeContext.worldGeometry, {
    selectedCountryCode: globeContext.selectedCountryCode,
  });
  if (!featureViewModels.length) {
    return "";
  }
  const visibleFeatureViewModels = sortGlobeFeatureViewModels(
    featureViewModels.filter((featureViewModel) => featureViewModel.isVisible),
  );

  const projection = buildOrthographicProjection({
    featureViewModels,
    width: globeContext.width,
    height: globeContext.height,
    padding: globeContext.padding,
  });
  const path = d3.geoPath(projection);
  const figure = d3.create("figure").attr("class", "globe-nav").attr("data-globe-adapter", "d3");
  figure.attr("data-selected-country-code", globeContext.selectedCountryCode || "");
  const svg = figure
    .append("svg")
    .attr("class", "globe-nav__svg")
    .attr("viewBox", `0 0 ${globeContext.width} ${globeContext.height}`)
    .attr("role", "img")
    .attr("aria-label", globeContext.title)
    .attr("preserveAspectRatio", "xMidYMid meet");

  const defs = svg.append("defs");
  const sphereGradient = defs.append("radialGradient").attr("id", "globe-nav-sphere-gradient");
  sphereGradient.append("stop").attr("offset", "0%").attr("stop-color", "#f7fbfd");
  sphereGradient.append("stop").attr("offset", "100%").attr("stop-color", "#d7e7ef");

  svg
    .append("path")
    .datum({ type: "Sphere" })
    .attr("class", "globe-nav__sphere")
    .attr("d", path)
    .attr("fill", "url(#globe-nav-sphere-gradient)")
    .attr("stroke", "#35566b")
    .attr("stroke-width", 1.5);

  svg
    .append("path")
    .datum(d3.geoGraticule10())
    .attr("class", "globe-nav__graticule")
    .attr("d", path)
    .attr("fill", "none")
    .attr("stroke", "#aac2ce")
    .attr("stroke-opacity", 0.6)
    .attr("stroke-width", 0.6);

  svg
    .append("g")
    .attr("class", "globe-nav__countries")
    .selectAll("path")
    .data(visibleFeatureViewModels)
    .join("path")
    .attr("class", (featureViewModel) => buildCountryPathClassName(featureViewModel))
    .attr("data-country-code", (featureViewModel) => featureViewModel.countryCode || "")
    .attr("data-country-name", (featureViewModel) => featureViewModel.displayName || "")
    .attr("data-globe-country-select", (featureViewModel) => (featureViewModel.isSelectable ? "true" : null))
    .attr("data-globe-country-disabled", (featureViewModel) => (featureViewModel.isSelectable ? null : "true"))
    .attr("data-globe-selectable", (featureViewModel) => String(featureViewModel.isSelectable))
    .attr("data-country-selected", (featureViewModel) => String(featureViewModel.isSelected))
    .attr("data-globe-visibility", "visible")
    .attr("role", (featureViewModel) => (featureViewModel.isSelectable ? "button" : null))
    .attr("tabindex", (featureViewModel) => (featureViewModel.isSelectable ? "0" : null))
    .attr("focusable", (featureViewModel) => (featureViewModel.isSelectable ? "true" : "false"))
    .attr("aria-label", (featureViewModel) => (featureViewModel.isSelectable ? buildCountryTitle(featureViewModel) : null))
    .attr("aria-pressed", (featureViewModel) => (featureViewModel.isSelectable ? String(featureViewModel.isSelected) : null))
    .attr("d", (featureViewModel) => path(featureViewModel.feature))
    .attr("fill", (featureViewModel) => resolveCountryFill(featureViewModel))
    .attr("stroke", (featureViewModel) => resolveCountryStroke(featureViewModel))
    .attr("stroke-width", (featureViewModel) => (featureViewModel.isSelected ? 1.8 : 0.8))
    .each(function appendCountryTitle(featureViewModel) {
      d3.select(this)
        .append("title")
        .text(buildCountryTitle(featureViewModel));
    });

  const legend = figure.append("div").attr("class", "globe-nav__legend").attr("aria-hidden", "true");
  buildLegendItems().forEach((legendItem) => {
    const item = legend.append("span").attr("class", `globe-nav__legend-item globe-nav__legend-item--${legendItem.kind}`);
    item.append("span").attr("class", "globe-nav__legend-swatch");
    item.append("span").attr("class", "globe-nav__legend-label").text(legendItem.label);
  });

  figure
    .append("figcaption")
    .attr("class", "globe-nav__caption")
    .text(buildGlobeCaption(globeContext, featureViewModels));

  return figure.node()?.outerHTML || "";
}

function normalizeGlobeRenderContext(context) {
  return {
    worldGeometry: context?.worldGeometry || null,
    selectedCountryCode: normalizeCountryCode(context?.selectedCountryCode),
    title:
      typeof context?.title === "string" && context.title.trim().length > 0
        ? context.title.trim()
        : "CCOUTLINE country selection globe",
    width: Number.isFinite(context?.width) ? context.width : DEFAULT_GLOBE_DIMENSIONS.width,
    height: Number.isFinite(context?.height) ? context.height : DEFAULT_GLOBE_DIMENSIONS.height,
    padding: Number.isFinite(context?.padding) ? context.padding : DEFAULT_GLOBE_DIMENSIONS.padding,
  };
}

function normalizeWorldFeatures(worldGeometry) {
  return Array.isArray(worldGeometry?.features)
    ? worldGeometry.features.filter((feature) => feature && typeof feature === "object" && feature.geometry)
    : [];
}

function buildGlobeFeatureViewModels(worldGeometry, { selectedCountryCode } = {}) {
  return normalizeWorldFeatures(worldGeometry).map((feature) => {
    const supportedCountry = getSupportedGlobeCountryForFeature(feature);
    const countryCode = resolveGlobeFeatureCountryCode(feature);
    const centroid = d3.geoCentroid(feature);
    const distanceFromViewCenter = d3.geoDistance(centroid, GLOBE_FIXED_VIEW.center);
    const displayName =
      supportedCountry?.label ||
      (typeof feature?.properties?.display_name === "string" ? feature.properties.display_name.trim() : "") ||
      countryCode ||
      "Country";

    return {
      feature,
      countryCode,
      displayName,
      isVisible:
        Array.isArray(centroid) &&
        centroid.length === 2 &&
        Number.isFinite(distanceFromViewCenter) &&
        distanceFromViewCenter <= Math.PI / 2 + VISIBLE_HEMISPHERE_EPSILON,
      isSelectable: Boolean(supportedCountry),
      isSelected: Boolean(supportedCountry) && supportedCountry.countryCode === selectedCountryCode,
      supportedCountry,
    };
  });
}

function buildOrthographicProjection({ featureViewModels, width, height, padding }) {
  const supportedFeatures = featureViewModels.filter((featureViewModel) => featureViewModel.isSelectable);
  const fitFeatures = supportedFeatures.length ? supportedFeatures : featureViewModels;
  const featureCollection = {
    type: "FeatureCollection",
    features: fitFeatures.map((featureViewModel) => featureViewModel.feature),
  };

  return d3
    .geoOrthographic()
    .rotate(GLOBE_FIXED_VIEW.rotation)
    .precision(GLOBE_FIXED_VIEW.precision)
    .fitExtent(
      [
        [padding, padding],
        [Math.max(padding, width - padding), Math.max(padding, height - padding)],
      ],
      featureCollection,
    )
    .clipAngle(90);
}

function buildCountryPathClassName(featureViewModel) {
  const classes = ["globe-nav__country"];
  if (featureViewModel.isSelectable) {
    classes.push("globe-nav__country--supported");
  } else {
    classes.push("globe-nav__country--disabled");
  }

  if (featureViewModel.isSelected) {
    classes.push("globe-nav__country--selected");
  }

  return classes.join(" ");
}

function sortGlobeFeatureViewModels(featureViewModels) {
  return [...featureViewModels].sort((left, right) => {
    if (left.isSelected !== right.isSelected) {
      return left.isSelected ? 1 : -1;
    }
    if (left.isSelectable !== right.isSelectable) {
      return left.isSelectable ? 1 : -1;
    }
    return String(left.displayName).localeCompare(String(right.displayName));
  });
}

function resolveCountryFill(featureViewModel) {
  if (featureViewModel.isSelected) {
    return "#1d6f8c";
  }
  if (featureViewModel.isSelectable) {
    return "#7eb7c9";
  }
  return "#d7dee2";
}

function resolveCountryStroke(featureViewModel) {
  if (featureViewModel.isSelected) {
    return "#0b2b38";
  }
  if (featureViewModel.isSelectable) {
    return "#315a68";
  }
  return "#7b8f99";
}

function buildCountryTitle(featureViewModel) {
  if (featureViewModel.isSelected) {
    return `${featureViewModel.displayName} (selected supported country)`;
  }
  if (featureViewModel.isSelectable) {
    return `${featureViewModel.displayName} (supported country)`;
  }
  return `${featureViewModel.displayName} (shown for regional context only)`;
}

function buildLegendItems() {
  return [
    {
      kind: "selected",
      label: "Selected country",
    },
    {
      kind: "supported",
      label: "Supported country",
    },
    {
      kind: "disabled",
      label: "Context only",
    },
  ];
}

function buildGlobeCaption(globeContext, featureViewModels) {
  const selectedFeature = featureViewModels.find((featureViewModel) => featureViewModel.isSelected);
  if (selectedFeature) {
    return `${selectedFeature.displayName} is selected for country intelligence panel.`;
  }

  return `${featureViewModels.filter((featureViewModel) => featureViewModel.isSelectable).length} supported countries.`;
}

export const __test__ = {
  buildCountryPathClassName,
  buildCountryTitle,
  buildGlobeCaption,
  buildGlobeFeatureViewModels,
  buildLegendItems,
  buildOrthographicProjection,
  normalizeGlobeRenderContext,
  normalizeWorldFeatures,
  sortGlobeFeatureViewModels,
};
