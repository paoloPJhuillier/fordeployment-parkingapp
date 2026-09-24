# Cebuana Lhuillier Parking Reservation System — Documentation

## Overview
Complete technical and business documentation for the corporate parking reservation application.

## Document Index

| # | Document | Description | Path |
|---|----------|-------------|------|
| 1 | [Business Requirements Document](01-business-requirements/BRD.md) | User stories, business rules, stakeholder needs | `01-business-requirements/` |
| 2 | [System Requirements Specification](02-system-requirements/SRS.md) | Functional & non-functional requirements traceability | `02-system-requirements/` |
| 3 | [System Design Document](03-system-design/system-design.md) | Architecture, data model, sequence diagrams, compliance | `03-system-design/` |
| 3a | [Architecture Diagrams](03-system-design/diagrams/architecture.md) | Component, deployment, integration diagrams | `03-system-design/diagrams/` |
| 3b | [Entity Relationship Diagram](03-system-design/diagrams/erd.md) | Database schema and relationships | `03-system-design/diagrams/` |
| 3c | [Sequence Diagrams](03-system-design/diagrams/sequences.md) | Key workflow interactions | `03-system-design/diagrams/` |
| 3d | [Compliance Matrix](03-system-design/compliance-matrix.md) | Requirements-to-implementation traceability | `03-system-design/` |
| 4 | [Test Plan & Results](04-testing/test-plan.md) | Test strategy, scripts, and execution results | `04-testing/` |
| 4a | [Test Scripts](04-testing/test-scripts.md) | Unit, functional, integration, UI, security test cases | `04-testing/` |
| 4b | [Test Execution Results](04-testing/test-results.md) | Latest test run outcomes | `04-testing/` |
| 5a | [End User Guide](05-user-guides/end-user-guide.md) | Booking, vehicles, reservations | `05-user-guides/` |
| 5b | [Admin User Guide](05-user-guides/admin-user-guide.md) | User management, buildings, zones, reports | `05-user-guides/` |
| 5c | [Attendant Guide](05-user-guides/attendant-guide.md) | Daily operations, no-show reporting | `05-user-guides/` |
| 6 | [Deployment Guide](06-deployment/deployment-guide.md) | AWS deployment, prerequisites, step-by-step | `06-deployment/` |

## Technology Stack
- **Frontend:** React 19, TailwindCSS, shadcn/ui, Recharts
- **Backend:** Python FastAPI, Motor (async MongoDB), fastapi-utilities
- **Database:** MongoDB
- **Authentication:** HttpOnly cookie-based JWT with device fingerprinting
- **Background Tasks:** Auto no-show marking, waitlist expiry management

## Version
- **Application Version:** 2.0.0
- **Documentation Date:** February 24, 2026
- **Last Updated By:** System Documentation Generator
