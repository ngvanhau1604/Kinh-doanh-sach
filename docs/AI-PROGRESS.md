# Tiến độ thực hiện tự chủ

Cập nhật: 2026-11-10. Ghi lại để công việc tiếp tục được nếu phiên bị gián đoạn vì ngữ cảnh hoặc hạn mức.

## Trạng thái Git

- `main` @ `97624e3` — PR1 đã squash merge.
- `feat/simulation-design` @ `832a835` — PR2, đã push, **Draft PR #2** đang mở.
- `feat/analysis-visualization` — PR3, đã push, **Draft PR #3** đang mở, base là `feat/simulation-design` (stacked).
- Nhánh làm việc tiếp theo: `feat/academic-report` (PR4), tách từ nhánh PR3.

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

## PR3 — Draft PR #3, đã xong phần mã

Nội dung: khoảng bootstrap, hình so sánh ba loại khoảng, và **sửa lại kết luận F-04**.

### F-04 phải sửa lần thứ hai

PR2 kết luận giá trị quan sát nằm ngoài khoảng null. Kết luận đó sai, và sai vì một lỗi đơn vị:
`summarize` gộp sách theo `(ma_sach, ten_sach)` còn `null_band` gộp chỉ theo `ma_sach`. Các dòng
không tra được mã sách mang khóa thay thế `BK9999`, nên cách gộp thứ hai nhập sáu sách khác nhau
thành một và cộng dồn lượng của chúng. Giá trị quan sát và khoảng đem so được tính trên hai đơn vị
khác nhau.

Khi cả hai bên dùng cùng một cách gộp, qua 200 seed:

- trung bình 0,000; độ lệch chuẩn 0,058; khoảng 95% **[−0,112; 0,107]**
- giá trị quan sát **0,105456**, phân vị thứ 96,5
- **nằm trong khoảng**

Kết luận đúng: giá trị này tương thích với nhiễu của chính mô hình, không được trình bày như một
phát hiện. Báo cáo vẫn ghi kèm phân vị vì 96,5 nằm ở đuôi của khoảng trung tâm 95%, và gộp thành
một kết luận nhị phân sẽ che mất chi tiết đó.

Phán quyết nay do `_inside_band` / `_band_verdict` tính, không viết tay trong văn bản. Bản viết tay
đã lệch khỏi số liệu hai lần; có test chặn nếu lệch lại.

### Khoảng bootstrap

`bootstrap()` rút lại 2.000 lần, ghi `results/bootstrap_ci.csv`. Đơn vị rút lại khác nhau theo chỉ
tiêu: chỉ tiêu cấp dòng rút theo dòng, riêng tương quan điểm–lượng cấp sách rút theo đầu sách. Có
khoảng 300 sách so với khoảng 6.500 dòng, nên hai cách rút cho hai độ rộng rất khác nhau; một test
chặn điều này.

Báo cáo tách ba loại khoảng: bootstrap (độ chính xác của ước lượng), khoảng null (giá trị có thể do
chính mô hình sinh ra không), và độ tản giữa các kịch bản (kết quả đổi thế nào khi thay giả định).
Không loại nào là khoảng tin cậy thị trường.

### Kiểm thử

**48 passed**; `run.py` chạy xong; notebook `--check` pass, 18 code cells.

## PR4 — bước tiếp theo

Viết lại báo cáo học thuật, trích dẫn APA, tham chiếu bảng/hình, placeholder bìa (nhóm, trường,
giảng viên — giữ trống, không bịa). Sau đó tạo `docs/FINAL-REVIEW.md` bảy mục.

## Việc bắt buộc con người làm

- Điền thông tin nhóm, trường, giảng viên, mã học phần trên bìa.
- Quyết định có merge PR2–PR4 hay không.
- Đọc lại phần thảo luận để xác nhận giọng văn phù hợp yêu cầu học phần.
