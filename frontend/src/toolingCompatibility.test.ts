import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const packageManifest = JSON.parse(
  readFileSync(resolve(process.cwd(), "package.json"), "utf8"),
) as { engines: { node: string } };
const jsdomManifest = JSON.parse(
  readFileSync(resolve(process.cwd(), "node_modules/jsdom/package.json"), "utf8"),
) as { engines: { node: string } };
const frontendReadme = readFileSync(resolve(process.cwd(), "README.md"), "utf8");

describe("documented frontend toolchain compatibility", () => {
  it("sets the manifest engine range to the one supported by locked jsdom", () => {
    expect(packageManifest.engines.node).toBe(jsdomManifest.engines.node);
  });

  it("documents the Node versions supported by the locked jsdom toolchain", () => {
    expect(frontendReadme).toContain(`Node.js versions: \`${jsdomManifest.engines.node}\``);
  });
});
