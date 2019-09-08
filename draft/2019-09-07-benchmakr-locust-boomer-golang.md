---
layout: post
title:  "Load testting service "
author: thinhda
categories: [ gRPC ]
image: assets/images/grpc-comparison.png
tags: featured
---

Một bước mà chúng ta thường xuyên bỏ qua và coi thường khi xây dựng một service mới đó là load test nó. Load test là một quá trình quan trọng trước khi đưa sản phẩm vào thực tế. Load test mang lại rất nhiều lợi ích: cho ta biết khả năng phục vụ bao nhiêu người dùng cùng lúc của service, chất lượng dịch vụ trong các tình trạng tải khác nhau, phát hiện được những `bug` chỉ xảy ra trong môi trường multi-threading, ...

# Giới thiệu

Load test là một dạng của [performance testing](https://www.guru99.com/performance-testing.html). Chúng ta sẽ xác định được hiệu năng của hệ thống trong các điều kiện tải khác nhau trong thực tế. Bài kiểm tra này giúp ta hiểu hơn về hành vi của hệ thống khi có nhiều người dùng truy cập đồng thời.

Các bài load testing thường dùng để:

- Đo lượng request tối đa mà ứng dụng có thể phục vụ.
- Số lượng người dùng có thể phục vụ đồng thời và khả năng mở rộng khi có nhiều người dùng hơn truy cập.
- Nhận dạng những vị trí `bottleneck` trước khi lên production.
- Giảm rủi ro khi hệ thống downtime.
- Hiểu về hệ thống trong các điều kiện tải khác nhau: đánh giá hiệu năng database, thời gian các transaction, vấn đề thiết kế, giới hạn phần cứng,... để tạo ra những quyết định tinh chỉnh phù hợp.

Load testing còn nhiều lợi ích tích cực khác, nếu bạn vẫn chưa quen với khái niệm load testing có thể tìm hiểu thêm ở [Load Testing Tutorial](https://www.guru99.com/load-testing-tutorial.html).

Để thực hiện một bài load testing, ta có thể chọn nhiều công cụ khác nhau như Gatling, JMeter, The Grinder,... Nhưng trong bài viết này, mình sẽ sử dụng một công cụ khá nổi tiếng khác đó là Locust. Tại sao Locust được xem là tốt hơn, mình sẽ cho bạn thấy lợi thế của Locust so với Jmeter ( Đây là tool khá nổi tiếng về load testing). Đầu tiên, GUI của Jmeter khá tốt nhưng không phải nghiệp vụ nào cũng có thể `point-and-click` là được. Thứ hai, Jmeter là `thread-bound`, nghĩa là mỗi user bạn tạo ra trong quá trình test là một thread, hay nói cách khác, khi ta giả lập hàng ngàn người dùng cùng lúc trên một máy thì nó không thực hiện tốt được.

Locust là một công cụ load testing mà có thể tính toán được có bao nhiêu user đồng thời mà hệ thống có thể xử lý được. Locust cung cấp một Web-based UI, khả năng `load test distributed` trên nhiều máy và có thể tạo ngữ cảnh test với Python, Golang hoặc Java. Mình đã thử qua các thư viện kết nối với Locust và thấy [Boomer](https://github.com/myzhan/boomer) là tốt nhất vì các ưu điểm sau:

- Tạo load test nhưng ít tốn tài nguyên và tối ưu hóa resource nhờ được biết bằng Golang.
- Viết các testcase khá nhanh và dễ.
- Hỗ trợ rate limit.
- Có thể custom output.

# Cơ chế hoạt động

Mô hình deploy ví dụ: ping service, boomer client, locust master.

Cơ chế master slave của locust.

Simple client.

# Load testing với rate limit


# Tổng kết
