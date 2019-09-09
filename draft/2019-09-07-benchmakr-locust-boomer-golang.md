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

# Chế độ phân tán của Locust

Khi mà một máy đơn không thể tạo đủ số lượng người dùng mà bạn cần thì lúc này cơ chế phân tán sẽ chạy load test trên nhiều máy khác nhau. Locust sẽ hoạt động gồm 2 thành phần: master và slave.

- Master: Khi ta khởi chạy một instance Locust dưới chế độ master thì nó sẽ cung cấp một giao diện web để xem các giá trị thống kê, nó cũng sẽ không giả lập bất kì người dùng nào để load test mà chỉ đảm bảo nhiệm vụ cung cấp UI.
- Slave: Có thể được viết bằng nhiều ngôn ngữ Python, Java hoặc Golang. Slave sẽ hoạt động độc lập nhau, nhận lệnh điều khiển từ Locust master. Slave sẽ giả lập người dùng và gửi yêu cầu cho service, sau đó nó ghi nhận thông tin như latency rồi trả cho master.

![]()

# Boomer

Trong phần này chúng ta sẽ đi sâu vào cơ chế hoạt động master slave của Locust thông qua thư viện boomer. Thư viện boomer cung cấp khả năng giả lập số người dùng gửi yêu cầu vào hệ thống. Nhờ vào việc sử dụng goroutine nên boomer mang lại hiệu năng vượt trội so với các ngôn ngữ khác. Có một lưu ý là hãy sử dụng boomer như thư viện chứ không phải một công cụ benchmark.

Để dễ hiểu hơn về cách sử dụng boomer. Mình sẽ tạo ra một ví dụ đơn giản như sau: mình sẽ load test một `ping pong service` bằng locust và boomer. Mô hình triển khai và hoạt động như hình bên dưới.

![]()

Khi ta thực hiện việc tạo một bài test mới trên Locust UI thì chuyện gì sẻ xảy ra?

- Người dùng sẽ tạo ra một bài kiểm tra gồm lượng người dùng cần mô phỏng (Number of users to simulate) và số lượng request mỗi giây (Hatch rate).
- Hai thông số cấu hình bài test trên sẽ được gửi đến từng slave của locust. Với boomer, mỗi người cần mô phỏng là một goroutine. Số lượng người dùng cần tạo ra để mô phỏng sẽ được chia đều cho số slave, ví dụ bạn có 4 slave và cần tạo 10000 người dùng thì mỗi slave sẽ tọa 2500 người dùng để bắn request.
- Sao khi mỗi goroutine được khởi tạo, nó sẽ thực hiện một `Task` được định nghĩa sẵn từ trước. `Task` sẽ thực hiện một business logic của bạn. Như ví dụ ở đây, Task sẽ là thực hiện một request gọi vào API ping. Ngoài ra, Boomer hỗ trợ việc đặt trọng số cho từng task, tính năng này khá hữu hiệu khi bạn cần test nhiều API cùng lúc.
- Ở mỗi `Task`, ta cần ghi nhận trạng thái của request là thành công hay thất bại và các meta data cho nó. Như ví dụ dưới đây là mình đã tính latency cho việc request vào API /ping sau đó ghi nhận kết quả về Locust thông qua hàm `TBD`. Trong trường hợp lỗi xảy ra, chúng ta cũng cần ghi nhận các kết quả để hỗ trợ thống kê.
- Ở trên giao diện của Locust, ta sẽ thấy được các thông số cần thiết 

Cơ chế master slave của locust.

Simple client.

# Load testing với rate limit


# Tổng kết
