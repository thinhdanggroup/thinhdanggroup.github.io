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
    overlay_image: /assets/images/nodejs/banner.jpeg
    overlay_filter: 0.5
    teaser: /assets/images/nodejs/banner.jpeg
title: "The Essential Blueprint for Node.js: A Step-by-Step Guide for Junior Engineers"
tags:
    - Coding
    - Node.js

---

Embark on a comprehensive journey into the world of Node.js, a powerful JavaScript runtime environment that has revolutionized web development. This blog serves as an essential blueprint for junior engineers, providing a step-by-step guide to understanding the fundamentals, core concepts, and practical applications of Node.js. Dive into the history, significance, and comparison of Node.js with traditional server-side languages. Explore the relationship between JavaScript and Node.js, and discover how the V8 engine enables JavaScript execution outside the browser. Master the core concepts of Node.js, including the Event Loop, Non-Blocking I/O, Callbacks, Promises, Streams, Buffers, Modules, and Requiring Files. Engage in hands-on exercises to build a simple web server, work with databases, create RESTful APIs, explore asynchronous programming, test and debug applications, and deploy Node.js projects. Conclude with a summary of key points, encouragement for continued learning and experimentation, and valuable resources for further exploration. Whether you're a beginner or an aspiring web developer, this blog will equip you with the knowledge and skills to harness the power of Node.js and create dynamic, scalable web applications.

## Introduction to Node.js

### What is Node.js?

Node.js is a cross-platform runtime environment and JavaScript library that allows developers to run JavaScript code server-side. It is an open-source project that was created by Ryan Dahl in 2009. Node.js is built on the V8 JavaScript engine, which is the same engine that powers Google Chrome. This makes Node.js very fast and efficient.

### History of Node.js

Node.js was created in 2009 by Ryan Dahl. Dahl was a software engineer at Joyent, a cloud computing company. He was frustrated with the lack of a good way to write scalable network applications in JavaScript. So, he created Node.js as a way to run JavaScript code outside of a web browser.

Node.js quickly gained popularity among developers, and it is now one of the most popular programming languages in the world. It is used by companies such as Netflix, Uber, and PayPal.

### Why is Node.js Important in Web Development?

Node.js is important in web development because it allows developers to write scalable, real-time applications in JavaScript. Node.js is also very easy to learn, which makes it a good choice for developers who are new to web development.

### Comparison with Traditional Server-Side Languages

Node.js is often compared to traditional server-side languages such as PHP, Python, and Java. Node.js has a number of advantages over these languages, including:

* **Speed:** Node.js is very fast, thanks to the V8 JavaScript engine.
* **Scalability:** Node.js is very scalable, thanks to its event-driven architecture.
* **Real-time:** Node.js is ideal for building real-time applications, such as chat applications and multiplayer games.
* **Easy to learn:** Node.js is very easy to learn, which makes it a good choice for developers who are new to web development.

Node.js is a powerful and versatile programming language that is perfect for building scalable, real-time applications. It is easy to learn and use, and it is backed by a large and active community of developers. If you are looking for a new programming language to learn, Node.js is a great option.

In the next session, we will delve deeper into the core concepts of Node.js, exploring its event loop, non-blocking I/O, callbacks, promises, streams, buffers, modules, and more. We will also set up a Node.js development environment and build a simple web server to solidify our understanding.


## Understanding JavaScript and Node.js

In this section, we will delve into the relationship between JavaScript and Node.js, the role of the V8 engine, and how Node.js leverages JavaScript for server-side scripting.

### JavaScript and Node.js

JavaScript is a high-level, interpreted programming language that is used for both client-side and server-side development. It is a versatile language that can be used to create a wide variety of applications, including web pages, mobile apps, and games.

Node.js is a runtime environment that allows developers to run JavaScript code outside of a web browser. This means that you can use JavaScript to write server-side applications, such as web servers, APIs, and command-line tools.

### The V8 Engine

The V8 engine is a high-performance JavaScript engine that is used by Google Chrome and Node.js. It is written in C++ and is designed to be fast and efficient. The V8 engine is responsible for compiling JavaScript code into machine code that can be executed by the computer.

### Node.js and Server-Side Scripting

Node.js uses JavaScript for server-side scripting. This means that you can use JavaScript to write code that runs on a server. This code can be used to handle HTTP requests, process data, and generate dynamic content.

Node.js is a popular choice for server-side scripting because it is fast, scalable, and easy to use. It is also a good choice for developers who are already familiar with JavaScript.

In the next section, we will explore the core concepts of Node.js, including its event loop, non-blocking I/O, callbacks, promises, streams, buffers, modules, and more. We will also set up a Node.js development environment and build a simple web server to solidify our understanding.

## Core Concepts of Node.js

In this section, we will explore the core concepts of Node.js, including its event loop, non-blocking I/O, callbacks, promises, streams, buffers, modules, and more. We will also set up a Node.js development environment and build a simple web server to solidify our understanding.

### Event Loop

The event loop is one of the most important concepts in Node.js. It is a mechanism that allows Node.js to handle multiple concurrent requests without blocking. The event loop works by continuously checking for new events, such as incoming HTTP requests, and then executing the appropriate callback function.

The event loop has six phases, each with a queue of callbacks to process. The phases are:

- **Timers**: This phase executes callbacks scheduled by `setTimeout()` and `setInterval()`.
- **Pending callbacks**: This phase executes I/O callbacks that were deferred to the next loop iteration.
- **Idle, prepare**: This phase is only used internally by the event loop for housekeeping purposes.
- **Poll**: This phase polls for new I/O events and executes the corresponding callbacks. This is where most of the asynchronous I/O operations are handled.
- **Check**: This phase executes callbacks registered by `setImmediate()`.
- **Close callbacks**: This phase executes callbacks related to closing events, such as `socket.on('close', ...)`.

The event loop does not run in a fixed order. Depending on the state of the system and the callbacks in the queues, the event loop may switch between phases or skip some phases altogether. For example, if the poll phase has no pending callbacks, the event loop may jump to the check phase or the timers phase, depending on the timers that are due.

The event loop is what makes Node.js fast and scalable. By delegating most of the I/O operations to the system kernel or the thread pool, Node.js can handle many requests with a single thread, without blocking or waiting for the I/O to complete. This allows Node.js to achieve high throughput and low latency for applications that are I/O intensive, such as web servers, chat applications, or real-time data processing.

### Non-Blocking I/O

Node.js uses non-blocking I/O, which means that it does not wait for I/O operations to complete before continuing execution. This allows Node.js to handle a large number of concurrent requests without blocking.

Non-blocking I/O is achieved by using asynchronous methods that take callback functions as arguments. These methods return immediately and do not block the execution of the rest of the code. The callback functions are executed later, when the I/O operation is finished, by the event loop.

For example, the `fs.readFile()` method is an asynchronous method that reads a file from the disk. It takes a callback function as the second argument, which is called when the file is read. The method does not block the execution of the code after it, and the callback function is executed in a future iteration of the event loop.

```js
// Non-blocking example
const fs = require('fs');

// This method does not block the execution
fs.readFile('file.txt', (err, data) => {
  if (err) throw err;
  // This callback function is executed later
  console.log(data.toString());
});

// This code runs before the callback function
console.log('Reading file...');
```

The advantage of non-blocking I/O is that it allows Node.js to handle many requests with a single thread, without wasting resources on waiting for I/O operations. This makes Node.js suitable for applications that are I/O intensive, such as web servers, chat applications, or real-time data processing.

### Callbacks

Callbacks are functions that are passed to other functions as arguments. When the other function is called, it will call the callback function. Callbacks are used extensively in Node.js to handle asynchronous operations.

Asynchronous operations are those that do not block the execution of the code and allow the program to continue while waiting for the result. For example, reading a file from the disk, making a network request, or querying a database are all asynchronous operations in Node.js.

Callbacks are a way of defining what to do when an asynchronous operation is completed. The callback function is usually the last argument of an asynchronous function, and it takes two parameters: an error object and a result object. The error object is null if the operation was successful, and the result object contains the data returned by the operation.

For example, the `fs.readFile()` function is an asynchronous function that reads a file from the disk and calls a callback function when it is done. The callback function can check the error object and handle it if it is not null, or print the result object if it is. Here is an example of using a callback with `fs.readFile()`:

```js
// Import the fs module
const fs = require('fs');

// Define a callback function
function readCallback(err, data) {
  // Check if there is an error
  if (err) {
    // Handle the error
    console.error(err);
  } else {
    // Print the data
    console.log(data.toString());
  }
}

// Call the readFile function with a file name and a callback
fs.readFile('file.txt', readCallback);
```

The advantage of using callbacks is that they allow us to write non-blocking code that can handle multiple concurrent requests without waiting for each one to finish. This makes Node.js fast and scalable for applications that are I/O intensive, such as web servers, chat applications, or real-time data processing.

However, callbacks also have some disadvantages, such as:

- They can lead to **callback hell**, which is a situation where the code becomes nested and indented too deeply, making it hard to read and maintain.
- They can cause **inversion of control**, which is a loss of control over the flow of the program, as the callback function depends on the behavior of the function that calls it.
- They can make **error handling** difficult, as each callback function needs to check and handle the error object, or pass it to another callback function.

To overcome these disadvantages, there are other ways of writing asynchronous code in Node.js, such as using promises, async/await, or event emitters.

### Promises

Promises are a newer way to handle asynchronous operations in Node.js. Promises are objects that represent the eventual completion (or failure) of an asynchronous operation. Promises can be used to chain together multiple asynchronous operations.

A promise has two possible outcomes: **fulfilled** or **rejected**. A fulfilled promise means that the operation was successful and the promise returns a value. A rejected promise means that the operation failed and the promise returns an error.

A promise can be created by using the `new Promise()` constructor, which takes a function as an argument. This function is called the **executor** and it has two parameters: `resolve` and `reject`. These are functions that can be used to settle the promise, either by fulfilling it with a value or rejecting it with an error.

For example, the following code creates a promise that simulates an asynchronous operation that takes one second to complete:

```js
// Create a promise
const myPromise = new Promise((resolve, reject) => {
  // Simulate an async operation
  setTimeout(() => {
    // Fulfill the promise with a value
    resolve('Hello, world!');
  }, 1000);
});
```

A promise can be **consumed** by using the `.then()` and `.catch()` methods, which register callbacks to handle the fulfillment or rejection of the promise. The `.then()` method takes a function that receives the value of the fulfilled promise as an argument. The `.catch()` method takes a function that receives the error of the rejected promise as an argument.

For example, the following code consumes the promise created above and prints the value or the error to the console:

```js
// Consume the promise
myPromise
  .then((value) => {
    // Handle the fulfillment
    console.log(value); // Hello, world!
  })
  .catch((error) => {
    // Handle the rejection
    console.error(error);
  });
```

A promise can also be **chained** by returning another promise from the `.then()` or `.catch()` callbacks. This allows us to perform multiple asynchronous operations in a sequence, passing the result of one promise to the next one.

For example, the following code chains two promises that each return a random number between 1 and 10. The second promise adds the two numbers and fulfills with the sum, or rejects if the sum is greater than 15.

```js
// Create a function that returns a promise with a random number
function getRandomNumber() {
  return new Promise((resolve, reject) => {
    // Generate a random number between 1 and 10
    const number = Math.floor(Math.random() * 10) + 1;
    // Fulfill the promise with the number
    resolve(number);
  });
}

// Chain two promises
getRandomNumber()
  .then((number1) => {
    // Print the first number
    console.log(number1);
    // Return another promise with the second number
    return getRandomNumber();
  })
  .then((number2) => {
    // Print the second number
    console.log(number2);
    // Add the two numbers
    const sum = number1 + number2;
    // Check if the sum is less than or equal to 15
    if (sum <= 15) {
      // Fulfill the promise with the sum
      resolve(sum);
    } else {
      // Reject the promise with an error
      reject(new Error('The sum is too big!'));
    }
  })
  .then((sum) => {
    // Print the sum
    console.log(sum);
  })
  .catch((error) => {
    // Print the error
    console.error(error);
  });
```

Promises are a powerful and elegant way to handle asynchronous operations in Node.js, as they avoid the problems of callback hell, inversion of control, and error handling that are common with callbacks. However, promises can still be complex and verbose, especially when dealing with nested or parallel promises. To simplify the syntax and readability of promises, Node.js also supports the `async/await` feature, which allows us to write asynchronous code in a synchronous-like manner.

### Streams

Streams are objects that represent a sequence of data. Streams are used extensively in Node.js to handle data that is being transferred over a network or from a file.

Streams can be **readable**, **writable**, **duplex**, or **transform**. A readable stream is a source of data that can be consumed by another stream or a callback function. A writable stream is a destination of data that can be written to by another stream or a function. A duplex stream is both readable and writable, such as a TCP socket. A transform stream is a duplex stream that can modify or transform the data as it is written and read, such as a compression or encryption stream.

Streams have many advantages over other ways of handling data, such as:

- They allow us to process data **incrementally** and **efficiently**, without waiting for the entire data to be available or loading it into memory.
- They enable us to **compose** complex operations by piping data from one stream to another, creating a data flow.
- They provide a **consistent** and **simple** interface for different types of data sources and destinations, such as files, network sockets, HTTP requests and responses, etc.

Node.js provides a built-in module called `stream` that contains the base classes and utilities for working with streams. Many of the core modules in Node.js also implement the stream interface, such as `fs`, `http`, `zlib`, `crypto`, etc.

To use streams in Node.js, we need to understand the following concepts:

- How to create and consume readable and writable streams using the `stream.Readable` and `stream.Writable` classes or their subclasses.
- How to pipe data between streams using the `.pipe()` method and handle backpressure and errors.
- How to create and use duplex and transform streams using the `stream.Duplex` and `stream.Transform` classes or their subclasses.
- How to use the utility functions `stream.pipeline()`, `stream.finished()`, and `stream.Readable.from()` to simplify working with streams.

### Buffers

Buffers are objects that represent a chunk of memory. Buffers are used to store data that is being transferred over a network or from a file.

Buffers are similar to arrays of integers, but they have a fixed size and can only store binary data. Buffers are useful for working with data that is not in a human-readable format, such as images, audio, video, or compressed data.

Buffers can be created in several ways, such as:

- Using the `Buffer.alloc()` method, which creates a new buffer of a specified size and optionally fills it with a given value.
- Using the `Buffer.from()` method, which creates a new buffer from an existing array, array buffer, string, or another buffer.
- Using the `Buffer.concat()` method, which creates a new buffer by concatenating a list of buffers.

Buffers have many methods and properties that allow us to manipulate and access the binary data, such as:

- The `buf.length` property, which returns the size of the buffer in bytes.
- The `buf[index]` syntax, which allows us to read and write a single byte at a given index.
- The `buf.slice()` method, which returns a new buffer that references the same memory as the original buffer, but with a different start and end position.
- The `buf.toString()` method, which converts the buffer to a string using a specified encoding, such as 'utf8', 'hex', or 'base64'.
- The `buf.write()` method, which writes a string to the buffer using a specified encoding and offset.
- The `buf.read*()` and `buf.write*()` methods, which allow us to read and write different types of numbers, such as integers, floats, or bigints, in big-endian or little-endian format.

### Modules

Modules are files that contain JavaScript code that can be reused in other JavaScript files. Modules are used to organize code and make it easier to reuse.

There are two types of modules in Node.js: **CommonJS modules** and **ECMAScript modules**. CommonJS modules are the original way to package JavaScript code for Node.js, using the `require()` and `module.exports` syntax. ECMAScript modules are the standard way to package JavaScript code for browsers and other JavaScript runtimes, using the `import` and `export` syntax.

Node.js supports both types of modules, but they have some differences and limitations, such as:

- CommonJS modules use dynamic module resolution, which means that the module identifier passed to `require()` can be a variable or an expression. ECMAScript modules use static module resolution, which means that the module specifier passed to `import` must be a string literal.
- CommonJS modules are loaded synchronously, which means that the code execution is blocked until the module is loaded. ECMAScript modules are loaded asynchronously, which means that the code execution can continue while the module is being loaded.
- CommonJS modules are executed in the order they are required, which means that the module code is run when it is first imported. ECMAScript modules are executed in the order they are imported, which means that the module code is run after all the imports are resolved.
- CommonJS modules have a circular dependency problem, which means that if two modules require each other, one of them will get an incomplete or undefined export. ECMAScript modules have a circular dependency solution, which means that if two modules import each other, they will get the correct export.

To use modules in Node.js, we need to understand the following concepts:

- How to create and export CommonJS modules using the `module.exports` or `exports` object.
- How to import and use CommonJS modules using the `require()` function.
- How to create and export ECMAScript modules using the `export` keyword or the `export default` syntax.
- How to import and use ECMAScript modules using the `import` keyword or the `import()` function.
- How to enable and configure ECMAScript modules in Node.js using the `.mjs` file extension, the `package.json` `"type"` field, or the `--input-type` or `--experimental-default-type` flags.
- How to interoperate between CommonJS and ECMAScript modules using the `import` statement, the `require()` function, or the `import.meta.require()` function.
- How to use the built-in modules in Node.js, such as `fs`, `http`, `crypto`, etc., which implement the stream interface and provide various utilities and functionalities.

In this section, we have explored the core concepts of Node.js, including its event loop, non-blocking I/O, callbacks, promises, streams, buffers, modules, and more. In the next section, we will set up a Node.js development environment and build a simple web server to solidify our understanding.


## Playground: Hands-On Experience with Node.js

In this section, we will engage in practical exercises to solidify our understanding of Node.js. We will build a simple web server, work with databases, create RESTful APIs, explore asynchronous programming, test and debug applications, and deploy Node.js projects.

### Building a Simple Web Server

To start, let's create a simple web server using Node.js. Open your terminal and navigate to the directory where you want to create your project. Then, run the following command to initialize a new Node.js project:

```
npm init -y
```

This command will create a `package.json` file, which contains information about your project.

Next, install the Express.js framework, a popular framework for building web applications in Node.js:

```
npm install express
```

Create a new file called `server.js` and add the following code:

```javascript
const express = require('express');

const app = express();

app.get('/', (req, res) => {
  res.send('Hello, world!');
});

app.listen(3000, () => {
  console.log('Server listening on port 3000');
});
```

This code creates a simple web server that listens on port 3000. When a client makes a GET request to the root URL (`/`), the server responds with the message "Hello, world!".

To start the server, run the following command:

```
node server.js
```

You should see the following output in your terminal:

```
Server listening on port 3000
```

Now, open your web browser and navigate to `http://localhost:3000`. You should see the message "Hello, world!" displayed in your browser.

### Working with Databases

Next, let's explore how to work with databases in Node.js. We will use MongoDB, a popular NoSQL database, for this purpose.

First, install the MongoDB driver for Node.js:

```
npm install mongodb
```

Create a new file called `database.js` and add the following code:

```javascript
const { MongoClient } = require('mongodb');

const client = new MongoClient('mongodb://localhost:27017');

async function connectToDatabase() {
  await client.connect();
  const db = client.db('my_database');
  const collection = db.collection('my_collection');

  // Insert a document into the collection
  const result = await collection.insertOne({ name: 'John Doe' });
  console.log(`Inserted document with ID: ${result.insertedId}`);

  // Find a document from the collection
  const foundDocument = await collection.findOne({ name: 'John Doe' });
  console.log(`Found document: ${JSON.stringify(foundDocument)}`);

  // Update a document in the collection
  const updateResult = await collection.updateOne({ name: 'John Doe' }, { $set: { age: 30 } });
  console.log(`Updated ${updateResult.modifiedCount} document(s)`);

  // Delete a document from the collection
  const deleteResult = await collection.deleteOne({ name: 'John Doe' });
  console.log(`Deleted ${deleteResult.deletedCount} document(s)`);

  await client.close();
}

connectToDatabase();
```

This code connects to a MongoDB database, inserts a document, finds a document, updates a document, and deletes a document.

To run this code, make sure you have a MongoDB server running on your local machine. Then, run the following command:

```
node database.js
```

You should see the following output in your terminal:

```
Inserted document with ID: 63974746f31c91a5a9d4411b
Found document: {"_id":"63974746f31c91a5a9d4411b","name":"John Doe"}
Updated 1 document(s)
Deleted 1 document(s)
```

### Building RESTful APIs

RESTful APIs are a popular way to expose data and functionality to other applications. Let's create a simple RESTful API using Node.js and Express.js.

In your `server.js` file, add the following code:

```javascript
const express = require('express');

const app = express();

app.get('/api/users', (req, res) => {
  res.json([{ id: 1, name: 'John Doe' }, { id: 2, name: 'Jane Doe' }]);
});

app.post('/api/users', (req, res) => {
  const newUser = req.body;
  // Save the new user to the database
  res.json(newUser);
});

app.put('/api/users/:id', (req, res) => {
  const updatedUser = req.body;
  // Update the user in the database
  res.json(updatedUser);
});

app.delete('/api/users/:id', (req, res) => {
  // Delete the user from the database
  res.json({ message: 'User deleted successfully' });
});

app.listen(3000, () => {
  console.log('Server listening on port 3000');
});
```

This code creates a RESTful API with four endpoints:

* `/api/users`: Get all users
* `/api/users`: Create a new user
* `/api/users/:id`: Update a user
* `/api/users/:id`: Delete a user

To test the API, you can use a tool like Postman or curl. For example, to get all users, you can send a GET request to `http://localhost:3000/api/users`.

### Exploring Asynchronous Programming

Asynchronous programming is a fundamental concept in Node.js. It allows Node.js to handle multiple requests concurrently without blocking.

Let's explore asynchronous programming by creating a simple Node.js script that fetches data from two different APIs concurrently.

Create a new file called `async.js` and add the following code:

```js
const axios = require('axios');

async function fetchUserData() {
  const user1 = await axios.get('https://api.github.com/users/octocat');
  const user2 = await axios.get('https://api.github.com/users/nodejs');

  console.log(`User 1: ${user1.data.login}`);
  console.log(`User 2: ${user2.data.login}`);
}

fetchUserData();
```

This code uses the `axios` library to make two API requests concurrently. The `await` keyword is used to wait for the API requests to complete before proceeding.


## Conclusion

In this blog post, we have covered a wide range of topics related to Node.js, from its history and evolution to its core concepts and practical applications. We have also explored the importance of Node.js in web development and its comparison with traditional server-side languages.

We have learned about the event loop, non-blocking I/O, callbacks, promises, streams, buffers, modules, and more. We have also set up a Node.js development environment and built a simple web server to solidify our understanding.

We have worked with databases, built resourceful APIs, and explored asynchronous programming.

We have provided many resources for further exploration, including books, tutorials, and online courses.

We encourage you to continue learning and experiment with Node.js. It is a versatile and powerful technology that can be used to build a wide variety of web applications.

We hope you found this blog post helpful. If you have any questions or comments, please feel free to reach out to us.

