# Architectural Design Principles

## 1. Domain-Driven App Separation

We organize our Django project into apps based on distinct business domains:

- **Commerce**: Handles financial aspects (wallets, transactions, points, fees, etc.)
- **Product Management**: Manages product-related entities (bounties, challenges, competitions, etc.)
- **Talent**: Focuses on individual contributors, their skills, and accomplishments
- **Security**: Manages authentication and user accounts
- **Event Hub**: Facilitates inter-app communication

### Principle: 
Apps are separated based on business domains, not technical concerns. This promotes high cohesion within apps and loose coupling between apps.

## 2. Model Ownership and Cross-App References

Each app "owns" its core models. Cross-app references are made judiciously:

- Commerce can reference bounties as line items, but the Bounty model lives in Product Management
- Talent references bounties for claims, but doesn't own the Bounty model
- Security owns the User model, while Talent owns the Person model

### Principle: 
Models belong to the app most closely aligned with their primary business function. Cross-app references are allowed but minimized to maintain clear boundaries.

## 3. Intra-App Coupling

Within an app, we allow direct usage of models in services:

- Services can directly query and manipulate models within the same app
- This leverages Django's ORM effectively without introducing unnecessary abstractions

### Principle: 
Within app boundaries, we prioritize simplicity and leverage Django's features fully, avoiding over-abstraction.

## 4. Inter-App Decoupling

Apps communicate with each other primarily through:

- The Event Hub for asynchronous, event-driven interactions
- Well-defined interfaces or DTOs for synchronous calls when necessary

### Principle: 
Inter-app communication is structured to minimize direct dependencies, promoting modularity and easier future refactoring.

## 5. Dependency Injection and Testability

Services use dependency injection for external dependencies:

- This allows for easy mocking in tests
- It provides flexibility to change implementations without altering service logic

### Principle: 
Design for testability, using dependency injection to decouple services from their dependencies.

## 6. Leveraging Django Features

We make full use of Django's built-in features:

- ORM for database interactions
- Forms for data validation where appropriate
- Django's authentication system as a foundation for our Security app

### Principle: 
Utilize Django's robust feature set by default, introducing custom solutions only when Django's offerings are insufficient for our specific needs.

## 7. Cross-Cutting Concerns

Handle cross-cutting concerns like logging, caching, and authentication through:

- Django middleware for request/response cycle concerns
- Decorators for function/method-level concerns
- The Event Hub for broadcasting events that multiple apps might be interested in

### Principle: 
Address cross-cutting concerns in a centralized manner to avoid code duplication and ensure consistent behavior across the application.

## 8. Evol

