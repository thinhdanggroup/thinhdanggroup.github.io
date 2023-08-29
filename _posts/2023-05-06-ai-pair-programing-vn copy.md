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
  overlay_image: /assets/images/copilot/copilot.jpeg
  overlay_filter: 0.5 
  teaser: /assets/images/copilot/copilot.jpeg
title:  "GitHub Copilot: Đánh giá và Hướng dẫn cho Người mới bắt đầu"
tags: 
- github copilot
---

Bạn đã bao giờ muốn có một đối tác thông minh và hữu ích có thể giúp bạn với việc lập trình? Một người có thể gợi ý đoạn mã, hàm hoặc giải pháp dựa trên ngữ cảnh của mã của bạn? Một người có thể giúp bạn học những kỹ năng, quan điểm và phương pháp mới từ những đoạn mã mà họ đề xuất? Một người có thể làm cho việc lập trình trở nên nhanh hơn và dễ dàng hơn cho bạn?

Nếu bạn trả lời "có" cho bất kỳ câu hỏi nào trong số này, thì bạn có thể quan tâm đến GitHub Copilot, một trình lập trình cùng AI có thể làm tất cả những việc đó và nhiều hơn nữa. Trong bài đăng trên blog này, tôi sẽ chia sẻ với bạn trải nghiệm của mình trong việc sử dụng GitHub Copilot trong vài tháng qua và đưa ra một số mẹo và thủ thuật về cách sử dụng nó một cách hiệu quả.

## GitHub Copilot là gì?

GitHub Copilot cung cấp các gợi ý mã từ hệ thống trí tuệ nhân tạo khi bạn nhập. Nó sử dụng OpenAI Codex, một mô hình học máy chuyển đổi ngôn ngữ tự nhiên thành mã, để tạo ra những gợi ý liên quan dựa trên ngữ cảnh và ý định của mã của bạn. Nó có thể gợi ý cả dòng mã hoặc toàn bộ hàm cho các ngôn ngữ và khung công việc khác nhau, như Python, JavaScript, TypeScript, Ruby và Go.

GitHub Copilot không phải là một công cụ ma thuật có thể viết code thay bạn. Nó không hoàn hảo và không đảm bảo tính chính xác, chất lượng hoặc bảo mật của mã mà nó gợi ý. Bạn vẫn cần xem xét và chỉnh sửa các gợi ý trước khi chấp nhận chúng và kiểm tra tính chức năng và hiệu suất của chúng. Bạn cũng cần kiểm tra nguồn và giấy phép của các gợi ý, đặc biệt là nếu bạn đang làm việc trên dự án thương mại hoặc mã nguồn mở.

GitHub Copilot là một công cụ mạnh mẽ có thể giúp bạn viết mã nhanh hơn và với ít công sức hơn. Nó cũng có thể giúp bạn học những kỹ năng, quan điểm và phương pháp mới từ những đoạn mã mà nó gợi ý. Bạn có thể sử dụng GitHub Copilot để khám phá các giải pháp khác nhau, khám phá các thư viện hoặc khung công việc mới, hoặc lấy cảm hứng từ các phong cách hoặc kỹ thuật lập trình khác nhau. Bạn cũng có thể đặt câu hỏi hoặc thách thức GitHub Copilot trong các comment của bạn và xem nó phản hồi như thế nào.

### Cách bắt đầu sử dụng GitHub Copilot?

![copilot-b](../assets/images/copilot/copilot-blog-hero.webp)

Trước khi bạn có thể bắt đầu sử dụng GitHub Copilot, bạn cần cài đặt tiện ích mở rộng trong Visual Studio Code. Bạn có thể tìm thấy nó trên Trung tâm mở rộng Visual Studio Code hoặc tìm kiếm nó trong tab Extensions trong Visual Studio Code.

Bạn cũng cần đăng nhập vào GitHub Copilot bằng tài khoản GitHub của bạn. Bạn sẽ cần đăng ký dùng GitHub Copilot hoặc dùng phiên dùng thử miễn phí để sử dụng nó. Bạn có thể đăng ký GitHub Copilot trên trang web của GitHub hoặc trong cài đặt Visual Studio Code.

GitHub Copilot miễn phí cho sinh viên, giáo viên và những người duy trì dự án mã nguồn mở phổ biến. Nếu bạn không phải là sinh viên, giáo viên hoặc người duy trì dự án mã nguồn mở phổ biến, bạn có thể thử GitHub Copilot miễn phí với phiên dùng thử một lần trong vòng 30 ngày. Sau phiên dùng thử miễn phí, bạn sẽ cần có một đăng ký trả phí để tiếp tục sử dụng. Để biết thêm thông tin về giá cả và thanh toán cho GitHub Copilot, [xem trang này](https://github.com/features/copilot#pricing).

Sau khi bạn đã cài đặt tiện ích mở rộng và đăng nhập vào GitHub Copilot bằng phiên dùng thử hoặc đăng ký của bạn, bạn có thể bắt đầu viết mã trong một tập tin như thông thường. Bạn có thể sử dụng bất kỳ ngôn ngữ hoặc khung công việc nào mà GitHub Copilot hỗ trợ. Khi bạn gõ, bạn sẽ thấy một ô gợi ý với viền màu xanh và biểu tượng Copilot ở góc dưới bên phải.

Để kích hoạt cácgợi ý của GitHub Copilot, nhấn `Ctrl+Shift+Space` hoặc `Cmd+Shift+Space` (trên Mac). Để xem lại gợi ý và chấp nhận bằng cách nhấn Tab hoặc Enter, hoặc từ chối bằng cách nhấn Esc. Bạn cũng có thể duyệt qua các gợi ý khác nhau bằng cách nhấn `Ctrl+.` hoặc `Cmd+.` (trên Mac).

Bạn có thể chỉnh sửa gợi ý theo cần thiết. Bạn cũng có thể thêm nhận xét hoặc chuỗi tài liệu để cung cấp thêm ngữ cảnh cho GitHub Copilot để tạo ra các gợi ý tốt hơn.

### Cách sử dụng GitHub Copilot hiệu quả?

GitHub Copilot là một công cụ mạnh mẽ có thể giúp bạn viết mã nhanh hơn và với ít công việc hơn. Nhưng giống như bất kỳ công cụ nào khác, bạn cần biết cách sử dụng nó một cách hiệu quả. Đây là một số gợi ý về cách sử dụng GitHub Copilot hiệu quả:

- Viết nhận xét rõ ràng và mô tả. GitHub Copilot sử dụng nhận xét của bạn để hiểu ngữ cảnh và ý định của mã của bạn, và tạo ra các gợi ý phù hợp. Càng cụ thể và thông tin hơn nhận xét của bạn, GitHub Copilot càng có thể giúp bạn tốt hơn.
- Xem xét và chỉnh sửa các gợi ý. GitHub Copilot không hoàn hảo, và nó không thể đảm bảo tính chính xác, chất lượng hoặc bảo mật của mã mà nó gợi ý. Bạn nên luôn xem xét và chỉnh sửa các gợi ý trước khi chấp nhận chúng, và kiểm tra chúng về chức năng và hiệu suất. Bạn cũng nên kiểm tra nguồn và giấy phép của các gợi ý, đặc biệt nếu bạn đang làm việc trên một dự án thương mại hoặc mã nguồn mở.
- Sử dụng GitHub Copilot như một công cụ học tập. GitHub Copilot có thể giúp bạn học những kỹ năng, quan điểm và phương pháp mới từ mã mà nó gợi ý. Bạn có thể sử dụng GitHub Copilot để khám phá các giải pháp khác nhau, khám phá các thư viện hoặc khung công việc mới, hoặc lấy cảm hứng từ các phong cách hoặặc kỹ thuật lập trình khác nhau. Bạn cũng có thể đặt câu hỏi hoặc thách thức GitHub Copilot trong nhận xét của bạn và xem nó phản ứng ra sao.

- Thử nghiệm với các cài đặt và tùy chọn khác nhau. GitHub Copilot có nhiều cài đặt và tùy chọn mà bạn có thể tùy chỉnh để phù hợp với nhu cầu và sở thích của bạn. Bạn có thể thay đổi tần suất, độ dài và kiểu gợi ý, cũng như phím tắt và lệnh để kích hoạt chúng. Bạn cũng có thể bật hoặc tắt các tính năng cụ thể, chẳng hạn như gợi ý đa dòng, gợi ý chuỗi tài liệu hoặc gợi ý dịch mã. Bạn có thể tìm thấy các cài đặt này trong cài đặt Visual Studio Code hoặc trong trang cài đặt GitHub Copilot của bạn.

- Cung cấp phản hồi và báo cáo vấn đề. GitHub Copilot vẫn là một sản phẩm mới và đang phát triển, và nó phụ thuộc vào phản hồi và đóng góp của bạn để cải thiện. Bạn có thể cung cấp phản hồi hoặc báo cáo vấn đề bằng cách nhấp vào biểu tượng mặt cười ở góc dưới bên phải của hộp gợi ý, hoặc bằng cách sử dụng bảng lệnh trong Visual Studio Code. Bạn cũng có thể tham gia diễn đàn cộng đồng GitHub Copilot để chia sẻ kinh nghiệm, ý tưởng hoặc câu hỏi của bạn với các người dùng khác.

## Kinh nghiệm của tôi khi sử dụng GitHub Copilot

Tôi đã sử dụng GitHub Copilot trong vài tháng qua và phải nói rằng tôi ấn tượng với khả năng và tiềm năng của nó. Tôi đã sử dụng nó cho các dự án và nhiệm vụ khác nhau, chẳng hạn như viết bài blog (như bài viết này), tạo ứng dụng web, xây dựng đường ống dữ liệu và giải quyết các thách thức lập trình.

GitHub Copilot đã giúp tôi viết mã nhanh hơn và với ít công việc hơn. Nó đã tiết kiệm thời gian và công sức cho tôi bằng cách gợi ý đoạnmã, các hàm hoặc giải pháp mà tôi khác phải tự viết hoặc tra cứu trực tuyến. Nó cũng giúp tôi tránh việc gõ sai chính tả, lỗi và lỗi trước khi chúng gây ra vấn đề.

GitHub Copilot cũng giúp tôi học được những kỹ năng, quan điểm và phương pháp mới từ mã mà nó gợi ý. Nó đã giới thiệu cho tôi các kiểu mã, kỹ thuật và quy ước tốt hơn mà tôi có thể áp dụng vào các dự án của mình. Nó cũng giới thiệu cho tôi các thư viện hoặc framework mới mà tôi có thể sử dụng để nâng cao mã của mình. Nó cũng thách thức tôi nghĩ về các cách khác nhau để giải quyết vấn đề bằng cách đặt câu hỏi hoặc đưa ra các phương án khác.

GitHub Copilot không hoàn hảo và nó có một số hạn chế và thách thức. Đôi khi nó gợi ý mã không chính xác, không liên quan hoặc không an toàn. Đôi khi nó không hiểu ý kiến hoặc mục đích của tôi. Đôi khi nó không hỗ trợ ngôn ngữ hoặc framework mà tôi muốn sử dụng. Đôi khi nó không đưa ra bất kỳ gợi ý nào.

Nhưng những vấn đề này nhỏ hơn so với những lợi ích mà GitHub Copilot mang lại. Tôi luôn xem xét và chỉnh sửa các gợi ý trước khi chấp nhận chúng và kiểm tra chúng để đảm bảo tính chức năng và hiệu suất. Tôi cũng kiểm tra nguồn và giấy phép của các gợi ý, đặc biệt là khi tôi làm việc trên dự án thương mại hoặc mã nguồn mở. Tôi cũng cung cấp phản hồi và báo cáo vấn đề để giúp GitHub Copilot cải thiện.

## Kết luận

GitHub Copilot là một công cụ lập trình cặp AI có thể giúp bạn viết mã nhanh hơn và với ít công việc hơn. Nó cũng giúp bạn học được những kỹ năng, quan điểm và phương pháp mới từ mã mà nó gợi ý. Bạn có thể sử dụng GitHub Copilot bằng cách cài đặt tiện mở rộng vào Visual Studio Code, đăng nhập bằng tài khoản GitHub của bạn và kích hoạt các gợi ý khi bạn gõ code.

GitHub Copilot không hoàn hảo và nó không thể đảm bảo tính chính xác, chất lượng hoặc bảo mật của mã mà nó gợi ý. Bạn vẫn cần xem xét và chỉnh sửa các gợi ý trước khi chấp nhận chúng, và kiểm tra tính chức năng và hiệu suất của chúng. Bạn cũng cần kiểm tra nguồn và giấy phép của các gợi ý, đặc biệt là khi bạn làm việc trên dự án thương mại hoặc mã nguồn mở.

GitHub Copilot là một công cụ mạnh mẽ có thể giúp bạn viết code nhanh hơn và với ít công việc hơn. Nhưng giống như bất kỳ công cụ nào khác, bạn cần biết cách sử dụng nó một cách hiệu quả. Hy vọng bài viết này đã giúp bạn có một số mẹo và thủ thuật về cách sử dụng GitHub Copilot hiệu quả.

Nếu bạn quan tâm muốn thử GitHub Copilot, bạn có thể đăng ký dùng thử miễn phí hoặc đăng ký gói trả phí trên trang web của GitHub. Bạn cũng có thể tham gia diễn đàn cộng đồng GitHub Copilot để chia sẻ kinh nghiệm, ý tưởng hoặc câu hỏi với người dùng khác.

Cảm ơn bạn đã đọc bài viết này. Hy vọng bạn đã thấy thú vị và học được điều gì đó từ đó. Nếu có, hãy chia sẻ với bạn bè và đồng nghiệp của bạn có thể quan tâm đến GitHub Copilot. Bạn cũng có thể để lại một comment dưới đây để cho tôi biết ý kiến của bạn về GitHub Copilot, hoặc nếu bạn có bất kỳ câu hỏi hoặc phản hồi nào dành cho tôi.