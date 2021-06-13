---
layout: post
title:  "Hướng dẫn public service lên internet với ngrok và docker-compose"
author: thinhda
categories: [ ngrok, docker-compose, nginx]
image: assets/images/executor/banner.jpeg
tags: featured
---

Nếu bạn đang muốn public service chạy ở máy local ra mạng internet, hoặc là một ssh server hay ftp server thì Ngrok là một giải pháp hoàn hảo cho vấn đề này.

Ngrok hỗ trợ rất nhiều tính năng như:

- Public một web service qua HTTPS url
- TCP tunnels
- Web socket cho các ứng dụng realtime
- Replay webhook request

Trong bài viết này, mình sẽ hướng dẫn sử dụng ngrok một cách dễ dàng với docker-compose. Như chúng ta đã biết, docker giúp ta giải quyết các vấn đề phức tạp về cài đặt và cấu hình hệ thống. Ví dụ dưới đây, mình sẽ demo một hệ thống với nhiều thành phần: proxy, web server, ssh server.


![deployment](/assets/images/ngrok/ngrok-docker.png)

Tất cả source code có sẵn ở [thinhdanggroup/ngrok-docker](https://github.com/thinhdanggroup/ngrok-docker), các thành phần:

- `ngrok` chưa ngrok client, sẽ giao tiếp trực tiếp với ngrok-service để tạo tunnel tới các server local. Mình config ngrok bằng conf `ngrok.yml`. Hãy nhớ thay đổi giá trị `authtoken` cho tài khoản của bạn.
- `nginx` vai trò là một proxy, nó sẽ route request tới đúng server bạn muốn. Trong ví dụ này chỉ có một web server nhưng nếu chúng ta có nhiều web khác, sử dụng một nginx ở đây là một giải thuận tiện khi muốn public nhiều web cùng lúc.
- `simple web app` là một web server đơn giản để kiểm tra tính năng tạo tunnel cho HTTP.
- `ssh server` cùng là một ssh server đơn giản để kiểm tra tính năng tạo tunnel cho SSH. Vì ssh-server cần authen người dùng nên hãy nhớ thêm vào file `public-key` để ssh được nhé.


Bắt đầu sử dùng nào:

- Khi tất cả config đã ổn, ta bắt đầu khởi động cluster
	```sh
	docker-compose up
	```
- Khi cluster khởi động thành công, ta sẽ thấy log sau:
	![log-docker](/assets/images/ngrok/log-docker.png)
- Có 2 tunnel đã được tạo là:
  - HTTP: truy cập vào domain https://4db6390a9f3c.ngrok.io
        ![http](/assets/images/ngrok/http-example.png)
  - SSH: với ssh ta chạy lệnh `ssh -p 14693 root@2.tcp.ngrok.io`
        ![ssh](/assets/images/ngrok/ssh-example.png)

Với docker thì mọi thứ thật dễ dàng, hãy thử áp dụng và thay đổi simple-web thành image bạn muốn nhé.