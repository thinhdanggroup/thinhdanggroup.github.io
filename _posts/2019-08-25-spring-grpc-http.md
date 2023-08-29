---
author:
  name             : "Thinh Dang"
  avatar           : "/assets/images/avatar.png"
  bio              : "Experienced Fintech Software Engineer Driving High-Performance Solutions"
  location         : "Viet Nam"
  email            : "thinhdang206@gmail.com"
  links:
    - label: "Linkedin"
      icon: "fab fa-fw fa-linkedin"
      url: "https://www.linkedin.com/in/thinh-dang/"
toc: true
toc_sticky: true
header:
  overlay_image: /assets/images/grpc-json.png
  overlay_filter: 0.5 
  teaser: /assets/images/grpc-json.png
title:  "Xây dựng Service cung cấp HTTP và gRPC API bằng Spring"
tags: 
- Spring
- gRPC
---

Nếu bạn đã từng xây dựng một ứng dụng với gRPC thì chắc chắn bạn đã biết được những ưu điểm của gRPC là khả năng truyền tải nhanh(lên tới 8 lần) và tối ưu hoá nội dung tin nhắn gửi đi. Nhưng hẳn là bạn cũng biết được khuyết điểm lớn nhất của nó là không phải ứng dụng nào cũng hỗ trợ giao thức gRPC. Ví dụ như browser không thể gọi trực tiếp một service bằng gRPC. Vậy tại sao chúng ta không xây dựng một service mà có thể hỗ trợ API cho gRPC và Http?

## 1. Giới thiệu

[GRPC Gateway](https://github.com/grpc-ecosystem/grpc-gateway) là một giải pháp cho vấn đề này nhưng nó yêu cầu ta phải triển khai một service `side car`. Tôi đã từng thử nó cho một sản phẩm thực tế nhưng đã có rất nhiều vấn đề xuất hiện với `gRPC Gateway` này như authenticate, streaming data, bảo mật đường truyền, lỗi networking giữa gateway và service,... Lúc này, cách duy nhất để giải quyết vấn đề là ta phải vào thay đổi code của `gRPC Gateway` nhưng không phải ai cũng biết về golang. Cùng với đó, một khuyết điểm chung của gateway là gói tin sẽ tốn thời gian đi qua thêm một `hop`, điều này cũng ảnh hưởng một phần đến độ trễ của tin nhắn.

Đó là lúc chúng ta cần một service hỗ trợ cả hai đầu API gRPC và Http. Với `Spring Boot`, mọi thứ đều trở nên dễ dàng khi ta chỉ cần thêm vài cấu hình. Lúc này, service của chúng ta sẽ có cả hai đầu API sử dụng chung `data transfer object` là object được tạo ra từ file `proto`.

Trước khi đến với phần 2, mình hi vọng các bạn đã có kiến thức cơ bản về Spring Boot, gRPC, Protobuf, ...

## 2. Cách thực hiện

Mình sẽ tạo một service Ping Pong hỗ trợ API Http và gRPC. Toàn bộ ví dụ mẫu nằm repository [spring_grpc_http](https://github.com/thinhdanggroup/spring_grpc_http).

### 2.1. Định nghĩa API

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

Sử dụng command `mvn clean install` để tạo các object từ file proto.

### 2.2. Xây dựng gRPC Controller

Sử dụng gRPC thư viện [grpc-spring-boot-starter](https://github.com/LogNet/grpc-spring-boot-starter), đây là thư viện khá hay nếu bạn muốn tạo một `service gRPC`. Ta chỉ cần cấu hình port chạy gRPC và tập trung hiện thực logic mong muốn mà không cần quan tâm về nhiều cách khởi tạo `gRPC Server`. Bên cạnh, thư viện này cũng cung cấp tính năng tạo `interceptor`, ta có thể thêm nhiều lớp interceptor để hỗ trợ logging, authenticate, dịch cách exception sang error code tương ứng để trả về người dùng,...

Thêm cấu hình port vào file `application.yaml` để khởi chạy gRPC service ở port `6790`:

```yaml
grpc:
  port: 6790
```

Bên cạnh, ta cũng cần thêm anotation `@GRpcService` vào class [GrpcController](https://github.com/thinhdanggroup/spring_grpc_http/blob/master/core/src/main/java/com/thinhda/spring/grpc/core/controller/GrpcController.java) để có thể khởi tạo một service gRPC.

### 2.3. Sử dụng protobuf class cho Http Controller

Đây là phần quan trọng nhất để ta có thể sử dụng object được tạo ra từ proto file. Thêm [class config](https://github.com/thinhdanggroup/spring_grpc_http/blob/master/core/src/main/java/com/thinhda/spring/grpc/core/config/ApiConfig.java) cấu hình sau

```java
package com.thinhda.spring.grpc.core.config;

import lombok.Data;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.converter.protobuf.ProtobufJsonFormatHttpMessageConverter;
import org.springframework.web.filter.CommonsRequestLoggingFilter;

@Data
@Configuration
public class ApiConfig {

    @Bean
    public ProtobufJsonFormatHttpMessageConverter protobufHttpMessageConverter() {
        return new ProtobufJsonFormatHttpMessageConverter();
    }

}
```

Phương pháp decode mặc định của Spring không hỗ trợ format và decode `object` được tạo ra từ file proto. Nhưng ta có thể thay đổi cách format này bằng cách cung cấp cho Spring một bean là `ProtobufJsonFormatHttpMessageConverter`.


### 2.4 Kiểm tra

Sử dụng [BloomRPC](https://github.com/uw-labs/bloomrpc) (công cụ để gọi Api của gRPC) để kiểm tra gRPC API:

![grpc](../assets/images/grpc_test.jpg)

Kiểm tra Http Api với Postman:

![http](../assets/images/http_test.jpg)

## 3. Kết luận

Một service cung cấp cả hai đầu API Http và gRPC mang lại rất nhiều lợi ích khi người dùng muốn gọi vào service của bạn, họ có thể lựa chọn tốc độ truyền tải nhanh và nhẹ khi giao tiếp với gRPC hoặc cũng có thể lựa chọn cách đơn giản, dễ hiện thực bằng Http. Còn ở phía của bạn, không hề có dòng `duplicate code` dư thừa nào. Thật tuyệt phải không nào.
