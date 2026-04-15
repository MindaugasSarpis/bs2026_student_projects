import test from "node:test";
import assert from "node:assert/strict";

import { exposeBuildInfo, getBuildInfo } from "../src/app/config/build-info.js";

test("build info exposes a stable browser-global and logs the startup fingerprint", () => {
  const windowRef = {};
  const infoCalls = [];
  const consoleRef = {
    info(message) {
      infoCalls.push(message);
    },
  };

  const buildInfo = {
    version: "0123456789abcdef0123456789abcdef01234567",
    versionShort: "0123456",
    versionSource: "git_sha",
  };

  const exposedBuildInfo = exposeBuildInfo({
    buildInfo,
    windowRef,
    consoleRef,
  });

  assert.deepEqual(exposedBuildInfo, buildInfo);
  assert.deepEqual(windowRef.__CCOUTLINE_BUILD__, buildInfo);
  assert.deepEqual(infoCalls, ["CCOUTLINE build 0123456"]);
});

test("build info falls back to the committed unknown fingerprint in source trees", () => {
  assert.deepEqual(getBuildInfo(), {
    version: "unknown",
    versionShort: "unknown",
    versionSource: "unknown",
  });
});
