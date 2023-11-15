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
    overlay_image: /assets/images/graphql_fastapi/banner.jpg
    overlay_filter: 0.5
    teaser: /assets/images/graphql_fastapi/banner.jpg
title: "Building and Optimizing GraphQL and FastAPI with Python"
tags:
    - Python

---

In this blog post, we delve into the world of GraphQL and FastAPI with Python, two powerful technologies that are revolutionizing how we build and interact with APIs. We kick off by introducing GraphQL and FastAPI, explaining what they are, their benefits, and why there's a growing need to integrate them. We then provide a comprehensive guide on how to build a GraphQL and FastAPI application with Python, covering everything from setting up the development environment to creating a new project and integrating GraphQL with FastAPI. We also touch on deployment strategies for your application, including containerization with Docker and scaling the application. In addition, we share some best practices for working with GraphQL and FastAPI, such as optimizing GraphQL queries, effective error handling, database modeling, automated testing, and documentation. We also discuss how to improve the performance of your application, focusing on asynchronous programming with FastAPI. Lastly, we explore the importance of unit tests and how to write them for your application. So, whether you're a seasoned developer or just starting out, this blog post is a valuable resource for anyone looking to harness the power of GraphQL and FastAPI with Python.

## Introduction

Today, we are going to delve into the world of GraphQL and FastAPI, two powerful technologies that are making waves in the field of API development. We will discuss what they are, why they are needed, and how they can be integrated to create efficient and robust APIs.

### What is GraphQL?

GraphQL, according to Hasura , is a query language for APIs and a runtime for executing those queries with your existing data. It offers an efficient and powerful alternative to REST. With GraphQL, you can define the shape of your data and operations that can be performed on it. This gives you more control over the data you receive, helping to avoid over-fetching or under-fetching of data. This is especially useful in scenarios where the client needs to interact with an API and would benefit from more control over the data it receives .

### What is FastAPI?

FastAPI, on the other hand, is a modern, fast (high-performance), web framework for building APIs with Python 3.6+ based on standard Python type hints . It is used for creating REST endpoints. FastAPI is easy to use and comes with automatic interactive API documentation. It is also very fast, allowing for the creation of high-performance REST APIs quickly and efficiently. FastAPI can be used when you need to build REST APIs quickly and efficiently, with automatic interactive API documentation .

### Why Use GraphQL and FastAPI?

The combination of GraphQL and FastAPI offers several advantages. GraphQL allows for more efficient data retrieval as only the required data is transferred, reducing the amount of data that needs to be transferred over the network . This can significantly improve the performance of your app. 

FastAPI, being a high-performance framework, allows for quick development of robust web APIs with very little boilerplate code . It also supports asynchronous code, which can lead to significant performance improvements .

These technologies are ideal for building high-performance web APIs that need to aggregate data from multiple sources, and when the client needs to have flexibility in the structure of the data returned from the server. They are also perfect for real-time applications due to GraphQL's support for subscriptions .

### The Need for Integration

The integration of GraphQL and FastAPI allows developers to build efficient and reliable APIs that take advantage of GraphQL's flexibility in querying data. This combination allows for faster development times, improved performance, and less boilerplate code. More so, FastAPI's support for asynchronous code can lead to significant performance improvements .

In the following sections, we will delve deeper into how to build, deploy, and optimize GraphQL and FastAPI with Python. We will also cover best practices and how to write unit tests for your GraphQL and FastAPI applications. So, let's dive in!




## Understanding GraphQL and FastAPI

In this section, we will delve deeper into understanding what GraphQL and FastAPI are. We will also look at their benefits and the scenarios where they are best used.

### Elaborating on GraphQL

As mentioned earlier, GraphQL is a query language for APIs and a runtime for executing those queries with your existing data. Developed by Facebook, it provides a more efficient, powerful, and flexible alternative to REST. It allows clients to define the structure of the data required, and the same structure of the data is returned from the server. This makes it easier to aggregate data from multiple sources.

One of the key advantages of using GraphQL is efficient data loading. It allows clients to specify exactly what data they need, which can reduce the amount of data that needs to be transferred over the network. This is particularly beneficial for applications with large data sets or complex data structures.

Furthermore, GraphQL schemas are strongly typed, providing compile-time checks of the data you are querying. This ensures type safety and helps to prevent errors that might occur due to incorrect data types.

Finally, GraphQL includes support for subscriptions, which allows real-time data updates. This makes it ideal for applications that require real-time functionality, such as chat applications, live updates, and more.

### Elaborating on FastAPI

FastAPI, on the other hand, is a high-performance framework for building web APIs with Python. It's built on top of Starlette for web routing and Pydantic for data validation. 

FastAPI is designed to be easy to use, while also enabling high performance. It allows developers to quickly develop robust web APIs using very little boilerplate code. This leads to faster development times and more efficient code.

Moreover, FastAPI supports asynchronous code, which can lead to significant performance improvements. This is particularly beneficial for applications that require handling of multiple requests concurrently or applications with I/O-bound tasks.

FastAPI also provides automatic interactive API documentation. This makes it easier for developers to understand and use the API, leading to increased productivity and efficiency.

### Best Use Cases for GraphQL and FastAPI

Given their features and benefits, GraphQL and FastAPI can be used in a variety of applications. They are particularly useful in scenarios where the client needs to interact with an API and would benefit from more control over the data it receives.

For instance, social media platforms, e-commerce sites, and any other application that involves complex querying of data can greatly benefit from using GraphQL and FastAPI. They are also ideal for real-time applications due to GraphQL's support for subscriptions.

In conclusion, understanding GraphQL and FastAPI, their benefits, and their best use cases can help developers make informed decisions when building APIs. In the next section, we will look at how to build GraphQL and FastAPI with Python.



## Building GraphQL and FastAPI with Python

In this section, we'll walk you through the process of building a GraphQL and FastAPI application with Python. We'll cover everything from setting up the development environment to creating a new project, integrating GraphQL with FastAPI, and building GraphQL queries and mutations.

### Setting up the Development Environment

First, we need to set up our development environment. FastAPI requires Python 3.6+ installed. To install FastAPI, you can use pip, the Python package manager:

```python
pip install fastapi
```

You also need Uvicorn, an ASGI server to serve your app:

```python
pip install uvicorn
```

Additionally, for building GraphQL schemas and types, you need to install strawberry-graphql:

```python
pip install 'strawberry-graphql[fastapi]'
```

To work with JSON data, the built-in `json` package is used.

### Creating a New FastAPI Project

Once you have your development environment set up, you can start a new FastAPI project by creating a new directory for your app. Inside this directory, create a new file named `main.py`. This will be the index file for your server.

### Integrating GraphQL with FastAPI

With your project set up, the next step is to integrate GraphQL with FastAPI. FastAPI is based on the ASGI standard, making it very easy to integrate any GraphQL library also compatible with ASGI. You can combine normal FastAPI path operations with GraphQL on the same application.

Here is an example of how you can integrate Strawberry, a GraphQL library with ASGI support, with FastAPI:

```python
from typing import List

import strawberry
from fastapi import FastAPI
from strawberry.asgi import GraphQL
import uvicorn


@strawberry.type
class User:
    id: int
    name: str
    age: int


Users: List[User] = [User(id=1, name="Patrick", age=100)]


@strawberry.type
class Query:
    @strawberry.field
    def user(self, id: int) -> User:
        for user in Users:
            if user.id == id:
                return user
        raise ValueError(f"User with id {id} not found")

schema = strawberry.Schema(query=Query, mutation=Mutation)

graphql_app = GraphQL(schema)

app = FastAPI()
app.add_route("/graphql", graphql_app)
app.add_websocket_route("/graphql", graphql_app)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

In this code, we first define a `User` type with `name` and `age` fields. We then define a `Query` type with a `user` field that returns a `User`. We then create a Strawberry schema with our `Query` type and use it to create a `GraphQL` application. Finally, we add a route for our GraphQL application in our FastAPI application.

### Building GraphQL Queries and Mutations

In GraphQL, queries are used to fetch data, and mutations are used to modify data.

Here is an example of how you can define a query to fetch a user and a mutation to add a user:

```python
@strawberry.type
class Query:
    @strawberry.field
    def user(self, id: int) -> User:
        for user in Users:
            if user.id == id:
                return user
        raise ValueError(f"User with id {id} not found")


@strawberry.type
class AddUserResult:
    user: User

@strawberry.type
class Mutation:
    @strawberry.mutation
    def add_user(self, name: str, age: int) -> AddUserResult:
        # add user to database
        user = User(id=len(Users) + 1, name=name, age=age)
        Users.append(user)
        print(f"Added user: {user}")
        return AddUserResult(user=user)


schema = strawberry.Schema(query=Query, mutation=Mutation)
```

This code is a simple GraphQL API built with Strawberry, a Python library for building GraphQL APIs. It defines two types, `Query` and `Mutation`, and a schema that includes these types.

1. `Query` class: This class represents the queries that clients can make to the API. It has one field, `user`, which is a method that takes an `id` parameter and returns a `User` object. The `@strawberry.field` decorator indicates that this method is a field in the GraphQL schema. The method iterates over the `Users` list (which is assumed to be a list of `User` objects defined elsewhere in your code), and returns the user with the matching `id`. If no user is found, it raises a `ValueError`.

2. `AddUserResult` class: This class is a custom output type for the `add_user` mutation. It has one field, `user`, which is a `User` object. This class is used to wrap the result of the `add_user` mutation.

3. `Mutation` class: This class represents the mutations that clients can make to the API. It has one field, `add_user`, which is a method that takes `name` and `age` parameters and returns an `AddUserResult` object. The `@strawberry.mutation` decorator indicates that this method is a mutation in the GraphQL schema. The method creates a new `User` object, adds it to the `Users` list, prints a message to the console, and returns an `AddUserResult` object that wraps the new user.

4. `schema` object: This object represents the GraphQL schema for the API. It is created with the `strawberry.Schema` function, which takes the `Query` and `Mutation` classes as arguments. This schema can be used to create a GraphQL server that serves the defined queries and mutations.

To use this code, you would need to define the `User` class and the `Users` list, and create a server with the `schema` object. You could then send GraphQL queries to get users and mutations to add users. The server would execute the corresponding methods in the `Query` and `Mutation` classes and return the results in a GraphQL response.


And there you have it! A step-by-step guide on how to build a GraphQL and FastAPI application with Python. In the next section, we will look at how to deploy this application.


## Deploying GraphQL and FastAPI with Python

After building our GraphQL and FastAPI application, the next step is to deploy it. Deployment involves making our application available on a server so that it can be accessed by users over the internet. In this section, we will look at how to containerize our application with Docker and how to scale it to handle more traffic.

### Containerizing GraphQL and FastAPI Application with Docker

Docker is a popular platform that allows us to package our application and its dependencies into a container. Containers are lightweight, standalone, and executable software packages that include everything needed to run an application, including the code, a runtime, libraries, environment variables, and config files.

Containerizing our application with Docker provides several benefits. It ensures that our application runs the same way regardless of the environment. This means that we can avoid the common problem of "it works on my machine" where an application works on one machine but not on another due to differences in the environment.

To containerize our GraphQL and FastAPI application, we need to create a Dockerfile. A Dockerfile is a text file that contains the instructions to build a Docker image. Here is an example of a Dockerfile for our application:

```dockerfile
## Use an official Python runtime as a parent image
FROM python:3.9-slim-buster

## Set the working directory in the container to /app
WORKDIR /app

## Add the current directory contents into the container at /app
ADD . /app

## Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

## Make port 8000 available to the world outside this container
EXPOSE 8000

## Run app.py when the container launches
CMD ["python", "graphql_fastapi/main.py"]
```

Run the following command to build the Docker image:

```bash
docker build -t graphql-fastapi .
````

And then run the following command to run the Docker container:

```bash
docker run -p 8000:8000 graphql-fastapi
```

This Dockerfile starts with a Python 3.9 image, sets the working directory to `/app`, and adds the contents of the current directory to the container. It then installs the required packages using pip and exposes port 8000. Finally, it starts our application using the uvicorn command.

### Scaling GraphQL and FastAPI Application

Once our application is containerized, we can easily scale it to handle more traffic. Scaling involves increasing the resources available to our application, such as CPU, memory, and network bandwidth. There are two main types of scaling: vertical scaling and horizontal scaling.

Vertical scaling, also known as scaling up, involves increasing the resources of an existing server. For example, we can upgrade our server to have a faster CPU, more memory, or more network bandwidth.

Horizontal scaling, also known as scaling out, involves adding more servers to our application. For example, we can deploy our Docker container to multiple servers and use a load balancer to distribute the traffic among these servers.

FastAPI is built on Starlette for the web parts and Pydantic for the data parts, which allows it to be one of the fastest Python frameworks. This makes it an excellent choice for building high-performance applications that can handle a large number of requests per second.

In conclusion, deploying a GraphQL and FastAPI application involves containerizing the application with Docker and scaling it to handle more traffic. By following these steps, we can ensure that our application is available to users over the internet and can handle a large number of requests.


## Playground for GraphQL and FastAPI with Python

GraphQL Playground is a powerful web-based IDE (Integrated Development Environment) that allows you to interact with a GraphQL API. It provides a user-friendly interface where you can send GraphQL queries and mutations, view the responses, and explore the available schema.

When you access GraphQL Playground over "http://localhost:8000/graphql", it means that you can access the GraphQL API running on your local machine at port 8000. This is typically the default URL and port for a FastAPI-based GraphQL server.

Once you open GraphQL Playground in your web browser, you will see a text editor where you can write your GraphQL queries and mutations. You can use the auto-complete feature to easily explore the available fields and types in the schema.

To send a query or mutation, simply type it in the editor and press the play button (usually located at the top right corner of the interface). The response will be displayed in the right panel, showing the data returned by the API.

GraphQL Playground also provides additional features to enhance your development experience. For example, you can view the documentation for the available types and fields by hovering over them or clicking on them. You can also save your queries and mutations for future use, and even share them with others.

Overall, GraphQL Playground is a valuable tool for developers working with GraphQL APIs. It simplifies the process of testing and exploring the API, making it easier to understand and work with the data provided by the server.


## Best Practices for GraphQL and FastAPI with Python

When working with GraphQL and FastAPI, it's essential to follow best practices to ensure that your application is robust, efficient, and maintainable. In this section, we will share some of these best practices, including optimizing GraphQL queries, effective error handling, database modeling, automated testing, and documentation.

### Optimizing GraphQL Queries

One of the key advantages of GraphQL is the ability to fetch exactly the data you need. This is known as query optimization and is a crucial practice when working with GraphQL. When designing your GraphQL schema and queries, consider the following:

1. **Specify only the fields you need**: GraphQL allows clients to specify exactly what data they need, which can reduce the amount of data that needs to be transferred over the network. This can lead to significant performance improvements, especially for large applications and networks.

2. **Use aliases for renamed fields**: If you need to request the same field with different arguments, you can use aliases to rename the result field in the response.

3. **Use fragments to reuse parts of queries**: Fragments are a way to reuse parts of GraphQL queries. This can make your queries more readable and maintainable.

### Effective Error Handling

Proper error handling is crucial for any application. In GraphQL and FastAPI, you can handle errors by raising exceptions. When an exception is raised, GraphQL will return an error. For example, you can raise an exception if a user tries to create a course with an ID that already exists in your data store.

In FastAPI, unhandled exceptions will result in a 500 Internal Server Error response. However, you can also handle exceptions manually by using FastAPI's `@app.exception_handler` decorator to define a custom exception handler.

### Database Modeling and Relationships

When working with databases, it's crucial to model your data correctly and define the right relationships between your tables. In FastAPI, you can use Pydantic models for data validation. Each Pydantic model defines a set of fields and their types, and FastAPI will automatically validate request data against these models.

### Automated Testing

Automated testing is a best practice for any software development process. It helps to ensure that your code works as expected and makes it easier to catch and fix bugs early. In FastAPI, you can use the `TestClient` class to make requests to your application and check the responses.

### Documentation

Good documentation is crucial for any API. It helps developers understand how to use your API and what to expect from it. FastAPI provides automatic interactive API documentation. By navigating to 'http://localhost:8000/docs' in a browser, one can view the beautiful documentation that FastAPI has.

In conclusion, following these best practices when working with GraphQL and FastAPI can help you build robust, efficient, and maintainable APIs. In the next section, we will look at how to improve the performance of your GraphQL and FastAPI application.



## Improving Performance for GraphQL and FastAPI with Python

As we've seen, GraphQL and FastAPI are powerful technologies for building efficient and robust APIs. However, as with any technology, there are ways to optimize your use of GraphQL and FastAPI to further improve the performance of your application. One key strategy for improving performance is to leverage the power of asynchronous programming in FastAPI.

### Asynchronous Programming with FastAPI

Asynchronous programming is a design pattern that is used in computing to enhance the performance of your application. It allows a unit of work to run separately from the main application thread and notifies the main thread when it is done. In the context of a FastAPI application, it can be beneficial in handling and making requests.

FastAPI, as a modern web framework, is built to enable high performance and it supports HTTP/2 and WebSockets. It is built on top of Starlette for the web parts and Pydantic for the data parts, which allows it to be one of the fastest Python frameworks. This makes it an excellent choice for building high-performance applications that can handle a large number of requests per second.

FastAPI is designed to be easy to use and comes with built-in support for data validation, serialization, and documentation, along with several other features. However, one of its most powerful features is its support for asynchronous request handling.

In Python, the keywords `async` and `await` are used to define coroutines. Coroutines are special functions that can be paused and resumed, allowing them to be non-blocking. This means that in a FastAPI application, you can define route handling functions with `async def` instead of just `def`, and FastAPI will run them in a non-blocking way using Python's asyncio. Here's an example:

```python
@app.get('/')
async def read_root():
    return {"Hello": "World"}
```

In this example, the function `read_root` is defined with `async def` instead of just `def`. This means that FastAPI can pause and resume the execution of the function, allowing it to handle other requests while waiting for the function to complete. This can lead to significant performance improvements, especially in I/O-bound scenarios where the function is waiting for a response from a database or an external API.

In conclusion, asynchronous programming in FastAPI can be a powerful tool for improving the performance of your GraphQL and FastAPI application. By using `async` and `await` in your route handling functions, you can make your application more responsive and capable of handling a larger number of requests.



## Writing Unit Tests for GraphQL and FastAPI with Python

Testing is a key aspect of software development that helps to ensure the functionality and reliability of your code. In particular, unit tests, which test individual units of code in isolation, can be invaluable in catching bugs early in the development process.

In this section, we will discuss the importance of unit tests and provide a step-by-step guide on how to write them for a GraphQL and FastAPI application.

### The Importance of Unit Tests

Unit tests are a type of automated test that focus on a small "unit" of code, such as a single function or method. By testing these small pieces of code in isolation, we can ensure that they function correctly in any situation. This can help us catch bugs and errors early in the development process, before they become bigger problems.

In addition, unit tests serve as a form of documentation. They demonstrate how a piece of code is supposed to work, and what its expected behavior is in different situations. This can be especially useful for other developers who might be working with your code.

Finally, having a suite of unit tests can make it easier to refactor or add new features to your code. By running the tests after making changes, you can ensure that your changes haven't broken anything.

### Writing Unit Tests for GraphQL and FastAPI

When writing unit tests for a GraphQL and FastAPI application, there are a few key steps to follow:

1. **Set Up Your Testing Environment**: Before you can write your tests, you need to set up a testing environment. This might involve creating a separate database configuration to avoid overwriting data in your main development database.

2. **Create Test Data**: You'll also need to create some test data. This can be done using pytest fixtures, which are functions that provide a fixed baseline of data for your tests.

3. **Write Your Tests**: Now you're ready to write your tests. In each test, you'll want to make a request to your application and then check the response. To make requests to your application, you can use FastAPI's `TestClient` class.

Here's an example of what a unit test might look like for a GraphQL and FastAPI application:

```python
from fastapi.testclient import TestClient
from graphql_fastapi.graphql_fastapi.main import app

client = TestClient(app)


def test_get_user():
    response = client.post("/graphql", json={
        "query": """
            query($id: Int!) {
                user(id: $id) {
                    id
                    name
                    age
                }
            }
        """,
        "variables": {
            "id": 1
        }
    })

    assert response.status_code == 200
    assert response.json() == {
        "data": {
            "user": {
                "id": 1,
                "name": "Patrick",
                "age": 100
            }
        }
    }


def test_get_user_not_found():
    response = client.post("/graphql", json={
        "query": """
            query($id: Int!) {
                user(id: $id) {
                    id
                    name
                    age
                }
            }
        """,
        "variables": {
            "id": 100
        }
    })

    assert response.status_code == 200
    assert "errors" in response.json()
    assert response.json()["errors"][0]["message"] == "User with id 100 not found"


def test_add_user():
    response = client.post("/graphql", json={
        "query": """
            mutation($name: String!, $age: Int!) {
                addUser(name: $name, age: $age) {
                    user {
                        name
                        age
                    }
                }
            }
        """,
        "variables": {
            "name": "John",
            "age": 25
        }
    })

    assert response.status_code == 200
    assert response.json() == {
        "data": {
            "addUser": {
                "user": {
                    "name": "John",
                    "age": 25
                }
            }
        }
    }

```

This code is a set of unit tests for a GraphQL API built with FastAPI. It uses the `TestClient` class from the `fastapi.testclient` module to send requests to the API and pytest to define and run the tests.

1. `test_get_user`: This test function sends a GraphQL query to get the user with the ID of 1. It checks that the response status code is 200 (which means the request was successful) and that the response data matches the expected user data.

2. `test_get_user_not_found`: This test function sends a GraphQL query to get a user with a non-existing ID (100 in this case). It checks that the response status code is 200 and that the response contains an error with the expected message. The status code is 200 because in GraphQL, an error in a query or mutation does not result in an HTTP error status code. Instead, the error is included in the "errors" field of the GraphQL response.

3. `test_add_user`: This test function sends a GraphQL mutation to add a new user. It checks that the response status code is 200 and that the response data matches the expected data for the added user.

In each test function, the `client.post` method is used to send a POST request to the "/graphql" endpoint of the API. The GraphQL query or mutation is passed as a string to the `json` parameter of this method. The `json` parameter also includes a "variables" field that contains the variables for the query or mutation.

The `assert` statements are used to check that the actual response matches the expected response. If an `assert` statement fails, pytest will report the test as failed.

4. **Run Your Tests**: Once you've written your tests, you can run them using a test runner like `pytest`. If any of your tests fail, the test runner will provide detailed output that can help you diagnose and fix the problem.

In conclusion, unit tests are a crucial part of developing a robust and reliable GraphQL and FastAPI application. They help you catch bugs early, serve as documentation, and make it easier to refactor your code or add new features. By following the steps outlined above, you can write effective unit tests for your own applications.


## Conclusion

In this blog post, we have taken a deep dive into the world of GraphQL and FastAPI with Python, two powerful technologies that are transforming the way we build APIs. We discussed what GraphQL and FastAPI are, their benefits, and the best use cases for each.

We've learned that GraphQL is a query language for APIs that provides an efficient and powerful alternative to REST. It allows clients to define the structure of the data required, leading to more efficient data retrieval. FastAPI, on the other hand, is a high-performance framework for building web APIs with Python. It's built on top of Starlette for web routing and Pydantic for data validation. 

We also explored how to build a GraphQL and FastAPI application with Python, from setting up the development environment to creating a new project, integrating GraphQL with FastAPI, and building GraphQL queries and mutations. 

We also covered essential aspects of deploying our application, including containerizing our application with Docker and scaling it to handle more traffic. 

Following best practices when working with GraphQL and FastAPI was emphasized, including optimizing GraphQL queries, effective error handling, database modeling, automated testing, and documentation. 

We also discussed how to improve the performance of our GraphQL and FastAPI application by leveraging the power of asynchronous programming in FastAPI. 

Finally, we highlighted the importance of unit tests and provided a step-by-step guide on how to write them for a GraphQL and FastAPI application.

With the knowledge gained from this blog post, I encourage you to start building your own GraphQL and FastAPI applications with Python. Remember, the key to mastering any technology is through consistent practice and continuous learning. Happy coding!


Source code for this blog post can be found [here](https://github.com/thinhdanggroup/thinhda_dev_blog/tree/main/graphql_fastapi).


## References

- [Hasura.io](https://hasura.io/learn/graphql/backend-stack/languages/python/) 
- [Obytes](https://www.obytes.com/blog/getting-started-with-graphql-in-python-with-fastapi-&-ariadne) 
- [Testdriven.io](https://testdriven.io/blog/fastapi-graphql/) 
- [LogRocket](https://blog.logrocket.com/building-a-graphql-server-with-fastapi/) 
- [FastAPI](https://fastapi.tiangolo.com/how-to/graphql/) 
- [FastAPI GitHub](https://github.com/tiangolo/fastapi/issues/1664) 
