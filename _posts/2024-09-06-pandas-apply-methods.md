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
    overlay_image: /assets/images/pandas-apply-methods/banner.jpeg
    overlay_filter: 0.5
    teaser: /assets/images/pandas-apply-methods/banner.jpeg
title: "Optimizing Data Processing with Pandas Apply: Python vs. Cython"
tags:
    - python
    - pandas

---

This article explores the use of the 'apply' function in the Pandas library, a crucial tool for data manipulation and
analysis. It begins by explaining the importance of 'apply' in performing complex operations across data sets. The
discussion then shifts to comparing two approaches: using pure Python functions and leveraging Cython for enhanced
performance. Through detailed sections, readers will learn about the simplicity and flexibility of pure Python, ideal
for smaller data sets and quick prototyping. In contrast, Cython offers significant speed improvements, making it
suitable for large-scale data processing. The article provides performance comparisons, showcasing execution times and
resource efficiency. It also outlines specific use cases where each method excels, helping readers decide based on their
needs. The conclusion offers a framework for choosing between speed and simplicity, empowering data professionals to
optimize their workflows effectively.

### Introduction to Pandas Apply

Pandas is a powerful library for data manipulation and analysis, and the 'apply' function is one of its most versatile
tools. For data scientists and analysts, understanding why we need to use the 'apply' function is crucial. It allows for
the application of custom functions across a DataFrame, enabling complex operations that go beyond simple aggregations
or transformations.

![introduce](/assets/images/2024-09-06-python-apply-methods/introduce.jpeg)

#### Why We Need to Use Pandas Apply

The 'apply' function is essential when dealing with operations that are too intricate for vectorized solutions. While
vectorized operations are highly efficient, they may not accommodate the complexity required for certain tasks. Here, '
apply' comes into play, providing the flexibility to implement custom logic for each element, row, or column.

Consider a scenario where you need to apply a custom transformation to each row of a DataFrame, based on the values of
multiple columns. The 'apply' function allows you to define a function that encapsulates this logic and apply it
seamlessly across the dataset.

#### Example: Custom Transformation

Here's a simple example using `apply` to calculate a custom metric for each row:

```python
import pandas as pd

# Sample DataFrame
data = {"A": [1, 2, 3, 4], "B": [5, 6, 7, 8], "C": [9, 10, 11, 12]}
df = pd.DataFrame(data)


# Custom function with complex logic
def complex_operation(row):
    if row["A"] % 2 == 0:
        return row["A"] * row["B"] - row["C"]
    else:
        return row["A"] + row["B"] + row["C"]


# Apply the function
df["ComplexMetric"] = df.apply(complex_operation, axis=1)
print(df)
```

This example shows how `apply` can be used to compute a new column based on a custom calculation involving multiple
columns.

#### Flexibility and Customization

The true power of `apply` lies in its ability to handle complex logic that would be cumbersome or impossible with
standard DataFrame operations. Whether it's data cleaning, feature engineering, or custom aggregations, `apply` provides
the flexibility needed to tailor operations to specific requirements.

In the following sections, we will delve deeper into comparing the performance of `apply` with pure Python functions and
using Cython. We will explore when each approach is most effective, providing practical insights and examples for
optimal use.

### Pandas Apply with Pure Python Functions

![pure_python](/assets/images/2024-09-06-python-apply-methods/pure_python.jpeg)

Using pure Python functions with Pandas' `apply` is a straightforward and accessible approach for data manipulation.
This section will delve into how to implement `apply` with Python functions, emphasizing its simplicity and flexibility.

#### Implementation

The `apply` method allows you to apply a function along an axis of the DataFrame. Here's a basic example:

```python
import pandas as pd

## Sample DataFrame
df = pd.DataFrame({
    'A': [1, 2, 3],
    'B': [4, 5, 6]
})


## Function to add 10
def add_ten(x):
    return x + 10


## Applying the function
df['C'] = df['A'].apply(add_ten)
print(df)
```

#### Simplicity and Flexibility

The use of pure Python functions with `apply` is particularly beneficial when dealing with smaller datasets or when the
goal is to prioritize ease of use. The syntax is intuitive, and the function can be as simple or complex as needed.

#### Benefits of Native Python

1. **Readability**: Python functions are often more readable than complex vectorized operations. This makes it easier
   for others (or your future self) to understand the code.

2. **Ease of Debugging**: Debugging Python functions is generally more straightforward. You can use standard debugging
   tools and techniques to trace and fix issues.

#### Scenarios Where It Excels

- **Small Datasets**: When working with smaller datasets, the performance overhead of using pure Python functions is
  negligible, making this approach a good fit.

- **Custom Logic**: If your operation requires custom logic that's not easily vectorized, using a Python function
  with `apply` can be the best option.

- **Rapid Prototyping**: For quick experiments or prototyping, the flexibility and ease of Python functions allow for
  rapid development and iteration.

In summary, using pure Python functions with Pandas' `apply` is a powerful tool for data manipulation, particularly when
simplicity, readability, and ease of debugging are priorities. However, it's essential to consider performance
implications for larger datasets, which we'll explore in the following sections.

### Pandas Apply with Cython

![apply_cython](/assets/images/2024-09-06-python-apply-methods/apply_cython.jpeg)

Cython offers a powerful way to enhance the performance of Python code by compiling it into C. When working with Pandas,
integrating Cython with the `apply` function can lead to significant speed improvements, especially for computationally
intensive tasks. In this section, we'll explore how to set up Cython, write Cython functions, and apply them within
Pandas. We'll also discuss the trade-offs involved, such as increased complexity and the need for additional setup.

#### Setting Up Cython

To begin using Cython, you'll need to install it if you haven't already:

```bash
pip install cython
```

Once installed, you can start writing Cython code. Typically, this involves creating `.pyx` files where you can declare
C types and define functions.

#### Writing Cython Functions

Cython allows you to declare C types for variables, which can significantly boost performance by reducing dynamic typing
overhead. Here's an example of a simple Cython function:

```cython
## cython_functions.pyx
def csquare(double x):
    return x * x
```

In this example, `double[:] arr` declares a typed memory view for a NumPy array, and `cdef int i` and `cdef int n`
declare C integer types, enhancing performance.

#### Applying Cython Functions in Pandas

To use the Cython function with Pandas, compile the `.pyx` file using a setup script:

```python
## setup.py
from distutils.core import setup
from Cython.Build import cythonize

setup(ext_modules=cythonize("cython_functions.pyx"))
```

Compile the Cython code:

```bash
python setup.py build_ext --inplace
```

Now, you can use the compiled function in your Pandas workflow:

```python
import pandas as pd
import numpy as np
import time

from cython_functions import csquare

## Sample DataFrame
df = pd.DataFrame({"A": np.random.rand(100)})

start_time = time.time()
df["B"] = df["A"].apply(csquare)
cython_time = time.time() - start_time

print(f"Cython Time: {cython_time:.4f} seconds")
```

#### Trade-offs and Considerations

While Cython can greatly enhance performance, it introduces additional complexity:

- **Setup Overhead**: Compiling Cython code requires a setup script and additional build steps.
- **Complexity**: Writing Cython code involves understanding C types and memory management, which can be more complex
  than pure Python.
- **Maintainability**: Mixing Cython with Python can make the codebase harder to maintain, especially for teams
  unfamiliar with Cython.

Despite these trade-offs, the performance gains can be substantial, particularly for tasks involving large datasets or
intensive computations.

### Performance Comparison

![performance_comparison](/assets/images/2024-09-06-python-apply-methods/performance_comparison.jpeg)

When it comes to optimizing data processing tasks with Pandas, performance is a key consideration. The choice between
using a pure Python function or leveraging Cython with Pandas' `apply` method can significantly impact execution times
and efficiency. Let's dive into a detailed comparison, backed by benchmarks and real-world examples, to understand these
differences.

#### Execution Times

The primary reason developers consider using Cython is the potential for faster execution times. Cython compiles Python
code to C, allowing for more efficient execution of computationally intensive tasks. Here's a simple benchmark to
illustrate the difference:

```python
import pandas as pd
import numpy as np
import time

from cython_functions import csquare

## Sample DataFrame
df = pd.DataFrame({"A": np.random.rand(100000000)})


## Pure Python function
def square(x):
    return x * x


## Timing pure Python
start_time = time.time()
df["B"] = df["A"].apply(square)
python_time = time.time() - start_time

## Timing Cython
start_time = time.time()
df["B"] = df["A"].apply(csquare)
cython_time = time.time() - start_time

print(f"Pure Python Time: {python_time:.4f} seconds")
print(f"Cython Time: {cython_time:.4f} seconds")
```

Result:

```shell
(base) ➜  compare_3 git:(main) ✗ python compare_3.py
Pure Python Time: 15.9472 seconds
Cython Time: 12.8075 seconds
```

#### Efficiency and Resource Utilization

Beyond execution time, efficiency in terms of memory usage and CPU utilization is also crucial. Cython can optimize data
types and reduce overhead, leading to better resource management. However, the benefits can vary based on the complexity
of operations.

##### Memory Usage

Cython's ability to use static typing allows for more efficient memory usage. Here's how memory usage can differ:

- **Pure Python**: Uses dynamic typing, which can lead to higher memory consumption due to overhead.
- **Cython**: Allows for static typing, reducing memory usage by optimizing data storage.

### Use Cases for Pure Python Functions

![use case pure python](/assets/images/2024-09-06-python-apply-methods/usecase_pure_python.jpeg)

While Cython offers performance benefits, there are scenarios where using pure Python with Pandas' `apply` is more
advantageous. Let's explore some use cases where simplicity, rapid prototyping, and ease of maintenance are prioritized.

#### Simplicity and Readability

Pure Python functions are often easier to read and understand, especially for teams that may not have experience with
Cython. This simplicity can be crucial when working on collaborative projects where code clarity is a priority. For
instance, a straightforward transformation like converting temperatures from Celsius to Fahrenheit can be easily
implemented and understood using a pure Python function:

```python
import pandas as pd

## Sample DataFrame
df = pd.DataFrame({'Celsius': [0, 20, 37, 100]})


## Pure Python function
def celsius_to_fahrenheit(celsius):
    return (celsius * 9 / 5) + 32


## Applying the function
df['Fahrenheit'] = df['Celsius'].apply(celsius_to_fahrenheit)
```

#### Rapid Prototyping

When speed of development is more critical than execution speed, pure Python functions allow for quick iteration and
testing. This is particularly useful in the early stages of a project where the focus is on validating ideas rather than
optimizing performance.

#### Ease of Maintenance

Maintaining code written in pure Python is generally more straightforward due to its interpretative nature. Debugging is
simpler since you don't have to deal with the compilation step required by Cython. This can be a significant advantage
in projects that require frequent updates or changes.

#### Flexibility in Development

Pure Python allows for greater flexibility when dealing with dynamic or complex logic that may not fit neatly into a
Cython-optimized approach. For example, handling data transformations that involve conditional logic or custom
aggregations might be more naturally expressed in Python:

```python
## Custom transformation with conditional logic
def custom_transformation(x):
    if x > 50:
        return x * 2
    else:
        return x / 2


## Applying the transformation
df['Transformed'] = df['Celsius'].apply(custom_transformation)
```

#### Integration with Other Libraries

Pure Python functions can be seamlessly integrated with other libraries like NumPy or SciPy, leveraging their powerful
data structures and operations without the need for Cython. This integration can enhance functionality while keeping the
codebase simple and maintainable.

By focusing on these aspects, you can leverage the strengths of pure Python functions with Pandas' `apply`, ensuring
efficient development and maintenance without the added complexity of Cython.

### Use Cases for Cython

![use case cython](/assets/images/2024-09-06-python-apply-methods/usecase_cython.jpeg)

Cython shines in scenarios where performance is paramount, particularly with Pandas' `apply`. Let's delve into cases
where the speed benefits of Cython outweigh its complexity, focusing on large datasets, computationally intensive
operations, and real-time data processing needs.

#### Large Datasets

When dealing with massive datasets, the overhead of Python can become a bottleneck. Cython allows for significant
speedups by compiling Python code into C, reducing execution time. For example, if you're processing millions of rows in
a DataFrame, using Cython can drastically reduce the time required for data transformations.

#### Computationally Intensive Operations

Tasks involving heavy computations, such as numerical simulations or complex mathematical transformations, can benefit
greatly from Cython. By declaring variable types and optimizing loops, you can achieve performance that approaches that
of native C code.

```pyx
## Example of a computationally intensive operation
def cython_heavy_computation(x):
    cdef float result = 0
    for i in range(1000):
        result += x * i
    return result


## Applying the function
df['Computation'] = df['Value'].apply(cython_heavy_computation)
```

#### Parallel Processing

Cython can leverage parallel processing using OpenMP, enabling multi-core utilization. This is particularly useful for
tasks that can be parallelized, enhancing performance in data-intensive applications.

```pyx
from cython.parallel import prange
cimport cython

@cython.boundscheck(False)
@cython.wraparound(False)
def cython_parallel_function(double[:] arr):
    cdef int i
    cdef int n = len(arr)
    cdef double[:] result = arr.copy()

    # Use OpenMP for parallel processing
    with nogil, parallel():
        for i in prange(n, nogil=True):
            result[i] = arr[i] ** 2

    return result
```

#### Integration with C/C++ Libraries

For projects that require integration with existing C/C++ libraries, Cython offers seamless interoperability. This
capability is essential for leveraging optimized solutions available in C/C++ without sacrificing performance.

By understanding these contexts, you can strategically choose Cython to maximize efficiency in your data processing
tasks.


![conclusion](/assets/images/2024-09-06-python-apply-methods/conclusion.jpeg)