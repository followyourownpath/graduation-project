import test from "node:test";
import assert from "node:assert/strict";
import { isPublicPath, safeRedirectPath, withBasePath } from "../src/lib/auth-utils.js";

test("safeRedirectPath accepts only local absolute paths", () => {
  assert.equal(safeRedirectPath("/dashboard"), "/dashboard");
  assert.equal(safeRedirectPath("//evil.example"), "/update-password");
  assert.equal(safeRedirectPath("https://evil.example"), "/update-password");
});

test("public routes exclude dashboard routes", () => {
  assert.equal(isPublicPath("/login"), true);
  assert.equal(isPublicPath("/auth/confirm"), true);
  assert.equal(isPublicPath("/dashboard"), false);
});

test("withBasePath leaves local paths unchanged when no base path is configured", () => {
  assert.equal(withBasePath("/auth/confirm"), "/auth/confirm");
  assert.equal(withBasePath("dashboard"), "/dashboard");
});
