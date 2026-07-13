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
  assert.equal(feedbackStatusLabel("APPROVED"), "Approved");
  assert.equal(feedbackStatusLabel("ARCHIVED"), "Archived");
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
  assert.match(source, /const \[feedbackNote, setFeedbackNote\] = useState\(""\)/);
  assert.match(
    source,
    /placeholder="Example: This cover letter led to an interview invite\."/,
  );
  assert.doesNotMatch(source, /Black Box AI Engineer Intern/);
  assert.match(source, /Save and teach/);
  assert.match(source, /Recent feedback events/);
  assert.match(source, /Edit event/);
  assert.match(source, /Save changes/);
  assert.match(source, /This looks similar to an existing feedback event\./);
  assert.match(
    source,
    /Edit the existing event instead of adding a duplicate\./,
  );
  assert.match(source, /role="alert"/);
  assert.match(source, /Similar existing event/);
  assert.match(source, /Approve guidance/);
  assert.match(source, /Approved guidance can influence future diagnosis/);
  assert.match(source, /Archived events are excluded from future diagnosis/);
  assert.match(source, /Archive/);
  assert.match(source, /Outcome signals · not canonical proof/);

  const teachHandler = source.slice(
    source.indexOf("async function teachCareerOS()"),
    source.indexOf("async function changeFeedbackStatus"),
  );
  assert.match(teachHandler, /if \(isDuplicateFeedbackError\(error\)\)/);
  assert.match(teachHandler, /setDuplicateFeedback\(null\)/);
  assert.equal(teachHandler.match(/setFeedbackNote\(""\)/g)?.length, 1);
  const duplicateCatch = teachHandler.slice(teachHandler.indexOf("} catch"));
  assert.doesNotMatch(duplicateCatch, /setFeedbackNote\(""\)/);

  assert.match(
    source,
    /function changeFeedbackNote\(value: string\)[\s\S]*setDuplicateFeedback\(null\)/,
  );
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
  assert.match(navigation, /href: "\/proof-artifacts", label: "Proof"/);
  assert.match(dashboard, /Run Career Diagnosis/);
  assert.match(dashboard, /href: "\/diagnosis"/);
  assert.match(dashboard, /Build a proof artifact/);
  assert.match(dashboard, /href: "\/proof-artifacts"/);
});
