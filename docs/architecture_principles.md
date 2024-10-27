# Architectural Design Principles

## Core Principles

1. **Domain-Driven Design**: Organize apps based on business domains, not technical concerns.
2. **Clear Ownership**: Each app owns its core models, with judicious cross-app references.
3. **Intra-App Simplicity**: Within an app, leverage Django's features fully, avoiding over-abstraction.
4. **Inter-App Decoupling**: Use event-driven architecture and well-defined interfaces for inter-app communication.
5. **Dependency Injection**: Design for testability and flexibility.
6. **Django-First**: Utilize Django's built-in features by default, introducing custom solutions only when necessary.
7. **Centralized Cross-Cutting Concerns**: Address logging, caching, authentication, etc., in a centralized manner.
8. **Evolutionary Architecture**: Regularly review and refactor as the project grows.
9. **Lightweight Frontend**: Prioritize server-side rendering and progressive enhancement.
10. **Event-Driven Communication**: Use event hub and Celery for scalable, decoupled interactions.
11. **Test-Driven Development with Pytest**: Write isolated, focused tests using pytest, mocks, and dependency injection for clear, concise, and powerful tests.
12. **Custom ID Generation**: Use Base58-encoded UUIDv5 for model IDs to ensure uniqueness, readability, and security.

## Detailed Explanations

### 1. Domain-Driven App Separation

We organize our Django project into apps based on distinct business domains:

- **Commerce**: Handles financial aspects (wallets, transactions, points, fees, etc.)
- **Product Management**: Manages product-related entities (bounties, challenges, competitions, etc.)
- **Talent**: Focuses on individual contributors, their skills, and accomplishments
- **Security**: Manages authentication and user accounts
- **Event Hub**: Facilitates inter-app communication

This promotes high cohesion within apps and loose coupling between apps.

### 2. Model Ownership and Cross-App References

Each app "owns" its core models. Cross-app references are made judiciously:

- Commerce can reference bounties as line items, but the Bounty model lives in Product Management
- Talent references bounties for claims, but doesn't own the Bounty model
- Security owns the User model, while Talent owns the Person model

Models belong to the app most closely aligned with their primary business function. Cross-app references are allowed but minimized to maintain clear boundaries.

### 3. Intra-App Coupling

Within an app, we allow direct usage of models in services:

- Services can directly query and manipulate models within the same app
- This leverages Django's ORM effectively without introducing unnecessary abstractions

Within app boundaries, we prioritize simplicity and leverage Django's features fully, avoiding over-abstraction.

### 4. Inter-App Decoupling

Apps communicate with each other primarily through:

- The Event Hub for asynchronous, event-driven interactions
- Well-defined interfaces or DTOs for synchronous calls when necessary

Inter-app communication is structured to minimize direct dependencies, promoting modularity and easier future refactoring.

### 5. Dependency Injection and Testability

Services use dependency injection for external dependencies:

- This allows for easy mocking in tests
- It provides flexibility to change implementations without altering service logic

Design for testability, using dependency injection to decouple services from their dependencies.

### 6. Leveraging Django Features

We make full use of Django's built-in features:

- ORM for database interactions
- Forms for data validation where appropriate
- Django's authentication system as a foundation for our Security app

Utilize Django's robust feature set by default, introducing custom solutions only when Django's offerings are insufficient for our specific needs.

### 7. Cross-Cutting Concerns

Handle cross-cutting concerns like logging, caching, and authentication through:

- Django middleware for request/response cycle concerns
- Decorators for function/method-level concerns
- The Event Hub for broadcasting events that multiple apps might be interested in

Address cross-cutting concerns in a centralized manner to avoid code duplication and ensure consistent behavior across the application.

### 8. Evolving the Architecture

As the project grows:

- Regularly review and refactor services to manage complexity
- Consider splitting apps if they grow too large or their responsibilities become too diverse
- Continuously evaluate the boundaries between apps and adjust if necessary

The architecture should evolve with the project. Regular reviews and refactoring are essential to maintain clean architecture as the system grows.

### 9. Frontend Architecture

We employ a modern, lightweight approach to frontend development:

- **HTMX**: Used for dynamic HTML interactions
- **Tailwind CSS**: Utilized for styling
- **Tailwind UI**: Leveraged for pre-built components and design patterns

Prioritize server-side rendering and progressive enhancement over complex client-side frameworks.

Implementation Details:
- Django views return HTML fragments for HTMX requests
- Tailwind's utility classes are used directly in HTML templates
- JavaScript is used minimally, primarily through HTMX attributes and occasional custom scripts for complex interactions

Benefits:
1. Simplified Frontend Development
2. Improved Performance
3. Consistency with Backend
4. Rapid Development
5. SEO Friendly

Considerations:
- Ensure proper organization of Django templates
- Use Django template tags and filters effectively
- Regularly audit and optimize Tailwind CSS usage

### 10. Event-Driven Architecture with Event Hub and Celery

Our event_hub app works in conjunction with Celery to facilitate asynchronous, event-driven communication between different parts of the system.

Implementation Details:
- The event_hub defines a set of events that can be published and subscribed to
- Celery tasks are used to process these events asynchronously
- Publishers emit events without needing to know about subscribers
- Subscribers (Celery tasks) process events without direct coupling to publishers

Example:
1. In the commerce app:
   - Use `publish_event('order_completed', {'order_id': order_id})` to emit an event
2. In the event_hub app:
   - Define a Celery task `process_order_completed` that handles the 'order_completed' event
3. In Celery configuration:
   - Set up task routing for 'process_order_completed' to an appropriate queue

Benefits:
1. Scalability: Events can be processed asynchronously, allowing for better load handling
2. Flexibility: New subscribers can be added without modifying existing code
3. Resilience: Failed event processing can be retried using Celery's retry mechanisms

### 11. Test-Driven Development with Pytest

We employ a test-driven development approach using pytest as our testing framework, along with pytest-mock for creating mock objects. Our use of Dependency Injection (DI) facilitates easier testing through the use of mocks.

Implementation Details:
1. Fixtures for setting up test dependencies and mock objects
2. Mocking service methods using mocker.patch.object
3. Data setup using fixtures
4. Isolated tests focusing on specific scenarios or behaviors
5. Assertions using pytest's assert statements

Example:
1. Define a fixture for a mock payment service
2. Create a test function that uses the mock payment service
3. Set up expectations on the mock
4. Call the service method being tested
5. Assert the results and verify mock interactions

Benefits:
1. Isolation: Tests focus on specific components without requiring the entire system to be set up.
2. Speed: Mocked dependencies run faster than real implementations, speeding up the test suite.
3. Flexibility: Easy to test various scenarios, including edge cases and error conditions.
4. Clarity: Tests clearly show the expected inputs and outputs of the system under test.
5. Confidence: Comprehensive test coverage ensures that changes don't break existing functionality.

Considerations:
- Ensure mocks accurately represent the behavior of real dependencies.
- Use integration tests alongside unit tests to verify system behavior with real dependencies.
- Regularly review and update tests as the system evolves to maintain their relevance and accuracy.

### 12. Custom ID Generation

We use a custom Django field, `Base58UUIDv5Field`, for generating IDs across our models.

Benefits:
1. Conciseness and Human Readability: Base58 encoding produces shorter, more readable strings compared to standard UUIDs.
2. Uniqueness Across Systems: UUIDv5 with a custom namespace ensures uniqueness even when multiple systems are generating IDs in parallel.
3. Security: Avoids exposing sequential IDs, which can be a security risk in some scenarios.
4. Consistency: Provides a standardized way of generating IDs across all models in our system.
5. Performance: Base58 encoding is efficient for both encoding and decoding operations.

Implementation:
The `Base58UUIDv5Field` is a custom CharField that generates a Base58-encoded UUIDv5 based on a custom namespace and a per-record UUIDv4.

Usage:
Models use this field as their primary key, ensuring consistent ID generation across the system.

This custom field ensures that all our models have consistent, secure, and user-friendly IDs, which is particularly beneficial for our distributed system architecture.
