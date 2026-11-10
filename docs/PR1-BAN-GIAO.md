# PR1 — Báo cáo bàn giao

**Nhánh:** `fix/reproducibility-and-tests` (từ `main` @ `ef2b543`)
**Commit:** `4ead4f6`, `64682c3`, `1352203`, `44c02d3`, `fbdd8fa`, `213c3bf`
**Trạng thái:** đã push, **CI 12/12 xanh** trên cả hai lần chạy (6 job × 2 sự kiện: Python 3.11/3.12/3.13 trên ubuntu-latest và windows-latest), sẵn sàng squash merge.
**Remote:** `https://github.com/ngvanhau1604/Kinh-doanh-sach.git`
**`main` không bị sửa** trong suốt quá trình này.

### Ghi chú về lần chạy CI đầu tiên (đã sửa)

Lần chạy đầu của PR1 báo đỏ 12/12, không phải vì phân tích sai mà vì hai lỗi hạ tầng. Ghi lại vì cả hai đều là bài học về tính tái lập:

1. `?? .ci-out/` làm bước "working tree clean" thất bại. Bước smoke run ghi đầu ra vào `.ci-out/` và không có gì bỏ qua thư mục đó. Đã thêm vào `.gitignore`.
2. `--check` báo "Notebook outputs are stale" trên ubuntu-latest với một notebook giống hệt từng byte trên Windows. Nguyên nhân: so sánh byte tuyệt đối, trong khi PNG nhúng do bản matplotlib/freetype cục bộ render, nên cùng một hình cho ra byte khác nhau giữa Linux và Windows. Một phép so sánh byte không thể đúng across-platform.

Cách sửa: `--check` nay so sánh những gì người đọc kiểm chứng được — số ô và thứ tự, source từng ô, execution count, văn bản từng output, và sự hiện diện cùng loại của từng hình. Byte của hình không được so sánh vì nó không phải thuộc tính của phân tích. Notebook cũng render hình vào thư mục tạm thay vì `charts/`, nên chạy lại không thể làm bẩn cây làm việc trên bất kỳ nền tảng nào.

Đây là giới hạn tái lập byte cần nêu rõ: **văn bản và cấu trúc tái lập chính xác; hình ảnh tái lập theo nội dung, không theo byte, và phụ thuộc môi trường render.**

---

## 1. Danh sách lỗi đã sửa (kèm vị trí)

| Mã | Lỗi | Vị trí | Cách sửa |
|---|---|---|---|
| F-02 | Số liệu viết cứng trong báo cáo sinh tự động | `src/academic_report.py` (toàn bộ), `src/report_builder.py:build_sections` | Mọi con số lấy từ `m`, `v`, `stages`, `q`, `exp`, `PARAMS`. Thêm phát hiện: `build_sections` đọc `raw` từ đĩa trong khi nhận `d` từ bộ nhớ → trộn tập sạch mới với tệp raw cũ khi `n_lines` đổi. Nay nhận `raw`/`missing` qua tham số. |
| F-03 | `experiments()` bỏ qua cấu hình | `src/analysis.py:experiments` | `p = dict(PARAMS, **(params or {}))`; `n`, `missing_rate` truyền vào `generate`/`corrupt`. |
| F-05 | So sánh số thực bằng `==` làm notebook dừng | `notebooks/book_sales_analysis.ipynb` cell 7, `tools/refresh_presentation.py` | Làm tròn 6 chữ số khi ghi (`analysis._r`); so sánh dung sai tương đối `1e-9`. |
| F-08 | `online_share` gộp sàn + Website | `src/analysis.py:channel_shares`, `run.py`, notebook cell 25 | Tách `marketplace_share` (3 sàn) và `digital_channel_share` (3 sàn + Website). |
| F-11 | `price_group(NaN)` rơi vào nhóm cao nhất | `src/data_cleaner.py:price_group` | `out.where(s.notna(), 'Chưa biết')`. |
| F-12 | Thiếu kiểm thử hồi quy | `tests/test_regressions.py` (mới, 23 test) | Mỗi test được kiểm chứng bằng đột biến (mục 4). |
| F-13 | Đầu ra văn bản không tái lập theo byte | `run.py`, `src/report_builder.py`, `src/dashboard_builder.py` | `newline='\n'`; manifest loại `data_dictionary.md` và chính nó; PDF dùng `invariant=1`. |
| F-13b | Notebook làm bẩn working tree sau mỗi lần chạy | `tools/execute_notebook.py` | Xem mục 5. |
| F-16 | Chú thích bảng/hình trùng tiêu đề mục, không dẫn trong bài | `src/report_builder.py`, `src/visualizer.py` | `caption` tách khỏi `title`; đánh số theo thứ tự tài liệu qua token `[[Bảng:…]]`/`[[Hình:…]]`; bỏ số hình in cứng trên PNG. |
| F-18 | Định dạng số kiểu Anh trong văn bản tiếng Việt | `src/report_builder.py:f` | `f()` dùng '.' hàng nghìn, ',' thập phân; áp dụng cho mọi số trong báo cáo. |
| F-09 | `requirements.txt` ghi sai phiên bản Python, không có CI | `requirements.txt`, `pyproject.toml` (mới), `.github/workflows/ci.yml` (mới) | CI cho 3.11/3.12/3.13 trên Linux + Windows; `requires-python = ">=3.11"` (sàn thật do numpy 2.3.5). |

Ngoài ra: hằng số sinh dữ liệu chuyển vào `PARAMS` (`src/config.py`, `src/data_generator.py`) — **dòng RNG không đổi**, xác nhận bằng hash SHA-256 của cả 4 tệp nguồn.

---

## 2. Kết quả kiểm thử thực tế

| Kiểm chứng | Kết quả |
|---|---|
| `pytest -q` (bản làm việc, Python 3.13.17) | **41 passed** in 44.35s |
| `pytest -q` (clone sạch, Python **3.14.3**) | 38 passed in 49.59s (trước khi thêm test dashboard và test notebook) |
| `tools/execute_notebook.py` (clone sạch) | **15 code cells, no execution errors** |
| `tools/execute_notebook.py --check` | **đạt** — notebook đã commit khớp lần chạy mới |
| `run.py` từ clone sạch | hoàn tất; chỉ `report/bao_cao.pdf` và `results/manifest.json` khác (xem mục 6) |
| `n_lines=7000` trong thư mục riêng | **không còn số liệu 6500** (0 kết quả khớp); bản sao 155→167, cách ly 25→26 |
| Tái lập: 2 lần chạy độc lập | **38/38 tệp giống nhau từng byte** (kể cả PDF) |
| Nhất quán metrics ↔ CSV ↔ dashboard ↔ báo cáo | **64/66** kiểm tra tự động; 2 mục còn lại là do kiểm tra sai cách (dashboard tính KPI phía trình duyệt) — đã thay bằng test đối soát dữ liệu nhúng: **đạt** |
| CI GitHub Actions (run `42725422143`, `42725428969`) | **12/12 SUCCESS** — 3 phiên bản Python × 2 hệ điều hành × 2 lần chạy |

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

## 5. Notebook không còn làm bẩn working tree (F-13b)

**Triệu chứng.** Chạy `tools/execute_notebook.py` xong, `git status` báo `M notebooks/book_sales_analysis.ipynb` dù nội dung phân tích không đổi.

**Nguyên nhân thật.** Không phải output thay đổi. nbclient gắn metadata theo thời gian thực vào **từng cell**:

```json
"metadata": {"execution": {"iopub.execute_input": "2026-11-09T12:43:25.327159Z", ...}}
```

Đo trực tiếp: 15/15 cell code khác nhau **chỉ ở trường `metadata.execution`**; `source`, `outputs` và `execution_count` giống tuyệt đối.

**Cách sửa.** `tools/execute_notebook.py` chuẩn hóa trước khi ghi: bỏ `metadata.execution` của từng cell và `metadata.language_info.version` (phụ thuộc phiên bản Python đang chạy). **Output được giữ nguyên** — đó là bằng chứng nộp bài, không phải rác build.

**Vì sao không xóa output.** Xóa output là cách sửa phổ biến và sai ở đây: notebook có output là một phần của bản nộp và là bằng chứng notebook chạy được. Yêu cầu là "không xóa output cần thiết cho việc nộp và tái lập" — nên output ở lại, chỉ metadata biến động bị bỏ.

**Thêm `--check`.** Chạy notebook rồi so với tệp đã commit; khác thì exit 1. CI dùng nó để chứng minh output đã commit là **hiện hành**, không chỉ là **có tồn tại**.

**Đo lại.** Chạy 2 lần liên tiếp: lần 1 ghi (chuẩn hóa CRLF→LF một lần), lần 2 **"File unchanged"**. `--check` exit 0. Test hồi quy `test_notebook_execution_is_idempotent` mô phỏng đúng việc nbclient gắn timestamp và khẳng định tệp không đổi.

**Lưu ý về diff một lần.** Tệp notebook đã commit dùng CRLF; nay ghi bằng LF. Đây là điều kiện để `--check` chạy được trên runner Linux (nơi LF là chuẩn), và khớp với `.gitattributes`/quy ước các tệp văn bản khác. Diff hiển thị 3083 dòng nhưng **đã kiểm chứng bằng so sánh cấu trúc**: sau khi chuẩn hóa CRLF và bỏ metadata biến động, hai phiên bản **bằng nhau hoàn toàn** (`equal after normalising line endings + volatile metadata: True`).

---

## 6. Danh sách tệp thay đổi

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

## 7. Rủi ro và lỗi còn lại

1. **PDF khác nhau giữa các phiên bản Python — không thể tránh.** Python 3.13 dùng zlib 1.3.1; Python 3.14 dùng **zlib-ng**. Cùng ảnh nguồn (PNG giống từng byte), cùng nội dung, nhưng 8/8 luồng ảnh nhúng nén ra độ dài khác nhau (ví dụ 145316 vs 146428 byte). Đã xác minh bằng `/Length` của từng image stream. Trong **cùng một** môi trường, PDF tái lập từng byte (đã có test). Nếu cần PDF giống tuyệt đối giữa các máy, phải ghim phiên bản Python hoặc tắt nén ảnh.
2. **CSV dùng CRLF có chủ ý** (`utf-8-sig` cho Excel trên Windows). Đây là lựa chọn có ghi chú trong `run.py`, không phải sơ suất. Tệp văn bản/HTML/JSON/notebook thì dùng LF.
3. **`data_dictionary.md` không còn trong manifest** — đúng theo thiết kế (tệp viết tay, không do pipeline sinh), nhưng nghĩa là manifest không còn xác nhận tệp này.
4. **F-04 (mâu thuẫn kế hoạch) chưa xử lý** — đúng như yêu cầu, để lại cho PR2. Ghi nhận: "1,5% vượt r = 0,117" không tự chứng minh giá trị nằm trong khoảng 95%; cần thiết kế lại tiêu chí.
5. **Giới hạn tái lập byte theo môi trường** — tóm tắt chính xác: trong cùng một môi trường Python, 38/38 tệp tái lập từng byte. Giữa các môi trường khác phiên bản Python, chỉ `report/bao_cao.pdf` khác (nén ảnh zlib vs zlib-ng); mọi tệp khác vẫn khớp. Đây là giới hạn của công cụ nén, không phải của pipeline.

---

## 8. Trạng thái PR

| Mục | Giá trị |
|---|---|
| PR | #1 — `fix: improve reproducibility, reporting consistency and regression tests` |
| Nhánh | `fix/reproducibility-and-tests` → `main` |
| Commit | 5 commit (4 trước + commit bàn giao này) |
| CI | 12/12 SUCCESS (Python 3.11/3.12/3.13 × ubuntu/windows) |
| Mergeable | MERGEABLE, mergeStateStatus CLEAN |
| Draft | Có → chuyển Ready trước khi merge |
| Chiến lược merge | Squash, không force-push |
