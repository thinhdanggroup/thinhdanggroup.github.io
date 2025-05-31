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
    overlay_image:  /assets/images/pytest-asyncio-v1/banner.jpeg
    overlay_filter: 0.5
    teaser:  /assets/images/pytest-asyncio-v1/banner.jpeg
title: "Navigating the Async Waves: A Deep Dive into pytest-asyncio 1.0 and Migration Strategies"
tags:
    - Python
    - Testing
    - pytest-asyncio
    - Migration

---

The Python ecosystem for asynchronous programming continues to mature, and testing asynchronous code effectively is paramount. The `pytest-asyncio` plugin has long been a cornerstone for developers working with `asyncio` in their Pytest suites. With the landmark release of version 1.0.0 on May 25, 2025, `pytest-asyncio` introduces significant changes aimed at simplifying the API, improving performance, and aligning more closely with modern `asyncio` practices.

This comprehensive guide will explore the key features and breaking changes in `pytest-asyncio` 1.0, with a primary focus on the removal of the `event_loop` fixture. It will then provide a detailed, step-by-step migration path, complete with code examples, to help developers smoothly transition their existing test suites to this new version.

## What's New in pytest-asyncio 1.0? A Refined Approach to Async Testing

The 1.0.0 release of `pytest-asyncio` is more than just a version bump; it represents a thoughtful evolution of the library. The changes are designed to offer a more intuitive and efficient testing experience.

### Key enhancements and changes include:

* **Removal of the Deprecated `event_loop` Fixture:** This is the most significant breaking change. The `event_loop` fixture, which was a common way to access and manage the asyncio event loop within tests and fixtures, has been completely removed. This change pushes towards a more standardized way of handling event loops, as will be detailed in the migration section.  
* **New Event Loop Creation Strategy:** Scoped event loops (e.g., module-scoped or class-scoped loops) are now created only once per scope, rather than potentially multiple times. This optimization can lead to reduced fixture setup overhead and faster test collection times, especially in large test suites with many scoped asynchronous fixtures or tests.  
* **Enhanced `loop_scope` Flexibility:** The `loop_scope` argument for the `@pytest.mark.asyncio` marker has become more flexible. It no longer strictly requires a Pytest Collector (like a class or module node) to exist at the level of the specified scope. For instance, a test function can be marked with `@pytest.mark.asyncio(loop_scope="class")` even if it's not part of a class, aligning its behavior more closely with the `scope` argument of `pytest_asyncio.fixture`. This consistency simplifies understanding and usage.  
* **Preliminary Python 3.14 Support:** Keeping pace with Python's evolution, version 1.0.0 includes preliminary support for the upcoming Python 3.14.  
* **Bug Fixes:** Several bugs have been addressed, including an error when using Pytest's `--setup-plan` option, issues with unsuppressed import errors when using `--doctest-ignore-import-errors`, and a "fixture not found" error related to package-scoped loops.

These changes collectively aim to provide a more robust, performant, and developer-friendly plugin for testing asynchronous Python applications. The removal of the `event_loop` fixture, while a breaking change, paves the way for a cleaner and more `asyncio`\-native approach to test writing.

## The Elephant in the Room: Removal of the `event_loop` Fixture

The most impactful change in `pytest-asyncio` 1.0 is undoubtedly the removal of the `event_loop` fixture. For years, developers relied on this fixture to:

* Run coroutines in synchronous tests using `event_loop.run_until_complete()`.  
* Obtain a reference to the event loop in asynchronous tests and fixtures, often to pass it explicitly to legacy APIs or for fine-grained control.  
* Define custom event loops with specific scopes or types by overriding the `event_loop` fixture.

The rationale behind its removal is to streamline the API, reduce boilerplate, and encourage patterns more idiomatic to `asyncio` itself. The explicit `event_loop` fixture could sometimes lead to inconsistencies in loop management, especially when combined with Pytest's own fixture scoping. The new approach centralizes loop control via markers and dedicated fixtures like `event_loop_policy`, offering a clearer and more robust system. The new approach relies on:

1. **`asyncio.get_running_loop()`:** For accessing the current event loop within an `async` function, this standard library function is now the preferred method.  
2. **`@pytest.mark.asyncio(loop_scope="...")`:** To control the lifecycle and scope of the event loop used for a test or a group of tests.  
3. **`@pytest_asyncio.fixture(loop_scope="...")`:** To control the lifecycle and scope of the event loop for asynchronous fixtures.  
4. **`event_loop_policy` fixture:** For scenarios requiring different types of event loops (e.g., using `uvloop`), this fixture can be overridden.

This shift means that tests and fixtures no longer explicitly request an `event_loop` argument to get a loop instance. Instead, the loop is implicitly managed by `pytest-asyncio` based on markers and configuration, and `async` code can access the current loop via `asyncio.get_running_loop()` when necessary. This reduces boilerplate and makes the test code cleaner.

## Migration Guide: Upgrading Your Tests to pytest-asyncio 1.0

Migrating to `pytest-asyncio` 1.0 requires careful attention, primarily due to the `event_loop` fixture's removal. The official documentation provides guidance for migrating from older versions like v0.21, which forms the basis of these steps.

### Prerequisites and Initial Considerations: `asyncio_mode`

Before diving into code changes, it's important to understand `pytest-asyncio`'s operating modes: `strict` and `auto`. This is configured via the `asyncio_mode` option in your `pytest.ini` (or `pyproject.toml`, `tox.ini`) or via the `--asyncio-mode` command-line flag.

* **`strict` mode (default):**  
  * Async tests *must* be marked with `@pytest.mark.asyncio`.  
  * Async fixtures *must* be decorated with `@pytest_asyncio.fixture`.  
  * This mode is designed for projects that might use multiple asynchronous libraries (e.g., `asyncio` and `trio`) and need `pytest-asyncio` to only handle explicitly marked items. 
* **`auto` mode:**  
  * `pytest-asyncio` automatically adds the `@pytest.mark.asyncio` marker to all `async def` test functions.  
  * It also treats all `async def` fixtures as `pytest-asyncio` fixtures, even if they are decorated with the standard `@pytest.fixture`. This significantly simplifies fixture definition in `auto` mode, as you no longer need to import and use `@pytest_asyncio.fixture` for most async fixtures.
  * This mode is simpler for projects using `asyncio` exclusively.

The migration steps below generally assume you'll adapt to the requirements of your chosen mode. If you're in `auto` mode, some explicit `pytest_asyncio.fixture` decorations might not be strictly necessary but can be good for clarity.

### Step 1: Addressing `event_loop` Fixture Usage

This step focuses on tests and fixtures that directly used the `event_loop` argument.

1. **Convert Synchronous Users to Asynchronous:** If you have synchronous tests (`def test_...`) or synchronous fixtures (`@pytest.fixture def my_fixture...`) that used the `event_loop` fixture (typically via `event_loop.run_until_complete()`), these must be converted to be asynchronous (`async def`).
   * **Old (synchronous test using `event_loop`):**

```python
# conftest.py or test file
# (Illustrative - http_client not defined here)
# async def http_client(url):...

def test_http_client_sync(event_loop):
    url = 'http://httpbin.org/get'
    resp = event_loop.run_until_complete(http_client(url)) # Fictional http_client
    assert b'HTTP/1.1 200 OK' in resp
    pass # Placeholder

```

   * **New (migrated to asynchronous test):**

```python
import pytest
import asyncio

# async def http_client(url):...

@pytest.mark.asyncio
async def test_http_client_async():
    url = 'http://httpbin.org/get'
    resp = await http_client(url)
    assert b'HTTP/1.1 200 OK' in resp
    await asyncio.sleep(0) # Placeholder for actual async operation

```

2. **Adapt Asynchronous Users:** For tests and fixtures that were already `async def` but took `event_loop` as an argument:  
   * Remove the `event_loop` argument from their definition.  
   * If the loop instance is genuinely needed inside the function (e.g., for an API that doesn't automatically use the running loop), obtain it using `loop = asyncio.get_running_loop()`. Many modern `asyncio` APIs (like `asyncio.sleep`) use the running loop by default.  
   * **Old (asynchronous test explicitly using `event_loop` argument):**

    ```python
    import asyncio
    import pytest

    # pytestmark = pytest.mark.asyncio # Example of module-level marker

    @pytest.mark.asyncio
    async def test_example_old(event_loop): # event_loop injected
        await asyncio.sleep(0.01, loop=event_loop) # Explicitly passing loop

    ```

   * **New (migrated asynchronous test):**

    ```python
    import asyncio
    import pytest

    @pytest.mark.asyncio
    async def test_example_new():
        # loop = asyncio.get_running_loop() # Get loop if needed for specific APIs
        await asyncio.sleep(0.01) # asyncio.sleep uses running loop by default

    ```

The following table summarizes the common patterns for migrating `event_loop` usage:

| Old Way (pre-1.0, using `event_loop` fixture) | New Way (pytest-asyncio 1.0) | Notes |
| ----- | ----- | ----- |
| `def test_sync_needs_loop(event_loop): event_loop.run_until_complete(my_coro())` | `@pytest.mark.asyncio async def test_async_equivalent(): await my_coro()` | Convert test to be `async`. |
| `@pytest.mark.asyncio async def test_uses_loop_arg(event_loop): await func(loop=event_loop)` | `@pytest.mark.asyncio async def test_uses_running_loop(): loop = asyncio.get_running_loop(); await func(loop=loop)` (if `func` truly needs `loop` arg) | Or simply `await func()` if `func` uses `get_running_loop()` internally or `asyncio.sleep`\-like calls. |
| `@pytest.fixture def my_sync_fixture_using_loop(event_loop): event_loop.run_until_complete(...)` | `@pytest_asyncio.fixture async def my_async_fixture(): await...` (or `@pytest.fixture` in auto mode) | Convert fixture to be `async`. |
| `@pytest.fixture(scope="module") def event_loop(): loop = MyCustomLoop(); yield loop; loop.close()` | (Removed) Define `loop_scope="module"` on tests/fixtures. Use `event_loop_policy` fixture for custom loop types. | Loop creation/closing is handled by `pytest-asyncio` based on `loop_scope` and `event_loop_policy`. |

This table provides a quick reference for the most common transformations. The removal of direct `event_loop` injection simplifies test signatures and encourages reliance on `asyncio`'s own mechanisms for loop management where possible.

### Step 2: Configuring Event Loop Scopes (Handling Custom `event_loop` Implementations)

If your test suite previously defined custom `event_loop` fixtures, often to change the loop's scope (e.g., to `module` or `session`) or to use a specific loop implementation (like `uvloop`), these require specific migration steps.

1. **Identify Original Scope and Purpose:** For each custom `event_loop` fixture you had:  
   * Determine its `scope` (e.g., `"function"`, `"class"`, `"module"`, `"session"`).  
   * Determine if it was providing a custom loop *type* or just a different *scope*.  
2. **Apply `loop_scope` for Scoped Loops:** If the custom `event_loop` fixture was primarily for changing the scope:  
   * For tests that relied on this custom-scoped loop, apply the `@pytest.mark.asyncio(loop_scope="your_original_scope")` marker.  
   * For asynchronous fixtures that relied on this custom-scoped loop, apply the `@pytest_asyncio.fixture(loop_scope="your_original_scope")` decorator (or `@pytest.fixture(scope="your_original_scope")` in `auto` mode, then also ensure the test using it has the correct `loop_scope`).  
   * **Example: Migrating a module-scoped loop setup:**  
     * **Old (custom module-scoped `event_loop`):**

    ```python
    # conftest.py
    import pytest
    import pytest_asyncio # Assuming older version or explicit decoration
    import asyncio

    @pytest.fixture(scope="module")
    def event_loop(request): # Custom module-scoped loop
        loop = asyncio.get_event_loop_policy().new_event_loop()
        yield loop
        loop.close()

    @pytest_asyncio.fixture(scope="module") # Async fixture using module-scoped loop
    async def my_module_fixture(event_loop): # Implicitly uses the above
        await asyncio.sleep(0.01, loop=event_loop)
        return "module_data"

    # test_module.py
    # (in older versions, test might implicitly use the module-scoped loop if fixture did)
    @pytest.mark.asyncio
    async def test_something_module_scope(my_module_fixture, event_loop):
        assert my_module_fixture == "module_data"
        await asyncio.sleep(0.01, loop=event_loop)

    ```

     *  **New (migrated using `loop_scope`):**

    ```python
    # conftest.py
    import pytest
    import pytest_asyncio # If in strict mode for fixtures
    import asyncio

    # The custom event_loop fixture for scope is REMOVED.
    # If a custom loop *type* was needed, use event_loop_policy (see below).

    @pytest_asyncio.fixture(loop_scope="module") # Explicitly declare loop_scope for the fixture
    async def my_module_fixture():
        # loop = asyncio.get_running_loop() # Access if needed
        await asyncio.sleep(0.01)
        return "module_data"

    # test_module.py
    # To run all tests in this module with a module-scoped loop:
    # pytestmark = pytest.mark.asyncio(loop_scope="module")
    # or individually:
    @pytest.mark.asyncio(loop_scope="module") # Test now explicitly uses module-scoped loop
    async def test_something_module_scope(my_module_fixture):
        assert my_module_fixture == "module_data"
        # loop = asyncio.get_running_loop() # Access if needed
        await asyncio.sleep(0.01)


    ```

    - This new approach is more declarative. The `loop_scope` argument directly tells `pytest-asyncio` how to manage the loop for that specific test or fixture.  

3. **Use `event_loop_policy` for Custom Loop Types:** If your custom `event_loop` fixture was providing a different event loop *policy* (e.g., to use `uvloop`), you should now override the `event_loop_policy` fixture.

    ```python
    # conftest.py
    import pytest
    import asyncio
    # import uvloop # If using uvloop

    class MyCustomEventLoopPolicy(asyncio.DefaultEventLoopPolicy): # Or your specific policy
        # def new_event_loop(self):
        #     return uvloop.new_event_loop() # Example for uvloop
        pass

    @pytest.fixture(scope="session") # Policy fixture scope should typically be broad
    def event_loop_policy():
        return MyCustomEventLoopPolicy()

    ```

    `pytest-asyncio` will then use this policy to create event loops for all relevant scopes.

4. **Global Default Scopes (Alternative/Complementary):** If many tests or fixtures in your suite share a common non-function scope, you can set global defaults in your Pytest configuration file (e.g., `pytest.ini`):

    ```python
    # pytest.ini
    [pytest]
    asyncio_default_test_loop_scope = module
    asyncio_default_fixture_loop_scope = module

    ```

    Possible values are `function`, `class`, `module`, `package`, `session`. This can reduce the need for explicit `loop_scope` markers everywhere.  

5. **Remove Old Custom `event_loop` Fixture Definitions:** Once the scopes (and types, if applicable) are correctly handled by `loop_scope` arguments, default configurations, or the `event_loop_policy` fixture, you can and should remove your old custom `event_loop` fixture definitions.  

6. **A Note on `asyncio_default_fixture_loop_scope`:** The migration guide for v0.21 suggests setting `asyncio_default_fixture_loop_scope = function` if not already set, to silence a deprecation warning. Documentation for version 0.26.0 indicates that if this option is unset, it defaults to the fixture's own scope, but will default to `function` in future versions. This implies that `function` is the forward-looking default and a safe choice unless a broader scope is explicitly needed for many fixtures.

### Step 3: Adapting Asynchronous Fixtures

Ensure your `async def` fixtures are correctly defined and scoped:

1. **Use Correct Decorators:**  
   * In `strict` mode (the default): All `async def` fixtures must be decorated with `@pytest_asyncio.fixture`.  
   * In `auto` mode: Standard `@pytest.fixture` can be used for `async def` fixtures, as `pytest-asyncio` will handle them automatically. Using `@pytest_asyncio.fixture` in `auto` mode is also fine and can be clearer.  
2. **Specify `loop_scope`:** If an asynchronous fixture requires a specific event loop scope (e.g., it was intended to share a module-scoped loop with tests), ensure its `loop_scope` is set in its decorator: `@pytest_asyncio.fixture(loop_scope="module")`. This was highlighted as a fix for issues where fixtures and tests could end up on different loops if scopes weren't aligned.  
3. **Accessing the Loop (If Needed):** The example provided for `my_global_resource` comments out `loop = asyncio.get_running_loop()`. To make this point more concrete, consider adding a small, separate example where `asyncio.get_running_loop()` is actively used within a fixture. For example:

    ```python
    import pytest_asyncio
    import asyncio

    @pytest_asyncio.fixture(loop_scope="session") # Example of a session-scoped async fixture
    async def my_global_resource():
        # loop = asyncio.get_running_loop() # Get loop if needed
        # resource = await setup_global_resource(loop)
        resource = {"data": "initialized"}
        await asyncio.sleep(0.1) # Simulate async setup
        yield resource
        # await teardown_global_resource(resource, loop)
        await asyncio.sleep(0.1) # Simulate async teardown

    ```

### Step 4: Final Review and Testing

After making these changes, a thorough run of your entire test suite is crucial.

* **Execute all tests:** `pytest`  
* **Watch for common errors:**  
  * `RuntimeError: Event loop is closed`: This can happen if there's a mismatch in how loop lifecycles are expected versus how they are managed, or if an operation tries to use a loop that `pytest-asyncio` has already cleaned up.  
  * `RuntimeError: Task <Task pending name='...' coro=<...>> attached to a different loop`: This indicates that parts of your test setup (e.g., a fixture) and the test itself might be running on different event loop instances. This was a known issue in older versions under certain conditions and is generally addressed by correct `loop_scope` usage.  
  * Unexpected changes in test behavior: Altered fixture setup/teardown timing due to different loop scoping can sometimes subtly affect tests.  
* The experience of projects like `cockpit-project`, which encountered "compatibility issues" requiring workarounds when upgrading (though specific code changes were not detailed in the snippet), underscores the necessity of comprehensive testing in your own environment.

## Why Upgrade? The Benefits of pytest-asyncio 1.0

The migration effort is justified by the tangible improvements and a more modern approach offered by `pytest-asyncio` 1.0:

* **'Streamlined API & Pytest Harmony: Enjoy a cleaner, more Pytest-idiomatic API. With `event_loop` gone, loop management aligns beautifully with Pytest's native markers and fixture scoping via `loop_scope`, reducing cognitive load and boilerplate.'** The removal of the specialized `event_loop` fixture and the consistent use of `loop_scope` for both tests and fixtures lead to a more declarative and Pytest-idiomatic way of managing event loop lifecycles. This reduces the learning curve and makes test suites easier to understand and maintain.  
* **Improved Performance and Resource Management:** The strategy of creating scoped event loops only once per scope is a key optimization. For test suites with many tests or fixtures sharing module, class, or session scopes, this can significantly speed up test collection and execution by reducing redundant loop setup and teardown operations.  
* **Better Alignment with Modern `asyncio`:** The plugin now encourages the use of standard `asyncio` patterns, such as `asyncio.get_running_loop()` for accessing the loop. This makes `pytest-asyncio` feel less like a separate abstraction and more like a natural extension of `asyncio` for testing purposes.  
* **Future-Proofing:** With preliminary support for Python 3.14 and ongoing maintenance by the `pytest-dev` team, upgrading ensures your testing framework remains compatible with the latest Python advancements and continues to receive improvements and bug fixes.  
* **Enhanced Flexibility in Loop Scoping:** The `loop_scope` argument in `@pytest.mark.asyncio` is now more flexible, no longer strictly requiring a Pytest collector to exist at the specified scope level. This offers more fine-grained control over loop management without imposing rigid structural requirements on your tests.

Collectively, these benefits contribute to a more efficient, maintainable, and robust asynchronous testing experience. The move away from the explicit `event_loop` fixture towards a more declarative scope-based management system represents a maturation of the library's design.

## Conclusion and Further Resources

`pytest-asyncio` 1.0 marks a significant step forward for testing asynchronous Python code. The primary change, the removal of the `event_loop` fixture, is replaced by a more streamlined and `asyncio`\-native approach centered around `loop_scope` configuration and `asyncio.get_running_loop()`. While migration requires careful attention to how event loops were previously used and scoped, the process is manageable by following the steps outlined.

The benefits of upgrading—including a cleaner API, potential performance gains, and better alignment with modern Python—make it a worthwhile endeavor for any project relying on `pytest-asyncio`. Developers are encouraged to upgrade and explore the refined capabilities of this essential testing tool.

For more detailed information, refer to the official resources:

* [**Official `pytest-asyncio` Documentation**](https://pytest-asyncio.readthedocs.io/)  
* [**Changelog**](https://pytest-asyncio.readthedocs.io/en/latest/reference/changelog.html)  
* [**GitHub Repository (Source Code, Issues)**](https://github.com/pytest-dev/pytest-asyncio/)  

By embracing these changes, the Python community can continue to build and test robust asynchronous applications with greater ease and efficiency.
