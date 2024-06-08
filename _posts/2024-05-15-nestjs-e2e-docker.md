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
    overlay_image: /assets/images/nestjs-e2e-docker/banner.jpeg
    overlay_filter: 0.5
    teaser: /assets/images/nestjs-e2e-docker/banner.jpeg
title: "Mastering End-to-End Testing in NestJS with TypeScript and Docker"
tags:
    - NestJS
    - NodeJS
    - E2E Testing
    - Docker

---

This article is a step-by-step guide to mastering end-to-end testing in NestJS applications using TypeScript. It covers the importance of E2E testing, setting up the testing environment, and writing and running E2E tests. The article also provides unique insights into testing scenarios involving PostgreSQL and Redis databases, including the Cache Aside pattern. Whether you're a beginner or an experienced developer, this article offers valuable knowledge and best practices to ensure the reliability and robustness of your NestJS applications.

### Introduction

As software applications continue to grow in complexity, ensuring their reliability and robustness becomes increasingly important. One crucial aspect of this is testing, and in particular, end-to-end (E2E) testing. In this blog post, we will delve into the world of E2E testing for NestJS applications using TypeScript, exploring the importance of E2E testing, setting up the testing environment, and writing and running E2E tests.

#### The Importance of E2E Testing

E2E testing is a crucial step in the software development lifecycle, as it ensures that the application works as expected from the user's perspective. By simulating real-world scenarios, E2E testing helps to identify issues that may not be caught by unit testing or integration testing. This is particularly important for NestJS applications, which often involve complex interactions between multiple components and services.

#### Introducing the Technologies

In this blog post, we will be using the following technologies:

* **NestJS**: A popular Node.js framework for building efficient, scalable, and enterprise-grade server-side applications.
* **TypeScript**: A statically typed, superset of JavaScript that helps to improve code maintainability and scalability.
* **Docker**: A containerization platform that allows us to easily manage and deploy applications.
* **PostgreSQL**: A powerful, open-source relational database management system.
* **Redis**: An in-memory, NoSQL database that provides high-performance data storage and caching.

By the end of this blog post, you will have a comprehensive understanding of how to write effective E2E tests for your NestJS applications using TypeScript, and how to integrate them with PostgreSQL and Redis databases.

In the next section, we will discuss the prerequisites for getting started with E2E testing in NestJS.

### Prerequisites

Before we dive into the technical details of mastering end-to-end testing in NestJS with TypeScript, it's essential to ensure you have the necessary knowledge and skills to follow along. In this section, we'll cover the prerequisites and provide a step-by-step guide on setting up the required environment.

#### Knowledge and Skills

To get the most out of this guide, you should have a basic understanding of:

* **Node.js**: Familiarity with Node.js and its ecosystem is crucial for working with NestJS.
* **TypeScript**: Knowledge of TypeScript syntax and concepts is necessary for writing efficient and maintainable code.
* **NestJS**: Understanding of NestJS framework and its core concepts, such as modules, controllers, and services.
* **Docker**: Basic knowledge of Docker and containerization is required for setting up the testing environment.
* **PostgreSQL and Redis**: Familiarity with relational databases (PostgreSQL) and NoSQL databases (Redis) is necessary for understanding the testing scenarios.

#### Required Setup and Installations

To follow along with the examples and tutorials in this guide, you'll need to set up the following environment:

1. **Node.js**: Install Node.js (version 14 or later) from the official website: <https://nodejs.org/en/download/>
2. **NestJS**: Install NestJS using the following command: `npx @nestjs/cli new my-nest-app`
3. **Jest**: Install Jest as a dev dependency using the following command: `npm install --save-dev jest`
4. **Docker**: Install Docker from the official website: <https://www.docker.com/get-docker>
5. **PostgreSQL and Redis**: Install PostgreSQL and Redis using Docker containers. You can use the following commands:
        ```sh
        docker run -d --name postgres -p 5432:5432 postgres
        docker run -d --name redis -p 6379:6379 redis
        ```
6. **TypeScript**: Install TypeScript as a dev dependency using the following command: `npm install --save-dev typescript`

By the end of this section, you should have a solid understanding of the prerequisites and a fully set up environment to start writing end-to-end tests for your NestJS application. In the next section, we'll dive deeper into understanding E2E testing and its importance in the testing pyramid.


### Understanding E2E Testing

As we dive into the world of end-to-end (E2E) testing in NestJS, it's essential to understand the concept and its significance in the testing pyramid. In this section, we'll explore what E2E testing is, its role in the testing pyramid, and the benefits it brings to a NestJS application.

#### Definition and Role in the Testing Pyramid

E2E testing is a type of software testing that evaluates the entire software application from start to finish, simulating real-world user scenarios. It sits at the top of the testing pyramid, complementing unit and integration testing. This comprehensive approach provides a broad view of the system's functionality and user experience.

```
          +---------------+
          |  E2E Testing  |
          +---------------+
                  |
                  |
                  v
          +---------------+
          | Integration  |
          |  Testing      |
          +---------------+
                  |
                  |
                  v
          +---------------+
          |  Unit Testing  |
          +---------------+
```

#### Benefits for NestJS Applications

E2E testing offers several benefits for NestJS applications, including:

* **Improved application stability and reliability**: E2E testing helps identify defects and issues early on, reducing the risk of defects reaching production.
* **Reduced risk of defects reaching production**: By simulating real-world user scenarios, E2E testing ensures that the application behaves as expected, reducing the likelihood of defects making it to production.
* **Enhanced user experience and satisfaction**: E2E testing verifies that the application meets user expectations, leading to increased user satisfaction and loyalty.

By incorporating E2E testing into your NestJS application, you can ensure a more robust, reliable, and user-friendly experience.

In the next section, we'll explore how to set up the testing environment in NestJS, including configuring Jest and Docker for PostgreSQL and Redis.

#### Setting Up the Testing Environment

In this section, we will provide a step-by-step guide on setting up the testing environment in NestJS. We will explain the `jest.config.js` and `test` script in `package.json` and guide you on setting up Docker for PostgreSQL and Redis.

##### Configuring Jest

To set up Jest for our NestJS application, we need to create a `jest.config.js` file in the root of our project. This file will contain the configuration settings for Jest. Here's an example of what the file might look like:

```javascript
module.exports = {
  preset: 'jest-preset-angular',
  setupFilesAfterEnv: ['<rootDir>/setupJest.ts'],
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
  },
};
```

In this example, we're telling Jest to use the `jest-preset-angular` preset, which provides some default settings for Angular and NestJS applications. We're also specifying a `setupFilesAfterEnv` file, which will be executed after the environment has been set up. Finally, we're configuring the `moduleNameMapper` to resolve module names correctly.

##### Setting Up the Test Script

Next, we need to add a `test` script to our `package.json` file. This script will be used to run our tests using Jest. Here's an example of what the script might look like:

```json
"scripts": {
  "test": "jest",
},
```

This script simply runs Jest with the default configuration.

##### Setting Up Docker for PostgreSQL and Redis

To set up Docker for PostgreSQL and Redis, we'll need to create a `docker-compose.yml` file in the root of our project. This file will define the services we want to run using Docker. Here's an example of what the file might look like:

```yaml
version: '3'
services:
  db:
    image: postgres
    environment:
      POSTGRES_DB: mydb
      POSTGRES_USER: myuser
      POSTGRES_PASSWORD: mypassword
    ports:
      - "5432:5432"
  redis:
    image: redis
    ports:
      - "6379:6379"
```

In this example, we're defining two services: `db` for PostgreSQL and `redis` for Redis. We're specifying the images to use, as well as the environment variables and ports to expose.

To start the services, we can run the following command:

```sh
docker-compose up -d
```

This will start the services in detached mode, allowing us to run our tests in the background.

That's it for setting up the testing environment in NestJS! In the next section, we'll dive into writing our first end-to-end test.

#### Writing Your First E2E Test

In this section, we will provide a detailed walkthrough of writing a basic E2E test in NestJS. We will explain the `describe`, `it`, and `expect` functions and guide you through writing your first E2E test.

##### Understanding the `describe` Function

The `describe` function is a global function provided by Jest that allows you to group related tests together. It takes two arguments: a string description of the test suite and a callback function that contains the actual tests.

```typescript
describe('UsersController', () => {
  // tests go here
});
```

In the example above, we are creating a test suite for the `UsersController` class.

##### Understanding the `it` Function

The `it` function is a global function provided by Jest that allows you to define a single test. It takes two arguments: a string description of the test and a callback function that contains the actual test.

```typescript
it('should return a list of users', () => {
  // test implementation goes here
});
```

In the example above, we are defining a test that checks if the `UsersController` returns a list of users.

##### Understanding the `expect` Function

The `expect` function is a global function provided by Jest that allows you to assert that a certain condition is true. It takes a value as an argument and returns an object with various matcher functions.

```typescript
expect(response.status).toBe(200);
```

In the example above, we are asserting that the status code of the response is 200.

##### Writing Your First E2E Test

Let's create a simple E2E test for our `UsersController` class. We will test that the controller returns a list of users when we send a GET request to the `/users` endpoint.

```typescript
import { Test, TestingModule } from '@nestjs/testing';
import * as request from 'upertest';
import { UsersController } from './users.controller';

describe('UsersController', () => {
  let app: INestApplication;

  beforeEach(async () => {
    const moduleFixture: TestingModule = await Test.createTestingModule({
      controllers: [UsersController],
    }).compile();

    app = moduleFixture.createNestApplication();
    await app.init();
  });

  it('should return a list of users', () => {
    return request(app.getHttpServer())
     .get('/users')
     .expect(200)
     .expect((response) => {
        expect(response.body).toBeInstanceOf(Array);
      });
  });
});
```

In the example above, we are creating a test suite for the `UsersController` class. We are using the `beforeEach` function to create a new instance of the `NestApplication` class and initialize it before each test. In the `it` function, we are sending a GET request to the `/users` endpoint and asserting that the response status code is 200 and the response body is an array.

That's it! You have now written your first E2E test in NestJS. In the next section, we will explore how to test scenarios involving PostgreSQL and Redis.


#### Testing with PostgreSQL and Redis

In this section, we will provide a guide on how to write tests that interact with PostgreSQL and Redis. We will also explain the Cache Aside pattern and how to test it.

##### Understanding the Cache Aside Pattern

The Cache Aside pattern is a common caching strategy used in many applications. It involves storing data in a cache layer (in this case, Redis) and updating the cache whenever the underlying data in the primary data store (PostgreSQL) changes. This approach ensures that the cache remains consistent with the primary data store.

To implement the Cache Aside pattern, we need to model our data in PostgreSQL as the primary data store. Redis can be used as a cache layer to store frequently accessed data for faster retrieval. The data structure in Redis should match the structure in PostgreSQL to ensure efficient mapping and consistency.

##### Writing Tests for PostgreSQL and Redis

To write tests that interact with PostgreSQL and Redis, we need to create a test environment that allows us to mock the database and cache behavior. We can use Jest's mocking capabilities to achieve this.

Let's create a test for a scenario where we retrieve a user from the database and cache the result in Redis. We will use the `@nestjs/typeorm` package to interact with the database and the `redis` package to interact with the cache.

```typescript
import { Test, TestingModule } from '@nestjs/testing';
import * as request from 'upertest';
import { UsersController } from './users.controller';
import { UserRepository } from './user.repository';
import { RedisService } from './redis.service';

describe('UsersController', () => {
  let app: INestApplication;
  let userRepository: UserRepository;
  let redisService: RedisService;

  beforeEach(async () => {
    const moduleFixture: TestingModule = await Test.createTestingModule({
      controllers: [UsersController],
      providers: [UserRepository, RedisService],
    }).compile();

    app = moduleFixture.createNestApplication();
    await app.init();

    userRepository = moduleFixture.get<UserRepository>(UserRepository);
    redisService = moduleFixture.get<RedisService>(RedisService);
  });

  it('should retrieve a user from the database and cache the result in Redis', async () => {
    // Mock the database to return a user
    jest.spyOn(userRepository, 'findOne').mockResolvedValue({
      id: 1,
      name: 'John Doe',
    });

    // Mock the cache to return null
    jest.spyOn(redisService, 'get').mockResolvedValue(null);

    // Send a GET request to the /users/:id endpoint
    const response = await request(app.getHttpServer())
     .get('/users/1')
     .expect(200);

    // Assert that the user was retrieved from the database
    expect(userRepository.findOne).toHaveBeenCalledTimes(1);

    // Assert that the user was cached in Redis
    expect(redisService.set).toHaveBeenCalledTimes(1);
  });
});
```

In the example above, we are creating a test for the `UsersController` class. We are using the `beforeEach` function to create a new instance of the `NestApplication` class and initialize it before each test. We are also using Jest's mocking capabilities to mock the `UserRepository` and `RedisService` classes.

In the `it` function, we are sending a GET request to the `/users/:id` endpoint and asserting that the user was retrieved from the database and cached in Redis.

#### Running the E2E Tests

Now that we have written our E2E tests, it's time to run them and see the results. In this section, we will provide instructions on how to run the E2E tests and explain the output and how to interpret test results.

##### Running the Tests

To run the E2E tests, you can use the `jest` command in your terminal. Make sure you are in the root directory of your project and run the following command:

```sh
jest --config=jest.config.js
```

This command will run all the tests in your project, including the E2E tests. You can also run a specific test file or a specific test by using the `jest` command with the `--testNamePattern` option. For example:

```sh
jest --config=jest.config.js --testNamePattern="should retrieve a user successfully"
```

This command will run only the test with the name "should retrieve a user successfully".

##### Understanding the Output

When you run the E2E tests, you will see an output that indicates the test results. The output will show the number of tests that passed, failed, or skipped. For example:

```sh
 PASS  tests/e2e/user.test.ts (10.312s)
  User
    ✓ should retrieve a user successfully (123ms)
    ✓ should return a 404 error when retrieving a non-existent user (45ms)
    ✓ should cache the user in Redis (67ms)

Test Suites: 1 passed, 1 total
Tests:       3 passed, 3 total
Snapshots:   0 failed, 0 total
Time:        10.312s
Ran all test suites.
```

In this example, the output shows that all three tests passed, and the total test time was 10.312 seconds.

##### Interpreting Test Results

When interpreting test results, it's essential to understand what each test is testing and what the expected outcome is. For example, in the first test, "should retrieve a user successfully", we are testing that the application returns a user when a valid GET request is sent to the `/users/:id` endpoint. If the test passes, it means that the application is behaving as expected.

If a test fails, it means that the application is not behaving as expected. You can use the test output to identify the issue and debug the problem. For example, if the test "should return a 404 error when retrieving a non-existent user" fails, it may indicate that the application is not returning a 404 error when a non-existent user is requested.

By running the E2E tests and interpreting the test results, you can ensure that your application is behaving as expected and catch any issues early in the development process.


#### Best Practices for E2E Testing

Now that we have explored the importance of E2E testing, set up the testing environment, and written our first E2E test, it's essential to discuss best practices for writing and maintaining E2E tests in a NestJS application. These best practices will help you write effective and reliable E2E tests that ensure the reliability and robustness of your application.

1. **Keep Tests Independent**: Each test should be independent of others, and the order of test execution should not affect the test results. This ensures that tests can be run in parallel, and any issues with one test do not affect other tests.

2. **Use Descriptive Test Names**: Use descriptive test names that clearly indicate what the test is testing. This makes it easier to identify the purpose of each test and debug issues when tests fail.

3. **Test Only One Scenario per Test**: Each test should test only one scenario or functionality. This ensures that tests are focused and easy to maintain.

4. **Test for Failure**: In addition to testing for success, also test for failure scenarios. This ensures that your application handles errors and exceptions correctly.

5. **Keep Tests Up-to-Date**: As your application evolves, ensure that your tests are updated to reflect changes in functionality. This ensures that tests remain relevant and effective.

6. **Use a Consistent Testing Framework**: Use a consistent testing framework throughout your application. This makes it easier to write and maintain tests, and ensures that tests are consistent in style and structure.

7. **Test for Performance**: In addition to testing for functionality, also test for performance. This ensures that your application can handle a large number of requests and users.

By following these best practices, you can write effective and reliable E2E tests that ensure the reliability and robustness of your NestJS application. Remember to keep your tests independent, use descriptive test names, and test for failure scenarios. Additionally, keep your tests up-to-date, use a consistent testing framework, and test for performance.
