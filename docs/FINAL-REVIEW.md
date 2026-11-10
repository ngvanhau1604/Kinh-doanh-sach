# Đánh giá cuối — trạng thái bản nộp

Ngày: 2026-11-10. Tài liệu này ghi lại chính xác những gì đã thay đổi, những gì đã kiểm chứng, và
những gì còn lại con người phải làm. Mọi số trong đây lấy từ `results/metrics.json` và
`results/*.csv` của lần chạy `run.py --replications 50 --null-seeds 200 --missing-seeds 100`.

---

## 1. Lỗi đã sửa

| Mã | Lỗi | Cách sửa |
|---|---|---|
| F-01 | Precision và recall bằng 100% là tautology: quy tắc cách ly chính là nghịch đảo của quy tắc cài lỗi | Tám họ lỗi có tham số, đo trên toàn bộ dòng mang lỗi. Recall gộp nay **0,469** |
| F-02 | Báo cáo tự mâu thuẫn về số dòng và tỷ lệ khớp | Số suy từ `metrics.json`, không viết cứng |
| F-03 | `experiments()` không đọc `PARAMS` | Truyền `params` xuyên suốt |
| F-04 | r = 0,117 được mặc định nằm trong khoảng null | Xem mục 3 — kết luận đã đảo **hai lần** |
| F-05 | Notebook fail do so sánh float bằng `==` | So sánh có dung sai |
| F-08 | `marketplace_share` và `digital_channel_share` bị gộp làm một | Tách hai định nghĩa |
| F-09 | `requirements-lock.txt` ghi Python 3.12 trong khi môi trường 3.13 | Ghi rõ khoảng phiên bản, CI chạy 3.11/3.12/3.13 |
| F-10 | `catalog_coverage` là giả định chưa từng được kích hoạt | Thí nghiệm thật, 5 mức bao phủ |
| F-11 | `price_group(NaN)` trả nhóm sai | Xử lý NaN riêng |
| F-12 | Thiếu test hồi quy | 50 test, gồm các test chặn đúng những lỗi ở đây |
| F-13 | Đầu ra văn bản không tái lập byte | Chuẩn hóa metadata, ghi LF |
| F-16 | Chú thích trùng tiêu đề | Sửa |
| F-18 | 19 chỗ dùng dấu phẩy ngăn nghìn kiểu Anh | Định dạng số kiểu Việt Nam |

Lỗi phát hiện thêm trong quá trình làm, không có trong danh sách ban đầu:

- **Notebook làm bẩn working tree** sau mỗi lần chạy, và `--check` so sánh byte tuyệt đối nên đỏ trên Linux dù notebook giống hệt trên Windows. PNG nhúng do matplotlib/freetype cục bộ render. Nay `--check` so cấu trúc, source, execution count và văn bản output; hình render vào thư mục tạm.
- **Hai cách gộp sách khác nhau.** `summarize` gộp theo `(ma_sach, ten_sach)`, `null_band` gộp chỉ theo `ma_sach`. Các dòng không tra được mã sách mang khóa thay thế `BK9999`, nên cách gộp thứ hai nhập sáu sách khác nhau thành một. Đây là nguyên nhân trực tiếp của kết luận F-04 sai ở mục 3.
- **Câu văn mâu thuẫn còn sót** ở §4.5 nói ngược với §4.6 về cùng một kết quả.
- **Danh mục tham khảo lặp URL hai lần** và không sắp xếp.
- **CI chỉ chạy cho pull request có base là `main`.** PR3 và PR4 là stacked nên chưa từng được kiểm tra; danh sách check rỗng trông giống "chưa chạy" nhưng thực chất là "không bao giờ chạy". Sửa trigger xong thì lỗi tiếp theo lộ ra ngay bên dưới.
- **`run.py` sập trên Windows CI.** `print(json.dumps(..., ensure_ascii=False))` gặp stdout cp1252 và ném `UnicodeEncodeError` ở ký tự 2772, làm hỏng bước pipeline smoke trên cả Python 3.12 và 3.13. Lỗi này không hiện ở máy local vì shell đã đặt `PYTHONIOENCODING=utf-8`. Nay phần in ra console lùi về `ensure_ascii=True` khi cần; tệp `metrics.json` vẫn ghi UTF-8 như cũ.

## 2. Cải tiến học thuật

- **Thiết kế thí nghiệm theo ADEMP** (Morris và cộng sự, 2019), nêu rõ mục tiêu, cơ chế sinh, đại lượng, phương pháp, thước đo.
- **Tám họ lỗi có tham số**, số lỗi mỗi họ ~ Poisson(λ), gồm bốn họ tạo ra giá trị **hợp lệ nhưng sai**: giá đặt lại, giá hoán vị, ngày đảo, thể loại sai. Đây là phần quan trọng nhất: không quy tắc nào chỉ dựa trên miền giá trị phát hiện được chúng, và bài không dựng quy tắc đọc dữ liệu chuẩn để xóa chúng.
- **Tách phát hiện khỏi tác hại.** `n_cach_ly` (loại bỏ), `n_danh_dau` (đánh dấu giữ dòng), `con_sai` (dòng vẫn sai và vẫn nằm trong tập phân tích). Phát hiện không đồng nghĩa với không còn tác hại.
- **Ba loại khoảng bất định được tách bạch**: khoảng bootstrap (độ chính xác của ước lượng), khoảng null (giá trị có thể do chính mô hình sinh ra không), độ tản giữa các kịch bản (kết quả đổi thế nào khi thay giả định). Không loại nào là khoảng tin cậy thị trường.
- **Đơn vị rút lại theo chỉ tiêu.** Tương quan cấp sách rút theo đầu sách, không theo dòng, vì rút theo dòng sẽ tính một sách có 40 giao dịch như 40 quan sát độc lập.
- **Thí nghiệm dữ liệu thiếu** với ba cơ chế (MCAR, MAR, MNAR), ba tỷ lệ và bốn cách xử lý, kèm sai số Monte Carlo.
- **Trích dẫn APA 7**, tham chiếu bảng/hình tự động, bìa có placeholder rõ ràng.

## 3. So sánh kết quả trước và sau

| Chỉ tiêu | Trước | Sau | Ghi chú |
|---|---|---|---|
| Recall gộp | 1,000 | **0,469** | Đo trên toàn bộ 49 dòng mang lỗi, không chỉ hai họ quy tắc nhắm tới |
| Precision cách ly | 1,000 | 1,000 | Vẫn đúng: không dòng sạch nào bị cách ly oan |
| Dòng còn sai trong tập sạch | 0 | **32/49** | 17 dòng bị cách ly; trong 32 dòng còn lại, 6 được đánh dấu nhưng vẫn nằm trong tập phân tích |
| Sai lệch doanh thu so với chuẩn | 0% | **+2,992%** | 99,66% dòng được giữ |
| Số dòng phân tích | 6.478 | 6.478 | Không đổi |
| Doanh thu | 3.067.680.000 | 3.067.680.000 | Không đổi |

**F-04 — kết luận đã đảo hai lần, và lần này là lần đúng.**

Lần đầu: "r = 0,117 nằm trong khoảng null", dựa trên 12 seed nên khoảng quá hẹp, và thực ra chưa
từng được kiểm chứng.

Lần hai: "giá trị quan sát nằm ngoài khoảng 95%". Sai vì giá trị quan sát và khoảng null được tính
trên hai cách gộp sách khác nhau.

Lần ba, hiện tại — cả hai bên dùng cùng một cách gộp, 200 seed:

- trung bình 0,000; độ lệch chuẩn 0,058; khoảng 95% **[−0,112; 0,107]**
- giá trị quan sát **0,105456**, phân vị thứ **96,5**
- **nằm trong khoảng**

Kết luận: giá trị này tương thích với nhiễu của chính mô hình, không được trình bày như một phát
hiện, và cũng không phải bằng chứng quan hệ thị trường vì điểm đánh giá được sinh độc lập với lượng.
Báo cáo ghi kèm cả phân vị vì 96,5 nằm ở đuôi của khoảng trung tâm 95%; gộp thành kết luận nhị phân
sẽ che mất chi tiết đó.

Phán quyết nay do `_inside_band` / `_band_verdict` **tính**, không viết tay trong văn bản. Bản viết
tay đã lệch khỏi số liệu hai lần; có test chặn nếu lệch lại.

**Độ bao phủ danh mục — kết quả nghiêm trọng hơn mô tả cũ.** Ở mức bao phủ 50%, doanh thu giữ lại
còn 48,3% và lệch −50,5%; 3.363 dòng bị cách ly, tức 50,5% dữ liệu. Đây là điều kiện của toàn bộ
kết quả, không phải chi tiết kỹ thuật.

## 4. Kết quả chạy kiểm thử và pipeline

- `pytest -q`: **51 passed** (~84 s).
- `run.py --replications 50 --null-seeds 200 --missing-seeds 100`: chạy xong (~280 s), sinh PDF/HTML/MD.
- `run.py --out .ci-out --skip-presentation --replications 3` **không đặt `PYTHONIOENCODING`**: exit 0 (đây là điều kiện CI thật).
- `tools/build_notebook.py` + `tools/execute_notebook.py`: **18 code cells, không lỗi**; `--check` pass hai lần liên tiếp, working tree sạch.
- `report/bao_cao.md`: 49.366 ký tự, không còn token chưa giải, 9 bảng (1–9) và 13 hình (1–13) liên tục, 26 tiêu đề chương/mục, 7 placeholder bìa.
- CI: PR1 **12/12** xanh; PR2 **6/6**; PR3 **12/12**; PR4 **12/12** (6 job × 2 sự kiện, Python 3.11/3.12/3.13 trên ubuntu-latest và windows-latest).

## 5. Danh sách PR và trạng thái

| PR | Nhánh | Base | Trạng thái |
|---|---|---|---|
| [#1](https://github.com/ngvanhau1604/Kinh-doanh-sach/pull/1) | `fix/reproducibility-and-tests` | `main` | **ĐÃ MERGE** (squash `97624e3`), CI 12/12 xanh |
| [#2](https://github.com/ngvanhau1604/Kinh-doanh-sach/pull/2) | `feat/simulation-design` | `main` | Draft, CI **6/6** xanh, chờ review |
| [#3](https://github.com/ngvanhau1604/Kinh-doanh-sach/pull/3) | `feat/analysis-visualization` | `feat/simulation-design` | Draft, CI **12/12** xanh, stacked trên PR2 |
| [#4](https://github.com/ngvanhau1604/Kinh-doanh-sach/pull/4) | `feat/academic-report` | `feat/analysis-visualization` | Draft, CI **12/12** xanh, stacked trên PR3 |

Thứ tự merge: **PR2 → PR3 → PR4**. PR3 và PR4 là stacked, không merge độc lập được.

## 6. Giới hạn nghiên cứu còn tồn tại

1. **Dữ liệu là mô phỏng.** Không có kết luận nào về thị trường sách Việt Nam. Mọi tham số sinh là giả định thiết kế, chưa hiệu chỉnh theo dữ liệu thực.
2. **Độ bao phủ danh mục là điều kiện của toàn bộ kết quả.** Ở 50% bao phủ, một nửa doanh thu biến mất. Trong vận hành thật, đây là rủi ro lớn nhất và không thể phát hiện từ bên trong dữ liệu bán hàng.
3. **Bốn họ lỗi không thể phát hiện bằng quy tắc miền giá trị**: giá đặt lại, giá hoán vị, ngày đảo, thể loại sai. Chúng vẫn nằm trong tập phân tích và bài không cố che điều đó.
4. **Recall 0,469** nghĩa là hơn một nửa số dòng mang lỗi vẫn ở lại. Con số này là kết quả, không phải khuyết điểm cần che.
5. **Khoảng bootstrap không bao gồm bất định của mô hình sinh.** Nó chỉ đo biến thiên lấy mẫu trong một mẫu mô phỏng. Khoảng hẹp không làm kết quả đúng hơn.
6. **Tái lập byte chỉ đúng cho văn bản và cấu trúc.** Hình ảnh tái lập theo nội dung, không theo byte, và phụ thuộc môi trường render.
7. **`requirements-lock.txt` chưa được pin lại** theo môi trường 3.13 đang dùng; CI chạy được trên cả ba phiên bản nhưng lock file vẫn nên được tạo lại trước khi nộp.
8. **Chưa có dữ liệu thật để đối chứng.** Mọi so sánh "trước/sau" trong tài liệu này là so với bản trước của chính mô hình, không phải so với thực tế.

## 7. Việc bắt buộc con người phải làm trước khi nộp

- [ ] **Điền bìa**: tên trường, khoa/bộ môn, tên và mã học phần, giảng viên hướng dẫn, họ tên và mã số sinh viên của nhóm, địa điểm nộp. Sáu trường đang là `[CẦN ĐIỀN ...]`.
- [ ] **Đọc lại toàn bộ báo cáo** và xác nhận giọng văn, độ dài và cấu trúc phù hợp yêu cầu học phần.
- [ ] **Chạy lại pipeline trên máy của mình** (`python run.py --replications 50`) và xác nhận số liệu khớp với báo cáo đã nộp.
- [ ] **Chạy notebook** từ đầu đến cuối và đọc phần diễn giải.
- [ ] **Khai báo hỗ trợ AI** theo quy định của lớp, nếu lớp yêu cầu.
- [ ] **Quyết định merge PR2, PR3, PR4** — người dùng đã đặt quy tắc không tự merge ba PR này.
- [ ] **Kiểm tra lại các nguồn tham khảo** nếu giảng viên yêu cầu dẫn nguồn khác ngoài APA, hoặc yêu cầu tài liệu tiếng Việt.
- [ ] **Pin lại `requirements-lock.txt`** nếu muốn nộp kèm môi trường chính xác.

---

## Ghi chú về cách làm việc

Hai kết luận trong quá trình này đã bị đảo lại. Cả hai đều vì cùng một lý do: một con số được so
sánh với một con số khác được tính trên đơn vị khác. Đó là lý do phần F-04 ở trên ghi lại cả ba lần
kết luận thay vì chỉ lần cuối. Một báo cáo chỉ trình bày kết quả đúng sẽ không cho người đọc biết
phép kiểm đã từng sai ở đâu, và người đọc cần biết điều đó để đánh giá độ tin của phần còn lại.
