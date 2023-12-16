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
    overlay_image: /assets/images/token-vs-cookies/banner.jpeg
    overlay_filter: 0.5
    teaser: /assets/images/token-vs-cookies/banner.jpeg
title: "Enhancing Web Security: A Deep Dive into Cookies and Tokens for Authentication"
tags:
    - Cookies
    - Tokens
    - Authentication

---

This blog post provides an in-depth understanding of how cookies and tokens are used for authentication in web applications. It begins with an introduction to cookies and tokens, explaining what they are and how they work in the context of authentication. The blog then dives into real-life use cases of cookies and tokens for authentication, providing examples and explaining how they contribute to secure authentication. The blog also presents case studies of successful implementations of cookies and tokens, discussing the lessons learned from these examples and their impact on web security. Furthermore, it analyzes the advantages and disadvantages of using cookies and tokens for authentication and provides guidance on when to use one over the other. The blog concludes with a discussion on how cookies and tokens can be combined for enhanced security in web applications, covering the benefits, challenges, and future trends of this approach. This blog post is a comprehensive guide for anyone interested in understanding the role of cookies and tokens in secure web authentication.

## Introduction to Cookies and Tokens for Authentication

As the digital landscape continues to evolve, so does the need for secure authentication mechanisms in web applications. Authentication is a fundamental aspect of web security, ensuring that only authenticated and authorized users can access resources and perform actions within an application or system. It helps prevent identity theft, data breaches, and other security threats. In this blog post, we will dive deep into two widely used authentication mechanisms - cookies and tokens, and explore their role in securing web applications.

### Understanding Cookies and Tokens

#### Cookies

Cookies are small text files stored on a user's computer by a web browser. They are commonly used for authentication and session management purposes. Cookies can store information such as user preferences, login credentials, and session IDs. When a user visits a website, the browser sends the stored cookies to the web server, allowing the server to recognize the user and provide personalized content or maintain a user's session. Cookies can be either session cookies, which are deleted when the browser is closed, or persistent cookies, which remain on the user's computer until they expire or are manually deleted.

#### Tokens

On the other hand, tokens are used for authentication and authorization in web applications. They are typically issued by an authentication server after a user successfully logs in. Tokens contain information about the user and their permissions, and they are used to authenticate subsequent requests to protected resources. Unlike cookies, tokens are stored on the client side, usually in local storage or as HTTP headers. Tokens can be either JSON Web Tokens (JWT) or opaque tokens. JWTs are self-contained and contain all the necessary information within the token itself, while opaque tokens are references to server-side data stored in a database. Tokens are more secure than cookies because they are not susceptible to cross-site scripting (XSS) attacks.

### Role of Cookies and Tokens in Authentication

Both cookies and tokens play a role in authentication, but they serve different purposes. Cookies are used to maintain a user's session and provide stateful authentication. When a user logs in, a cookie is usually issued to the browser, and subsequent requests include the cookie to authenticate the user. 

Tokens, on the other hand, are used for stateless authentication. They contain all the necessary information to authenticate a user and are sent with each request as an HTTP header or within the payload of a JSON Web Token (JWT). Tokens are more secure than cookies because they are not vulnerable to cross-site scripting (XSS) attacks.

In the following sections, we will explore the use cases, real-life applications, pros and cons, and how to combine cookies and tokens for enhanced security in web applications. Stay tuned!



## Basic Concepts of Cookies and Tokens for Authentication

Let's delve deeper into the basic concepts of cookies and tokens, their functionality in authentication, and the differences between them. Understanding these concepts is crucial for implementing secure authentication mechanisms in your web applications.

### Detailed Explanation of Cookies and Tokens

#### Cookies

Cookies, as we mentioned earlier, are small text files that a web server stores on a user's computer. They are specifically designed to be a reliable mechanism for websites to remember stateful information (such as items added in a shopping cart in an online store) or to record the user's browsing activity (including clicking particular buttons, logging in, or recording which pages were visited in the past).

In the context of authentication, cookies are utilized to store session identifiers. When a user logs into a website, the server generates a unique identifier and stores it in a cookie. This cookie is then sent back to the client and stored on the user's computer. On subsequent requests, the client includes the cookie in the request headers, allowing the server to identify the user and authenticate the request. 

#### Tokens

Tokens, on the other hand, are strings of characters that are used to authenticate a user. They are used as a form of digital identity and are often used in web applications for authentication and authorization purposes. Tokens can be generated by an authentication server and then provided to the client upon successful authentication.

Tokens contain encoded information about the user's identity and are used to authenticate subsequent requests. Ory Session Token is an example of using tokens for session management in the Ory ecosystem. The token is then included in subsequent requests to authenticate the user. The server can verify the token to ensure that it is valid and belongs to a legitimate user.

### How Cookies and Tokens Work in Authentication

The way cookies and tokens work in authentication is quite different. Cookies, being stateful, store the session state on the server side. When a user logs into a website, the server creates a session for the user and sends a cookie with a session ID to the user's browser. The browser then stores the cookie and sends it with every subsequent request to the server. The server checks the session ID stored in the cookie and uses it to fetch the session information stored on the server.

Tokens, being stateless, do not store any session state on the server. Instead, they encode the session state within the token itself. When a user logs in, the server generates a token for the user and sends it back. The user's browser then stores the token and sends it with every subsequent request to the server. The server decodes the token to retrieve the session state.

### Differences Between Cookies and Tokens

There are several differences between cookies and tokens in the context of authentication:

1. **Storage Location**: Cookies are stored on the client-side, typically in the user's browser. Tokens, on the other hand, can be stored on either the client-side or the server-side.

2. **Statefulness**: Cookies are stateful, meaning they require the server to store session state. Tokens, on the other hand, are stateless, meaning the server does not need to store any session state.

3. **Security**: Tokens are generally more secure than cookies. They can be encrypted and signed, providing protection against tampering and ensuring data integrity.

4. **Flexibility**: Tokens are more flexible than cookies. They can be used across different domains and can be used in various client applications, including native mobile apps and desktop applications.

In the next sections, we will explore the use cases, real-life applications, pros and cons, and how to combine cookies and tokens for enhanced security in web applications.



## Use Cases of Cookies and Tokens for Authentication

Understanding the theoretical aspects of cookies and tokens is important, but seeing them in action brings a whole new perspective. In this section, we'll delve into some real-life examples of where cookies and tokens are used, how they contribute to secure authentication, and compare their usage in different scenarios.

### Real-Life Examples of Cookies and Tokens Usage

Cookies and tokens are critical components of authentication in countless web applications today. Let's look at some real-life examples:

#### Cookies

Cookies are extensively used in web applications for various purposes, such as session management, user authentication, and tracking user behavior.

- **Facebook**: When you log into Facebook, it uses cookies to remember your login status across different browsing sessions. This way, you don't have to log in every time you visit Facebook.

- **Amazon**: When shopping on Amazon, cookies are used to remember the items in your shopping cart. Even if you close the browser and come back later, your items will still be in the cart.

- **Google**: Google uses cookies to remember user preferences, such as your preferred language or location. This helps Google personalize your browsing experience.

#### Tokens

Tokens, particularly JSON Web Tokens (JWT), are widely used for secure authentication and authorization in web applications.

- **OAuth 2.0**: Many major tech companies like Google, Facebook, and Twitter use OAuth 2.0 for authentication. In OAuth 2.0, access tokens are issued to third-party applications by an authorization server with the approval of the resource owner (user). The third-party application can then use the access token to access the user's data hosted by the service provider.

- **Firebase Authentication**: Firebase Authentication is a backend service provided by Google that handles user authentication. It uses JWT for authentication and provides SDKs and libraries for integrating with various platforms, including Android, iOS, and web applications.

### How Cookies and Tokens Contribute to Secure Authentication

Cookies and tokens play a significant role in enhancing the security of web applications.

#### Cookies

Cookies contribute to secure authentication by providing a mechanism for session management and user identification. When a user logs in, a session cookie can be created and stored on their browser. This cookie is used to identify the user and maintain their authentication state across multiple requests. By securely storing session information in a cookie, the server can verify the user's identity and ensure that only authenticated users can access protected resources.

#### Tokens

Tokens, on the other hand, contribute to secure authentication by providing a stateless and tamper-proof mechanism for verifying the identity of a user. When a user logs in, a token is generated and sent to the client. This token contains all the necessary information to validate the user's identity and permissions. Since tokens are signed or encrypted by the server, they cannot be tampered with by malicious users. This helps to prevent unauthorized access to protected resources, as the server can verify the authenticity of the token before granting access.

### Comparison of Cookies and Tokens in Real-World Scenarios

In real-world scenarios, cookies and tokens have different use cases and considerations. Cookies are typically used for session management and user identification in web applications. They are stored on the client-side and sent with each request to the server.

Tokens, being stateless, do not store any session state on the server. Instead, they encode the session state within the token itself. When a user logs in, the server generates a token for the user and sends it back. The user's browser then stores the token and sends it with every subsequent request to the server. The server decodes the token to retrieve the session state.

In the next sections, we will explore the real-life applications, pros and cons, and how to combine cookies and tokens for enhanced security in web applications.



## Real-Life Applications of Cookies and Tokens for Authentication 

In the previous sections, we have discussed the theoretical aspects, use cases, and real-life examples of cookies and tokens. Now, let's dive deeper and explore some case studies of successful implementations of cookies and tokens in web applications, the lessons learned from these examples, and the impact of cookies and tokens on web security.

### Case Studies of Successful Implementations of Cookies and Tokens

#### Cookies

Cookies are widely used in web applications for various purposes, including session management, user authentication, and personalization. Here are some real-world examples of successful implementations of cookies:

- **Facebook**: Facebook uses cookies to remember user preferences, personalize content, and provide a seamless user experience across different devices.

- **Amazon**: Amazon uses cookies to track user behavior, recommend personalized products, and maintain shopping cart information.

- **Google**: Google uses cookies for various purposes such as user authentication, storing user preferences, and tracking user interactions with ads.

#### Tokens

Tokens, particularly JSON Web Tokens (JWT), are widely used for secure authentication and authorization in web applications. Here are some case studies of successful implementations of tokens:

- **OAuth 2.0**: Many major tech companies like Google, Facebook, and Twitter use OAuth 2.0 for authentication. In OAuth 2.0, access tokens are issued to third-party applications by an authorization server with the approval of the resource owner (user). The third-party application can then use the access token to access the user's data hosted by the service provider.

- **Firebase Authentication**: Firebase Authentication is a backend service provided by Google that handles user authentication. It uses JWT for authentication and provides SDKs and libraries for integrating with various platforms, including Android, iOS, and web applications.

### Lessons Learned from Cookies and Tokens Usage

The usage of cookies and tokens in web applications has taught us several important lessons:

- **Privacy concerns**: Cookies can store sensitive user information, so it is crucial to handle them securely and ensure proper consent and disclosure to users.

- **Cross-site scripting (XSS) vulnerabilities**: Cookies can be vulnerable to XSS attacks if not properly handled. It is essential to sanitize and validate cookie values to mitigate this risk.

- **Cookie security options**: Setting secure and HttpOnly flags on cookies helps protect against various attacks like session hijacking and cross-site scripting.

- **Cookie expiration and renewal**: Managing cookie expiration and renewal is important to maintain session security and prevent unauthorized access.

- **Token expiration and revocation**: Tokens should have a limited lifespan and be regularly refreshed to mitigate the risk of token theft and unauthorized access.

- **Token validation and integrity**: Proper validation and verification of tokens are crucial to ensure their authenticity and prevent tampering.

- **Token storage**: Tokens should be securely stored on the client-side and transmitted over secure channels to prevent interception and unauthorized use.

- **Token scope and permissions**: Tokens should be carefully scoped to only grant access to the necessary resources and permissions, reducing the potential impact of a compromised token.

### Impact of Cookies and Tokens on Web Security

Cookies and tokens play a significant role in web security. When used correctly, they can provide secure authentication and session management. However, improper implementation can lead to vulnerabilities and compromise the security of a web application.

Cookies that contain session tokens should be set with the 'http-only' flag to prevent them from being accessed by JavaScript. They should also be set with the 'secure' flag to ensure they are only sent over secure HTTPS connections. Additionally, custom HTTP headers can be used to send session tokens with requests, protecting against CSRF attacks.

Tokens, such as JSON Web Tokens (JWT), can be secure if a strong secret key is used. However, if the secret key is compromised, attackers can forge their own tokens. It is important to use randomly generated tokens that can be invalidated at any time to protect against token compromise. Tokens should also be stored securely and protected from unauthorized access.

In the next sections, we will explore the pros and cons of cookies and tokens for authentication and how to combine them for enhanced security in web applications.



## Pros and Cons of Cookies and Tokens for Authentication 

In the previous sections, we have discussed the fundamental concepts, use cases, and real-life applications of cookies and tokens for authentication. Now, let's delve into a detailed analysis of the advantages and disadvantages of using cookies and tokens for authentication. Understanding the pros and cons of each approach can help you make an informed decision on when to use one over the other.

### Advantages of Cookies for Authentication

Cookies have several advantages when used for authentication:

1. **Availability**: Cookies can be made available for an extended period, maintaining a session for a long time.
2. **Easy Configuration**: Websites can deliver cookies by configuring them as per requirement.
3. **User-friendly**: Cookie-based authentications are simple, and the cookies used in this method are user-friendly. Users can choose what to do with cookie files that have kept user credentials.

### Disadvantages of Cookies for Authentication

Despite their advantages, cookies also have certain disadvantages when used for authentication:

1. **Vulnerable to CSRF**: Cookie-based authentications are prone to Cross-site Request Forgery (CSRF) attacks.
2. **Less Mobile-friendly**: Cookie-based authentication does not work well with all native applications.
3. **Limitations**: There are certain limitations and concerns such as size limit (not more than 4KB of information per cookie), browser limitations on cookies, user privacy, etc., come with cookies and cookie-based authentication.
4. **Less Scalable**: Cookie-based authentication is less scalable, and the overhead rises when the user count increases on a particular site.

### Advantages of Tokens for Authentication

Tokens also have several advantages when used for authentication:

1. **Scalable and Efficient**: In cookieless authentication, the tokens remain stored on the user's end. This makes the authentication process more scalable and efficient.
2. **Better Performance**: Cookie-based authentication requires the server to perform an authentication lookup every time the user requests a page. On the other hand, token-based authentication eliminates this need, leading to better performance.
3. **Robust Security**: Since cookieless authentication leverages tokens like JWT (stateless), only a private key (used to create the authentication token) can validate it when received at the server-side.
4. **Seamless Across Devices**: Cookieless authentication works well with all native applications.
5. **Expiration Time**: Usually, tokens get generated with an expiration time, after which they become invalid.

### Disadvantages of Tokens for Authentication

Despite their advantages, tokens also have certain disadvantages when used for authentication:

1. **Single-key Token**: One of the significant challenges with cookieless authentication is that these access tokens rely on just one key.
2. **Data Overhead**: Storing a lot of data increases the overall size of the token. It slows down the request impacting the overall loading speed.
3. **Vulnerable to XSS and CSRF**: Cookieless authentications are susceptible to XSS and CSRF attacks.

### When to Use Cookies or Tokens for Authentication

Choosing between cookies and tokens for authentication depends on the specific requirements of your application. 

- Use **cookies** when you need availability, easy configuration, and user-friendly authentication. Cookies are also a good choice for web-only applications that do not require API access.

- Use **tokens** when you need scalability, better performance, robust security, seamless across devices, and expiration time for authentication. Tokens are particularly useful for applications that need to expose APIs for third-party access or for mobile applications.

In the next section, we will discuss how to combine cookies and tokens for enhanced security in web applications.



## Combining Cookies and Tokens for Enhanced Security in Web Applications

Secure authentication is a critical aspect of web application security. As we have seen, both cookies and tokens offer unique advantages and can be used effectively in different scenarios. However, a combination of both can lead to an enhanced security model, leveraging the strengths of both methods while mitigating their weaknesses. Let's delve into how cookies and tokens can be combined for enhanced security, the benefits of this approach, the challenges, and future trends in this area.

### How to Combine Cookies and Tokens for Authentication

Combining cookies and tokens involves using cookies for session management and tokens for authentication and authorization. When a user logs in, the server creates a session and stores a session identifier in a cookie. This cookie is sent to the client and stored in the user's browser. The server also generates an authentication token, which is sent to the client and stored in a secure manner, such as in the browser's local storage.

For each subsequent request, the client sends both the session cookie and the authentication token. The server validates the session cookie to maintain the user's session and verifies the token to authenticate the user. This approach combines the stateful nature of cookies with the stateless and flexible properties of tokens, providing a robust and scalable authentication solution.

Here is a simple example of how this could be implemented in a web application:

```javascript
// Import the required modules
const express = require('express');
const jwt = require('jsonwebtoken');
const cookieParser = require('cookie-parser');

// Create an express app
const app = express();

// Use cookie parser middleware
app.use(cookieParser());

// Define a secret key for signing the tokens
const secret = 'some-secret-key';

// Define a middleware function to verify the token
const verifyToken = (req, res, next) => {
  // Get the token from the request header
  const token = req.headers['authorization'];
  // If the token is not present, send a 401 response
  if (!token) {
    return res.status(401).send('Access denied');
  }
  // Verify the token using the secret key
  jwt.verify(token, secret, (err, decoded) => {
    // If the token is invalid, send a 403 response
    if (err) {
      return res.status(403).send('Invalid token');
    }
    // If the token is valid, set the req.user to the decoded payload
    req.user = decoded;
    // Call the next middleware function
    next();
  });
};

// Define a route for logging in
app.post('/login', (req, res) => {
  // Get the username and password from the request body
  const { username, password } = req.body;
  // Validate the credentials (this is just a mock example)
  if (username === 'admin' && password === 'password') {
    // Create a session object with the user's id and role
    const session = { id: 1, role: 'admin' };
    // Create a token with the session object as the payload and the secret key
    const token = jwt.sign(session, secret);
    // Set a cookie with the session id as the value
    res.cookie('session', session.id);
    // Send the token to the client
    res.send(token);
  } else {
    // If the credentials are invalid, send a 401 response
    res.status(401).send('Wrong username or password');
  }
});

// Define a route for accessing a protected resource
app.get('/protected', verifyToken, (req, res) => {
  // Get the session id from the cookie
  const sessionId = req.cookies['session'];
  // Validate the session id (this is just a mock example)
  if (sessionId === req.user.id) {
    // If the session id matches the user id, send a 200 response
    res.send('You are authorized to access this resource');
  } else {
    // If the session id does not match the user id, send a 403 response
    res.status(403).send('Invalid session');
  }
});

// Start the app on port 3000
app.listen(3000, () => {
  console.log('Server running on port 3000');
});
```

This code exemplifies the integration of tokens and cookies in a simple authentication system using the Express framework. The application features a mock login route ("/login") where a user with the credentials "admin" and "password" receives a JSON Web Token (JWT). This token is then securely stored in a cookie on the client side.

A middleware function ("verifyToken") is defined to protect a route ("/protected") that requires authentication. The middleware extracts the JWT from the request header, verifies it using a secret key, and sets the user information in the request object. The protected route checks for a valid session by comparing the session ID stored in the cookie with the user ID decoded from the token. Access is granted if the IDs match.

This demonstration showcases the synergy between tokens and cookies for user authentication, enhancing security and enabling seamless communication between the client and server. The server runs on port 3000, and the console logs a message upon successful startup. This code serves as a foundation for understanding and implementing a secure authentication system in web applications.

### Benefits of Combining Cookies and Tokens

Combining cookies and tokens for authentication offers several benefits:

1. **Enhanced Security**: This approach leverages the security benefits of both cookies and tokens. Cookies are protected against CSRF attacks by default, and tokens can be protected against XSS attacks by storing them securely on the client-side.

2. **Scalability**: Tokens allow for stateless authentication, which is more scalable than session-based authentication as it does not require the server to store session information for each user.

3. **Flexibility**: Tokens are more flexible than cookies and can be used in various contexts, including mobile and desktop applications, and different domains.

4. **Improved User Experience**: Using cookies for session management allows the server to remember the user's session, providing a seamless user experience across multiple requests.

### Challenges in Combining Cookies and Tokens

While combining cookies and tokens for authentication offers several benefits, it also presents some challenges:

1. **Complexity**: Implementing both cookies and tokens for authentication can add complexity to the authentication flow. Developers need to handle both session cookies and tokens, and ensure they are both securely transmitted and stored.

2. **Token Management**: Tokens need to be securely stored on the client-side and included in the headers of each request. Managing token expiration and refresh can also add complexity.

3. **Cross-Site Scripting (XSS) Attacks**: While tokens are not vulnerable to CSRF attacks, they can still be susceptible to XSS attacks if not properly stored. Developers need to ensure that tokens are securely stored in a way that they are not accessible to JavaScript.

### Future Trends in Combining Cookies and Tokens

Looking ahead, the trend of combining cookies and tokens for authentication is expected to continue, driven by the need for secure and scalable authentication solutions. We can expect to see more advanced techniques for token storage and management, and improved standards for secure token transmission. Additionally, advancements in browser technologies and security standards will further enhance the security and usability of this approach.

In conclusion, combining cookies and tokens for authentication offers a robust and flexible solution for secure authentication in web applications. While there are challenges to this approach, with proper implementation and management, it can provide significant benefits in terms of security, scalability, and user experience.



## Conclusion 

In this blog post, we have explored the fundamental aspects of cookies and tokens, two critical components of secure authentication in web applications. Both cookies and tokens play a pivotal role in ensuring that only authenticated and authorized users can access resources and perform actions within an application, thereby safeguarding against potential security threats.

We delved deep into the basic concepts of cookies and tokens, and how they function in the context of authentication. We learned that cookies are used to maintain a user's session and provide stateful authentication, while tokens are used for stateless authentication. 

We also examined real-life examples and use cases of cookies and tokens, gaining insights into how they contribute to secure authentication. We further analyzed their advantages and disadvantages, helping us understand when to use one over the other.

In the latter part of the blog post, we discussed how cookies and tokens can be combined for enhanced security in web applications. We explored the benefits of this approach, such as enhanced security, scalability, and flexibility, as well as the challenges it presents, like complexity and potential susceptibility to XSS attacks.

As we look ahead, the trend of combining cookies and tokens for authentication is expected to continue, driven by the need for secure, scalable, and flexible authentication solutions. With advancements in browser technologies and security standards, we can anticipate even more secure and user-friendly authentication mechanisms in the future.

In conclusion, understanding cookies and tokens and how they contribute to secure authentication is essential for any software engineer or web developer. Whether you're developing a new web application or enhancing the security of an existing one, a solid grasp of cookies and tokens can help you implement robust and secure authentication mechanisms, providing a safe and seamless user experience.





## References

- [Pros and Cons of Cookies and Tokens for Authentication](https://www.loginradius.com/blog/engineering/cookie-based-vs-cookieless-authentication/) 
- [Combining Cookies and Tokens for Enhanced Security](https://blog.bytebytego.com/p/password-session-cookie-token-jwt) 
- [Real-life examples of cookies usage](https://forums.fauna.com/t/do-i-need-a-backend-api-between-faunadb-and-my-app-what-are-the-use-cases-of-an-api/95) 
- [Case studies of cookies implementations](https://brightsec.com/blog/csrf-example/) 
- [Introduction to Cookies and Tokens for Authentication](https://curity.io/resources/learn/token-handler-overview/) 
- [Real-life examples of tokens usage](https://auth0.com/blog/refresh-tokens-what-are-they-and-when-to-use-them/) 
- [Case studies of tokens implementations](https://brightsec.com/blog/csrf-example/) 
- [Understanding Cookies](https://jwt.io/introduction) 
- [Understanding Tokens](https://curity.io/resources/learn/oauth-cookie-best-practices/) 
- [Lessons learned from cookies and tokens usage](https://brightsec.com/blog/csrf-example/) 
- [Explanation of cookies and tokens](https://community.auth0.com/t/combining-cookie-and-token-authentication-in-dotnet-core-2-0/11319) 
- [How cookies and tokens contribute to secure authentication](https://forums.fauna.com/t/do-i-need-a-backend-api-between-faunadb-and-my-app-what-are-the-use-cases-of-an-api/95) 
- [Impact of cookies and tokens on web security](https://brightsec.com/blog/csrf-example/) 
- [Role of Cookies and Tokens in Authentication](https://www.ory.sh/docs/kratos/session-management/overview) 
- [Comparison of cookies and tokens in real-world scenarios](https://auth0.com/blog/refresh-tokens-what-are-they-and-when-to-use-them/) 
- [Importance of secure authentication](https://developer.mozilla.org/en-US/docs/Web/HTTP/Cookies) 
- [How cookies work in authentication](https://community.auth0.com/t/combining-cookie-and-token-authentication-in-dotnet-core-2-0/11319) 
- [Combining Cookies and Tokens for Enhanced Security](https://blog.bytebytego.com/p/password-session-cookie-token-jwt) 
- [Understanding Cookies](https://developer.mozilla.org/en-US/docs/Web/HTTP/Cookies) 
