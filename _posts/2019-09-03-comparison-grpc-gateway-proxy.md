---
layout: post
title:  "So sánh grpc gateway với gRPC web"
author: thinhda
categories: [ gRPC ]
image: assets/images/grpc-comparison.png
tags: featured
---

Bạn đang có một service sử dụng gRPC để đảm bảo vấn đề hiệu năng khi giao tiếp. Nhưng rồi một ngày, bạn muốn xây một admin web cho nó nhưng trình duyệt lại không hỗ trợ giao thức HTTP/2, hay đơn giản là service khác muốn gọi qua HTTP. Và bạn tìm đến hai giải pháp grpc-gateway và gRPC-Web nhưng lại không biết nên dùng cái nào. Bài viết này sẽ cho bạn cái nhìn tổng quát về hai giải pháp này.

## 1. Khái niệm cơ bản

### 1.1. grpc-gateway là gì

[grpc-gateway](https://github.com/grpc-ecosystem/grpc-gateway) là một `reverse-proxy server` mà giúp ta chuyển từ `RESTful HTTP API` sang `gRPC`. Nó sẽ đọc định nghĩa của protobuf service và tự tạo ra đoạn mã để chạy gateway.

![grpc-gateway-model](/assets/images/grpc-gateway-model.png)

grpc-gateway đã cung cấp công cụ `protoc-gen-grpc-gateway` để tạo ra gateway. Bên cạnh, ta cũng dễ dàng định nghĩa HTTP API với các đặc tả ngay trong file proto.

### 1.2. gRPC-Web là gì

![grpc-web-model](/assets/images/grpc-web-model.png)

[gRPC-Web](https://github.com/grpc/grpc-web) là một thư viện Javascript để người dùng trình duyệt giao tiếp được với gRPC service. Hiện taị, gRPC-Web đang được sử dụng rộng rãi và có thể sử dụng cho production. gRPC-Web giao tiếp với gRPC service qua một gateway proxy (mặc định là [Envoy](https://www.envoyproxy.io/)).

gRPC-Web hỗ trợ hai dạng gửi tin nhắn:

- `mode=grpcwebtext`: Đây là dạng mặc định.
  - Content-type: application/grpc-web-text.
  - Payload là `base64-encoded`.
  - Hỗ trợ gọi một chiều và server streaming.
- `mode=grpcweb`: hỗ trợ định dạng binary protobuf.
  - Content-type: application/grpc-web+proto
  - Payload là định dạng binary.
  - Chỉ hỗ trợ gửi một chiều.
  - Sẽ có hiệu năng đường truyền tốt hơn vì nội dung tin nhắn ở dạng binary.

## 2. So sánh

Trước khi đi vào so sánh chi tiết về grpc-gateway và gRPC-Web, mình sẽ so sánh hai phương pháp này với phương pháp không sử dụng gateway như [grpc_http_spring](https://medium.com/@thinhda/build-service-that-provides-http-and-grpc-api-with-spring-9e7cff7aa17a):

- Ảnh hưởng nhiều hiệu năng khi phải đi qua thêm `1 hop`, có thể tốn thêm cả chi phí parsing.
- Tốn chi phí vận hành hệ thống khi phải theo dõi  thêm một gateway và sửa lỗi gateway nếu chúng có vấn đề.
- Sử dụng gateway sẽ giảm thiểu được khả năng bị `duplicate code`

Đó là tất cả những khác biệt lớn nhất giữa dùng và không dùng gateway. Giờ chúng ta đi vào phần quan trọng nhất trước khi ra bạn quyết định nên dùng phương pháp nào.

### 2.1. Cách sử dụng

Ta có thể rõ ràng thấy được khác biệt ở việc sử dụng là với grpc-gateway, ta sẽ tạo riêng một reverse-proxy bằng định nghĩa protobuf có sẵn. Ở phía front-end, ta gọi được trực tiếp qua REST APIs. Còn với gRPC-Web, ta phải hiện thực trực tiếp đoạn code ở phía front-end.

Với mô hình của gRPC-Web dùng Envoy, ta có thể cung cấp gRPC service với một port của Envoy. Các **ứng dụng mobile**, **gRPC-Web** hay **service khác** có thể dễ dàng giao tiếp với máy chủ chỉ với một đường dẫn. Còn grpc-gateway chỉ cung cấp duy nhất REST API, còn gRPC thì phải gọi trực tiếp service bên trong.

### 2.2. Hiệu năng

**grpc-gateway** sử dụng một **reverse proxy** để parsing tin nhắn json sang binary của protobuf, sau đó mới dùng tin nhắn được **parsing** gọi vào gRPC service của chúng ta, rồi khi có phản hồi, lại tốn thêm một bước parsing nữa. Như các bạn thấy, quá nhiều chi phí parsing ở đây, điều này sẽ ảnh hưởng không tốt tới hiệu năng.

Còn với **gRPC-Web** thì tin nhắn gửi đi đã là định dạng binary nên chi phí truyền tải sẽ thấp. Khi đến proxy, sẽ không có chi phí nào cho việc parsing vì tin nhắn đã đúng định dạng của nó. 

Rõ ràng, về mặt hiệu năng thì grpc-gateway thua khá nhiều so với gRPC-Web.

### 2.3. Bảo mật

Đầu tiên là bảo mật kênh truyền, cả hai đều hỗ trợ việc cấu hình TLS. Điều này đảm bảo sự an toàn khi bạn cung cấp API cho bên ngoài.

Tiếp theo, mình nói về cách `Authorization`. Nếu bạn đã từng làm việc với gRPC hẳn bạn cũng biết các thông tin về xác thực của người dùng thường nằm ở trường header `authorization`, đa số là jwt sẽ nằm trong đó. Và cả hai cách dùng gateway đều hỗ trợ truyền header này.

Về CORS, đây không phải là vấn đề lớn vì cả hai cách ta đều có thể cấu hình chúng.

### 2.4. Khả năng mở rộng

Với **grpc-gateway**, với mỗi thay đổi đặc tả API ở file proto, ta phải chạy tool để tạo lại code gateway. Và nếu trước đây bạn có một số chỉnh sửa ở đoạn code của gateway, điều này lại cần bạn phải tìm cách tổng hợp giữa code cũ và mới. Lúc này, ta phải thay đổi code ít nhất 2 vị trí là front-end và grpc-gateway.

Còn **gRPC-Web**, mỗi khi thay đổi về API ta chỉ cần thay đổi code ở phía front-end.

## 3. Tổng kết

Như các bạn đã thấy, cả hai cách trên đều có ưu và nhược điểm riêng. Tuỳ điều kiện bạn đang có và nhu cầu bạn cần, bạn sẽ chọn một cách thức phù hợp nhất. Nếu bạn đang viết một service từ đầu hay đã có sẵn một envoy proxy, hãy sử dụng gRPC-Web. Nhưng nếu bạn đã có một front-end và đang cần thay đổi backend sang gRPC, hãy dùng grpc-gateway sẽ tiết kiệm được nhiều chi phí viết lại front-end.
