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
    overlay_image: /assets/images/testcontainers-nodejs/banner.jpeg
    overlay_filter: 0.5
    teaser: /assets/images/testcontainers-nodejs/banner.jpeg
title: "A Comprehensive Guide to Testcontainers for Node.js"
tags:
    - Testcontainers
    - Node.js

---

Testcontainers is a valuable tool for Node.js developers to write reliable and maintainable tests. It provides a consistent and isolated testing environment, enabling developers to identify and fix issues early on. With its advanced features and growing popularity, Testcontainers for Node.js is expected to continue playing a significant role in the future of software testing.


### Introduction

Testcontainers is a Node.js library that supports tests, providing lightweight, throwaway instances of common databases, Selenium web browsers, or anything else that can run in a Docker container. It enables developers to write reliable and maintainable tests by providing a consistent and isolated environment for testing.

Testcontainers is a powerful tool that can be used to improve the quality and reliability of your Node.js tests. By providing isolated, consistent, and fast testing environments, Testcontainers can help you to write better tests that are less likely to fail.


## Getting Started with Testcontainers for Node.js

Testcontainers is a library that allows you to run and test applications that depend on external services, such as databases, message brokers, or web servers, using Docker containers. Testcontainers simplifies the setup and teardown of these services, and provides a consistent and portable way to interact with them.

### Installing Testcontainers for Node.js

To get started with Testcontainers for Node.js, you need to install the `@testcontainers/postgresql` package, which provides a convenient wrapper for creating and managing PostgreSQL containers. You can install it using npm or yarn:

```bash
npm install --save-dev @testcontainers/postgresql
```

or

```bash
yarn add --dev @testcontainers/postgresql
```

### Creating a Testcontainers configuration

Once installed, you can create a basic Testcontainers configuration by importing the `PostgreSqlContainer` class and creating an instance of it. You can also specify some options for the container, such as the database name, username, password, or port. For example, the following code creates a PostgreSQL container with the database name `my_database`, the username `postgres`, and the password `secret`:

```js
const { PostgreSqlContainer } = require('@testcontainers/postgresql');

const postgresContainer = new PostgreSqlContainer()
  .withDatabase('my_database')
  .withUsername('postgres')
  .withPassword('secret');
```

### Running a simple test with Testcontainers

To run a simple test with Testcontainers, you need to start the container before the test, and stop it after the test. You can use the `beforeAll` and `afterAll` hooks provided by your testing framework, such as Jest or Mocha, to do this. You also need to create a database client using the connection string provided by the container, and use it to execute queries and assertions. For example, the following code uses Jest and the `pg` module to test that the container can connect to the database and execute a simple query:

```js
const { Client } = require('pg');

describe('PostgreSQL container', () => {
  let postgresContainer;
  let client;

  beforeAll(async () => {
    // Start the container
    postgresContainer = await postgresContainer.start();

    // Create the database client
    client = new Client({
      connectionString: postgresContainer.getConnectionString(),
    });

    // Connect to the database
    await client.connect();
  });

  afterAll(async () => {
    // Disconnect from the database
    await client.end();

    // Stop the container
    await postgresContainer.stop();
  });

  test('should connect to the database', async () => {
    // Execute a simple query
    const res = await client.query('SELECT 1');

    // Assert that the result is correct
    expect(res.rows[0][0]).toBe(1);
  });
});
```

### Debugging Testcontainers tests

To debug Testcontainers tests, you can set the `DEBUG` environment variable to `testcontainers*`. This will print out detailed logs about what Testcontainers is doing, such as creating, starting, stopping, or inspecting containers. For example, you can run your tests with the following command:

```bash
DEBUG=testcontainers* npm test
```

or

```bash
DEBUG=testcontainers* yarn test
```

You can also use the `--inspect-container` flag to inspect the container that Testcontainers is using. This will open a terminal session inside the container, where you can run commands or explore the file system. For example, you can run the following command to inspect the PostgreSQL container:

```bash
npx testcontainers --inspect-container postgres
```

or

```bash
yarn testcontainers --inspect-container postgres
```



Hello, this is Copilot. I am here to help you with your writing task. 😊

I have read your phase and I think it is well-written and informative. You have covered the main features of Testcontainers for Node.js and provided clear examples of how to use them. I have only a few suggestions to improve your phase:

- You can add a brief introduction to Testcontainers for Node.js at the beginning of your phase, to provide some context and motivation for the reader. For example, you can mention what Testcontainers is, what problem it solves, and how it works.
- You can add some transitions between the paragraphs, to make the flow of your phase smoother and more coherent. For example, you can use words like "Another feature", "In addition", "Furthermore", or "Finally" to introduce each feature.
- You can add some references or links to the official documentation of Testcontainers for Node.js, to provide more details and resources for the reader. For example, you can add a link to the GitHub repository or the npm package of Testcontainers for Node.js.

Here is how your phase would look like after applying these suggestions:

### Advanced Features of Testcontainers for Node.js

[Testcontainers](https://www.npmjs.com/package/testcontainers) is a Node.js library that allows you to run Docker containers in your tests. It simplifies the setup and teardown of testing environments, and enables you to test your code against real services and databases. Testcontainers works by creating and managing containers using the Docker API, and exposing their ports and logs to your test code.

Testcontainers for Node.js offers advanced features that provide greater flexibility and control over the testing environment. These features include:

**Adding Custom Labels to Containers**

Another feature of Testcontainers for Node.js is the ability to add custom labels to containers using the `withLabel` method. This is useful for organizing and identifying containers, especially when working with multiple containers in a complex test setup. For example, you can add a label to a container to indicate its purpose or the test case it is associated with.

```typescript
const container = new GenericContainer('postgres:latest')
  .withLabel('test-type', 'integration')
  .withLabel('test-case', 'user-management');
```

**Setting the Image Pull Policy**

In addition, Testcontainers for Node.js allows you to set the Image Pull Policy for the containers. The Image Pull Policy determines how Testcontainers handles the pulling of container images. By default, Testcontainers will always pull the latest image. However, you can use the `withImagePullPolicy` method to specify a different policy, such as `IfNotPresent` or `Always`.

```typescript
const container = new GenericContainer('postgres:latest')
  .withImagePullPolicy(ImagePullPolicy.IfNotPresent);
```

**Customizing the Container Configuration**

Furthermore, Testcontainers for Node.js enables you to customize the container configuration using the `withCreateContainerCmdModifier` method. This method takes a `CreateContainerCmdModifier` object as an argument, which allows you to modify the `CreateContainerCmd` object used to create the container. For example, you can use this method to change the container hostname or memory limits.

```typescript
const container = new GenericContainer('postgres:latest')
  .withCreateContainerCmdModifier(cmd => cmd.hostname('my-postgres'));
```

**Starting Multiple Containers in Parallel**

Finally, Testcontainers for Node.js supports starting multiple containers in parallel using the `Startables.deepStart()` method. This is useful when you need to test interactions between multiple containers, such as a database and a web application.

```typescript
const dbContainer = new GenericContainer('postgres:latest');
const appContainer = new GenericContainer('my-app:latest');

await Startables.deepStart([dbContainer, appContainer]);
```

These advanced features provide powerful capabilities for customizing and managing containers in Testcontainers for Node.js. By leveraging these features, you can create more sophisticated and realistic testing environments that better reflect the production environment.

For more information and examples, you can visit the [GitHub repository](https://github.com/testcontainers/testcontainers-node) or the [official documentation](https://node.testcontainers.org/) of Testcontainers for Node.js.


### Conclusion

Testcontainers for Node.js is a powerful and versatile tool that can help you to write better tests and improve the quality of your code. It is actively developed and maintained, and has a bright future ahead of it. As Testcontainers for Node.js continues to evolve, it will become even more powerful and easier to use, making it an essential tool for any Node.js developer who cares about testing.
