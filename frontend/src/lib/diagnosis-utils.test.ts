import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import {
  diagnosisConfidenceLabel,
  diagnosisFocusLabel,
  evidenceStrengthLabel,
  feedbackEventTypeLabel,
  feedbackStatusLabel,
} from "./diagnosis-utils.ts";

test("diagnosis helpers produce judgment-specific labels", () => {
  assert.equal(diagnosisFocusLabel("AI_AUTOMATION"), "AI / Automation");
  assert.equal(diagnosisConfidenceLabel(0.82), "High confidence");
  assert.equal(diagnosisConfidenceLabel(0.6), "Moderate confidence");
  assert.equal(evidenceStrengthLabel("STRONG"), "Strong evidence");
  assert.equal(feedbackEventTypeLabel("POSITIONING_RULE"), "Positioning rule");
  assert.equal(feedbackStatusLabel("PROPOSED"), "Proposed");
});

test("diagnosis route renders the workspace", () => {
  const page = readFileSync(
    new URL("../app/diagnosis/page.tsx", import.meta.url),
    "utf8",
  );
  assert.match(page, /DiagnosisWorkspace/);
  assert.match(page, /Career Diagnosis/);
});

test("diagnosis workspace exposes inputs and complete diagnosis panels", () => {
  const source = readFileSync(
    new URL(
      "../components/diagnosis/diagnosis-workspace.tsx",
      import.meta.url,
    ),
    "utf8",
  );

  assert.match(source, /Target role or program/);
  assert.match(source, /Optional context or frustration/);
  assert.match(source, /Run diagnosis/);
  assert.match(source, /Strongest career identity/);
  assert.match(source, /Evidence Map/);
  assert.match(source, /Recognition Gap/);
  assert.match(source, /Missing proof/);
  assert.match(source, /7-day Proof Sprint/);
  assert.match(source, /What CareerOS thinks you should stop doing/);
  assert.match(source, /Exact next messages/);
  assert.match(source, /Approved memory needed/);
  assert.match(source, /Approve career memories before running a full diagnosis/);
});

test("Teach CareerOS input and feedback event review controls render", () => {
  const source = readFileSync(
    new URL(
      "../components/diagnosis/diagnosis-workspace.tsx",
      import.meta.url,
    ),
    "utf8",
  );

  assert.match(source, /Teach CareerOS note/);
  assert.match(source, /Save and teach/);
  assert.match(source, /Recent feedback events/);
  assert.match(source, /Approve guidance/);
  assert.match(source, /Archive/);
});

test("navigation and dashboard link to Career Diagnosis", () => {
  const navigation = readFileSync(
    new URL("../components/common/workspace-nav.tsx", import.meta.url),
    "utf8",
  );
  const dashboard = readFileSync(
    new URL("../components/dashboard/dashboard-shell.tsx", import.meta.url),
    "utf8",
  );

  assert.match(navigation, /href: "\/diagnosis", label: "Diagnosis"/);
  assert.match(dashboard, /Run Career Diagnosis/);
  assert.match(dashboard, /href: "\/diagnosis"/);
});
