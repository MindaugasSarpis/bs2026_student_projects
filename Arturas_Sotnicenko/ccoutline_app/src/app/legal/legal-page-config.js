const LEGAL_PAGE_DEFINITIONS = Object.freeze([
  {
    key: "privacy",
    pathname: "/privacy/",
    kicker: "CCOUTLINE legal",
    title: "Privacy Notice",
    lead:
      "This notice explains how CCOUTLINE handles analytics-related data on ccoutline.com. It is intentionally narrow and focuses on browser-side measurement for this static public site.",
    sections: [
      {
        heading: "Consent-first analytics",
        paragraphs: [
          "CCOUTLINE keeps analytics off by default. Analytics only becomes eligible to load after you explicitly accept analytics cookies for this browser.",
          "If you do not opt in, the site should remain usable without GA4 tracking assets or analytics events.",
        ],
      },
      {
        heading: "What may be collected after opt-in",
        paragraphs: [
          "If analytics is enabled, CCOUTLINE may send page-view and interaction events to Google Analytics 4 so the site operator can understand which countries, disclosures, charts, and controls visitors use most.",
          "This tranche does not add login accounts, remarketing audiences, or advertising-personalization features to the site.",
        ],
      },
      {
        heading: "Controller and contact placeholder",
        paragraphs: [
          "Final legal-owner and contact details are still pending. CCOUTLINE will publish the controlling-entity and contact route here before broader analytics rollout moves beyond this working implementation state.",
        ],
      },
    ],
  },
  {
    key: "cookies",
    pathname: "/cookies/",
    kicker: "CCOUTLINE legal",
    title: "Cookie Notice",
    lead:
      "This notice covers the browser storage and cookie behavior used for analytics consent on ccoutline.com.",
    sections: [
      {
        heading: "Storage used before analytics is enabled",
        paragraphs: [
          "CCOUTLINE stores your consent decision and the time it was updated in this browser so the site can remember whether analytics should stay off or may load later.",
          "Those values are stored with versioned local-storage keys rather than as advertising or cross-site profiling cookies.",
        ],
      },
      {
        heading: "Storage used after opt-in",
        paragraphs: [
          "If you accept analytics, Google Analytics 4 may place analytics cookies or related browser identifiers needed to measure site usage.",
          "CCOUTLINE does not request those analytics identifiers before consent is granted.",
        ],
      },
      {
        heading: "Changing your choice",
        paragraphs: [
          "You can revisit the Manage cookies page at any time to accept analytics, decline analytics, or confirm the current browser-level choice.",
        ],
      },
    ],
  },
  {
    key: "manage-cookies",
    pathname: "/manage-cookies/",
    kicker: "CCOUTLINE legal",
    title: "Manage Cookies",
    lead:
      "Use this page to review or change the analytics choice stored for this browser on ccoutline.com.",
    sections: [
      {
        heading: "How this control works",
        paragraphs: [
          "The buttons below update the browser-local consent decision that CCOUTLINE reads before any later analytics loader is allowed to run.",
          "Changing the stored choice here affects only this browser profile and device.",
        ],
      },
      {
        heading: "What acceptance means",
        paragraphs: [
          "Accepting analytics allows a later GA4 integration step to measure page views and interaction events described in the privacy and cookie notices.",
          "Declining analytics keeps that measurement path disabled for this browser until you change the choice again.",
        ],
      },
    ],
  },
]);

export function listLegalPages() {
  return LEGAL_PAGE_DEFINITIONS;
}

export function resolveLegalPage(pathname) {
  const normalizedPathname = normalizeAppPathname(pathname);
  return LEGAL_PAGE_DEFINITIONS.find((page) => page.pathname === normalizedPathname) || null;
}

export function normalizeAppPathname(pathname) {
  const trimmedPathname = typeof pathname === "string" && pathname.trim().length > 0 ? pathname.trim() : "/";
  const pathnameWithoutQuery = trimmedPathname.split("?")[0].split("#")[0] || "/";
  const pathnameWithLeadingSlash = pathnameWithoutQuery.startsWith("/") ? pathnameWithoutQuery : `/${pathnameWithoutQuery}`;

  if (pathnameWithLeadingSlash === "/") {
    return "/";
  }

  return pathnameWithLeadingSlash.endsWith("/") ? pathnameWithLeadingSlash : `${pathnameWithLeadingSlash}/`;
}

