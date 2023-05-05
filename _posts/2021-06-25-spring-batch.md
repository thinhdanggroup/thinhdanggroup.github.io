---
layout: post
title:  "Spring Batch: Xử lý dữ liệu dạng batch đơn giản"
author: thinhda
categories: [batch processing, sprint, spring batch]
image: assets/images/streaming/spring-batch-banner.png
tags: 
---

Các bạn đã bao giờ gặp tình cảnh được yêu cầu tính report từ dữ liệu trong database để hỗ trợ cho business. Thường thì chúng ta sẽ nghĩ ngay tới giải pháp mì ăn liền là dùng script python với pandas để xử lý đóng csv được xuất từ database. Hoặc một yêu cầu hay gặp hơn, khi chúng ta nâng cấp hệ thống từ version cũ sang version mới thì dữ liệu cần được migrate. Thường thì chúng ta phải từ hiện thực một tool hay script để làm điều này. Nhưng hôm nay, mình giới thiệu các bạn một framework nổi tiếng đó là Spring Batch. Cùng mình bắt đầu phần 2 của series làm quen với Streaming Data nào.

# Spring Batch là gì?

Chắc hẳn, các bạn ai cũng đã nghe về Spring Framework, [Spring Batch](https://docs.spring.io/spring-batch/docs/current/reference/html/job.html) là một phần của framework này. Chúng giúp ta xử lý một chuỗi công việc trong một lúc, giảm overhead so với việc xử lý từng request một.

Tại sao chúng ta cần dùng Spring Batch?

- Khi cần xử lý một lượng lớn dữ liệu (không thể load một lần lên memory) trong một khoảng thời gian ngắn.
- Spring Batch hỗ trợ sẵn việc đọc, ghi vào CSV, database, ...
- Spring Batch cũng hỗ trợ sẵn các `cross-cutting concern` như monitoring, logging, cơ chế fail-tolerance, ...
- Ngoài ra ta còn dễ dàng start, stop job, quản lý resource các thứ

Qua đó ta thấy, chúng ta chỉ cần tập trung vào business của bản thân, phần còn lại hãy cứ để Spring Batch lo.


Mình cũng sẽ giới thiệu sơ vể kiến trúc của Spring Batch như sau (khuyên các bạn nên đọc chi tiết ở [đây](https://docs.spring.io/spring-batch/docs/current/reference/html/job.html)):

![gioi thieu step](/assets/images/streaming/spring-batch-component-1.png)

- **JobLaucher**: `interface` cho phép thực thi Job với tham số truyền vào
- **Job**: nhận tham số và thực thi các `Step` được định nghĩa sẵn
- **Step**: ta sẽ qui định các business ở đây. Mỗi `Step` sẽ gồm 3 bước: *Item Reader*, *Item Processor*, *Item Writer*. Hai bước `Reader` và `Processor` sẽ được xử lý đồng thời tuỳ vào lượng worker, riêng bước `Writer` sẽ xử lý theo `chunk`.
- **JobRepository**: cung cấp CRUD cho JobLaucher, Job, Step.

# Ví dụ tính toán trial balance report 

Trong phần 1, mình đã giới thiệu về ví dụ mình sẽ làm cho xuyện suốt series. Nếu các bạn có bỏ qua phần 1 thì trở về đọc lại trước nhé. Giờ thì cùng mình bắt đầu trải nghiệm Spring Batch nào. 

Để giải bài toán `Bảng cân đối thử`, mình sẽ chia job ra 2 step như sau:

![example-design](../../assets/images/streaming/example-design.png)

Thiết kế khá dễ hiểu phải không nào? 

- Step1: mình sẽ tính tổng debit,credit theo từng ngày của từng user
- Step2: mình sẽ tính open, close của từng ngày bằng cách sort sau đó loop trên tập data để lấy `close = open + credit - debit` và `open ngày T` = `close ngày T-1`

Vậy còn code thì như nào? 

1. Bắt đầu với `pom.xml`

    ```xml

    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
            <version>2.3.1.RELEASE</version>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-batch</artifactId>
            <version>2.3.1.RELEASE</version>
        </dependency>
    </dependencies>

    ```

2. Enable Spring Batch bằng annotation @EnableBatchProcessing và định nghĩa pipeline như [BatchConfiguration](https://github.com/thinhdanggroup/kafka-stream-financial-report-example/blob/main/spring-batch/src/main/java/io/github/thinhdanggroup/config/BatchConfiguration.java)
3. Còn lại là tập trung vào hiện thực business logic trong [processor](https://github.com/thinhdanggroup/kafka-stream-financial-report-example/tree/main/spring-batch/src/main/java/io/github/thinhdanggroup/processor)

Nếu bạn muốn xem chi tiết, có thể tham khảo ở repo [kafka-stream-financial-report-example](https://github.com/thinhdanggroup/kafka-stream-financial-report-example)

Thế là đã xong phần 2, hướng dẫn batch processing với Spring Batch. Chờ đợi series tiếp theo về một stack phổ biến xử lý batch là `Spark` nhé.