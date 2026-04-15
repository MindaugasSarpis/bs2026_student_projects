import { exposeBuildInfo, getBuildInfo } from "./app/config/build-info.js";
import { getAnalyticsRuntimeConfig } from "./app/config/analytics-config.js";
import { startStaticSiteApp } from "./app/static-site-app.js";
import { createAppStore } from "./app/state/store.js";

const appRoot = document.querySelector("#app");

if (!appRoot) {
  throw new Error("Unable to find #app root for ccoutline.");
}

exposeBuildInfo({
  buildInfo: getBuildInfo(),
});

startStaticSiteApp({
  appRoot,
  analyticsConfig: getAnalyticsRuntimeConfig(),
  store: createAppStore(),
});
