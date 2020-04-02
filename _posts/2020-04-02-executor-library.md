---
layout: post
title:  "Executor: Worker Pool cho Golang"
author: thinhda
categories: [ golang , reflect]
image: assets/images/executor/banner.jpeg
tags: featured
---

Mục đích mình tạo ra thư viện này vì các thư viện hiện tại của golang chưa có ai đáp ứng đủ nhu cầu Worker Pool của mình như linh hoạt với cách định nghĩa job chạy, giới hạn số job thực thi trong một khoảng thời gian. Trong quá khứ mình tạo làm đi làm lại đoạn code dựa trên ý tưởng của Worker Pool và biết sự rắc rối mỗi khi hiện thực lại nhưng chưa bao giờ tổng quát hoá để tạo ra một thư viện hoàn chỉnh. Cuối cùng, mình đã ngừng lại và tạo ra Executor.

# Giới thiệu

[Executor](https://github.com/thinhdanggroup/executor) là một thư viện Worker Pool đơn giản với các tính năng:

- Job có hàm thực thi với đa dạng về params truyền vào bằng reflection
- Worker được tạo ra bằng Goroutine
- Một "rate limter" để hỗ trợ các job như crawl data, loadtest,...

# Cách hoạt động

Nguyên lý khá đơn giản:

![grpc-web-model](/assets/images/executor/executor.png)

Executor sẽ đẩy các Job vào một Channel. Channel sẽ làm trung gian để trung chuyển Job cho các Worker và cũng đảm bảo các Worker không quá tải.

Phần thú vị nhất vẫn là làm sao tổng quát hoá các Job. Lúc này, mình bắt đầu tìm hiểu về "reflect" của golang, mình đã thấy ta có thể thực thi một function chỉ bằng *interface* cung cấp, "Call" sẽ làm điều đó. Nhưng còn tham số đầu vào thì sao. Lúc này, *Variadic Functions* phát huy lợi thế của mình. Và cuối cùng, mình chỉ cần validate các thông tin của đầu vào:

```golang
func validateFunc(handler interface{}, nArgs int) (interface{}, error) {
  method := reflect.ValueOf(handler)
	f := reflect.Indirect(method)

  // check type func
	if f.Kind() != reflect.Func {
		return f, fmt.Errorf("%T must be a Function ", f)
	}

	methodType := method.Type()
	numIn := methodType.NumIn()

  // check number of args 
	if nArgs < numIn {
		return nil, errors.New("Call with too few input arguments")
	} else if nArgs > numIn {
		return nil, errors.New("Call with too many input arguments")
	}
	return f, nil
}
```

# Ví dụ

Tham số config

```golang
type Config struct {
	ReqPerSeconds int
	QueueSize     int
	NumWorkers    int
}
```

Executor sẽ sử dụng 3 tham số cơ bản:

- ReqPerSeconds: giới hạn số job trên giây, mặc định là 0, 0 là không giới hạn.
- QueueSize: kích thước buffer của channel.
- NumWorkers: số lượng worker thực thi.

```golang

func main() {
	executor, err := executor.New(executor.DefaultConfig())

	if err != nil {
		logrus.Error(err)
	}

	// close resource before quit
	defer executor.Close()

	for i := 0; i < 3; i++ {
		executor.Publish(mul, i)
		executor.Publish(pow, i)
		executor.Publish(sum, i, i+1)
	}

}

func mul(input int) {
	fmt.Printf("2 * %d = %d \n", input, 2*input)
}

func pow(input int) {
	fmt.Printf("2 ^ %d = %d \n", input, input^2)
}

func sum(a int, b int) {
	fmt.Printf("%d + %d = %d \n", a, b, a+b)
}

// Output:
// 2 * 0 = 0 
// 2 ^ 0 = 2 
// 2 ^ 1 = 3 
// 1 + 2 = 3 
// 2 * 2 = 4 
// 2 ^ 2 = 0 
// 2 + 3 = 5 
// 0 + 1 = 1 
// 2 * 1 = 2

```

Sau khi khởi tạo Executor, hãy nhớ Close resource. Ở trong hàm Close, thư viện sẽ đợi các Job hoàn thành và đóng Channel.

Như bạn đã thấy, ta chỉ việc đưa vào hàm thực thi và tham số, worker sẽ làm phần còn lại cho chúng ta. Quá đơn giản phải không nào!

