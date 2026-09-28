import { describe, expect, it } from "vitest";
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";

function appSourceFiles(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) return appSourceFiles(path);
    return /\.(ts|tsx)$/.test(entry.name) ? [path] : [];
  });
}

describe("browser/server module boundary", () => {
  it("keeps tenant resolution and direct API clients out of client components", () => {
    const files = appSourceFiles(join(process.cwd(), "src", "app"));
    const violations = files.flatMap((file) => {
      const source = readFileSync(file, "utf8");
      if (!/^\s*[\"']use client[\"'];/m.test(source)) return [];
      const matches = source.match(/from ["']@\/lib\/(?:tenant-context|mvp-api-client)["']/g) ?? [];
      const directReferenceImports = source.match(/import\s*\{[^}]*\b(?:submit[A-Z]|decide[A-Z]|get[A-Z])[^}]*\}\s*from\s*["']@\/lib\/reference-api-client["']/g) ?? [];
      return [...matches, ...directReferenceImports].map((match) => `${file}: ${match}`);
    });
    expect(violations).toEqual([]);
  });
});
