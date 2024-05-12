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
    overlay_image: /assets/images/nestjs-dd-interceptor/banner.jpeg
    overlay_filter: 0.5
    teaser: /assets/images/nestjs-dd-interceptor/banner.jpeg
title: "Mastering User Tracking with NestJS and DataDog"
tags:
    - Datadog
    - NestJS

---

This article provides a step-by-step guide on how to implement user tracking in NestJS applications using DataDog. It covers the basics of NestJS and DataDog, explains the concept of interceptors in NestJS, and shows how to create a custom UserTrackingInterceptor to track user behavior. The guide also covers how to apply and configure the interceptor, test its functionality, and view the tracking data in DataDog. By the end of this article, you will have a comprehensive understanding of user tracking and be able to implement it in your own NestJS applications.


### Introduction

In the dynamic landscape of modern web applications, user tracking stands out as an indispensable tool for comprehending user behavior, refining user experiences, and propelling business metrics forward. This comprehensive guide is designed to navigate you through the intricacies of user tracking, with a special emphasis on harnessing the power of NestJS and DataDog to monitor user interactions within your applications effectively.

NestJS, a progressive Node.js framework, offers a sturdy foundation for crafting scalable and maintainable server-side applications. In contrast, DataDog serves as an all-encompassing Application Performance Monitoring (APM) suite, empowering developers to scrutinize application performance metrics in real-time. The synergy between NestJS's server-side prowess and DataDog's analytical capabilities equips you with the means to extract actionable insights on user engagement, pinpoint areas ripe for enhancement, and ultimately elevate the user experience to new heights.

Throughout this blog post, we will explore:

- The pivotal role of user tracking in the ecosystem of modern web applications.
- An introductory overview of NestJS and DataDog.
- A detailed walkthrough for integrating user tracking into your NestJS applications, utilizing DataDog.
- The paramount importance of adhering to data privacy and security norms in user tracking implementations.
- Strategies for dissecting and leveraging user tracking data to inform and shape decision-making processes.

Whether you're an experienced developer or embarking on your initial foray into user tracking, this blog post aims to arm you with the essential insights and hands-on know-how to master user tracking with NestJS and DataDog. Let's embark on this journey into the realm of user tracking!


### Getting Started

Before we delve into the technical details, let's set the stage by briefly introducing **NestJS** and its advantages. We will also provide a quick overview of **DataDog** and its **Application Performance Monitoring (APM)** feature. To ensure you can follow along, we will guide you through setting up a basic NestJS project. If you're already familiar with these concepts, feel free to skip ahead.

#### NestJS

**NestJS** is a progressive Node.js framework for building efficient and scalable server-side applications. It is heavily inspired by Angular and utilizes TypeScript by default. Here are some of its core advantages:

- **Modular architecture:** NestJS structures applications into modules, fostering code reusability and streamlined maintenance.
- **Dependency injection:** NestJS's dependency injection mechanism simplifies the management of component interdependencies, facilitating the development of testable and maintainable code.
- **Robust HTTP support:** NestJS comes equipped with robust support for HTTP operations, streamlining the creation of web applications.
- **Extensible:** NestJS is designed to be highly extensible, allowing developers to use their own or third-party modules to add new capabilities.

To initiate a basic NestJS project, execute the following steps:

1. Globally install the NestJS CLI via npm:

   ```bash
   npm install -g @nestjs/cli
   ```

2. Generate a new NestJS project utilizing the CLI:

   ```bash
   nest new my-nest-app
   ```

3. Transition to the newly minted project directory:

   ```bash
   cd my-nest-app
   ```

4. Commence the NestJS application:

   ```bash
   npm run start
   ```

Launching the application on port 3000, you can now visit `http://localhost:3000` in your browser to witness the default greeting page.

#### DataDog

**DataDog** is a comprehensive monitoring service for cloud-scale applications, providing monitoring of servers, databases, tools, and services through a SaaS-based data analytics platform. Here's a more detailed look at its features:

- **Real-time monitoring:** DataDog provides real-time insights into your applications' performance, allowing you to observe how they behave under different conditions.
- **Error tracking:** With DataDog, you can track errors and exceptions, and get alerts so you can address issues before they affect users.
- **Distributed tracing:** DataDog offers end-to-end distributed tracing, giving you visibility across your entire infrastructure, from frontend to backend.
- **Custom metrics:** You can create custom metrics in DataDog to track the specific data that matters most to your business.

To integrate DataDog with your NestJS application, follow these steps:

1. Install the `dd-trace` package:

   ```bash
   npm install --save dd-trace
   ```

2. Initialize the tracer in your application's main file (usually `main.ts`):

   ```typescript
   import { NestFactory } from '@nestjs/core';
   import tracer from 'dd-trace';

   tracer.init(); // initialize your tracer here

   async function bootstrap() {
     const app = await NestFactory.create(AppModule);
     await app.listen(3000);
   }

   bootstrap();
   ```

3. Create a span for each request by implementing a custom interceptor:

   ```typescript
   import { Injectable, NestInterceptor, ExecutionContext, CallHandler } from '@nestjs/common';
   import { Observable } from 'rxjs';
   import { tap } from 'rxjs/operators';
   import tracer from 'dd-trace';

   @Injectable()
   export class TracingInterceptor implements NestInterceptor {
     intercept(context: ExecutionContext, next: CallHandler): Observable<any> {
       const span = tracer.startSpan('web.request');
       return next
         .handle()
         .pipe(
           tap(() => span.finish())
         );
     }
   }
   ```



### Understanding Interceptors in NestJS

In this section, we delve deeper into the concept of interceptors within the NestJS framework. Interceptors are a fundamental part of NestJS's robust architecture, offering the ability to execute code before and after the execution of a method in a controller or provider.

#### What are Interceptors?

**Interceptors** are NestJS components that tap into the execution flow of a request handling process. They are capable of:

- Intercepting incoming requests and outgoing responses.
- Transforming the result returned from a method.
- Extending the basic processing pipeline with custom behavior.
- Handling additional tasks like logging, auditing, or error handling.

#### How do Interceptors Work?

An interceptor is a class annotated with the `@Injectable()` decorator, which implements the `NestInterceptor` interface. This interface requires the implementation of the `intercept` method, which NestJS calls on every request handled by the method where the interceptor is applied.

The `intercept` method has the following signature:

```typescript
intercept(context: ExecutionContext, next: CallHandler): Observable<any>
```

Here's what each parameter represents:

- `context`: Provides details about the current request process, including the request object, response object, and handler details.
- `next`: A `CallHandler` that triggers the next interceptor in the chain or the route handler itself if there are no more interceptors.

#### Basic Examples of Using Interceptors

##### Logging Interceptor

A logging interceptor could look like this:

```typescript
@Injectable()
export class LoggingInterceptor implements NestInterceptor {
  intercept(context: ExecutionContext, next: CallHandler): Observable<any> {
    console.log('Before...');
    const now = Date.now();
    return next.handle().pipe(
      tap(() => console.log(`After... ${Date.now() - now}ms`))
    );
  }
}
```

##### Transforming Response Interceptor

To transform responses, you might have an interceptor that formats the response body:

```typescript
@Injectable()
export class TransformInterceptor implements NestInterceptor {
  intercept(context: ExecutionContext, next: CallHandler): Observable<any> {
    return next.handle().pipe(
      map(data => ({ data, timestamp: Date.now() }))
    );
  }
}
```

#### Applying Interceptors

Interceptors can be applied globally or to specific routes using decorators:

- Globally: `app.useGlobalInterceptors(new LoggingInterceptor());`
- On a route: `@UseInterceptors(LoggingInterceptor)`

#### Conclusion

Interceptors offer a powerful way to interact with the request-response cycle in NestJS. They provide a high degree of flexibility and control, allowing developers to implement cross-cutting concerns efficiently.

In the following section, we will guide you through creating a custom interceptor to monitor user activities.



### Setting Up DataDog in Your NestJS Application

Integrating DataDog into your NestJS application can significantly enhance your ability to monitor and track user behavior and application performance. Below, we delve deeper into the steps required to set up DataDog, focusing on the installation of the `dd-trace` package, initializing the tracer, and understanding the concept of spans.

#### Installing the `dd-trace` Package

The `dd-trace` package is essential for tracing operations within your NestJS application and sending the traced data to DataDog. To install this package, run the following command in your terminal:

```bash
npm install --save dd-trace
```

This command will add the `dd-trace` package to your project's dependencies, ensuring that the tracing functionality is available for use.

#### Initializing the Tracer

The tracer is a crucial component that creates and manages spans, which are representations of the execution of a request. To initialize the tracer, insert the following code into your application's main file (typically `main.ts`):

```typescript
import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';
import tracer from 'dd-trace';

// Initialize the tracer before starting the Nest application
tracer.init();

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  // Additional configuration can be done here
  await app.listen(3000);
}

bootstrap();
```

By calling `tracer.init()`, you activate the tracer, which will start creating spans for incoming requests.

#### Understanding Spans in DataDog

In DataDog, spans are the core building blocks of tracing. A span represents an individual operation or task within a larger request. The hierarchical organization of spans, with child spans nested under parent spans, mirrors the execution flow of the application.

A root span is generated when a request is received. Subsequent child spans are then created for each distinct operation or task executed during that request. For instance, a root span could be associated with an incoming web request, while child spans could correspond to database queries, external API calls, or other internal operations.

Each span captures critical information about its respective operation, including:

- **Operation Name**: A descriptive label for the operation.
- **Duration**: The time taken to complete the operation.
- **Error Details**: Any errors encountered during the operation.

DataDog utilizes this span data to provide valuable insights into your application's performance and user behavior patterns.

In the upcoming section, we will explore how to implement a custom interceptor in NestJS to facilitate the creation of spans and tracking of user activities within DataDog.



### Creating the UserTrackingInterceptor

In this section, we delve into the creation of a custom interceptor named `UserTrackingInterceptor`. This interceptor's role is pivotal for intercepting incoming requests, extracting user-related information, and appending this data as metadata to the spans generated by DataDog. This process is instrumental in tracking user activities and scrutinizing their influence on the application's performance metrics.

#### Setting Up the Interceptor

The inception of the `UserTrackingInterceptor` involves the following steps:

1. Initiate by creating a new file within your project's `src` directory, named `user-tracking.interceptor.ts`.
2. Proceed to import the requisite dependencies:

```typescript
import { Injectable, NestInterceptor, ExecutionContext, CallHandler } from '@nestjs/common';
import { Observable } from 'rxjs';
import { tap } from 'rxjs/operators';
import tracer from 'dd-trace';
```

3. Craft the `UserTrackingInterceptor` class:

```typescript
@Injectable()
export class UserTrackingInterceptor implements NestInterceptor {
  intercept(context: ExecutionContext, next: CallHandler): Observable<any> {
    // Retrieve user-related information from the request
    const request = context.switchToHttp().getRequest();
    const user = request.user; // Presuming the presence of a user object within the request

    // Initiate a span for the request
    const span = tracer.startSpan('web.request');

    // Incorporate user-related metadata into the span
    span.addTags({
      'user.id': user.id,
      'user.name': user.name,
      'user.email': user.email,
    });

    return next.handle().pipe(
      tap(() => span.finish())
    );
  }
}
```

In the above snippet, we:

- Extract user-centric information from the inbound request.
- Initiate a span for the request utilizing `tracer.startSpan()`.
- Enrich the span with user-centric metadata via `span.addTags()`.
- Invoke `next.handle()` to perpetuate the request handling sequence.
- Employ the `tap()` operator to conclude the span subsequent to the request's processing.

#### Applying the Interceptor

Post-creation, the `UserTrackingInterceptor` can be integrated into your routes to facilitate user tracking. The interceptor can be applied in two distinct manners:

- **Globally**: For universal route application, insert the following directive in your `main.ts` file:

```typescript
app.useGlobalInterceptors(new UserTrackingInterceptor());
```

- **Specifically**: For targeted route application, utilize the `@UseInterceptors()` decorator on the controller or route handler:

```typescript
@Controller('users')
@UseInterceptors(UserTrackingInterceptor)
export class UsersController {
  // Controller methods go here...
}
```

The application of the interceptor guarantees the capture and addition of user-related information to the spans for each request that aligns with the specified parameters.

#### Conclusion

This section has been dedicated to the construction of a bespoke `UserTrackingInterceptor` that extracts user information from incoming requests and integrates it as metadata within the spans crafted by DataDog. The deployment of this interceptor enables the tracking of user activities, thereby offering profound insights into their ramifications on the application's operational efficacy. The subsequent section will explore the configuration nuances of the interceptor to align with your unique application demands.



### Applying the UserTrackingInterceptor

After creating the `UserTrackingInterceptor`, it's essential to integrate it within your NestJS application to monitor user activities. This section delves into the methods of applying the interceptor both globally and to specific parts of your application.

#### Applying the Interceptor Globally

For a broad application of the interceptor that encompasses all incoming requests, you can register it globally. This is done in the `main.ts` file of your NestJS application. Here's how you can achieve this:

```typescript
import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';
import { UserTrackingInterceptor } from './user-tracking.interceptor';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  // Register the interceptor globally
  app.useGlobalInterceptors(new UserTrackingInterceptor());
  await app.listen(3000);
}

bootstrap();
```

By invoking `app.useGlobalInterceptors()`, the `UserTrackingInterceptor` will be active for every route, providing a comprehensive overview of user interactions.

#### Applying the Interceptor to Specific Controllers or Route Handlers

If you require more precision in tracking, you can bind the interceptor to particular controllers or even individual route handlers. This selective approach is facilitated by the `@UseInterceptors()` decorator.

##### To a Controller

When you want to track user behavior within a specific controller, apply the interceptor directly to the controller class:

```typescript
import { Controller, UseInterceptors } from '@nestjs/common';
import { UserTrackingInterceptor } from './user-tracking.interceptor';

@Controller('users')
@UseInterceptors(UserTrackingInterceptor)
export class UsersController {
  // Your controller methods will be tracked here...
}
```

##### To a Route Handler

For an even more granular level of tracking, you can attach the interceptor to specific route handlers within a controller:

```typescript
import { Controller, Get, UseInterceptors } from '@nestjs/common';
import { UserTrackingInterceptor } from './user-tracking.interceptor';

@Controller('users')
export class UsersController {
  @Get()
  @UseInterceptors(UserTrackingInterceptor)
  findAll() {
    // This particular route will be monitored...
  }
}
```

This method allows you to selectively monitor certain paths, which can be useful for sensitive endpoints or areas of high user interaction.

### Configuring the UserTrackingInterceptor

To customize the `UserTrackingInterceptor` for your application, you'll need to pass configuration options to it. This section delves into how to provide these options, modify the interceptor to utilize them, and includes code snippets to guide you through the implementation.

#### Passing Configuration Options

Configuration options are passed to the `UserTrackingInterceptor` using the `@Injectable()` decorator. This is done by defining a constructor that takes a configuration object. Here's an example:

```typescript
import { Injectable } from '@nestjs/common';
import { UserTrackingInterceptorConfig } from './user-tracking-config.interface';

@Injectable()
export class UserTrackingInterceptor {
  constructor(private readonly config: UserTrackingInterceptorConfig) {
    // The config property is now available throughout the interceptor
  }

  // Additional methods and logic...
}
```

In this code snippet, the `UserTrackingInterceptor` is equipped with a constructor that accepts a `UserTrackingInterceptorConfig` object. This allows the interceptor to access the provided configuration options through the `config` property.

#### Modifying the Interceptor to Use the Configuration

After injecting the configuration options, the interceptor's behavior can be modified accordingly. For instance, you might want to specify which user details should be tracked. Here's how you could implement this:

```typescript
import { Injectable, ExecutionContext, CallHandler } from '@nestjs/common';
import { Observable } from 'rxjs';
import { tap } from 'rxjs/operators';
import { UserTrackingInterceptorConfig } from './user-tracking-config.interface';
import { Tracer } from 'opentracing';

@Injectable()
export class UserTrackingInterceptor {
  constructor(private readonly config: UserTrackingInterceptorConfig) {}

  intercept(context: ExecutionContext, next: CallHandler): Observable<any> {
    const request = context.switchToHttp().getRequest();
    const user = request.user; // Assuming user object is present in the request

    const span = new Tracer().startSpan('web.request');

    // Add basic user information to the span
    span.addTags({
      'user.id': user.id,
      'user.name': user.name,
      'user.email': user.email,
    });

    // Conditionally add the IP address based on the configuration
    if (this.config.trackIpAddress) {
      span.addTags({ 'user.ip_address': request.ip });
    }

    // Close the span when the request handling is complete
    return next.handle().pipe(tap(() => span.finish()));
  }
}
```

This example demonstrates how the `UserTrackingInterceptor` uses the `trackIpAddress` from the configuration to decide if the user's IP address should be included in the span.


### Testing Your UserTrackingInterceptor

Testing is crucial to ensure that your `UserTrackingInterceptor` is functioning as expected. Proper testing verifies that the interceptor is invoked for each request and that it behaves correctly, capturing and logging user activity. This section will guide you through the process of writing tests for your interceptor and viewing the tracking data in DataDog.

#### Writing Tests

To thoroughly test your `UserTrackingInterceptor`, consider the following detailed steps:

1. **Initialize Your Testing Environment**
   - Create a new test file named `user-tracking.interceptor.spec.ts`.
   - Set up your testing module by importing the `UserTrackingInterceptor` and any necessary testing utilities from NestJS.

2. **Simulate a Request**
   - Within your test suite, simulate an HTTP request to trigger the interceptor.
   - Use the `ExecutionContext` to mock the request object, including any user data.

3. **Assert Interceptor Invocation**
   - Write an assertion to check that the interceptor is called when a request is made.
   - Utilize Jest's `toHaveBeenCalled` or similar assertion methods to verify the call.

4. **Mock the Tracer**
   - Create a mock for the `Tracer` class from `opentracing`.
   - Ensure that the `startSpan` method is called with the correct operation name, such as 'web.request'.

5. **Verify Metadata Attachment**
   - Confirm that user-related metadata is correctly attached to the span.
   - Check for the presence of user identifiers and other relevant information.

6. **Handle Asynchronous Operations**
   - If your interceptor performs asynchronous operations, use `async/await` or return an `Observable` to handle them in your tests.

7. **Clean Up After Tests**
   - After each test, clean up any mocks or spies to prevent cross-test contamination.

#### Example Test Case

Here's an enhanced example of a test case with additional comments for clarity:

```typescript
// Import testing utilities and the interceptor
import { Test, TestingModule } from '@nestjs/testing';
import { UserTrackingInterceptor } from './user-tracking.interceptor';
import { ExecutionContext, CallHandler } from '@nestjs/common';
import { Observable, of } from 'rxjs';
import { Tracer } from 'opentracing';

// Describe the test suite for the UserTrackingInterceptor
describe('UserTrackingInterceptor', () => {
  let interceptor: UserTrackingInterceptor;
  let tracer: Tracer;

  // Set up the testing module and mock objects before each test
  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      providers: [UserTrackingInterceptor],
    }).compile();

    interceptor = module.get<UserTrackingInterceptor>(UserTrackingInterceptor);
    tracer = new Tracer();
  });

  // Test that the interceptor is called on a request
  it('should be called', () => {
    // Mock the execution context with user data
    const context = {
      switchToHttp: () => ({
        getRequest: () => ({
          user: {
            id: 1,
            name: 'John Doe',
            email: 'john.doe@example.com',
          },
        }),
      }),
    } as ExecutionContext;

    const next: CallHandler = {
      handle: () => of({}),
    };

    // Call the interceptor and assert it has been invoked
    interceptor.intercept(context, next);
    expect(interceptor).toHaveBeenCalled();
  });

  // Additional test cases would follow...
});
```

#### Viewing Tracking Data in DataDog

After implementing and running your tests, you can view the tracking data in DataDog to ensure that user activities are being captured:

1. **Access DataDog Dashboard**
   - Log in to your DataDog account and navigate to the APM (Application Performance Monitoring) section.

2. **Locate Traces**
   - Find the traces generated by your application and filter them by the operation name used in your interceptor.

3. **Inspect Span Details**
   - Click on a specific trace to view the span details, including any user-related metadata.

4. **Analyze User Activity**
   - Use the DataDog tools to analyze the frequency and patterns of user activity within your application.

By following these steps, you can confidently verify that your `UserTrackingInterceptor` is capturing the necessary user data and that it's being logged correctly in DataDog.



### Conclusion

In this comprehensive guide, we've ventured deep into the intricacies of user tracking within modern web applications, utilizing the robust capabilities of NestJS and DataDog. We've underscored the pivotal role of user tracking in gleaning insights into user behavior, which is instrumental in refining user experiences and bolstering application performance.

**Key Takeaways:**

- **User Tracking Fundamentals:** We've demystified the core principles of user tracking, highlighting its indispensable benefits in decoding user interactions, tailoring user experiences, and driving performance enhancements.

- **NestJS & DataDog Overview:** A thorough exploration of NestJS, the forward-thinking Node.js framework, paired with DataDog's exhaustive Application Performance Monitoring (APM) solutions, has been presented, offering a solid foundation for implementing sophisticated tracking mechanisms.

- **Creating `UserTrackingInterceptor`:** Step-by-step guidance has been provided to craft a custom `UserTrackingInterceptor` within NestJS. This interceptor is pivotal in capturing user-centric data and integrating it with the spans generated by DataDog's APM tools.

- **Interceptor Application Strategies:** We've outlined strategic approaches to deploy the interceptor across your application globally or target specific routes, ensuring comprehensive tracking of user activities aligned with your operational objectives.

- **Interceptor Configuration Techniques:** Customization techniques for the interceptor have been detailed, enabling you to tailor the user data captured and logged, thus providing flexibility in monitoring user interactions.

- **Testing Methods:** We've introduced methodologies to rigorously test the interceptor, confirming its operational efficacy and guaranteeing it performs as anticipated.

- **DataDog Tracking Data Analysis:** Instructions have been provided to navigate DataDog's interface, allowing you to scrutinize the tracking data, uncover user activity trends, and extract actionable insights.

We urge you to harness the knowledge and methodologies expounded in this guide to amplify your user tracking prowess. Delve into additional resources, such as the comprehensive documentation of NestJS and DataDog, to broaden your understanding and fine-tune your tracking implementations.

By capitalizing on the synergy of NestJS and DataDog, you're equipped to unravel the nuances of user behavior within your applications. This empowers you to make data-driven decisions, optimize user journeys, and catalyze business growth.
