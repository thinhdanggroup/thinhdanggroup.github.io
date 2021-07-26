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

Chắc hẳn, các bạn ai cũng đã nghe về Spring Framework.