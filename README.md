# Kinh doanh sách: nghiên cứu mô phỏng có kiểm chứng

Đồ án Nhập môn Khoa học dữ liệu: xây dựng bộ dữ liệu, xử lý, phân tích khám phá, trực quan hóa và rút ra ý nghĩa trong phạm vi một nhà sách giả định.

**Toàn bộ dữ liệu là mô phỏng.** Tên sách, tác giả, NXB và kênh bán đều giả lập; không phải dữ liệu hoặc thị phần của Việt Nam. Các tham số là giả định thiết kế, chưa được hiệu chỉnh theo dữ liệu doanh nghiệp. Mục tiêu thực hành là xây dựng quy trình tin cậy và biết giới hạn suy luận.

## Bắt đầu đọc

- [Báo cáo PDF](report/bao_cao.pdf), [báo cáo HTML](report/bao_cao.html), [bản Markdown có thể sửa](report/bao_cao.md).
- [Dashboard ngoại tuyến](charts/dashboard.html): tải về và mở bằng trình duyệt; bộ lọc năm/kênh cập nhật mọi KPI. GitHub không chạy HTML tương tác trực tiếp trong trang xem mã.
- [Notebook đã chạy](notebooks/book_sales_analysis.ipynb).
- [Quy trình nghiên cứu](docs/QUY-TRINH.md), [từ điển dữ liệu](data/data_dictionary.md), [đối soát bản cũ](docs/DOI-SOAT-BAN-CU.md).
- [Việc nhóm cần hoàn thiện](docs/PHAN-VIEC-NHOM.md), [nhật ký thay đổi](CHANGELOG.md).

## Câu hỏi và quy mô

7 câu hỏi EDA về thể loại, mã sách, thời gian, giá/giảm giá, điểm sách, tương quan và cơ cấu kênh/phân khúc. Thêm hai câu hỏi kiểm chứng: phục hồi lỗi đúng đến đâu và kết quả phụ thuộc giả định thế nào?

Kịch bản cơ sở: 300 sách, 10 thể loại, 5 kênh, 6.500 đơn một đầu sách trong 2024–2025. Mỗi đơn có một dòng; đây là giới hạn mô hình, không phải mô tả chung về đơn bán lẻ. Sau thêm bản sao: 6.660 dòng thô. Quy trình giữ 6.478 dòng, ghi nhận 301 mã sách (300 mã danh mục chuẩn + mã ngoài danh mục BK9999, ứng với 306 đầu sách theo cặp mã–tên), cách ly 22 mã nghiệp vụ (27 biến thể nguồn). Các số mới không so trực tiếp với bản cũ vì cơ chế dữ liệu đã được thiết kế lại.

**Kết quả chính về phương pháp:** đối chiếu tám trường trên các dòng giữ lại cho thấy 3 trường danh mục khớp 100%, 5 trường giao dịch khớp từ 99,75% đến 99,98% do một số lỗi giá trị lọt lưới; tổng giá trị bán hàng toàn kỳ chênh lệch +2,992% (+89.125.000 đồng) so với dữ liệu chuẩn do lỗi giá trị còn sót (+99.657.000 đồng) chiếm ưu thế so với phần doanh thu mất do cách ly (10.532.000 đồng). Kết quả này không được gọi là “sạch 100%”. Giá trị cụ thể, phần trăm sai lệch và tổng EDA được sinh tự động trong `results/metrics.json` và báo cáo, tránh chép số thủ công.

## Chạy lại (Windows / macOS / Linux)

Đã kiểm thử với Python 3.12. Mở terminal tại thư mục chứa README này:

```text
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.venv\Scripts\python.exe run.py --replications 50
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe tools/execute_notebook.py
.venv\Scripts\python.exe -m notebook notebooks/book_sales_analysis.ipynb
```

macOS / Linux:

```bash
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python run.py --replications 50
.venv/bin/python -m pytest -q
.venv/bin/python tools/execute_notebook.py
.venv/bin/python -m notebook notebooks/book_sales_analysis.ipynb
```

`requirements-lock.txt` ghi môi trường Windows đã thử; `requirements.txt` liệt kê phụ thuộc trực tiếp đa nền tảng. Chưa xác nhận chạy thực tế trên macOS/Linux. Pipeline mặc định ghi lại dữ liệu và báo cáo sinh tự động. Nếu muốn bảo toàn một bản xuất, dùng `python run.py --out path/to/new-output --replications 50`. Không sửa trực tiếp báo cáo rồi chạy lại: nội dung báo cáo được quản lý tại `src/report_builder.py`.

Có thể tăng `--replications` lên 200 để cải thiện độ chính xác Monte Carlo; bài bàn giao đã chạy 50 lần/kịch bản, không tuyên bố kết quả 200 lần. Cùng seed và cùng môi trường cho cùng dữ liệu; thời điểm/tên hệ thống trong thông tin kiểm tra có thể khác.

## Luồng dữ liệu

```text
config → catalog + ground_truth → raw + nhãn lỗi
                    catalog + raw → clean + nhật ký + cách ly
           clean → bảng kết quả → biểu đồ / dashboard / báo cáo
ground_truth + nhãn lỗi + clean → đối soát (chỉ ở giai đoạn đánh giá)
```

`clean()` không nhận hoặc đọc ground_truth/nhãn lỗi. Chỉ danh mục giả định đáng tin được cung cấp cho bước khôi phục. Cần hiểu đây là giả định thuận lợi, không phải bằng chứng phục hồi hoàn hảo dữ liệu thật.

## Thư mục

| Đường dẫn | Vai trò |
|---|---|
| `data/reference/` | Danh mục đầu vào và dữ liệu chuẩn chỉ dùng đánh giá |
| `data/raw/` | Dữ liệu sau cài lỗi, chưa làm sạch |
| `data/processed/` | CSV phân tích chuẩn duy nhất |
| `data/audit/` | Nhãn lỗi, thay đổi ô, trạng thái từng dòng và cách ly |
| `src/` | Mã dùng chung cho pipeline và notebook |
| `results/` | Bảng kết quả, 150 lượt mô phỏng, metrics, hash |
| `charts/` | 8 PNG và dashboard HTML tự chứa |
| `report/` | Báo cáo PDF/HTML/Markdown từ cùng nội dung |
| `tests/` | Kiểm tra các rủi ro dữ liệu cụ thể |
| `docs/` | Phương pháp, nguồn, đối soát, kiểm tra, phần việc nhóm |

CSV là dữ liệu chuẩn; bỏ bản Excel cũ khỏi bộ mới để tránh giữ thêm bản có nguy cơ lệch. Có thể mở CSV UTF-8 trong Excel nhưng không coi một workbook chỉnh thủ công là dữ liệu đầu vào pipeline.


