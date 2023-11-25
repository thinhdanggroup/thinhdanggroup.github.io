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
    overlay_image: /assets/images/oauth2-python/banner.jpeg
    overlay_filter: 0.5
    teaser: /assets/images/oauth2-python/banner.jpeg
title: "Building Authentication and Authorization in Microservices using Python FastAPI and OAuth2"
tags:
    - OAuth2

---

This blog post provides a comprehensive guide on building authentication and authorization in microservices architecture using Python FastAPI and OAuth2. It begins with a detailed explanation of OAuth2, its roles, how it works, its benefits, differences from other authorization protocols, and its various applications. Next, it provides a step-by-step guide on how to implement OAuth2 in microservices architecture with FastAPI, including configuring an OAuth2 provider, defining OAuth2 credentials, implementing OAuth2 flows, generating access tokens, and securing API endpoints. It also discusses best practices when implementing OAuth2 with FastAPI, such as securely storing tokens, managing token expiration and renewal, handling user consent, preventing Cross-Site Request Forgery (CSRF), and using HTTPS for all OAuth2 requests. The blog post also highlights common pitfalls and challenges when implementing OAuth2 in microservices architecture with FastAPI, and how to avoid them. Finally, it showcases real-world examples of OAuth2 implementation in various applications, such as social media apps, banking applications, streaming services, healthcare applications, and e-commerce applications. The blog post concludes with a summary and a call to action for readers to implement what they have learned.

## Introduction

In today's digital world, the security of applications is paramount, and this is where authentication and authorization come in. Authentication is the process of verifying the identity of a user, device, or system. It often involves a username and password, but can involve any method of demonstrating identity, such as social logins or biometrics. Authorization, on the other hand, is the process of giving the authenticated party permission to access a specific resource or function.

When building microservices, it's crucial to implement authentication and authorization correctly, ensuring that each service can securely verify the identity of the user and determine what they're allowed to do. This is where OAuth2 comes into play.

OAuth2 is an authorization framework that enables applications to obtain limited access to user accounts on an HTTP service. It works by delegating user authentication to the service that hosts the user account and authorizing third-party applications to access that user account. It's widely used in various applications, including social media platforms, online marketplaces, and API integrations.

Python FastAPI is a modern, fast (high-performance) web framework for building APIs. It's easy to use, highly efficient, and provides automatic validation, serialization, and documentation of API endpoints. FastAPI is built on top of Starlette and Pydantic, supporting various authentication and authorization mechanisms, including OAuth2.

In this blog post, we will delve into how to build authentication and authorization in a microservices architecture using Python FastAPI and OAuth2. We will cover the basics of OAuth2, how to implement it in a microservices architecture with FastAPI, the best practices to follow, common pitfalls to avoid, and provide real-world examples. Whether you're a seasoned developer or just starting out, this blog post will provide valuable insights into securing your microservices with OAuth2 and FastAPI.



### Understanding OAuth2

OAuth2, which stands for "Open Authorization", is a standard designed to allow a website or application to access resources hosted by other web services on behalf of a user. It's an authorization framework that enables applications to obtain limited access to user accounts on an HTTP service.

OAuth2 defines four roles:

1. **Resource Owner**: The user who authorizes an application to access their account.
2. **Client**: The application that wants to access the user's account.
3. **Resource Server**: The server hosting the protected user accounts.
4. **Authorization Server**: The server that verifies the identity of the user and issues access tokens to the application.

OAuth2 works by delegating user authentication to the service that hosts the user account and authorizing third-party applications to access that user account. The process involves the client requesting authorization from the authorization server. The server authenticates the client, the resource owner grants access, and the authorization server redirects back to the client with an authorization code or access token. The client then uses the access token to request access to the resource from the resource server.

OAuth2 defines different grant types, such as the authorization code grant type, client credentials grant type, and device code grant type. These grant types determine how the application obtains an access token to access the user's account.

There are several benefits to using OAuth2. It improves security by not requiring the application to handle user credentials, simplifies the user authentication process, and allows granting limited access to user accounts without sharing credentials. It also offers a more flexible and simplified approach to authorization compared to other protocols like OAuth1 and OpenID.

OAuth2 is widely used in various applications, including social media platforms, online marketplaces, and API integrations. It allows users to easily authorize third-party applications to access their accounts and enables seamless integration between different services.

In the next section, we will explore how to implement OAuth2 in a microservices architecture with FastAPI.



### Implementing OAuth2 with FastAPI 

To implement OAuth2 in a microservices architecture with FastAPI, we will follow these steps:

#### Step 1: Configure an OAuth2 Provider

The first step is to set up an OAuth2 provider. This could be an existing service like Google or Facebook, or you could set up your own authorization server. The OAuth2 provider is responsible for authenticating the user and issuing access tokens to the client application.

#### Step 2: Define OAuth2 Credentials

Next, you need to obtain client credentials (client ID and client secret) from the OAuth2 provider. These credentials are used to authenticate the client application with the OAuth2 provider. 

#### Step 3: Implement OAuth2 Flows

FastAPI provides built-in support for integrating OAuth2 authentication and authorization. It allows you to implement OAuth2 flows, such as the password flow, and generate JWT access tokens. 

Here is an [example](https://github.com/thinhdanggroup/thinhda_dev_blog/blob/main/authorization_fastapi/app.py) of how you can define an OAuth2 password flow in FastAPI:

```python
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel

app = FastAPI()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@app.post("/token")
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    user_dict = fake_users_db.get(form_data.username)
    if not user_dict:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    user = UserInDB(**user_dict)
    hashed_password = fake_hash_password(form_data.password)
    if hashed_password != user.hashed_password:
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    return {"access_token": user.username, "token_type": "bearer"}
```

In this example, we define an OAuth2 password flow using the `OAuth2PasswordBearer` class. The `tokenUrl` parameter is the URL that the client (the browser) will use to send the username and password to get a token.

#### Step 4: Generate Access Tokens

Once the user is authenticated, you need to generate an access token using the OAuth2 library. This access token is used to authenticate subsequent requests from the client application. 

#### Step 5: Secure API Endpoints

After generating the access token, you need to secure your FastAPI endpoints by verifying and validating the access token in the request headers. This ensures that only authenticated requests can access the protected resources.

Here is how you can secure an API endpoint in FastAPI:

```python
@app.get("/users/me")
async def read_users_me(
        current_user: Annotated[User, Depends(get_current_active_user)]
):
    return current_user
```

In this example, we use the `Depends` function to declare a dependency on the `oauth2_scheme` instance. FastAPI will ensure that each request to this endpoint includes a valid OAuth2 access token.

#### Step 6: Handle Authorization

Finally, you need to handle authorization by using OAuth2 scopes or other mechanisms provided by FastAPI to handle authorization and permissions for different API endpoints.

FastAPI allows you to define scopes for your API endpoints, which can be used to specify the level of access granted to the client application. 

Here is an example of how you can [define scopes in FastAPI](https://github.com/thinhdanggroup/thinhda_dev_blog/blob/main/authorization_fastapi/app_scope.py):

```python
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="token",
    scopes={"me": "Read information about the current user.", "items": "Read items."},
)

@app.post("/token", response_model=Token)
async def login_for_access_token(
        form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
):
    user = authenticate_user(fake_users_db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "scopes": form_data.scopes},
        expires_delta=access_token_expires,
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me/items/")
async def read_own_items(
        current_user: Annotated[User, Security(get_current_active_user, scopes=["items"])]
):
    return [{"item_id": "Foo", "owner": current_user.username}]
```

In this example, we define a scope named "items" and associate it with the "/users/me/items/" endpoint. This means that the client must have the "items" scope in their access token to access this endpoint.

You can write [simple tests to verify that your API endpoints](https://github.com/thinhdanggroup/thinhda_dev_blog/blob/main/authorization_fastapi/test_auth.py) are secured properly. For example, you can write a test to verify that the "/users/me/items/" endpoint requires the "items" scope:

```python
import httpx
import pytest

from app import app
from app_scope import app as app_scope


@pytest.mark.asyncio
async def test_get_item():
    async with httpx.AsyncClient(app=app_scope, base_url="http://test") as ac:
        response = await ac.post("/token",
                                 data={"username": "johndoe", "password": "secret", "scope": "items me"})
        token = response.json()["access_token"]
        response = await ac.get("/users/me/items/", headers={"Authorization": f"Bearer {token}"})
    print("response.json()")
    print(response.json())
    assert response.status_code == 200
    assert response.text is not None
```

By following these steps, you can implement OAuth2 in a microservices architecture using FastAPI. In the next section, we will discuss some best practices for using OAuth2 with FastAPI.



### Best Practices for OAuth2 with FastAPI 

Implementing OAuth2 with FastAPI in a microservices architecture involves more than just setting up the OAuth2 provider and securing your API endpoints. It also requires following best practices to ensure the security and reliability of your application. Let's delve into some of these best practices.

#### Securely Storing Tokens

When working with OAuth2, it's crucial to securely store the access tokens and refresh tokens provided by the authorization server. One common approach is to store the tokens in a secure database or key-value store associated with the user or client they belong to. 

It's also important to encrypt the tokens before storing them to protect them from unauthorized access. Additionally, ensure that the storage mechanism is properly secured with appropriate access controls and encryption. FastAPI provides several tools for securely storing tokens, including JSON Web Tokens (JWT), which are encoded as a string and contain the necessary information for authentication.

#### Managing Token Expiration and Renewal

OAuth2 access tokens have a limited lifespan and will expire after a certain period. To manage token expiration and renewal, regularly check the expiration time of the access token and renew it before it expires. 

This can be done by using the refresh token provided by the authorization server. When the access token expires, use the refresh token to request a new access token without requiring the user to re-authenticate. Handle token expiration and renewal securely to prevent unauthorized access to protected resources.

#### Handling User Consent

When using OAuth2, it's important to handle user consent properly. Before requesting access to a user's protected resources, clearly explain the permissions your application requires and obtain the user's explicit consent.

This can be done through a consent screen or dialog that clearly explains the permissions and allows the user to grant or deny access. Be transparent and provide clear information about how the user's data will be used and protected.

#### Preventing Cross-Site Request Forgery (CSRF)

Cross-Site Request Forgery (CSRF) is a security vulnerability that allows an attacker to perform actions on behalf of a user without their knowledge or consent. To prevent CSRF attacks, include anti-CSRF measures in your OAuth2 implementation. 

This can be done by including a CSRF token in each request and validating it on the server-side. The CSRF token should be unique for each user session and should be securely generated and stored.

#### Using HTTPS for all OAuth2 Requests

To ensure the security of OAuth2 requests, use HTTPS for all requests. HTTPS encrypts the data being sent between the client, authorization server, and resource server, preventing unauthorized access and tampering. 

Additionally, HTTPS provides authentication of the server, ensuring that the client is communicating with the intended server and not a malicious attacker. By using HTTPS, you can protect sensitive user data and prevent man-in-the-middle attacks.

By following these best practices, you can ensure that your OAuth2 implementation with FastAPI is secure, reliable, and user-friendly. In the next section, we will discuss some common pitfalls to avoid when implementing OAuth2 with FastAPI.



### Pitfalls in OAuth2 Implementation 

While OAuth2 can significantly enhance the security and user experience of your microservices architecture, it's not without its challenges. Implementing OAuth2 with FastAPI can present several pitfalls that can compromise the security and effectiveness of your application if not properly addressed. Let's delve into these common pitfalls and how to avoid them.

#### Inadequate Token Storage

One common pitfall is inadequate token storage. OAuth2 relies on access tokens to authenticate requests, and these tokens need to be stored securely to prevent unauthorized access. If these tokens are not securely stored and encrypted, they can be intercepted by malicious entities, leading to unauthorized access to user data and potential data breaches.

To avoid this, always store tokens securely, using encryption and secure databases or key-value stores. Also, ensure that your storage mechanism is protected with appropriate access controls and encryption.

#### Inadequate Token Validation

Another common pitfall is inadequate token validation. When a request is made to a protected resource, the access token included in the request needs to be validated to ensure it's legitimate. If the token validation is not thorough, it could allow invalid or expired tokens to be used, leading to unauthorized access.

To avoid this, ensure that your application includes robust token validation. Check the token's signature, issuer, audience, and expiration time, and reject any tokens that fail these checks.

#### Insufficient User Consent

Insufficient user consent is another pitfall that can occur when implementing OAuth2. Before accessing a user's protected resources, your application should clearly explain what permissions it requires and obtain the user's explicit consent. If this is not done properly, it can lead to unauthorized access and a poor user experience.

To avoid this, always clearly explain the permissions your application requires and obtain the user's explicit consent. Use clear, user-friendly consent screens and provide detailed information about how the user's data will be used and protected.

#### Not Using HTTPS

Not using HTTPS for all OAuth2 requests is a common pitfall that can compromise the security of your application. Without HTTPS, the data being transmitted between the client, authorization server, and resource server is not encrypted, making it vulnerable to interception and tampering.

To avoid this, always use HTTPS for all OAuth2 requests. This ensures the confidentiality and integrity of the data being transmitted and provides authentication of the server.

By being aware of these common pitfalls and taking steps to avoid them, you can ensure that your OAuth2 implementation with FastAPI is secure, reliable, and effective. In the next section, we will explore some real-world examples of OAuth2 in microservices architecture with FastAPI.



### Real-world Examples of OAuth2 Implementation

To illustrate the practical applications of OAuth2 in microservices architecture using FastAPI, let's explore some real-world examples. These examples cover a range of applications, from social media apps to banking applications, streaming services, healthcare applications, and e-commerce applications.

#### Social Media Apps

OAuth2 is widely used in social media apps to allow users to log in using their social media accounts. This eliminates the need for users to create a new account and remember additional credentials. The app can use OAuth2 to authenticate the user with the social media platform and obtain an access token. This access token can then be used to access the user's profile information and perform actions on their behalf, such as posting updates or sharing content.

#### Banking Applications

In a banking application, OAuth2 can be used to enable third-party financial services to access account information and perform transactions on behalf of the user. For example, a user may want to use a personal finance management app that requires access to their bank account information. OAuth2 can be used to securely authenticate the user with their bank and authorize the personal finance app to access their account data. This allows the app to retrieve transaction history, account balances, and perform transfers without the user needing to share their banking credentials.

#### Streaming Services

A streaming service can utilize OAuth2 to allow users to sign in using their existing accounts from other platforms, such as Google or Facebook. By implementing OAuth2, the streaming service can securely authenticate the user with the chosen platform and obtain an access token. This access token can then be used to access the user's profile information, preferences, and recommendations. Additionally, OAuth2 can be used to enable the streaming service to share user activity and preferences with other platforms, providing a seamless and personalized user experience across multiple services.

#### Healthcare Applications

In a healthcare application, OAuth2 can be used to facilitate secure access to patient health records and medical information. Healthcare providers can implement OAuth2 to allow patients to grant access to their medical data to other healthcare professionals or third-party applications. This enables seamless sharing of medical records, lab results, and treatment history, while maintaining strict privacy and security measures. OAuth2 ensures that only authorized individuals or applications can access the patient's sensitive health information.

#### E-commerce Applications

In an e-commerce application, OAuth2 can be used to enable users to log in using their existing accounts from popular platforms like Google, Facebook, or Amazon. By implementing OAuth2, the e-commerce application can securely authenticate the user with their chosen platform and obtain an access token. This access token can then be used to access the user's profile information, purchase history, and preferences. Additionally, OAuth2 can be used to authorize third-party applications to access the user's e-commerce account data for personalized recommendations and targeted marketing.

These examples illustrate the versatility and effectiveness of OAuth2 in securing microservices and enhancing the user experience. By implementing OAuth2 with FastAPI, you can provide secure, seamless, and personalized experiences for your users across a wide range of applications.



### Conclusion

In this blog post, we've explored the power and utility of implementing OAuth2 in a microservices architecture using FastAPI. We've delved into the theory of OAuth2, understanding its roles, how it works, its benefits, and its wide range of applications. We've also walked through a practical guide on how to implement OAuth2 with FastAPI, covering key steps from configuring an OAuth2 provider to securing API endpoints and handling user consent.

We've highlighted best practices for OAuth2 implementation, including securely storing tokens, managing token expiration and renewal, handling user consent, preventing Cross-Site Request Forgery (CSRF), and using HTTPS for all OAuth2 requests. We've also discussed common pitfalls to avoid when implementing OAuth2 with FastAPI to ensure a secure, reliable, and effective application.

Furthermore, we've explored real-world examples of OAuth2 implementation in a variety of applications, from social media apps and banking applications to streaming services, healthcare applications, and e-commerce applications. These examples illustrate the versatility and effectiveness of OAuth2 in securing microservices and enhancing the user experience.

Implementing OAuth2 in a microservices architecture with FastAPI provides numerous benefits. It enhances the security of your application by not requiring the application to handle user credentials and by granting limited access to user accounts without sharing credentials. It simplifies the user authentication process, provides a more flexible and simplified approach to authorization, and enables seamless integration between different services.

As an engineer, understanding and implementing OAuth2 with FastAPI is a valuable skill that can greatly enhance the security and user experience of your microservices. I encourage you to apply what you've learned in this blog post to your own projects. Whether you're building a social media app, a streaming service, or an e-commerce platform, OAuth2 and FastAPI can provide a secure, efficient, and user-friendly solution for authentication and authorization in your microservices architecture.

Remember, the journey to mastering OAuth2 and FastAPI doesn't end here. There's always more to learn and discover. So, keep exploring, keep learning, and keep building secure and user-friendly microservices with OAuth2 and FastAPI.




## References

- [An Introduction to OAuth2](https://www.digitalocean.com/community/tutorials/an-introduction-to-oauth-2) 
- [FastAPI](http://richard.to/programming/microservice-authorization-questions.html) 
- [Introduction to OAuth2](https://auth0.com/intro-to-iam/what-is-oauth-2) 
- [Microservice Authorization Questions](http://richard.to/programming/microservice-authorization-questions.html) 
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/) 
- [Microservice in Python using FastAPI](https://dev.to/paurakhsharma/microservice-in-python-using-fastapi-24cc) 
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/docker/) 
- [Awesome FastAPI](https://github.com/mjhea0/awesome-fastapi) 
