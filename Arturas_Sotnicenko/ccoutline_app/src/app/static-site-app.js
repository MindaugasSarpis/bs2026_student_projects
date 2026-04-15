import { ANALYTICS_RUNTIME_CONFIG } from "./config/analytics-config.js";
import { readStoredConsentState, writeStoredConsentDecision } from "./consent/consent-storage.js";
import { fetchCountriesPayload, fetchCountryModel, fetchGlobeWorldGeometry } from "./data/site-data-loader.js";
import { analyticsLegalLinkClicked, analyticsPageViewed } from "./analytics/tracking-actions.js";
import { resolveLegalPage } from "./legal/legal-page-config.js";
import { syncAnalyticsTimelineInteractions } from "./charts/analytics-timeline-interactions.js";
import { createChartRendererFacade } from "./charts/chart-renderer-facade.js";
import { createD3AnalyticsChartRenderer } from "./charts/d3-analytics-chart-renderer.js";
import { createD3IndicatorChartRenderer } from "./charts/d3-indicator-chart-renderer.js";
import { createD3GlobeRenderer } from "./globe/d3-globe-renderer.js";
import { createNoopAnalyticsChartRenderer } from "./charts/noop-analytics-chart-renderer.js";
import { createNoopIndicatorChartRenderer } from "./charts/noop-indicator-chart-renderer.js";
import {
  renderCountryPanelRegionMarkup,
  renderCountrySectionMarkup,
  renderGlobeNavigationMarkup,
  renderLoading,
  renderPage,
  renderRootErrorPage,
  renderStandaloneLegalPage,
} from "./rendering/page-renderer.js";
import {
  analyticsControlsReset,
  analyticsCountryStateHydrated,
  analyticsGlobalControlsUpdated,
  analyticsIndicatorOverrideControlsUpdated,
  analyticsIndicatorOverrideToggled,
  analyticsStateReset,
} from "./state/analytics-slice.js";
import { appBootstrapFailed, appBootstrapStarted, appBootstrapSucceeded } from "./state/app-slice.js";
import { consentAccepted, consentDeclined, consentStateHydrated } from "./state/consent-slice.js";
import {
  countriesPayloadReceived,
  countriesStateReset,
  countryPayloadLoadFinished,
  countryPayloadLoadStarted,
} from "./state/countries-slice.js";
import {
  createSelectCountryAnalyticsState,
  createSelectCountryUiState,
  selectAppRenderState,
  selectBootstrapStatus,
  selectCountryAnalyticsControlsStateByCode,
  selectCountryModelByCode,
  selectOrderedCountryEntries,
  selectSelectedCountryCode,
  selectSelectedCountryModel,
  selectConsentState,
} from "./state/selectors.js";
import { createAppStore } from "./state/store.js";
import { uiCountryStateHydrated, uiDisclosureToggled, uiSelectedCountrySet, uiStateReset } from "./state/ui-slice.js";

export function startStaticSiteApp({
  appRoot,
  analyticsConfig = ANALYTICS_RUNTIME_CONFIG,
  store = createAppStore(),
}) {
  const countryAnalyticsSelectorByCode = new Map();
  const countryUiSelectorByCode = new Map();
  const timelineSelectionStateByCountry = new Map();
  const runtimeAnalyticsConfig = analyticsConfig;
  const legalPage = resolveLegalPage(globalThis.window?.location?.pathname || "/");
  const documentRef = globalThis.document;
  let lastRenderContext = null;
  let globeWorldGeometry = null;
  let scrollLockSnapshot = null;
  const chartRenderer = createChartRendererFacade({
    indicatorChartRenderer: createD3IndicatorChartRenderer({
      fallbackIndicatorChartRenderer: createNoopIndicatorChartRenderer(),
    }),
    analyticsChartRenderer: createD3AnalyticsChartRenderer({
      fallbackAnalyticsChartRenderer: createNoopAnalyticsChartRenderer(),
    }),
  });
  const globeRenderer = createD3GlobeRenderer();

  if (!runtimeAnalyticsConfig?.ga4?.measurementId || !runtimeAnalyticsConfig?.consent?.decisionStorageKey) {
    throw new Error("analyticsConfig must expose GA4 identifiers and versioned consent storage keys.");
  }

  appRoot.addEventListener("change", handleAppInteraction);
  appRoot.addEventListener("click", handleAppInteraction);
  appRoot.addEventListener("keydown", handleAppInteraction);
  store.subscribe(render);

  bootstrap();

  async function bootstrap() {
    countryAnalyticsSelectorByCode.clear();
    countryUiSelectorByCode.clear();
    const storedConsentState = readStoredConsentState(runtimeAnalyticsConfig);
    store.dispatch(consentStateHydrated(storedConsentState));
    if (storedConsentState?.decision === "accepted") {
      dispatchPageView("initial_load");
    }
    if (legalPage) {
      return;
    }
    store.dispatch(appBootstrapStarted());
    store.dispatch(analyticsStateReset());
    store.dispatch(uiStateReset());

    try {
      globeWorldGeometry = await fetchGlobeWorldGeometry();
      const countriesPayload = await fetchCountriesPayload();
      store.dispatch(countriesPayloadReceived(countriesPayload));

      const countryEntries = selectOrderedCountryEntries(store.getState());
      await Promise.all(
        countryEntries.map(async (countryEntry) => {
          store.dispatch(countryPayloadLoadStarted({ countryCode: countryEntry?.country_code }));
          const countryModel = await fetchCountryModel(countryEntry);
          store.dispatch(countryPayloadLoadFinished(countryModel));
          store.dispatch(analyticsCountryStateHydrated(countryModel));
          store.dispatch(uiCountryStateHydrated(countryModel));
        }),
      );
      store.dispatch(appBootstrapSucceeded());
    } catch (error) {
      store.dispatch(countriesStateReset());
      store.dispatch(analyticsStateReset());
      store.dispatch(uiStateReset());
      store.dispatch(appBootstrapFailed(error instanceof Error ? error.message : "Unexpected application failure."));
    }
  }

  function render() {
    if (legalPage) {
      lastRenderContext = null;
      renderStandaloneLegalPage(appRoot, legalPage, selectConsentState(store.getState()));
      syncConsentModalState();
      return;
    }

    if (selectBootstrapStatus(store.getState()) === "loading") {
      lastRenderContext = null;
      renderLoading(appRoot, "Loading country data", selectConsentState(store.getState()));
      syncConsentModalState();
      return;
    }

    const appState = buildRenderAppState();
    if (appState.countriesError) {
      lastRenderContext = null;
      renderRootErrorPage(appRoot, appState.consentState);
      syncConsentModalState();
      return;
    }

    if (shouldRenderFullPage(appState, lastRenderContext)) {
      renderPage(appRoot, appState, { chartRenderer });
      syncAnalyticsTimelineInteractions(appRoot, {
        selectionStateByCountry: timelineSelectionStateByCountry,
      });
      syncConsentModalState();
      lastRenderContext = createRenderContext(appState);
      return;
    }

    if (didSelectedCountryChange(appState, lastRenderContext)) {
      const didPatchSelectionSurfaces = rerenderSelectionSurfaces(appState);
      if (!didPatchSelectionSurfaces) {
        renderPage(appRoot, appState, { chartRenderer });
      }
      syncAnalyticsTimelineInteractions(appRoot, {
        selectionStateByCountry: timelineSelectionStateByCountry,
      });
      lastRenderContext = createRenderContext(appState);
      return;
    }

    const changedCountryCodes = collectChangedCountryCodes(appState, lastRenderContext);
    if (!changedCountryCodes.length) {
      lastRenderContext = createRenderContext(appState);
      return;
    }

    const didPatchSections = rerenderCountrySections(appState, changedCountryCodes);
    if (!didPatchSections) {
      renderPage(appRoot, appState, { chartRenderer });
    }
    syncAnalyticsTimelineInteractions(appRoot, {
      selectionStateByCountry: timelineSelectionStateByCountry,
    });

    lastRenderContext = createRenderContext(appState);
  }

  function handleAppInteraction(event) {
    const target = event.target;
    if (!(target instanceof Element)) {
      return;
    }

    if (event.type === "keydown") {
      if (handleConsentModalKeydown(event)) {
        return;
      }
    }

    const consentAction = target.closest("[data-consent-action]");
    if (event.type === "click" && consentAction instanceof Element) {
      const consentSurface = readConsentSurface(consentAction);
      const storedDecision = writeStoredConsentDecision(
        runtimeAnalyticsConfig,
        consentAction.getAttribute("data-consent-action") || "",
      );
      if (storedDecision.decision === "accepted") {
        event.preventDefault();
        store.dispatch(consentAccepted({ surface: consentSurface, updatedAt: storedDecision.updatedAt }));
        dispatchPageView("consent_accept");
        return;
      }
      if (storedDecision.decision === "declined") {
        event.preventDefault();
        store.dispatch(consentDeclined({ surface: consentSurface, updatedAt: storedDecision.updatedAt }));
        return;
      }
    }

    const legalLink = target.closest("a[data-legal-link]");
    if (event.type === "click" && legalLink instanceof Element) {
      store.dispatch(
        analyticsLegalLinkClicked({
          currentPathname: globalThis.window?.location?.pathname || "/",
          href: legalLink.getAttribute("href") || "",
          linkKey: legalLink.getAttribute("data-legal-link") || "",
          placement: readLegalLinkPlacement(legalLink),
        }),
      );
    }

    const globeSelectionCountryCode = readGlobeSelectionCountryCode(event);
    if (globeSelectionCountryCode) {
      const selectedCountryModel = selectCountryModelByCode(store.getState(), globeSelectionCountryCode);
      if (selectedCountryModel) {
        event.preventDefault();
        store.dispatch(
          uiSelectedCountrySet({
            countryCode: globeSelectionCountryCode,
            source: event.type === "keydown" ? "globe_keyboard" : "globe_click",
          }),
        );
      }
      return;
    }

    const controlSelectionCountryCode = readCountrySelectionControlCode(event);
    if (controlSelectionCountryCode) {
      const selectedCountryModel = selectCountryModelByCode(store.getState(), controlSelectionCountryCode);
      if (selectedCountryModel) {
        event.preventDefault();
        store.dispatch(
          uiSelectedCountrySet({
            countryCode: controlSelectionCountryCode,
            source: "country_button",
          }),
        );
      }
      return;
    }

    const disclosureToggle = target.closest("[data-ui-disclosure-toggle]");
    if (event.type === "click" && disclosureToggle instanceof Element) {
      const disclosureId = disclosureToggle.getAttribute("data-disclosure-id") || "";
      if (disclosureId) {
        event.preventDefault();
        store.dispatch(uiDisclosureToggled({ disclosureId }));
        return;
      }
    }

    const analyticsContainer = target.closest("[data-analytics-country-code]");
    const countryCode = analyticsContainer?.getAttribute("data-analytics-country-code") || "";
    if (!countryCode) {
      return;
    }

    const model = selectCountryModelByCode(store.getState(), countryCode);
    const analyticsControlsState = selectCountryAnalyticsControlsStateByCode(store.getState(), countryCode);
    if (!model?.normalizedSeries || !analyticsControlsState) {
      return;
    }

    if (event.type === "click" && target.matches("[data-analytics-reset]")) {
      event.preventDefault();
      store.dispatch(analyticsControlsReset({ countryCode }));
      return;
    }

    if (event.type !== "change") {
      return;
    }

    if (target.matches("[data-analytics-global-control]")) {
      const controlName = target.getAttribute("data-analytics-global-control") || "";
      store.dispatch(
        analyticsGlobalControlsUpdated({
          countryCode,
          updates: {
            [controlName]: readControlValue(target),
          },
        }),
      );
      return;
    }

    if (target.matches("[data-analytics-override-toggle]")) {
      const indicatorId = target.getAttribute("data-indicator-id") || "";
      store.dispatch(
        analyticsIndicatorOverrideToggled({
          countryCode,
          indicatorId,
          enabled: target instanceof HTMLInputElement ? target.checked : false,
        }),
      );
      return;
    }

    if (target.matches("[data-analytics-override-control]")) {
      const indicatorId = target.getAttribute("data-indicator-id") || "";
      const controlName = target.getAttribute("data-analytics-override-control") || "";
      store.dispatch(
        analyticsIndicatorOverrideControlsUpdated({
          countryCode,
          indicatorId,
          updates: {
            [controlName]: readControlValue(target),
          },
        }),
      );
    }
  }

  function buildRenderAppState() {
    const appState = selectAppRenderState(store.getState());
    const selectedCountryCode = selectSelectedCountryCode(store.getState());
    const selectedCountryModel = selectSelectedCountryModel(store.getState());
    const enrichedCountryModels = appState.countryModels.map((model) => {
      const analyticsState = getCountryAnalyticsSelector(model.countryCode)(store.getState(), model.countryCode);
      const uiState = getCountryUiSelector(model.countryCode)(store.getState(), model.countryCode);
      return analyticsState
        ? {
            ...model,
            analyticsState,
            uiState,
          }
        : {
            ...model,
            uiState,
          };
    });
    const enrichedSelectedCountryModel =
      selectedCountryModel && selectedCountryCode
        ? enrichedCountryModels.find((model) => model.countryCode === selectedCountryCode) || null
        : null;

    return {
      ...appState,
      globeMarkup:
        globeWorldGeometry && globeRenderer
          ? globeRenderer.renderGlobe({
              selectedCountryCode,
              worldGeometry: globeWorldGeometry,
            })
          : "",
      selectedCountryCode,
      selectedCountryModel: enrichedSelectedCountryModel,
      countryModels: enrichedCountryModels,
    };
  }

  function dispatchPageView(trigger) {
    store.dispatch(
      analyticsPageViewed({
        trigger,
      }),
    );
  }

  function getCountryAnalyticsSelector(countryCode) {
    if (!countryAnalyticsSelectorByCode.has(countryCode)) {
      countryAnalyticsSelectorByCode.set(countryCode, createSelectCountryAnalyticsState());
    }

    return countryAnalyticsSelectorByCode.get(countryCode);
  }

  function getCountryUiSelector(countryCode) {
    if (!countryUiSelectorByCode.has(countryCode)) {
      countryUiSelectorByCode.set(countryCode, createSelectCountryUiState());
    }

    return countryUiSelectorByCode.get(countryCode);
  }

  function createRenderContext(appState) {
    return {
      consentState: appState.consentState || null,
      countryCodes: appState.countryModels.map((model) => model.countryCode),
      selectedCountryCode: appState.selectedCountryCode || null,
      snapshotsByCode: Object.fromEntries(
        appState.countryModels.map((model) => [
          model.countryCode,
          {
            forecast: model.forecast || null,
            forecastLoadError: model.forecastLoadError,
            loadError: model.loadError,
            normalizedSeries: model.normalizedSeries || null,
            analyticsState: model.analyticsState || null,
            uiState: model.uiState || null,
          },
        ]),
      ),
    };
  }

  function shouldRenderFullPage(appState, previousContext) {
    if (!previousContext) {
      return true;
    }

    if (
      previousContext.consentState?.decision !== (appState.consentState?.decision || null) ||
      previousContext.consentState?.hydrated !== Boolean(appState.consentState?.hydrated) ||
      previousContext.consentState?.updatedAt !== (appState.consentState?.updatedAt || null)
    ) {
      return true;
    }

    const countryCodes = appState.countryModels.map((model) => model.countryCode);
    if (countryCodes.length !== previousContext.countryCodes.length) {
      return true;
    }

    return countryCodes.some((countryCode, index) => countryCode !== previousContext.countryCodes[index]);
  }

  function collectChangedCountryCodes(appState, previousContext) {
    const selectedCountryCode = appState.selectedCountryCode || null;
    if (!selectedCountryCode) {
      return [];
    }

    return appState.countryModels
      .filter((model) => model.countryCode === selectedCountryCode)
      .filter((model) => {
        const previousSnapshot = previousContext?.snapshotsByCode?.[model.countryCode];
        if (!previousSnapshot) {
          return true;
        }

        return (
          previousSnapshot.forecast !== (model.forecast || null) ||
          previousSnapshot.forecastLoadError !== model.forecastLoadError ||
          previousSnapshot.loadError !== model.loadError ||
          previousSnapshot.normalizedSeries !== (model.normalizedSeries || null) ||
          previousSnapshot.analyticsState !== (model.analyticsState || null) ||
          previousSnapshot.uiState !== (model.uiState || null)
        );
      })
      .map((model) => model.countryCode);
  }

  function didSelectedCountryChange(appState, previousContext) {
    return (appState.selectedCountryCode || null) !== (previousContext?.selectedCountryCode || null);
  }

  function rerenderSelectionSurfaces(appState) {
    const globeNavigationBlock = appRoot.querySelector("[data-globe-navigation-block='true']");
    const countryPanelRegion = appRoot.querySelector("[data-country-panel-region='true']");
    if (!(globeNavigationBlock instanceof Element) || !(countryPanelRegion instanceof Element)) {
      return false;
    }

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

    globeNavigationBlock.outerHTML = globeNavigationMarkup;
    countryPanelRegion.outerHTML = countryPanelMarkup;
    return true;
  }

  function rerenderCountrySections(appState, changedCountryCodes) {
    for (const countryCode of changedCountryCodes) {
      const countrySection = Array.from(appRoot.querySelectorAll("section[data-country-code]")).find(
        (section) => section.getAttribute("data-country-code") === countryCode,
      );
      const model = appState.countryModels.find((entry) => entry.countryCode === countryCode);

      if (!countrySection || !model) {
        return false;
      }

      countrySection.outerHTML = renderCountrySectionMarkup(model, { chartRenderer });
    }

    return true;
  }

  function readControlValue(target) {
    if (target instanceof HTMLInputElement && target.type === "range") {
      return Number(target.value);
    }
    return target.getAttribute("value") !== null || "value" in target ? target.value : "";
  }

  function syncConsentModalState() {
    const consentDialog = getConsentDialog();
    const hasOpenConsentModal = consentDialog instanceof HTMLElement;

    for (const child of Array.from(appRoot.children)) {
      if (hasOpenConsentModal && !child.hasAttribute("data-consent-banner")) {
        child.setAttribute("inert", "");
        child.setAttribute("aria-hidden", "true");
        continue;
      }

      child.removeAttribute("inert");
      child.removeAttribute("aria-hidden");
    }

    if (!hasOpenConsentModal) {
      unlockBodyScroll();
      return;
    }

    lockBodyScroll();
    if (!consentDialog.contains(documentRef?.activeElement)) {
      consentDialog.focus();
    }
  }

  function handleConsentModalKeydown(event) {
    const consentDialog = getConsentDialog();
    if (!(consentDialog instanceof HTMLElement)) {
      return false;
    }

    if (event.key === "Escape") {
      event.preventDefault();
      return true;
    }

    if (event.key !== "Tab") {
      return false;
    }

    const focusableElements = listFocusableElements(consentDialog);
    if (!focusableElements.length) {
      event.preventDefault();
      consentDialog.focus();
      return true;
    }

    const firstElement = focusableElements[0];
    const lastElement = focusableElements.at(-1);
    const activeElement = documentRef?.activeElement;

    if (!consentDialog.contains(activeElement)) {
      event.preventDefault();
      firstElement.focus();
      return true;
    }

    if (activeElement === consentDialog) {
      event.preventDefault();
      (event.shiftKey ? lastElement : firstElement).focus();
      return true;
    }

    if (event.shiftKey && activeElement === firstElement) {
      event.preventDefault();
      lastElement.focus();
      return true;
    }

    if (!event.shiftKey && activeElement === lastElement) {
      event.preventDefault();
      firstElement.focus();
      return true;
    }

    return false;
  }

  function getConsentDialog() {
    const consentDialog = appRoot.querySelector("[data-consent-dialog='true']");
    return consentDialog instanceof HTMLElement ? consentDialog : null;
  }

  function lockBodyScroll() {
    const body = documentRef?.body;
    const documentElement = documentRef?.documentElement;
    if (!body || !documentElement) {
      return;
    }

    if (!scrollLockSnapshot) {
      scrollLockSnapshot = {
        bodyOverflow: body.style.overflow,
        documentOverflow: documentElement.style.overflow,
      };
    }

    body.style.overflow = "hidden";
    documentElement.style.overflow = "hidden";
  }

  function unlockBodyScroll() {
    const body = documentRef?.body;
    const documentElement = documentRef?.documentElement;
    if (!body || !documentElement || !scrollLockSnapshot) {
      return;
    }

    body.style.overflow = scrollLockSnapshot.bodyOverflow;
    documentElement.style.overflow = scrollLockSnapshot.documentOverflow;
    scrollLockSnapshot = null;
  }
}

function listFocusableElements(container) {
  if (!(container instanceof Element)) {
    return [];
  }

  return Array.from(
    container.querySelectorAll(
      'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
    ),
  ).filter((element) => {
    const tabIndex = Number(element.getAttribute("tabindex"));
    return Number.isNaN(tabIndex) || tabIndex >= 0;
  });
}

function readGlobeSelectionCountryCode(event) {
  const target = event.target;
  if (!(target instanceof Element)) {
    return "";
  }

  const selectableCountry = target.closest("[data-globe-country-select='true']");
  if (!(selectableCountry instanceof Element)) {
    return "";
  }

  if (event.type === "click") {
    return selectableCountry.getAttribute("data-country-code") || "";
  }

  if (event.type !== "keydown" || !isGlobeKeyboardActivation(event)) {
    return "";
  }

  return selectableCountry.getAttribute("data-country-code") || "";
}

function readCountrySelectionControlCode(event) {
  const target = event.target;
  if (!(target instanceof Element) || event.type !== "click") {
    return "";
  }

  const control = target.closest("[data-country-select-control='true']");
  if (!(control instanceof Element)) {
    return "";
  }

  return control.getAttribute("data-country-code") || "";
}

function isGlobeKeyboardActivation(event) {
  const key = typeof event?.key === "string" ? event.key : "";
  return key === "Enter" || key === " " || key === "Spacebar";
}

function readConsentSurface(element) {
  if (!(element instanceof Element)) {
    return "unknown";
  }

  if (element.closest("[data-manage-cookies-panel='true']")) {
    return "manage_cookies_page";
  }

  if (element.closest("[data-consent-banner='true']")) {
    return "banner";
  }

  return "unknown";
}

function readLegalLinkPlacement(element) {
  if (!(element instanceof Element)) {
    return "unknown";
  }

  if (element.closest("[data-consent-banner='true']")) {
    return "consent_banner";
  }

  if (element.closest(".site-footer")) {
    return "site_footer";
  }

  if (element.closest("[data-legal-page]")) {
    return "legal_page";
  }

  return "unknown";
}

export const __test__ = {
  analyticsConfig: ANALYTICS_RUNTIME_CONFIG,
  isGlobeKeyboardActivation,
  readConsentSurface,
  readCountrySelectionControlCode,
  readGlobeSelectionCountryCode,
  readLegalLinkPlacement,
};
