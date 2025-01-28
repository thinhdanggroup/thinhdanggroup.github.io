---
author:
    name: "Thinh Dang"
    avatar: "/assets/images/avatar.png"
    bio: "Experienced Fintech Software Engineer Driving High-Performance Solutions"
    location: "Viet Nam"
    email: "thinhdang206@gmail.com"
    links:
        - label: "Linkedin"
          icon: "fab fa-fw fa-linkedin"
          url: "https://www.linkedin.com/in/thinh-dang/"
toc: true
toc_sticky: true
header:
    overlay_image: /assets/images/blog-on-chat-deepseek-r1-api-/banner.png
    overlay_filter: 0.5
    teaser: /assets/images/blog-on-chat-deepseek-r1-api-/banner.png
title: "Getting Started with Chat DeepSeek R1 API: Installation, Usage, and Integration with Langchain"
tags:
    - DeepSeek R1
    - API
---

This article serves as a comprehensive guide to understanding and utilizing the Chat DeepSeek R1 API, a powerful tool developed to enhance applications with advanced reasoning capabilities. We begin by introducing DeepSeek R1, an open-source model known for its ability to tackle complex tasks requiring logical inference and decision-making. The introductory section highlights the model's unique features, such as its transparency and adaptability, making it ideal for various industries.

Next, we provide a step-by-step guide on installing the Chat DeepSeek R1 API from PyPI, ensuring that even those new to API integration can easily follow along. With the API installed, we then delve into a basic usage example, demonstrating how to set up your environment, initialize the API, and engage in a chat session. This hands-on example equips readers with the foundational knowledge needed to interact with the API effectively.

Finally, the article explores the integration of the Chat DeepSeek R1 API with Langchain, a popular framework for building language models. Through a detailed code example, readers will learn how to create a custom chat model within Langchain, facilitating seamless communication with the API. By the end of this article, readers will have a solid understanding of how to install, use, and integrate the Chat DeepSeek R1 API into their projects, unlocking its full potential for advanced reasoning and interaction.

## Introduction to DeepSeek R1

DeepSeek-R1 is an innovative open-source reasoning model developed by DeepSeek, crafted to address complex tasks that demand logical inference, mathematical problem-solving, and real-time decision-making. This model is particularly notable for its transparency in the reasoning process, a feature that is increasingly important in applications where explainability is paramount. By allowing users to understand the steps and logic behind its conclusions, DeepSeek-R1 supports more informed decision-making.

The open-source nature of DeepSeek-R1 is one of its significant strengths, providing developers and researchers the freedom to explore, modify, and implement the model to suit their specific requirements. This adaptability makes it a versatile tool across various industries, from research and education to business and technology, where tailored solutions can be developed to meet unique challenges.

DeepSeek-R1's architecture is designed to facilitate real-time decision-making, with considerations for latency and efficiency, making it suitable for applications that require immediate responses. This capability is supported by an underlying framework that, while not explicitly detailed in available resources, likely combines elements of neural networks and symbolic reasoning to achieve its goals.

In the sections that follow, we will delve into the integration of DeepSeek-R1 with the Chat DeepSeek R1 API, providing insights into how this powerful model can be harnessed in practical applications. This exploration will include installation instructions, usage examples, and a demonstration of its integration with Langchain, illustrating the model's potential to enhance various technological solutions.

## Installing Chat DeepSeek R1 API

The Chat DeepSeek R1 API is designed to be easily installed from PyPI, providing developers with a straightforward way to access the powerful reasoning capabilities of the DeepSeek-R1 model. This section will guide you through the installation process, ensuring that you are ready to integrate the API into your applications.

### Step-by-Step Installation Guide

1. **Prerequisites**:

    - Ensure that you have Python 3.x installed on your system. The Chat DeepSeek R1 API is compatible with Python 3.x, but it's always a good idea to check the official documentation for specific version requirements.
    - It's recommended to set up a virtual environment to avoid conflicts with other installed packages. You can create a virtual environment using the following command:
        ```bash
        python -m venv deepseek_env
        ```
    - Activate your virtual environment:
        - On Windows:
            ```bash
            deepseek_env\Scripts\activate
            ```
        - On macOS and Linux:
            ```bash
            source deepseek_env/bin/activate
            ```

2. **Installing the API**:

    - Use pip to install the Chat DeepSeek R1 API directly from its GitHub repository. Run the following command in your terminal:
        ```bash
        pip install chat-deepseek-api
        ```
    - This command fetches the latest version of the API and installs it in your virtual environment.

3. **Handling Installation Issues**:

    - If you encounter any issues during installation, ensure that your network connection is stable and that you have the correct version of pip installed.
    - For permission-related errors, try running the command with elevated privileges (e.g., using `sudo` on Linux or macOS).

4. **Verify Installation**:
    - After installation, you can verify that the API is installed correctly by importing it in a Python script or interactive shell:
        ```python
        import deepseek_api
        ```
    - If no errors are raised, the installation was successful.

By following these steps, you will have the Chat DeepSeek R1 API installed and ready to be configured for use in your projects. The process is designed to be straightforward, ensuring accessibility even for developers new to working with APIs. Once installed, you can proceed to set up the necessary credentials and start leveraging the API's capabilities in your applications.

## Basic Usage of Chat DeepSeek R1 API

In this section, we will walk through a basic example of using the Chat DeepSeek R1 API. This guide will help you set up your environment with the necessary credentials, initialize the API, and start a chat session. The provided Python script demonstrates how to send a message to the API and handle the asynchronous response, serving as a foundation for understanding how to interact with the API and leverage its capabilities for logical reasoning and response generation.

### Setting Up Your Environment

Before diving into the code, it's essential to configure your environment with the necessary credentials. Here's how you can do it:

1. **Install Required Libraries**: Make sure you have the necessary Python packages installed. You can install the Chat DeepSeek R1 API using the following command:

    ```bash
    pip install chat-deepseek-api
    ```

2. **Environment Variables**: Copy the `.env.example` file to `.env` and fill in your DeepSeek credentials:

    ```plaintext
    DEEPSEEK_EMAIL=your_email@example.com
    DEEPSEEK_PASSWORD=your_password
    DEEPSEEK_DEVICE_ID=your_device_id
    DEEPSEEK_COOKIES=your_cookies
    DEEPSEEK_DS_POW_RESPONSE=your_ds_pow_response
    ```

### Python Script for Basic Interaction

Below is a Python script that demonstrates how to interact with the Chat DeepSeek R1 API. This script sets up the API, starts a chat session, and sends a message to the API. It handles responses asynchronously, showcasing the efficiency of asynchronous programming in handling API calls.

```python
import asyncio
import os
from deepseek_api import DeepseekAPI
from dotenv import load_dotenv
from deepseek_api.model import MessageData

load_dotenv()

async def main():
    email = os.environ.get("DEEPSEEK_EMAIL")
    password = os.environ.get("DEEPSEEK_PASSWORD")
    device_id = os.environ.get("DEEPSEEK_DEVICE_ID")
    cookies = os.environ.get("DEEPSEEK_COOKIES")
    ds_pow_response = os.environ.get("DEEPSEEK_DS_POW_RESPONSE")

    app = await DeepseekAPI.create(
        email=email,
        password=password,
        save_login=True,
        device_id=device_id,
        custom_headers={
            "cookie": cookies,
            "x-ds-pow-response": ds_pow_response,
        },
    )

    chat_session_id = await app.new_chat()
    print(f"Starting chat session with id: {chat_session_id}")

    message_id = None
    async for chunk in app.chat(
        message="who are you", id=chat_session_id, parent_message_id=message_id
    ):
        chunk_data: MessageData = chunk
        print(chunk_data.choices[0].delta.content, end="")
        cur_message_id = chunk.get_message_id()
        if not cur_message_id:
            cur_message_id = 0
        if not message_id or cur_message_id > message_id:
            message_id = cur_message_id
    print()

    await app.close()

if __name__ == "__main__":
    asyncio.run(main())
```

### Explanation of the Code

-   **Loading Environment Variables**: We use the `dotenv` package to load environment variables from the `.env` file. This allows us to securely manage sensitive information like credentials.

-   **Asynchronous API Initialization**: The `DeepseekAPI.create()` method initializes the API asynchronously, ensuring that your credentials are used to authenticate the session.

-   **Starting a Chat Session**: The `new_chat()` method creates a new session, and the returned session ID is used for subsequent interactions.

-   **Sending a Message**: The `app.chat()` method sends a message to the API. The response is handled asynchronously, allowing other tasks to proceed while waiting for the API's response.

-   **Handling Responses**: The script processes each response chunk as it arrives, printing the content to the console. This demonstrates how to handle streaming data efficiently.

By following this example, you will gain hands-on experience with the core functionalities of the Chat DeepSeek R1 API, setting the stage for more complex interactions and applications.

## Integrating Chat DeepSeek R1 API with Langchain

In this section, we'll delve into integrating the Chat DeepSeek R1 API with Langchain, a powerful framework for building language models. The aim is to illustrate how you can create a custom chat model using the Chat DeepSeek API within Langchain, enabling advanced reasoning and interaction capabilities in your applications.

### Setting Up the Integration

To begin, ensure you have your environment variables set up correctly. These include your DeepSeek credentials such as email, password, device ID, cookies, and the DS POW response. You can manage these by placing them in a `.env` file, which should look something like this:

```plaintext
DEEPSEEK_EMAIL=your_email
DEEPSEEK_PASSWORD=your_password
DEEPSEEK_DEVICE_ID=your_device_id
DEEPSEEK_COOKIES=your_cookies
DEEPSEEK_DS_POW_RESPONSE=your_ds_pow_response
```

### Code Example

Below is a comprehensive code example demonstrating how to integrate the Chat DeepSeek R1 API with Langchain:

```python
import asyncio
import os
from typing import Any, AsyncIterator, Dict, Iterator, List, Optional
from dotenv import load_dotenv
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from langchain_core.language_models.llms import LLM
from langchain_core.outputs import GenerationChunk
from chat_deepseek_api.model import MessageData
from chat_deepseek_api import DeepseekAPI

class ChatDeepSeekApiLLM(LLM):
    email: str = None
    password: str = None
    device_id: str = None
    cookies: str = None
    ds_pow_response: str = None
    app: DeepseekAPI = None
    chat_session_id: str = None
    message_id: int = 0

    def __init__(self, email: str, password: str, device_id: str, cookies: str, ds_pow_response: str):
        super(ChatDeepSeekApiLLM, self).__init__()
        self.email = email
        self.password = password
        self.device_id = device_id
        self.cookies = cookies
        self.ds_pow_response = ds_pow_response

    def _call(self, prompt: str, stop: Optional[List[str]] = None, run_manager: Optional[CallbackManagerForLLMRun] = None, **kwargs: Any) -> str:
        if stop is not None:
            raise ValueError("stop kwargs are not permitted.")
        self._verify_config()
        for message in self._generate_message(prompt):
            chunk = GenerationChunk(text=message)
            if run_manager:
                run_manager.on_llm_new_token(chunk.text, chunk=chunk)
        return "".join([chunk for chunk in self._generate_message(prompt)])

    async def _async_generate_message(self, prompt: str) -> AsyncIterator[str]:
        if not self.app:
            self.app = await DeepseekAPI.create(
                email=self.email,
                password=self.password,
                save_login=True,
                device_id=self.device_id,
                custom_headers={
                    "cookie": self.cookies,
                    "x-ds-pow-response": self.ds_pow_response,
                },
            )
        if not self.chat_session_id:
            self.chat_session_id = await self.app.new_chat()
        self.message_id = None
        async for chunk in self.app.chat(
            message=prompt, id=self.chat_session_id, parent_message_id=self.message_id
        ):
            chunk_data: MessageData = chunk
            yield chunk_data.choices[0].delta.content
            cur_message_id = chunk.get_message_id()
            if not cur_message_id:
                cur_message_id = 0
            if not self.message_id or cur_message_id > self.message_id:
                self.message_id = cur_message_id

    def _close(self) -> None:
        if self.app:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self.app.close())

    def _verify_config(self) -> None:
        if not self.email:
            raise ValueError("Email is required.")
        if not self.password:
            raise ValueError("Password is required.")
        if not self.device_id:
            raise ValueError("Device ID is required.")
        if not self.cookies:
            raise ValueError("Cookies are required.")
        if not self.ds_pow_response:
            raise ValueError("DS POW Response is required.")

if __name__ == "__main__":
    load_dotenv()
    email = os.environ.get("DEEPSEEK_EMAIL")
    password = os.environ.get("DEEPSEEK_PASSWORD")
    device_id = os.environ.get("DEEPSEEK_DEVICE_ID")
    cookies = os.environ.get("DEEPSEEK_COOKIES")
    ds_pow_response = os.environ.get("DEEPSEEK_DS_POW_RESPONSE")
    model = ChatDeepSeekApiLLM(
        email=email,
        password=password,
        device_id=device_id,
        cookies=cookies,
        ds_pow_response=ds_pow_response,
    )
    result = model.invoke("who are you")
    print(result)
    result = model.invoke("what can you do")
    print(result)
    model._close()
```

### Key Components

-   **Authentication Setup**: We initialize the `DeepseekAPI` using credentials stored in environment variables. This ensures secure and efficient authentication.

-   **Custom Chat Model**: The `ChatDeepSeekApiLLM` class extends the `LLM` class from Langchain, tailored to interact with the Chat DeepSeek API.

-   **Message Generation**: The `_async_generate_message` method handles prompt processing and response generation asynchronously, ensuring efficient communication with the API.

-   **Session Management**: Each chat session is managed with a unique session ID, ensuring context is maintained across interactions.

By following this example, you can leverage Langchain to build robust applications that utilize the reasoning capabilities of the Chat DeepSeek R1 API. This integration allows for advanced interaction models, enhancing the functionality and responsiveness of your applications.

All source code can be found in the [DeepSeek R1 GitHub repository](https://github.com/thinhdanggroup/thinhda_dev_blog/blob/main/deepseek_unofficial_api/chat_deepseek_langchain.py)