# Kết quả kiểm tra bản bàn giao

Ngày kiểm tra: 08/11/2026. Đây là kiểm tra cục bộ bằng công cụ và trình duyệt, không phải xác nhận của giảng viên hoặc phản biện độc lập.

| Nội dung | Kết quả đã quan sát |
|---|---|
| Môi trường mới | Tạo môi trường Python 3.12 riêng, cài thư viện; `pip check` không phát hiện phụ thuộc hỏng. Phiên bản trong requirements-lock.txt. |
| Bộ kiểm tra dữ liệu | 18 kiểm tra qua; gồm biên giá/điểm, tiền tệ, xung đột khóa, nguồn thiếu catalog, dòng mua nhiều, miền giá trị, tái lập và tổng theo nhóm. |
| Pipeline đầy đủ | Đã chạy sinh dữ liệu → làm sạch → bảng → 150 lượt mô phỏng → 8 hình → dashboard → báo cáo. |
| Kịch bản cơ sở | 6.500 mã dòng chuẩn, 6.660 dòng thô, 6.478 dòng sạch; 27 biến thể bị cách ly tương ứng 22 mã nghiệp vụ. |
| Khớp giá trị | 3 trường danh mục khớp 100%, 5 trường giao dịch khớp 99,75%–99,98%; tổng kỳ chênh lệch +2,992% so với truth do lỗi còn sót (+99.657.000 đ) và cách ly (10.532.000 đ). |
| Nhật ký dòng | Mỗi trong 6.660 raw_row_id có đúng một trạng thái cuối. |
| Mô phỏng lặp | 3 kịch bản × 50 seed (100–149); có kết quả từng lượt và SD/MCSE/phân vị. |
| Notebook | Chạy kernel mới, 15 ô mã hoàn thành; dữ liệu sạch và KPI khớp pipeline, không lỗi thực thi. |
| Dashboard | Kiểm tra bằng Edge headless, tắt mạng; 18 tổ hợp năm/kênh đối soát đúng giá trị và số dòng với tổng hợp độc lập bằng Python. Không lỗi JavaScript. |
| Màn hình nhỏ | 390×844; sau sửa không tràn ngang trang. Đã xem ảnh desktop và mobile. |
| Báo cáo HTML | Tám ảnh tải thành công từ đường dẫn tương đối khi ngoại tuyến. |
| PDF bản ban đầu | 16 trang; render từng trang và xem bố cục; không có khối nội dung vượt biên kiểm tra. Dấu tiếng Việt, hình, bảng và số trang hiển thị. |
| Kiểm tra toàn vẹn | Các tệp trong results/manifest.json khớp SHA-256 sau notebook cuối. |
| Chạy lại độc lập | Chạy từ thư mục khác, xuất sang thư mục khác: raw/clean/truth trùng SHA-256; 6 lượt đầu (2 seed × 3 kịch bản) khớp kết quả trong bản 150 lượt. |
| Repository gốc | Trước khi cập nhật, bản sao commit 6bfe691904b4d721ee1a1743509f6b581b70ce81 giữ sạch; commit này được giữ trong lịch sử để đối chiếu. |

Hai lỗi giao diện đã được phát hiện và sửa trong quá trình kiểm tra: mục năm 2024 thiếu thẻ option; vùng biểu đồ bị tràn khi đổi sang kích thước điện thoại. Một lỗi xử lý danh mục rỗng được bộ kiểm tra phát hiện và sửa trước khi hoàn tất. Đây là lý do kiểm tra thực thi quan trọng hơn chỉ đọc mã.

## Giới hạn kiểm tra

- Đã chạy trên Windows, chưa thực thi trên Linux/macOS hoặc mọi phiên bản trình duyệt.
- Kết quả phục hồi tốt phụ thuộc loại lỗi cài và giả định catalog đáng tin; không chứng minh hiệu năng trên dữ liệu nhà sách thực.
- Chưa kiểm thử nguồn dữ liệu bên ngoài hoặc trường hợp có hàng triệu dòng.
- Không có thông tin học phần/thành viên đầy đủ để làm bìa chính thức; nhóm cần bổ sung và hiểu nội dung trước khi nộp.
- Không có xác nhận về yêu cầu số trang, mẫu bìa hoặc chính sách AI của lớp. Không tự coi kết quả kiểm tra này là phê duyệt nộp bài.

## Cập nhật báo cáo học thuật ngày 08/11/2026

Bản PDF mới có 19 trang, sáu chương, mục lục có số trang, tám hình, năm bảng, tài liệu tham khảo và phụ lục. Đã tái tạo từ bảng kết quả hiện có, render và xem bố cục toàn bộ trang, chỉnh vị trí chú thích bảng, kiểm tra hash trong manifest. Nguồn dữ liệu và KPI được giữ nguyên. Lượt cập nhật này kiểm tra báo cáo, không chạy lại toàn bộ thí nghiệm hoặc notebook. Bìa dùng tên học phần và đề tài, còn thiếu thông tin nhóm, lớp và giảng viên.

Chạy `python tools/refresh_report.py` để tạo lại riêng báo cáo từ dữ liệu và kết quả đã lưu.
