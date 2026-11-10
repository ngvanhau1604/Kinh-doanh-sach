# Tiến độ thực hiện tự chủ

Cập nhật: 2026-11-10. Ghi lại để công việc tiếp tục được nếu phiên bị gián đoạn vì ngữ cảnh hoặc hạn mức.

## Trạng thái Git

- `main` @ `97624e3` — PR1 đã squash merge.
- `feat/simulation-design` @ `832a835` — PR2, đã push, **Draft PR #2** đang mở.
- Nhánh làm việc tiếp theo: `feat/analysis-visualization` (PR3), tách từ `832a835`.

## PR1 — đã merge

Squash merge `97624e3`. CI 12/12 xanh trên commit cuối (`0772ed6`), 6 job × 2 sự kiện.

Hai lỗi hạ tầng phát hiện trong lần chạy CI đầu và đã sửa:

1. `.ci-out/` không được gitignore, làm bước "working tree clean" thất bại trên mọi nền tảng.
2. `--check` so sánh byte tuyệt đối, trong khi PNG nhúng do matplotlib/freetype cục bộ render → khác byte giữa Linux và Windows. Nay so sánh cấu trúc, source, execution count và văn bản output; byte của hình không so sánh.

Giới hạn tái lập cần nêu trong báo cáo: **văn bản và cấu trúc tái lập chính xác; hình ảnh tái lập theo nội dung, không theo byte.**

## PR2 — Draft PR #2, đã xong phần mã

Kết quả đo được (seed 42, 6500 dòng):

| Chỉ tiêu | Trước | Sau |
|---|---|---|
| Recall gộp | 1,000 | 0,469 |
| Precision cách ly | 1,000 | 1,000 |
| Dòng còn sai trong tập sạch | 0 | 32/49 |
| Sai lệch doanh thu so với chuẩn | 0% | +2,99% |
| F-04 (r cấp sách) | "nằm trong khoảng null" | **ngoài khoảng null** |

Chi tiết theo họ lỗi: `qty_negative` 100%, `qty_fractional` 100%, `catalog_missing` 100% (đánh dấu, không cách ly), `price_swap` 40%, `date_swap` 37,5%, `qty_scale` 25%, `price_reset` 0%, `genre_mislabel` 0%.

**F-04:** 200 seed, trung bình 0,000, sd 0,058, khoảng 95% [−0,112; 0,112]. Giá trị quan sát 0,105 ở phân vị 96,5 → ngoài khoảng. Kết luận cũ (12 seed) sai vì khoảng quá hẹp.

**Độ bao phủ danh mục:** ở 50% bao phủ, doanh thu giữ lại còn 48,2% và lệch −50,5%. Đây là giả định điều kiện của toàn bộ kết quả, không phải chi tiết kỹ thuật.

Kiểm thử: **42 passed**; `run.py --replications 50 --null-seeds 200 --missing-seeds 100` chạy xong; notebook `--check` pass.

## PR3 — bước tiếp theo

Phạm vi dự kiến:

1. Bootstrap khoảng tin cậy cho các chỉ tiêu chính (doanh thu, tương quan, tỷ trọng quý IV) — phân biệt rõ với khoảng null và với phân vị Monte Carlo.
2. Hình phân phối null đã có (Hình 7); cần thêm hình khoảng bootstrap và hình so sánh ba loại khoảng để người đọc không nhầm chúng với nhau.
3. Rà soát chú thích: mọi bảng/hình phải có n, đơn vị và nguồn.
4. Kiểm tra diễn giải: mọi câu khẳng định trong báo cáo phải truy được về `results/*.csv` hoặc `metrics.json`.

## PR4 — sau PR3

Viết lại báo cáo học thuật, trích dẫn APA, tham chiếu bảng/hình, placeholder bìa (nhóm, trường, giảng viên — giữ trống, không bịa).

## Việc bắt buộc con người làm

- Điền thông tin nhóm, trường, giảng viên, mã học phần trên bìa.
- Quyết định có merge PR2–PR4 hay không.
- Đọc lại phần thảo luận để xác nhận giọng văn phù hợp yêu cầu học phần.
