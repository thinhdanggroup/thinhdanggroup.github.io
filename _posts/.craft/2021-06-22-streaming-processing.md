---
layout: post
title:  "Spring Batch: Xử lý dữ liệu dạng batch đơn giản"
author: thinhda
categories: [batch processing, sprint, spring batch]
image: assets/images/streaming/banner-part1.jpeg
tags: featured
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

![anh spring] 