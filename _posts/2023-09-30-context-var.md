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
    overlay_image: /assets/images/context_var/banner.jpeg
    overlay_filter: 0.5
    teaser: /assets/images/context_var/banner.jpeg
title: "Demystifying ContextVar in Python"
tags:
    - Python

---

This blog post will demystify ContextVar, a simple way to share values between functions and coroutines in Python. We'll start with an introduction to ContextVar, explaining what it is, its purpose, origin, basic structure, and how it works in Python. Next, we'll provide a step-by-step guide on how to use ContextVar, including how to define, set, get, and delete a value from ContextVar, with examples. We'll then compare ContextVar with ThreadLocal, global variables, and thread local storage in Python, discussing their similarities, differences, and when to use one over the other. Finally, we'll discuss the advantages and limitations of using ContextVar, common errors when working with ContextVar, and best practices for using it. By the end of this blog post, you'll have a solid understanding of ContextVar and how to use it effectively in your Python projects.

## Introduction

In the world of concurrent programming, sharing state between different parts of the code can be a tricky business. As Python developers, we have several tools at our disposal to handle this, one of which is the `ContextVar` class. Introduced in Python 3.7 as part of the `contextvars` module, `ContextVar` provides a simple and efficient way to manage, store, and access context-local state.

In this blog post, we will dive deep into the workings of `ContextVar`. We will answer questions such as: What is `ContextVar`? How do we use it? How does it differ from alternatives like `ThreadLocal` and global variables? And, why is it a crucial tool for Python developers, especially those working with concurrent code?

Understanding `ContextVar` is important for Python developers because it provides a mechanism to manage context variables effectively, especially for asynchronous tasks. It helps keep track of variables per asynchronous task and prevents context values from unexpectedly bleeding into other code when used in async/await code. This can be particularly useful for managing context-related data like request-related data in web applications, profiling, tracing, and logging in large code bases.

So, whether you're a seasoned Python developer or just starting your journey, this blog post will provide you with valuable insights into `ContextVar` and how to use it effectively in your Python projects. Let's get started!



## What is ContextVar?

`ContextVar` is a class in the `contextvars` module in Python. It is used to declare and work with Context Variables. Context Variables are used to manage, store, and access context-local state. They are created at the top module level and never in closures.

The purpose of `ContextVar` is to provide a way to manage, store, and access context-local state. This is useful in concurrent code where context managers that have state should use Context Variables instead of `threading.local()` to prevent their state from bleeding to other code unexpectedly. It is designed to handle cases where thread-local variables are insufficient for asynchronous tasks that execute concurrently in the same operating system thread.

Context Variables were introduced in Python 3.7, as part of the `contextvars` module. The feature was proposed in PEP 567.

The `ContextVar` class has a few methods: `get()`, `set()`, and `reset()`. `get()` returns a value for the context variable for the current context. `set()` sets a new value for the context variable in the current context. `reset()` resets the context variable to the value it had before the `ContextVar.set()` that created the token was used.

`ContextVar` works by providing a way to manage, store, and access context-local state. You can create a new `ContextVar` with a name and optional default value. The `get()` method returns the value for the context variable in the current context, or the default value if one was set. The `set()` method sets a new value for the context variable in the current context. The `reset()` method resets the context variable to its previous value.

Let's look at a simple example of how to use `ContextVar`:

```python
from contextvars import ContextVar

# Create a new ContextVar with a name and optional default value
var: ContextVar[int] = ContextVar('var')

# Set a new value for the context variable in the current context
token1 = var.set('new value')
token2 = var.set('new value 1')

# Get the value for the context variable in the current context
print(var.get())  # Outputs: new value 1

# Reset the context variable to its previous value
var.reset(token2)

print(var.get())  # Outputs: new value
var.reset(token1)

# Now the variable has no value again, so var.get() would raise a LookupError
try:
    print(var.get())
except LookupError:
    print("Variable has no value")  # Outputs: Variable has no value
```

In the next sections, we will discuss how `ContextVar` differs from alternatives like `ThreadLocal` and global variables, and why it is a crucial tool for Python developers, especially those working with concurrent code.



## How to use ContextVar

In this section, we will walk through a step-by-step guide on how to define, set, get, and delete a value from `ContextVar`. We will also include examples to illustrate each of these operations.

### Defining a ContextVar

Defining a `ContextVar` is straightforward. You simply instantiate a `ContextVar` object and provide a name for the variable. You can also provide an optional default value.

```python
from contextvars import ContextVar

## Define a ContextVar with a name and an optional default value
my_var: ContextVar[int] = ContextVar('my_var', default=42)
```

In this example, we have created a new `ContextVar` named 'my_var' with a default value of 42.

### Setting a Value for ContextVar

To set a new value for a `ContextVar` in the current context, you use the `set` method.

```python
## Set a new value for the ContextVar in the current context
token = my_var.set(100)
```

In this example, we have set the value of 'my_var' in the current context to 100.

### Getting a Value from ContextVar

To get the value of a `ContextVar`, you use the `get` method.

```python
## Get the value of the ContextVar in the current context
value = my_var.get()
print(value)  # Outputs: 100
```

In this example, we have retrieved the value of 'my_var' in the current context, which is 100.

### Deleting a Value from ContextVar

Deleting a value from a `ContextVar` is done using the `reset` method together with a token. The `reset` method restores the variable to its previous value or removes it from the context if it was not set before.

```python
## Reset the ContextVar to its previous value
my_var.reset(token)

## Now the variable has no value again, so my_var.get() would raise a LookupError
try:
    print(my_var.get())
except LookupError:
    print("Variable has no value")  # Outputs: Variable has no value
```

In this example, we have reset 'my_var' to its previous value. Since 'my_var' was not set before we set it to 100, it now has no value again.

And that's it! You now know how to define, set, get, and delete a value from `ContextVar`. In the next sections, we will discuss how `ContextVar` differs from alternatives like `ThreadLocal` and global variables, and why it is a crucial tool for Python developers, especially those working with concurrent code.



## ContextVar vs ThreadLocal

Both `ContextVar` and `ThreadLocal` are mechanisms in Python for handling data that is specific to a particular context or thread. They both allow for data isolation in the context of multi-threading, where each thread can have its own instance of the variable. 

### Similarities

Both `ContextVar` and `ThreadLocal` provide a way to store and access data that is local to a specific context or thread. This allows different parts of the code to access this data without the need for explicit argument passing. In the case of `ContextVar`, the context is not necessarily bound to a thread, but the concept is similar.

In addition, both `ContextVar` and `ThreadLocal` are used for managing state in concurrent code. They provide a way to store and access data that is local to a specific context or a specific thread respectively. In other words, each thread will have a different set of data for each variable stored in thread local storage or `ContextVar`.

### Differences

The key difference between `ContextVar` and `ThreadLocal` is their behavior with coroutines. While they behave similarly in multi-threading projects, in the context of coroutines, using `ThreadLocal` is dangerous as different coroutines share the same thread, breaking the safety of the `ThreadLocal` mechanism. `ContextVar`, on the other hand, is designed to handle this situation correctly.

`ThreadLocal` is tied to individual threads and each thread will have its own set of data for each variable stored in thread local storage. On the other hand, `ContextVar` is tied to a specific context and can be used to prevent state from bleeding to other code unexpectedly, when used in concurrent code.

### When to use ContextVar over ThreadLocal

`ContextVar` should be used over `ThreadLocal` when working with coroutines in Python. This is because coroutines in the same thread share the same `ThreadLocal` instance, which can lead to unexpected behavior, whereas `ContextVar` handles this situation correctly.

`ContextVar` is more suitable when you need to manage variables per thread or per coroutine. It is particularly useful when you want to update legacy programs that use global state to be concurrent.

### When to use ThreadLocal over ContextVar

You might prefer to use `ThreadLocal` over `ContextVar` in multi-threading projects where coroutines are not involved. This is because `ThreadLocal` and `ContextVar` behave very similarly in these scenarios.

In conclusion, while both `ContextVar` and `ThreadLocal` are useful tools for managing state in concurrent code, `ContextVar` provides several advantages over `ThreadLocal`, especially when working with coroutines.



## ContextVar vs Global Variables

In this section, we will compare `ContextVar` with global variables in Python, highlighting their differences, and discussing the benefits of using `ContextVar` over global variables.

### Similarities

At first glance, `ContextVar` and global variables might appear similar as they both allow different parts of the code to access shared data without the need for explicit argument passing. However, the way they manage and isolate this shared data is fundamentally different.

### Differences

One of the key differences between `ContextVar` and global variables is the scope of their data. Global variables, as the name suggests, are global to the entire program. Any part of the code can access and modify a global variable. This can lead to unexpected behavior in multi-threaded or concurrent code, where different threads or tasks might interfere with each other's modifications of the global variable.

On the other hand, `ContextVar` variables act like global variables but are local to a specific context. If you set a certain value in one thread, every time you read it again in the same thread, you'll get back that value, but if you read it from another thread, it will be different. This allows for data isolation in the context of multi-threading or concurrent code, where each thread or task can have its own instance of the variable.

Another difference is the level of control over the state of the variable. With global variables, it's difficult to control when and where the variable's state is changed, especially in large codebases or in multi-threaded code. In contrast, `ContextVar` provides methods to explicitly set, get, and reset the variable's value, giving you more control over the variable's state.

### When to use ContextVar over Global Variables

Given the differences outlined above, `ContextVar` should be used over global variables in concurrent or multi-threaded code. The data isolation provided by `ContextVar` prevents unexpected behavior caused by different threads or tasks interfering with each other's modifications of the variable.

`ContextVar` is also more suitable when you need to manage variables per thread or per coroutine. It is particularly useful when you want to update legacy programs that use global state to be concurrent.

### Benefits of ContextVar over Global Variables

The main benefit of using `ContextVar` over global variables is the ability to manage and isolate data in concurrent or multi-threaded code. `ContextVar` allows each thread or task to have its own instance of the variable, preventing unexpected behavior caused by different threads or tasks interfering with each other's modifications of the variable.

Another benefit is the level of control over the variable's state. `ContextVar` provides methods to explicitly set, get, and reset the variable's value, giving you more control over the variable's state.

In conclusion, while global variables can be useful in certain scenarios, `ContextVar` provides several advantages, especially when working with concurrent or multi-threaded code.


## Advantages, Limitations, and Best Practices

Understanding the advantages and limitations of `ContextVar` allows us to make the most of this feature and avoid common pitfalls. In this section, we will discuss the benefits and potential drawbacks of using `ContextVar`, common errors that might occur, and best practices for using `ContextVar` effectively.

### Advantages of Using ContextVar

The main advantage of using `ContextVar` is that it provides a way to manage, store, and access context-local state. This is especially useful in concurrent code, where it can prevent state from bleeding to other code unexpectedly. Context Variables are also natively supported in `asyncio` and don't require extra configuration.

`ContextVar` also offers a level of control over the variable's state. It provides methods to explicitly set, get, and reset the variable's value, giving you more control over the variable's state.

### Limitations of Using ContextVar

One limitation of `ContextVar` is that it does not support context variables in generators and asynchronous generators. Also, it does not directly support context managers, although it can be used by context managers to store their state. Additionally, `ContextVar` objects do not have `__module__` and `__qualname__` attributes, which can complicate the pickling process.

### Common Errors When Working with ContextVar

Common errors when working with `ContextVar` include calling `ContextVar.get()` when there is no value for the variable in the current context and no default value is provided; this will raise a `LookupError`. Another error is calling `ContextVar.reset(token)` with a token object created by another variable or in a different context, which will raise a `ValueError`. Also, calling `ContextVar.reset(token)` with a token that has already been used once to reset the variable will raise a `RuntimeError`.

### Best Practices for Using ContextVar

When using `ContextVar`, it's important to follow best practices to avoid common pitfalls and make the most of this feature.

- `ContextVar` should be created at the top module level and never in closures.

- When setting a new value for the context variable in the current context, it's a good practice to save the returned token. This token can be used later to reset the context variable to its previous value.

- Always handle exceptions properly when getting the value of a context variable with `ContextVar.get()` and resetting the context variable with `ContextVar.reset(token)`. 

- When using `ContextVar` in concurrent code, ensure that it doesn't bleed state to other code unexpectedly.

In conclusion, while `ContextVar` is a powerful tool for managing context-local state in Python, it's important to understand its advantages and limitations, be aware of common errors, and follow best practices to use it effectively.



## Conclusion

In this blog post, we explored `ContextVar`, a powerful feature in Python that provides a way to manage, store, and access context-local state. We discussed its origins, purpose, and how it works. We also compared it with alternatives like `ThreadLocal` and global variables, and discussed the benefits of using `ContextVar` over these alternatives.

One of the key takeaways is the importance of `ContextVar` in concurrent programming. `ContextVar` provides a way to manage state in concurrent code, preventing state from bleeding to other code unexpectedly. This is particularly useful in asynchronous tasks, where many tasks can be running in the same thread but at different times or interleaved with each other.

We also learned about the advantages and limitations of using `ContextVar`. While `ContextVar` provides several benefits, such as natively supporting `asyncio` and offering more control over the variable's state, it also has some limitations, such as not supporting context variables in generators and asynchronous generators.

In addition, we discussed common errors when working with `ContextVar` and best practices to avoid these errors. These include creating `ContextVar` at the top module level, saving the token when setting a new value, and handling exceptions properly when getting and resetting the variable's value.

Understanding and using `ContextVar` effectively can greatly enhance your Python programming, especially when working with concurrent code. It provides a simple and efficient way to manage context-local state, giving you more control over the state of your program. So, whether you're a seasoned Python developer or just starting your journey, mastering `ContextVar` is a valuable addition to your Python toolkit.





## References

- [Introduction to ContextVar in Python](https://docs.python.org/3/library/contextvars.html) 
- [Using ContextVar in Python](https://peps.python.org/pep-0567/) 
- [ContextVar vs Global Variables in Python](https://rolisz.ro/2020/05/15/context-variables-in-python/) 
- [ContextVar vs Thread Local Storage in Python](https://superfastpython.com/thread-context-variables-in-python/) 
- [ContextVar vs ThreadLocal in Python](https://valarmorghulis.io/tech/201904-contextvars-and-thread-local/) 
- [ContextVar vs Global Variables in Python](https://rolisz.ro/2020/05/15/context-variables-in-python/) 
- [ContextVar vs Thread Local Storage in Python](https://superfastpython.com/thread-context-variables-in-python/) 
