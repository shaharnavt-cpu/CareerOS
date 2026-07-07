# Sprint 07 — Universal Listening

> Status: Planning Specification
> Version: Draft 1.0

## Objective

Transform CareerOS from accepting a few text files into a universal career evidence listener.

Users should not think about file formats. They should simply provide career artifacts while continuing a natural conversation.

## Product Principle

**CareerOS listens continuously.**

Conversation and evidence ingestion happen in parallel.

## Phase 1 Sources

- PDF
- DOCX
- TXT
- Markdown
- CSV

Future-ready interfaces:

- LinkedIn exports
- Portfolio websites
- GitHub
- Google Drive
- Gmail
- OCR images

## Pipeline

Raw Source
→ Document Detection
→ Source Adapter
→ Specialized Listener
→ Evidence
→ Evidence Fusion
→ Knowledge Reasoning
→ Career Memory
→ Career Stories

## UX

Replace the dedicated upload step with a unified chat composer.

Support:

- Paperclip attachments
- Drag & drop
- Multiple simultaneous files
- Continue chatting while documents are processed
- Add new evidence at any time

## Background Listening

Show progress:

- Queued
- Reading
- Extracting evidence
- Comparing sources
- Preparing proposals
- Complete

## Backend

Implement:

- PDF adapter
- DOCX adapter
- Document detector
- Listening job orchestration
- Progress reporting
- Retry support

Reuse existing Listening and Reasoning architecture.

## Acceptance Criteria

- PDF and DOCX ingestion works.
- Multiple files supported.
- Automatic document detection.
- Conversation remains responsive while processing.
- Existing Story Intelligence remains compatible.

## Definition of Done

CareerOS naturally accepts the professional artifacts people already possess without requiring them to change formats or workflow.
