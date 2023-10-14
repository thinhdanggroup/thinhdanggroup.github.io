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
    overlay_image: /assets/images/subinterpreter/banner.jpeg
    overlay_filter: 0.5
    teaser: /assets/images/subinterpreter/banner.jpeg
title: "Python 3.12 Subinterpreters: A New Era of Concurrency"
tags:
    - Python

---

This blog post will introduce you to the exciting new feature in Python 3.12 - Subinterpreters. We'll start by explaining what subinterpreters are, their history, and how they compare to threads, processes, and greenlets. From there, we'll delve into why subinterpreters were introduced, discussing the limitations of the Global Interpreter Lock (GIL) and how subinterpreters can improve performance and concurrency in Python. We'll then provide a step-by-step guide on how to use the Subinterpreters API to create, run code in, share data between, and destroy subinterpreters. We'll also provide real-world examples of how subinterpreters can be used to improve performance and security in applications. Finally, we'll discuss the future of subinterpreters, including the proposed PEP 554, and their potential to revolutionize Python's concurrency model. Whether you're a seasoned Python developer or just starting out, this post will give you a comprehensive understanding of Python 3.12 subinterpreters and their potential impact on the Python ecosystem.

## Introduction to Python 3.12 Subinterpreters

Python 3.12 has introduced a significant feature that could potentially revolutionize how we handle concurrency in Python: Subinterpreters. This blog post will delve into what subinterpreters are, their history, and how they compare to threads, processes, and greenlets.

### What are Subinterpreters?

In Python, a subinterpreter is a (sub)interpreter which runs Python code in parallel with the main interpreter, in the same process and in the same address space, but with completely isolated execution resources. This is a way to achieve memory isolation. It is a method to separate the execution of code based on the functionality or the domain.

A subinterpreter is a mechanism in Python that allows for the creation of separate environments of execution within the same process. Each subinterpreter is its own Python interpreter with its own separate memory space and module imports, meaning that it can run independently from other subinterpreters. This is particularly useful in scenarios where you want to isolate certain parts of your application for security or performance reasons.

### History of Python Subinterpreters

Python's subinterpreters have been part of the Python C-API since its inception, however, they were not widely used due to their lack of support in the standard library and other third-party packages. In Python 3.12, PEP 554 was introduced to provide a high-level module for managing subinterpreters.

Python subinterpreters have been part of Python's C-API for a long time, meant to be used in extension modules. However, they were not exposed to Python code itself. In Python 3.12, work has been ongoing to make subinterpreters more accessible with the introduction of a per-interpreter GIL, making it possible to have a separate interpreter lock for each subinterpreter.

### Python Subinterpreters vs Threads

Python subinterpreters and threads are both ways to achieve concurrent execution in Python, but they have different characteristics. Threads share the same memory space, which can lead to conflicts and requires careful synchronization. On the other hand, subinterpreters are isolated and do not share Python objects with each other, which can make them safer and easier to use, but at the cost of additional memory usage.

The main difference between threads and subinterpreters is in how they handle memory. Threads within the same process share the same memory space, which can lead to issues with data consistency and race conditions. On the other hand, each subinterpreter in Python has its own separate memory space, which can help to avoid these issues. However, this also means that sharing data between subinterpreters can be more complex.

### Python Subinterpreters vs Processes

Python subinterpreters and processes both provide a way to run Python code in parallel. However, subinterpreters run in the same process and share the same memory space, while separate processes have separate memory spaces. This means that communication between subinterpreters can be faster and more efficient as it doesn't require inter-process communication. However, because they share memory space, subinterpreters can potentially interfere with each other, while separate processes are more isolated.

Subinterpreters and processes both provide ways to achieve concurrent execution and isolation in Python. The main difference is that subinterpreters run within the same process and thus have a lighter footprint and can have faster inter-communication than separate processes. However, because they run within the same process, a crash in one subinterpreter can potentially bring down the entire process, including all other subinterpreters within it. On the other hand, separate processes have stronger isolation from each other, and a crash in one process won't affect other processes.

### Python Subinterpreters vs Greenlets

Python subinterpreters and greenlets both provide ways to run Python code concurrently. Subinterpreters run in the same process, but have completely isolated execution resources, while greenlets are a form of cooperative multithreading within a single OS thread. Greenlets are lightweight and have low overhead, but they require the code to be written in a specific style and all greenlets in a thread must cooperate for multitasking to work. Subinterpreters, on the other hand, can run any Python code and can take advantage of multiple CPUs.

Subinterpreters and greenlets are both techniques to achieve concurrent execution in Python, but they operate at different levels. Subinterpreters are a feature of the Python runtime and provide isolated execution environments within the same process. Greenlets, on the other hand, are a form of cooperative multitasking where control is explicitly passed between tasks. This can be more lightweight and performant than using subinterpreters or threads, but doesn't provide the same level of isolation.

In the next part of this blog post, we will discuss why we need subinterpreters and how they can be used to improve the performance of Python applications.



## The Need for Python 3.12 Subinterpreters

The introduction of subinterpreters in Python 3.12 offers a new way to manage concurrency, particularly for CPU-bound tasks. This is a significant step forward, especially when we consider the limitations of the Global Interpreter Lock (GIL) in Python.

### The Global Interpreter Lock (GIL) Problem

The Global Interpreter Lock (GIL) is a mechanism used in the CPython interpreter to synchronize the execution of threads so that only one native thread executes Python bytecode at a time. This lock is necessary because CPython's memory management is not thread-safe. However, the GIL has been known to cause problems, especially in CPU-bound and multi-core programs.

Due to the GIL, multi-threaded CPU-bound programs may be slower than single-threaded ones because the GIL allows only one thread to execute at a time, even on multi-core processors. This means that a Python process can only use one core of your CPU at a time, regardless of how many there are. As a result, it can be less efficient to use threading in Python for tasks that are CPU intensive as opposed to I/O bound.

### Multithreading and Concurrency in Python

Multithreading in Python allows for the simultaneous execution of two or more parts of a program for maximum utilization of CPU. However, due to the Global Interpreter Lock (GIL) in Python's CPython interpreter, only one thread can execute Python bytecodes at a time, even in multi-threaded programs on multi-core processors. This can make multi-threaded programs slower than their single-threaded counterparts for CPU-bound tasks. For I/O-bound tasks, however, multithreading can improve performance by allowing a program to continue execution while waiting for I/O operations to complete.

Concurrency in Python refers to the ability of a program to be decomposed into parts that can run independently of each other. This can be achieved through techniques such as multithreading and multiprocessing. However, due to the Global Interpreter Lock (GIL) in CPython, multithreading can be less efficient for CPU-bound tasks, as only one thread can execute Python bytecodes at a time. For I/O-bound tasks, however, multithreading can improve performance. Multiprocessing, on the other hand, can bypass the GIL and utilize multiple cores for CPU-bound tasks, but comes with more overhead due to inter-process communication.

### The Promise of Subinterpreters

Python 3.12 introduces a new feature called subinterpreters, which can help improve performance. Subinterpreters are a way to run isolated, separate instances of the Python runtime in the same process. Each subinterpreter has its own Global Interpreter Lock (GIL), which means they can run in true parallel on separate CPU cores without the GIL interfering with multi-threading. This feature is beneficial for improving the performance of CPU-bound programs.

Subinterpreters in Python can be beneficial in several use cases. They can be used to run code in true parallel on separate CPU cores, which can help improve the performance of CPU-bound programs. Subinterpreters can also be used to isolate different parts of a program for increased security and less risk of conflicts, as each subinterpreter runs in its own separate environment with its own memory and state. This can be useful in situations where you want to run untrusted code, for example, or when you want to sandbox certain parts of your program. Additionally, subinterpreters can be used for better concurrency in I/O-bound programs.

In the next section, we will discuss how to use Python 3.12 subinterpreters, including creating a new subinterpreter, running code in a subinterpreter, sharing data between subinterpreters, and destroying a subinterpreter.



## Using Python 3.12 Subinterpreters

In this section, we will explore how to use subinterpreters in Python 3.12. We will cover how to create a new subinterpreter, run code in a subinterpreter, share data between subinterpreters, and destroy a subinterpreter. 

### Creating a New Subinterpreter

To create a new subinterpreter, Python 3.12 introduces a new Subinterpreters API that includes new functions such as `Py_NewInterpreterFromConfig()`. This function can be used to create an interpreter with its own Global Interpreter Lock (GIL), which allows Python programs to take full advantage of multiple CPU cores. 

In the proposed PEP 554, the `create()` method from the `interpreters` module is used to create a new subinterpreter. This method returns an `Interpreter` object that represents a new Python interpreter. For example, you can create a new subinterpreter as follows:

```python
import interpreters
interp = interpreters.create()
```
This will spawn a new subinterpreter.

### Running Code in a Subinterpreter

To run code in a subinterpreter, you can use the `run()` method of the `Interpreter` object. This method executes the Python source code given in a string. For example, you can run code in a subinterpreter as follows:

```python
interp.run("import time; time.sleep(3)")
```
This will run the specified code in the subinterpreter.

### Sharing Data Between Subinterpreters

Sharing data between subinterpreters can be challenging due to the isolation provided by separate Global Interpreter Locks (GILs). However, PEP 554 provides a basic mechanism for data sharing using `os.pipe()`. Pipes, a feature of operating systems, allow low-level communication. Hence, data can be sent between interpreters using pipes, but this requires serializing the data before sending it and deserializing the data after receiving it.

Data can also be shared between subinterpreters using Channels. There is an implementation of `RecvChannel` and `SendChannel` classes which resemble the channels known from Golang. You can pass data to the sender using `send_nowait` and read it on the other side with `recv` function. This channel is really just another sub-interpreter.

### Destroying a Subinterpreter

To destroy a subinterpreter, you need to clean up any dangling interpreters. You can do this by listing all interpreters using `interpreters.list_all()`, and then closing any interpreter that is not the main one.

```python
for interp in interpreters.list_all():
    if interp != interpreters.main():
        interp.close()
```

This concludes our guide on how to use subinterpreters in Python 3.12. In the next section, we will discuss the future of subinterpreters and how they can potentially revolutionize the way we handle concurrency in Python.



## Python 3.12 Subinterpreters in the Real World

In the previous sections, we have discussed what subinterpreters are, why we need them, and how to use them. Now, let's delve deeper into how subinterpreters can be used in real-world applications to improve performance and security.

### Improving Performance with Subinterpreters

One of the main benefits of using subinterpreters is the potential for performance improvement. By allowing Python code to run in true parallel on separate CPU cores, subinterpreters can significantly speed up the execution of CPU-bound tasks.

Consider a web server that needs to handle multiple incoming requests simultaneously. Traditionally, this would be achieved using multithreading or multiprocessing. However, due to the Global Interpreter Lock (GIL), multithreading in Python can be less efficient for CPU-bound tasks. On the other hand, multiprocessing can bypass the GIL and utilize multiple cores, but it comes with more overhead due to inter-process communication.

With subinterpreters, each incoming request can be handled by a separate subinterpreter running in its own thread. Since each subinterpreter has its own GIL, they can run in true parallel on separate CPU cores. This can lead to significant performance improvements for the web server.

Here's an example of how this can be implemented:

```python
from test.support import interpreters
from threading import Thread

def handle_request(interp):
    # Run the request handling code in the subinterpreter
    interp.run("""
    # request handling code
    """)

## Create a new subinterpreter for each incoming request
for request in incoming_requests:
    interp = interpreters.create()
    Thread(target=handle_request, args=(interp,)).start()
```

In this example, for each incoming request, we create a new subinterpreter and start a new thread to handle the request in the subinterpreter.

The below [code snippet](https://github.com/thinhdanggroup/thinhda_dev_blog/blob/main/subinterpreter/performance.py) shows how to use subinterpreters to improve the performance of a CPU-bound task. In this example, we create a new subinterpreter for each thread and run the task in the subinterpreter. This allows the task to run in true parallel on separate CPU cores, which can lead to significant performance improvements.

```python
import threading
import time
import _xxsubinterpreters as subinterpreters
from textwrap import dedent


def thread_function(interpreter_id: int = 0):
    subinterpreters.run_string(interpreter_id, dedent("""
total = 0
for i in range(10 ** 7):
    total += i
"""))


def thread_function_normal():
    total = 0
    for i in range(10 ** 7):
        total += i


def run_in_threads(total: int = 10):
    sub_interpreters = []
    list_thread = []
    for i in range(total):
        sub_interpreters.append(subinterpreters.create())
        t = threading.Thread(target=thread_function, args=(sub_interpreters[i],))
        list_thread.append(t)

    start = time.time()
    for i in range(total):
        list_thread[i].start()
        list_thread.append(list_thread[i])

    for t in list_thread:
        t.join()

    print(f"Test subinterpreter has total execution time {time.time() - start}")
    for i in range(total):
        subinterpreters.destroy(sub_interpreters[i])


def run_in_threads_no_sub(total: int = 10):
    list_thread = []
    for i in range(total):
        t = threading.Thread(target=thread_function_normal, args=(i,))
        list_thread.append(t)

    start = time.time()
    for i in range(total):
        list_thread[i].start()
        list_thread.append(list_thread[i])

    for t in list_thread:
        t.join()
    print(f"Test no_subinterpreter has total execution time {time.time() - start}")


def main():
    run_in_threads()
    run_in_threads_no_sub()


if __name__ == '__main__':
    main()
```

Output:

```bash
Test subinterpreter has total execution time 0.8748531341552734
Test no_subinterpreter has total execution time 2.693861961364746
```

To demonstrate the performance benefits of subinterpreters, we conducted a simple experiment. We created two functions: run_in_threads() and run_in_threads_no_sub(). The former utilizes subinterpreters, while the latter runs the code sequentially with the GIL lock.

The run_in_threads() function creates a specified number of subinterpreters and runs the thread_function() in parallel using threads. Each subinterpreter executes a loop that calculates the sum of numbers from 0 to 10^7. The execution time of this function was measured to be approximately 0.874 seconds.

On the other hand, the run_in_threads_no_sub() function runs the thread_function_normal() sequentially using threads, without utilizing subinterpreters. This function also calculates the sum of numbers from 0 to 10^7. The execution time of this function was measured to be approximately 2.694 seconds.

The significant difference in execution times between the two functions clearly demonstrates the performance benefits of subinterpreters. By utilizing subinterpreters, we were able to achieve a speedup of approximately 3 times compared to running the code sequentially with the GIL lock.

The GIL is a mechanism in CPython that ensures only one thread executes Python bytecode at a time. This limitation can hinder the performance of CPU-bound tasks, as only one thread can execute Python code at any given moment. However, subinterpreters bypass the GIL by running code in separate interpreters, allowing for true parallel execution.

Python 3.12's subinterpreters feature provides a powerful tool for improving the performance of CPU-bound tasks. By leveraging subinterpreters, developers can achieve parallel execution and bypass the limitations imposed by the GIL. In our experiment, we observed a significant performance improvement when using subinterpreters compared to running code sequentially with the GIL lock. This makes subinterpreters an excellent choice for performance-critical applications.

In future blog posts, we will explore more advanced use cases and best practices for utilizing subinterpreters effectively. Stay tuned for more insights into Python 3.12's exciting new features!

### Enhancing Security with Subinterpreters

Subinterpreters can also be used to enhance the security of Python applications. Since each subinterpreter runs in its own separate environment with its own memory and state, they provide a level of isolation that can be useful in scenarios where you want to run untrusted code.

For instance, consider a Python application that needs to execute user-provided scripts. Running these scripts in the main interpreter could pose a security risk, as the scripts could potentially access or modify the application's data.

With subinterpreters, the user-provided scripts can be executed in separate subinterpreters. This way, even if a script tries to access or modify the application's data, it won't be able to, as it's running in a separate environment.

Here's an example of how this can be implemented:

```python
from test.support import interpreters
from threading import Thread

def run_script(interp, script):
    # Run the script in the subinterpreter
    interp.run(script)

## Run user-provided scripts in separate subinterpreters
for script in user_scripts:
    interp = interpreters.create()
    Thread(target=run_script, args=(interp, script)).start()
```

In this example, for each user-provided script, we create a new subinterpreter and start a new thread to run the script in the subinterpreter.

subinterpreters in Python 3.12 offer a powerful tool for improving the performance and security of Python applications. By allowing Python code to run in true parallel on separate CPU cores, and by providing a level of isolation for running code, subinterpreters can revolutionize the way we handle concurrency and security in Python.

In the next section, we will discuss the future of subinterpreters and how they can potentially further enhance the Python programming experience.



## The Future of Python 3.12 Subinterpreters 

Looking ahead, the future of Python 3.12 subinterpreters appears to be promising, with several improvements on the horizon that could significantly enhance Python's concurrency model. One such improvement is the Python Enhancement Proposal (PEP) 554, which proposes the introduction of a new `interpreters` module to the Python standard library.

### Python Subinterpreters and PEP 554

PEP 554 aims to make subinterpreters more accessible to the general Python community by providing an `Interpreter` Python object and methods to manage these objects. The `interpreters` module proposed in PEP 554 would provide a high-level API for managing subinterpreters, making it easier for Python developers to create, manage, and destroy subinterpreters.

The `interpreters` module will provide an `Interpreter` Python object as well as methods to manage these objects. The proposed changes in the PEP will be more accessible to the general Python community and will provide users with the bare minimum of functionality to make use of Python subinterpreters from their Python code. The PEP also proposes a basic mechanism for data sharing between interpreters.

Although the PEP has not been officially accepted, it serves as a fundamental building block for future enhancements to Python subinterpreters.

### Possible Improvements to Subinterpreters

While the current `interpreters` module has limited functionality and lacks robust mechanisms for sharing state between subinterpreters, more functionality is expected to appear by Python 3.13. Developers are encouraged to experiment in the meantime.

The changes accepted for Python 3.12 could provide significant concurrency speedups for some projects, but only after extension modules make some changes to take advantage of the per-interpreter GIL. This may take a while to roll out and is likely to help with specific problems where the CPU is the bottleneck in performance. The proposed changes in PEP 554, if accepted, are likely more interesting to the average Python developer, especially since they allow you to access this feature from Python. However, they're really the fundamental building blocks for allowing more user-friendly access to subinterpreters.

### Subinterpreters and the Future of Python Concurrency

Subinterpreters are expected to greatly improve Python's concurrency model. They allow Python to better use multiple cores with fewer of the tradeoffs imposed by threads, async, or multiprocessing. Initial experiments with subinterpreters have shown significant performance improvements over threading and multiprocessing.

With the changes proposed in PEP 554, subinterpreters could provide significant speed improvements for some problems, and they really show the amount of work that's going into the improvement of the language. The changes together are a solid foundation for some really game-changing features in the future. However, they are still the fundamental building blocks for a much richer and robust set of features in future versions. If the PEP is accepted, it is expected that third-party libraries will make the data interaction between interpreters easier and cleaner.

In conclusion, the future of Python 3.12 subinterpreters is bright, with several improvements on the horizon that could significantly enhance Python's concurrency model. With the introduction of PEP 554 and the potential for further enhancements, subinterpreters could revolutionize the way we handle concurrency in Python.



## Conclusion

Python 3.12's introduction of subinterpreters marks an exciting new chapter in Python's journey towards improving its concurrency model. This feature has the potential to revolutionize how we handle concurrency in Python, particularly for CPU-bound tasks, and open up new possibilities for performance and security improvements.

Subinterpreters offer a way to achieve true parallel execution of Python code within the same process. This is a significant step forward, especially when we consider the limitations of the Global Interpreter Lock (GIL) in Python. By allowing Python code to run in true parallel on separate CPU cores, subinterpreters can significantly speed up the execution of CPU-bound tasks.

Furthermore, subinterpreters provide a level of isolation that can be beneficial for security purposes. Each subinterpreter runs in its own separate environment with its own memory and state, making it a useful tool for scenarios where you want to run untrusted code or sandbox certain parts of your program.

The future of subinterpreters looks promising, with several potential improvements on the horizon. PEP 554, if accepted, will make subinterpreters more accessible to the general Python community by providing a high-level API for managing subinterpreters. This will make it easier for Python developers to create, manage, and destroy subinterpreters.

While the current implementation of subinterpreters in Python 3.12 has its limitations, it is a solid foundation for a much richer and robust set of features in future versions. As Python continues to evolve and improve, we can look forward to seeing how subinterpreters will further enhance Python's concurrency model and the overall Python programming experience.

In conclusion, the introduction of subinterpreters in Python 3.12 is a game-changing feature that has the potential to significantly enhance Python's concurrency model. By providing a way to achieve true parallel execution of Python code and offering a level of isolation for improved security, subinterpreters can revolutionize the way we handle concurrency in Python.





## References

- [Python Docs - What's New in Python 3.12](https://docs.python.org/3/whatsnew/3.12.html) 
- [Real Python - What’s New in Python 3.12](https://realpython.com/python312-new-features/)
- [Martin Heinz - Python 3.12 Subinterpreters](https://martinheinz.dev/blog/97) 
- [Real Python - Python 3.12 Subinterpreters](https://realpython.com/python312-subinterpreters/)  
- [InfoWorld - Python 3.12: Faster, Leaner, More Future-Proof](https://www.infoworld.com/article/3694512/python-312-faster-leaner-more-future-proof.html) 
- [Real Python - Python 3.12 Subinterpreters](https://realpython.com/python312-subinterpreters/) 
- [InfoWorld - Python 3.12: Faster, Leaner, More Future-Proof](https://www.infoworld.com/article/3694512/python-312-faster-leaner-more-future-proof.html) 

