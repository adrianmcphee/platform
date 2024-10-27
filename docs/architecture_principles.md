# Architectural Design Principles

## Core Principles

1. Domain-Driven Design
2. Clear Ownership
3. Intra-App Simplicity
4. Inter-App Decoupling
5. Dependency Injection
6. Django-First Approach
7. Centralized Cross-Cutting Concerns
8. Evolutionary Architecture
9. Lightweight Frontend
10. Event-Driven Communication
11. Test-Driven Development with Pytest
12. Custom ID Generation

## Detailed Explanations

### 1. Domain-Driven Design

- Organize apps based on business domains:
  - Commerce: Financial aspects
  - Product Management: Bounties, challenges, competitions
  - Talent: Contributors, skills, accomplishments
  - Security: Authentication, user accounts
  - Event Hub: Inter-app communication

### 2. Clear Ownership

- Each app owns its core models
- Cross-app references are minimized
- Example: Commerce references bounties, but Bounty model lives in Product Management

### 3. Intra-App Simplicity

- Direct usage of models in services within an app
- Leverage Django's ORM effectively
- Avoid unnecessary abstractions

### 4. Inter-App Decoupling

- Use Event Hub for asynchronous communication
- Employ Data Transfer Objects (DTOs) for synchronous calls
- Example: BountyPurchaseData DTO in common/data_transfer_objects.py

### 5. Dependency Injection

- Design for testability and flexibility
- Allows easy mocking in tests
- Facilitates changing implementations without altering service logic

### 6. Django-First Approach

- Utilize Django's built-in features:
  - ORM for database interactions
  - Forms for data validation
  - Authentication system

### 7. Centralized Cross-Cutting Concerns

- Handle logging, caching, authentication through:
  - Django middleware
  - Decorators
  - Event Hub for broadcasting events

### 8. Evolutionary Architecture

- Regularly review and refactor services
- Split apps when they grow too large
- Continuously evaluate app boundaries

### 9. Lightweight Frontend

- Use HTMX for dynamic HTML interactions
- Employ Tailwind CSS for styling
- Leverage Tailwind UI for pre-built components
- Prioritize server-side rendering and progressive enhancement

### 10. Event-Driven Communication

- Use Event Hub with Celery for asynchronous, decoupled interactions
- Publishers emit events without knowing subscribers
- Subscribers process events without direct coupling to publishers

### 11. Test-Driven Development with Pytest

- Use pytest and pytest-mock
- Create fixtures for mock objects
- Inject mock dependencies into services
- Set expectations on mocks
- Assert results and interactions with mocks

### 12. Custom ID Generation

- Use Base58UUIDv5Field for model IDs
- Benefits:
  - Conciseness and readability
  - Uniqueness across systems
  - Security
  - Consistency
  - Performance
