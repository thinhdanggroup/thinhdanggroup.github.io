---
layout: post
title:  "Nhật ký làm quen với Streaming Data"
author: thinhda
categories: [streaming, kafka, avro, spark]
image: assets/images/streaming/banner.png
tags: featured
---

Chào mọi người, không biết mọi người đã trải qua tính cảnh như mình chưa. Trước đây, mình là `Software Engineer` tại một công ty fintech và chuyên xây dựng hệ thống real-time với latency vài ms (hệ thống accounting). Và rồi một ngày, sếp mình đưa mình một project xây dựng hệ thống report `near real-time` (hệ thống report cho accounting). Mình kiểu "what the f**k" nhưng rồi vẫn nhận vì mình nghĩ sẽ học thêm được rất nhiều vì đây là hệ thống cần techstack hoàn toàn mới (thế giới của big data) so với những thứ mình đã biết trước đây. Và rồi, một thế giới mới đến thật, một hệ thống offline report khác hoàn toàn với hệ thống online transaction từ logic tính toán, cách monitoring, logging, công nghệ và cả mindset. Thời gian đầu nó gần như làm mình ngụp lặn với những kiến thức và vấn đề. Nếu các bạn cũng gặp tình huống như mình, lời khuyên chân thành hãy bắt đầu với quyền [Designing Data-Intensive Applications](https://www.amazon.com/Designing-Data-Intensive-Applications-Reliable-Maintainable/dp/1449373321), vì chưa có người hướng dẫn nên trước đây mình đã vấp ngã rất nhiều nhưng quyển sách này quả thật đã đưa mình tới chân trời mới. Giờ cùng mình làm quen với streaming data nhé.

## Stream Processing với Batch processing

![react](../assets/images/streaming/react-time.png)

Đây là kiến thức đầu tiên mình thấy cơ bản và giá trị nhất. Chúng không có một định nghĩa chính thống nhưng có thể hiểu đơn giản như sau: 

- Với batch processing: 
  - Một tập dữ liệu được thu thập qua thời gian, sau đó đưa vào hệ thống phân tích. Hay nói cách khác, bạn thu thập toàn bộ dữ liệu và đem đi xử lý.
  - Phù hợp với những hệ thống có report không cần real-time như Payroll, Billing, ...
  - Ưu điểm: đơn giản, dễ hiện thực, dễ xử lý khi có sự cố, phù hợp với các hệ thống truyền thống chưa hỗ trợ stream.
  - Nhược điểm: khi lượng dữ liệu lớn thì thời gian xử lý cũng lâu hơn, khả năng scale không tốt
- Với stream processing: 
  - Dữ liệu được đưa vào hệ thống phân tích từng phần nhỏ, và lượng dữ liệu này là vô hạn, không bao giờ dừng lại.
  - Phù hợp với những hệ thống cần report realtime như fraud detection, log monitoring, ...
  - Ưu điểm: report real-time, khả năng scale tốt khi data càng ngày càng lớn.
  - Nhược điểm:
    - Xây dựng phức tạp, phải đảm bảo yếu tố idempotent, cần checkpoint, ...
    - Monitoring phức tạp
    - Khắc phục sự cố khó hơn nhiều so với batch processing

Thời gian đâu, mình đã nghĩ đơn giản, streaming khá giống như cách ta xử lý request-response của hệ thống realtime, mỗi event tới thì mình sẽ xử lý như 1 request, và lưu id event lại để mình không xử lý hai lần cũng như kiểm tra missing dễ hơn. Thế là mình bắt tay xây dựng một hệ thống bằng java. Nhưng hệ thống hoàn toàn thất bại về performance khi một hệ thống offline phải chiụ tải và xử lý như hệ thống online. Hệ thống offline luôn luôn nên xử lý data dạng batch, nó giảm đi rất nhiều IO và sử dụng tối ưu hoá resource hệ thống.

Những nâng cấp bắt đầu, mình chuyển sang xử lý từng batch nhỏ với việc scan database theo một window time và lưu lại checkpoint sau khi xử lý xong, performance quả thực tăng một cách tích cực. Mọi thứ hoàn toàn trông khá tuyệt. Nhưng đời không như mơ, những late event đến, chúng nằm ngoài khoảng thời gian window của mình, giải pháp truy vấn bằng thời gian của hệ thống khác làm window time là sai lầm lớn nhất. Chúng ta nên phải tránh việc này, nếu không muốn phải hối hận cho sao này. Điều này dẫn tới khái niệm watermark, các kỹ thuật làm việc với window sẽ được nói ở series sau.

## Đau để trưởng thành

Qua những bài học trên, mình nhận ra nên bắt đầu mọi thứ chuẩn chỉ hơn bằng cách:

- Hiểu rõ data mình đang làm việc bằng batch processing, làm rõ hết các business flow (`make the right thing first`) rồi hãy ứng dụng stream processing.
- Sử dụng các technical stack của big data: CDC, spark, kafka, spark streaming, kafka streaming.

Trong loạt bài viết này mình sẽ dùng ứng dụng đơn giản về báo cáo tài chính để làm quen với các công nghệ trên. Đợi part 2 nhé.