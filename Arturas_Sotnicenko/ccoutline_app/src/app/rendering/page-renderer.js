import { summarizeCountryCoverage, supportedCountryCodes } from "../view-models/page-model.js";
import { createIndicatorViewModels } from "../view-models/indicator-view-model.js";
import { findCompatibleForecastOverlay, findForecastChartDisclosure } from "../view-models/forecast-overlay-model.js";
import {
  buildCountryAnchor,
  formatProjectionFlag,
  formatScalar,
  formatYearRange,
  normalizeCountryCode,
  resolveCountrySummaryYearRange,
} from "../shared/formatters.js";
import { escapeAttribute, escapeHtml } from "../shared/html.js";
import { buildIndicatorDisclosureKey } from "../state/ui-disclosure-keys.js";
import { listLegalPages, normalizeAppPathname } from "../legal/legal-page-config.js";

export function renderLoading(appRoot, label, consentState = null) {
  appRoot.innerHTML = renderPageShell({
    consentState,
    currentPathname: "/",
    bodyMarkup: `
      <main class="page-shell">
        <section class="section-panel">
          <p class="kicker">CCOUTLINE</p>
          <h1>Loading</h1>
          <p>${escapeHtml(label)}</p>
        </section>
      </main>
    `,
  });
}

export function renderPage(appRoot, appState, { chartRenderer }) {
  if (appState.countriesError) {
    renderRootErrorPage(appRoot, appState?.consentState || null);
    return;
  }

  const activeCountryCodes = supportedCountryCodes(appState);
  if (!activeCountryCodes.length) {
    renderEmptyDataPage(appRoot, appState?.consentState || null);
    return;
  }

  const countrySummary = summarizeCountryCoverage(appState);
  const globeNavigationMarkup = renderGlobeNavigationMarkup({
    countryModels: appState.countryModels,
    globeMarkup: appState.globeMarkup || "",
    selectedCountryCode: appState.selectedCountryCode || null,
  });
  const countryPanelMarkup = renderCountryPanelRegionMarkup({
    selectedCountryCode: appState.selectedCountryCode || null,
    selectedCountryModel: appState.selectedCountryModel || null,
    chartRenderer,
  });

  appRoot.innerHTML = renderPageShell({
    consentState: appState?.consentState || null,
    currentPathname: "/",
    bodyMarkup: `
      <main class="page-shell">
        <section class="section-panel">
          <p class="kicker">COUNTRY CODE OUTLINE</p>
          <h1>Country intelligence in one place</h1>
          <p>
            CCOUTLINE brings together published macroeconomic indicators, analytics, and forecasts
            for each country in one place. Explore definitions, yearly data, analytical views,
            and forecast series with the context needed to read them clearly.
          </p>
          <ul class="intro-list">
            <li>Browse each country to see which indicators are covered and how far the yearly series runs.</li>
            <li>Use analytics views and indicator charts to spot patterns, unusual years, and contrasts across indicators.</li>
            <li>Check the forecast section to distinguish observed history from CCOUTLINE forecasts.</li>
          </ul>
          <p class="body-muted">
            Countries currently covered: ${escapeHtml(countrySummary)}
          </p>
        </section>
        ${globeNavigationMarkup}
        ${countryPanelMarkup}
      </main>
    `,
  });
}

export function renderRootErrorPage(appRoot, consentState = null) {
  appRoot.innerHTML = renderPageShell({
    consentState,
    currentPathname: "/",
    bodyMarkup: `
      <main class="page-shell">
        <section class="empty-state">
          <p class="kicker">CCOUTLINE</p>
          <h1>Country data is temporarily unavailable.</h1>
          <p>
            This page is meant to show published country indicators, but the data for this publication
            could not be loaded right now.
          </p>
          <p>Please try again later.</p>
        </section>
      </main>
    `,
  });
}

export function renderStandaloneLegalPage(appRoot, legalPage, consentState = null) {
  const legalSectionsMarkup = Array.isArray(legalPage?.sections)
    ? legalPage.sections.map((section) => renderLegalSectionMarkup(section)).join("")
    : "";

  appRoot.innerHTML = renderPageShell({
    consentState,
    currentPathname: legalPage?.pathname || "/",
    bodyMarkup: `
      <main class="page-shell">
        <article class="section-panel legal-page" data-legal-page="${escapeAttribute(legalPage?.key || "legal")}">
          <p class="kicker">${escapeHtml(legalPage?.kicker || "CCOUTLINE legal")}</p>
          <h1>${escapeHtml(legalPage?.title || "Legal information")}</h1>
          <p class="legal-page__lead">${escapeHtml(legalPage?.lead || "")}</p>
          ${legalPage?.key === "manage-cookies" ? renderManageCookiesPanel(consentState) : ""}
          ${legalSectionsMarkup}
        </article>
      </main>
    `,
  });
}

function renderEmptyDataPage(appRoot, consentState = null) {
  appRoot.innerHTML = renderPageShell({
    consentState,
    currentPathname: "/",
    bodyMarkup: `
      <main class="page-shell">
        <section class="empty-state">
          <p class="kicker">CCOUTLINE</p>
          <h1>No country publication is available yet.</h1>
          <p>
            CCOUTLINE is intended to present published country indicators, glossary information, and yearly
            data series in one place. There is no active country dataset available to browse on this page yet.
          </p>
        </section>
      </main>
    `,
  });
}

function renderPageShell({ consentState, currentPathname = "/", bodyMarkup }) {
  return `
    ${renderConsentBanner(consentState)}
    ${bodyMarkup}
    ${renderSiteFooter(currentPathname)}
  `;
}

function renderConsentBanner(consentState) {
  if (consentState?.hydrated !== true || consentState?.decision) {
    return "";
  }

  return `
    <div class="consent-banner" data-consent-banner="true">
      <div class="consent-banner__backdrop" data-consent-backdrop="true" aria-hidden="true"></div>
      <aside
        class="consent-banner__inner"
        data-consent-dialog="true"
        role="dialog"
        aria-modal="true"
        aria-labelledby="consent-dialog-title"
        aria-describedby="consent-dialog-description consent-dialog-links"
        tabindex="-1"
      >
        <p class="kicker">Cookie choice</p>
        <h2 id="consent-dialog-title">Choose whether CCOUTLINE may load analytics.</h2>
        <p id="consent-dialog-description">
          Analytics is off by default. You can accept or decline analytics cookies for this browser before any
          later tracking script is allowed to load.
        </p>
        <p class="body-muted consent-banner__links" id="consent-dialog-links">
          Read the <a href="/privacy/" data-legal-link="privacy">Privacy Notice</a>,
          <a href="/cookies/" data-legal-link="cookies">Cookie Notice</a>, or
          <a href="/manage-cookies/" data-legal-link="manage-cookies">Manage cookies</a> later.
        </p>
        <div class="consent-banner__actions">
          <button type="button" data-consent-action="accepted">Accept analytics</button>
          <button type="button" data-consent-action="declined">Decline analytics</button>
        </div>
      </aside>
    </div>
  `;
}

function renderLegalSectionMarkup(section) {
  const paragraphs = Array.isArray(section?.paragraphs)
    ? section.paragraphs.map((paragraph) => `<p>${escapeHtml(paragraph)}</p>`).join("")
    : "";

  return `
    <section class="legal-page__section">
      <h2>${escapeHtml(section?.heading || "")}</h2>
      ${paragraphs}
    </section>
  `;
}

function renderManageCookiesPanel(consentState) {
  const decisionLabel =
    consentState?.decision === "accepted"
      ? "Accepted"
      : consentState?.decision === "declined"
        ? "Declined"
        : "Not set";
  const updatedAtMarkup =
    typeof consentState?.updatedAt === "string" && consentState.updatedAt.trim().length > 0
      ? `<p class="body-muted">Stored choice updated: <time datetime="${escapeAttribute(consentState.updatedAt)}">${escapeHtml(consentState.updatedAt)}</time></p>`
      : `<p class="body-muted">No analytics choice has been stored for this browser yet.</p>`;

  return `
    <section class="legal-page__section legal-page__section--manage" data-manage-cookies-panel="true">
      <h2>Current browser setting</h2>
      <p class="indicator-summary" aria-label="Current analytics choice">
        <span class="indicator-summary__item" data-manage-cookies-status="true">Current analytics choice: ${escapeHtml(decisionLabel)}</span>
      </p>
      ${updatedAtMarkup}
      <div class="consent-banner__actions legal-page__actions">
        <button type="button" data-consent-action="accepted">Accept analytics</button>
        <button type="button" data-consent-action="declined">Decline analytics</button>
      </div>
    </section>
  `;
}

function renderSiteFooter(currentPathname) {
  const normalizedCurrentPathname = normalizeAppPathname(currentPathname);
  const footerLinks = [
    {
      key: "home",
      href: "/",
      label: "Home",
    },
    ...listLegalPages().map((page) => ({
      key: page.key,
      href: page.pathname,
      label: page.title,
      isLegalLink: true,
    })),
  ];

  const linksMarkup = footerLinks
    .map((link) => {
      const normalizedLinkPathname = normalizeAppPathname(link.href);
      const isCurrent = normalizedCurrentPathname === normalizedLinkPathname;
      const legalLinkAttribute = link.isLegalLink ? ` data-legal-link="${escapeAttribute(link.key)}"` : "";
      const currentAttribute = isCurrent ? ` aria-current="page"` : "";
      return `<a href="${escapeAttribute(link.href)}"${legalLinkAttribute}${currentAttribute}>${escapeHtml(link.label)}</a>`;
    })
    .join("");

  return `
    <footer class="site-footer" aria-label="Footer">
      <div class="site-footer__inner">
        <nav class="site-footer__links" aria-label="Legal and site links">
          ${linksMarkup}
        </nav>
      </div>
    </footer>
  `;
}

export function renderCountrySectionMarkup(model, { chartRenderer }) {
  const displayName = model.countryEntry?.display_name || model.normalizedSeries?.display_name || model.countryCode;
  const countryCode = model.countryCode || normalizeCountryCode(model.countryEntry?.country_code) || "unknown";

  if (model.loadError) {
    return `
      <section class="section-panel" id="${escapeAttribute(buildCountryAnchor(countryCode))}" data-country-code="${escapeAttribute(countryCode)}">
        <p class="kicker">Country</p>
        <h2>${escapeHtml(displayName)} (${escapeHtml(countryCode)})</h2>
        <p>This country's indicator tables are temporarily unavailable.</p>
      </section>
    `;
  }

  const normalizedSeries = model.normalizedSeries || {};
  const indicatorViewModels = createIndicatorViewModels(normalizedSeries.indicators);
  const countrySummaryYearRange = resolveCountrySummaryYearRange(normalizedSeries);
  const analyticsState = model.analyticsState || null;
  const uiState = model.uiState || buildFallbackCountryUiState(indicatorViewModels);
  const forecastMarkup = renderCountryForecastSection(model.forecast, model.forecastLoadError);
  const glossaryMarkup = renderIndicatorGlossary(indicatorViewModels);
  const analyticsMarkup = analyticsState
    ? renderCountryAnalyticsSection(analyticsState, uiState, chartRenderer)
    : `<p class="indicator-state-message">Analytics state is temporarily unavailable for this country.</p>`;
  const chartsMarkup = renderIndicatorDisclosures(indicatorViewModels, uiState, chartRenderer, model.forecast);

  return `
    <section class="section-panel" id="${escapeAttribute(buildCountryAnchor(countryCode))}" data-country-code="${escapeAttribute(countryCode)}">
      <p class="kicker">Country</p>
      <h2>${escapeHtml(displayName)} (${escapeHtml(countryCode)})</h2>
      <p class="body-muted">
        ${escapeHtml(String(indicatorViewModels.length))} indicators • ${escapeHtml(formatYearRange(countrySummaryYearRange))}
      </p>
      ${renderSectionDisclosure({
        disclosureId: uiState.countrySections.glossary.disclosureId,
        isOpen: uiState.countrySections.glossary.open,
        variant: "country",
        title: "Indicator glossary",
        bodyMarkup: glossaryMarkup,
        summaryItems: [formatDisclosureCount(indicatorViewModels.length, "indicator", "indicators"), "labels, units, and ranges"],
      })}
      ${renderSectionDisclosure({
        disclosureId: uiState.countrySections.analytics.disclosureId,
        isOpen: uiState.countrySections.analytics.open,
        variant: "country",
        title: "Data analytics",
        bodyMarkup: analyticsMarkup,
        summaryItems: analyticsState
          ? [
              `${analyticsState.rawTable.renderableRowCount} numeric z-score row${analyticsState.rawTable.renderableRowCount === 1 ? "" : "s"}`,
              `${analyticsState.controls.activeOverrideCount} active override${analyticsState.controls.activeOverrideCount === 1 ? "" : "s"}`,
            ]
          : ["Analytics unavailable"],
      })}
      ${renderSectionDisclosure({
        disclosureId: uiState.countrySections.forecast.disclosureId,
        isOpen: uiState.countrySections.forecast.open,
        variant: "country",
        title: "Forecast",
        bodyMarkup: forecastMarkup,
        summaryItems: buildForecastSectionSummaryItems(model.forecast, model.forecastLoadError),
      })}
      ${renderSectionDisclosure({
        disclosureId: uiState.countrySections.charts.disclosureId,
        isOpen: uiState.countrySections.charts.open,
        variant: "country",
        title: "Indicator charts",
        bodyMarkup: chartsMarkup,
        summaryItems: [formatDisclosureCount(indicatorViewModels.length, "chart-backed disclosure", "chart-backed disclosures")],
      })}
    </section>
  `;
}

export function renderGlobeNavigationMarkup({ countryModels, globeMarkup, selectedCountryCode }) {
  const selectableCountries = Array.isArray(countryModels)
    ? countryModels
        .filter((model) => model && typeof model === "object" && normalizeCountryCode(model.countryCode))
        .map((model) => ({
          countryCode: normalizeCountryCode(model.countryCode),
          displayName:
            model.countryEntry?.display_name || model.normalizedSeries?.display_name || normalizeCountryCode(model.countryCode),
        }))
    : [];

  if (!globeMarkup || !selectableCountries.length) {
    return "";
  }

  const selectedCode = normalizeCountryCode(selectedCountryCode);
  const buttonsMarkup = selectableCountries
    .map((country) => {
      const isSelected = country.countryCode === selectedCode;
      return `
        <button
          type="button"
          class="globe-nav__country-button${isSelected ? " globe-nav__country-button--selected" : ""}"
          data-country-select-control="true"
          data-country-code="${escapeAttribute(country.countryCode)}"
          aria-pressed="${isSelected ? "true" : "false"}"
        >
          ${escapeHtml(country.displayName)}
        </button>
      `;
    })
    .join("");

  return `
    <section class="section-panel section-panel--globe-nav" data-globe-navigation-block="true">
      <p class="kicker">Navigation</p>
      <h2>Choose a country from the globe</h2>
      <p>
        Use the globe to focus on country panel, or use the
        country buttons below if standard controls are more convenient.
      </p>
      <div class="globe-nav__surface">
        ${globeMarkup}
      </div>
      <div class="globe-nav__controls" aria-label="Supported country controls">
        ${buttonsMarkup}
      </div>
    </section>
  `;
}

export function renderCountryPanelRegionMarkup({ selectedCountryCode, selectedCountryModel, chartRenderer }) {
  const normalizedSelectedCountryCode = normalizeCountryCode(selectedCountryCode);
  const panelInnerMarkup =
    selectedCountryModel && normalizedSelectedCountryCode
      ? renderCountrySectionMarkup(selectedCountryModel, { chartRenderer })
      : `
        <section class="empty-state country-panel-region__empty-state" data-country-panel-empty-state="true">
          <p class="kicker">Country panel</p>
          <h2>Select a supported country to begin.</h2>
          <p>
            Choose Lithuania, Latvia, Estonia, or Denmark from the globe or the country controls above
            to open that country's current indicator panel here.
          </p>
        </section>
      `;

  return `
    <section
      class="country-panel-region"
      data-country-panel-region="true"
      data-selected-country-code="${escapeAttribute(normalizedSelectedCountryCode)}"
    >
      ${panelInnerMarkup}
    </section>
  `;
}

function renderSectionDisclosure({ disclosureId, title, bodyMarkup, summaryItems = [], isOpen = false, variant = "country" }) {
  const itemsMarkup = summaryItems
    .filter((item) => typeof item === "string" && item.trim().length > 0)
    .map((item) => `<span class="indicator-summary__item">${escapeHtml(item)}</span>`)
    .join("");

  return `
    <details class="section-disclosure section-disclosure--${escapeAttribute(variant)}"${isOpen ? " open" : ""}>
      <summary
        class="section-disclosure__summary"
        aria-label="${escapeAttribute(`Toggle ${title} section`)}"
        data-ui-disclosure-toggle
        data-disclosure-id="${escapeAttribute(disclosureId)}"
      >
        <span class="section-disclosure__summary-inner">
          <span class="section-disclosure__title">${escapeHtml(title)}</span>
          ${itemsMarkup ? `<span class="indicator-summary" aria-hidden="true">${itemsMarkup}</span>` : ""}
        </span>
      </summary>
      <div class="section-disclosure__body">
        ${bodyMarkup}
      </div>
    </details>
  `;
}

function formatDisclosureCount(count, singularLabel, pluralLabel) {
  return `${count} ${count === 1 ? singularLabel : pluralLabel}`;
}

function buildForecastSectionSummaryItems(forecast, forecastLoadError) {
  if (forecastLoadError) {
    return ["Forecast unavailable"];
  }

  if (!forecast || typeof forecast !== "object") {
    return ["No forecast payload"];
  }

  const rowCount = Number.isFinite(forecast?.row_count) ? forecast.row_count : Array.isArray(forecast?.rows) ? forecast.rows.length : 0;
  const status = typeof forecast?.status === "string" && forecast.status.trim().length > 0 ? forecast.status.trim() : "unknown";

  return [formatDisclosureCount(rowCount, "forecast row", "forecast rows"), `Status: ${status}`];
}

function renderCountryForecastSection(forecast, forecastLoadError) {
  if (forecastLoadError) {
    return `
      <p class="indicator-state-message">
        Forecast data is temporarily unavailable for this country, but the rest of the country section remains available.
      </p>
    `;
  }

  if (!forecast || typeof forecast !== "object") {
    return `
      <p class="indicator-state-message">
        No forecast payload was staged for this country yet.
      </p>
    `;
  }

  const notes = Array.isArray(forecast?.notes)
    ? forecast.notes.filter((note) => typeof note === "string" && note.trim().length > 0)
    : [];
  const rows = Array.isArray(forecast?.rows) ? forecast.rows.filter((row) => row && typeof row === "object") : [];
  const status = typeof forecast?.status === "string" && forecast.status.trim().length > 0 ? forecast.status.trim() : "unknown";
  const rowCount = Number.isFinite(forecast?.row_count) ? forecast.row_count : rows.length;
  const notesMarkup = notes.length
    ? `
      <ul class="forecast-notes">
        ${notes.map((note) => `<li>${escapeHtml(note)}</li>`).join("")}
      </ul>
    `
    : "";

  if (!rows.length) {
    return `
      <div class="forecast-summary">
        <p class="body-muted">
          Forecast status: ${escapeHtml(status)}.
        </p>
        <p class="indicator-state-message">
          No forecast rows are available for this country under the current publication settings.
        </p>
        ${notesMarkup}
      </div>
    `;
  }

  const rowMarkup = rows.map((row) => renderForecastRow(row)).join("");

  return `
    <div class="forecast-summary">
      <p>
        These CCOutline forecasts are educational projections based on the latest published data shown for
        each indicator. They are not observed history and should be read together with the interpretation
        and limitation notes below.
      </p>
      <p class="body-muted">
        Forecast status: ${escapeHtml(status)} • ${escapeHtml(String(rowCount))} forecast row${rowCount === 1 ? "" : "s"} shown.
      </p>
      ${notesMarkup}
      <div class="forecast-rows">
        ${rowMarkup}
      </div>
    </div>
  `;
}

function renderForecastRow(row) {
  const title = String(row?.indicator_label || row?.target_indicator_name || row?.indicator_name || row?.indicator_id || "Forecast").trim();
  const forecastYear = row?.forecast_year;
  const forecastValue = formatScalar(row?.forecast_value);
  const forecastUnit = String(row?.forecast_unit || "n/a").trim() || "n/a";
  const latestObservedYear = resolveForecastLatestObservedYear(row);
  const splitCount = Number.isFinite(row?.metric_summary?.split_count) ? row.metric_summary.split_count : null;
  const transformMethod = resolveForecastTransformMethod(row);
  const transformLabel = formatForecastTransformLabel(transformMethod);
  const summaryItems = [
    forecastYear ? `CCOutline forecast: ${forecastYear}` : "CCOutline forecast year unavailable",
    `${forecastValue || "n/a"} ${forecastUnit}`,
  ];

  if (latestObservedYear !== null) {
    summaryItems.push(`Selected source through ${latestObservedYear}`);
  }

  if (splitCount !== null) {
    summaryItems.push(`${splitCount} split${splitCount === 1 ? "" : "s"}`);
  }

  if (transformLabel) {
    summaryItems.push(transformLabel);
  }

  const transformedUnitMarkup =
    transformMethod && transformMethod !== "none"
      ? `
        <p class="indicator-state-message">
          This forecast is shown in transformed units rather than the raw indicator level, so compare it as a
          model output rather than as a direct raw-value estimate.
        </p>
      `
      : "";

  return `
    <article class="forecast-row">
      <h4>${escapeHtml(title)}</h4>
      <p class="indicator-summary" aria-label="Forecast row summary">
        ${summaryItems.map((item) => `<span class="indicator-summary__item">${escapeHtml(item)}</span>`).join("")}
      </p>
      <p>
        <strong>Interpretation:</strong> ${escapeHtml(String(row?.interpretation || "No interpretation text was exported."))}
      </p>
      ${transformedUnitMarkup}
      <p class="body-muted">
        ${escapeHtml(String(row?.limitations || "No limitation text was exported."))}
      </p>
    </article>
  `;
}

function resolveForecastTransformMethod(row) {
  const exportedMethod = String(row?.transform_method || "").trim();
  if (exportedMethod) {
    return exportedMethod;
  }

  return parseForecastTransformMethod(row?.selected_candidate);
}

function parseForecastTransformMethod(selectedCandidate) {
  const candidateKey = String(selectedCandidate || "").trim();
  if (!candidateKey.includes("__")) {
    return "";
  }

  const parts = candidateKey.split("__");
  return parts.length >= 2 ? String(parts[1] || "").trim() : "";
}

function formatForecastTransformLabel(transformMethod) {
  switch (String(transformMethod || "").trim()) {
    case "pct_change_yoy":
    case "log_diff_yoy":
      return "Shown as yearly change";
    case "pp_change_lag1":
      return "Shown as percentage-point change";
    default:
      return "";
  }
}

function resolveForecastLatestObservedYear(row) {
  if (Number.isFinite(row?.latest_observed_year)) {
    return row.latest_observed_year;
  }

  if (Number.isFinite(row?.history_preview?.max_year)) {
    return row.history_preview.max_year;
  }

  return null;
}

function renderIndicatorGlossary(indicatorViewModels) {
  if (!indicatorViewModels.length) {
    return "<p>No indicators were exported for this country.</p>";
  }

  const rows = indicatorViewModels
    .map(
      (indicatorViewModel) => `
        <tr>
          <td>${escapeHtml(indicatorViewModel.indicatorId)}</td>
          <td>${escapeHtml(indicatorViewModel.indicatorLabel)}</td>
          <td>${escapeHtml(indicatorViewModel.sourceLabel)}</td>
          <td>${escapeHtml(indicatorViewModel.unit)}</td>
          <td>${escapeHtml(String(indicatorViewModel.observationCount))}</td>
          <td>${escapeHtml(formatYearRange(indicatorViewModel.yearRange))}</td>
        </tr>
      `,
    )
    .join("");

  return `
    <table>
      <thead>
        <tr>
          <th>Indicator ID</th>
          <th>Label</th>
          <th>Source</th>
          <th>Unit</th>
          <th>Obs</th>
          <th>Range</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

function renderIndicatorDisclosures(indicatorViewModels, uiState, chartRenderer, forecast) {
  if (!indicatorViewModels.length) {
    return "<p>No chart-backed indicator sections are available for this country.</p>";
  }

  return indicatorViewModels
    .map((indicatorViewModel, index) => renderIndicatorDisclosure(indicatorViewModel, index, uiState, chartRenderer, forecast))
    .join("");
}

function renderCountryAnalyticsSection(analyticsState, uiState, chartRenderer) {
  const overrideSummaryText = analyticsState.controls.activeOverrideCount
    ? `${analyticsState.controls.activeOverrideCount} indicator override${analyticsState.controls.activeOverrideCount === 1 ? "" : "s"} currently active.`
    : "No per-indicator overrides are active right now.";
  const stateLabel = analyticsState.controls.hasChanges
    ? "Modified from published settings."
    : "Matches published settings.";
  const renderableTimelineCount = analyticsState.rendering.timelines.series.filter(
    (series) => series.renderablePointCount > 0,
  ).length;
  const visualStateNoteId = `${analyticsState.countryCode}-analytics-visual-state-note`;
  const rawTableStateNoteId = `${analyticsState.countryCode}-analytics-table-state-note`;
  const controlsMarkup = renderAnalyticsControls(analyticsState);
  const summaryMarkup = renderSectionDisclosure({
    disclosureId: uiState.analyticsSections.summary.disclosureId,
    isOpen: uiState.analyticsSections.summary.open,
    variant: "nested",
    title: "Analytics state summary",
    summaryItems: [
      stateLabel.replace(/\.$/, ""),
      `${analyticsState.rawTable.renderableRowCount} numeric z-score row${analyticsState.rawTable.renderableRowCount === 1 ? "" : "s"}`,
    ],
    bodyMarkup: renderAnalyticsStateSummarySection({
      analyticsState,
      overrideSummaryText,
      renderableTimelineCount,
      stateLabel,
    }),
  });
  const overrideMarkup = renderSectionDisclosure({
    disclosureId: uiState.analyticsSections.overrides.disclosureId,
    isOpen: uiState.analyticsSections.overrides.open,
    variant: "nested",
    title: "Per-indicator overrides",
    summaryItems: [
      `${analyticsState.controls.activeOverrideCount} active override${analyticsState.controls.activeOverrideCount === 1 ? "" : "s"}`,
      formatDisclosureCount(analyticsState.controls.indicatorOverrides.length, "indicator", "indicators"),
    ],
    bodyMarkup: renderAnalyticsOverridesTable(analyticsState),
  });

  if (!analyticsState.hasRows) {
    return `
      <div data-analytics-country-code="${escapeAttribute(analyticsState.countryCode)}">
        ${controlsMarkup}
        ${summaryMarkup}
        ${overrideMarkup}
        <p class="indicator-state-message">
          No numeric yearly rows are available for the analytics view in this country yet.
        </p>
        ${renderSectionDisclosure({
          disclosureId: uiState.analyticsSections.rawTable.disclosureId,
          isOpen: uiState.analyticsSections.rawTable.open,
          variant: "nested",
          title: "Raw z-score table",
          summaryItems: ["0 numeric z-score rows", `${analyticsState.rowCount} exported row${analyticsState.rowCount === 1 ? "" : "s"}`],
          bodyMarkup: `
            <p class="body-muted">
              No raw z-score table is available yet because this country has no numeric yearly rows available for the analytics view.
            </p>
          `,
        })}
      </div>
    `;
  }

  const rowsMarkup = analyticsState.rawTableRows
    .map(
      (row) => `
        <tr>
          ${analyticsState.rawTable.columns
            .map((column) => `<td>${renderAnalyticsRawTableCell(row, column.key)}</td>`)
            .join("")}
        </tr>
      `,
    )
    .join("");

  return `
    <div data-analytics-country-code="${escapeAttribute(analyticsState.countryCode)}">
      ${controlsMarkup}
      ${summaryMarkup}
      ${overrideMarkup}
      ${renderSparseStateMessage(analyticsState)}
      ${renderAnalyticsVisuals(analyticsState, chartRenderer, {
        visualStateNoteId,
        rawTableStateNoteId,
      })}
      ${renderSectionDisclosure({
        disclosureId: uiState.analyticsSections.rawTable.disclosureId,
        isOpen: uiState.analyticsSections.rawTable.open,
        variant: "nested",
        title: "Raw z-score table",
        summaryItems: [
          `${analyticsState.rawTable.renderableRowCount} numeric z-score row${analyticsState.rawTable.renderableRowCount === 1 ? "" : "s"}`,
          `${analyticsState.rowCount} row${analyticsState.rowCount === 1 ? "" : "s"} in view`,
        ],
        bodyMarkup: `
          <p class="body-muted" id="${escapeAttribute(rawTableStateNoteId)}">
            The table below shows the values, z-scores, and row statuses under the current analytics settings.
          </p>
          <div class="analytics-table-wrap" aria-describedby="${escapeAttribute(rawTableStateNoteId)}">
            <table>
              <thead>
                <tr>
                  ${analyticsState.rawTable.columns.map((column) => `<th>${escapeHtml(column.label)}</th>`).join("")}
                </tr>
              </thead>
              <tbody>${rowsMarkup}</tbody>
            </table>
          </div>
        `,
      })}
    </div>
  `;
}

function renderAnalyticsControls(analyticsState) {
  const globalMode = analyticsState.controls.global.values.mode;
  return `
    <div class="analytics-summary">
      <p>
        These analytics views help visitors compare the published yearly values under the current settings.
      </p>
      <div class="analytics-controls">
        <div class="analytics-controls__header">
          <div>
            <h4>Global defaults</h4>
            <p class="body-muted">
              Use these controls to review how the analytics views change under the available settings. In static
              baseline, minimum observations stays visible but disabled because changing it does not alter the current
              country results. Baseline start year and exclude-current behavior stay aligned to the published settings
              unless a later tranche promotes them into the UI.
            </p>
          </div>
          <button type="button" data-analytics-reset>Reset to published settings</button>
        </div>
        <div class="analytics-controls__grid">
          ${renderModeControl({
            idPrefix: `${analyticsState.countryCode}-global`,
            dataAttribute: "data-analytics-global-control",
            controlName: "mode",
            value: analyticsState.controls.global.values.mode,
            disabled: false,
          })}
          ${renderRangeControl({
            idPrefix: `${analyticsState.countryCode}-global`,
            dataAttribute: "data-analytics-global-control",
            controlName: "rollingWindowYears",
            label: "Rolling window",
            value: analyticsState.controls.global.values.rollingWindowYears,
            bounds: analyticsState.controls.bounds.rollingWindowYears,
            unitLabel: "years",
            disabled: shouldDisableRollingWindowControl({ mode: globalMode }),
          })}
          ${renderRangeControl({
            idPrefix: `${analyticsState.countryCode}-global`,
            dataAttribute: "data-analytics-global-control",
            controlName: "minObsForZscore",
            label: "Minimum observations",
            value: analyticsState.controls.global.values.minObsForZscore,
            bounds: analyticsState.controls.bounds.minObsForZscore,
            unitLabel: "obs",
            disabled: shouldDisableMinObsControl({ mode: globalMode }),
          })}
        </div>
      </div>
    </div>
  `;
}

function renderAnalyticsStateSummarySection({
  analyticsState,
  overrideSummaryText,
  renderableTimelineCount,
  stateLabel,
}) {
  return `
    <div class="analytics-summary">
      <table>
        <thead>
          <tr>
            <th>Setting</th>
            <th>Active state</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>Current country setting</td>
            <td>${escapeHtml(analyticsState.defaultSummaryText)}</td>
          </tr>
          <tr>
            <td>Published setting</td>
            <td>${escapeHtml(analyticsState.exportDefaultSummaryText)}</td>
          </tr>
          <tr>
            <td>Overrides</td>
            <td>${escapeHtml(overrideSummaryText)}</td>
          </tr>
          <tr>
            <td>State</td>
            <td>${escapeHtml(stateLabel)}</td>
          </tr>
          <tr>
            <td>Rows in analytics view</td>
            <td>${escapeHtml(`${analyticsState.rowCount} rows across ${analyticsState.indicatorCount} indicators`)}</td>
          </tr>
          <tr>
            <td>Renderable z-scores</td>
            <td>${escapeHtml(`${analyticsState.rawTable.renderableRowCount} rows currently produce numeric z-scores`)}</td>
          </tr>
          <tr>
            <td>Visual coverage</td>
            <td>${escapeHtml(
              `${analyticsState.rendering.summary.renderableCellCount} heatmap cells across ${analyticsState.rendering.summary.yearCount} years and ${renderableTimelineCount} timeline series are currently visible`,
            )}</td>
          </tr>
        </tbody>
      </table>
      ${renderAnalyticsStatusSummary(analyticsState)}
    </div>
  `;
}

function renderAnalyticsVisuals(analyticsState, chartRenderer, { visualStateNoteId, rawTableStateNoteId }) {
  const heatmapMarkup =
    analyticsState.rendering.heatmap.hasRenderableCells &&
    typeof chartRenderer.renderCountryAnalyticsHeatmap === "function"
      ? chartRenderer.renderCountryAnalyticsHeatmap({ analyticsState })
      : "";
  const timelineMarkup =
    analyticsState.rendering.timelines.hasRenderableSeries &&
    typeof chartRenderer.renderCountryAnalyticsTimeline === "function"
      ? chartRenderer.renderCountryAnalyticsTimeline({ analyticsState })
      : "";
  const coherenceText = `These visuals and the raw z-score table below reflect the same current analytics settings: ${analyticsState.rendering.summary.renderableCellCount} renderable heatmap cells across ${analyticsState.rendering.summary.yearCount} years, ${analyticsState.rawTable.renderableRowCount} numeric z-score rows, and ${analyticsState.controls.activeOverrideCount} active override${analyticsState.controls.activeOverrideCount === 1 ? "" : "s"}.`;

  return `
    <div class="analytics-visuals" aria-label="Analytics visuals">
      <p class="analytics-visuals__state-note" id="${escapeAttribute(visualStateNoteId)}">
        ${escapeHtml(coherenceText)}
      </p>
      <div class="analytics-visual">
        <h4>Analytics heatmap</h4>
        <p class="body-muted">
          The heatmap shows how each indicator's z-scores change over time under the current settings: cooler colors
          mark lower z-scores, warmer colors mark higher z-scores, and gray cells stay visible when no numeric
          z-score is available.
        </p>
        ${renderAnalyticsVisualBody(heatmapMarkup, {
          visualKind: "heatmap",
          emptyReason: analyticsState.rendering.heatmap.emptyReason,
          visualStateNoteId,
          rawTableStateNoteId,
        })}
      </div>
      <div class="analytics-visual">
        <h4>Timeline and anomaly view</h4>
        <p class="body-muted">
          The timeline view uses the same z-scores and highlights the strongest swings without hiding the rest of the
          indicator history.
        </p>
        ${renderAnalyticsVisualBody(timelineMarkup, {
          visualKind: "timeline",
          emptyReason: analyticsState.rendering.timelines.emptyReason,
          visualStateNoteId,
          rawTableStateNoteId,
        })}
      </div>
    </div>
  `;
}

function renderAnalyticsVisualBody(markup, { visualKind, emptyReason, visualStateNoteId, rawTableStateNoteId }) {
  if (!markup) {
    return renderAnalyticsVisualEmptyState(visualKind, emptyReason);
  }

  return `
    <div
      class="analytics-chart-scroller"
      tabindex="0"
      aria-label="${escapeAttribute(`Scrollable ${visualKind} chart`)}"
      aria-describedby="${escapeAttribute(`${visualStateNoteId} ${rawTableStateNoteId}`)}"
    >
      ${markup}
    </div>
  `;
}

function renderAnalyticsStatusSummary(analyticsState) {
  if (!analyticsState.statusSummary.statusCounts.length) {
    return "";
  }

  const items = analyticsState.statusSummary.statusCounts
    .map((entry) => `<span class="indicator-summary__item">${escapeHtml(`${entry.label}: ${entry.count}`)}</span>`)
    .join("");

  return `
    <p class="body-muted">Row outcomes under the current settings:</p>
    <p class="indicator-summary" aria-label="Analytics status summary">
      ${items}
    </p>
  `;
}

function renderSparseStateMessage(analyticsState) {
  if (analyticsState.sectionState === "ready") {
    return "";
  }

  if (analyticsState.sectionState === "no_renderable_zscores") {
    return `
      <p class="indicator-state-message">
        Rows are available, but none produce a numeric z-score under the current settings. The table keeps those rows
        visible with their statuses and normalization-observation counts instead of hiding them.
      </p>
    `;
  }

  if (analyticsState.sectionState === "partial") {
    return `
      <p class="indicator-data-note">
        Some rows produce numeric z-scores and some remain unavailable under the current settings. The raw table keeps
        both kinds visible so the sparse parts of the series remain auditable.
      </p>
    `;
  }

  return "";
}

function renderAnalyticsVisualEmptyState(kind, emptyReason) {
  if (emptyReason === "no_renderable_zscores") {
    return `
      <p class="indicator-state-message">
        The current settings do not produce any numeric z-scores, so this ${escapeHtml(kind)} is hidden instead of
        showing an empty visual.
      </p>
    `;
  }

  return `
    <p class="indicator-state-message">
      No exported numeric rows are available yet for this ${escapeHtml(kind)}.
    </p>
  `;
}

function renderAnalyticsRawTableCell(row, columnKey) {
  if (columnKey === "year") {
    return escapeHtml(String(row.year ?? ""));
  }
  if (columnKey === "value" || columnKey === "recomputedZscore" || columnKey === "normalizationObs") {
    return escapeHtml(formatScalar(row[columnKey]));
  }
  if (columnKey === "isProjection") {
    return escapeHtml(formatProjectionFlag(row.isProjection));
  }
  return escapeHtml(row[columnKey] ?? "");
}

function renderAnalyticsOverridesTable(overrideSummaries) {
  const rows = overrideSummaries.controls.indicatorOverrides
    .map(
      (overrideSummary) => {
        const modeControlDisabled = !overrideSummary.hasActiveOverride;
        const rollingWindowDisabled =
          modeControlDisabled || shouldDisableRollingWindowControl({ mode: overrideSummary.currentValues.mode });
        const minObsDisabled =
          modeControlDisabled || shouldDisableMinObsControl({ mode: overrideSummary.currentValues.mode });

        return `
        <tr>
          <td>${escapeHtml(overrideSummary.indicatorLabel)}</td>
          <td>
            <label class="analytics-toggle">
              <input
                type="checkbox"
                data-analytics-override-toggle
                data-indicator-id="${escapeAttribute(overrideSummary.indicatorId)}"
                ${overrideSummary.hasActiveOverride ? "checked" : ""}
              />
              <span>${escapeHtml(overrideSummary.hasActiveOverride ? "Override active" : "Use country defaults")}</span>
            </label>
            <p class="body-muted analytics-cell-note">
              ${escapeHtml(
                overrideSummary.hasExportOverride
                  ? "The published export ships with an indicator-specific override for this series."
                  : "This indicator inherits the country-level defaults in the published export.",
              )}
            </p>
          </td>
          <td>
            ${renderModeControl({
              idPrefix: `${overrideSummaries.countryCode}-${overrideSummary.indicatorId}`,
              dataAttribute: "data-analytics-override-control",
              controlName: "mode",
              value: overrideSummary.currentValues.mode,
              disabled: modeControlDisabled,
              extraAttributes: `data-indicator-id="${escapeAttribute(overrideSummary.indicatorId)}"`,
            })}
          </td>
          <td>
            ${renderRangeControl({
              idPrefix: `${overrideSummaries.countryCode}-${overrideSummary.indicatorId}`,
              dataAttribute: "data-analytics-override-control",
              controlName: "rollingWindowYears",
              label: "Rolling window",
              value: overrideSummary.currentValues.rollingWindowYears,
              bounds: overrideSummaries.controls.bounds.rollingWindowYears,
              unitLabel: "years",
              disabled: rollingWindowDisabled,
              extraAttributes: `data-indicator-id="${escapeAttribute(overrideSummary.indicatorId)}"`,
              compact: true,
            })}
          </td>
          <td>
            ${renderRangeControl({
              idPrefix: `${overrideSummaries.countryCode}-${overrideSummary.indicatorId}`,
              dataAttribute: "data-analytics-override-control",
              controlName: "minObsForZscore",
              label: "Minimum observations",
              value: overrideSummary.currentValues.minObsForZscore,
              bounds: overrideSummaries.controls.bounds.minObsForZscore,
              unitLabel: "obs",
              disabled: minObsDisabled,
              extraAttributes: `data-indicator-id="${escapeAttribute(overrideSummary.indicatorId)}"`,
              compact: true,
            })}
          </td>
          <td>
            <div>${escapeHtml(overrideSummary.policySummaryText)}</div>
            <p class="body-muted analytics-cell-note">
              ${escapeHtml(overrideSummary.isDirty ? "Changed from export baseline." : "Matches export baseline.")}
            </p>
          </td>
        </tr>
      `;
      },
    )
    .join("");

  return `
    <div class="analytics-table-wrap">
      <table>
        <thead>
          <tr>
            <th>Indicator</th>
            <th>Override</th>
            <th>Mode</th>
            <th>Rolling window</th>
            <th>Min obs</th>
            <th>Effective state</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </div>
  `;
}

function shouldDisableRollingWindowControl({ mode }) {
  return mode === "static_baseline";
}

function shouldDisableMinObsControl({ mode }) {
  return mode === "static_baseline";
}

function renderModeControl({ idPrefix, dataAttribute, controlName, value, disabled, extraAttributes = "" }) {
  const controlId = `${idPrefix}-${controlName}`;
  return `
    <label class="analytics-control" for="${escapeAttribute(controlId)}">
      <span class="analytics-control__label">Normalization mode</span>
      <select
        id="${escapeAttribute(controlId)}"
        ${dataAttribute}="${escapeAttribute(controlName)}"
        ${extraAttributes}
        ${disabled ? "disabled" : ""}
      >
        <option value="static_baseline" ${value === "static_baseline" ? "selected" : ""}>Static baseline</option>
        <option value="rolling_trailing" ${value === "rolling_trailing" ? "selected" : ""}>Rolling trailing</option>
      </select>
    </label>
  `;
}

function renderRangeControl({
  idPrefix,
  dataAttribute,
  controlName,
  label,
  value,
  bounds,
  unitLabel,
  disabled,
  extraAttributes = "",
  compact = false,
}) {
  const controlId = `${idPrefix}-${controlName}`;
  return `
    <label class="analytics-control${compact ? " analytics-control--compact" : ""}" for="${escapeAttribute(controlId)}">
      <span class="analytics-control__label">${escapeHtml(label)}</span>
      <input
        id="${escapeAttribute(controlId)}"
        type="range"
        min="${escapeAttribute(String(bounds.min))}"
        max="${escapeAttribute(String(bounds.max))}"
        step="1"
        value="${escapeAttribute(String(value))}"
        ${dataAttribute}="${escapeAttribute(controlName)}"
        ${extraAttributes}
        ${disabled ? "disabled" : ""}
      />
      <span class="analytics-control__value">${escapeHtml(`${value} ${unitLabel}`)}</span>
    </label>
  `;
}

function renderIndicatorDisclosure(indicatorViewModel, index, uiState, chartRenderer, forecast) {
  const indicatorKey = buildIndicatorDisclosureKey(indicatorViewModel.indicatorId, index);
  const indicatorDisclosureState = uiState.indicatorDisclosures[indicatorKey] || {
    disclosureId: indicatorKey,
    open: false,
    rawDataDisclosureId: `${indicatorKey}-raw-data`,
    rawDataOpen: false,
  };
  const forecastOverlay = findCompatibleForecastOverlay({ indicatorViewModel, forecast });
  const forecastChartDisclosure = findForecastChartDisclosure({ indicatorViewModel, forecast });
  const chartMarkup = indicatorViewModel.hasRenderableChart
    ? chartRenderer.renderIndicatorChart({
        indicatorViewModel,
        forecastOverlay,
        forecastChartDisclosure,
      })
    : "";
  const bodyMarkup = renderIndicatorDisclosureBody(indicatorViewModel, chartMarkup, indicatorDisclosureState);

  return `
    <details class="indicator-disclosure"${indicatorDisclosureState.open ? " open" : ""}>
      <summary
        class="indicator-disclosure__summary"
        aria-label="Toggle indicator details"
        data-ui-disclosure-toggle
        data-disclosure-id="${escapeAttribute(indicatorDisclosureState.disclosureId)}"
      >
        <span class="indicator-disclosure__summary-inner">
          <span class="indicator-disclosure__title">${escapeHtml(indicatorViewModel.title)}</span>
          ${renderIndicatorSummary(indicatorViewModel)}
        </span>
      </summary>
      <div class="indicator-disclosure__body">
        ${bodyMarkup}
      </div>
    </details>
  `;
}

function renderIndicatorDisclosureBody(indicatorViewModel, chartMarkup, indicatorDisclosureState) {
  if (!indicatorViewModel.hasPoints) {
    return `
      <p class="indicator-state-message">${escapeHtml(indicatorViewModel.missingDataMessage)}</p>
    `;
  }

  const rows = indicatorViewModel.points
    .map(
      (point) => `
        <tr>
          <td>${escapeHtml(point.year ?? "")}</td>
          <td>${escapeHtml(formatScalar(point.value))}</td>
          <td>${escapeHtml(formatScalar(point.zscore))}</td>
          <td>${escapeHtml(point.status || "")}</td>
          <td>${escapeHtml(formatProjectionFlag(point.is_projection))}</td>
        </tr>
      `,
      )
      .join("");
  const chartStateMarkup = indicatorViewModel.chartAvailabilityMessage
    ? `<p class="indicator-state-message">${escapeHtml(indicatorViewModel.chartAvailabilityMessage)}</p>`
    : "";
  const missingDataMarkup =
    indicatorViewModel.missingDataMessage && indicatorViewModel.hasRenderableChart
      ? `<p class="indicator-data-note">${escapeHtml(indicatorViewModel.missingDataMessage)}</p>`
      : "";
  const rawTableMarkup = renderIndicatorRawDataTable(rows, indicatorDisclosureState.rawDataDisclosureId, indicatorDisclosureState.rawDataOpen);

  return `
    ${chartMarkup}
    ${chartStateMarkup}
    ${missingDataMarkup}
    ${rawTableMarkup}
  `;
}

function renderIndicatorSummary(indicatorViewModel) {
  const summaryItems = Array.isArray(indicatorViewModel.summaryItems) ? indicatorViewModel.summaryItems : [];

  if (!summaryItems.length) {
    return "";
  }

  const itemsMarkup = summaryItems
    .map(
      (item) => `
        <span class="indicator-summary__item">${escapeHtml(item)}</span>
      `,
    )
    .join("");

  return `
    <p class="indicator-summary" aria-label="Indicator summary">
      ${itemsMarkup}
    </p>
  `;
}

function renderIndicatorRawDataTable(rows, disclosureId, isOpen) {
  return `
    <details class="indicator-raw-data"${isOpen ? " open" : ""}>
      <summary
        class="indicator-raw-data__summary"
        aria-label="Toggle raw yearly rows"
        data-ui-disclosure-toggle
        data-disclosure-id="${escapeAttribute(disclosureId)}"
      >
        <span class="indicator-raw-data__summary-label">Raw yearly rows</span>
      </summary>
      <div class="indicator-raw-data__body">
        <table>
          <thead>
            <tr>
              <th>Year</th>
              <th>Value</th>
              <th>Z-score</th>
              <th>Status</th>
              <th>Projection</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    </details>
  `;
}

function buildFallbackCountryUiState(indicatorViewModels) {
  const indicatorDisclosures = {};

  indicatorViewModels.forEach((indicatorViewModel, index) => {
    const indicatorKey = buildIndicatorDisclosureKey(indicatorViewModel.indicatorId, index);
    indicatorDisclosures[indicatorKey] = {
      disclosureId: indicatorKey,
      open: false,
      rawDataDisclosureId: `${indicatorKey}-raw-data`,
      rawDataOpen: false,
    };
  });

  return {
    countrySections: {
      glossary: { disclosureId: "fallback-glossary", open: false },
      analytics: { disclosureId: "fallback-analytics", open: false },
      forecast: { disclosureId: "fallback-forecast", open: false },
      charts: { disclosureId: "fallback-charts", open: false },
    },
    analyticsSections: {
      summary: { disclosureId: "fallback-analytics-summary", open: false },
      overrides: { disclosureId: "fallback-analytics-overrides", open: false },
      rawTable: { disclosureId: "fallback-analytics-raw-table", open: false },
    },
    indicatorDisclosures,
  };
}
