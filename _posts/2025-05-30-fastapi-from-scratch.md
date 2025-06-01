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
    overlay_image:  /assets/images/fastapi-from-scratch/banner.png
    overlay_filter: 0.5
    teaser:  /assets/images/fastapi-from-scratch/banner.png
title: "Building a Modern Python Web Framework from Scratch: An In-Depth Guide"
tags:
    - Python
    - FastAPI
    - ASGI
    - Web Framework

---

FastAPI has rapidly gained popularity in the Python ecosystem for its remarkable performance and developer-friendly features. It elegantly combines asynchronous capabilities with Python's type hinting system to offer a robust platform for building APIs. But what truly makes FastAPI, and similar modern frameworks, function so effectively? This guide embarks on an investigative journey to construct a simplified FastAPI-like framework from its foundational principles, using pure Python. The goal is not to create a production-ready replacement but to demystify the internal mechanics, providing a deep, practical understanding of how these powerful tools are built.

By following this comprehensive exploration, developers will gain insights into:

* The pivotal transition from synchronous (WSGI) to asynchronous (ASGI) web communication in Python.  
* The core Asynchronous Server Gateway Interface (ASGI) protocol, including its scope, receive, and send mechanisms, and its event-driven architecture.  
* The complete request-to-response lifecycle within an asynchronous web framework.  
* The step-by-step implementation of essential framework components, such as routing, request parsing, and response generation.  
* The underlying principles that power features often perceived as "magic," like path operation decorators, type-hint-based data validation, and dependency injection.

The journey is structured to guide the reader from fundamental web server communication protocols to the implementation of sophisticated framework features, ultimately revealing that the "magic" of modern frameworks is built upon understandable and re-implementable principles. Developers often achieve true mastery not merely by using tools, but by comprehending their inner workings. The shift from WSGI to ASGI, for instance, represents a fundamental paradigm shift in Python web development, enabling a new generation of high-performance, I/O-bound applications. Understanding this transition is key to appreciating the design and capabilities of frameworks like FastAPI.

<div style="width: 100%; height: 800px; border: 1px solid #ddd; border-radius: 8px; overflow: hidden; margin: 20px 0;">
    <iframe 
        src="/assets/htmls/fastapi-from-scratch.html" 
        width="100%" 
        height="100%" 
        frameborder="0"
        style="border: none;">
        Your browser does not support iframes. 
        <a href="/assets/htmls/fec.html" target="_blank">View the interactive demo in a new window</a>
    </iframe>
</div>

<div style="text-align: center; margin: 10px 0 20px 0;">
    <a href="/assets/htmls/fastapi-from-scratch.html" target="_blank" 
       style="display: inline-block; 
              padding: 12px 24px; 
              background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
              color: white; 
              text-decoration: none; 
              border-radius: 6px; 
              font-weight: 500;
              box-shadow: 0 4px 15px rgba(0,0,0,0.2);
              transition: all 0.3s ease;
              font-size: 14px;"
       onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 20px rgba(0,0,0,0.3)';"
       onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 15px rgba(0,0,0,0.2)';">
        🔗 Open Interactive Demo in Full Page
    </a>
</div>

## Part 1: Foundations - Understanding the Web and Asynchronous Python

### The Gateway Interfaces: WSGI and ASGI – The Lingua Franca of Python Web Servers

At the heart of how Python web applications communicate with web servers lie two crucial specifications: the Web Server Gateway Interface (WSGI) and its successor, the Asynchronous Server Gateway Interface (ASGI). These interfaces define a standard contract, allowing for interoperability between different servers and application frameworks.

#### WSGI (Web Server Gateway Interface): The Synchronous Predecessor

WSGI, formalized in PEP 333 and later updated by PEP 3333, established a standard interface between web servers and Python web applications for synchronous programming. Historically, it was a significant development, as it allowed developers to choose and combine various web servers (like Gunicorn, uWSGI, or Apache with mod\_wsgi) and web frameworks (like Flask or Django in their WSGI modes) without worrying about custom integration code.

**How WSGI Works: The WSGI Callable**

The core of a WSGI application is a callable object—this can be a function, a method, or a class instance with a __call__ method. This callable must accept two arguments:

1. environ: A dictionary containing environment variables. This dictionary is similar to those used in Common Gateway Interface (CGI) and provides the application with details about the incoming request, such as the HTTP method (REQUEST_METHOD), path (PATH_INFO), query string (QUERY_STRING), headers (prefixed with HTTP_), client address, server information, and a file-like object for reading the request body (wsgi.input).  
2. start_response: A callable provided by the server. The application *must* invoke this callable before returning the first chunk of the response body. It takes two required arguments: the HTTP status string (e.g., '200 OK', '404 Not Found') and a list of HTTP header tuples (header_name, header_value) (e.g., []).

The WSGI application callable must then return an iterable (e.g., a list) that yields byte strings. These byte strings collectively form the body of the HTTP response.

**A Simple WSGI "Hello, World!" Application**

Consider the following example of a minimal WSGI application:

```python
# wsgi_app.py  
def application(environ, start_response):  
    status = '200 OK'  
    headers = [('Content-type', 'text/plain')]  
    start_response(status, headers)  
      
    path = environ.get('PATH_INFO', '/')  
    response_body = f"Hello from WSGI! You requested: {path}".encode('utf-8')  
      
    return [response_body]

# To run this with a simple server (e.g., Gunicorn):  
# gunicorn wsgi_app:application
```

In this example, the application function defines the status and headers, calls start_response, and returns a list containing a single byte string as the response body. The environ dictionary is used to access the request path.

The design of WSGI, particularly the start_response callable and the iterable response body, implies a specific sequence: headers must be sent before any part of the body. Once start_response is called and the application starts yielding body chunks, the status and headers are considered fixed. This characteristic is a key differentiator from more flexible protocols. Furthermore, the environ dictionary provides most request information upfront, with the request body typically accessed as a synchronous, file-like stream via environ['wsgi.input'].

**Limitations in the Asynchronous Era**

WSGI's synchronous, blocking nature means that a single worker process (or thread) can typically handle only one request at a time. For I/O-bound operations (like waiting for database queries, external API calls, or network operations), this leads to the worker being idle, unable to process other incoming requests. This model is inefficient for applications requiring high concurrency or features like WebSockets, which involve long-lived, bidirectional connections that don't fit neatly into WSGI's strict request/response cycle.

#### ASGI (Asynchronous Server Gateway Interface): Embracing Asynchronicity

ASGI emerged as the spiritual successor to WSGI, designed specifically for Python's async and await syntax to enable asynchronous web applications. It provides a standard interface for communication between asynchronous-capable web servers and Python applications. ASGI supports both asynchronous and synchronous applications (the latter typically through an adapter library like asgiref) and can handle a variety of protocols beyond simple HTTP, including WebSockets and HTTP/2.

**The ASGI Application Signature**

An ASGI application is an async callable that conforms to the following signature:  
```python
async def application(scope: dict, receive: Callable, send: Callable) -> None:  
```
This application callable is instantiated by the server once per "connection." A connection's lifetime depends on the protocol; for HTTP, it's typically a single request-response cycle, but for WebSockets, it's the entire duration the socket remains open.

**Core Concepts In-depth - The ASGI Triad**

ASGI communication revolves around three key components provided by the server to the application:

1. **scope (dictionary)**:  
   * **Role**: The scope dictionary contains information about the incoming connection. It is established when the connection is initiated and persists for the duration of that connection.  
   * **Essential Keys**:  
     * type (string): This is a critical key that specifies the protocol of the connection (e.g., "http", "websocket", or "lifespan"). The value of type dictates the expected structure of the rest of the scope dictionary and the types of messages that will be exchanged via receive and send.  
     * asgi (dictionary): This sub-dictionary provides ASGI versioning information, such as {'version': '3.0', 'spec_version': '2.3'} (indicating ASGI version 3.0 and HTTP/WebSocket spec version 2.3).  
   * **HTTP-Specific scope Keys**: For an HTTP connection (scope['type'] == 'http'), common keys include:  
     * method (string): The HTTP method (e.g., "GET", "POST").  
     * scheme (string): The URL scheme (e.g., "http", "https").  
     * path (string): The request path (e.g., "/users/info").  
     * raw_path (bytes): The undecoded, raw path.  
     * query_string (bytes): The portion of the URL after the ? (e.g., b"name=alice&limit=10").  
     * headers (list of [bytes, bytes]): A list of [name, value] pairs representing HTTP headers. Header names are lowercased byte strings.  
     * client (tuple [str, int]): The client's network address (host, port).  
     * server (tuple [str, Optional[int]]): The server's network address (host, port).  
     * http_version (string): E.g., "1.1", "2".  
   * **Contrast with WSGI environ**: Unlike environ, the HTTP request body is *not* included in the initial scope. It is streamed via the receive channel. The scope is more structured and explicitly protocol-aware due to the type key.  
2. **receive (awaitable callable)**:  
   * **Role**: An async function that the application calls (and awaits) to receive event messages from the server. Each call to await receive() will pause the application's execution until a new event message is available from the client or server.  
   * **HTTP Request Body Event**: For HTTP requests, the body is streamed through one or more messages of type http.request. Each such message is a dictionary like: {'type': 'http.request', 'body': b'...bytes...', 'more_body': True/False}  
     * body: A byte string containing a chunk of the request body.  
     * more_body: A boolean. If True, more body chunks are expected. If False, this is the final (or only) chunk of the request body. This mechanism is crucial for efficiently handling large request bodies by streaming them.  
   * **Other Event Types**: For WebSockets, an application might await receive() to get a websocket.receive message containing incoming data. An http.disconnect message indicates the client has closed the HTTP connection.  
3. **send (awaitable callable)**:  
   * **Role**: An async function that the application calls (and awaits) to send event messages to the server, which then forwards them to the client.  
   * **HTTP Response Events**: To send an HTTP response, the application typically sends two types of messages in sequence:  
     * {'type': 'http.response.start', 'status': int, 'headers': [[b'name', b'value'],...]: This message is sent once at the beginning of the response. It includes the HTTP status code (e.g., 200, 404) and a list of header pairs (name and value as byte strings).  
     * {'type': 'http.response.body', 'body': b'...bytes...', 'more_body': True/False}: This message is sent one or more times to transmit the response body.  
       * body: A byte string containing a chunk of the response body.  
       * more_body: A boolean. If True, the application will send more body chunks. If False, this is the final (or only) chunk, and the server can consider the response complete. This allows for streaming responses.

The scope can be seen as establishing the context of a connection, while receive and send are the bidirectional channels for event-based communication within that context. This separation and event-driven model are what grant ASGI its flexibility to support diverse and long-lived protocols, a significant advancement over WSGI's more rigid request-response structure. The more_body flag, present in both request and response body events, is the explicit mechanism that enables efficient streaming of large payloads, preventing the need to buffer entire bodies in memory.

**Event-Driven Model**

ASGI is fundamentally event-driven. The application code is structured to react to incoming events (received via await receive()) and to produce outgoing events (sent via await send()). This asynchronous, message-passing paradigm is a core distinction from WSGI's synchronous, function-call-and-return model.

**Application Lifecycle (lifespan protocol)**

ASGI defines a special "lifespan" protocol to manage application startup and shutdown events gracefully.

* When the server starts, it may initiate a lifespan connection by calling the application with scope['type'] == 'lifespan'.  
* The application then expects to receive a {'type': 'lifespan.startup'} message. Upon receiving this, it can perform any necessary initialization (e.g., establishing database connection pools, loading machine learning models). Once complete, it must send either {'type': 'lifespan.startup.complete'} or {'type': 'lifespan.startup.failed'} if initialization fails.  
* Similarly, when the server is shutting down, it will send a {'type': 'lifespan.shutdown'} message. The application should then perform cleanup tasks (e.g., closing database connections, releasing resources) and send {'type': 'lifespan.shutdown.complete'} or {'type': 'lifespan.shutdown.failed'}.

This standardized lifecycle management was often handled in ad-hoc ways by WSGI servers and applications, but in ASGI, it's a first-class part of the specification, leading to more robust and predictable application behavior.

**A Simple "Hello, ASGI!" Application**

Here's a minimal ASGI application demonstrating these concepts:

```python
# asgi_app.py  
async def application(scope, receive, send):  
    if scope['type'] == 'http':  
        # For an HTTP request, send a simple response  
        await send({  
            'type': 'http.response.start',  
            'status': 200,  
            'headers': [b'content-type', b'text/plain'],  
                [b'content-length', b'13'],  
        })  
        await send({  
            'type': 'http.response.body',  
            'body': b'Hello, ASGI!',  
            'more_body': False, # This is the only body chunk  
        })  
    elif scope['type'] == 'lifespan':  
        while True:  
            message = await receive()  
            if message['type'] == 'lifespan.startup':  
                print("ASGI App: Lifespan startup...")  
                # Perform app startup tasks here  
                await send({'type': 'lifespan.startup.complete'})  
                print("ASGI App: Lifespan startup complete.")  
            elif message['type'] == 'lifespan.shutdown':  
                print("ASGI App: Lifespan shutdown...")  
                # Perform app shutdown tasks here  
                await send({'type': 'lifespan.shutdown.complete'})  
                print("ASGI App: Lifespan shutdown complete.")  
                return # End lifespan handling  
    # Other scope types (e.g., 'websocket') could be handled here

# To run this with Uvicorn:  
# uvicorn asgi_app:application --reload
```

This example shows the basic structure for handling HTTP requests and the lifespan protocol.

The following table summarizes the key differences between WSGI and ASGI:

| Feature | WSGI (Web Server Gateway Interface) | ASGI (Asynchronous Server Gateway Interface) |
| :---- | :---- | :---- |
| **Primary Goal** | Standard interface for synchronous Python web apps & servers. | Standard interface for asynchronous (and synchronous) Python web apps & servers. |
| **Programming Model** | Synchronous, blocking. | Asynchronous, non-blocking (async/await). |
| **Application Signature** | application(environ, start_response) | async def application(scope, receive, send) |
| **Protocol Support** | Primarily HTTP. Limited for long-lived connections (WebSockets). | HTTP, HTTP/2, WebSockets, and other protocols. Designed for multiple event types. |
| **Request Handling** | Single request-response cycle per call. | Connection-oriented; can handle multiple events over a single connection (e.g., WebSocket messages). |
| **Request Body** | Typically in environ['wsgi.input'] as a synchronous stream. | Streamed via await receive() as http.request events with more_body flag. |
| **Response Body** | Returned as an iterable of byte strings after start_response. | Sent via await send() as http.response.body events with more_body flag. |
| **Concurrency** | Achieved via threads or multiple processes. | Achieved via asynchronous event loop, enabling high concurrency for I/O-bound tasks. |
| **Lifecycle Events** | No standardized application lifecycle events. | Standardized lifespan protocol for startup and shutdown events. |

This table highlights how ASGI addresses the limitations of WSGI for modern, high-concurrency web applications.

#### Uvicorn: The ASGI Server

An ASGI server is the runtime environment that hosts an ASGI application. It is responsible for handling network connections (e.g., listening on a TCP port), parsing incoming raw byte streams according to network protocols (like HTTP or WebSocket), translating these into the ASGI scope dictionary and event messages, and then invoking the ASGI application with these inputs. When the application sends event messages back via the send callable, the ASGI server translates these into the appropriate network protocol data and transmits them to the client.

**Uvicorn Specifics**

Uvicorn is a lightning-fast ASGI server, widely used and often recommended for running FastAPI applications. Its performance characteristics stem from its use of uvloop and httptools.

* **uvloop**: This is a high-performance, drop-in replacement for Python's built-in asyncio event loop. uvloop is built on libuv, the same library that provides the event loop for Node.js, and this contributes significantly to Uvicorn's speed and efficiency in handling asynchronous operations. The choice of event loop implementation can directly influence an ASGI server's performance, making uvloop a key advantage for Uvicorn.  
* **httptools**: Uvicorn uses the httptools library for parsing HTTP messages. This library is known for its speed in processing raw HTTP requests and converting them into a structured format that can be easily translated into ASGI http.request events.

To run an ASGI application (e.g., saved in my_app.py with the application callable named app), the command is typically:  

```bash
uvicorn my_app:app --reload  
```

Here, my_app refers to the Python file (my_app.py), and app is the name of the ASGI application instance within that file. The --reload flag instructs Uvicorn to monitor for code changes and automatically restart the server, which is highly convenient during development.  
Uvicorn supports HTTP/1.1, HTTP/2, and WebSockets, translating client interactions over these protocols into the standardized ASGI message format for the application to consume.

For more control, especially in production environments, Uvicorn can also be run programmatically:

```python
import uvicorn

if __name__ == "__main__":  
    uvicorn.run("my_app:app", host="0.0.0.0", port=8000, log_level="info")
```

This allows for finer-grained configuration.

It's important to understand that the ASGI application code itself does not deal with low-level network operations like managing sockets or parsing raw HTTP byte streams; these are the responsibilities of the ASGI server. While the --reload flag is useful for development, production deployments often involve a process manager like Gunicorn to manage Uvicorn worker processes. A common pattern is gunicorn -k uvicorn.workers.UvicornWorker my_app:app, which combines Gunicorn's robust process management features with Uvicorn's high-performance asynchronous request handling. This setup provides both scalability and resilience.

### Our First "Framework": A Basic ASGI App Structure

Having explored the foundational ASGI protocol, the next step is to create the basic structure for our custom framework. This initial version will be a simple class that acts as an ASGI application, capable of handling the essential lifespan protocol and responding to basic HTTP requests.

**The Framework Class: MyMiniFastAPI**

```python
# my_framework.py  
import json # For pretty printing scope later

class MyMiniFastAPI:  
    def __init__(self):  
        self.routes =  # Placeholder for routing table  
        print("MyMiniFastAPI instance created. Ready to handle connections.")

    async def __call__(self, scope: dict, receive: callable, send: callable):  
        # This method makes instances of MyMiniFastAPI callable,  
        # fulfilling the ASGI application interface.  
        # print(f"Connection scope received: {json.dumps(scope, indent=2)}") # Detailed scope logging

        if scope['type'] == 'lifespan':  
            await self.handle_lifespan(scope, receive, send)  
        elif scope['type'] == 'http':  
            await self.handle_http(scope, receive, send)  
        elif scope['type'] == 'websocket':  
            # Placeholder for future WebSocket handling  
            print(f"WebSocket connection received from {scope.get('client')}. Path: {scope.get('path')}. Not yet implemented.")  
            # A minimal WebSocket app should at least accept and close, or just close.  
            # For now, we'll let the server handle it if we don't process messages.  
            # Example: await self.handle_websocket(scope, receive, send)  
            pass # Or raise NotImplementedError if we want to be strict  
        else:  
            print(f"Unsupported scope type: {scope['type']}")  
            # Optionally, raise an error to indicate an unsupported protocol  
            # raise NotImplementedError(f"Scope type {scope['type']} not supported.")

    async def handle_lifespan(self, scope: dict, receive: callable, send: callable):  
        print("Lifespan handler initiated.")  
        while True:  
            message = await receive()  
            print(f"Lifespan message received: {message['type']}")  
            if message['type'] == 'lifespan.startup':  
                # Perform any application startup tasks here  
                # (e.g., initialize database connections, load ML models)  
                print("Framework: Lifespan startup sequence initiated...")  
                # Example: await self.initialize_database()  
                await send({'type': 'lifespan.startup.complete'})  
                print("Framework: Lifespan startup complete message sent.")  
            elif message['type'] == 'lifespan.shutdown':  
                # Perform any application shutdown tasks here  
                # (e.g., close database connections, release resources)  
                print("Framework: Lifespan shutdown sequence initiated...")  
                # Example: await self.cleanup_database()  
                await send({'type': 'lifespan.shutdown.complete'})  
                print("Framework: Lifespan shutdown complete message sent.")  
                return # Exit the lifespan handling loop

    async def handle_http(self, scope: dict, receive: callable, send: callable):  
        # This method will be significantly expanded with routing,  
        # request objects, and response objects in subsequent sections.  
        print(f"HTTP Request received: {scope['method']} {scope['path']}")  
          
        # For now, send a very basic "Hello World" response for any HTTP request  
        response_body_content = b'Hello from MyMiniFastAPI!'  
        response_headers = [b'content-type', b'text/plain'],  
            [b'content-length', str(len(response_body_content)).encode('utf-8')]  
          
        await send({  
            'type': 'http.response.start',  
            'status': 200,  
            'headers': response_headers,  
        })  
        print("HTTP Response Start sent.")  
          
        await send({  
            'type': 'http.response.body',  
            'body': response_body_content,  
            'more_body': False # Indicating this is the complete body  
        })  
        print("HTTP Response Body sent.")

# Create an instance of our framework. This 'app' is what Uvicorn will run.  
app = MyMiniFastAPI()

```

**Explanation:**

* **__init__(self)**: The constructor initializes an empty list self.routes, which will later store our routing rules.  
* **__call__(self, scope, receive, send)**: This special method makes instances of MyMiniFastAPI callable, which is the fundamental requirement for an ASGI application. It acts as the main entry point for incoming connections.  
  * It inspects scope['type'] to determine the nature of the connection (lifespan, HTTP, WebSocket, etc.).  
  * Based on the type, it dispatches to a specific handler method (handle_lifespan, handle_http). This dispatching based on scope['type'] is a fundamental pattern for ASGI applications designed to handle multiple protocols or concerns.  
* **handle_lifespan(self, scope, receive, send)**: This asynchronous method correctly implements the ASGI lifespan protocol.  
  * It enters a loop to await receive() messages from the server.  
  * If a lifespan.startup message is received, it simulates startup procedures and sends lifespan.startup.complete back to the server.  
  * If a lifespan.shutdown message is received, it simulates cleanup procedures, sends lifespan.shutdown.complete, and then returns, effectively ending the lifespan handling.  
  * Properly handling the lifespan protocol is crucial for an ASGI application to integrate correctly with the server, allowing for resource initialization at startup and graceful cleanup at shutdown.  
* **handle_http(self, scope, receive, send)**: This method is currently a placeholder for full HTTP request processing.  
  * It prints information about the incoming HTTP request.  
  * It sends a hardcoded "Hello from MyMiniFastAPI!" response. This involves sending two ASGI messages:  
    1. http.response.start: Contains the status code (200) and headers (Content-Type and Content-Length).  
    2. http.response.body: Contains the actual response content as bytes. more_body: False indicates that this is the complete response body.  
* **app = MyMiniFastAPI()**: An instance of our framework class is created. This app object is what an ASGI server like Uvicorn will interact with.

**Running with Uvicorn**

To run this basic framework, save the code as my_framework.py and execute the following command in the terminal:  

```bash
uvicorn my_framework:app --reload  
```

Upon starting, Uvicorn will first interact with the application using the lifespan protocol. The console output should show messages from MyMiniFastAPI instance created, followed by lifespan startup messages. If a web browser is then pointed to http://127.0.0.1:8000, the handle_http method will be invoked, printing request details and sending the "Hello from MyMiniFastAPI!" response. The browser will display this text. The server logs will also show the lifespan shutdown messages when Uvicorn is terminated (e.g., with Ctrl+C).

This initial structure forms the skeleton upon which more sophisticated features like routing, request parsing, and response generation will be built. It demonstrates the fundamental interaction between an ASGI server and an ASGI application.

### Routing: Directing Traffic

With the basic ASGI application structure in place, the next critical component is routing. Routing is the mechanism that determines how an application responds to a client request for a specific endpoint, typically defined by a URL path and an HTTP method.25

#### Principles of Web Routing

In web frameworks, routing involves mapping an incoming request's URL and HTTP method to a specific piece of code—a handler function or method—that will process the request and generate a response. This is akin to a telephone switchboard operator directing incoming calls to the correct department based on the number dialed and the purpose of the call.

The key components that define a route are:

* **URL Path**: The specific path component of the URL (e.g., /, /users, /items/123).  
* **HTTP Method**: The method used for the request (e.g., GET, POST, PUT, DELETE, PATCH). A single URL path can have different handlers for different HTTP methods.
* **Handler Function**: The Python function or method designated to execute when a request matches the path and method.

An effective routing system is essential for creating well-structured and maintainable web applications and APIs. It forms the primary contract with clients, and clear, consistent URL structures make an API intuitive to use and navigate.

#### Implementing a Simple Router

Our framework will manage routes by storing them in a list, a strategy similar to that used by Starlette. Each route entry will contain the path, the handler function, and the HTTP methods it supports.

**Adding Routes to MyMiniFastAPI**

First, an add_route method is needed in the MyMiniFastAPI class to register routes:

```python
# In MyMiniFastAPI class
import re # Will be used for dynamic routing later

#... (previous __init__ and __call__, handle_lifespan)...

    def add_route(self, path: str, handler: callable, methods: list = None):
        if methods is None:
            methods =  # Default to GET if no methods specified
        
        # Ensure methods are uppercase for consistent matching
        processed_methods = [method.upper() for method in methods]
        
        self.routes.append({
            "path": path,
            "handler": handler,
            "methods": processed_methods,
            "is_dynamic": "{" in path and "}" in path, # Basic check for dynamic path
            "path_regex": None, # Will store compiled regex for dynamic paths
            "param_names": # Will store param names for dynamic paths
        })
        print(f"Route added: Path='{path}', Handler='{handler.__name__}', Methods={processed_methods}")
```

**Modifying handle_http for Routing Logic**

The handle_http method needs to be updated to iterate through the registered routes, find a match based on the request's path and method, and then call the appropriate handler.

```python
# In MyMiniFastAPI class

#... (previous methods)...

    async def handle_http(self, scope: dict, receive: callable, send: callable):
        request_path = scope['path']
        request_method = scope['method']
        print(f"HTTP Request: Attempting to route {request_method} {request_path}")

        matched_route = None
        path_params = {}

        for route_entry in self.routes:
            # For now, simple string matching for static paths
            # Dynamic routing will be added in the next section
            if not route_entry["is_dynamic"]: # Simple static path matching
                if route_entry['path'] == request_path and request_method in route_entry['methods']:
                    matched_route = route_entry
                    break
            # Placeholder for dynamic route matching logic to be added later
            # else:
            #   match = re.match(route_entry['path_regex'], request_path)
            #   if match and request_method in route_entry['methods']:
            #       matched_route = route_entry
            #       path_params = match.groupdict()
            #       break


        if matched_route:
            handler = matched_route['handler']
            print(f"Routing to handler: {handler.__name__} for {request_method} {request_path}")
            
            # The way handlers are called and responses are constructed will be refined
            # when we introduce Request and Response objects.
            # For now, assume handlers are async and return a string response body.
            # And path_params will be passed to handler later.
            try:
                # This will be: response_content = await handler(request_object, **path_params)
                response_content_str = await handler(**path_params) 
                status_code = 200
                content_type = b'text/plain' # Default, will be improved
                response_body_bytes = response_content_str.encode('utf-8')

            except Exception as e:
                print(f"Error in handler {handler.__name__}: {e}")
                status_code = 500
                response_content_str = "Internal Server Error"
                content_type = b'text/plain'
                response_body_bytes = response_content_str.encode('utf-8')

            response_headers = [b'content-type', content_type],
                [b'content-length', str(len(response_body_bytes)).encode('utf-8')]

            await send({
                'type': 'http.response.start',
                'status': status_code,
                'headers': response_headers,
            })
            await send({
                'type': 'http.response.body',
                'body': response_body_bytes,
                'more_body': False
            })
            print(f"Response sent for {request_method} {request_path}")
            return

        # No route matched - send 404
        print(f"No route found for {request_method} {request_path}. Sending 404.")
        response_body_404 = b'Not Found'
        response_headers_404 = [b'content-type', b'text/plain'],
            [b'content-length', str(len(response_body_404)).encode('utf-8')]
        await send({
            'type': 'http.response.start',
            'status': 404,
            'headers': response_headers_404,
        })
        await send({
            'type': 'http.response.body',
            'body': response_body_404,
            'more_body': False
        })
```

**Example Usage with Static Routes:**

```python
# At the bottom of my_framework.py
app = MyMiniFastAPI()

async def home_handler():
    return "Welcome to the MyMiniFastAPI Home Page!"

async def about_handler():
    return "This is the About Page for MyMiniFastAPI."

async def contact_handler_post():
    # This handler would typically process form data from the request body
    return "Contact form submitted (POST request)!"

app.add_route("/", home_handler, methods=)
app.add_route("/about", about_handler, methods=)
app.add_route("/contact", contact_handler_post, methods=)

# To test:
# uvicorn my_framework:app --reload
# Then, in your browser:
#   GET http://127.0.0.1:8000/        -> "Welcome to the MyMiniFastAPI Home Page!"
#   GET http://127.0.0.1:8000/about   -> "This is the About Page for MyMiniFastAPI."
# To test POST, use a tool like curl or Postman:
#   curl -X POST http://127.0.0.1:8000/contact -> "Contact form submitted (POST request)!"
#   GET http://127.0.0.1:8000/contact   -> Will result in a 404 (or 405 if we implement it) 
#                                             because no GET handler is defined for /contact.
```

This simple router iterates through the list of routes. For static paths, it performs a direct string comparison of the path and checks if the request method is allowed for that route. If a match is found, the corresponding handler is executed. If no route matches, a 404 "Not Found" response is sent. This linear search approach is straightforward to implement but has a time complexity of O(N) for N routes. For a very large number of routes, more sophisticated data structures like Radix trees or Tries can offer better performance, though they add implementation complexity. Starlette itself uses a list and matches routes in the order they are defined, which is suitable for many applications.

#### Dynamic Routing and Path Parameters

Static paths are insufficient for many real-world applications where parts of the URL need to be variable, such as retrieving a user by their ID (/users/{user_id}) or an item by its slug (/products/{product_slug}). This requires dynamic routing, where the framework can extract these variable segments, known as path parameters, and pass them to the handler function.

**Approach: Using Named Placeholders and Regular Expressions**

Our framework will adopt a common syntax for defining path parameters, such as /items/{item_id}. Internally, these path strings will be converted into regular expressions to enable matching and extraction of parameter values. For instance:

* /items/{item_id} could be translated to the regex ^/items/(?P<item_id>[^/\]+)$.  
  * ^ and $ anchor the regex to the start and end of the path.  
  * (?P<item_id>...) creates a named capture group called item_id.  
  * \[^/\]+ matches one or more characters that are not a slash. This is a common default for path parameters.  
* To support type-like converters similar to Starlette's {param:converter} (e.g., {item_id:int} or {filepath:path}), we can extend this. For example:  
  * /items/{item_id:int} could become ^/items/(?P<item_id>\d+)$ (matching digits).  
  * /files/{filepath:path} could become ^/files/(?P<filepath>.*)$ (matching any characters, including slashes).

**Updating add_route for Dynamic Paths**

The add_route method needs to be enhanced to parse these path strings, generate the corresponding regex, and store parameter names.

```python
# In MyMiniFastAPI class
# (ensure 'import re' is at the top of the file)

    def _compile_path(self, path: str):
        """
        Converts a path string with placeholders like {name} or {name:type}
        into a regex pattern and extracts parameter names and their types.
        """
        param_names =
        path_regex_parts = ["^"] # Start of string anchor
        
        segments = path.split('/')
        for i, segment in enumerate(segments):
            if not segment: # Handles leading/trailing slashes or multiple slashes
                if i == 0 or i == len(segments) -1: # Allow leading/trailing slash in regex
                    continue 
                else: # Treat empty segment between slashes as literal empty segment (unlikely)
                    path_regex_parts.append("/") 
                    continue

            if segment.startswith("{") and segment.endswith("}"):
                param_descriptor = segment[1:-1]
                param_name = param_descriptor
                converter_type = "str" # Default converter

                if ':' in param_descriptor:
                    param_name, converter_type = param_descriptor.split(':', 1)
                
                param_names.append(param_name)

                if converter_type == "int":
                    path_regex_parts.append(f"(?P<{param_name}>\\d+)")
                elif converter_type == "path":
                    path_regex_parts.append(f"(?P<{param_name}>.+)") # Matches one or more of anything
                elif converter_type == "str": # Default string match (no slashes)
                    path_regex_parts.append(f"(?P<{param_name}>[^/]+)")
                else: # Unknown converter, treat as string for now or raise error
                    print(f"Warning: Unknown converter type '{converter_type}' for param '{param_name}'. Defaulting to string match.")
                    path_regex_parts.append(f"(?P<{param_name}>[^/]+)")
            else:
                path_regex_parts.append(re.escape(segment)) # Escape literal parts
            
            if i < len(segments) - 1 and segments[i+1]: # Add slash if not the last segment and next is not empty
                 path_regex_parts.append("/")
            elif i < len(segments) - 1 and not segments[i+1] and i!= len(segments) -2 : # if next is empty and its not the last segment
                 path_regex_parts.append("/")


        # Handle trailing slash: if original path ends with / and regex doesn't, add it.
        # Or if original path does not end with / but regex does, remove it unless it's just "^/$"
        if path.endswith("/") and not path_regex_parts[-1].endswith("/?") and path_regex_parts[-1]!= "^":
             if path_regex_parts[-1] == "/": # if last part is already a slash
                 path_regex_parts.append("?") # make it optional
             else:
                 path_regex_parts.append("/?") # Add optional trailing slash
        elif not path.endswith("/") and path_regex_parts[-1] == "/" and len(path_regex_parts) > 2 : # Path like /foo/
             path_regex_parts.pop()


        path_regex_parts.append("$") # End of string anchor
        
        final_regex_str = "".join(path_regex_parts)
        # Correct common issue: remove slash before $ if path is not "/"
        if final_regex_str.endswith("/$") and path!= "/" and not path.endswith("/"):
            final_regex_str = final_regex_str[:-2] + "$"
        if final_regex_str == "^/$": # Special case for root
            pass
        elif final_regex_str.endswith("//?$"): # Avoid double slashes from optional trailing
            final_regex_str = final_regex_str.replace("//?$", "/?$")


        # print(f"Original path: '{path}', Compiled regex: '{final_regex_str}', Params: {param_names}")
        return re.compile(final_regex_str), param_names

    def add_route(self, path: str, handler: callable, methods: list = None):
        if methods is None:
            methods =
        processed_methods = [method.upper() for method in methods]

        is_dynamic = "{" in path and "}" in path
        path_regex = None
        param_names =

        if is_dynamic:
            path_regex, param_names = self._compile_path(path)
        
        self.routes.append({
            "path_str": path, # Store original path string
            "handler": handler,
            "methods": processed_methods,
            "is_dynamic": is_dynamic,
            "path_regex": path_regex,
            "param_names": param_names
        })
        print(f"Route added: Path='{path}', Handler='{handler.__name__}', Methods={processed_methods}, Dynamic={is_dynamic}")
```

**Updating handle_http for Dynamic Matching**

The handle_http method now needs to differentiate between static and dynamic routes and use regex matching for the latter.

```python
# In MyMiniFastAPI class

#... (previous methods, including updated add_route and _compile_path)...

    async def handle_http(self, scope: dict, receive: callable, send: callable):
        request_path = scope['path']
        # Ensure request_path has a leading slash and no trailing slash (unless it's just "/")
        # This normalization helps in consistent matching with defined routes.
        if request_path!= '/' and request_path.endswith('/'):
            request_path = request_path.rstrip('/')
        if not request_path.startswith('/'): # Should always be true from ASGI server
            request_path = '/' + request_path


        request_method = scope['method']
        print(f"HTTP Request: Attempting to route {request_method} {request_path}")

        matched_route_info = None 
        path_params = {}

        for route_entry in self.routes:
            if request_method not in route_entry['methods']:
                continue # Skip if method doesn't match

            if route_entry["is_dynamic"]:
                match = route_entry['path_regex'].fullmatch(request_path) # Use fullmatch for exact path
                if match:
                    matched_route_info = route_entry
                    path_params = match.groupdict() # Extracts named parameters
                    # Attempt basic type conversion based on original path definition (simplified)
                    # Example: if path was /items/{item_id:int}, try to convert item_id
                    # This is a very simplified version of what Pydantic/FastAPI do with type hints
                    for param_name, value_str in path_params.items():
                        # This logic would be more robust by storing converter types in route_entry
                        # For now, a simple check if ':int' was in the original path segment
                        {% raw %}original_segment_placeholder = f"{{{param_name}:int}}"{% endraw %}
                        if original_segment_placeholder in route_entry["path_str"]:
                            try:
                                path_params[param_name] = int(value_str)
                            except ValueError:
                                # Handle conversion error - e.g., return 400 Bad Request
                                print(f"Path parameter type conversion error for '{param_name}': expected int, got '{value_str}'")
                                # This error handling should be more formal
                                await self._send_error_response(send, 400, "Bad Request: Invalid path parameter type")
                                return
                        # Add more converters like float, etc. if needed
                    break 
            else: # Static path matching
                # Normalize defined static path for matching (remove trailing slash if not root)
                defined_path = route_entry['path_str']
                if defined_path!= '/' and defined_path.endswith('/'):
                    defined_path = defined_path.rstrip('/')
                
                if defined_path == request_path:
                    matched_route_info = route_entry
                    break
        
        if matched_route_info:
            handler = matched_route_info['handler']
            print(f"Routing to handler: {handler.__name__} for {request_method} {request_path} with params {path_params}")
            
            try:
                # Pass extracted path_params to the handler
                # Ensure handler function is defined to accept these as keyword arguments
                response_content_str = await handler(**path_params)
                status_code = 200
                content_type = b'text/plain' 
                response_body_bytes = response_content_str.encode('utf-8')

            except TypeError as e: # Handles cases where handler doesn't accept the params
                 print(f"Handler argument mismatch for {handler.__name__}: {e}")
                 status_code = 500
                 response_content_str = "Internal Server Error: Handler argument mismatch"
                 content_type = b'text/plain'
                 response_body_bytes = response_content_str.encode('utf-8')

            except Exception as e:
                print(f"Error in handler {handler.__name__}: {e}")
                status_code = 500
                response_content_str = "Internal Server Error"
                content_type = b'text/plain'
                response_body_bytes = response_content_str.encode('utf-8')
            
            #... (rest of response sending logic from previous handle_http)
            response_headers = [b'content-type', content_type],
                [b'content-length', str(len(response_body_bytes)).encode('utf-8')]

            await send({
                'type': 'http.response.start',
                'status': status_code,
                'headers': response_headers,
            })
            await send({
                'type': 'http.response.body',
                'body': response_body_bytes,
                'more_body': False
            })
            print(f"Response sent for {request_method} {request_path}")
            return

        # No route matched or method not allowed for matched path
        # (Currently, method check is done before matching. If a path matches but method doesn't,
        # it will fall through to 404. A 405 Method Not Allowed would be more appropriate
        # if path matches but method is wrong for *any* handler on that path.)
        print(f"No route found for {request_method} {request_path}. Sending 404.")
        await self._send_error_response(send, 404, "Not Found")

    async def _send_error_response(self, send: callable, status_code: int, message: str):
        body_bytes = message.encode('utf-8')
        headers = [b'content-type', b'text/plain'],
            [b'content-length', str(len(body_bytes)).encode('utf-8')]
        await send({
            'type': 'http.response.start',
            'status': status_code,
            'headers': headers,
        })
        await send({
            'type': 'http.response.body',
            'body': body_bytes,
            'more_body': False
        })
```


**Example Usage with Dynamic Routes**

```python
# At the bottom of my_framework.py
app = MyMiniFastAPI()

async def get_user_details(username: str): # Handler expects 'username'
    return f"Details for user: {username}"

async def get_item_info(item_id: int): # Handler expects 'item_id' as int
    # The router will attempt to convert item_id to int due to ':int'
    return f"Information for item ID: {item_id} (type: {type(item_id).__name__})"

async def get_file_content(filepath: str):
    return f"Content of file at path: {filepath}"

app.add_route("/users/{username}", get_user_details, methods=)
app.add_route("/items/{item_id:int}", get_item_info, methods=) # Using :int converter
app.add_route("/files/{filepath:path}", get_file_content, methods=) # Using :path converter
app.add_route("/fixed/path", async def() : return "This is a fixed path.", methods=)


# To test:
# uvicorn my_framework:app --reload
# Then, in your browser:
#   GET http://127.0.0.1:8000/users/alice      -> "Details for user: alice"
#   GET http://127.0.0.1:8000/items/123        -> "Information for item ID: 123 (type: int)"
#   GET http://127.0.0.1:8000/items/abc        -> Should give a 400 Bad Request due to int conversion failure
#   GET http://127.0.0.1:8000/files/documents/report.pdf -> "Content of file at path: documents/report.pdf"
#   GET http://127.0.0.1:8000/fixed/path       -> "This is a fixed path."
```

**Path Parameter Type Conversion**

The example above includes a very basic mechanism within the router to attempt int conversion if {param_name:int} was specified in the route path. FastAPI achieves more robust and extensive data conversion and validation by leveraging Pydantic models and type hints in the handler function's signature. Our simplified version demonstrates the core idea: path parameters are initially strings extracted by regex, and the framework can attempt to convert them based on some defined expectation.  

**Route Priority**

With a list-based router where routes are evaluated in the order they are added, route priority is critical. More specific routes must be defined before more general or dynamic routes that might otherwise unintentionally capture requests intended for the specific ones. For example:

* app.add_route("/users/me", current_user_handler)  
* app.add_route("/users/{username}", user_details_handler)

If the order were reversed, a request to /users/me would match "/users/{username}" with username being "me", and current_user_handler would never be reached. This behavior is a direct consequence of the linear search matching strategy.

#### Handling Different HTTP Methods

A fundamental aspect of RESTful API design and web applications, in general, is the ability for a single URL path to respond differently based on the HTTP method used in the request (e.g., GET, POST, PUT, DELETE). Our add_route method already accepts a methods list, and the routing logic in handle_http checks scope['method'] against these allowed methods.

If a request's path matches a defined route pattern, but the HTTP method used in the request is not listed in that route's methods, the current implementation will fall through and eventually return a 404 Not Found. A more correct HTTP behavior would be to return a 405 Method Not Allowed status code. This would require the router to first find all routes matching the path and then check if any of them support the request's method. If path matches exist but none for the given method, then a 405 is appropriate. If no path matches at all, then 404 is correct.

For simplicity in this "from scratch" implementation, we'll stick to the current behavior, where a method mismatch for a matched path pattern effectively leads to the route not being considered fully matched for dispatch, thus potentially resulting in a 404 if no other route matches. Production frameworks typically implement distinct 405 handling. The Leapcell article's WSGI router also demonstrates storing and checking request methods.

The current add_route and handle_http methods already incorporate the logic for associating handlers with specific HTTP methods and checking against scope['method']. This fulfills the basic requirement of method-based dispatching.

### The Request Object: Understanding What the Client Wants

Interacting directly with the raw ASGI scope dictionary and receive callable in every request handler would be cumbersome, repetitive, and error-prone. To provide a more developer-friendly and abstracted way to access incoming request data, web frameworks typically introduce a Request object.

#### Why a Request Object?

A Request object encapsulates all the details of an incoming HTTP request, offering a clean, high-level API for accessing information such as headers, query parameters, path parameters, and the request body.  
The benefits include:

* **Abstraction**: Hides the lower-level details of the ASGI scope and receive channel.  
* **Ease of Use**: Provides convenient properties and methods (e.g., request.headers, await request.json()).  
* **Cleaner Handler Signatures**: Handler functions can accept a single Request object instead of scope, receive, and send.  
* **Helper Methods**: Can include utility methods for common tasks like parsing form data or JSON.

Starlette's Request class is a prime example of this abstraction, providing a rich interface to incoming request data. Our framework will implement a simplified version.

#### Creating Our Request Class

The Request class will take the ASGI scope and receive callable in its constructor and provide methods and properties to access parsed request information.

```python
# my_framework.py
# Add to existing imports:
from urllib.parse import parse_qs, unquote # For query string and form parsing
import json # For JSON body parsing

class Request:
    def __init__(self, scope: dict, receive: callable):
        self._scope = scope
        self._receive = receive
        self._body = None # To cache the request body once read
        self._stream_consumed = False # To track if the raw stream has been accessed

        # Pre-parse some common attributes from scope
        self.method = self._scope['method']
        self.path = self._scope['path']
        self.query_string = self._scope.get('query_string', b'')
        
        _headers = {}
        for name_bytes, value_bytes in self._scope.get('headers',):
            name = name_bytes.decode('latin-1') # Headers are typically ASCII/Latin-1
            value = value_bytes.decode('latin-1')
            # Handle multi-value headers by appending to a list
            if name in _headers:
                if isinstance(_headers[name], list):
                    _headers[name].append(value)
                else:
                    _headers[name] = [_headers[name], value]
            else:
                _headers[name] = value
        self.headers = _headers # Provides a dictionary-like interface

        self.client = self._scope.get('client') # Tuple (host, port) or None

    @property
    def query_params(self) -> dict:
        if not hasattr(self, '_query_params'):
            # parse_qs returns a dict where values are lists
            # We'll simplify for this example, taking the first value if only one.
            parsed_qs = parse_qs(self.query_string.decode('utf-8'))
            self._query_params = {
                k: v if len(v) == 1 else v for k, v in parsed_qs.items()
            }
        return self._query_params

    async def _load_body(self):
        """
        Internal method to read the full request body from the receive channel.
        The body is cached to prevent re-reading the stream.
        """
        if self._body is not None: # Body already loaded
            return
        if self._stream_consumed:
            raise RuntimeError("Cannot read body after stream has been consumed.")

        body_chunks =
        more_body = True
        while more_body:
            message = await self._receive()
            if message['type']!= 'http.request':
                # Handle disconnect or other unexpected messages if necessary
                print(f"Unexpected message type while reading body: {message['type']}")
                break 
            body_chunks.append(message.get('body', b''))
            more_body = message.get('more_body', False)
        
        self._body = b''.join(body_chunks)
        self._stream_consumed = True # Mark stream as consumed after full body read

    async def body(self) -> bytes:
        """Returns the raw request body as bytes."""
        if self._body is None:
            await self._load_body()
        return self._body

    async def json(self) -> any:
        """Parses the request body as JSON."""
        raw_body = await self.body()
        if not raw_body:
            return None
        try:
            return json.loads(raw_body.decode('utf-8'))
        except json.JSONDecodeError as e:
            # Handle malformed JSON, perhaps raise a custom HTTP error
            print(f"JSONDecodeError: {e}")
            raise ValueError("Invalid JSON body") from e # Or a custom exception

    async def form(self) -> dict:
        """Parses the request body as form data (application/x-www-form-urlencoded)."""
        # Ensure Content-Type is appropriate
        content_type = self.headers.get('content-type', '').lower()
        if 'application/x-www-form-urlencoded' not in content_type:
            # Consider raising an error or returning empty dict if content type is wrong
            print(f"Warning: Form data parsed for content type '{content_type}'")

        raw_body = await self.body()
        if not raw_body:
            return {}
        
        try:
            decoded_body = raw_body.decode('utf-8')
            # parse_qs returns dict with list values, simplify like query_params
            parsed_form = parse_qs(decoded_body)
            return {k: v if len(v) == 1 else v for k, v in parsed_form.items()}
        except Exception as e:
            print(f"Error parsing form data: {e}")
            raise ValueError("Invalid form data") from e

    async def stream(self) -> callable: # Changed to callable for yielding chunks
        """
        Provides an async generator to stream the request body chunks.
        Once this is called,.body(),.json(),.form() may not be available
        if they haven't been called before and cached the body.
        """
        if self._body is not None: # Body already fully read and cached
            yield self._body
            yield b'' # End of stream
            return
        
        if self._stream_consumed:
            raise RuntimeError("Stream has already been consumed or body fully read.")

        self._stream_consumed = True # Mark stream as being consumed
        more_body = True
        while more_body:
            message = await self._receive()
            if message['type']!= 'http.request':
                # Handle disconnect or other unexpected messages
                break
            yield message.get('body', b'')
            more_body = message.get('more_body', False)

# Update MyMiniFastAPI.handle_http to use this Request object:
# In MyMiniFastAPI class
    async def handle_http(self, scope: dict, receive: callable, send: callable):
        request = Request(scope, receive) # Create our Request object
        
        # Normalize request_path for matching (as done before)
        request_path = request.path 
        if request_path!= '/' and request_path.endswith('/'):
            request_path = request_path.rstrip('/')
        # if not request_path.startswith('/'): # ASGI path should always start with /
        #     request_path = '/' + request_path

        request_method = request.method
        print(f"HTTP Request (via Request object): Attempting to route {request_method} {request_path}")

        matched_route_info = None
        path_params = {}

        for route_entry in self.routes:
            if request_method not in route_entry['methods']:
                continue

            if route_entry["is_dynamic"]:
                match = route_entry['path_regex'].fullmatch(request_path)
                if match:
                    matched_route_info = route_entry
                    raw_path_params = match.groupdict()
                    
                    # Type conversion for path parameters (simplified)
                    path_params = {}
                    conversion_error = False
                    for param_name, value_str in raw_path_params.items():
                        path_params[param_name] = value_str # Default to string
                        {% raw %}original_segment_placeholder_int = f"{{{param_name}:int}}"{% endraw %}
                        if original_segment_placeholder_int in route_entry["path_str"]:
                            try:
                                path_params[param_name] = int(value_str)
                            except ValueError:
                                print(f"Path parameter type conversion error for '{param_name}': expected int, got '{value_str}'")
                                await self._send_error_response(send, 400, "Bad Request: Invalid path parameter type")
                                conversion_error = True
                                break
                        # Add other type checks here if needed (e.g., :float)
                    if conversion_error: return
                    break # Route matched
            else: # Static path matching
                defined_path = route_entry['path_str']
                if defined_path!= '/' and defined_path.endswith('/'):
                    defined_path = defined_path.rstrip('/')
                
                if defined_path == request_path:
                    matched_route_info = route_entry
                    break
        
        if matched_route_info:
            handler = matched_route_info['handler']
            print(f"Routing to handler: {handler.__name__} for {request_method} {request_path} with params {path_params}")
            
            try:
                # Now, pass the request object to the handler
                # Handlers should be updated to accept 'request' as their first argument
                # e.g., async def my_handler(request: Request, username: str):...
                
                # Inspect handler signature to see if it expects 'request'
                import inspect
                sig = inspect.signature(handler)
                handler_args = {}
                
                # Pass path parameters if the handler expects them
                for p_name, p_value in path_params.items():
                    if p_name in sig.parameters:
                        handler_args[p_name] = p_value
                
                # Check if the first parameter is 'request' or has a 'Request' type hint
                # This is a simplified check. Real DI is more complex.
                if 'request' in sig.parameters or \
                   any(p.annotation == Request for p in sig.parameters.values()):
                    handler_args['request'] = request
                
                # Call handler with potentially 'request' and path_params
                response_obj_or_content = await handler(**handler_args)

                # This part will be refined when Response objects are fully integrated
                if isinstance(response_obj_or_content, str): # Simple string response
                    status_code = 200
                    content_type = b'text/plain'
                    response_body_bytes = response_obj_or_content.encode('utf-8')
                    response_headers = [b'content-type', content_type],
                        [b'content-length', str(len(response_body_bytes)).encode('utf-8')]
                    await send({'type': 'http.response.start', 'status': status_code, 'headers': response_headers})
                    await send({'type': 'http.response.body', 'body': response_body_bytes, 'more_body': False})
                
                # Later, we will expect handlers to return Response objects:
                # elif isinstance(response_obj_or_content, Response): # Assuming Response class exists
                #    await response_obj_or_content(scope, receive, send) # Response object handles sending

            except TypeError as e:
                 print(f"Handler argument mismatch or call error for {handler.__name__}: {e}")
                 await self._send_error_response(send, 500, "Internal Server Error: Handler call failed")
            except Exception as e:
                print(f"Error in handler {handler.__name__}: {e}")
                await self._send_error_response(send, 500, "Internal Server Error")
            
            print(f"Response sent for {request_method} {request_path}")
            return

        print(f"No route found for {request_method} {request_path}. Sending 404.")
        await self._send_error_response(send, 404, "Not Found")
```

The Request class now encapsulates scope and receive. It provides properties like method, path, headers, client, and query_params (which lazily parses the query_string using urllib.parse.parse_qs). The handle_http method in MyMiniFastAPI is updated to instantiate this Request object and (conceptually) pass it to the matched route handler. Handlers would then be defined like async def my_handler(request: Request):....

#### Handling the Request Body (Deep Dive)

The HTTP request body is not available in the initial scope; it must be read from the ASGI receive channel through http.request messages. This is where the asynchronous nature of ASGI truly comes into play, especially for streaming large bodies.

**Internal Body Loading (load_body)**

The Request class's load_body method is responsible for this.

* It loops, calling await self._receive(), until a message with more_body: False is received.  
* It accumulates the byte chunks from message['body'].  
* Crucially, it caches the full body in self._body and sets self._stream_consumed = True. This is vital because the ASGI receive stream for the body can typically only be consumed once. If the application tries to read it again, it might get no data or an error. Starlette's Request object also caches the body after the first full read. Issues around re-reading the body or stream are common pitfalls if not handled carefully.

**Public Body Accessor Methods**

* async def body(self) -> bytes: This method ensures load_body is called if the body hasn't been loaded yet, then returns the cached self._body.  
* async def json(self): It calls await self.body() to get the raw bytes, then decodes them (assuming UTF-8) and uses json.loads() to parse. It should handle potential json.JSONDecodeError.  
* async def form(self): This method also calls await self.body(). For application/x-www-form-urlencoded data, it decodes the body and uses urllib.parse.parse_qs. Parsing multipart/form-data is significantly more complex and typically requires a dedicated library (like python-multipart, which Starlette and FastAPI use). For our "from scratch" version, we will primarily focus on x-www-form-urlencoded or acknowledge that full multipart parsing is an advanced topic beyond the immediate scope of a simple rebuild. Starlette itself can stream multipart file uploads to temporary files to avoid high memory usage.  
* async def stream(self) -> AsyncGenerator[bytes, None]: This method provides a way to iterate over body chunks as they arrive from the receive channel without loading the entire body into memory first.  
  * If self._body is already loaded (e.g., await request.body() was called first), it can yield the cached body (perhaps in one chunk or as configured) or raise an error indicating the stream was already consumed by a full read.  
  * If the body hasn't been loaded and self._stream_consumed is false, it directly await self._receive() and yield message.get('body', b'') in a loop, setting self._stream_consumed = True once iteration begins.  
  * Starlette's behavior is that if .stream() is accessed first, subsequent calls to .body(), .form(), or .json() will raise an error because the raw stream has been consumed chunk by chunk. This is an important detail for users to understand: choose one way to consume the body.

The design of the ASGI receive channel, being an iterable and generally allowing one-time consumption of body messages, directly influences how a Request object must be implemented to handle body parsing robustly. Caching the body after a full read (by .body(), .json(), or .form()) is essential for allowing multiple accesses to the *parsed* data, while the .stream() method offers a lower-level, memory-efficient way to process very large bodies.

The following table illustrates how various parts of an HTTP request map to the ASGI specification and how our Request class provides access to them:

| HTTP Request Part | ASGI Source (scope key / receive event) | Our Request Class Accessor (request.attribute) |
| :---- | :---- | :---- |
| **Method** | scope['method'] (e.g., "GET") | request.method |
| **Path** | scope['path'] (e.g., "/items/123") | request.path |
| **Query String** | scope['query_string'] (e.g., b"name=foo&limit=10") | request.query_params (parsed dictionary) |
| **Headers** | scope['headers'] (list of [b'name', b'value']) | request.headers (parsed, dictionary-like access) |
| **Client Address** | scope\['client'\] (e.g., ('127.0.0.1', 12345)) | request.client |
| **Raw Request Body** | await receive() for {'type': 'http.request', 'body':..., 'more_body':...} | await request.body() (returns bytes) |
| **JSON Body** | (Derived from Raw Request Body) | await request.json() (parses JSON from body) |
| **Form Data** | (Derived from Raw Request Body, for x-www-form-urlencoded) | await request.form() (parses form data from body) |
| **Streaming Body** | await receive() for {'type': 'http.request', 'body':..., 'more_body':...} | async for chunk in request.stream():... |

This table clearly demonstrates the abstraction provided by the Request object over the underlying ASGI mechanisms.

### The Response Object: Crafting the Server's Reply

Just as a Request object simplifies handling incoming data, a Response object provides a structured and convenient way to define the HTTP response that our framework will send back to the client. This encapsulates status codes, headers, and the response body, abstracting away the direct use of the ASGI send callable for common response patterns.

#### Why a Response Object?

Manually constructing the ASGI http.response.start and http.response.body messages in every handler function would be verbose, error-prone, and would lead to much boilerplate code. A Response object offers:

* **Abstraction**: Hides the low-level details of ASGI send calls.  
* **Consistency**: Ensures responses are formatted correctly according to HTTP and ASGI specifications.  
* **Convenience**: Provides helper methods or subclasses for common response types (e.g., JSON, HTML).  
* **Cleaner Handlers**: Allows handler functions to simply return a Response instance, delegating the task of sending ASGI messages to the framework or the Response object itself.

Starlette provides a suite of Response classes (e.g., Response, JSONResponse, HTMLResponse, FileResponse) that serve this purpose effectively.

#### Creating Our Response Class

Our base Response class will handle plain text or byte content and manage status codes and headers. A key design feature, inspired by Starlette, is making the Response object itself an ASGI awaitable by implementing the __call__ method.

```python
# my_framework.py
# (Ensure 'import json' is available if not already imported)

class Response:
    media_type = None # Default media type, subclasses can override
    charset = "utf-8"

    def __init__(
        self,
        content: any, # Can be str, bytes, or for subclasses, other types like dict
        status_code: int = 200,
        headers: dict = None,
        media_type: str = None,
    ):
        self.status_code = status_code
        self.content = content
        self._headers = headers if headers is not None else {} # Use a private attribute for headers
        
        # Determine and set content type
        if media_type is not None:
            self.media_type = media_type
        
        if self.media_type and 'content-type' not in (key.lower() for key in self._headers.keys()):
            content_type_val = self.media_type
            if self.media_type.startswith("text/"): # Add charset for text types
                content_type_val += f"; charset={self.charset}"
            self._headers = content_type_val
        
        self.body_bytes = self.render_content(content)
        self._headers['Content-Length'] = str(len(self.body_bytes))


    def render_content(self, content: any) -> bytes:
        """Converts content to bytes. Subclasses can override for specific types."""
        if isinstance(content, bytes):
            return content
        if isinstance(content, str):
            return content.encode(self.charset)
        raise TypeError(f"Unsupported content type: {type(content)}. Must be str or bytes for base Response.")

    def render_headers(self) -> list:
        """Converts internal headers dictionary to ASGI header list format."""
        return [
            (key.lower().encode('latin-1'), value.encode('latin-1'))
            for key, value in self._headers.items()
        ]

    async def __call__(self, scope: dict, receive: callable, send: callable):
        """
        This makes the Response object an ASGI application (or part of one),
        responsible for sending itself over the ASGI 'send' channel.
        """
        await send({
            'type': 'http.response.start',
            'status': self.status_code,
            'headers': self.render_headers(),
        })
        await send({
            'type': 'http.response.body',
            'body': self.body_bytes, # Use pre-rendered body
            'more_body': False # Assuming complete body for base Response
        })

# Example of a handler returning a Response object (conceptual for now)
# async def home_handler_returns_response(request: Request):
#     return Response("Hello from Response Object!", media_type="text/plain")

# MyMiniFastAPI.handle_http would be updated to:
# if matched_route_info:
#    ...
#     response_object = await handler(**handler_args) # Handler returns a Response instance
#     if isinstance(response_object, Response):
#         await response_object(scope, receive, send) # Call the response object
#     else: # Fallback for handlers returning strings (as in previous version)
#         #... handle string response...
# else:
#     # Handle 404 by creating and calling a Response object
#     error_response = Response("Not Found", status_code=404, media_type="text/plain")
#     await error_response(scope, receive, send)

```

**Explanation**

* **__init__**:  
  * Stores content, status_code.  
  * Initializes self._headers as a dictionary. It automatically sets the Content-Type header based on media_type (defaulting if not provided or overridden by subclasses). For text-based media types, it appends the charset.  
  * Calls render_content to convert the input content into self.body_bytes.  
  * Sets the Content-Length header based on the length of self.body_bytes. Starlette also automatically includes these headers.  
* **render_content(self, content)**: This base implementation handles str (encodes to bytes) and bytes. Subclasses (like JSONResponse) will override this to handle their specific content types.  
* **render_headers(self)**: Converts the internal self._headers dictionary into the list of (byte_name, byte_value) pairs required by ASGI. Header names are lowercased.  
* **async def __call__(self, scope, receive, send)**: This is the core of the "Response as an ASGI app" pattern. When the framework gets a Response object back from a handler, it can simply await response_object(scope, receive, send).  
  * It sends the http.response.start message with the status code and rendered headers.  
  * It sends the http.response.body message with the rendered (and now byte-encoded) body. more_body: False is used as the base Response assumes it sends the entire body in one go. Streaming responses would require more complex logic here or in a specialized subclass.

This design decouples the creation of response data within a handler from the actual mechanics of sending ASGI messages. The framework's main HTTP handling logic becomes simpler: it calls the route handler, expects a Response object back, and then "executes" that response object.

#### Specialized Responses (e.g., JSONResponse)

Building on the base Response class, we can easily create specialized subclasses for common response types, like JSON.

```python
# my_framework.py (continued)

class JSONResponse(Response):
    media_type = "application/json" # Override default media type

    def __init__(
        self,
        content: any, # Expects a JSON-serializable Python object (dict, list, etc.)
        status_code: int = 200,
        headers: dict = None,
    ):
        super().__init__(content, status_code, headers, media_type=self.media_type)

    def render_content(self, content: any) -> bytes:
        """Serializes Python dict/list to a JSON byte string."""
        try:
            return json.dumps(content, separators=(",", ":")).encode(self.charset)
        except TypeError as e:
            # Handle cases where content is not JSON serializable
            print(f"Error serializing content to JSON: {e}")
            # Fallback or raise a more specific server error
            raise ValueError("Content is not JSON serializable") from e

class HTMLResponse(Response):
    media_type = "text/html"

    # __init__ can be inherited if no special content processing before render_content
    # render_content is also inherited if content is expected to be string/bytes

class PlainTextResponse(Response):
    media_type = "text/plain"

    # Similar to HTMLResponse, can often rely on base class methods if content is string/bytes

# Example Usage in MyMiniFastAPI (conceptual, assuming handlers return these)
# async def json_data_handler(request: Request):
#     return JSONResponse({"message": "Hello, JSON!", "data": })

# async def html_page_handler(request: Request):
#     html_content = "<html><body><h1>Hello, HTML!</h1></body></html>"
#     return HTMLResponse(html_content)

# Update MyMiniFastAPI.handle_http to use these Response objects:
# In MyMiniFastAPI class, the part where a handler is called:
    #... (inside the 'if matched_route_info:' block)
    # try:
    #     response_object = await handler(**handler_args) # Handler now returns a Response instance
    #     if not isinstance(response_object, Response):
    #         # If handler returns something else (e.g. string), wrap it for safety
    #         print(f"Warning: Handler {handler.__name__} did not return a Response object. Wrapping in PlainTextResponse.")
    #         response_object = PlainTextResponse(str(response_obj_or_content))
        
    #     await response_object(scope, receive, send) # Call the response object to send itself

    # except Exception as e:
    #     print(f"Error processing request or in handler {handler.__name__}: {e}")
    #     # Create and send an error response object
    #     error_response = JSONResponse({"detail": "Internal Server Error"}, status_code=500)
    #     await error_response(scope, receive, send)
    #...

    # And for 404:
    # print(f"No route found for {request_method} {request_path}. Sending 404.")
    # not_found_response = JSONResponse({"detail": "Not Found"}, status_code=404)
    # await not_found_response(scope, receive, send)

```

**JSONResponse Explanation:**

* It inherits from Response.  
* It overrides media_type to "application/json".  
* Its render_content method uses json.dumps() to serialize the Python object (typically a dict or list) into a JSON string, which is then encoded to bytes. Using separators=(",", ":") creates a more compact JSON output, similar to FastAPI's default.

Similarly, HTMLResponse and PlainTextResponse can be created, primarily by setting the correct media_type. Their render_content might simply call the superclass's method if they expect string or byte content. This pattern of specialized response classes significantly improves developer ergonomics for common API tasks, mirroring the convenience offered by Starlette and FastAPI.

## Part 2: Adding FastAPI's "Magic" - Decorators, Validation, and DI

With the core ASGI application, routing, and request/response objects in place, we can now explore some of the features that give FastAPI its characteristic "magic" and developer-friendliness: path operation decorators, type hint-based data validation (simplified), and a basic dependency injection system.

### Path Operation Decorators: The @app.get Magic

One of FastAPI's most recognizable features is its use of decorators like @app.get("/") to define API endpoints. This provides a clean, declarative syntax for associating a URL path and HTTP method with a handler function.

#### Understanding Python Decorators

A Python decorator is a function that takes another function (the decorated function) as an argument and returns a new function, typically an augmented version of the input function, or it can register the function somewhere. The @decorator syntax is syntactic sugar for my_function = decorator(my_function).

Here's a simple example of a decorator that logs when a function is called:

```python
import functools

def log_calls(func):
    @functools.wraps(func) # Preserves original function metadata
    def wrapper(*args, **kwargs):
        print(f"Calling function: {func.__name__} with args: {args}, kwargs: {kwargs}")
        result = func(*args, **kwargs)
        print(f"Function {func.__name__} returned: {result}")
        return result
    return wrapper

@log_calls
def add(a, b):
    return a + b

result = add(5, 3) 
# Output will show "Calling function: add..." and "Function add returned: 8"

```

In the context of a web framework, decorators are used not just to modify function behavior but often to register the decorated function with the framework, associating it with metadata like a route path or HTTP methods.

#### Implementing Framework Decorators in MyMiniFastAPI

We will add methods like get(self, path), post(self, path), etc., to our MyMiniFastAPI class. These methods will themselves be decorators.

```python
# In MyMiniFastAPI class

#... (previous methods: __init__, __call__, handle_lifespan, handle_http, 
#      _compile_path, add_route, _send_error_response)...

    def route(self, path: str, methods: list = None):
        """
        A general decorator for adding routes.
        This will be wrapped by specific HTTP method decorators like.get(),.post().
        """
        if methods is None:
            methods = # Default to GET if not specified by specific decorator

        def decorator(handler_func: callable):
            self.add_route(path, handler_func, methods=methods)
            # @functools.wraps(handler_func) # Good practice, though not strictly needed if not modifying handler
            # def wrapper(*args, **kwargs):
            #     # If we needed to wrap the handler, we'd do it here.
            #     # For route registration, we just need to register it.
            #     return await handler_func(*args, **kwargs) # Assuming handler is async
            return handler_func # Return the original handler, as we're just registering it
        return decorator

    def get(self, path: str):
        """Decorator for GET requests."""
        return self.route(path, methods=)

    def post(self, path: str):
        """Decorator for POST requests."""
        return self.route(path, methods=)

    def put(self, path: str):
        """Decorator for PUT requests."""
        return self.route(path, methods=)

    def delete(self, path: str):
        """Decorator for DELETE requests."""
        return self.route(path, methods=)

    # Add more for PATCH, OPTIONS, HEAD, TRACE if desired
```

#### Using the New Decorators

The example usage at the bottom of my_framework.py can now be rewritten:

```python

# At the bottom of my_framework.py
app = MyMiniFastAPI() # Instance of our framework

# Define handlers (ensure they can accept path parameters if route defines them)
async def home_handler(request: Request): # Updated to accept Request
    return PlainTextResponse("Welcome via @app.get!")

async def about_handler(request: Request):
    return PlainTextResponse("This is the About Page, registered with @app.get.")

async def submit_data_handler(request: Request): # For POST
    try:
        data = await request.json() # Assuming JSON data for POST
        return JSONResponse({"message": "Data received via @app.post", "data": data})
    except ValueError: # Handles invalid JSON
        return JSONResponse({"error": "Invalid JSON data"}, status_code=400)
    except Exception as e:
        return JSONResponse({"error": f"An error occurred: {str(e)}"}, status_code=500)


async def user_profile_handler(request: Request, username: str): # Dynamic path
    return PlainTextResponse(f"Profile page for user: {username}")

async def get_item_handler(request: Request, item_id: int): # Dynamic path with type hint
    return JSONResponse({"item_id": item_id, "description": f"Details for item {item_id}"})

# Register routes using decorators
@app.get("/")
async def home_decorated_handler(request: Request):
    return PlainTextResponse("Decorated Home!")

@app.get("/about-decorated")
async def about_decorated_handler(request: Request):
    return PlainTextResponse("Decorated About Page!")

@app.post("/submit-decorated")
async def submit_decorated_handler(request: Request):
    try:
        data = await request.json()
        return JSONResponse({"message": "Decorated POST received", "data": data})
    except ValueError:
        return JSONResponse({"error": "Invalid JSON data from decorated POST"}, status_code=400)

@app.get("/users/{username}") # Dynamic route with decorator
async def user_profile_decorated_handler(request: Request, username: str):
    return PlainTextResponse(f"Decorated profile for: {username}")

@app.get("/items/{item_id:int}") # Dynamic route with type converter and decorator
async def item_decorated_handler(request: Request, item_id: int):
    return JSONResponse({"item_id": item_id, "type": type(item_id).__name__, "message": "Decorated item details"})

# Ensure MyMiniFastAPI.handle_http is updated to pass the Request object
# and to expect a Response object from handlers, then call that Response object.
# The simplified handler call in the previous handle_http needs to be replaced with:
#
#   response_object = await handler(**handler_args)
#   if not isinstance(response_object, Response):
#       print(f"Warning: Handler {handler.__name__} did not return a Response object.")
#       # Default to PlainTextResponse or raise an error
#       response_object = PlainTextResponse(str(response_object))
#   await response_object(scope, receive, send)
#
# And for 404/500 errors, also use Response objects:
#   error_response = JSONResponse({"detail": "Not Found"}, status_code=404)
#   await error_response(scope, receive, send)
```

#### Refining handle_http to use Response Objects fully

```python
# In MyMiniFastAPI class

#... (previous methods)...

    async def handle_http(self, scope: dict, receive: callable, send: callable):
        request = Request(scope, receive)
        
        request_path = request.path 
        if request_path!= '/' and request_path.endswith('/'):
            request_path = request_path.rstrip('/')

        request_method = request.method
        print(f"HTTP Request (via Request object): Attempting to route {request_method} {request_path}")

        matched_route_info = None
        path_params = {}
        final_handler_args = {} # Arguments to be passed to the handler

        for route_entry in self.routes:
            if request_method not in route_entry['methods']:
                continue

            current_path_params = {} # Params for this specific route match attempt
            if route_entry["is_dynamic"]:
                match = route_entry['path_regex'].fullmatch(request_path)
                if match:
                    raw_path_params = match.groupdict()
                    conversion_error = False
                    for param_name, value_str in raw_path_params.items():
                        current_path_params[param_name] = value_str # Default to string
                        {% raw %}original_segment_placeholder_int = f"{{{param_name}:int}}"{% endraw %}
                        if original_segment_placeholder_int in route_entry["path_str"]:
                            try:
                                current_path_params[param_name] = int(value_str)
                            except ValueError:
                                print(f"Path parameter type conversion error for '{param_name}': expected int, got '{value_str}'")
                                await JSONResponse({"detail": "Bad Request: Invalid path parameter type"}, status_code=400)(scope, receive, send)
                                conversion_error = True
                                break
                        # Add other type checks here if needed (e.g., :float)
                    if conversion_error: return
                    
                    matched_route_info = route_entry
                    path_params = current_path_params # Use successfully converted params
                    break 
            else: 
                defined_path = route_entry['path_str']
                if defined_path!= '/' and defined_path.endswith('/'):
                    defined_path = defined_path.rstrip('/')
                
                if defined_path == request_path:
                    matched_route_info = route_entry
                    break
        
        if matched_route_info:
            handler = matched_route_info['handler']
            print(f"Routing to handler: {handler.__name__} for {request_method} {request_path} with params {path_params}")
            
            # Prepare arguments for the handler
            import inspect
            sig = inspect.signature(handler)
            
            # Path parameters
            for p_name, p_value in path_params.items():
                if p_name in sig.parameters:
                    final_handler_args[p_name] = p_value
            
            # Request object (if expected by handler)
            # A more robust check would look at type hints or a specific parameter name convention
            if 'request' in sig.parameters and sig.parameters['request'].annotation == Request:
                 final_handler_args['request'] = request
            elif any(p.annotation == Request for p in sig.parameters.values()):
                # Find the first param annotated as Request if 'request' name isn't used
                for p_name, param_obj in sig.parameters.items():
                    if param_obj.annotation == Request:
                        final_handler_args[p_name] = request
                        break
            
            try:
                response_object = await handler(**final_handler_args)
                
                if not isinstance(response_object, Response):
                    print(f"Warning: Handler {handler.__name__} did not return a Response object. Wrapping in PlainTextResponse.")
                    response_object = PlainTextResponse(str(response_object)) # Default wrap
                
                await response_object(scope, receive, send) # Execute the response object

            except TypeError as e: # Catches argument mismatches if inspect logic isn't perfect
                 print(f"Handler argument mismatch or call error for {handler.__name__}: {e}")
                 error_response = JSONResponse({"detail": "Internal Server Error: Handler call failed"}, status_code=500)
                 await error_response(scope, receive, send)
            except Exception as e:
                print(f"Unhandled error in handler {handler.__name__}: {e}")
                # Log the full traceback for debugging
                import traceback
                traceback.print_exc()
                error_response = JSONResponse({"detail": "Internal Server Error"}, status_code=500)
                await error_response(scope, receive, send)
            
            print(f"Response sent for {request_method} {request_path}")
            return

        print(f"No route found for {request_method} {request_path}. Sending 404.")
        not_found_response = JSONResponse({"detail": "Not Found"}, status_code=404)
        await not_found_response(scope, receive, send)
```

The route method is a general-purpose decorator factory. It takes a path and methods list and returns the actual decorator (decorator). This inner decorator function receives the user's handler function (handler_func) as an argument, calls self.add_route to register it, and then returns the original handler_func (as we are not modifying its behavior, just registering it). Specific methods like get, post, etc., simply call self.route with the appropriate HTTP method. This use of decorators provides a much cleaner and more declarative way to define API endpoints, which is a hallmark of frameworks like FastAPI and Flask.

### Data Validation and Serialization with Type Hints (Simplified Pydantic)

FastAPI's strong integration with Pydantic for data validation and serialization using Python type hints is a cornerstone of its design. Pydantic models, inheriting from BaseModel, allow developers to define data schemas with types, and FastAPI uses these models to automatically validate incoming request data and serialize outgoing response data. While replicating the entirety of Pydantic is beyond our scope, we can implement a simplified version of type hint-based validation and data conversion for path parameters, query parameters, and basic request bodies.

The inspect module in Python's standard library is key here, as it allows us to introspect function signatures to get parameter names and their type annotations.

#### Our Simplified Approach to Validation/Conversion

1. **Path Parameters**: As partially implemented in our dynamic router (_compile_path and handle_http), if a path segment is defined like {item_id:int}, the router attempts to convert the extracted string to an int. If this fails, a 400 Bad Request can be returned. We can extend this to look at the handler function's type hints for path parameters.  
2. **Query Parameters**:  
   * Handler functions can define query parameters with type hints: `async def items(limit: int = 10, q: str = None):...`  
   * Our framework, when preparing to call the handler, can inspect its signature.  
   * It would parse query parameters from request.query_params (which are initially strings).  
   * For each query parameter expected by the handler, if a type hint (e.g., int, bool, float) is present, the framework attempts to convert the string value. If conversion fails, it can return a 400 Bad Request.  
   * Default values from the handler signature are used if the query parameter is not provided.  
3. **Request Body (JSON)**:  
   * Handlers can type-hint a parameter to represent the request body, for example, item: ItemSchema where ItemSchema could be a simple Python dataclass or a dictionary structure we define.  
   * When await request.json() is called, if the handler expects a specific structure (e.g., a dataclass), our framework could attempt to instantiate that dataclass with the parsed JSON dictionary. Type errors during instantiation would indicate a validation failure.  
   * For a "from scratch" approach without full Pydantic, we might focus on basic type checks for dictionary keys or structural validation if the type hint is a dataclass.  
4. **Response Serialization**:  
   * FastAPI uses the response_model parameter in decorators to define the shape of the output and filter/validate it.  
   * Our simplified framework could inspect the return type hint of the handler function (e.g., `async def get_item() -> ItemSchema:...`). If JSONResponse is used, it already handles serialization of basic Python types. If a custom object (like a dataclass instance) is returned, JSONResponse might need to be smarter (e.g., by calling dataclasses.asdict() if it's a dataclass) or the handler should ensure it returns a serializable dictionary.

#### Using inspect.signature() for Basic Validation/Conversion

Let's refine how path parameters and query parameters could be handled by inspecting handler signatures.

```python
# In MyMiniFastAPI.handle_http, when preparing to call the handler:
# (This replaces parts of the existing path_param conversion and adds query_param handling)

#... (inside 'if matched_route_info:' block, after 'sig = inspect.signature(handler)')...
            
            final_handler_args = {}
            conversion_failed = False

            # 1. Path Parameters (already extracted into path_params dict)
            for p_name, p_value_str in path_params.items():
                if p_name in sig.parameters:
                    param_obj = sig.parameters[p_name]
                    target_type = param_obj.annotation
                    if target_type == int:
                        try:
                            final_handler_args[p_name] = int(p_value_str)
                        except ValueError:
                            await JSONResponse({"detail": f"Invalid path parameter '{p_name}'. Expected integer."}, status_code=400)(scope, receive, send)
                            conversion_failed = True; break
                    elif target_type == float: # Example for another type
                        try:
                            final_handler_args[p_name] = float(p_value_str)
                        except ValueError:
                            await JSONResponse({"detail": f"Invalid path parameter '{p_name}'. Expected float."}, status_code=400)(scope, receive, send)
                            conversion_failed = True; break
                    elif target_type == str or target_type == inspect.Parameter.empty:
                        final_handler_args[p_name] = p_value_str # Already a string
                    else: # Unsupported type hint for path param for now
                        final_handler_args[p_name] = p_value_str 
            if conversion_failed: return

            # 2. Query Parameters (from request.query_params)
            # request.query_params is already a dict of str: str (or str: list[str])
            for q_name, param_obj in sig.parameters.items():
                if q_name in path_params or q_name == 'request': # Already handled or is the request object
                    continue

                query_val_str = request.query_params.get(q_name)
                target_type = param_obj.annotation
                
                if query_val_str is not None: # Parameter provided in query string
                    if target_type == int:
                        try:
                            final_handler_args[q_name] = int(query_val_str)
                        except ValueError:
                            await JSONResponse({"detail": f"Invalid query parameter '{q_name}'. Expected integer."}, status_code=400)(scope, receive, send)
                            conversion_failed = True; break
                    elif target_type == float:
                        try:
                            final_handler_args[q_name] = float(query_val_str)
                        except ValueError:
                            await JSONResponse({"detail": f"Invalid query parameter '{q_name}'. Expected float."}, status_code=400)(scope, receive, send)
                            conversion_failed = True; break
                    elif target_type == bool:
                        # Common boolean representations: "true", "false", "1", "0", "yes", "no"
                        val_lower = query_val_str.lower()
                        if val_lower in ("true", "1", "yes"): final_handler_args[q_name] = True
                        elif val_lower in ("false", "0", "no"): final_handler_args[q_name] = False
                        else:
                            await JSONResponse({"detail": f"Invalid query parameter '{q_name}'. Expected boolean."}, status_code=400)(scope, receive, send)
                            conversion_failed = True; break
                    elif target_type == str or target_type == inspect.Parameter.empty:
                        final_handler_args[q_name] = query_val_str
                    else: # For other types (e.g., custom Pydantic-like models), this would be more complex
                        final_handler_args[q_name] = query_val_str # Pass as string for now
                elif param_obj.default is not inspect.Parameter.empty:
                    final_handler_args[q_name] = param_obj.default # Use default value
                # If no value and no default, and not optional (e.g. Optional[int]), it's a missing required param
                # This basic check doesn't handle Optional or Union type hints yet.
            if conversion_failed: return

            # 3. Request Body (JSON, simplified)
            # Assume one parameter might be for the body, often type-hinted with a dataclass or dict
            # This is a very simplified model for body handling. FastAPI's is much more robust.
            # For example, if a handler is `async def create_item(item: ItemModel, request: Request):`
            # we'd need to identify 'item' as the body parameter.
            # This part requires more thought for a clean "from scratch" implementation
            # without fully replicating Pydantic's field analysis.
            # For now, handlers will explicitly call `await request.json()` or `await request.form()`.

            # Inject request object if handler expects it
            if 'request' in sig.parameters and sig.parameters['request'].annotation == Request:
                 final_handler_args['request'] = request
            #... (rest of the handler call and response processing)
```

This snippet demonstrates how `inspect.signature` can be used to retrieve parameter names and their type annotations. Based on these annotations, basic type conversions for path and query parameters are attempted. If a ValueError occurs during conversion (e.g., trying to convert "abc" to int), a 400 Bad Request response is sent. This illustrates the core principle of runtime type checking and conversion that FastAPI does so powerfully with Pydantic. The availability of Python's type hints and the inspect module makes this elegant approach to data validation feasible.

### Dependency Injection (Simplified Depends)

Dependency Injection (DI) is a design pattern where components' dependencies are provided (injected) from an external source rather than being created internally by the component itself. FastAPI features a powerful and intuitive DI system, primarily through the Depends marker. This system promotes decoupled, reusable, and testable code by managing shared logic, resource access (like database connections), and authentication.

#### FastAPI's Depends System

In FastAPI, a dependency is typically a callable (like a function) that FastAPI will execute before running the path operation function. The return value of this dependency callable is then injected into the path operation function as an argument.
Example: `async def get_items(db: Session = Depends(get_db_session)):...`  
Here, get_db_session is the dependency callable. FastAPI calls it, and its return value is passed as the db argument to get_items. Dependencies themselves can have further dependencies, forming a chain that FastAPI resolves.  

#### Implementing Our Simplified Depends

Our version will involve:

1. A marker class Depends to identify parameters that need dependency injection.  
2. Logic within MyMiniFastAPI to inspect handler signatures, identify Depends markers, execute the dependency callable, and inject the result.

```python
# my_framework.py

# Marker class for dependencies
class Depends:
    def __init__(self, dependency_callable: callable):
        if not callable(dependency_callable):
            raise TypeError("Dependency must be a callable")
        self.dependency_callable = dependency_callable

# Update MyMiniFastAPI.handle_http to include dependency resolution
# This logic should be placed before calling the handler, after route matching
# and initial path/query parameter processing.

# In MyMiniFastAPI.handle_http, before the 'try...except' block for calling the handler:
    #... (after path_params and query_params are processed into final_handler_args)...

            # 4. Dependency Injection
            # Iterate over signature parameters again to resolve dependencies
            for param_name, param_obj in sig.parameters.items():
                if isinstance(param_obj.default, Depends):
                    dependency_marker = param_obj.default
                    dep_callable = dependency_marker.dependency_callable
                    
                    # Inspect the dependency callable itself for its own needs (e.g., request, other params)
                    dep_sig = inspect.signature(dep_callable)
                    dep_args = {}

                    # Provide 'request' to dependency if it expects it
                    if 'request' in dep_sig.parameters and dep_sig.parameters['request'].annotation == Request:
                        dep_args['request'] = request
                    
                    # Provide already resolved path/query params to dependency if it expects them by name
                    for p_name_dep in dep_sig.parameters:
                        if p_name_dep in final_handler_args: # From path/query params
                            dep_args[p_name_dep] = final_handler_args[p_name_dep]
                        elif p_name_dep in request.query_params: # Check request.query_params directly for deps
                             # This part would need type conversion similar to main handler params
                            dep_args[p_name_dep] = request.query_params[p_name_dep]


                    print(f"Resolving dependency for '{param_name}' using '{dep_callable.__name__}' with args {dep_args}")
                    try:
                        if inspect.iscoroutinefunction(dep_callable):
                            dependency_result = await dep_callable(**dep_args)
                        else:
                            dependency_result = dep_callable(**dep_args)
                        final_handler_args[param_name] = dependency_result
                    except Exception as e:
                        print(f"Error resolving dependency '{dep_callable.__name__}': {e}")
                        # This should ideally return a 500 error to the client
                        await JSONResponse({"detail": f"Failed to resolve dependency: {dep_callable.__name__}"}, status_code=500)(scope, receive, send)
                        return # Stop processing

            # Now, final_handler_args contains path params, query params, AND resolved dependencies
            # The handler call:
            # response_object = await handler(**final_handler_args)
            #... (rest of handler call and response sending)
```

#### Example Usage of Simplified Depends

```python
# At the bottom of my_framework.py
app = MyMiniFastAPI() # Assume this and Response classes are defined

# --- Dependency Function ---
async def get_common_params(request: Request, limit: int = 100, offset: int = 0):
    # This dependency could also perform validation or fetch common data
    print(f"Dependency get_common_params called: limit={limit}, offset={offset}, path={request.path}")
    return {"limit": limit, "offset": offset, "q": request.query_params.get("q")}

# --- Another Dependency for User (simplified) ---
async def get_current_user(request: Request) -> dict | None:
    token = request.headers.get("x-token")
    if token == "fake-super-secret-token":
        return {"username": "testuser", "email": "user@example.com"}
    return None

# --- Route Handlers ---
@app.get("/items/")
async def read_items(request: Request, commons: dict = Depends(get_common_params)):
    # 'commons' will be the dictionary returned by get_common_params
    # Query parameters 'limit' and 'offset' for get_common_params will be auto-parsed if defined in its signature
    # and present in the request.
    items_data =
    # Apply common params (e.g., slicing for pagination)
    offset = commons.get("offset", 0)
    limit = commons.get("limit", 2) # Default limit for this handler if not from dep
    q = commons.get("q")

    response_data = {
        "query_params_used": commons,
        "items": items_data[offset : offset + limit]
    }
    if q:
        response_data["filter_query"] = q
        # Actual filtering logic would go here
        
    return JSONResponse(response_data)

@app.get("/users/me")
async def read_users_me(current_user: dict = Depends(get_current_user)):
    if current_user is None:
        return JSONResponse({"detail": "Not authenticated"}, status_code=401)
    return JSONResponse(current_user)

# To Test /items/:
# GET http://127.0.0.1:8000/items/?offset=0&limit=1&q=test
# Expected output (simplified):
# {
#   "query_params_used": {"limit": 1, "offset": 0, "q": "test"},
#   "items": [{"id": 1, "name": "Item A"}],
#   "filter_query": "test"
# }

# To Test /users/me:
# GET http://127.0.0.1:8000/users/me (no token) -> 401 Not authenticated
# GET http://127.0.0.1:8000/users/me with Header "X-Token: fake-super-secret-token"
# -> {"username": "testuser", "email": "user@example.com"}
```

In this simplified DI system:

* The Depends class acts as a marker.  
* MyMiniFastAPI inspects handler parameters. If a default value is Depends(dep_func), it calls dep_func.  
* The dependency dep_func can itself receive the request object or other query/path parameters if its signature declares them. Our DI resolver attempts to provide these.  
* The result of dep_func is injected into the handler.

This demonstrates the core mechanism: introspection of function signatures and dynamic execution of callables to provide required arguments. FastAPI's actual DI system is far more advanced, handling sub-dependencies, classes as dependencies, dependency caching, and integration with security scopes, but the fundamental principle of inspecting callables and injecting results is similar.

### Middleware: Adding Cross-Cutting Concerns

Middleware components are software that sit in the request/response processing pipeline, typically between the web server and the main application logic, or wrapping the application itself. They allow for the implementation of cross-cutting concerns—functionalities that apply to multiple (or all) endpoints—without cluttering the endpoint-specific handler logic. Common use cases include logging, authentication/authorization, CORS handling, response compression, custom header manipulation, and global error handling.

#### WSGI vs. ASGI Middleware

* **WSGI Middleware**: Typically a class with an __init__(self, app) method (where app is the WSGI application it wraps) and a __call__(self, environ, start_response) method. It can inspect/modify environ before calling the wrapped app, and can inspect/modify the status, headers, or body returned by the wrapped app.  
* **ASGI Middleware**: An ASGI middleware is itself an ASGI application. It takes another ASGI application (app) in its constructor. Its async def __call__(self, scope, receive, send) method can:  
  * Inspect or modify the scope before passing it to the wrapped self.app.  
  * Intercept or modify messages on the receive or send channels by providing wrapped versions of these callables to self.app.  
  * Decide to handle a request entirely and not call self.app at all (e.g., an authentication middleware denying access).  
  * Modify the response messages sent by self.app after it has processed the request. The structure of an ASGI app wrapping another ASGI app is a common and flexible pattern.

#### Implementing a Simple Logging Middleware for Our Framework

```python
# my_framework.py

class LoggingMiddleware:
    def __init__(self, app):
        self.app = app # The ASGI application to wrap (e.g., an instance of MyMiniFastAPI)
        print("LoggingMiddleware initialized.")

    async def __call__(self, scope: dict, receive: callable, send: callable):
        if scope['type'] == 'http':
            # For HTTP scopes, log request and response details
            print(f"--- LoggingMiddleware: Request START ---")
            print(f"Path: {scope['method']} {scope['path']}")
            if scope.get('query_string'):
                print(f"Query: {scope['query_string'].decode()}")
            
            # To log response status, we need to wrap the 'send' callable
            original_send = send 
            async def wrapped_send(message: dict):
                if message['type'] == 'http.response.start':
                    print(f"--- LoggingMiddleware: Response START ---")
                    print(f"Status: {message['status']}")
                    # One could also log headers here: print(f"Headers: {message['headers']}")
                
                # Pass the message to the original send
                await original_send(message)

                if message['type'] == 'http.response.body' and not message.get('more_body', False):
                    print(f"--- LoggingMiddleware: Response END ---")
            
            await self.app(scope, receive, wrapped_send) # Call the wrapped app with our wrapped_send
        
        elif scope['type'] == 'lifespan':
            print(f"--- LoggingMiddleware: Lifespan event ---")
            # For lifespan, we might just pass through or add specific lifespan logging
            await self.app(scope, receive, send)
        else:
            # For other scope types (e.g., websocket), pass through directly
            await self.app(scope, receive, send)

# To use this middleware, you'd wrap your MyMiniFastAPI instance:
# original_app_instance = MyMiniFastAPI()
# # Decorators like @original_app_instance.get("/") would be used here to define routes
# #... define routes on original_app_instance...
#
# app = LoggingMiddleware(original_app_instance) # This 'app' is now what Uvicorn runs

# Or, integrate middleware support into MyMiniFastAPI:
# In MyMiniFastAPI.__init__
# self.middleware_stack = # Initialize an empty list for middleware

# In MyMiniFastAPI
# def add_middleware(self, middleware_class, **options):
#     self.middleware_stack.append((middleware_class, options))

# In MyMiniFastAPI.__call__
# Before dispatching to handle_http, handle_lifespan, etc., build the wrapped app:
# wrapped_app = self # Start with the core app itself
# for mw_class, mw_options in reversed(self.middleware_stack): # Apply in reverse so first added is outermost
#     wrapped_app = mw_class(wrapped_app, **mw_options)
# await wrapped_app(scope, receive, send) # Call the fully wrapped application
```

#### Integrating Middleware into MyMiniFastAPI

A more robust way is to allow middleware to be added to the framework instance.

```python
# my_framework.py

# In MyMiniFastAPI class:

    def __init__(self):  
        self.routes =  
        self._middleware_chain = None # Will hold the final ASGI app after middleware wrapping  
        self.user_middleware = # List to store user-added middleware constructors  
        print("MyMiniFastAPI instance created.")

    def add_middleware(self, middleware_class: type, **options):  
        """Adds a middleware class and its instantiation options."""  
        self.user_middleware.append({"class": middleware_class, "options": options})  
        self._middleware_chain = None # Invalidate cached chain

    def _build_middleware_chain(self):  
        """Builds the chain of middleware wrapping the core application logic."""  
        # The core app logic is essentially self.dispatch_request or a similar method  
        # that handles routing and calling the actual endpoint handler.  
        # For simplicity, we'll consider a method \`_dispatch\` as the core app.  
        app_handler = self._dispatch   
          
        for mw_info in reversed(self.user_middleware): # Apply in reverse for intuitive order  
            mw_class = mw_info["class"]  
            mw_options = mw_info["options"]  
            app_handler = mw_class(app=app_handler, **mw_options)  
        return app_handler

    async def _dispatch(self, scope: dict, receive: callable, send: callable):  
        """The core request dispatcher, called after all middleware."""  
        # This method now contains the logic previously in __call__ for type dispatching  
        if scope['type'] == 'lifespan':  
            await self.handle_lifespan(scope, receive, send)  
        elif scope['type'] == 'http':  
            await self.handle_http(scope, receive, send) # handle_http now contains routing logic  
        elif scope['type'] == 'websocket':  
            print(f"WebSocket connection received. Path: {scope.get('path')}. Not yet implemented.")  
            # Minimal WebSocket handling:  
            # message = await receive()  
            # if message['type'] == 'websocket.connect':  
            #     await send({'type': 'websocket.accept'})  
            #     # Echo server example:  
            #     # while True:  
            #     #     msg = await receive()  
            #     #     if msg['type'] == 'websocket.receive':  
            #     #         await send({'type': 'websocket.send', 'text': msg['text']})  
            #     #     elif msg['type'] == 'websocket.disconnect':  
            #     #         break  
            # elif message['type'] == 'websocket.disconnect':  
            #     pass  
            pass  
        else:  
            print(f"Unsupported scope type in _dispatch: {scope['type']}")  
            # Consider raising NotImplementedError

    async def __call__(self, scope: dict, receive: callable, send: callable):  
        if self._middleware_chain is None:  
            self._middleware_chain = self._build_middleware_chain()  
          
        # print(f"MyMiniFastAPI __call__: Scope type {scope['type']}")  
        await self._middleware_chain(scope, receive, send)

# Example usage with integrated middleware:  
app_instance = MyMiniFastAPI()  
app_instance.add_middleware(LoggingMiddleware) # Add our logging middleware

@app_instance.get("/")  
async def root_handler(request: Request):  
    return PlainTextResponse("Root with logging middleware!")

# The 'app' variable Uvicorn runs is now the MyMiniFastAPI instance itself  
app = app_instance 
```

In this integrated approach:

* MyMiniFastAPI has an add_middleware method.  
* _build_middleware_chain constructs the chain of ASGI applications, where each middleware wraps the next one, with the core _dispatch method (which further routes to handle_lifespan, handle_http, etc.) at the innermost layer.  
* The main __call__ method of MyMiniFastAPI then invokes this fully wrapped application chain.

This middleware structure allows for modular addition of functionalities like logging, authentication, or custom header processing, keeping the endpoint handlers clean and focused on their specific tasks. The ability to wrap the send callable (as shown in LoggingMiddleware) provides fine-grained control over outgoing messages, enabling modification or logging of response status and headers. Starlette's BaseHTTPMiddleware offers a convenient base for HTTP-specific tasks 58, but understanding the pure ASGI middleware pattern is fundamental.

## Part 3: Putting It All Together and Looking Ahead

Having constructed the individual components of our FastAPI-like framework—from the basic ASGI application structure, routing, request and response objects, to path operation decorators, simplified validation, dependency injection, and middleware—it's time to see them integrated and consider what distinguishes this educational model from a production-grade framework like FastAPI.

### Assembling Our MyMiniFastAPI Framework

The following provides a consolidated view of the MyMiniFastAPI framework incorporating the key features developed. This example is illustrative and would require all previously defined classes (Request, Response, JSONResponse, PlainTextResponse, Depends, LoggingMiddleware) to be in the same file or properly imported.

```python
# my_framework_complete.py (Conceptual - assumes all classes are defined above)
import re
import json
import inspect
from urllib.parse import parse_qs # For Request.form and Request.query_params

# --- Re-define or import supporting classes first ---
# class Request:... (as defined in section 4.2 & 4.3)
# class Response:... (as defined in section 5.2)
# class JSONResponse(Response):... (as defined in section 5.3)
# class PlainTextResponse(Response):... (as defined in section 5.3)
# class Depends:... (as defined in section 8)
# class LoggingMiddleware:... (as defined in section 9)
# --- (Ensure these class definitions are complete and correct from previous sections) ---

class MyMiniFastAPI:
    def __init__(self):
        self.routes =
        self._middleware_chain = None
        self.user_middleware =
        print("MyMiniFastAPI instance created.")

    def add_middleware(self, middleware_class: type, **options):
        self.user_middleware.append({"class": middleware_class, "options": options})
        self._middleware_chain = None 

    def _build_middleware_chain(self):
        app_handler = self._dispatch
        for mw_info in reversed(self.user_middleware):
            mw_class = mw_info["class"]
            mw_options = mw_info["options"]
            app_handler = mw_class(app=app_handler, **mw_options)
        return app_handler

    async def _dispatch(self, scope: dict, receive: callable, send: callable):
        if scope['type'] == 'lifespan':
            await self.handle_lifespan(scope, receive, send)
        elif scope['type'] == 'http':
            await self.handle_http(scope, receive, send)
        elif scope['type'] == 'websocket':
            # Basic WebSocket handling (example: just accept and close)
            if scope['type'] == 'websocket':
                message = await receive()
                if message['type'] == 'websocket.connect':
                    await send({'type': 'websocket.accept'})
                    # Further WebSocket logic (e.g., echo, broadcast) would go here
                    # For now, just wait for disconnect
                    while True:
                        message = await receive()
                        if message['type'] == 'websocket.disconnect':
                            break
                elif message['type'] == 'websocket.disconnect':
                     pass # Already disconnected
            print(f"WebSocket connection received. Path: {scope.get('path')}. Basic handling.")
        else:
            print(f"Unsupported scope type in _dispatch: {scope['type']}")

    async def __call__(self, scope: dict, receive: callable, send: callable):
        if self._middleware_chain is None:
            self._middleware_chain = self._build_middleware_chain()
        await self._middleware_chain(scope, receive, send)

    async def handle_lifespan(self, scope: dict, receive: callable, send: callable):
        #... (as defined in section 2)
        print("Lifespan handler initiated.")
        while True:
            message = await receive()
            print(f"Lifespan message received: {message['type']}")
            if message['type'] == 'lifespan.startup':
                print("Framework: Lifespan startup sequence initiated...")
                await send({'type': 'lifespan.startup.complete'})
                print("Framework: Lifespan startup complete message sent.")
            elif message['type'] == 'lifespan.shutdown':
                print("Framework: Lifespan shutdown sequence initiated...")
                await send({'type': 'lifespan.shutdown.complete'})
                print("Framework: Lifespan shutdown complete message sent.")
                return

    def _compile_path(self, path: str):
        #... (as defined in section 3.3)
        param_names =
        path_regex_parts = ["^"]
        segments = path.split('/')
        for i, segment in enumerate(segments):
            if not segment: 
                if i == 0 or i == len(segments) -1: continue
                else: path_regex_parts.append("/"); continue
            if segment.startswith("{") and segment.endswith("}"):
                param_descriptor = segment[1:-1]
                param_name, converter_type = (param_descriptor.split(':', 1) + ["str"])[:2] # Ensure converter_type defaults to "str"
                param_names.append(param_name)
                if converter_type == "int": path_regex_parts.append(f"(?P<{param_name}>\\d+)")
                elif converter_type == "path": path_regex_parts.append(f"(?P<{param_name}>.+)")
                else: path_regex_parts.append(f"(?P<{param_name}>[^/]+)") # Default "str"
            else:
                path_regex_parts.append(re.escape(segment))
            if i < len(segments) - 1 and segments[i+1]: path_regex_parts.append("/")
            elif i < len(segments) - 1 and not segments[i+1] and i!= len(segments) -2 : path_regex_parts.append("/")
        if path.endswith("/") and (not path_regex_parts[-1].endswith("/?") if path_regex_parts else True) and path_regex_parts[-1]!= "^":
             if path_regex_parts and path_regex_parts[-1] == "/": path_regex_parts.append("?")
             else: path_regex_parts.append("/?")
        elif not path.endswith("/") and (path_regex_parts[-1] == "/" if path_regex_parts else False) and len(path_regex_parts) > 2 :
             path_regex_parts.pop()
        path_regex_parts.append("<span class="math-inline">"\)
final\_regex\_str \= ""\.join\(path\_regex\_parts\)
if final\_regex\_str\.endswith\("/</span>") and path!= "/" and not path.endswith("/"): final_regex_str = final_regex_str[:-2] + "<span class="math-inline">"
if final\_regex\_str \=\= "^/</span>": pass
        elif final_regex_str.endswith("//?<span class="math-inline">"\)\: final\_regex\_str \= final\_regex\_str\.replace\("//?</span>", "/?$")
        return re.compile(final_regex_str), param_names


    def add_route(self, path: str, handler: callable, methods: list = None):
        #... (as defined in section 3.3, using _compile_path)
        if methods is None: methods =
        processed_methods = [method.upper() for method in methods]
        is_dynamic = "{" in path and "}" in path
        path_regex, param_names = (self._compile_path(path) if is_dynamic else (None,))
        self.routes.append({
            "path_str": path, "handler": handler, "methods": processed_methods,
            "is_dynamic": is_dynamic
```

## **Works cited**

1. [FastAPI Python for Infra and Ops, Made Simple \- Last9, accessed June 1, 2025](https://last9.io/blog/fastapi-python/)  
2. [An Introduction to Using FastAPI \- Refine dev, accessed June 1, 2025](https://refine.dev/blog/introduction-to-fast-api/)  
3. [Implementing FastAPI from Scratch Using Only Pure Python \- DEV Community, accessed June 1, 2025](https://dev.to/leapcell/implementing-fastapi-from-scratch-using-only-pure-python-ni)  
4. [Articles \- Leapcell, accessed June 1, 2025](https://leapcell.io/articles)  
5. [First Steps \- FastAPI, accessed June 1, 2025](https://fastapi.tiangolo.com/tutorial/first-steps/)  
6. [ASGI (Asynchronous Server Gateway Interface) Specification ..., accessed June 1, 2025](https://asgi.readthedocs.io/en/latest/specs/main.html)  
7. [Difference Between ASGI and WSGI in Django \- GeeksforGeeks, accessed June 1, 2025](https://www.geeksforgeeks.org/difference-between-asgi-and-wsgi-in-django/)  
8. [Understanding Python web deployment \- Mirek Długosz personal website, accessed June 1, 2025](https://mirekdlugosz.com/blog/2025/understanding-python-web-deployment/)  
9. [What Is WSGI (Web Server Gateway Interface)?, accessed June 1, 2025](https://www.liquidweb.com/blog/what-is-wsgi/)  
10. [What Is a WSGI (Web Server Gateway Interface)? \- Built In, accessed June 1, 2025](https://builtin.com/data-science/wsgi)  
11. [Building Your Own Python Web Framework \- WSGI - TestDriven.io, accessed June 1, 2025](https://testdriven.io/courses/python-web-framework/wsgi/)  
12. [Python Web Applications: The basics of WSGI \- SitePoint, accessed June 1, 2025](https://www.sitepoint.com/python-web-applications-the-basics-of-wsgi/)  
13. [Uvicorn and Gunicorn? WSGI and ASGI? Coffee or Tea? : r/ToadProgramming \- Reddit, accessed June 1, 2025](https://www.reddit.com/r/ToadProgramming/comments/1aqgxx9/uvicorn_and_gunicorn_wsgi_and_asgi_coffee_or_tea/)  
14. [Asynchronous Server Gateway Interface \- Wikipedia, accessed June 1, 2025](https://en.wikipedia.org/wiki/Asynchronous_Server_Gateway_Interface)  
15. [ASGI Specification: Understanding its Core Principles \- Mangum, accessed June 1, 2025](https://mangum.io/asgi-specification-understanding-its-core-principles/)  
16. [Working with ASGI and HTTP \- Encode, accessed June 1, 2025](https://www.encode.io/articles/asgi-http)  
17. [Exploring ASGI: Python's Async Protocol for Web Apps \- DEV Community, accessed June 1, 2025](https://dev.to/leapcell/exploring-asgi-pythons-async-protocol-for-web-apps-35kh)  
18. [Working with HTTP requests in ASGI \- Encode, accessed June 1, 2025](https://www.encode.io/articles/working-with-http-requests-in-asgi)  
19. [How to Build a Python API from Scratch with FastAPI \- DEV Community, accessed June 1, 2025](https://dev.to/adeboyedn/how-to-build-a-python-api-from-scratch-with-fastapi-2p92)  
20. [FastAPI with Uvicorn: A Comprehensive Tutorial \- Orchestra, accessed June 1, 2025](https://www.getorchestra.io/guides/fastapi-with-uvicorn-a-comprehensive-tutorial)  
21. [FastAPI Uvicorn \- Tutorialspoint, accessed June 1, 2025](https://www.tutorialspoint.com/fastapi/fastapi_uvicorn.htm)  
22. [Think You Know FastAPI and ASGI? Let's Dive In! \- DEV Community, accessed June 1, 2025](https://dev.to/kfir-g/think-you-know-fastapi-and-asgi-lets-dive-in-164i)  
23. [How to use Django with Uvicorn, accessed June 1, 2025](https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/uvicorn/)  
24. [How To Set Up an ASGI Django App with Postgres, Nginx, and Uvicorn on Ubuntu 20.04, accessed June 1, 2025](https://www.digitalocean.com/community/tutorials/how-to-set-up-an-asgi-django-app-with-postgres-nginx-and-uvicorn-on-ubuntu-20-04)  
25. [What is Routing? \- Network Routing Explained \- AWS \- Amazon.com, accessed June 1, 2025](https://aws.amazon.com/what-is/routing/)  
26. [What is a Router in Web Development? Exploring Routes \- Oyova, accessed June 1, 2025](https://www.oyova.com/blog/what-is-a-route-web-dev/)  
27. [Routing \- Starlette, accessed June 1, 2025](https://www.starlette.io/routing/)  
28. [google/pygtrie: Python library implementing a trie data structure. \- GitHub, accessed June 1, 2025](https://github.com/google/pygtrie)  
29. [Trie Data Structure Tutorial - GeeksforGeeks, accessed June 1, 2025](https://www.geeksforgeeks.org/introduction-to-trie-data-structure-and-algorithm-tutorials/)  
30. [Trie \- Wikipedia, accessed June 1, 2025](https://en.wikipedia.org/wiki/Trie)  
31. [Path Parameters \- FastAPI, accessed June 1, 2025](https://fastapi.tiangolo.com/tutorial/path-params/)  
32. [Requests \- Starlette, accessed June 1, 2025](https://www.starlette.io/requests/)  
33. [starlette/docs/requests.md at master \- GitHub, accessed June 1, 2025](https://github.com/encode/starlette/blob/master/docs/requests.md)  
34. [urllib.parse — Parse URLs into components — Python 3.13.3 documentation, accessed June 1, 2025](https://docs.python.org/3/library/urllib.parse.html)  
35. [URL Decoding query strings or form parameters in Python - URLDecoder, accessed June 1, 2025](https://www.urldecoder.io/python/)  
36. [Question about Request.Body() · Issue #493 · encode/starlette \- GitHub, accessed June 1, 2025](https://github.com/encode/starlette/issues/493)  
37. [Starlette, accessed June 1, 2025](https://www.starlette.io/)  
38. [Responses \- Starlette, accessed June 1, 2025](https://www.starlette.io/responses/)  
39. [starlette/docs/responses.md at master \- GitHub, accessed June 1, 2025](https://github.com/encode/starlette/blob/master/docs/responses.md)  
40. [Pydantic Response Models in FastAPI: A Detailed Tutorial \- Orchestra, accessed June 1, 2025](https://www.getorchestra.io/guides/pydantic-response-models-in-fastapi-a-detailed-tutorial)  
41. [Path Operations \- KodeKloud Notes, accessed June 1, 2025](https://notes.kodekloud.com/docs/Python-API-Development-with-FastAPI/FastAPI-Basics/Path-Operations)  
42. [Fast API Path Operation Decorators: A Comprehensive Tutorial \- Orchestra, accessed June 1, 2025](https://www.getorchestra.io/guides/fast-api-path-operation-decorators-a-comprehensive-tutorial)  
43. [Creating Custom Metaclasses in Python \- HeyCoach - Blogs, accessed June 1, 2025](https://blog.heycoach.in/creating-custom-metaclasses/)  
44. [Think You're a Senior Python Dev? Prove It With These 15 Concepts, accessed June 1, 2025](https://www.index.dev/blog/advanced-python-concepts-senior-developers)  
45. [FastAPI Data Validation with Pydantic Explained \- Mindbowser, accessed June 1, 2025](https://www.mindbowser.com/fastapi-data-validation-pydantic/)  
46. [Models \- Pydantic, accessed June 1, 2025](https://docs.pydantic.dev/latest/concepts/models/)  
47. [Basic model usage \- Pydantic, accessed June 1, 2025](https://docs.pydantic.dev/1.10/usage/models/)  
48. [Pydantic Response Model \- KodeKloud Notes, accessed June 1, 2025](https://notes.kodekloud.com/docs/Python-API-Development-with-FastAPI/Advanced-FastAPI/Pydantic-Response-Model)  
49. [Dependency Injection in FastAPI \- GeeksforGeeks, accessed June 1, 2025](https://www.geeksforgeeks.org/dependency-injection-in-fastapi/)  
50. [Dependencies \- FastAPI, accessed June 1, 2025](https://fastapi.tiangolo.com/tutorial/dependencies/)  
51. [Understanding FastAPI's Built-In Dependency Injection \- Developer Service Blog, accessed June 1, 2025](https://developer-service.blog/understading-fastapis-built-in-dependency-injection/)  
52. [FastAPI – Dependencies \- GeeksforGeeks, accessed June 1, 2025](https://www.geeksforgeeks.org/fastapi-dependencies/)  
53. [What is a Pythonic Way for Dependency Injection? \- GeeksforGeeks, accessed June 1, 2025](https://www.geeksforgeeks.org/what-is-a-pythonic-way-for-dependency-injection/)  
54. [FastAPI Architecture - GeeksforGeeks, accessed June 1, 2025](https://www.geeksforgeeks.org/fastapi-architecture/)  
55. [Logging to SQLite using ASGI middleware \- Simon Willison's Weblog, accessed June 1, 2025](https://simonwillison.net/2019/Dec/16/logging-sqlite-asgi-middleware/)  
56. [Middleware \- Starlette, accessed June 1, 2025](https://www.starlette.io/middleware/)  
57. [How to write ASGI middleware \- PGJones, accessed June 1, 2025](https://pgjones.dev/blog/how-to-write-asgi-middleware-2021/)  
58. [The Core of FastAPI: A Deep Dive into Starlette \- DEV Community, accessed June 1, 2025](https://dev.to/leapcell/the-core-of-fastapi-a-deep-dive-into-starlette-59hc)