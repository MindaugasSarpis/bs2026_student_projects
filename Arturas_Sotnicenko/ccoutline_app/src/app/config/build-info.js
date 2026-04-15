const BUILD_INFO = Object.freeze({
  version: "unknown",
  versionShort: "unknown",
  versionSource: "unknown",
});

export function getBuildInfo() {
  return BUILD_INFO;
}

export function exposeBuildInfo({
  buildInfo = BUILD_INFO,
  windowRef = globalThis.window,
  consoleRef = globalThis.console,
} = {}) {
  if (windowRef && typeof windowRef === "object") {
    windowRef.__CCOUTLINE_BUILD__ = buildInfo;
  }

  if (consoleRef && typeof consoleRef.info === "function") {
    consoleRef.info(`CCOUTLINE build ${buildInfo.versionShort}`);
  }

  return buildInfo;
}
