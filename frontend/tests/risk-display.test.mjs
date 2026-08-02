import test from "node:test";
import assert from "node:assert/strict";
import {
  RISK_DISPLAY,
  riskDisplay,
  formatRiskScoreBadge,
  assessmentStatusDisplay,
  documentStatusDisplay,
  maskAccountNumber,
} from "../src/lib/risk-display.js";

test("five risk levels return correct label and score", () => {
  assert.equal(riskDisplay("low").label, "Low Risk");
  assert.equal(riskDisplay("low").score, 0);
  assert.equal(riskDisplay("lower").label, "Lower Risk");
  assert.equal(riskDisplay("lower").score, 25);
  assert.equal(riskDisplay("medium").label, "Medium Risk");
  assert.equal(riskDisplay("medium").score, 50);
  assert.equal(riskDisplay("higher").label, "Higher Risk");
  assert.equal(riskDisplay("higher").score, 75);
  assert.equal(riskDisplay("high").label, "High Risk");
  assert.equal(riskDisplay("high").score, 100);

  assert.equal(RISK_DISPLAY.low.score, 0);
  assert.equal(RISK_DISPLAY.high.score, 100);
});

test("null and unknown risk levels return Not assessed neutral display", () => {
  assert.equal(riskDisplay(null).label, "Not assessed");
  assert.equal(riskDisplay(undefined).label, "Not assessed");
  assert.equal(riskDisplay("").label, "Not assessed");
  assert.equal(riskDisplay("High").label, "Not assessed");
  assert.equal(riskDisplay("unknown").label, "Not assessed");
  assert.match(riskDisplay(null).className, /slate/);
});

test("score 0 is treated as a valid value via ?? not ||", () => {
  const badge = formatRiskScoreBadge({
    assessment_status: "completed",
    overall_risk_score: 0,
    risk_level: "low",
  });
  assert.equal(badge.scoreText, "0");
  assert.equal(badge.label, "Low Risk");
  assert.match(badge.className, /emerald/);

  const rawScore = 0;
  assert.equal(rawScore ?? "N/A", 0);
  assert.notEqual(rawScore || "N/A", 0);
});

test("unassessed and failed assessment statuses are not green", () => {
  const notAssessed = formatRiskScoreBadge({
    assessment_status: "not_started",
    overall_risk_score: null,
    risk_level: null,
  });
  assert.equal(notAssessed.label, "Not assessed");
  assert.match(notAssessed.className, /slate/);

  const failed = formatRiskScoreBadge({
    assessment_status: "failed",
    overall_risk_score: null,
    risk_level: null,
  });
  assert.equal(failed.label, "Assessment failed");
  assert.match(failed.className, /red/);
});

test("account masking keeps only last 4 digits", () => {
  assert.equal(maskAccountNumber("12345678"), "•••• 5678");
  assert.equal(maskAccountNumber("12-345-6789"), "•••• 6789");
  assert.equal(maskAccountNumber("00001234"), "•••• 1234");
  assert.equal(maskAccountNumber(null), null);
  assert.equal(maskAccountNumber(""), "");
});

test("document status pass/fail/N/A/incomplete copy is correct", () => {
  assert.equal(documentStatusDisplay("pass").label, "Pass");
  assert.equal(documentStatusDisplay("fail").label, "Fail");
  assert.equal(documentStatusDisplay("not_applicable").label, "N/A");
  assert.equal(documentStatusDisplay("N/A").label, "N/A");
  assert.equal(documentStatusDisplay("incomplete").label, "Incomplete");
});

test("assessment status display labels", () => {
  assert.equal(assessmentStatusDisplay("not_started").label, "Not started");
  assert.equal(assessmentStatusDisplay("processing").label, "Assessing…");
  assert.equal(assessmentStatusDisplay("completed").label, "Completed");
  assert.equal(assessmentStatusDisplay("failed").label, "Assessment failed");
});
