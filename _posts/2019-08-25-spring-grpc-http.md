---
layout: post
title:  "Xây dựng Spring service với API HTTP và GRpc"
author: thinhda
categories: [ Spring, Grpc ]
image: assets/images/client-db.jpg
tags: [Spring,GRpc]
---

Nếu bạn đã từng xây dựng một ứng dụng với GRpc thì chắc chắn bạn đã biết được những ưu điểm của GRpc là khả năng truyền tải nhanh ( lên tới 8 lần ). Nhưng hẳn là bạn cũng biết được khuyết điểm lớn nhất của nó là không phải ứng dụng nào cũng có thể gọi GRpc dễ dàng. Ví dụ như browser không thể gọi trực tiếp một service bằng GRpc. Vậy tại sao chúng ta không xây dựng một service mà có thể hỗ trợ API cho GRpc và Http?

# 1. Giới thiệu

[GRpc gateway](https://github.com/grpc-ecosystem/grpc-gateway) là một giải pháp cho vấn đề này nhưng nó yêu cầu ta phải deploy một service `side car`. Và khi đi vào vận hành thực tế, rất nhiều vấn đề sẽ xuất hiện với grpc gateway này như authenticate, streaming data, bảo mật đường truyền, ... Nó yêu cầu ta phải vào thay đổi code của Grpc gateway và không phải ai cũng thích điều này.

Vậy tại sao không tạo một service mà có thể hỗ trợ cả hai loại API này? Với `Spring Boot`, mọi thứ ta cần làm chỉ cần là cấu hình. Lúc này, ta sẽ có cả hai đầu API sử dụng chung DTO là object được tạo ra từ file `proto`.

Trước khi đến với phần 2, mình hi vọng các bạn đã có kiến thức cơ bản về Spring Boot, GRpc, Protobuf, ...

# 2. Cách thực hiện

Mình sẽ tạo một service Ping Pong hỗ trợ API Http và Grpc. Toàn bộ ví dụ mẫu nằm repository [spring_grpc_http](https://github.com/thinhdanggroup/spring_grpc_http).

## 2.1. Định nghĩa API

Tạo một API proto là Ping theo [định nghĩa](https://github.com/thinhdanggroup/spring_grpc_http/blob/master/core/src/main/proto/ping.proto) sau:

```proto
syntax = "proto3";

// options for Java generated sources
option java_multiple_files = true;
option java_package = "com.thinhda.spring.grpc.core.model";
option java_outer_classname = "CoreGrpcApi";

package sms.core;

message PingRequest {
    int64 timestamp = 1;
}

message PingResponse {
    int64 timestamp = 1;
    string message = 2;
}

service CoreService {
    rpc Ping (PingRequest) returns (PingResponse);
}
```

Sử dụng command `mvn clean install` để tạo các object sử dụng.

## 2.2. Xây dựng Grpc Controller

Sử dụng Grpc 
