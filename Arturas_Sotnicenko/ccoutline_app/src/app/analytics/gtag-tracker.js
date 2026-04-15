function normalizeDecision(value) {
  return value === "accepted" || value === "declined" ? value : null;
}

function normalizeMeasurementId(value) {
  const trimmedValue = typeof value === "string" ? value.trim() : "";
  return /^G-[A-Z0-9]+$/i.test(trimmedValue) ? trimmedValue : "";
}

function toSerializableEventParams(params) {
  return Object.fromEntries(
    Object.entries(params || {}).filter(([, value]) => {
      return (
        typeof value === "string" ||
        typeof value === "number" ||
        typeof value === "boolean"
      );
    }),
  );
}

export function createGtagTracker({
  analyticsConfig,
  windowRef = globalThis.window,
  documentRef = globalThis.document,
} = {}) {
  const measurementId = normalizeMeasurementId(analyticsConfig?.ga4?.measurementId);
  let consentDecision = null;
  let scriptInjected = false;
  let configSent = false;
  let consentDefaultSent = false;
  let lastQueuedConsentDecision = null;

  return {
    enable,
    syncConsentDecision,
    trackEvent,
  };

  function enable() {
    if (consentDecision !== "accepted") {
      return false;
    }

    if (!ensureConfigured()) {
      return false;
    }

    queueConsentUpdate("accepted");
    return true;
  }

  function syncConsentDecision(nextDecision) {
    consentDecision = normalizeDecision(nextDecision);
    if (!consentDecision) {
      return false;
    }

    if (!windowRef) {
      return false;
    }

    ensureGtagStub();
    ensureConsentDefault();
    queueConsentUpdate(consentDecision);
    return true;
  }

  function trackEvent(name, params = {}) {
    if (consentDecision !== "accepted" || !ensureConfigured()) {
      return false;
    }

    windowRef.gtag("event", name, toSerializableEventParams(params));
    return true;
  }

  function ensureConfigured() {
    if (!measurementId || !windowRef || !documentRef) {
      return false;
    }

    ensureGtagStub();
    ensureConsentDefault();
    ensureScriptTag();

    if (!configSent) {
      windowRef.gtag("js", new Date());
      windowRef.gtag("config", measurementId, { send_page_view: false });
      configSent = true;
    }

    return true;
  }

  function ensureGtagStub() {
    if (!Array.isArray(windowRef.dataLayer)) {
      windowRef.dataLayer = [];
    }

    if (typeof windowRef.gtag !== "function") {
      windowRef.gtag = function gtag() {
        windowRef.dataLayer.push(arguments);
      };
    }
  }

  function ensureConsentDefault() {
    if (consentDefaultSent) {
      return false;
    }

    windowRef.gtag("consent", "default", {
      analytics_storage: "denied",
    });
    consentDefaultSent = true;
    return true;
  }

  function ensureScriptTag() {
    if (scriptInjected) {
      return;
    }

    const scriptSrc = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(measurementId)}`;
    const existingScript = documentRef.querySelector(`script[src="${scriptSrc}"]`);
    if (existingScript) {
      scriptInjected = true;
      return;
    }

    const script = documentRef.createElement("script");
    script.async = true;
    script.src = scriptSrc;
    documentRef.head.append(script);
    scriptInjected = true;
  }

  function queueConsentUpdate(decision) {
    if (lastQueuedConsentDecision === decision) {
      return false;
    }

    windowRef.gtag("consent", "update", {
      analytics_storage: decision === "accepted" ? "granted" : "denied",
    });
    lastQueuedConsentDecision = decision;
    return true;
  }
}
