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
    overlay_image: /assets/images/testcontainers-2/banner.jpeg
    overlay_filter: 0.5
    teaser: /assets/images/testcontainers-2/banner.jpeg
title: "Mastering Unit Testing with Testcontainers: A Comprehensive Guide for Python Developers"
tags:
    - Testcontainers
    - Python

---

This blog post provides a comprehensive guide for Python developers on mastering unit testing with Testcontainers. Starting with an introduction to unit testing and the role of Testcontainers, the post dives into a step-by-step guide on writing your first test using Testcontainers. It then discusses how to manage resources in Testcontainers with illustrative code examples. The post also shares best practices for writing tests and highlights common pitfalls and how to avoid them when writing tests with Testcontainers. It further explains how to test an API using Testcontainers, offering a code example for better understanding. The post concludes with a case study on testing a payment API using Testcontainers, providing a detailed walkthrough and code examples. The readers will gain a solid understanding of using Testcontainers for unit testing in Python, making their testing process more efficient and effective.

## Introduction

Testing is an integral part of software development. It ensures the correctness of our code, increases the reliability of our software, and gives us confidence in our work. Among the various types of testing, unit testing is fundamental. It focuses on small, isolated parts of a program, ensuring that each unit of code performs as expected.

However, writing effective unit tests can be challenging, especially when dealing with external dependencies like databases, APIs, or other services. This is where Testcontainers comes into play.

Testcontainers is a powerful library that simplifies the process of testing code that interacts with external resources. It provides lightweight, throwaway instances of common databases, Selenium web browsers, or anything else that can run in a Docker container, which are perfect for use in your unit tests.

The beauty of Testcontainers is that it allows you to bring your tests closer to production reality. Instead of mocking external dependencies, which can be error-prone and lead to false positives, you can test against real instances of these dependencies. This results in tests that are more reliable, accurate, and valuable.

In this blog post, we'll dive deep into how to master unit testing with Testcontainers, specifically for Python developers. We'll cover everything from writing your first test with Testcontainers, managing resources, best practices, common pitfalls, and a detailed case study on testing a Payment API. By the end of this post, you'll have a solid understanding of how to leverage Testcontainers to write effective unit tests that provide real value.

## Writing Your First Test with Testcontainers and Python

Now that we have a basic understanding of Testcontainers and its benefits, let's dive into writing our first unit test using Testcontainers and Python. We will write a simple test that connects to a PostgreSQL database running inside a Docker container.

### Step 1: Installing Testcontainers

Before we start, we need to install the Testcontainers library. Testcontainers is available as a Python package and can be installed using pip:

```python
pip install testcontainers
```

### Step 2: Importing the Necessary Libraries

Next, we import the necessary libraries for our test. We will use `unittest` for our testing framework and `psycopg2` for connecting to the PostgreSQL database:

```python
import unittest
import psycopg2
from testcontainers.postgres import PostgresContainer
```

### Step 3: Creating a PostgreSQL Container

We then create a PostgreSQL container using the `PostgresContainer` class from Testcontainers:

```python
container = PostgresContainer("postgres:9.5")
```

This line of code creates a new PostgreSQL container with the image `postgres:9.5`. The image is automatically downloaded from Docker Hub if it's not already available locally.

### Step 4: Starting the Container

After creating the container, we need to start it:

```python
container.start()
```

The `start()` method starts the PostgreSQL container and waits until it's ready to accept connections.

### Step 5: Connecting to the Database

Once the container is running, we can connect to the PostgreSQL database using the `psycopg2` library. We use the `get_connection_url()` method of the container to get the connection URL:

```python
connection_url = container.get_connection_url()
conn = psycopg2.connect(connection_url)
cursor = conn.cursor()
```

### Step 6: Writing the Test

Now that we have a connection to the database, we can write our test. In this test, we execute a simple SQL query to fetch the version of the PostgreSQL database:

```python
class MyTestCase(unittest.TestCase):
    def test_postgres_version(self):
        cursor.execute('SELECT version()')
        result = cursor.fetchone()
        self.assertIsNotNone(result)
```

In this test, we execute the `SELECT version()` SQL query using the cursor, fetch the result, and assert that the result is not None.

### Step 7: Cleaning Up

Finally, after the test, we clean up by closing the cursor and connection, and stopping the container:

```python
cursor.close()
conn.close()
container.stop()
```

And that's it! We have written our first unit test using Testcontainers and Python. This test verifies the connection to a real PostgreSQL database running inside a Docker container, providing a more accurate and reliable test result compared to mocking the database connection.

In the next section, we will discuss how to manage resources with Testcontainers and Python, including how to automatically start and stop containers using the `with` statement. Stay tuned!


## Managing Resources with Testcontainers and Python

One of the key features of Testcontainers is its ability to manage resources effectively. When we run our tests, Testcontainers automatically starts the necessary Docker containers, and once the tests are finished, it stops and removes them. This ensures that our tests are isolated and do not interfere with each other, and it also prevents resource leaks.

However, it's important to understand how Testcontainers manages these resources and how we can control this behavior. In this section, we'll explore how to manage resources with Testcontainers and Python, and provide a code example demonstrating the process.

### Resource Management in Testcontainers

When we create a container with Testcontainers, the container is not immediately started. It's only started when we call the `start()` method. Once started, the container runs in the background until we stop it by calling the `stop()` method.

This gives us fine-grained control over the lifecycle of our containers. We can start and stop them at any point in our tests, and we can even start multiple containers at the same time. However, manually starting and stopping containers can be error-prone and tedious, especially when we have multiple tests.

### Using the `with` Statement for Automatic Resource Cleanup

To simplify resource management, Testcontainers provides a context manager that automatically starts and stops containers. This context manager is implemented using Python's `with` statement. When we create a container inside a `with` block, the container is automatically started before the block and stopped after the block.

Here's an example of how to use the `with` statement with Testcontainers:

```python
from testcontainers.postgres import PostgresContainer

with PostgresContainer("postgres:9.5") as postgres:
    # Use the PostgreSQL container in your tests
    pass  # Replace this with your test code

## The PostgreSQL container is automatically stopped and removed
```

In this example, we create a PostgreSQL container inside a `with` block. The container is automatically started before the block and stopped after the block. This ensures that our tests are always run in a clean environment, and it also simplifies our test code by removing the need to manually start and stop containers.

Managing resources effectively is crucial for writing reliable and efficient tests. Testcontainers provides powerful features for resource management, allowing us to easily start, stop, and control containers in our tests. By using the `with` statement, we can ensure that our containers are automatically cleaned up after our tests, preventing resource leaks and ensuring that our tests are isolated.

In the next section, we'll discuss some best practices for writing tests with Testcontainers and Python, providing tips and tricks to help you write more effective tests. Stay tuned!


## Best Practices for Writing Tests with Testcontainers and Python

Writing tests with Testcontainers and Python is a powerful way to ensure the quality and reliability of your software. However, to get the most out of your tests, it's essential to follow some best practices. In this section, we'll discuss several tips and tricks for writing efficient and effective tests with Testcontainers and Python, complete with code examples to illustrate these best practices.

### Use Descriptive Test Names

When writing tests, it's important to give each test a descriptive name that clearly indicates what the test is verifying. This makes it easier to understand the purpose of the test and to diagnose failures when they occur. For example, if you're testing a function that calculates the sum of two numbers, a good test name might be `test_sum_calculates_correctly`.

```python
def test_sum_calculates_correctly(self):
    result = sum(1, 2)
    assert result == 3
```

### Keep Your Tests Isolated and Independent

Each test should be isolated and independent of other tests. This means that the outcome of one test should not affect the outcome of another test. To achieve this, you should avoid sharing state between tests and clean up any resources that are created during a test. Testcontainers makes this easy by automatically starting and stopping containers for each test.

```python
class MyTestCase(unittest.TestCase):
    def test_a(self):
        with PostgresContainer("postgres:9.5") as postgres:
            # Use the PostgreSQL container in test_a
            pass

    def test_b(self):
        with PostgresContainer("postgres:9.5") as postgres:
            # Use the PostgreSQL container in test_b
            pass
```

### Use Appropriate Assertions

Make sure to use the appropriate assertions for each test. The assertions should accurately reflect what you're trying to verify in the test. For example, if you're testing that a function returns a certain value, you should use the `assertEqual` assertion. If you're testing that a function raises an exception, you should use the `assertRaises` assertion.

```python
def test_divide_by_zero_raises_exception(self):
    with self.assertRaises(ZeroDivisionError):
        divide(1, 0)
```

### Handle Test Failures Gracefully

When a test fails, it should provide clear and useful information about what went wrong. This makes it easier to diagnose and fix the issue. You can achieve this by using descriptive assertion messages and by handling exceptions properly.

```python
def test_sum_calculates_correctly(self):
    result = sum(1, 2)
    self.assertEqual(result, 3, "The sum function did not calculate the sum correctly")
```

### Keep Your Tests Simple and Focused

Each test should be simple and focused on a single aspect of the functionality. Avoid writing complex tests that try to verify multiple things at once. This makes the tests easier to understand and maintain, and it also makes it clearer what's going wrong when a test fails.

```python
def test_sum_calculates_correctly(self):
    result = sum(1, 2)
    assert result == 3

def test_sum_handles_negative_numbers(self):
    result = sum(-1, -2)
    assert result == -3
```

By following these best practices, you can write more effective and efficient tests with Testcontainers and Python. In the next section, we'll look at a case study of testing a Payment API with Testcontainers and Python.

## Testing a Payment API with Testcontainers and Python

In this section, we will walk through a case study of testing a Payment API with Testcontainers and Python. This Payment API allows creating and retrieving payments. It interacts with a PostgreSQL database to store and retrieve payment data. We will write tests for this API using Testcontainers to provide a real PostgreSQL database for our tests.

### Step 1: Define the Payment API

First, let's define our Payment API. This API exposes two endpoints: one for creating a payment and another for retrieving a payment. The API interacts with a PostgreSQL database to store and retrieve payment data.

```python
import os

from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("SQLALCHEMY_DATABASE_URI",
                                                       "postgresql://user:password@localhost/db")
db = SQLAlchemy(app)


class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), nullable=False)
    status = db.Column(db.String(10), nullable=False)


@app.route('/payments', methods=['POST'])
def create_payment():
    data = request.get_json()
    payment = Payment(amount=data['amount'], currency=data['currency'], status='pending')
    db.session.add(payment)
    db.session.commit()
    return jsonify({"id": payment.id}), 201


@app.route('/payments/<int:id>', methods=['GET'])
def get_payment(id):
    payment = Payment.query.get(id)
    if payment is None:
        return jsonify({"error": "Payment not found"}), 404
    return jsonify({"amount": payment.amount, "currency": payment.currency, "status": payment.status}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
```

### Step 2: Write the Test

Now, let's write a test for our Payment API using Testcontainers. We will create a PostgreSQL container and pass the connection URL to our Flask application. We will then send a POST request to the `/payments` endpoint to create a new payment, and a GET request to the `/payments/<id>` endpoint to retrieve the payment.

```python
import os
import unittest

from testcontainers.postgres import PostgresContainer


class APITestCase(unittest.TestCase):
    container = None

    @classmethod
    def setUpClass(cls):
        cls.container = PostgresContainer("postgres:9.5")
        cls.container.start()
        os.environ["SQLALCHEMY_DATABASE_URI"] = cls.container.get_connection_url()
        from payment_testcontainers.app import app, db
        cls.app = app
        cls.db = db

    def setUp(self):
        with self.app.app_context():
            self.db.create_all()
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            self.db.session.remove()
            self.db.drop_all()

    def test_create_payment(self):
        response = self.client.post('/payments', json={'amount': 100.0, 'currency': 'USD'})
        self.assertEqual(response.status_code, 201)
        self.assertIn('id', response.get_json())

        response = self.client.get(f"/payments/{response.get_json()['id']}")
        self.assertEqual(response.status_code, 200)
        payment = response.get_json()
        self.assertEqual(payment['amount'], 100.0)
        self.assertEqual(payment['currency'], "USD")
        self.assertEqual(payment['status'], "pending")
```

In this test, we create a PostgreSQL container using the `PostgresContainer` class and start it in the `setUpClass` method. We then send a POST request to the `/payments` endpoint to create a new payment, and a GET request to the `/payments/{id}` endpoint to retrieve the payment. We validate the responses using assertions to ensure that the API is working as expected.

By using Testcontainers, we can test our Payment API against a real PostgreSQL database, providing a more accurate and reliable test result compared to mocking the database connection. This allows us to catch potential issues that could occur in a production environment, improving the quality and reliability of our Payment API.

In the end, testing is a crucial part of software development. It helps us catch bugs early, ensures that our code meets its requirements, and gives us confidence when we release our software. Using tools like Testcontainers can make the testing process easier and more effective, helping us write better software.


## Conclusion 

Throughout this blog post, we've explored the benefits of using Testcontainers for unit testing in Python. We've covered the basics of Testcontainers, discussed how to write your first test, and delved into resource management. We've also shared some best practices for writing tests with Testcontainers and Python, and highlighted common pitfalls and how to avoid them.

The key takeaway is that Testcontainers offers a powerful and flexible way to write unit tests that interact with external resources. By providing lightweight, disposable instances of common databases, Selenium web browsers, or anything else that can run in a Docker container, Testcontainers allows you to bring your tests closer to the production environment. This results in tests that are more reliable, accurate, and valuable.

We've also demonstrated through a case study how to test a Payment API using Testcontainers and Python. This practical example showcased how Testcontainers can be used to create a real-world testing environment for APIs that interact with a PostgreSQL database. 

In conclusion, Testcontainers is a valuable tool for any Python developer looking to improve the quality and reliability of their unit tests. By simulating real-world environments and dependencies, it allows you to catch potential issues early and ensure that your code behaves as expected under various conditions. Whether you're testing simple functions or complex APIs, Testcontainers can make your testing process easier and more effective. 

Remember, good testing practices are vital for the success of any software project. And with tools like Testcontainers, you can ensure that your tests provide real value and contribute to the overall quality of your software. Happy testing!




## References

- https://testcontainers.com/
- https://testcontainers.com/getting-started/
- https://java.testcontainers.org/quickstart/junit_5_quickstart/
- https://github.com/testcontainers/testcontainers-python/issues/138
- https://github.com/testcontainers/testcontainers-python
- https://java.testcontainers.org/test_framework_integration/manual_lifecycle_control/
- https://github.com/testcontainers/testcontainers-python/issues/109
- https://thinhdanggroup.github.io/testcontainers/
- https://github.com/testcontainers/testcontainers-java/issues/955
- https://www.atomicjar.com/2022/11/testcontainers-testing-with-real-dependencies/

