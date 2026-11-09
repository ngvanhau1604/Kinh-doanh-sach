# PR1 — Báo cáo bàn giao

**Nhánh:** `fix/reproducibility-and-tests` (từ `main` @ `ef2b543`)
**Commit:** `4ead4f6`, `64682c3`
**Trạng thái:** đã commit tại máy, **chưa push, chưa merge** — chờ duyệt.
**Remote đã xác nhận:** `https://github.com/ngvanhau1604/Kinh-doanh-sach.git`
**`main` không bị sửa.**

---

## 1. Danh sách lỗi đã sửa (kèm vị trí)

| Mã | Lỗi | Vị trí | Cách sửa |
|---|---|---|---|
| F-02 | Số liệu viết cứng trong báo cáo sinh tự động | `src/academic_report.py` (toàn bộ), `src/report_builder.py:build_sections` | Mọi con số lấy từ `m`, `v`, `stages`, `q`, `exp`, `PARAMS`. Thêm phát hiện: `build_sections` đọc `raw` từ đĩa trong khi nhận `d` từ bộ nhớ → trộn tập sạch mới với tệp raw cũ khi `n_lines` đổi. Nay nhận `raw`/`missing` qua tham số. |
| F-03 | `experiments()` bỏ qua cấu hình | `src/analysis.py:experiments` | `p = dict(PARAMS, **(params or {}))`; `n`, `missing_rate` truyền vào `generate`/`corrupt`. |
| F-05 | So sánh số thực bằng `==` làm notebook dừng | `notebooks/book_sales_analysis.ipynb` cell 7, `tools/refresh_presentation.py` | Làm tròn 6 chữ số khi ghi (`analysis._r`); so sánh dung sai tương đối `1e-9`. |
| F-08 | `online_share` gộp sàn + Website | `src/analysis.py:channel_shares`, `run.py`, notebook cell 25 | Tách `marketplace_share` (3 sàn) và `digital_channel_share` (3 sàn + Website). |
| F-11 | `price_group(NaN)` rơi vào nhóm cao nhất | `src/data_cleaner.py:price_group` | `out.where(s.notna(), 'Chưa biết')`. |
| F-12 | Thiếu kiểm thử hồi quy | `tests/test_regressions.py` (mới, 21 test) | Mỗi test được kiểm chứng bằng đột biến (mục 4). |
| F-13 | Đầu ra văn bản không tái lập theo byte | `run.py`, `src/report_builder.py`, `src/dashboard_builder.py` | `newline='\n'`; manifest loại `data_dictionary.md` và chính nó; PDF dùng `invariant=1`. |
| F-16 | Chú thích bảng/hình trùng tiêu đề mục, không dẫn trong bài | `src/report_builder.py`, `src/visualizer.py` | `caption` tách khỏi `title`; đánh số theo thứ tự tài liệu qua token `[[Bảng:…]]`/`[[Hình:…]]`; bỏ số hình in cứng trên PNG. |
| F-18 | Định dạng số kiểu Anh trong văn bản tiếng Việt | `src/report_builder.py:f` | `f()` dùng '.' hàng nghìn, ',' thập phân; áp dụng cho mọi số trong báo cáo. |
| F-09 | `requirements.txt` ghi sai phiên bản Python, không có CI | `requirements.txt`, `pyproject.toml` (mới), `.github/workflows/ci.yml` (mới) | CI cho 3.11/3.12/3.13 trên Linux + Windows; `requires-python = ">=3.11"` (sàn thật do numpy 2.3.5). |

Ngoài ra: hằng số sinh dữ liệu chuyển vào `PARAMS` (`src/config.py`, `src/data_generator.py`) — **dòng RNG không đổi**, xác nhận bằng hash SHA-256 của cả 4 tệp nguồn.

---

## 2. Kết quả kiểm thử thực tế

| Kiểm chứng | Kết quả |
|---|---|
| `pytest -q` (bản làm việc, Python 3.13.17) | **39 passed** in 42.51s |
| `pytest -q` (clone sạch, Python **3.14.3**) | **38 passed** in 49.59s (trước khi thêm test dashboard) |
| `tools/execute_notebook.py` (clone sạch) | **15 code cells, no execution errors** |
| `run.py` từ clone sạch | hoàn tất; chỉ `report/bao_cao.pdf` và `results/manifest.json` khác (xem mục 5) |
| `n_lines=7000` trong thư mục riêng | **không còn số liệu 6500** (0 kết quả khớp); bản sao 155→167, cách ly 25→26 |
| Tái lập: 2 lần chạy độc lập | **38/38 tệp giống nhau từng byte** (kể cả PDF) |
| Nhất quán metrics ↔ CSV ↔ dashboard ↔ báo cáo | **64/66** kiểm tra tự động; 2 mục còn lại là do kiểm tra sai cách (dashboard tính KPI phía trình duyệt) — đã thay bằng test đối soát dữ liệu nhúng: **đạt** |

---

## 3. Bảng so sánh trước/sau (kịch bản cơ sở)

Không có giá trị nghiệp vụ nào thay đổi. Chỉ độ chính xác biểu diễn và cột F-08 thay đổi.

| Chỉ tiêu | Trước (`ef2b543`) | Sau | Giống |
|---|---|---|---|
| lines | 6480 | 6480 | ✓ |
| books | 300 | 300 | ✓ |
| revenue | 2 969 430 000 | 2 969 430 000 | ✓ |
| quantity | 30 790 | 30 790 | ✓ |
| average_unit_price | 96441.37707047742 | 96441.37707 | ✓ (làm tròn 6) |
| yoy_pct | -1.3050806742470722 | -1.305081 | ✓ (làm tròn 6) |
| rating_qty_r | 0.009118716366735929 | 0.009119 | ✓ |
| rating_book_qty_r | 0.11723347685840545 | 0.117233 | ✓ |
| discount_qty_r | 0.1729538125923124 | 0.172954 | ✓ |
| good_rating_pct | 74.1820987654321 | 74.182099 | ✓ |
| iqr_flags | 179 | 179 | ✓ |
| truth_revenue | 2 978 555 000 | 2 978 555 000 | ✓ |
| relative_revenue_error_pct | -0.30635660580382584 | -0.306357 | ✓ |
| retained_pct | 99.6923076923077 | 99.692308 | ✓ |
| quarantine_precision / recall | 1.0 / 1.0 | 1.0 / 1.0 | ✓ |
| retained_revenue_error | 0 | 0 | ✓ |
| unresolved_missing | 0 | 0 | ✓ |

Tất cả bảng `results/*.csv` (genre, books, month, year, channel, segment, discount, recovery, author, publisher): **cùng số dòng, cùng tổng doanh thu**.

Thay đổi cấu trúc duy nhất: `sensitivity_runs.csv` bỏ `online_share`, thêm `marketplace_share` + `digital_channel_share` (150 dòng không đổi).

---

## 4. Kiểm chứng test có khả năng phát hiện lỗi thật

Đã hoàn nguyên từng bản sửa và chạy test tương ứng — **9/9 đột biến bị bắt**:

| Đột biến | Kết quả |
|---|---|
| F-11 bỏ `where(notna)` | CAUGHT |
| F-03 `experiments` bỏ `params` | CAUGHT |
| F-08 trả về cùng một giá trị cho 2 định nghĩa | CAUGHT |
| F-18 bỏ định dạng Việt | CAUGHT |
| F-02 chèn lại `'6.660 / 6.480'` | CAUGHT |
| F-02b `raw` đọc từ đĩa | CAUGHT |
| F-16 caption = tiêu đề mục | CAUGHT |
| F-13 bỏ `newline='\n'` | CAUGHT |
| F-05 bỏ làm tròn | CAUGHT |

---

## 5. Danh sách tệp thay đổi

```
 .github/workflows/ci.yml            |   49 +
 charts/*.png (7 tệp)                |  Bin (nhỏ hơn, bỏ số hình in cứng)
 charts/dashboard.html               | 7786 +++---
 notebooks/book_sales_analysis.ipynb |  372 +-
 pyproject.toml                      |   24 +
 report/bao_cao.html                 |    2 +-
 report/bao_cao.md                   |   78 +-
 report/bao_cao.pdf                  |  894 ++--
 requirements.txt                    |    3 +-
 results/manifest.json               |   33 +-
 results/metrics.json                |  140 +-
 results/missing_sensitivity.csv     |   12 +-
 results/sensitivity_runs.csv        |  302 +-
 results/sensitivity_summary.csv     |   39 +-
 run.py                              |   41 +-
 src/academic_report.py              |   49 +-
 src/analysis.py                     |   39 +-
 src/config.py                       |   16 +
 src/dashboard_builder.py            |    3 +-
 src/data_cleaner.py                 |    9 +-
 src/data_generator.py               |   48 +-
 src/report_builder.py               |  201 +-
 src/visualizer.py                   |   25 +-
 tests/test_regressions.py           |  307 +
 tools/refresh_presentation.py       |   17 +-
 tools/refresh_report.py             |    7 +-
 32 files changed, 5643 insertions(+), 4853 deletions(-)
```

---

## 6. Rủi ro và lỗi còn lại

1. **PDF khác nhau giữa các phiên bản Python — không thể tránh.** Python 3.13 dùng zlib 1.3.1; Python 3.14 dùng **zlib-ng**. Cùng ảnh nguồn (PNG giống từng byte), cùng nội dung, nhưng 8/8 luồng ảnh nhúng nén ra độ dài khác nhau (ví dụ 145316 vs 146428 byte). Đã xác minh bằng `/Length` của từng image stream. Trong **cùng một** môi trường, PDF tái lập từng byte (đã có test). Nếu cần PDF giống tuyệt đối giữa các máy, phải ghim phiên bản Python hoặc tắt nén ảnh.
2. **CSV dùng CRLF có chủ ý** (`utf-8-sig` cho Excel trên Windows). Đây là lựa chọn có ghi chú trong `run.py`, không phải sơ suất. Tệp văn bản/HTML/JSON thì dùng LF.
3. **Notebook ghi lại output khi chạy** (execution_count, thời gian) → `git status` bẩn sau khi chạy. Source không đổi (đã kiểm tra 31/31 cell giống nhau). Nếu muốn sạch hoàn toàn, cần thêm bước `git checkout` hoặc strip output trong CI.
4. **`data_dictionary.md` không còn trong manifest** — đúng theo thiết kế (tệp viết tay, không do pipeline sinh), nhưng nghĩa là manifest không còn xác nhận tệp này.
5. **F-04 (mâu thuẫn kế hoạch) chưa xử lý** — đúng như yêu cầu, để lại cho PR2. Ghi nhận: "1,5% vượt r = 0,117" không tự chứng minh giá trị nằm trong khoảng 95%; cần thiết kế lại tiêu chí.
6. **Chưa chạy CI thật trên GitHub** — workflow đã viết và validate cú pháp YAML, nhưng chỉ chạy được sau khi push. Chưa push theo yêu cầu.

---

## 7. Đề xuất commit và nội dung PR

Hai commit đã tạo:

```
64682c3 Make dashboard output LF-stable and add dashboard reconciliation test
4ead4f6 Fix reproducibility, reporting and test coverage (PR1)
```

Nội dung PR (dán vào GitHub):

> **Fix reproducibility, reporting and test coverage (PR1)**
>
> Removes hard-coded figures from the generated report, makes the experiment layer honour the configured parameters, and adds regression tests that fail when each fix is reverted.
>
> **Defects addressed:** F-02, F-03, F-05, F-08, F-11, F-12, F-13, F-16, F-18, F-09.
>
> **Business results unchanged.** Base-case metrics are identical; only float precision (6 decimals) and the F-08 column split differ.
>
> **Verification:** 39 tests pass; two independent pipeline runs produce 38/38 byte-identical outputs; notebook executes on a clean clone under Python 3.14; `n_lines=7000` run contains no base-case figures; 9/9 reverted fixes are caught by the new tests.
>
> **Known limitation:** the PDF differs across Python builds because 3.14 ships zlib-ng while 3.13 ships stock zlib. Within one environment it is byte-reproducible.

---

## 8. Việc cần bạn quyết định

- Push `fix/reproducibility-and-tests` lên GitHub và mở PR? (chưa làm)
- Có muốn giữ 2 commit hay squash thành 1?
- `n_lines=7000` chỉ dùng để kiểm chứng — không thay đổi kịch bản cơ sở.
