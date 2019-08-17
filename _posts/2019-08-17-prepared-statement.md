---
layout: post
title:  "Prepared Statement Deep Dive"
author: ThinhDA
categories: [ statement, database ]
image: assets/images/client-db.jpg
tags: [Prepared Statement]
---

Để tối ưu hiệu năng của hệ thống, có rất nhiều cách để thực hiện nhưng hiệu quả nhất vẫn là tối ưu các câu truy vấn database. Một trong số này đó là sử dụng prepared statement để truy vấn. 

## 1. Prepared Statement là gì

Prepared statement là một tính năng được sử dụng để thực hiện lặp lại các câu lệnh SQL tương tự nhau với hiệu quả cao.

Đối với prepared statement, quá trình hoạt động sẽ diễn ra như sau:

![psmt](https://cdn.hyvor.com/uploads/developer/prepared-stmt.png)

1. **Prepare**: đầu tiên, ứng dụng tạo ra 1 statement template và gửi nó cho DBMS. Các giá trị không được chỉ ra và được gọi là parameters (dấu ? bên dưới)
    SELECT * FROM accounts WHERE id = ?;
1. Sau đó, DBMS compile (parse, optimizes và translates) statement template, store kết quả mà không thực thi.
1. **Execute**: ứng dụng gửi giá trị của parametes của statement template và DBMS thực thi nó. Ứng dụng có thể thực thi statement nhiều lần với nhiều giá trị khác nhau.

So với gửi statement trực tiếp thì prepared statement có lợi là:

- Overhead của compile statement diễn ra 1 lần còn statement được thực thi nhiều lần. Về lý thuyết, khi sử dụng prepared statement, ta sẽ tiết kiệm được: `cost_of_prepare_preprocessing * (#statement_executions - 1)`. Nhưng thực tế, tuỳ từng loại query sẽ có cách optimize khác nhau([chi tiết](http://s.petrunia.net/blog/?p=16)).
- Chống SQL injection.
- Phát hiện sớm các lỗi syntax.
- Có thể cache prepared statement và sử dụng lại sau này.

Tuy nhiên, prepared statement vẫn có những lưu ý khi sử dụng để tránh mang lại tác dụng ngược:

- Không nên sử dụng cho những so sánh không phải hằng số. Ví dụ

    ```md
    FIRST_NAME LIKE “Jon%”
    AMOUNT > 19.95
    ```
    
- Prepared statement sẽ trao dồi hiệu năng tốt hơn nếu bạn sử dụng lại cùng một statement như ví dụ bên dưới. Ta chỉ cần chuẩn bị câu statement một lần, các lần sau chỉ cần gửi các biến nên giảm thiểu được lượng dữ liệu gửi qua network.
    
    ```java
    PreparedStatement ps = connection.prepare("SOME SQL");

    for (Data data : dataList) {
      ps.setInt(1, data.getId());
      ps.setString(2, data.getValue();
      ps.executeUpdate();
    }

    ps.close();
    ```

- Nhưng nếu, ta chuẩn bị statement một lần và thực thi nó một lần và đóng kết  nối. Lúc này, có tới ba lần round-trip tới server, nó sẽ làm giảm hiệu năng.

## 2. Sử dụng prepared statement

Ví dụ [simple về SQL statement](https://dev.mysql.com/doc/refman/5.7/en/sql-syntax-prepared-statements.html):

```sh
mysql> PREPARE stmt1 FROM 'SELECT SQRT(POW(?,2) + POW(?,2)) AS hypotenuse';
mysql> SET @a = 3;
mysql> SET @b = 4;
mysql> EXECUTE stmt1 USING @a, @b;
+------------+
| hypotenuse |
+------------+
|          5 |
+------------+
mysql> DEALLOCATE PREPARE stmt1;
```

Từ ví dụ trên ta thấy là database đã lưu lại statement nên các lần query với statement trên chỉ cần truyền lại params. Việc parse đã diễn ra ở phía server chứ không phải ở phía client.

## 3. Kết luận

Những lợi ích mang lại từ prepared statement là không thể phủ nhận. Nó giúp giảm tải cho database bằng cách sử dụng lại các statement đã chuẩn bị sẵn. Sử dụng prepared statement cũng là tận dụng cơ chế cache của database để tăng hiệu suất cho ứng dụng. Hãy luôn sử dụng prepared statement thay vì một câu truy vấn bình thường.