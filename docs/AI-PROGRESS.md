# Tiến độ thực hiện tự chủ

Cập nhật: 2026-11-10. Ghi lại để công việc tiếp tục được nếu phiên bị gián đoạn vì ngữ cảnh hoặc hạn mức.

## Trạng thái Git

- `main` @ `97624e3` — PR1 đã squash merge.
- `feat/simulation-design` @ `832a835` — PR2, **Draft PR #2**, base `main`.
- `feat/analysis-visualization` @ `d5c9718` — PR3, **Draft PR #3**, base `feat/simulation-design` (stacked).
- `feat/academic-report` @ `24759b1` — PR4, **Draft PR #4**, base `feat/analysis-visualization` (stacked).

Thứ tự merge: **PR2 → PR3 → PR4**. Không PR nào được tự merge.

## PR1 — đã merge

Squash merge `97624e3`. CI 12/12 xanh trên commit cuối (`0772ed6`), 6 job × 2 sự kiện.

Hai lỗi hạ tầng phát hiện trong lần chạy CI đầu và đã sửa:

1. `.ci-out/` không được gitignore, làm bước "working tree clean" thất bại trên mọi nền tảng.
2. `--check` so sánh byte tuyệt đối, trong khi PNG nhúng do matplotlib/freetype cục bộ render → khác byte giữa Linux và Windows. Nay so sánh cấu trúc, source, execution count và văn bản output; byte của hình không so sánh.

Giới hạn tái lập cần nêu trong báo cáo: **văn bản và cấu trúc tái lập chính xác; hình ảnh tái lập theo nội dung, không theo byte.**

## PR2 — Draft PR #2, xong phần mã

Kết quả đo được (seed 42, 6500 dòng):

| Chỉ tiêu | Trước | Sau |
|---|---|---|
| Recall gộp | 1,000 | 0,469 |
| Precision cách ly | 1,000 | 1,000 |
| Dòng còn sai trong tập sạch | 0 | 32/49 |
| Sai lệch doanh thu so với chuẩn | 0% | +2,992% |

Chi tiết theo họ lỗi: `qty_negative` 100%, `qty_fractional` 100%, `catalog_missing` 100% (đánh dấu, không cách ly), `price_swap` 40%, `date_swap` 37,5%, `qty_scale` 25%, `price_reset` 0%, `genre_mislabel` 0%.

**Độ bao phủ danh mục:** ở 50% bao phủ, doanh thu giữ lại còn 48,3% và lệch −50,5%; 3.363 dòng bị cách ly. Đây là giả định điều kiện của toàn bộ kết quả, không phải chi tiết kỹ thuật.

Kiểm thử: **42 passed**; `run.py --replications 50 --null-seeds 200 --missing-seeds 100` chạy xong; notebook `--check` pass.

> **Lưu ý lịch sử:** bản ghi PR2 từng viết F-04 là "ngoài khoảng null" với khoảng [−0,112; 0,112]. Cả kết luận và khoảng đó đều sai — xem PR3 bên dưới. Số đúng là [−0,112; 0,107] và giá trị quan sát **nằm trong** khoảng.

## PR3 — Draft PR #3, xong phần mã

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

## PR4 — Draft PR #4, xong phần mã

- Trích dẫn chuyển sang **APA 7** (author-date). Danh mục sắp xếp theo chữ cái, không còn lặp URL.
- Thêm **Efron (1979)** cho phần bootstrap — trước đó đây là phương pháp duy nhất được dùng mà không có nguồn. Đã đối chiếu DOI `10.1214/aos/1176344552`; Morris và cộng sự cũng được đối chiếu lại qua DOI thay vì tin theo trí nhớ.
- Bìa có 6 trường `[CẦN ĐIỀN ...]`: trường, khoa/bộ môn, học phần và mã, giảng viên hướng dẫn, nhóm và mã số sinh viên, nơi nộp. Không trường nào được đoán.
- Hai test mới: `test_every_reference_is_cited_and_every_citation_has_a_reference`, `test_cover_placeholders_are_marked_not_invented`.
- **50 passed**; `run.py` chạy xong (~280 s); notebook 18 code cells, `--check` pass; `report/bao_cao.md` 49.366 ký tự, 9 bảng, 13 hình, 0 token chưa giải.
- `docs/FINAL-REVIEW.md` đã tạo, đủ 7 mục.

### Lỗi CI phát hiện ở bước này

`.github/workflows/ci.yml` chỉ chạy cho pull request có base là `main`. PR3 và PR4 là stacked nên
**chưa từng được CI kiểm tra** — danh sách check rỗng, trông giống "chưa chạy" nhưng thực chất là
"không bao giờ chạy". Đã sửa thành chạy cho mọi base (`pull_request:` không lọc nhánh, thêm `feat/**`
vào push), và cherry-pick cùng sửa đó sang nhánh PR3 vì nhánh đó tách trước khi sửa.

## Việc bắt buộc con người làm

Xem `docs/FINAL-REVIEW.md` mục 7. Tóm tắt: điền bìa, đọc lại báo cáo, chạy lại pipeline trên máy
mình, chạy notebook, khai báo hỗ trợ AI theo quy định lớp, quyết định merge PR2–PR4, và pin lại
`requirements-lock.txt` nếu muốn nộp kèm môi trường chính xác.
