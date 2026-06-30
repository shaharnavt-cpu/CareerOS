# CareerOS Technology Stack

Version: 0.1

Status: Draft

---

# Technology Philosophy

CareerOS should be built using technologies that are:

- Widely adopted in industry
- Easy to maintain
- Modular
- AI-friendly
- Extensible
- Cloud deployable

The architecture should remain model-agnostic so that AI providers can be changed without requiring major code changes.

---

# Frontend

## Framework

Next.js

### Language

TypeScript

### UI

React

### Styling

Tailwind CSS

### Why

- Industry standard
- Excellent developer experience
- Large ecosystem
- Easy deployment
- Works well with browser extensions

---

# Browser Extension

Framework

Plasmo

### Supported Browsers

- Chrome
- Edge

Future

- Firefox
- Brave

### Responsibilities

- Detect supported job sites
- Read job descriptions
- Launch CareerOS
- Autofill supported fields
- Display Fit Score
- Launch application workflow

---

# Backend

Framework

FastAPI

Language

Python

### Why

- Excellent AI ecosystem
- High performance
- Simple API development
- Familiar language
- Easy integration with LLMs

---

# Database

Primary Database

PostgreSQL

### Extensions

pgvector

### Why

PostgreSQL stores structured career knowledge.

pgvector enables semantic search over resumes, projects, achievements, and application history.

---

# Authentication

Clerk

### Responsibilities

- Sign in
- User accounts
- OAuth
- Session management

Future

- Google
- Microsoft
- GitHub
- LinkedIn

---

# Storage

Supabase Storage

Stores

- Resume exports
- Cover letters
- Attachments
- Generated PDFs
- Screenshots
- User uploads

---

# AI Layer

CareerOS is model independent.

Supported providers may include:

- OpenAI
- Anthropic
- Google Gemini
- Local models (future)

The application should never directly depend on a specific provider.

All AI requests should pass through a common AI interface.

---

# Document Generation

Python

Libraries

- python-docx
- ReportLab

Exports

- DOCX
- PDF

Future

- HTML
- Markdown

---

# Email Integration

Version 1

Manual updates

Future

Microsoft Outlook

Gmail

Automatic status tracking

Email classification

---

# Job Sites

Version 1

- LinkedIn
- Workday

Future

- Greenhouse
- Lever
- Handshake
- Indeed
- RippleMatch

---

# Deployment

Frontend

Vercel

Backend

Railway

Database

Supabase PostgreSQL

---

# Development Environment

IDE

Cursor

Additional AI Development

- ChatGPT
- Codex
- Claude Code

Version Control

GitHub

Project Management

GitHub Issues

GitHub Projects

---

# Engineering Principles

## AI Last

Do not use AI when deterministic software can solve the problem.

Examples

Deterministic

- File naming
- GPA
- Graduation dates
- Timeline calculations
- Application tracking

AI

- Resume tailoring
- Cover letters
- Interview preparation
- Company summaries
- Strategy recommendations

---

## Model Independence

Every AI feature should interact through a shared interface.

CareerOS should never be tightly coupled to a single model provider.

---

## Human Approval

Important actions require user confirmation.

Examples

- Resume generation
- Cover letter generation
- Application submission
- Strategy changes

---

## Modular Design

Every major capability should exist as an independent service.

Examples

- Resume Engine
- Cover Letter Engine
- Application Engine
- Analytics Engine
- Career Knowledge Engine

This allows CareerOS to evolve without tightly coupling unrelated features.

---

# Future Integrations

- LinkedIn
- Outlook
- Gmail
- GitHub
- Google Drive
- OneDrive
- Calendar
- Slack
- Microsoft Teams

CareerOS should be designed so future integrations can be added without requiring major architectural changes.
