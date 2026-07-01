# CareerOS API Specification

> Version: Draft 0.1

## Purpose

Defines the REST API contract between the frontend, backend, browser
extension, and future integrations.

## Initial Endpoints

-   GET /api/health
-   GET /api/profile
-   PATCH /api/profile
-   GET /api/applications
-   POST /api/applications
-   GET /api/applications/{id}
-   PATCH /api/applications/{id}
-   POST /api/jobs/analyze
-   POST /api/resumes/generate
-   POST /api/cover-letters/generate

Each endpoint should define: - Request schema - Response schema -
Validation - Error responses - Authentication requirements
