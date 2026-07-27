# PROJECT_RULES.md

Version: 1.0
Project: CevonDocs

---

# Purpose

This document defines the engineering rules for implementing CevonDocs.

The primary objective is **a complete, stable, easy-to-understand implementation that satisfies all project requirements with the lowest possible implementation risk.**

When making implementation decisions, always prefer **simplicity over cleverness**.

---

# Core Philosophy

The project is a **capstone**, not a production SaaS.

Optimize for:

* correctness
* simplicity
* readability
* reliability
* maintainability
* predictable implementation

Do **not** optimize for enterprise architecture.

---

# Guiding Principles

## 1. Keep It Simple

Always choose the simplest solution that satisfies the requirement.

Avoid unnecessary abstraction.

Avoid premature optimization.

## 2. Follow the Implementation Plan

The implementation plan is the source of truth.

Do not introduce new architecture unless absolutely necessary.

If a requirement is unclear, implement the simplest reasonable solution.

## 3. One Responsibility Per File

Each file should have one clear purpose.

Examples:

* extraction.py -> GPT extraction
* moderation.py -> moderation
* watermark.py -> watermarking
* confidence.py -> confidence routing

Do not mix unrelated responsibilities.

## 4. Plain Functions First

Prefer standalone functions.

Only introduce classes when there is a clear technical need.

Avoid service classes, managers, controllers, repositories, factories, or similar enterprise patterns.

## 5. Flat Project Structure

Keep the project structure shallow.

Avoid deeply nested folders.

Avoid unnecessary packages.

## 6. Standard Library First

Prefer Python's standard library whenever practical.

Examples:

* sqlite3
* pathlib
* uuid
* json
* logging
* os
* datetime
* base64

Do not add dependencies unless they provide clear value.

---

# FastAPI Rules

* Keep all endpoints inside `main.py`.
* Do not split routers unless explicitly required.
* Keep endpoint logic straightforward.
* Use helper functions from other modules instead of creating additional routing layers.

Required endpoints:

* GET `/health`
* POST `/ingest`
* GET `/review`
* POST `/approve`
* GET `/metrics`

No additional API endpoints unless required.

---

# Database Rules

Use SQLite with `sqlite3`.

Do not introduce:

* SQLAlchemy
* Alembic
* ORM layers
* Repository pattern
* Dependency injection

Database access should remain small and readable.

---

# Error Handling

Handle expected failures.

Examples:

* invalid file
* invalid image
* OpenAI timeout
* OpenAI rate limit
* schema validation failure
* missing document

Do not create large custom exception hierarchies.

Return meaningful HTTP status codes.

---

# Logging

Use Python's built-in logging module.

Never log extracted text before PII redaction.

Keep log messages concise.

---

# AI API Rules

All OpenAI interactions should:

* use retry logic
* validate responses
* fail gracefully
* return structured errors

Never silently ignore failures.

---

# Code Style

Functions should generally stay below approximately 50 lines when practical.

Avoid deeply nested logic.

Prefer early returns.

Keep variable names descriptive.

Avoid unnecessary comments.

Write self-explanatory code.

---

# Dependencies

Keep dependencies minimal.

Do not introduce new libraries unless:

* required by the specification
* they significantly reduce complexity

If an existing dependency can solve the problem, do not add another.

---

# Testing Rules

Every completed milestone should leave the project in a runnable state.

Tests should focus on project requirements, not implementation details.

Required test areas:

* schema validation
* confidence routing
* PII redaction

---

# Milestone Rules

Only work on one milestone at a time.

Do not begin the next milestone until:

* current milestone builds successfully
* current milestone runs successfully
* current milestone has been manually verified
* existing functionality still works

Avoid large multi-feature commits.

---

# Refactoring Rules

Do not refactor unrelated code while implementing a feature.

Only refactor when:

* fixing a bug
* reducing duplication
* significantly improving clarity

Avoid cosmetic refactoring.

---

# Security Rules

Always validate uploaded files.

Never trust filenames.

Generate UUIDs for stored documents.

Never overwrite original uploaded images.

Always save watermarked copies separately.

Redact PII before logging.

---

# Performance Rules

Optimize for correctness first.

Do not introduce caching, concurrency, background workers, or asynchronous processing unless explicitly required.

The project is expected to process one document at a time.

---

# Documentation Rules

Keep README instructions accurate.

Update documentation whenever behavior changes.

Document environment variables in `.env.example`.

---

# Completion Criteria

A milestone is considered complete only if:

* Code builds successfully.
* Application starts successfully.
* Feature works manually.
* Existing functionality still works.
* Tests for that milestone pass.

---

# Out of Scope

Unless explicitly requested, do **not** introduce:

* SQLAlchemy
* Repository Pattern
* Service Layer Architecture
* Dependency Injection Frameworks
* Event Systems
* Message Queues
* Background Workers
* Celery
* Redis
* Microservices
* Authentication Systems
* Authorization Systems
* Multi-user Support
* Multi-tenant Support
* Caching Layers
* Complex Configuration Frameworks
* Kubernetes
* Terraform
* Generic Plugin Systems
* Generic Workflow Engines

---

# Decision Rule

When multiple implementations are possible:

1. Choose the simplest.
2. Choose the easiest to debug.
3. Choose the one with the fewest dependencies.
4. Choose the one with the lowest chance of breaking existing code.
5. Prefer clarity over cleverness.

If a solution feels over-engineered for a capstone project, it probably is.
