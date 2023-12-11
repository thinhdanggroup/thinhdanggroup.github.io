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
    overlay_image: /assets/images/health-check-api/banner.jpeg
    overlay_filter: 0.5
    teaser: /assets/images/health-check-api/banner.jpeg
title: "A Deep Dive into Proper Health Check API Implementation"
tags:
    - Serverless

---

In this blog post, we will take a deep dive into the world of health check APIs. We will kick off by introducing the concept of health check APIs and their importance in software development. From there, we will delve into the basic concepts of health check APIs, including their definition and how they differ from other types of APIs. We will then explain how health check APIs work, focusing on the process and the role of endpoints. Moving forward, we will explore the real-world use cases of health check APIs and the benefits they bring. In the next section, we will share some best practices for implementing health check APIs correctly. But it's not all roses - we will also discuss common pitfalls in health check API implementation and how to avoid them. Lastly, we will provide example codes of health check APIs and explain how they work. So, whether you are a beginner or an experienced developer, this blog post will equip you with the knowledge and skills you need to implement health check APIs effectively and efficiently.

### Introduction

Welcome to our deep dive into health check APIs. In this blog, we will explore the importance of these APIs, how they function, and how they can be effectively implemented to avoid common pitfalls. 

Health check APIs are an essential part of modern software development. They serve as a critical tool for monitoring the health of applications and infrastructure, providing valuable insights that help developers maintain the stability and availability of their software. 

In the world of software development, the health of an application or service is of paramount importance. It is not just about whether the software is functioning, but also about how well it is performing. This is where health check APIs come into play.

A health check API is a specialized API that provides information on the health and status of a server or application. It is designed to monitor the availability and detect any inconsistencies or issues. In essence, health check APIs act as a diagnostic tool, allowing developers to proactively identify problems and take necessary actions to resolve them.

The use of health check APIs can significantly enhance the reliability and stability of software. They provide a mechanism to monitor the health of the server and its components, enabling developers to detect any inconsistencies or issues in the software and take necessary actions to resolve them. This helps in ensuring the availability, stability, and smooth functioning of the software.

In the following sections, we will delve deeper into the basic concepts of health check APIs, how they work, and their use cases. We will also provide you with best practices for implementing health check APIs and common mistakes to avoid. Stay with us as we navigate through the world of health check APIs.



### Basic Concepts of Health Check APIs

Before we proceed, let's get a clear understanding of what a health check API is and how it differs from other types of APIs.

#### What is a Health Check API?

A health check API is a specific type of API designed to provide information on the health and status of a server or application. It serves as a diagnostic tool that allows developers to monitor the availability and status of various components of the software, such as databases and services. 

In other words, a health check API is like a doctor for your software, constantly checking its vital signs and alerting you to any potential problems. By using the health check API, developers can proactively identify issues and take necessary actions to resolve them, thereby ensuring the availability and stability of the software.

#### How Does a Health Check API Differ From Other Types of APIs?

The main difference between a health check API and other types of APIs lies in their purpose. While the primary function of most APIs is to enable interaction and data exchange between different applications or services, a health check API is specifically designed to monitor the health and status of a server or application.

For instance, a REST API, which is a common type of API, allows developers to perform operations, retrieve data, or integrate functionalities from external services. On the other hand, a health check API, while it may also use RESTful principles, is primarily focused on providing information about the health and status of the server or application.

In conclusion, while all APIs serve as a communication bridge between different software components, a health check API is unique in its focus on monitoring and maintaining the health and performance of the software. In the next section, we'll delve deeper into the working process of health check APIs.



### How Health Check APIs Work

To understand how Health Check APIs function, we first need to comprehend the underlying process. The process of a health check API generally involves a series of checks or tests that are performed to determine the health or status of a server or application.

These checks can include a variety of tests, such as verifying the availability of a database, checking the response time of an API endpoint, or monitoring the utilization of server resources. The results of these checks are then returned by the health check API in a standardized format, typically JSON, which provides a clear and concise overview of the health status.

The process of a health check API can be summarized in the following steps:

1. **Request**: A client (which could be a developer, a monitoring system, or another service) sends a request to the health check API endpoint.

2. **Checks**: The health check API performs a series of checks or tests to assess the health of the server or application. These checks can vary depending on the specific requirements of the application.

3. **Response**: The health check API returns a response that includes the results of the health checks. This response provides a snapshot of the health of the server or application at that particular moment.

4. **Analysis**: The client analyzes the response from the health check API to determine the health status and take appropriate actions if necessary.

#### Role of Endpoints in Health Check APIs

In the context of health check APIs, an endpoint refers to a specific URL where the API can be accessed. Each endpoint corresponds to a specific function or resource in the server or application.

For instance, a health check API might have an endpoint such as `/healthz` that returns the overall health status of the server. Other endpoints might return more specific health information, such as `/healthz/db` for database health or `/healthz/api` for API health.

Endpoints play a crucial role in health check APIs as they provide a way for clients to access the health information. By making a request to a specific endpoint, clients can retrieve the health status of a particular component or functionality of the server or application.

In conclusion, health check APIs function by performing a series of checks or tests and returning the results through specific endpoints. These APIs provide a valuable tool for monitoring the health of servers and applications, enabling developers to proactively identify and resolve issues.

In the next section, we will look at some real-world examples of where health check APIs are used and discuss the benefits of using them.



### Use Cases of Health Check APIs

As we've seen, health check APIs play a crucial role in software development, providing valuable insights into the health and status of servers and applications. But where exactly are these APIs used in the real world, and what benefits do they bring? Let's explore some examples.

#### Real-World Examples of Health Check APIs

Health check APIs are used in a wide range of scenarios across various industries. Here are a few examples:

1. **Container Orchestrators and API Load Balancers**: In the world of containerized applications and microservices, health check APIs are used by container orchestrators and API load balancers to manage and distribute traffic efficiently. By monitoring the health of individual services, these systems can make informed decisions about routing traffic, scaling services, and handling failures.

2. **Server Resource Monitoring**: Health check APIs can be used to monitor server resources such as memory and disk usage. This information can be crucial for optimizing performance, managing resources, and planning capacity.

3. **Dependency Monitoring**: Many applications depend on external services or APIs. Health check APIs can be used to monitor the availability and functioning of these dependencies. This can help in identifying and resolving issues with dependencies, ensuring smooth operation of the application.

#### Benefits of Using Health Check APIs

The use of health check APIs brings several benefits:

1. **Early Problem Detection**: Health check APIs can help in identifying issues with the API before they become more significant problems. By monitoring the health of the API, problems can be identified and addressed early, preventing them from impacting the overall application.

2. **Improved Performance**: By monitoring the health and performance of the API, optimizations can be made to enhance its overall performance. Health check APIs provide metrics and insights into the health of the application, enabling better resource utilization and load balancing.

3. **Reliability**: Health check APIs ensure that the API is running smoothly and can handle incoming requests. This can help in maintaining the reliability and stability of the software system.

4. **Dependency Monitoring**: Health check APIs can verify the availability and functioning of dependencies, ensuring smooth operation of the API. This can be particularly useful in microservice architectures, where an application may depend on multiple external services.

Health check APIs are a powerful tool for monitoring the health and performance of servers and applications. They are used in a wide range of scenarios and bring several benefits, including early problem detection, improved performance, reliability, and dependency monitoring.

In the next section, we will provide you with best practices for implementing health check APIs and common mistakes to avoid.



### Best Practices for Implementing Health Check APIs

Implementing health check APIs is a critical aspect of software development. However, without proper implementation, these APIs can fail to provide accurate health status, leading to undetected issues and system failures. So, let's delve into some best practices to ensure an effective implementation of health check APIs.

#### Use Liveness Checks

Liveness checks are a type of health check that tests basic connectivity and server process presence. They help to determine if an application or service is 'up' and ready to accept requests. Implementing liveness checks as part of your health check API can provide a quick and simple way to monitor the availability of your application or service.

#### Implement Local Health Checks

Local health checks verify that the application is functioning properly. They are designed to test the internal components of the application, such as databases and internal services. Implementing local health checks can provide a more detailed view of the health of your application, allowing you to identify and resolve issues at the component level.

#### Perform Dependency Health Checks

Dependency health checks inspect the ability of an application to interact with its adjacent systems. These checks are crucial for applications that depend on external services or APIs. By performing dependency health checks, you can monitor the availability and functioning of these dependencies and take proactive measures to handle any issues.

#### Prioritize Health Checks Over Regular Work

Health checks should be prioritized over regular work, especially in overload conditions. This is because health checks provide vital information about the health of the system, which is essential for maintaining the availability and performance of the application. By prioritizing health checks, you can ensure that they are performed regularly and reliably, even when the system is under heavy load.

#### Balance Dependency Health Checks With the Scope of Impact

While dependency health checks are important, they should be balanced with the scope of impact to avoid cascading failures. This means that you should carefully consider the potential impact of a dependency failure on your application and adjust the frequency and depth of health checks accordingly.

#### Implement Fail-Open Behavior in Load Balancers

A fail-open behavior in load balancers ensures that they continue serving traffic even when all servers fail health checks. This can help to maintain the availability of your application, even in the event of a system-wide failure.

#### Regularly Monitor and Update the Health Check API

Health check APIs should be regularly monitored and updated based on changing system requirements and performance data. This can help to ensure that the API remains effective and relevant, providing accurate and up-to-date health information.

By following these best practices, you can implement a robust and effective health check API that provides accurate and timely information about the health of your application or service.

In the next section, we will discuss some common pitfalls to avoid when implementing health check APIs.



### Common Mistakes to Avoid When Implementing Health Check APIs

While implementing health check APIs can greatly enhance the reliability and performance of your software, there are several common pitfalls that developers often fall into. By being aware of these potential issues, you can take steps to avoid them and ensure that your health check APIs are as effective as possible.

#### Not Using Health Check APIs Correctly or At All

One of the most common mistakes is not using health check APIs correctly, or not using them at all. Health check APIs are a powerful tool for monitoring the health of your application and identifying potential issues before they become serious problems. If you're not using health check APIs in your application, or if you're not using them correctly, you're missing out on a valuable opportunity to improve the reliability and performance of your software.

#### Having Insufficient Information Returned

Another common pitfall is having a health check API that returns insufficient information. A good health check API should provide a detailed snapshot of the health of your application, including the status of individual components and dependencies. If your health check API only returns a simple "pass" or "fail" status, it may not provide enough information to diagnose and resolve issues effectively.

#### Not Automating Health Checks

Health checks should be performed regularly to ensure that your application is functioning properly. However, manually performing health checks can be time-consuming and error-prone. One common mistake is not automating health checks, which can lead to missed or delayed detection of issues. By automating health checks, you can ensure that they are performed consistently and reliably, allowing you to identify and address issues promptly.

#### Not Disabling Cache

Caching can improve the performance of your application by storing data in a cache for quick retrieval. However, when it comes to health check APIs, caching can actually be a disadvantage. If your health check API is cached, it may return outdated information, which can lead to inaccurate health status. It's important to disable caching for your health check API to ensure that it always returns the most up-to-date information.

#### Not Considering Protecting Your Health Check Endpoint

Health check APIs often provide sensitive information about the internal workings of your application. If this information falls into the wrong hands, it could be used to exploit vulnerabilities in your application. It's important to protect your health check endpoint to prevent unauthorized access. This can be done by implementing authentication and authorization mechanisms, and by limiting access to the health check endpoint to trusted systems and users.

#### Not Using JSON Response

Finally, it's important to use a standardized response format for your health check API. JSON is a widely used format that is easy to read and parse, making it an ideal choice for health check API responses. If you're not using JSON for your health check API responses, you may encounter compatibility issues with other systems or tools.

In conclusion, while implementing health check APIs can greatly enhance the reliability and performance of your software, it's important to avoid these common pitfalls. By using health check APIs correctly, providing sufficient information, automating health checks, disabling cache, protecting your health check endpoint, and using a standardized response format, you can ensure that your health check APIs are as effective as possible.

In the next section, we will provide some code examples of health check APIs.



### Example Codes of Health Check APIs

Now that we've covered the importance, use cases, and best practices of health check APIs, let's look at some example codes. These code snippets will demonstrate how to implement a health check API and provide explanations to understand them better.

#### Example health check API

The following code snippet is a health check API response in JSON format. This response includes information about the status of the service, version, release ID, notes, output, service ID, description, checks, and links. The 'checks' object provides detailed health statuses of additional downstream systems and endpoints. Each check has various properties such as component ID, component type, observed value, observed unit, status, affected endpoints, time, output, and links. The 'links' object contains link relations and URIs for external links related to the health of the endpoint.

```java
GET /health HTTP/1.1
Host: example.org
Accept: application/health+json

HTTP/1.1 200 OK
Content-Type: application/health+json
Cache-Control: max-age=3600
Connection: close

{
  "status": "pass",
  "version": "1",
  "releaseId": "1.2.2",
  "notes": [""],
  "output": "",
  "serviceId": "f03e522f-1f44-4062-9b55-9587f91c9c41",
  "description": "health of authz service",
  "checks": {
    "cassandra:responseTime": [
      {
        "componentId": "dfd6cf2b-1b6e-4412-a0b8-f6f7797a60d2",
        "componentType": "datastore",
        "observedValue": 250,
        "observedUnit": "ms",
        "status": "pass",
        "affectedEndpoints" : [
          "/users/{userId}",
          "/customers/{customerId}/status",
          "/shopping/{anything}"
        ],
        "time": "2018-01-17T03:36:48Z",
        "output": ""
      }
    ],
    "cassandra:connections": [
      {
        "componentId": "dfd6cf2b-1b6e-4412-a0b8-f6f7797a60d2",
        "componentType": "datastore",
        "observedValue": 75,
        "status": "warn",
        "time": "2018-01-17T03:36:48Z",
        "output": "",
        "links": {
          "self": "http://api.example.com/dbnode/dfd6cf2b/health"
        }
      }
    ],
    "uptime": [
      {
        "componentType": "system",
        "observedValue": 1209600.245,
        "observedUnit": "s",
        "status": "pass",
        "time": "2018-01-17T03:36:48Z"
      }
    ],
    "cpu:utilization": [
      {
        "componentId": "6fd416e0-8920-410f-9c7b-c479000f7227",
        "node": 1,
        "componentType": "system",
        "observedValue": 85,
        "observedUnit": "percent",
        "status": "warn",
        "time": "2018-01-17T03:36:48Z",
        "output": ""
      },
      {
        "componentId": "6fd416e0-8920-410f-9c7b-c479000f7227",
        "node": 2,
        "componentType": "system",
        "observedValue": 85,
        "observedUnit": "percent",
        "status": "warn",
        "time": "2018-01-17T03:36:48Z",
        "output": ""
      }
    ],
    "memory:utilization": [
      {
        "componentId": "6fd416e0-8920-410f-9c7b-c479000f7227",
        "node": 1,
        "componentType": "system",
        "observedValue": 8.5,
        "observedUnit": "GiB",
        "status": "warn",
        "time": "2018-01-17T03:36:48Z",
        "output": ""
      },
      {
        "componentId": "6fd416e0-8920-410f-9c7b-c479000f7227",
        "node": 2,
        "componentType": "system",
        "observedValue": 5500,
        "observedUnit": "MiB",
        "status": "pass",
        "time": "2018-01-17T03:36:48Z",
        "output": ""
      }
    ]
  },
  "links": {
    "about": "http://api.example.com/about/authz",
    "http://api.x.io/rel/thresholds":
      "http://api.x.io/about/authz/thresholds"
  }
}
```


In this code, a GET request is made to the `/health` endpoint. The server responds with a 200 OK status, indicating that the request was successful. The response body is a JSON object that provides detailed information about the health status of the service.

The `status` field indicates the overall health status of the service. In this case, the status is `pass`, which means the service is healthy. The `version` and `releaseId` fields provide information about the version and release ID of the service, respectively.

The `checks` object contains a list of health checks that were performed. Each health check includes information such as the component ID, component type, observed value, observed unit, status, affected endpoints, time, and output. This information provides a detailed snapshot of the health of various components of the service.

The `links` object contains link relations and URIs for external links related to the health of the service. These links can provide additional information or resources related to the health of the service.

#### Example health check API 2

The following code snippet demonstrates how to call the SonarQube API to retrieve the health status of the system. It uses cURL to make the API call and includes the token for authentication.

```bash
curl -u THIS_IS_MY_TOKEN: https://sonarqube.com/api/system/health
```


In this code, `curl` is a command-line tool used to make HTTP requests. The `-u` option is used to specify the user credentials (in this case, the token) for authentication. The URL `https://sonarqube.com/api/system/health` is the endpoint of the SonarQube health check API.

When this command is executed, it sends a GET request to the SonarQube health check API. The server responds with the health status of the SonarQube system in JSON format.

In conclusion, these example demonstrate how health check APIs can be implemented and used to monitor the health of servers and applications. By understanding these examples, you can gain insights into how to effectively implement and use health check APIs in your own projects.


### Conclusion

In this blog, we've taken a deep dive into the world of health check APIs, exploring their significance, functionality, and best practices for implementation. 

We've learned that health check APIs serve as a diagnostic tool, providing valuable insights into the health and status of servers or applications. These APIs allow developers to monitor the availability, detect any inconsistencies or issues, and take necessary actions to resolve them. This ensures the availability, stability, and smooth functioning of the software.

We've also discussed the difference between health check APIs and other types of APIs. While most APIs enable interaction and data exchange between different applications or services, health check APIs are specifically designed to monitor the health and status of a server or application.

We've examined the process and the role of endpoints in health check APIs. We learned that the process involves a series of checks or tests to determine the health or status of a server or application. The role of endpoints in health check APIs is to provide a way for clients to access the health information.

We've looked at real-world examples of where health check APIs are used and the benefits they bring. Health check APIs are used in a wide range of scenarios across various industries. They bring several benefits, including early problem detection, improved performance, reliability, and dependency monitoring.

We've provided best practices for implementing health check APIs and common mistakes to avoid. We learned that by using health check APIs correctly, providing sufficient information, automating health checks, disabling cache, protecting your health check endpoint, and using a standardized response format, you can ensure that your health check APIs are as effective as possible.

Finally, we've shared some example codes of health check APIs, demonstrating how they can be implemented and used to monitor the health of servers and applications.

In conclusion, health check APIs are an essential part of modern software development. They provide a powerful tool for monitoring the health of applications and infrastructure, helping developers maintain the stability and availability of their software. By understanding and implementing these APIs effectively, developers can proactively identify and resolve issues, ensuring the smooth operation of their software.





## References

- [Hasura API Reference](https://hasura.io/docs/latest/api-reference/health/) 
- [Microsoft Architecture Guide](https://learn.microsoft.com/en-us/dotnet/architecture/microservices/implement-resilient-applications/monitor-app-health) 
- [Akita Software Blog](https://www.akitasoftware.com/blog-posts/a-gentle-introduction-to-and-indoctrination-on-health-check-endpoints) 
- [Stripe API Documentation](https://stripe.com/docs/api) 
- [Testfully Blog](https://testfully.io/blog/api-health-check-monitoring/) 
- [Oracle Coherence Documentation](https://docs.oracle.com/pls/topic/lookup?ctx=en/middleware/standalone/coherence/14.1.1.2206/release-notes&id=COHMG-GUID-1FF1C711-A7C3-45C7-B1E5-07DDA0D81515) 
- [AWS Builders' Library](https://aws.amazon.com/builders-library/implementing-health-checks/) 
- [Oracle Coherence Documentation](https://docs.oracle.com/pls/topic/lookup?ctx=en/middleware/standalone/coherence/14.1.1.2206/release-notes&id=COHMG-GUID-1FF1C711-A7C3-45C7-B1E5-07DDA0D81515) 
- [IETF Draft](https://datatracker.ietf.org/doc/html/draft-inadarei-api-health-check) 
- [SonarSource Community](https://community.sonarsource.com/t/using-the-health-check-api/16325) 

