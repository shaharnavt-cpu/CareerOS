# CareerOS Database Schema

> Version: Draft 0.1

## Purpose

This document defines the relational database schema for CareerOS. It
serves as the implementation reference for SQLAlchemy models, Alembic
migrations, and PostgreSQL.

## Design Principles

-   Canonical career knowledge is editable.
-   Submission snapshots are immutable.
-   Applications are mutable workflows.
-   Evidence is first-class.
-   Every record belongs to a user.
-   All important entities include audit timestamps.

## Core Tables

-   users
-   education
-   experiences
-   projects
-   achievements
-   skills
-   companies
-   jobs
-   applications
-   submissions
-   evidence
-   contacts
-   timeline_events

## Required for Each Table

-   Primary key
-   Foreign keys
-   Data types
-   Indexes
-   Constraints
-   Created/updated timestamps
-   Soft delete strategy
-   Versioning rules

## Implementation Goals

-   PostgreSQL
-   SQLAlchemy ORM
-   Alembic migrations
-   pgvector support (future)
