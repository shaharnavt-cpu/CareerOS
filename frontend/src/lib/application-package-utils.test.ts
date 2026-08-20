import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import {
  applicationEvidenceSourceLabel,
  applicationEvidenceSupportLabel,
  applicationGenerationReasonLabel,
  applicationPackageCopyText,
  applicationPackageInputFingerprint,
  applicationPackageStatusLabel,
  applicationPackageVersionInput,
  applicationOpportunityRoleTitle,
  applicationWarningSeverityLabel,
  applicationProviderLabel,
  defaultRecommendedMemoryIds,
  moveSelectedMemory,
  normalizeApplicationPackageInput,
  packageMatchesInput,
  resumeApplicationClaimId,
  resumeBulletGroupText,
  snippetApplicationClaimId,
  splitPackageList,
  type ApplicationPackageInput,
} from "./application-package-utils.ts";

const baseInput: ApplicationPackageInput = {
  opportunityId: "opportunity-1",
  roleTitle: "Data Science Intern",
  company: "Test Company",
  location: "Chicago, IL",
  jobType: "Internship",
  targetDescription: "Analyze data, modeling, and uncertainty.",
  requiredSkills: ["Python", "modeling"],
  preferredSkills: ["communication"],
  responsibilities: ["Analyze messy data"],
  applicationQuestions: [
    {
      question_id: "motivation",
      question_text: "Why are you interested in this role?",
      required: true,
      maximum_length: 500,
      response_type: "paragraph",
      relevant_target_requirement_ids: ["requirement-python"],
    },
  ],
  selectedMemoryIds: ["gas-memory", "unicorn-memory"],
};

test("package list parsing and normalization mirror the backend target contract", () => {
  assert.deepEqual(
    splitPackageList(" Python, modeling\nPython; uncertainty reasoning "),
    ["Python", "modeling", "uncertainty reasoning"],
  );
  assert.deepEqual(
    normalizeApplicationPackageInput({
      ...baseInput,
      company: "  Test Company  ",
      requiredSkills: [" Python ", "data   analysis", "python"],
    }),
    {
      opportunity_id: "opportunity-1",
      role_title: "Data Science Intern",
      company: "Test Company",
      location: "Chicago, IL",
      job_type: "Internship",
      target_description: "Analyze data, modeling, and uncertainty.",
      required_skills: ["Python", "data analysis"],
      preferred_skills: ["communication"],
      responsibilities: ["Analyze messy data"],
      application_questions: [
        {
          question_id: "motivation",
          question_text: "Why are you interested in this role?",
          required: true,
          maximum_length: 500,
          response_type: "paragraph",
          relevant_target_requirement_ids: ["requirement-python"],
        },
      ],
      selected_memory_ids: ["gas-memory", "unicorn-memory"],
    },
  );
});

test("saved opportunity titles remain the exact package role instead of the broad classifier", () => {
  assert.equal(
    applicationOpportunityRoleTitle({
      title: "  Data   Analytics Intern  ",
      detected_role_type: "Data",
    }),
    "Data Analytics Intern",
  );
  assert.equal(
    normalizeApplicationPackageInput({
      ...baseInput,
      roleTitle: "  Data   Analytics Intern  ",
    }).role_title,
    "Data Analytics Intern",
  );
});

test("material target and exact ordered-memory changes invalidate the fingerprint", () => {
  const base = applicationPackageInputFingerprint(baseInput);
  const changes: ApplicationPackageInput[] = [
    { ...baseInput, opportunityId: "opportunity-2" },
    { ...baseInput, roleTitle: "AI Engineer Intern" },
    { ...baseInput, company: "Another Company" },
    { ...baseInput, location: "Remote" },
    { ...baseInput, jobType: "Full-time" },
    { ...baseInput, targetDescription: "Build AI workflows." },
    { ...baseInput, requiredSkills: ["Python", "SQL"] },
    { ...baseInput, preferredSkills: ["automation"] },
    { ...baseInput, responsibilities: ["Review image labels"] },
    {
      ...baseInput,
      applicationQuestions: [
        {
          ...baseInput.applicationQuestions[0],
          question_text: "Describe a complex data project.",
        },
      ],
    },
    {
      ...baseInput,
      applicationQuestions: [
        ...baseInput.applicationQuestions,
        {
          question_id: "quality",
          question_text: "How did you ensure quality?",
          required: false,
          maximum_length: null,
          response_type: null,
          relevant_target_requirement_ids: [],
        },
      ],
    },
    { ...baseInput, applicationQuestions: [] },
    { ...baseInput, selectedMemoryIds: ["gas-memory"] },
    {
      ...baseInput,
      selectedMemoryIds: ["unicorn-memory", "gas-memory"],
    },
  ];
  for (const changed of changes) {
    assert.notEqual(applicationPackageInputFingerprint(changed), base);
  }
});

test("fingerprints ignore harmless outer whitespace but not selection order", () => {
  assert.equal(
    applicationPackageInputFingerprint({
      ...baseInput,
      roleTitle: "  Data Science Intern ",
      company: " Test Company ",
      targetDescription: " Analyze data, modeling, and uncertainty.  ",
      requiredSkills: [" Python ", "modeling"],
      applicationQuestions: [
        {
          ...baseInput.applicationQuestions[0],
          question_id: " motivation ",
          question_text: " Why are you interested in this role? ",
          response_type: " paragraph ",
          relevant_target_requirement_ids: [" requirement-python "],
        },
      ],
    }),
    applicationPackageInputFingerprint(baseInput),
  );
});

test("saved output matches only its exact current target and memory order", () => {
  const applicationPackage = {
    is_stale: false,
    latest_version: {
      target_snapshot: {
        opportunity_id: "opportunity-1",
        role_title: "Data Science Intern",
        company: "Test Company",
        location: "Chicago, IL",
        job_type: "Internship",
        target_description: "Analyze data, modeling, and uncertainty.",
        required_skills: ["Python", "modeling"],
        preferred_skills: ["communication"],
        responsibilities: ["Analyze messy data"],
        application_questions: baseInput.applicationQuestions,
      },
      selected_memory_ids: ["gas-memory", "unicorn-memory"],
    },
  };

  assert.equal(packageMatchesInput(applicationPackage, baseInput), true);
  assert.equal(
    packageMatchesInput(applicationPackage, {
      ...baseInput,
      roleTitle: "AI Engineer Intern",
    }),
    false,
  );
  assert.equal(
    packageMatchesInput(applicationPackage, {
      ...baseInput,
      selectedMemoryIds: ["unicorn-memory", "gas-memory"],
    }),
    false,
  );
  assert.equal(
    packageMatchesInput({ ...applicationPackage, is_stale: true }, baseInput),
    false,
  );
});

test("version input restoration uses the immutable snapshot, not mutable parent fields", () => {
  const restored = applicationPackageVersionInput({
    target_snapshot: {
      opportunity_id: "historical-opportunity",
      role_title: "Historical Role",
      company: "Historical Company",
      location: "Remote",
      job_type: "Internship",
      target_description: "Historical target text",
      required_skills: ["Python"],
      preferred_skills: ["SQL"],
      responsibilities: ["Analyze data"],
      application_questions: [
        {
          question_id: "historical-motivation",
          question_text: "Why this historical role?",
          required: true,
          maximum_length: null,
          response_type: "paragraph",
          relevant_target_requirement_ids: ["historical-requirement"],
        },
      ],
    },
    selected_memory_ids: ["historical-memory"],
  });

  assert.deepEqual(restored, {
    opportunityId: "historical-opportunity",
    roleTitle: "Historical Role",
    company: "Historical Company",
    location: "Remote",
    jobType: "Internship",
    targetDescription: "Historical target text",
    requiredSkills: ["Python"],
    preferredSkills: ["SQL"],
    responsibilities: ["Analyze data"],
    applicationQuestions: [
      {
        question_id: "historical-motivation",
        question_text: "Why this historical role?",
        required: true,
        maximum_length: null,
        response_type: "paragraph",
        relevant_target_requirement_ids: ["historical-requirement"],
      },
    ],
    selectedMemoryIds: ["historical-memory"],
  });
});

test("selected memory movement is ordered, bounded, and non-mutating", () => {
  const ids = ["gas", "unicorn", "coursework"];
  assert.deepEqual(moveSelectedMemory(ids, "unicorn", -1), [
    "unicorn",
    "gas",
    "coursework",
  ]);
  assert.deepEqual(moveSelectedMemory(ids, "unicorn", 1), [
    "gas",
    "coursework",
    "unicorn",
  ]);
  assert.deepEqual(moveSelectedMemory(ids, "gas", -1), ids);
  assert.deepEqual(ids, ["gas", "unicorn", "coursework"]);
});

test("fresh selections use only the first four ranked recommendations", () => {
  const memories = [
    { id: "four", title: "Fourth", recommended: true, recommendation_rank: 4 },
    { id: "none", title: "Not recommended", recommended: false },
    { id: "two", title: "Second", recommended: true, recommendation_rank: 2 },
    { id: "five", title: "Fifth", recommended: true, recommendation_rank: 5 },
    { id: "one", title: "First", recommended: true, recommendation_rank: 1 },
    { id: "three", title: "Third", recommended: true, recommendation_rank: 3 },
  ].map((memory) => ({
    memory_type: "PROJECT",
    evidence_count: 1,
    source_labels: [],
    confidence: 1,
    ...memory,
  }));

  assert.deepEqual(defaultRecommendedMemoryIds(memories), [
    "one",
    "two",
    "three",
    "four",
  ]);
  assert.deepEqual(defaultRecommendedMemoryIds(memories, 2), ["one", "two"]);
  assert.deepEqual(
    defaultRecommendedMemoryIds([
      {
        id: "only",
        title: "Only recommendation",
        memory_type: "PROJECT",
        evidence_count: 1,
        source_labels: [],
        confidence: 1,
        recommended: true,
        recommendation_rank: 1,
      },
    ]),
    [],
  );
});

test("provider labels stay useful for both local and optional model-backed drafts", () => {
  assert.equal(
    applicationProviderLabel({ provider: "local-deterministic" }),
    "Local deterministic",
  );
  assert.equal(
    applicationProviderLabel({
      provider: "openai",
      model: "gpt-5.6-terra",
      review_model: "gpt-5.6-sol",
      review_pass_ran: true,
    }),
    "GPT-5.6 Terra + GPT-5.6 Sol review",
  );
  assert.equal(applicationProviderLabel(undefined), "Generation details unavailable");
});

test("editable surface claim IDs match the backend one-based ledger contract", () => {
  assert.equal(resumeApplicationClaimId(0, 0), "resume-1-1");
  assert.equal(resumeApplicationClaimId(1, 2), "resume-2-3");
  assert.equal(snippetApplicationClaimId(0), "snippet-1");
  assert.equal(snippetApplicationClaimId(1), "snippet-2");
});

test("package labels distinguish proof, strategy, relevance, and status", () => {
  assert.equal(applicationPackageStatusLabel("READY"), "Ready");
  assert.equal(
    applicationEvidenceSourceLabel("STRATEGY_SIGNAL"),
    "Strategy signal · not proof",
  );
  assert.equal(
    applicationEvidenceSupportLabel("RELEVANCE_ONLY"),
    "Relevance only · not factual proof",
  );
  assert.equal(applicationWarningSeverityLabel("BLOCKING"), "Needs resolution");
  assert.equal(applicationGenerationReasonLabel("USER_EDIT"), "Saved edits");
});

test("package outputs become copy-ready text without raw IDs", () => {
  const outputs = {
    positioning_summary: {
      primary_positioning: "Lead with evidence-backed analysis.",
      strongest_evidence: "Gas Kinematics",
      secondary_evidence: [],
      risks_and_gaps: [],
      recommended_emphasis: [],
      do_not_claim: [],
    },
    resume_bullets: [
      {
        section_suggestion: "Projects",
        memory_id: "gas-memory",
        memory_title: "Gas Kinematics",
        target_reason: "Relevant analysis",
        bullets: [
          {
            bullet_text: "Analyzed approved spectroscopy data.",
            evidence_trace: [],
            confidence: 0.9,
            warnings: [],
            why_this_bullet: "Supported",
          },
        ],
      },
    ],
    cover_letter: {
      subject_or_heading: "Application",
      greeting: "Dear team,",
      opening_paragraph: "Opening",
      body_paragraphs: [],
      closing_paragraph: "Closing",
      full_text: "Dear team,\n\nEvidence-backed letter.",
      evidence_trace_by_paragraph: [],
      warnings: [],
      strategy_notes: [],
    },
    application_snippets: [
      {
        question_id: "motivation",
        question: "Why this role?",
        text: "It matches my approved analysis experience.",
        evidence_trace: [],
        warnings: [],
      },
    ],
    suggested_proof_artifacts: [],
    reviewer_questions: [],
    unsupported_claims: [],
  };
  assert.equal(
    resumeBulletGroupText(outputs.resume_bullets[0]),
    "• Analyzed approved spectroscopy data.",
  );
  const copy = applicationPackageCopyText(outputs);
  assert.match(copy, /POSITIONING SUMMARY/);
  assert.match(copy, /RESUME BULLETS/);
  assert.match(copy, /COVER LETTER/);
  assert.match(copy, /APPLICATION ANSWERS/);
  assert.doesNotMatch(copy, /gas-memory/);
});

test("application package route and workspace expose the full review flow", () => {
  const route = readFileSync(
    new URL("../app/application-packages/page.tsx", import.meta.url),
    "utf8",
  );
  const workspace = readFileSync(
    new URL(
      "../components/application-packages/application-package-workspace.tsx",
      import.meta.url,
    ),
    "utf8",
  );
  const navigation = readFileSync(
    new URL("../components/common/workspace-nav.tsx", import.meta.url),
    "utf8",
  );

  assert.match(route, /ApplicationPackageWorkspace/);
  assert.match(route, /Application Package Builder/);
  assert.match(workspace, /Resume \+ Cover Letter Builder/);
  assert.match(workspace, /Target opportunity/);
  assert.match(workspace, /Role title/);
  assert.match(workspace, /Company/);
  assert.match(workspace, /Role \/ job description/);
  assert.match(workspace, /Required skills/);
  assert.match(workspace, /Preferred skills/);
  assert.match(workspace, /Responsibilities/);
  assert.match(workspace, /Application questions/);
  assert.match(workspace, /Add question/);
  assert.match(workspace, /Zero questions/);
  assert.match(workspace, /No application questions were supplied/);
  assert.match(workspace, /Select and order memory/);
  assert.match(workspace, /Recommended \{memory\.recommendation_rank/);
  assert.match(workspace, /Recommended for this target/);
  assert.match(workspace, /Other eligible memories/);
  assert.match(workspace, /Requirement coverage/);
  assert.match(workspace, /Writing-quality review/);
  assert.match(workspace, /Provider and model/);
  assert.match(workspace, /Grouped evidence by selected memory/);
  assert.match(workspace, /GroupedWarnings/);
  assert.match(workspace, /WritingQualityCard/);
  assert.match(workspace, /Move \$\{memory\?\.title/);
  assert.match(workspace, /Generate package/);
  assert.match(workspace, /Regenerate new version/);
  assert.match(workspace, /Save edits/);
  assert.match(workspace, /Archive package/);
  assert.match(workspace, /Restore draft/);
  assert.match(workspace, /Validation blocked/);
  assert.match(workspace, /Positioning summary/);
  assert.match(workspace, /Tailored resume bullets/);
  assert.match(workspace, /Copy bullet/);
  assert.match(workspace, /Cover letter draft/);
  assert.match(workspace, /Application answer snippets/);
  assert.doesNotMatch(workspace, /Five (?:reviewable|copy-ready) starting points/);
  assert.match(workspace, /Human-readable evidence trace/);
  assert.match(workspace, /Visible safeguards/);
  assert.match(workspace, /Suggested proof artifacts/);
  assert.match(workspace, /Reviewer questions/);
  assert.match(workspace, /Immutable version history/);
  assert.match(workspace, /Copy full package/);
  assert.match(workspace, /Saved output hidden · new draft required/);
  assert.match(workspace, /packageMatchesInput/);
  assert.match(workspace, /currentFingerprintRef/);
  assert.match(workspace, /setNotice\(errorMessage\(error\)\)/);
  assert.match(workspace, /job text cannot serve as proof/i);
  assert.match(workspace, /strategy-only/);
  assert.match(
    navigation,
    /href: "\/application-packages"[\s\S]*label: "Application Packages"/,
  );
});
