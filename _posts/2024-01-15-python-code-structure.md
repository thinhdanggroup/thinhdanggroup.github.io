---
author:
    name: "Thinh Dang"
    avatar: "/assets/images/avatar.png"
    bio: "Experienced Fintech Software Engineer Driving High-Performance Solutions"
    location: "Viet Nam"
    email: "thinhdang206@gmail.com"
    links:
        -   label: "Linkedin"
            icon: "fab fa-fw fa-linkedin"
            url: "https://www.linkedin.com/in/thinh-dang/"
toc: true
toc_sticky: true
header:
    overlay_image: /assets/images/python-code-structure/banner.jpeg
    overlay_filter: 0.5
    teaser: /assets/images/python-code-structure/banner.jpeg
title: "Crafting Maintainable Python Applications with Domain-Driven Design and Clean Architecture"
tags:
    - Coding

---

In this comprehensive blog post, we embark on a journey to explore the intricacies of crafting maintainable Python
applications using Domain-Driven Design (DDD) and Clean Architecture. We delve into the core principles of DDD,
emphasizing its role in aligning software design with business requirements. We then provide a thorough overview of
Clean Architecture, explaining its concentric circles (layers) and the responsibilities of each layer. To bridge the gap
between theory and practice, we offer practical techniques for implementing Clean Architecture in Python, covering
dependency injection, layered structure, value objects and entities, domain events, repositories, and testing
strategies. To solidify our understanding, we walk through the process of building a simple auctioning system using
Clean Architecture and DDD in Python, showcasing how each layer interacts and how business logic is isolated. We
conclude by addressing common pitfalls and misconceptions, providing practical advice for junior software engineers, and
suggesting resources for further learning. Whether you're a seasoned developer or just starting out, this blog post will
equip you with the knowledge and skills to create robust, maintainable, and scalable Python applications.

## Introduction

Domain-Driven Design (DDD) and Clean Architecture are two important concepts in software engineering that can help you
build robust and maintainable Python applications.

### Domain-Driven Design (DDD)

DDD is a software development approach that focuses on creating a model of the domain that is independent of the
implementation. This can help you to better understand the problem you are trying to solve and to design a solution that
is more likely to be successful.

### Clean Architecture

Clean Architecture is a software architecture pattern that is designed to improve the maintainability, testability, and
scalability of software applications. The responsibilities of each layer in Clean Architecture vary depending on the
specific application, but typically the Domain Layer is responsible for the business logic, the Application Layer is
responsible for the user interface and application logic, and the Infrastructure Layer is responsible for the data
access and other infrastructure concerns.

### Why are DDD and Clean Architecture important for Python applications?

DDD and Clean Architecture can help you to build Python applications that are:

* **More maintainable:** DDD and Clean Architecture can help you to create a codebase that is easier to understand and
  change. This can make it easier to maintain your application over time.
* **More testable:** DDD and Clean Architecture can help you to create a codebase that is easier to test. This can make
  it easier to catch bugs early and to ensure that your application is working as expected.
* **More scalable:** DDD and Clean Architecture can help you to create a codebase that is more scalable. This can make
  it easier to handle increasing traffic or to add new features to your application.

In the next section, we will discuss how to apply DDD and Clean Architecture to Python applications.

## Understanding Domain-Driven Design

In the previous section, we introduced Domain-Driven Design (DDD) and Clean Architecture as two important concepts for
building robust and maintainable Python applications. In this section, we will delve deeper into the core principles of
DDD and explore how it can help you align software design with business requirements.

### Core Principles of Domain-Driven Design

DDD is based on the idea that the domain model should be the center of the software system, and that all other
components of the system should be designed to support the domain model. The core principles of DDD include:

* **Ubiquitous Language:** A shared language that is used by all stakeholders to describe the domain. This helps to
  ensure that everyone involved in the project has a common understanding of the problem space.
* **Bounded Contexts:** A bounded context is a part of the domain that is separated from other parts by a boundary. This
  allows different teams to work on different parts of the domain without having to worry about the details of other
  parts.
* **Entities:** Entities are the real-world objects that are represented in the software system. They have a unique
  identity and a set of properties that describe their state.
* **Value Objects:** Value objects are immutable objects that represent a single value. They do not have an identity and
  are compared by their value.
* **Aggregates:** Aggregates are groups of entities that are related to each other. They are the unit of consistency in
  DDD and can be used to ensure that data is always consistent.
* **Repositories:** Repositories are responsible for persisting and retrieving entities and aggregates from the
  database.

### How DDD Aligns Software Design with Business Requirements

DDD helps to align software design with business requirements by focusing on the domain model. The domain model is a
representation of the real-world problem space that the software system is intended to solve. By focusing on the domain
model, software designers can ensure that the system is designed to meet the needs of the business.

DDD also helps to improve communication between business stakeholders and software developers. By using a shared
language, business stakeholders and software developers can more easily understand each other's needs and requirements.
This can lead to better software systems that are more closely aligned with the business's goals.

In this section, we have explored the core principles of DDD and discussed how it can help to align software design with
business requirements. In the next section, we will discuss how to apply DDD and Clean Architecture to Python
applications.

## Clean Architecture Overview

In the previous section, we introduced Domain-Driven Design (DDD) and Clean Architecture as two important concepts for
building robust and maintainable Python applications. In this section, we will delve deeper into Clean Architecture and
explore its fundamental idea and the concentric circles (layers) it comprises. We will also discuss the responsibilities
of each layer, highlighting the separation of concerns and the isolation of the domain model.

### Fundamental Idea of Clean Architecture

Clean Architecture is a software architecture pattern that emphasizes the separation of concerns and the isolation of
the domain model from the rest of the system. The fundamental idea behind Clean Architecture is that the architecture of
a software system should be designed to minimize the dependencies between the different components of the system. This
makes the system easier to understand, maintain, and test.

### Concentric Circles (Layers) of Clean Architecture

Clean Architecture is organized into a series of concentric circles (layers), with the domain layer at the core and the
infrastructure layer at the outermost layer. The layers are as follows:

* **Domain Layer:** The domain layer contains the business logic of the system. It is the core of the system and should
  be independent of the other layers.
* **Application Layer:** The application layer contains the use cases and workflows of the system. It uses the domain
  layer to perform business logic.
* **Infrastructure Layer:** The infrastructure layer contains the technical details of the system, such as the database,
  the web server, and the operating system.

### Responsibilities of Each Layer

Each layer in Clean Architecture has its own specific responsibilities. The responsibilities of each layer are as
follows:

* **Domain Layer:**
    * Defines the business rules and logic of the system.
    * Is independent of the other layers.
    * Should be easy to understand and maintain.
* **Application Layer:**
    * Contains the use cases and workflows of the system.
    * Uses the domain layer to perform business logic.
    * Should be easy to test.
* **Infrastructure Layer:**
    * Contains the technical details of the system.
    * Is responsible for the persistence, communication, and presentation of data.

### Separation of Concerns and Isolation of the Domain Model

One of the key benefits of Clean Architecture is that it promotes the separation of concerns and the isolation of the
domain model. This makes the system easier to understand, maintain, and test.

The separation of concerns is achieved by organizing the system into layers, with each layer having its own specific
responsibilities. This makes it easier to identify and fix problems in the system.

The isolation of the domain model is achieved by placing the domain layer at the core of the system. This makes it
easier to change the domain model without affecting the rest of the system.

In this section, we have provided a comprehensive explanation of Clean Architecture, its fundamental idea, and the
concentric circles (layers) it comprises. We have also discussed the responsibilities of each layer, highlighting the
separation of concerns and the isolation of the domain model. In the next section, we will discuss how to apply Clean
Architecture and Domain-Driven Design in Python.

## Applying Clean Architecture and Domain-Driven Design in Python

In the previous sections, we introduced Domain-Driven Design (DDD) and Clean Architecture as important concepts for
building robust and maintainable Python applications. In this section, we will discuss practical techniques for
implementing Clean Architecture in Python, covering dependency injection, layered structure, value objects and entities,
domain events, repositories, and testing strategies. We will emphasize the importance of decoupling components and
ensuring testability.

### Dependency Injection

Dependency injection is a technique for decoupling components in Python. It involves passing dependencies to a function
or class instead of creating them within the function or class itself. This makes it easier to test the function or
class in isolation and to replace dependencies with mocks or stubs.

There are a number of ways to implement dependency injection in Python. One common approach is to use a dependency
injection framework such as Dagger or Injector. These frameworks allow you to define dependencies and then inject them
into your classes and functions automatically.

### Layered Structure

The layered structure of Clean Architecture is a way of organizing your codebase into distinct layers. The domain layer
is at the core of the application and contains the business logic. The application layer sits on top of the domain layer
and contains the use cases and workflows of the application. The infrastructure layer is at the bottom of the stack and
contains the technical details of the application, such as the database, the web server, and the operating system.

Organizing your codebase into layers makes it easier to understand, maintain, and test your application. It also makes
it easier to make changes to the application without affecting other parts of the system.

### Value Objects and Entities

Value objects and entities are two important concepts in DDD. Value objects are immutable objects that represent a
single value. They do not have an identity and are compared by their value. Entities are real-world objects that have a
unique identity and a set of properties that describe their state.

In Python, you can create value objects using the `dataclass` decorator. Entities can be created using the `namedtuple`
class.

### Domain Events

Domain events are events that occur within the domain layer of an application. They are used to communicate changes in
the state of the domain to other parts of the application. Domain events can be used to trigger actions, such as sending
a notification to a user or updating a database record.

In Python, you can create domain events using the `Event` class from the `eventlet` library.

### Repositories

Repositories are responsible for persisting and retrieving entities and aggregates from the database. They provide a way
to abstract away the details of the underlying data storage mechanism.

In Python, you can create repositories using the `Repository` class from the `sqlalchemy` library.

### Testing Strategies

Testing is an important part of software development. It helps to ensure that your application is working as expected
and that it is free of bugs.

There are a number of different testing strategies that you can use with Clean Architecture and DDD. Some common
strategies include:

* **Unit testing:** Unit testing involves testing individual functions and classes in isolation.
* **Integration testing:** Integration testing involves testing the interaction between different components of your
  application.
* **End-to-end testing:** End-to-end testing involves testing the entire application from start to finish.

You should use a combination of different testing strategies to ensure that your application is thoroughly tested.

In this section, we have discussed practical techniques for implementing Clean Architecture and DDD in Python. We have
covered dependency injection, layered structure, value objects and entities, domain events, repositories, and testing
strategies. We have emphasized the importance of decoupling components and ensuring testability.

By following the techniques discussed in this section, you can build robust and maintainable Python applications that
are easy to understand, maintain, and test.

### Example Project: Auctioning Platform with Clean Architecture and Domain-Driven Design in Python using FastAPI

#### Project Structure with Interfaces

The project will be structured using Clean Architecture and Domain-Driven Design principles, with interfaces defined
within the domain layer. The structure will consist of the following layers:

- `app/`
    - `__init__.py` (initializes the application)
    - `domain/` (contains entities, value objects, and interfaces)
        - `__init__.py`
        - `interfaces/` (directory containing all interface definitions)
            - `__init__.py`
            - `iauction_repository.py` (interface for AuctionRepository)
            - `ithird_party_service.py` (interface for ThirdPartyService)
        - `entities/`
            - `__init__.py`
            - `auction.py` (contains the Auction entity class)
        - `value_objects/`
            - `__init__.py`
            - `money.py` (contains the Money value object class)
    - `application/` (contains use cases and workflows)
        - `__init__.py`
        - `auction_service.py` (contains the AuctionService class)
    - `infrastructure/` (contains technical details like database and web server)
        - `__init__.py`
        - `repositories/`
            - `__init__.py`
            - `auction_repository.py` (implementation of AuctionRepository interface)
        - `services/`
            - `__init__.py`
            - `third_party_service.py` (implementation of ThirdPartyService interface)
    - `main.py` (entry point for the FastAPI application)

#### Defining Interfaces

Interfaces are defined in the `domain/interfaces/` directory and are used to establish contracts for repositories and
services. Here's an example of an interface for a repository:

```python
# app/domain/interfaces/iauction_repository.py
from abc import ABC, abstractmethod
from app.domain.entities.auction import Auction


class IAuctionRepository(ABC):

    @abstractmethod
    def save(self, auction: Auction):
        pass

    @abstractmethod
    def retrieve(self, auction_id: int):
        pass
```

And an interface for a service:

```python
# app/domain/interfaces/ithird_party_service.py
from abc import ABC, abstractmethod


class IThirdPartyService(ABC):

    @abstractmethod
    async def get_data(self, endpoint: str):
        pass
```

#### Implementing Interfaces

Implementations of these interfaces are provided in the `infrastructure` layer. For example, the `AuctionRepository`
class implements the `IAuctionRepository` interface:

```python
# app/infrastructure/repositories/auction_repository.py
from app.domain.interfaces.iauction_repository import IAuctionRepository
from app.domain.entities.auction import Auction


class AuctionRepository(IAuctionRepository):

    def save(self, auction: Auction):
        # Logic to save the auction to the database
        pass

    def retrieve(self, auction_id: int):
        # Logic to retrieve an auction from the database
        pass
```

Similarly, the `ThirdPartyService` class implements the `IThirdPartyService` interface:

```python
# app/infrastructure/services/third_party_service.py
from app.domain.interfaces.ithird_party_service import IThirdPartyService
import httpx


class ThirdPartyService(IThirdPartyService):

    def __init__(self, base_url: str):
        self.base_url = base_url

    async def get_data(self, endpoint: str):
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}{endpoint}")
            response.raise_for_status()
            return response.json()
```

#### FastAPI Implementation

The `main.py` file serves as the entry point for the FastAPI application. It sets up the application and wires up the
dependencies, including the implementations of the interfaces:

```python
# main.py
from fastapi import FastAPI, Depends
from app.domain.entities.auction import Auction
from app.domain.value_objects.money import Money
from app.application.auction_service import AuctionService
from app.infrastructure.repositories.auction_repository import AuctionRepository
from app.infrastructure.services.third_party_service import ThirdPartyService

app = FastAPI()

# Dependency Injection
auction_repo = AuctionRepository()
third_party_service = ThirdPartyService(base_url="https://example.com/api/")
auction_service = AuctionService(auction_repo, third_party_service)


@app.post("/create_auction")
async def create_auction(title: str, start_date: str, end_date: str, initial_bid: Money):
    auction = Auction(title, start_date, end_date, initial_bid)
    await auction_service.create_auction(auction)
    # ... save auction to the repository ...
    return {"message": "Auction created successfully.", "auction": auction.__dict__}


# Run the application with Uvicorn
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
```

This FastAPI application demonstrates the creation of an auction using the defined domain entities and value objects,
with the integration of a third-party service. The `create_auction` endpoint accepts the necessary parameters, creates
an `Auction` instance, and then uses the `AuctionService` to handle the business logic, including fetching data from the
third-party service.

In this section, we have walked through the process of building a simple auctioning system using Clean Architecture and
DDD in Python. We have demonstrated how each layer interacts, how business logic is isolated, and how to handle
real-world challenges and trade-offs.

By following the techniques discussed in this section, you can build robust and maintainable Python applications that
are easy to understand, maintain, and test.

## Tips for Junior Software Engineers

In this section, we will address common pitfalls and misconceptions that junior software engineers may encounter when
applying DDD and Clean Architecture. We will provide practical advice, suggest resources for further learning, and
encourage continuous improvement.

### Common Pitfalls and Misconceptions

* **Misunderstanding the purpose of DDD and Clean Architecture:** DDD and Clean Architecture are not silver bullets.
  They are tools that can help you build better software, but they are not a guarantee of success. It is important to
  understand the purpose of each approach and how it can benefit your project.
* **Trying to apply DDD and Clean Architecture to every project:** Not every project is a good fit for DDD and Clean
  Architecture. These approaches are best suited for complex projects with a large number of stakeholders. If you are
  working on a small project with a simple domain, it may be overkill to use DDD and Clean Architecture.
* **Getting bogged down in the details:** DDD and Clean Architecture can be complex topics. It is important to focus on
  the big picture and avoid getting bogged down in the details. Once you have a good understanding of the basic
  principles, you can start to apply them to your projects.
* **Not testing your code:** Testing is an essential part of software development. It is especially important to test
  your code when you are using DDD and Clean Architecture. These approaches can make it more difficult to write tests,
  but it is important to ensure that your code is working as expected.

### Practical Advice

* **Start small:** Don't try to apply DDD and Clean Architecture to a large project right away. Start with a small
  project that you can easily manage. This will help you to learn the basics and gain experience.
* **Focus on the domain:** The most important part of DDD is understanding the domain. Spend time talking to
  stakeholders and learning about the business problem that you are trying to solve. Once you have a good understanding
  of the domain, you can start to design your software solution.
* **Use a framework:** There are a number of frameworks that can help you to implement DDD and Clean Architecture in
  your projects. These frameworks can make it easier to get started and to avoid common pitfalls.
* **Test your code:** As mentioned above, testing is essential. Make sure to write tests for your code, especially when
  you are using DDD and Clean Architecture.
* **Get feedback:** Once you have implemented DDD and Clean Architecture in a project, get feedback from your team
  members and stakeholders. This feedback can help you to identify areas where you can improve your implementation.

### Encourage Continuous Improvement

DDD and Clean Architecture are complex topics. It takes time and effort to learn them and to apply them effectively.
Don't get discouraged if you don't get it right the first time. Just keep learning and practicing, and you will
eventually become proficient in these approaches.

Here are some tips for encouraging continuous improvement:

* **Read books and articles:** There are a number of great books and articles available on DDD and Clean Architecture.
  Make a habit of reading these resources to stay up-to-date on the latest trends and best practices.
* **Attend conferences and workshops:** There are a number of conferences and workshops held each year on DDD and Clean
  Architecture. Attending these events is a great way to learn from experts and to network with other developers who are
  using these approaches.
* **Contribute to open source projects:** There are a number of open source projects that are using DDD and Clean
  Architecture. Contributing to these projects is a great way to learn more about these approaches and to get feedback
  on your work.
* **Get involved in online communities:** There are a number of online communities dedicated to DDD and Clean
  Architecture. Participating in these communities is a great way to learn from others and to share your own
  experiences.

By following these tips, you can become a proficient DDD and Clean Architecture developer and build robust and
maintainable software applications.

In this section, we have addressed common pitfalls and misconceptions that junior software engineers may encounter when
applying DDD and Clean Architecture. We have provided practical advice, suggested resources for further learning, and
encouraged continuous improvement.

By following the tips in this section, you can avoid common pitfalls, learn from others, and become a proficient DDD and
Clean Architecture developer.

## Conclusion

In this blog post, we have discussed the importance of Domain-Driven Design (DDD) and Clean Architecture for building
robust and maintainable Python applications. We have explored the core principles of DDD, the concentric circles (
layers) of Clean Architecture, and the responsibilities of each layer. We have also provided practical techniques for
implementing DDD and Clean Architecture in Python, covering dependency injection, layered structure, value objects and
entities, domain events, repositories, and testing strategies.

By following the techniques discussed in this blog post, you can build Python applications that are:

* **More maintainable:** DDD and Clean Architecture help you to create a codebase that is easier to understand and
  change. This can make it easier to maintain your application over time.
* **More testable:** DDD and Clean Architecture help you to create a codebase that is easier to test. This can make it
  easier to catch bugs early and to ensure that your application is working as expected.
* **More scalable:** DDD and Clean Architecture help you to create a codebase that is more scalable. This can make it
  easier to handle increasing traffic or to add new features to your application.

In addition to the benefits mentioned above, DDD and Clean Architecture can also help you to:

* **Improve communication between business stakeholders and software developers:** By using a shared language, business
  stakeholders and software developers can more easily understand each other's needs and requirements. This can lead to
  better software systems that are more closely aligned with the business's goals.
* **Reduce the risk of introducing bugs:** By isolating the domain model from the rest of the system, DDD and Clean
  Architecture make it less likely that changes to the domain model will cause problems in other parts of the system.
* **Make it easier to reuse code:** By organizing your codebase into layers, DDD and Clean Architecture make it easier
  to reuse code across different projects.

Overall, DDD and Clean Architecture are powerful tools that can help you to build better Python applications. If you are
not already using these approaches, I encourage you to give them a try. You may be surprised at how much they can
improve your productivity and the quality of your code.

### References

* [Domain-Driven Design: Tackling Complexity in the Heart of Software](https://www.amazon.com/Domain-Driven-Design-Tackling-Complexity-Software/dp/0321125215)
  by Eric Evans
* [Clean Architecture: A Craftsman's Guide to Software Structure and Design](https://www.amazon.com/Clean-Architecture-Craftsmans-Software-Structure/dp/0134494164)
  by Robert C. MartinMatt Wynne