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
    overlay_image: /assets/images/cython/banner.jpeg
    overlay_filter: 0.5
    teaser: /assets/images/cython/banner.jpeg
title: "Securing Your Python Code with Cython: A Comprehensive Guide"
tags:
    - Cython
    - Security

---

In this comprehensive guide, we delve into the world of Cython, a superset of Python that combines the ease of Python
with the speed of C, and how it can be used to protect your Python code. We start off by understanding what Cython is,
its relationship with Python, and how it works. We then guide you through the process of migrating your existing Python
projects to Cython, discussing the steps involved, the tools required, and the best practices to follow. We also take a
look at both the benefits and drawbacks of using Cython, providing a balanced view. Finally, we provide a detailed guide
on how to use Cython to protect your Python code from being read by users, including the steps to follow, the tools you
can use, and best practices. Whether you're a seasoned Python developer or just starting out, this guide will provide
you with the knowledge you need to protect your Python code effectively using Cython.

## Introduction

In an age where data is the new oil, protecting your intellectual property, including your code, is paramount. Python,
being an interpreted language, presents some challenges in this regard. However, there are ways to mitigate these
challenges and one such way is by using Cython.

Cython is a superset of the Python language, allowing Python code to be compiled into C or C++ code. This not only
provides significant performance improvements but also adds a layer of security by making it more difficult for casual
snoopers to reverse engineer your code.

In this blog post, we will delve deeper into the world of Cython, exploring what it is, how to migrate your existing
Python project to use Cython, the benefits and drawbacks of using Cython, and most importantly, how you can use Cython
to protect your Python code from being read by users.

So, let's dive in!

### Understanding Cython

Cython is a programming language that is essentially a superset of Python. This means that any valid Python code is also
valid Cython code. Cython allows you to write C extensions for Python with a syntax that is very similar to Python. It
combines the ease of writing Python code with the speed of C.

Cython and Python have a close relationship. Cython is built on top of Python and extends its capabilities. It allows
you to write Python code that can be compiled to C code for improved performance.

The primary purpose of using Cython is to improve the performance of Python code. By writing performance-critical parts
of your code in Cython, you can achieve significant speedups compared to pure Python.

Cython was created by Stefan Behnel in 2007 as a way to optimize Python code. It has since grown in popularity and is
now widely used in the scientific computing and data analysis communities.

Cython works by translating Python code into C code and then compiling it into a binary module that can be imported and
used like a regular Python module. This allows the code to run faster than pure Python code.

Cython can provide performance boosts ranging from a few percent to several orders of magnitude, depending on the task.
It is especially effective for numerical operations or any operations not involving Python's own internals.

By compiling Python modules into binaries, Cython can also make it more difficult for casual snooping. However, it is
not foolproof and determined individuals can still decompile or reverse-engineer the binaries.

Cython can generate C libraries that can be bundled with existing Python code. It allows developers to make spot changes
to the code, rather than rewriting the whole application, making it easier to integrate with C or C++ code.

Cython's approach is incremental, allowing developers to gradually translate hot spots into Cython for performance gains
without rewriting the entire application. This makes it easier to maintain and update code.

However, Cython is not without its drawbacks. For work bound by Python's native object types, the speedups won't be
large. It provides minimal speedup for conventional Python code and native Python data structures. The performance gains
are more significant for numerical operations and operations not involving Python's own internals. Additionally, Cython
code runs fastest when written in 'pure C', but any references to Python-native code can become performance bottlenecks.

Debugging Cython code can be more challenging compared to pure Python code. Since Cython code is compiled to C,
traditional Python debugging tools may not work. However, Cython provides its own tooling for profiling and analyzing
the performance of Cython code. It's important to profile and test the code to identify and resolve any issues.

### Migrating Python Projects to Cython

Migrating an existing Python project to use Cython can be an efficient way to optimize your code and protect it from
casual snooping. This process involves a few steps and requires some tools. Let's walk through the process together.

#### Steps to Migrate Python Project to Cython Using Annotations

1. **Install Cython**: The first step is to install Cython on your system. You can do this using pip, the Python package
   installer, with the command `pip install cython`.

2. **Identify Performance-Critical Parts of Your Code**: Not all parts of your code may benefit from being converted to
   Cython. Identify the parts of your code that are performance-critical and could benefit from the speed improvements
   that Cython can provide.

3. **Replace Python Code with Cython Code**: Once you've identified the parts of your code that you want to optimize,
   you can start replacing the Python code with Cython code. This involves adding type hints and variable annotations using the cython module and using
   Cython-specific features.

4. **Build and Compile the Cython Code**: After replacing the Python code with Cython code, you need to build and
   compile the Cython code. This will generate a .cpp file, which can then be compiled into a binary module.

5. **Test the Performance of the Migrated Code**: After compiling the Cython code, test the performance of the migrated
   code to ensure it meets your expectations.

6. **Optimize the Cython Code Further if Needed**: If the performance of the migrated code is not up to your
   expectations, you can optimize the Cython code further.

7. **Repeat Steps 4-6 Until You Achieve the Desired Performance Improvements**: Keep repeating these steps until you
   achieve the desired performance improvements.

#### Tools Required for Migration

There are several tools that can be helpful for migrating a Python project to Cython:

- **Cython**: The main tool for converting Python code to Cython code.
- **Python**: The original Python interpreter is needed as a runtime environment for executing the Cython code.
- **C Compiler**: Cython code needs to be compiled to C code and then to machine code using a C compiler.
- **Build System**: A build system like Make or CMake can be used to automate the compilation and linking process.
- **Testing Framework**: A testing framework like pytest can be used to verify the correctness of the migrated code.

#### Common Challenges in Migration

Migrating a Python project to Cython can come with its own set of challenges:

- **Understanding Cython Syntax and Features**: Cython has its own syntax and features that may be unfamiliar to Python
  developers.
- **Dealing with Python-Specific Code**: Cython may not support all Python features, so some code may need to be
  modified or rewritten.
- **Handling C Dependencies**: If the Python project has dependencies on C libraries, they need to be properly handled
  in the Cython code.
- **Debugging and Profiling**: Debugging and profiling Cython code can be more challenging than Python code.
- **Performance Optimization**: While Cython can improve performance, it requires careful optimization to achieve the
  desired results.

#### Best Practices for Migration

When migrating a Python project to Cython, there are a few best practices you should follow:

- **Start with Small, Performance-Critical Parts**: Identify the parts of the code that would benefit the most from
  Cython and start with those.
- **Measure Performance**: Before and after migrating the code, measure the performance to ensure the desired
  improvements are achieved.
- **Use Static Typing**: Use static typing where possible to help Cython generate more efficient C code.
- **Profile and Optimize**: Use profiling tools to identify performance bottlenecks and optimize the Cython code
  accordingly.
- **Test Thoroughly**: Thoroughly test the migrated code to ensure it works correctly and doesn't introduce any new
  bugs.

Migrating a Python project to Cython can be a powerful way to optimize your code and protect it from
being read by users. However, it's a process that requires careful planning and execution. With the right approach and
tools, you can successfully migrate your Python project to Cython and reap the benefits it offers.

### Protecting Python Code with Cython

One of the major advantages of using Cython is its ability to protect Python code from being read by users. This is
achieved by compiling Python code into C code, which is then compiled into machine code. The compiled code is harder to
reverse engineer, providing a layer of protection for your code.

Let's take a detailed look at how to use Cython to protect your Python code, the steps involved, the tools required,
best practices, and a case study.

#### Steps to Protect Python Code with Cython

To protect Python code with Cython, you can follow these steps([Source code](https://github.com/thinhdanggroup/thinhda_dev_blog/tree/main/cython_example)):

1. **Install Cython**: Begin by installing Cython on your system. You can do this using pip, the Python package installer, with the command `pip install cython`.

2. **Write Python Code with Annotations**: Write the Python code that you want to protect. Use type annotations to specify the types of your variables, functions, and classes. In this example, I have two Python files: `main.py` and `util.py`. The `util.py` file contains two functions: `extract_blog_posts` and `extract_url`. These functions are annotated with `@cython.annotation_typing(True)`, which tells Cython to interpret the annotations as type declarations.
    ```python
    # distutils: language=c++
    # cython: language_level=3
    import requests
    from bs4 import BeautifulSoup
    import cython
    
    
    @cython.annotation_typing(True)
    def extract_blog_posts(content):
        soup = BeautifulSoup(content, 'html.parser')
        blog_posts = soup.find_all('article', class_='archive__item')
    
        for post in blog_posts:
            title = post.find('h2', class_='archive__item-title').text.strip()
            link = post.find('a')['href']
            print(f'Title: {title}\nLink: {link}\n')
    
    
    @cython.annotation_typing(True)
    def extract_url(url):
        response = requests.get(url)
        extract_blog_posts(response.text)

    ```
   
    The comments at the top of your Cython file are known as compiler directives. They provide instructions to the Cython compiler on how to compile your code.

    - `#distutils: language=c++`: This directive tells Cython to compile the code as C++ code. Without this directive, Cython would compile the code as C code. C++ allows for more advanced features like classes and exceptions, which might be necessary depending on your code [cython.readthedocs.io](https://cython.readthedocs.io/en/latest/src/userguide/wrapping_CPlusPlus.html).
    - `#cython: language_level=3`: This directive sets the Python language level that Cython should use when compiling your code. By setting language_level=3, you're telling Cython to use Python 3 syntax. If you don't specify a language level, Cython defaults to language level 2 (Python 2 syntax), unless it's overridden by compiler arguments or the CYTHON_LANGUAGE_LEVEL environment variable [cython.readthedocs.io](https://cython.readthedocs.io/en/latest/src/userguide/language_basics.html).

3. **Create a Cython Setup File**: Create a setup.py file for my Python code. This file is used to build my Python code into a Python extension module. Here's an example of what the setup file might look like:

   ```python
   from distutils.core import setup
   from distutils.extension import Extension
   from Cython.Build import cythonize

   # define an extension that will be cythonized and compiled
   ext = Extension(name="cutil", sources=["util.py"])
   setup(ext_modules=cythonize(ext))
   ```

   In this setup file, an Extension object is created with the name "cutil" and the source file "util.py". This Extension object is then passed to the `cythonize` function, which compiles the Python code into a Python extension module.

5. **Compile with Cython**: Use Python to compile your Python code into C code. This is done by running the setup file with the command `python setup.py build_ext --inplace`. This will generate a .cpp file and a .so file.

6. **Import and Use the Cython Module**: You can now import the compiled Cython module in your Python code just like any other Python module. For example, in your `main.py` file, you can import the `cutil` module with `import cutil`.
    ```python 
   import cutil
    
    def main():
        url = "https://thinhdanggroup.github.io/"
        print("Scraping blog from the website...\n")
        cutil.extract_url(url)
    
    
    if __name__ == "__main__":
        main()

    ```

7. **Distribute the Compiled Code**: Distribute the compiled .so file instead of the original Python code to protect your intellectual property. Note that the .so file is platform-specific, so you will need to compile your Cython code on each platform that you want to support.

Remember, Cython is a superset of Python, so you can start with your existing Python code and incrementally add type annotations to optimize performance. Also, note that while Cython can help protect your code by making it harder to reverse engineer, it does not provide absolute protection.

#### Best Practices for Code Protection with Cython

When using Cython for code protection, it is important to follow some best practices:

- **Minimize the Exposure of Your Original Python Source Code**: Distribute only the compiled modules and not the
  original Python source code.
- **Use Static Typing**: Use static typing where possible to help Cython generate more efficient C code.
- **Regularly Update and Patch Your Code**: Keep your code up to date with the latest security patches and updates to
  minimize vulnerabilities.
- **Use Other Code Protection Techniques**: In addition to Cython, consider using other code protection techniques like
  obfuscation and encryption.

#### Case Study: Protecting Python Code with Cython

Dropbox is an example of a company that has successfully used Cython to protect their Python code. Dropbox used Cython
to compile their Python code into C and implemented various protection mechanisms to make it harder to reverse engineer
and modify the code. This included techniques like using specialized obfuscation, encryption, and anti-debugging
techniques. While no protection method is foolproof, using Cython provided an additional layer of code protection for
Dropbox's client software.

Cython is a powerful tool for optimizing Python code and protecting it from being read by users. By
following the steps outlined above and adhering to best practices, you can effectively use Cython to protect your Python
code.

## Conclusion

In this blog post, we have taken an in-depth look at Cython, a powerful tool that enables Python developers to optimize
their code and protect it from being read by users.

Cython, being a superset of Python, allows for Python code to be compiled into C or C++ code, providing significant
performance improvements. More importantly, it adds a layer of security by making the code more difficult to reverse
engineer. This makes Cython a valuable tool for protecting your intellectual property.

We have discussed the process of migrating a Python project to Cython, which involves identifying performance-critical
parts of your code, replacing Python code with Cython code, building and compiling the Cython code, and then testing and
optimizing the migrated code. We have also highlighted some of the challenges that may arise during this process and
shared best practices to ensure a successful migration.

Furthermore, we have explored how Cython can be used to protect Python code. By compiling Python code into C code, which
is then compiled into machine code, the compiled code is harder to reverse engineer, providing a layer of protection for
your code. We have also outlined the steps involved in this process, the tools required, best practices, and a case
study of Dropbox, a company that has successfully used Cython to protect their Python code.

However, it's important to note that while Cython can make it more difficult for someone to access your source code, it
may not provide absolute protection. Therefore, it's recommended to use other code protection techniques like
obfuscation and encryption in addition to Cython.

In conclusion, Cython is a powerful tool that offers Python developers a way to optimize their code for better
performance and protect it from being read by users. By understanding how to use Cython effectively, you can leverage
its benefits to enhance your Python projects.

## References

- [Intro to Just Enough Cython to be Useful - Peter Baumgartner](https://www.peterbaumgartner.com/blog/intro-to-just-enough-cython-to-be-useful/)
- [What is Cython? Python at the speed of C - InfoWorld](https://www.infoworld.com/article/3250299/what-is-cython-python-at-the-speed-of-c.html)
- [Securing Python Code with Cython - Cisco Blogs](https://blogs.cisco.com/developer/securingpythoncodewithcython01)
- [Cython Documentation](https://cython.readthedocs.io/)
- [What is Cython? Python at the speed of C - InfoWorld](https://www.infoworld.com/article/3250299/what-is-cython-python-at-the-speed-of-c.html)
- [Securing Python Code with Cython - Cisco Blogs](https://blogs.cisco.com/developer/securingpythoncodewithcython01)
- [How do I protect Python code from being read by users - StackOverflow](https://stackoverflow.com/questions/261638/how-do-i-protect-python-code-from-being-read-by-users) 
