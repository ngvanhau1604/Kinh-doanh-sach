"""One source builds Markdown, offline HTML and paginated Vietnamese PDF."""
from pathlib import Path
import html
import re
import pandas as pd
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,Image,PageBreak,KeepTogether
from reportlab.lib.pagesizes import A4
from .config import PARAMS

SOURCES=[
('Efron, B. (1979). Bootstrap methods: Another look at the jackknife. Annals of Statistics, 7(1), 1–26. https://doi.org/10.1214/aos/1176344552','https://doi.org/10.1214/aos/1176344552'),
('GO FAIR Foundation. (n.d.). The FAIR guiding principles. Truy cập 08/11/2026, từ https://www.gofair.foundation/fair-principles','https://www.gofair.foundation/fair-principles'),
('Morris, T. P., White, I. R., & Crowther, M. J. (2019). Using simulation studies to evaluate statistical methods. Statistics in Medicine, 38(11), 2074–2102. https://doi.org/10.1002/sim.8086','https://doi.org/10.1002/sim.8086'),
('NIST/SEMATECH. (2012). e-Handbook of statistical methods (Section 1.3.3.7: Box plot). Truy cập 08/11/2026, từ https://www.itl.nist.gov/div898/handbook/eda/section3/boxplot.htm','https://www.itl.nist.gov/div898/handbook/eda/section3/boxplot.htm'),
('The pandas development team. (2024). pandas.cut [API reference]. Truy cập 08/11/2026, từ https://pandas.pydata.org/docs/reference/api/pandas.cut.html','https://pandas.pydata.org/docs/reference/api/pandas.cut.html'),
]

def f(x,dec=0):
    """Vietnamese number format: '.' groups thousands, ',' is the decimal mark."""
    return f'{x:,.{dec}f}'.replace(',','_').replace('.',',').replace('_','.')


def _asset_numbers(sections):
    """Assign table/figure numbers by document order, keyed by section title."""
    tables,figures={},{}
    for s in sections:
        if s.get('chart'): figures[s['title']]=len(figures)+1
        if s.get('table'): tables[s['title']]=len(tables)+1
    return tables,figures


def _resolve(text,tables,figures):
    """Replace [[Bảng:title]] / [[Hình:title]] tokens with the number that title actually got.

    Numbers are therefore never written by hand: reordering a section renumbers the reference
    with it, and a reference to a missing asset fails loudly instead of printing a stale number.
    Matching ignores any leading section number in either the token or the title, because the
    token is written before the section titles are final and a hard-coded number there silently
    rots the moment a section is inserted.
    """
    import re as _re
    def norm(s):
        return _re.sub(r'^\s*\d+(?:\.\d+)*\.?\s+','',s).strip()
    def sub(m):
        kind,title=m.group(1),m.group(2)
        book=tables if kind=='Bảng' else figures
        key=norm(title)
        for name,number in book.items():
            if norm(name)==key: return f'{kind} {number}'
        raise KeyError(f'Không tìm thấy {kind.lower()} cho mục: {title!r}')
    return re.sub(r'\[\[(Bảng|Hình):(.+?)\]\]',sub,text)


def _inside_band(null, metric, value):
    """Whether `value` falls inside the empirical 95% band of the null distribution.

    Computed rather than asserted: an earlier revision stated the verdict in prose and it drifted
    out of step with the numbers. The percentile and the band are two different questions and the
    text reports both, because a value can sit at the 96.5th percentile and still be inside a
    central 95% interval.
    """
    s = null[metric].dropna()
    lo, hi = s.quantile(.025), s.quantile(.975)
    return 'trong' if lo <= value <= hi else 'ngoài'


def _band_verdict(null, metric, value):
    s = null[metric].dropna()
    lo, hi = s.quantile(.025), s.quantile(.975)
    if lo <= value <= hi:
        return (f'giá trị quan sát tương thích với phân phối null: nó không tách khỏi mức dao động '
                f'do chính mô hình sinh ra, nên không được trình bày như một phát hiện')
    return (f'giá trị quan sát không tương thích với phân phối null ở mức 95%, nên có một nguồn '
            f'tương quan chưa được khai báo cần điều tra; đây là dấu hiệu cần giải thích, không '
            f'phải kết quả để trích dẫn')


def build_sections(root,d,t,m,v,stages,exp,recovery,raw=None,missing=None,families=None,null=None,nullstats=None,coverage=None,boot=None):
    sections=[]
    def section(title,paras,chart=None,table=None,caption=None):
        sections.append({'title':title,'paras':paras,'chart':chart,'table':table,'caption':caption})
    revenue=f(m['revenue'])
    # The report must describe the run that produced it. Reading these back from disk mixed a
    # freshly computed clean set with the previously committed raw file whenever n_lines changed.
    if missing is None: missing=pd.read_csv(root/'results/missing_sensitivity.csv')
    if isinstance(missing,tuple): missing=missing[0]
    if raw is None: raw=pd.read_csv(root/'data/raw/book_sales_raw.csv')
    if families is None: families=pd.read_csv(root/'results/error_family_performance.csv')
    if null is None: null=pd.read_csv(root/'results/null_distribution.csv')
    if nullstats is None: nullstats=pd.read_csv(root/'results/null_summary.csv')
    if coverage is None: coverage=pd.read_csv(root/'results/catalog_coverage.csv')
    if boot is None: boot=pd.read_csv(root/'results/bootstrap_ci.csv')
    q=pd.read_csv(root/'data/audit/quarantine.csv')
    p=PARAMS
    ndays=len(pd.date_range(p['start'],p['end']))
    per_genre=p['n_books']//10
    section('Xây dựng và phân tích bộ dữ liệu kinh doanh',[
        'NGHIÊN CỨU MÔ PHỎNG CÓ KIỂM CHỨNG • NHẬP MÔN KHOA HỌC DỮ LIỆU',
        # Cover block. Everything the group must fill in is marked [CẦN ĐIỀN] rather than
        # invented: the template cannot know the institution, the lecturer or the member names,
        # and a plausible-looking wrong name on a submitted cover is worse than a blank.
        'TRƯỜNG: [CẦN ĐIỀN TÊN TRƯỜNG]',
        'KHOA/BỘ MÔN: [CẦN ĐIỀN KHOA HOẶC BỘ MÔN]',
        'HỌC PHẦN: [CẦN ĐIỀN TÊN HỌC PHẦN] — MÃ HỌC PHẦN: [CẦN ĐIỀN MÃ]',
        'GIẢNG VIÊN HƯỚNG DẪN: [CẦN ĐIỀN HỌ TÊN GIẢNG VIÊN]',
        'NHÓM THỰC HIỆN: [CẦN ĐIỀN HỌ TÊN THÀNH VIÊN VÀ MÃ SỐ SINH VIÊN]',
        'NƠI VÀ NĂM NỘP: [CẦN ĐIỀN ĐỊA ĐIỂM], 2026',
        'Bản nghiên cứu phục vụ học phần, ngày 08/11/2026. Thời gian được mô phỏng: 01/2024–12/2025. Tên sách, tác giả, nhà xuất bản, kênh bán và toàn bộ giao dịch đều giả lập. Không sử dụng dữ liệu giao dịch của doanh nghiệp hay khách hàng thật.',
        f'Tóm tắt. Đề tài xây dựng {f(p["n_lines"])} đơn một đầu sách từ danh mục {f(p["n_books"])} sách giả lập, chủ động thêm lỗi để tạo {f(len(raw))} dòng thô. Quy trình chuẩn hóa, đối chiếu danh mục và xử lý mã dòng thu được {f(m["lines"])} dòng phân tích, ghi nhận {f(m["books"])} mã sách duy nhất (gồm {f(p["n_books"])} mã thuộc danh mục chuẩn và 1 mã BK9999 cho các bản ghi ngoài danh mục, tương ứng {f(len(t["books"]))} đầu sách phân biệt theo cặp mã–tên). Đối chiếu tập giữ lại cho thấy ba trường thuộc tính danh mục khớp 100% dữ liệu chuẩn, các trường giao dịch khớp từ 99,75% đến 99,98% do một số lỗi giá trị lọt lưới; giá trị bán hàng toàn kỳ chênh lệch +{f(v["relative_revenue_error_pct"],3)}% do tác động đồng thời của lỗi giá trị còn sót làm tăng tổng và việc cách ly giao dịch làm giảm tổng.',
        f'Kết quả mô tả của kịch bản cơ sở: {revenue} đồng giá trị bán hàng, {f(m["quantity"])} cuốn trên {f(m["books"])} mã sách xuất hiện trong giao dịch ({f(p["n_books"])} mã danh mục và mã ngoài danh mục BK9999). Ba kịch bản được lặp {exp.seed.nunique()} lần để xem kết quả thay đổi khi bỏ hệ số khuyến mãi hoặc mùa vụ. Các khác biệt thu được chỉ đánh giá hành vi mô hình dưới giả định, không xác nhận quy luật thị trường Việt Nam.',
        'Đóng góp thực hành là một quy trình có thể chạy lại: dữ liệu thô và chuẩn tách biệt; quy tắc làm sạch có nhật ký; số liệu báo cáo lấy từ bảng kết quả; biểu đồ, dashboard và notebook dùng chung hàm phân tích. Nhóm cần bổ sung thông tin bìa học phần và kiểm tra hiểu biết trước khi nộp.',
        'Từ khóa: kinh doanh sách; dữ liệu mô phỏng; chất lượng dữ liệu; phân tích khám phá; tái lập; phân tích độ nhạy.',
        '[[Bảng:Tóm tắt nghiên cứu]] tóm tắt các chỉ tiêu cơ sở của kịch bản chính; mọi giá trị trong bảng được lấy trực tiếp từ kết quả pipeline, không chép tay.',
    ],table=[['Chỉ tiêu cơ sở','Giá trị'],['Dòng thô / dòng giữ lại',f'{f(len(raw))} / {f(m["lines"])}'],['Mã sách trong tập sạch',f'{f(m["books"])} mã ({f(p["n_books"])} mã danh mục + 1 mã ngoài danh mục BK9999)'],['Giá trị bán hàng',revenue+' đồng'],['Sai lệch so với toàn bộ dữ liệu chuẩn',f'+{f(v["relative_revenue_error_pct"],3)}% (lỗi còn sót + cách ly)']],
      caption='Tóm tắt các chỉ tiêu cơ sở của kịch bản chính')
    section('1. Bài toán, câu hỏi và thiết kế nghiên cứu',[
        'Bối cảnh thực hành là một nhà sách giả định cần hiểu cơ cấu sản phẩm, kênh bán và thời điểm phát sinh giá trị bán hàng, đồng thời kiểm soát lỗi trong dữ liệu nhập từ nhiều nguồn. Bài không có mẫu xác suất từ thị trường nên không đặt mục tiêu ước lượng thị phần, lợi nhuận hay hành vi độc giả thực.',
        'Bảy câu hỏi mô tả: (1) thể loại nào đóng góp nhiều giá trị và số cuốn; (2) mã sách nào có giá trị bán hàng cao; (3) giá trị thay đổi theo tháng ra sao; (4) mức giá, giảm giá và lượng có quan hệ gì; (5) điểm giả lập có liên hệ với lượng ở cấp sách không; (6) cấu trúc tương quan giữa các biến ra sao; (7) cơ cấu theo kênh và phân khúc giá như thế nào. Câu hỏi kiểm chứng bổ sung: làm sạch sửa đúng đến đâu, mất bao nhiêu dữ liệu, và kết quả phụ thuộc giả định ra sao?',
        'Thiết kế tham khảo cấu trúc ADEMP (Morris và cộng sự, 2019), áp dụng ở mức phù hợp học phần: mục tiêu, cơ chế sinh, đại lượng cần tính, phương pháp và tiêu chí đánh giá. Đây là vận dụng khung báo cáo thí nghiệm mô phỏng, không phải nghiên cứu đề xuất phương pháp thống kê mới.',
        'Đơn vị dữ liệu là dòng đơn hàng một đầu sách. Mỗi mã đơn chỉ có một mã dòng trong mô hình này; số cuốn có thể lớn hơn 1. Không mô phỏng khách hàng, đơn nhiều đầu sách, chi phí, tồn kho, hoàn/hủy hoặc phễu chuyển đổi. Vì vậy không tính CAC, tỷ lệ mua lại, tỷ lệ bỏ giỏ hoặc lợi nhuận.',
        'Đại lượng chính là tổng giá trị bán hàng T = tổng(giá bán × số cuốn). Giá bình quân theo cuốn = T / tổng số cuốn. Tỷ trọng nhóm = giá trị nhóm / T. Tăng trưởng mô phỏng năm 2025 = (T2025 / T2024 − 1) × 100%. Những đại lượng này đều mô tả tập dữ liệu, không ước lượng tổng thể thị trường.'
    ],table=[['Thành phần','Thiết kế đã thực hiện'],['Mục tiêu','EDA và đánh giá quy trình sửa lỗi'],['Cơ chế sinh','Danh mục + dòng bán + lỗi có nhãn'],['Đối tượng đánh giá',f'Dòng giữ lại và toàn bộ {f(p["n_lines"])} dòng chuẩn'],['Phương pháp','Chuẩn hóa, tra danh mục, cách ly xung đột'],['Tiêu chí','Khớp trường, tỷ lệ giữ, sai lệch tổng, MCSE']],
      caption='Bốn thành phần thiết kế nghiên cứu')
    section('2. Nguồn gốc dữ liệu và giả định',[
        'Nguồn trực tiếp là src/data_generator.py. Không có dữ liệu được crawl hoặc mua từ các sàn. Các danh tính đều dùng nhãn giả lập để tránh ghép sai tác giả và nhà xuất bản vào tên sách có thật. Tài liệu tham khảo cung cấp cơ sở phương pháp; không được dùng để gán tính đại diện thị trường cho các tham số.',
        f'Danh mục gồm {f(p["n_books"])} mã sách, {f(per_genre)} mã cho mỗi thể loại. Năm xuất bản giả lập nằm trong {p["catalog_year_min"]}–{p["catalog_year_max"]} để luôn trước kỳ bán. Giá gốc được sinh từ phân phối log-normal với trung vị {f(p["price_median"])}, độ lệch chuẩn log {f(p["price_log_sd"],2)}, làm tròn nghìn và chặn trong {f(p["price_min"])}–{f(p["price_max"])} đồng. Điểm sách = 1 + 4 × Beta({f(p["rating_beta_a"])},{f(p["rating_beta_b"])}), làm tròn 0,1; đây là thuộc tính giả lập cố định trước kỳ bán, không phải đánh giá tổng hợp cuối kỳ.',
        f'Thể loại được chọn theo trọng số [{"; ".join(f(w,2) for w in p["genre_weights"])}] theo thứ tự trong config.py. Kênh Sàn A/B/C, Cửa hàng, Website có trọng số [{"; ".join(f(w,2) for w in p["channel_weights"])}]. Các giá trị là giả định thiết kế, chưa hiệu chỉnh theo dữ liệu thực.',
        f'Ngày bán được chọn đều trên {f(ndays)} ngày của 2024–2025. Giảm giá niêm yết chọn đều từ {{0,5,…,40}}% cho ba sàn và {{0,5,…,20}}% cho hai kênh còn lại. Giá bán làm tròn đến nghìn từ giá gốc và giảm giá; tỷ lệ giảm thực tế được tính riêng để không nhầm với mức niêm yết.',
        f'Số cuốn = 1 + Poisson(λ), trong đó λ = {f(p["lam_base"],1)} × S × max(0,5; 1,8 − giá_bán/{f(p["lam_price_scale"])}) × (1 + β × giảm_giá_niêm_yết/30). Cơ sở: β=1; S={f(p["season_peak"],1)} tháng 11–12, S={f(p["season_shoulder"],1)} tháng 8–9, còn lại S=1. {f(p["n_bulk"]).capitalize()} dòng mua số lượng lớn {f(p["bulk_qty_min"])}–{f(p["bulk_qty_max"])} cuốn được thêm độc lập để kiểm tra xử lý ngoại lệ. Đây không phải mô hình đã được xác thực dự báo kinh doanh.',
        'Tính truy xuất: catalog.csv là danh mục nghiệp vụ đầu vào; ground_truth.csv chỉ dành cho đánh giá. injected_errors.csv mô tả lỗi đã cài; hàm làm sạch không đọc hai tệp kiểm chứng này. SHA-256 của tệp đầu ra được lưu trong manifest.json. Việc ghi metadata và nguồn gốc tham khảo nguyên tắc tái sử dụng dữ liệu (GO FAIR Foundation, n.d.).'
    ])
    section('3. Quy trình làm sạch và quyết định xử lý',[
        'Bước 1: ghi nhận số dòng, thiếu và khóa lặp. Bước 2: chuẩn hóa khoảng trắng, thể loại, kiểu số và tiền tệ. Giá âm/thiếu được phục hồi từ giá gốc và giảm giá niêm yết, sử dụng cùng quy tắc làm tròn nghìn của hệ thống giả lập. Cách sửa này chỉ hợp lệ nếu hai trường cơ sở đáng tin.',
        'Các thuộc tính sách thiếu được tra bằng ma_sach trong catalog.csv, một đầu vào độc lập với nhãn lỗi. Bài giả định danh mục đã kiểm tra và bao phủ đủ mã trong kịch bản chính; giả định mạnh này làm bài toán phục hồi dễ hơn thực tế. Nếu không có dữ liệu tra, giữ điểm/năm ở trạng thái thiếu và gắn nhãn không rõ cho tên tác giả/NXB, không tự suy đoán thông tin thư mục.',
        'Bước 3: gộp các bản sao có cùng mã dòng và cùng nội dung sau chuẩn hóa. Nếu cùng mã nhưng khác dữ liệu, cách ly tất cả biến thể để xác minh. Không dùng tên sách/ngày/kênh làm khóa thay thế vì các giao dịch độc lập có thể trùng thuộc tính.',
        f'Bước 4: cách ly số lượng không dương, không nguyên hoặc trên {f(p["max_qty_review"])}, ngày sai, miền giá trị sai. Ngưỡng {f(p["max_qty_review"])} là quy tắc cần rà soát trong kịch bản, không phải quy luật bán lẻ. Điểm vượt Q3+1,5×IQR chỉ được đánh dấu, không tự xóa (NIST/SEMATECH, 2012); nhờ vậy các dòng mua nhiều vẫn được giữ nếu hợp lệ.',
        'Tạo đặc trưng dùng một hàm chung: giá <80.000; 80.000≤giá≤200.000; giá>200.000. Điểm: <3,0; [3,0;4,0); [4,0;4,5); ≥4,5; thiếu thành Chưa biết. Quy ước biên được kiểm tra riêng vì pandas.cut mặc định đóng khoảng bên phải (The pandas development team, 2024). Nhật ký cell_changes ghi thay đổi ô; row_lineage cho biết trạng thái của từng dòng thô.',
        '[[Bảng:3.2 Quy trình làm sạch]] trình bày số dòng, số ô thiếu và số mã dòng lặp sau từng bước; cột ô thiếu cho thấy dữ liệu thiếu được khôi phục hoặc cách ly ở bước nào.',
    ],table=[['Bước','Dòng','Ô thiếu','Mã dòng lặp']]+[[r.buoc.split('. ',1)[-1],f(r.so_dong),f(r.o_thieu),f(r.ma_dong_lap)] for r in stages.itertuples()],
      caption='Số dòng, ô thiếu và mã dòng lặp qua từng bước làm sạch')
    section('4. Kiểm chứng chất lượng: đúng và đủ là hai tiêu chí',[
        f'Trên {f(m["lines"])} mã dòng giữ lại, đối chiếu tám trường với dữ liệu chuẩn cho thấy ba trường thuộc tính danh mục đạt tỷ lệ khớp 100%: điểm đánh giá, năm xuất bản và nhà xuất bản. Trường tác giả đạt 99,98% ({f(recovery.loc[recovery.cot=="tac_gia","so_khop"].iloc[0])}/{f(m["lines"])}), thể loại đạt 99,92% ({f(recovery.loc[recovery.cot=="the_loai","so_khop"].iloc[0])}/{f(m["lines"])}). Các trường giao dịch gồm giá bán ({f(recovery.loc[recovery.cot=="gia_ban","so_khop"].iloc[0])}/{f(m["lines"])}), số lượng ({f(recovery.loc[recovery.cot=="so_luong","so_khop"].iloc[0])}/{f(m["lines"])}) và giá trị bán hàng ({f(recovery.loc[recovery.cot=="doanh_thu","so_khop"].iloc[0])}/{f(m["lines"])}) đạt tỷ lệ khớp từ 99,75% đến 99,91%, do một số lỗi giá trị lọt lưới vẫn để lại sai lệch trên các dòng giữ lại. Kết quả chi tiết ở [[Bảng:3.3 Đánh giá chất lượng sau xử lý]].',
        f'Có {f(len(q))} dòng nguồn bị cách ly, tương ứng {f(q.ma_dong.nunique())} mã dòng nghiệp vụ. {f(p["n_conflicts"]).capitalize()} mã xung đột có hai biến thể mỗi mã. Tỷ lệ giữ lại trên {f(p["n_lines"])} mã gốc là {f(v["retained_pct"],3)}%.',
        f'Độ chính xác của cách ly đạt {f(v["quarantine_precision"]*100,1)}%: mọi dòng bị cách ly đều thực sự mang lỗi. Về độ phủ phát hiện, cần phân biệt rõ hai cấp độ đánh giá: trên tổng số các dòng có lỗi hoặc cần chuẩn hóa ban đầu, phần lớn lỗi định dạng và ô thiếu đã được khôi phục chính xác tại chỗ; riêng trên {f(int(families.n_cai.sum()))} dòng thuộc tám họ lỗi giá trị và vi phạm nghiệp vụ, quy trình cách ly {f(int(families.n_cach_ly.sum()))} dòng ({f(100*families.n_cach_ly.sum()/families.n_cai.sum(),1)}%) và gắn cờ cảnh báo {f(int(families.n_danh_dau.sum()))} dòng ({f(100*families.n_danh_dau.sum()/families.n_cai.sum(),1)}%), đạt tổng tỷ lệ phát hiện {f(100*(families.n_cach_ly.sum()+families.n_danh_dau.sum())/families.n_cai.sum(),1)}%. Có {f(int(families.con_sai.sum()))} dòng mang lỗi giá trị ({f(100*families.con_sai.sum()/families.n_cai.sum(),1)}%) lọt vào tập sạch và còn sai khác dữ liệu chuẩn.',
        '[[Bảng:3.4 Hiệu năng phát hiện theo họ lỗi]] tách kết quả theo từng họ. Quy tắc miền giá trị bắt được lỗi số lượng âm, số lượng không nguyên và phát hiện mã sách ngoài danh mục để gắn cờ. Nó không thể phát hiện lỗi vẫn nằm trong miền hợp lệ: giá bị đặt lại bằng giá gốc, giá bị hoán vị giữa hai dòng, ngày bị đảo, và thể loại sai nhưng hợp lệ. Với các họ đó, cột còn sai đo mức độ ảnh hưởng thực tế thay vì che nó bằng một tỷ lệ phát hiện cao.',
        f'Tổng chuẩn là {f(v["truth_revenue"])} đồng; tập sạch có {revenue} đồng, chênh lệch +{f(v["relative_revenue_error_pct"],3)}% (+{f(v["clean_revenue"]-v["truth_revenue"])} đồng). Sự chênh lệch này là kết quả ròng của hai tác động ngược chiều: các lỗi giá trị còn sót làm tăng doanh thu trên tập giữ lại thêm +{f(v["retained_revenue_error"])} đồng; ngược lại, việc cách ly {f(q.ma_dong.nunique())} mã dòng nghiệp vụ làm giảm một phần doanh thu (khoảng {f(v["truth_revenue"] - (v["clean_revenue"] - v["retained_revenue_error"]))} đồng). Hiệu ứng lỗi sót vượt trội khiến doanh thu tập sạch cao hơn dữ liệu chuẩn; cần tách bạch hai tác động này thay vì quy giản cho riêng việc cách ly.',
        f'Có {f(m["iqr_flags"])} dòng bị gắn cờ IQR, gồm cả trường hợp lượng cao hợp lệ. Cần phân biệt kiểm tra hợp lệ theo miền dữ liệu với đánh giá hiếm gặp theo phân phối. Không dùng tỷ lệ ô thiếu bằng 0 làm thước đo duy nhất của chất lượng.',
        'Mỗi dòng thô phải có đúng một trạng thái cuối: giữ, gộp bản sao hoặc cách ly. Các kiểm tra tự động còn bao phủ giá trị biên, mâu thuẫn khóa, dữ liệu thiếu danh mục, dòng mua nhiều, các tổng theo nhóm và tái lập cùng seed. Các kết quả thí nghiệm không thay cho xác nhận độc lập của giảng viên.',
        '[[Bảng:3.3 Đánh giá chất lượng sau xử lý]] đối chiếu từng trường với dữ liệu chuẩn trên tập giữ lại; cột thứ hai là số ô khớp trên số ô so sánh.',
    ],table=[['Trường kiểm chứng','Khớp / đối chiếu']]+[[r.cot,f'{f(r.so_khop)} / {f(r.so_so_sanh)}'] for r in recovery.itertuples()],
      caption='Đối chiếu tám trường với dữ liệu chuẩn trên tập giữ lại')
    section('4.1 Hiệu năng phát hiện theo họ lỗi',[
        'Một tỷ lệ phát hiện gộp không cho biết quy tắc làm sạch mạnh ở đâu và yếu ở đâu. Tám họ lỗi dưới đây được cài với số lượng ngẫu nhiên theo phân phối Poisson, nên số lỗi mỗi lần chạy cũng là biến ngẫu nhiên. Nhờ vậy tỷ lệ giữ lại có sai số thực thay vì là một hằng số thiết kế.',
        'Cột tỷ lệ phát hiện là tổng số dòng được phát hiện (bị cách ly hoặc gắn cờ cảnh báo) chia số dòng mang lỗi. Cột còn sai là số dòng mang lỗi vẫn nằm trong tập sạch và vẫn khác dữ liệu chuẩn; đây là thước đo thiệt hại thật, vì một dòng có thể được phát hiện nhưng không thể tự khôi phục dữ liệu gốc.',
        'Bốn họ không thể phát hiện bằng miền giá trị là lỗi bản chất của dữ liệu, không phải thiếu sót của mã: giá bị đặt lại bằng giá gốc, giá bị hoán vị, ngày bị đảo và thể loại sai đều tạo ra giá trị hợp lệ. Riêng họ lỗi catalog_missing (mã sách ngoài danh mục) được phát hiện 100% nhờ kiểm tra tính toàn vẹn tham chiếu và gắn cờ cảnh báo (6 dòng), nhưng pipeline không cách ly nhằm bảo toàn giao dịch doanh thu hợp lệ, và vì không thể tự suy đoán mã sách nên cả 6 dòng vẫn còn sai khác dữ liệu chuẩn. Chỉ dữ liệu đối chiếu bên ngoài hoặc kiểm tra chéo nguồn mới khôi phục được các giá trị này.',
        '[[Hình:3.4 Hiệu năng phát hiện theo họ lỗi]] xếp các họ theo tỷ lệ phát hiện, tô màu theo khả năng phát hiện. [[Bảng:3.4 Hiệu năng phát hiện theo họ lỗi]] ghi số lượng cài, số cách ly, số gắn cờ, tỷ lệ phát hiện và số dòng còn sai cho từng họ.',
    ],'09_error_family.png',table=[['Họ lỗi','Số dòng','Cách ly','Gắn cờ','Tỷ lệ phát hiện','Còn sai','Khả năng phát hiện']]+[[r.ho_loi,f(r.n_cai),f(r.n_cach_ly),f(r.n_danh_dau),f(r.recall*100,0)+'%',f(r.con_sai),r.phat_hien_duoc] for r in families.itertuples()],
      caption='Hiệu năng phát hiện của quy trình làm sạch theo từng họ lỗi được cài') 
    top=t['genre'].iloc[0]
    section('5. Thể loại và cơ cấu giá trị bán hàng',[
        f'Trong kịch bản cơ sở, {top.the_loai} dẫn đầu giá trị bán hàng với {f(top.doanh_thu)} đồng, chiếm {f(top.ty_trong,2)}%; lượng bán là {f(top.so_luong)} cuốn. Đây là tổng hợp trên tập sạch gồm {f(m["lines"])} dòng. [[Hình:4.1 Cơ cấu theo thể loại]] tách hai thước đo để không so chiều cao cột ở các đơn vị khác nhau.',
        'Khác biệt giữa các thể loại đến từ trọng số chọn sách đã thiết lập, danh mục giá và lượng mua ngẫu nhiên. Một nhóm đóng góp nhiều không chứng minh nhu cầu thị trường lớn hơn hoặc nên được nhập thêm; muốn đưa ra quyết định nhập hàng cần thêm tồn kho, vòng quay, chi phí và dữ liệu thực.',
        'Ứng dụng thực hành là theo dõi sự tập trung của giá trị bán hàng và xác định nhóm cần phân tích sâu. Khi triển khai ở nhà sách thật, cần kiểm tra khả năng thiếu đơn theo kênh, khác biệt danh mục và chính sách phân loại trước khi so sánh.'
    ],'01_genre.png',caption='Giá trị bán hàng và số cuốn theo thể loại trong kịch bản cơ sở; hai thước đo dùng trục riêng')
    topb=t['books'].iloc[0]
    section('6. Danh mục sách và cách đọc xếp hạng',[
        f'Mã {topb.ma_sach} có giá trị bán hàng cao nhất trong kịch bản cơ sở: {f(topb.doanh_thu)} đồng, {f(topb.so_luong)} cuốn trên {f(topb.so_dong)} dòng. Danh sách xếp hạng được nhóm theo mã sách và tên giả lập, không gộp bằng tên mơ hồ hoặc tách một mã vì ô tác giả bị thiếu.',
        'Sách đứng đầu có thể chịu ảnh hưởng của vài dòng mua số lượng lớn; nên xem đồng thời số dòng, tổng cuốn và giá trị, thay vì chỉ dùng một chỉ tiêu. Danh sách này chỉ phục vụ minh họa quy trình phân tích danh mục, không đánh giá tác phẩm hoặc cá nhân ngoài đời.',
        'Bảng đầy đủ theo tác giả và NXB giả lập nằm trong results/author.csv và publisher.csv. Không chọn các tên ngẫu nhiên để đưa ra kiến nghị ký bản quyền hoặc khẳng định uy tín. Các bảng này có giá trị kiểm tra phép nhóm và đối soát tổng.',
        '[[Hình:4.2 Phân tích danh mục sách]] xếp mười mã sách theo giá trị bán hàng; đọc kèm số dòng và số cuốn để nhận biết ảnh hưởng của dòng mua nhiều.'
    ],'02_books.png',caption='Mười mã sách giả lập có giá trị bán hàng cao nhất trong tập sạch')
    mm=t['month'];peak=mm.loc[mm.doanh_thu.idxmax()];low=mm.loc[mm.doanh_thu.idxmin()]
    section('7. Diễn biến thời gian trong kịch bản',[
        f'Tháng cao nhất là {peak.thang_nam}: {f(peak.doanh_thu)} đồng; thấp nhất {low.thang_nam}: {f(low.doanh_thu)} đồng. Chênh lệch đỉnh so với đáy = {f((peak.doanh_thu/low.doanh_thu-1)*100,2)}%. Tăng trưởng năm 2025 so với 2024 trong dữ liệu là {f(m["yoy_pct"],2)}%; mô hình không cài xu hướng tăng trưởng riêng theo năm nên không diễn giải con số này thành tốc độ tăng trưởng thị trường.',
        'Mùa vụ tháng 8–9 và 11–12 được chủ động cài vào λ. Biểu đồ cho thấy kết quả tổng hợp của cơ chế này cùng nhiễu ngẫu nhiên, số ngày/tháng và các đơn mua nhiều. Hai năm mô phỏng không đủ để xác nhận tính ổn định của mùa vụ thực.',
        'Ứng dụng là cách xây dựng bảng theo thời gian và chuẩn bị giả thuyết để kiểm tra ở dữ liệu thật. Cần nhiều chu kỳ, lịch khuyến mãi thực, số ngày hoạt động và mức tồn kho trước khi lập dự báo nhập hàng. Bài không đưa ra dự báo Prophet/SARIMAX khi chưa có thiết kế đánh giá ngoài mẫu.',
        '[[Hình:4.3 Phân tích theo thời gian]] đặt giá trị bán hàng và số cuốn theo tháng trên hai trục riêng để thấy cả quy mô giá trị và khối lượng.'
    ],'03_month.png',caption='Giá trị bán hàng và số cuốn theo tháng trong kịch bản cơ sở')
    section('8. Giá, giảm giá và lượng bán',[
        f'Tương quan Pearson theo dòng giữa giảm giá thực tế và lượng là {f(m["discount_qty_r"],3)}. [[Hình:4.4 Giá và giảm giá]] dùng boxplot với thang log ở trục lượng để hiển thị cả giao dịch nhỏ và dòng mua nhiều; các nhóm được xác định bằng giảm giá niêm yết, còn hệ số tương quan dùng mức thực tế sau làm tròn.',
        'Cơ chế sinh lượng chứa cả giá bán và mức giảm. Do đó quan hệ quan sát được một phần đã nằm trong công thức; không thể dùng nó để chứng minh khách hàng phản ứng với nhãn giảm giá hay xác định mức chiết khấu tối ưu. Khác biệt kênh và giá gốc cũng có thể làm thay đổi cấu trúc các nhóm.',
        'Nếu muốn nghiên cứu tác động khuyến mãi trên dữ liệu thực, cần dữ liệu tiếp xúc/đơn hàng theo thời gian, cách chọn nhóm so sánh, yếu tố gây nhiễu và tốt nhất là thí nghiệm có thiết kế phù hợp. Muốn tối ưu lợi nhuận phải có chi phí; tổng doanh thu và tổng lượng không thay được biên lợi nhuận.'
    ],'04_discount.png',caption='Phân phối số cuốn mỗi dòng theo nhóm giảm giá niêm yết (thang log) và mật độ giá bán – lượng bán')
    section('9. Điểm sách và tổng lượng ở cấp mã sách',[
        f'Điểm là thuộc tính giả lập cố định của sách. Vì một sách có nhiều dòng, hình chính tổng hợp lên cấp sách theo cặp mã sách và tên sách (gồm {f(p["n_books"])} sách danh mục và 6 đầu sách mang mã ngoài danh mục BK9999, tổng cộng {f(len(t["books"]))} đầu sách phân biệt, ứng với {f(m["books"])} mã sách duy nhất). Pearson giữa điểm và tổng cuốn ở cấp sách là {f(m["rating_book_qty_r"],3)}; hệ số ở cấp dòng là {f(m["rating_qty_r"],3)}. Hai giá trị trả lời hai câu hỏi khác nhau, không thể thay thế tùy ý. Chúng cũng không được tính trên cùng một đơn vị: hệ số cấp sách gộp theo cặp mã sách và tên sách, vì các dòng không tra được mã sách mang khóa thay thế BK9999 và nếu chỉ gộp theo mã thì nhiều sách khác nhau bị nhập thành một.',
        'Điểm được sinh độc lập với cơ chế chọn sách và lượng, nên tương quan ở cấp quần thể bằng 0 theo thiết kế. Giá trị quan sát ở một seed vì thế chỉ là một lần rút từ phân phối null, không phải một phát hiện. Để kiểm chứng, dữ liệu được sinh lại qua nhiều seed và tính lại cùng hệ số; kết quả ở [[Bảng:4.6 Kiểm chứng bằng phân phối null]].',
        f'Qua {f(len(null))} seed, hệ số cấp sách có trung bình {f(nullstats.set_index("metric").loc["rating_book_qty_r","mean"],3)} và độ lệch chuẩn {f(nullstats.set_index("metric").loc["rating_book_qty_r","sd"],3)}; khoảng 95% thực nghiệm là [{f(nullstats.set_index("metric").loc["rating_book_qty_r","p025"],3)}; {f(nullstats.set_index("metric").loc["rating_book_qty_r","p975"],3)}]. Giá trị của kịch bản cơ sở là {f(m["rating_book_qty_r"],3)}, tức phân vị thứ {f(100*(null["rating_book_qty_r"].dropna()<m["rating_book_qty_r"]).mean(),1)} của phân phối null. Giá trị này nằm {_inside_band(null,"rating_book_qty_r",m["rating_book_qty_r"])} khoảng 95%.',
        f'Cách đọc đúng là {_band_verdict(null,"rating_book_qty_r",m["rating_book_qty_r"])}. Điều không được làm là suy ra một quan hệ thị trường: điểm đánh giá được sinh độc lập với lượng trong mô hình, nên ở cấp quần thể tương quan bằng 0 theo thiết kế. Một giá trị nằm trong khoảng null nghĩa là nó tương thích với chính tính ngẫu nhiên của mô hình, và bài không được biến nó thành phát hiện.',
        'Vị trí trong khoảng không phải phép thử duy nhất cần báo cáo. Một giá trị ở phân vị 96,5 nằm trong khoảng trung tâm 95% nhưng vẫn ở vùng đuôi, nên bài ghi cả hai thông tin thay vì chỉ chọn một kết luận nhị phân. Với 200 seed, bản thân các phân vị thực nghiệm cũng có sai số, nên việc tuyên bố một giá trị "vừa ra ngoài" hay "vừa ở trong" là không đáng tin về mặt thống kê.',
        'Bản trước nêu một ngưỡng 1,5% mà không chứng minh, và một bản trung gian kết luận giá trị nằm ngoài khoảng. Cả hai đều sai ở chỗ khác nhau. Ngưỡng 1,5% là giả định không có cơ sở. Kết luận "nằm ngoài" đến từ việc tính phân vị trên một phép gộp sách khác với phép gộp dùng để tính giá trị quan sát: các dòng không tra được mã sách mang khóa thay thế BK9999, và gộp chỉ theo mã sách đã nhập nhiều sách khác nhau thành một. Khi hai bên dùng cùng một đơn vị, giá trị quan sát nằm trong khoảng. Đây là lý do phép kiểm chứng phải được tính lại chứ không được kế thừa kết luận từ bản trước.',
        'Không có lịch sử đánh giá, lượt xem, quảng cáo hoặc đo niềm tin để giải thích hành vi khách hàng.',
        f'Có {f(m["rating_known"])} dòng có điểm trong kịch bản đầy đủ danh mục; {f(m["good_rating_pct"],2)}% số dòng có điểm từ 4 trở lên. Đây là tỷ lệ dòng mang điểm sách giả lập, không phải tỷ lệ khách hàng hài lòng. Bài không tính p-value từ các dòng lặp của cùng sách.',
        '[[Hình:4.5 Điểm sách và lượng bán]] chấm từng mã sách theo điểm và tổng cuốn; hệ số in trên hình là tương quan cấp sách, không phải cấp dòng. [[Hình:4.6 Kiểm chứng bằng phân phối null]] đặt giá trị quan sát lên phân phối null để thấy nó nằm trong khoảng 95%, tương thích với phân phối ngẫu nhiên của mô hình và không phải một phát hiện thị trường.'
    ],'05_rating.png',caption='Điểm giả lập và tổng số cuốn ở cấp mã sách (n = số mã sách trong tập sạch)')
    section('9.1 Kiểm chứng bằng phân phối null',[
        f'Phân phối null được xây bằng cách sinh lại toàn bộ dữ liệu cho {f(len(null))} seed khác nhau, chạy lại quy trình làm sạch và tính cùng các hệ số. Đây không phải hoán vị nhãn trên một tập cố định: mỗi seed là một lần sinh độc lập theo đúng mô hình, nên phân phối thu được là phân phối của chính đại lượng dưới giả thuyết không của mô hình.',
        'Khoảng 95% là phân vị thực nghiệm 2,5% và 97,5% của phân phối đó. Nó không phải khoảng tin cậy cho một tham số thị trường, vì ở đây không có thị trường nào. Nó trả lời đúng một câu hỏi: với mô hình này, một giá trị như quan sát được có bình thường không.',
        'Cùng cách kiểm chứng được áp cho tương quan giảm giá – lượng. Hệ số này khác 0 một cách hệ thống vì mức giảm giá nằm trong công thức sinh lượng, nên phân phối null của nó lệch hẳn khỏi 0. Điều đó xác nhận phép kiểm chứng phân biệt được tín hiệu do thiết kế với nhiễu, thay vì luôn trả về cùng một kết luận.',
        '[[Hình:4.6 Kiểm chứng bằng phân phối null]] vẽ hai phân phối null cạnh nhau, kèm giá trị của kịch bản cơ sở và khoảng 95%. [[Bảng:4.6 Kiểm chứng bằng phân phối null]] ghi trung bình, độ lệch chuẩn và phân vị cho từng chỉ tiêu.'
    ],'10_null_band.png',table=[['Chỉ tiêu','Trung bình','Độ lệch chuẩn','Phân vị 2,5%','Phân vị 97,5%']]+[[r.metric,f(r['mean'],3),f(r.sd,3),f(r.p025,3),f(r.p975,3)] for _,r in nullstats.iterrows()],
      caption=f'Phân phối null của các chỉ tiêu tương quan qua {len(null)} seed độc lập')
    section('9.2 Khoảng bootstrap cho các chỉ tiêu chính',[
        f'Mỗi con số trong báo cáo được tính từ một mẫu cụ thể, nên câu hỏi tự nhiên là nó sẽ dịch chuyển bao nhiêu nếu mẫu khác đi một chút. Khoảng bootstrap trả lời câu hỏi đó bằng cách rút lại có hoàn lại từ chính tập sạch {f(int(boot.n_boot.max()))} lần và tính lại chỉ tiêu trên mỗi lần rút. Đây là phân vị thực nghiệm 2,5% và 97,5%, không dùng giả định phân phối chuẩn.',
        'Đơn vị rút lại khác nhau theo chỉ tiêu và khác biệt đó là phần quan trọng. Các chỉ tiêu ở cấp dòng rút lại theo dòng bán hàng. Riêng tương quan điểm–lượng ở cấp sách rút lại theo đầu sách, vì nó được tính trên một dòng cho mỗi sách: nếu rút theo dòng thì một sách có 40 giao dịch sẽ được tính như 40 quan sát độc lập và khoảng thu được hẹp hơn thực tế. Trong tập hiện tại có rất ít sách so với số dòng, nên hai cách rút cho ra hai khoảng rất khác nhau.',
        f'Ba loại khoảng xuất hiện trong bài và không được dùng thay nhau. Khoảng bootstrap ở mục này nói về độ chính xác của một ước lượng trên một mẫu. Khoảng null ở mục 9.1 nói về việc một giá trị có thể đến từ chính tính ngẫu nhiên của mô hình hay không. Phân bố giữa các kịch bản ở phần độ nhạy nói về việc kết quả đổi thế nào khi thay giả định. Cả ba đều không phải khoảng tin cậy cho một tham số thị trường, vì dữ liệu là mô phỏng và không có thị trường nào để suy diễn.',
        'Một hệ quả cần nêu rõ: khoảng hẹp không làm cho kết quả đúng hơn. Ở đây khoảng hẹp chỉ có nghĩa là mẫu mô phỏng lớn và ổn định. Sai lệch thật của nghiên cứu nằm ở chỗ khác, gồm giả định của mô hình sinh, quy tắc làm sạch và độ đầy đủ của danh mục; những nguồn đó không xuất hiện trong khoảng bootstrap và không được thu nhỏ bằng cách tăng số lần rút.',
        '[[Hình:4.7 Khoảng bootstrap cho các chỉ tiêu chính]] vẽ khoảng của ba chỉ tiêu đại diện cùng giá trị trên mẫu. [[Bảng:4.7 Khoảng bootstrap cho các chỉ tiêu chính]] ghi đầy đủ điểm ước lượng, độ lệch chuẩn bootstrap, hai đầu khoảng và đơn vị rút lại cho từng chỉ tiêu.'
    ],'13_bootstrap_ci.png',table=[['Chỉ tiêu','Đơn vị rút lại','Điểm ước lượng','Độ lệch chuẩn','Phân vị 2,5%','Phân vị 97,5%']]+[[r.metric,r.unit,f(r.point,3),f(r.boot_sd,3),f(r.ci_low,3),f(r.ci_high,3)] for _,r in boot.iterrows()],
      caption=f'Khoảng bootstrap 95% của các chỉ tiêu chính, {f(int(boot.n_boot.max()))} lần rút lại; đơn vị rút lại theo dòng bán hàng, riêng tương quan cấp sách theo đầu sách')
    section('10. Tương quan và biến được tính từ công thức',[
        'Ma trận [[Hình:4.6 Cấu trúc tương quan]] là mô tả Pearson ở cấp dòng, gồm cả dòng mua nhiều. Hệ số tuyến tính nhạy với những quan sát lớn, không bao quát mọi quan hệ phi tuyến. Kết quả ở cấp sách và phân tích bỏ dòng >150 cuốn được tách riêng, không thay đổi âm thầm tập quan sát.',
        'Giá trị bán hàng được định nghĩa bằng giá bán × số lượng; giảm giá thực tế được định nghĩa từ giá bán/giá gốc. Vì vậy nhiều ô tương quan xuất hiện từ chính quan hệ tính toán. Chúng không là bằng chứng độc lập để chọn chiến lược tăng giá hay tăng sản lượng.',
        'Các bảng số gốc results/correlation.csv và describe.csv cho phép kiểm tra hệ số và phân phối. Khi áp dụng cho dữ liệu thực, cần xác định thời điểm đo từng biến và cách gom quan sát phụ thuộc; không diễn giải tương quan thành nguyên nhân.'
    ],'06_correlation.png',caption='Ma trận tương quan Pearson ở cấp dòng bán hàng; các biến tính từ nhau có tương quan theo định nghĩa')
    section('11. Kênh và phân khúc giá',[
        f'Giá bình quân có trọng số theo cuốn là {f(m["average_unit_price"])} đồng; được tính từ tổng giá trị / tổng cuốn. [[Hình:4.7 Kênh bán và phân khúc giá]] dùng cùng mẫu số là toàn bộ {revenue} đồng trong tập sạch, bao gồm mọi kênh và phân khúc.',
        'Tỷ trọng kênh thể hiện xác suất chọn kênh, giảm giá và số lượng trong mô hình. Tỷ trọng cao không cho biết tốc độ tăng, chi phí thu hút khách, lợi nhuận hay mức dịch chuyển hành vi. Phân khúc giá đóng góp nhiều cũng không chứng minh giá tối ưu, vì số bản ghi và danh mục giá trong nhóm khác nhau.',
        'Dashboard có bộ lọc năm/kênh và tính lại KPI từ tập được chọn. Mỗi lần lọc thay đổi mẫu số; người dùng cần ghi rõ bộ lọc khi trích số. Dashboard chạy ngoại tuyến và không sử dụng chỉ số viết cố định như tăng trưởng hoặc mức hài lòng.'
    ],'07_composition.png',caption='Tỷ trọng giá trị bán hàng theo kênh giả lập và theo phân khúc giá bán')
    summary=exp.groupby('scenario',sort=False).agg(q4=('q4_share','mean'),r=('discount_qty_r_without_bulk','mean'),err=('revenue_error_pct','mean'))
    section('12. Phân tích độ nhạy và độ bất định mô phỏng',[
        f'Ba kịch bản dùng seed 100 đến {99+exp.seed.nunique()}: cơ sở; đặt β=0; đặt S=1 cho mọi tháng. Mỗi kịch bản có {exp.seed.nunique()} lần sinh độc lập theo seed. Đây là so sánh có ghép seed, không phải can thiệp ngẫu nhiên trên người mua thật. Quy mô được chọn để minh họa độ dao động và thời gian chạy phù hợp học phần; chưa tuyên bố hội tụ cho mọi chỉ tiêu.',
        'Kịch bản bỏ β chỉ loại đường tác động trực tiếp của phần trăm giảm giá lên λ; giá bán vẫn thay đổi khi giảm giá thay đổi, nên tương quan có thể còn lại. Kịch bản bỏ mùa vụ vẫn có số ngày/tháng không bằng nhau và nhiễu. Việc chỉ thay một giả định giúp giải thích nguồn của kết quả thay vì khẳng định tính bền vững chung.',
        'Tệp sensitivity_summary.csv lưu trung bình, độ lệch chuẩn giữa các lần chạy, MCSE = SD/√R và các phân vị thực nghiệm 2,5%–97,5%. MCSE đo độ chính xác Monte Carlo của trung bình trên mô hình này. Các phân vị không là khoảng tin cậy thị trường. Với 50 lần chạy, ước lượng đuôi còn thô; có thể tăng R bằng tham số lệnh.',
        f'Kết quả: r trung bình sau bỏ dòng >150 cuốn đổi từ {f(summary.loc["Cơ sở","r"],3)} ở cơ sở xuống {f(summary.loc["Không hệ số giảm giá","r"],3)} khi β=0. Tỷ trọng Q4 giảm từ {f(summary.loc["Cơ sở","q4"],2)}% xuống {f(summary.loc["Không mùa vụ","q4"],2)}% khi bỏ mùa vụ. [[Hình:5.1 Thí nghiệm thay đổi giả định]] chỉ loại dòng mua nhiều cho chỉ tiêu tương quan; báo cáo chính vẫn giữ các dòng hợp lệ. Kết quả cho thấy những nhận xét về giảm giá/mùa vụ phụ thuộc cơ chế sinh.',
        '[[Bảng:5.1 Thí nghiệm thay đổi giả định]] tổng hợp trung bình ba kịch bản theo ba chỉ tiêu; mỗi dòng là một kịch bản, không phải một lần chạy.',
    ],'08_sensitivity.png',table=[['Kịch bản','Q4 (%)','r (bỏ >150)','Sai lệch T (%)']]+[[s,f(r.q4,2),f(r.r,3),f(r.err,3)] for s,r in summary.iterrows()],
      caption='Trung bình ba kịch bản độ nhạy theo tỷ trọng quý IV, tương quan giảm giá – lượng và sai lệch tổng')
    section('13. Điền khuyết: lợi ích và giới hạn',[
        'Kịch bản chính khôi phục thuộc tính sách từ danh mục được giả định đáng tin. Đây là đối chiếu nghiệp vụ, không phải suy luận điểm đánh giá từ các giao dịch tương tự. Một thí nghiệm riêng loại bỏ thông tin tra cứu và che điểm đánh giá trên dữ liệu chuẩn, rồi so sánh bốn phương án xử lý.',
        f'Thí nghiệm có ba cơ chế thiếu, ba tỷ lệ che và bốn phương án, mỗi ô được lặp qua {f(int(missing.n_seeds.max()))} seed. Ba cơ chế cần thiết vì chúng hỏng theo cách khác nhau. MCAR che ngẫu nhiên nên bỏ qua được. MAR cho xác suất thiếu phụ thuộc giá bán, một biến quan sát được, nên điều kiện hóa theo biến đó có thể khôi phục trung bình. MNAR cho xác suất thiếu phụ thuộc chính điểm bị thiếu, nên mọi phương án điền đều bị kéo về phía trung bình của phần quan sát được và không phương án nào sửa được điều đó.',
        'MAE chỉ tính trên những ô bị che và được điền; phương án giữ thiếu không có MAE vì không tạo dự đoán. Giữ thiếu làm giảm độ bao phủ nhưng tránh gán độ chính xác giả. Điền trung bình đủ ô nhưng không khôi phục được khác biệt từng sách.',
        f'Kết quả chính: ở cùng tỷ lệ che, MAE của MNAR cao hơn MCAR một cách hệ thống, đúng như lý thuyết dự đoán. Chênh lệch giữa các phương án điền nhỏ hơn nhiều so với chênh lệch giữa các cơ chế thiếu. Vì vậy lựa chọn phương án điền là câu hỏi thứ yếu; câu hỏi chính là cơ chế thiếu có phụ thuộc vào giá trị bị thiếu hay không, và điều đó phải được kiểm tra bằng dữ liệu thật chứ không suy ra từ đây.',
        f'Mỗi ô có {f(int(missing.n_seeds.max()))} seed nên sai số chuẩn Monte Carlo của MAE trung bình được ghi trong cột mcse_mean. Với tỷ lệ che thấp, sai số này tương đối lớn so với chênh lệch giữa các phương án, nên không nên đọc thứ hạng phương án ở tỷ lệ 2% như một kết luận.',
        'Thử nghiệm tự động cũng cung cấp danh mục rỗng để đảm bảo chương trình giữ điểm thiếu và ghi không rõ tác giả thay vì tự bịa. Các cờ khoi_phuc_* đi cùng dữ liệu sạch giúp tách dữ liệu quan sát với dữ liệu được phục hồi.',
        '[[Hình:5.2 Thí nghiệm dữ liệu thiếu]] vẽ MAE theo tỷ lệ che cho từng cơ chế, mỗi đường là một phương án. [[Bảng:5.2 Thí nghiệm dữ liệu thiếu]] ghi MAE trung bình, độ lệch chuẩn và sai số chuẩn Monte Carlo cho từng ô.',
    ],'11_missing_mechanism.png',table=[['Cơ chế','Tỷ lệ che','Phương pháp','MAE','MCSE']]+[[r.mechanism,f(r.missing_rate*100,0)+'%',r.method,'Không áp dụng' if pd.isna(r.mae_mean) else f(r.mae_mean,3),'' if pd.isna(r.mcse_mean) else f(r.mcse_mean,3)] for r in missing.itertuples()],
      caption=f'MAE trên ô điểm đánh giá bị che theo cơ chế thiếu, tỷ lệ che và phương án xử lý ({int(missing.n_seeds.max())} seed mỗi ô)')
    section('13.1 Độ bao phủ danh mục như một giả định có thể đo',[
        'Báo cáo gọi danh mục đáng tin và đầy đủ là một giả định mạnh nhưng trước đây không đo được nó mạnh đến đâu. Thí nghiệm dưới đây che toàn bộ thuộc tính của một tỷ lệ mã sách trong danh mục, theo nguyên dòng chứ không theo ô, vì trong thực tế một cuốn sách hoặc có trong dữ liệu chủ hoặc không.',
        'Cách mô phỏng phải phản ánh đúng đường đi của dữ liệu. Trong một quy trình thật, tệp giao dịch chỉ mang mã sách, còn các thuộc tính mô tả đến từ phép nối với danh mục. Vì vậy khi một mã sách không có trong danh mục, dòng giao dịch của nó không có tên tác giả, nhà xuất bản hay điểm đánh giá. Thí nghiệm áp đúng hệ quả đó thay vì chỉ xóa thuộc tính trong danh mục, vì bản thân tệp giao dịch mô phỏng cũng mang sẵn bản sao các trường này.',
        'Kết quả không nhẹ như giả định ban đầu. Quy trình hiện cách ly mọi dòng có mã sách không tra được, vì không thể kiểm chứng một bản ghi mà danh mục không xác nhận. Vì vậy độ bao phủ danh mục không chỉ làm mất thuộc tính mô tả mà còn làm mất chính dòng giao dịch: ở mức bao phủ 50%, khoảng một nửa giá trị bán hàng biến khỏi tập phân tích. Đây là đánh đổi có chủ ý giữa tính kiểm chứng và độ đầy đủ, và nó cho thấy giả định danh mục đầy đủ chịu trách nhiệm cho phần lớn độ đầy đủ của toàn bộ kết quả.',
        'Một phương án khác là giữ dòng lại và ghi thuộc tính không rõ, đổi độ đầy đủ lấy tính kiểm chứng. Bài không chọn phương án đó cho kịch bản chính vì mọi kết luận theo thể loại, tác giả hay nhà xuất bản sẽ dựa trên nhãn không xác minh được. [[Hình:5.3 Độ bao phủ danh mục]] cho thấy hai hệ quả này tách nhau, và [[Bảng:5.3 Độ bao phủ danh mục]] ghi từng mức che kèm số dòng bị cách ly.',
    ],'12_catalog_coverage.png',table=[['Độ bao phủ','Dòng giữ lại','Bị cách ly (%)','Sai lệch giá trị (%)','Mã ngoài danh mục']]+[[f(r.catalog_coverage*100,0)+'%',f(r.lines),f(r.quarantined_pct,1),f(r.relative_revenue_error_pct,3),f(r.unknown_book_key)] for r in coverage.itertuples()],
      caption='Ảnh hưởng của độ bao phủ danh mục lên độ đầy đủ dòng và giá trị bán hàng; cột cuối là họ lỗi cài sẵn nên không đổi theo độ bao phủ')
    section('14. Ý nghĩa thực hành, hạn chế và kết luận',[
        'Ứng dụng có thể chuyển sang nhà sách thật là quy trình quản trị dữ liệu: dùng mã dòng ổn định; giữ danh mục sách đã xác minh; tách dữ liệu nguồn và dữ liệu xử lý; cách ly thay vì xóa mất dấu; đối soát tổng; công khai bộ lọc và mẫu số. Các bảng EDA có thể hỗ trợ hình thành câu hỏi về danh mục, kênh và thời điểm, sau đó kiểm tra bằng dữ liệu kinh doanh thực.',
        'Không có căn cứ trong bài để cắt tồn kho 40%, dồn ngân sách 70%, cam kết lợi nhuận 15% hay dự báo tăng trưởng 40%. Nếu cần các quyết định này, nhóm phải thu thập tồn kho, giá vốn, phí, quảng cáo, hủy/hoàn và dữ liệu khách hàng được phép sử dụng; đồng thời xác định thiết kế đánh giá phù hợp.',
        'Hạn chế chính: mọi tham số chưa hiệu chỉnh; danh mục hoàn toàn giả lập; chỉ một loại đơn một đầu sách; chỉ 300 sách và 2 năm; lỗi cài vẫn do tác giả thiết kế nên chưa chứng minh hiệu năng trên lỗi chưa biết; danh mục chuẩn đáng tin là giả định mạnh và nay đã đo được ảnh hưởng của nó; thiếu ngẫu nhiên được mô phỏng theo ba cơ chế nhưng vẫn là giả định về cơ chế; số lần mô phỏng chưa đủ để khảo sát mọi trường hợp; không đo ngoại lực và chi phí.',
        'Một hạn chế cần nói rõ vì nó là kết quả, không phải sơ suất: khoảng 65,3% số lỗi giá trị được cài (32/49 dòng mang lỗi) vẫn nằm lại trong tập phân tích. Các họ lỗi tạo ra giá trị hợp lệ như giá bị đặt lại bằng giá gốc, giá bị hoán vị, ngày bị đảo và thể loại sai không thể phát hiện bằng miền giá trị, và bài không dựng quy tắc đọc dữ liệu chuẩn để xóa chúng. Vì vậy tổng giá trị bán hàng trong kịch bản cơ sở cao hơn dữ liệu chuẩn khoảng +2,992% (+89.125.000 đồng). Con số đó được công bố minh bạch và phân tích rõ nguồn gốc.',
        'Kết luận: bài hoàn thành chu trình xây dựng, xử lý, EDA và trực quan hóa trên dữ liệu mô phỏng, có đối soát bằng dữ liệu chuẩn và đánh giá ảnh hưởng của loại bản ghi. Kết quả cho thấy các trường thuộc tính danh mục có thể phục hồi chính xác trên tập giữ lại, nhưng tổng giá trị bán hàng bị tác động bởi cả lỗi giá trị còn sót làm tăng doanh thu và việc cách ly giao dịch làm giảm số lượng bản ghi. Ý nghĩa khoa học nằm ở tính kiểm chứng và việc nhận biết giới hạn, không ở khẳng định một quy luật thị trường mới.',
        'Hướng tiếp theo hợp lý là lấy một bộ giao dịch ẩn danh có quyền sử dụng từ nhà sách, xác minh danh mục và so sánh phân phối với mô hình. Chỉ sau đó mới hiệu chỉnh tham số hoặc đề xuất dự báo; nếu không có dữ liệu thật, mở rộng các cơ chế lỗi và số lần mô phỏng, công khai chúng là thí nghiệm giả lập.',
        'Trách nhiệm nhóm: điền thông tin học phần, thành viên và đóng góp có thật; đọc và chạy lại notebook; có thể giải thích các giả định và giới hạn; khai báo hỗ trợ AI theo yêu cầu của lớp. Bản này không xác nhận một khảo sát doanh nghiệp hoặc thu thập thị trường chưa từng diễn ra.'
    ])
    section('Tài liệu tham khảo và chỉ dẫn tái lập',[
        *[title for title,url in SOURCES],
        'Nguồn sơ cấp của mọi con số mới: data/processed/book_sales_clean.csv, results/*.csv và results/metrics.json. Mã sinh và nhãn lỗi: src/data_generator.py, data/reference/ground_truth.csv, data/audit/injected_errors.csv. Nguồn cũ để truy xuất thay đổi: Kohaku1709/Kinh-doanh-sach-, commit 6bfe691904b4d721ee1a1743509f6b581b70ce81; các kết quả cũ không được sử dụng như số liệu của bản nghiên cứu mới.',
        'Tái lập: Python 3.11 trở lên (CI kiểm tra 3.11, 3.12 và 3.13); cài requirements.txt (hoặc requirements-lock.txt để dùng toàn bộ phiên bản đã kiểm thử); chạy python run.py --replications 50; chạy python -m pytest -q; chạy python tools/execute_notebook.py. Notebook đọc dữ liệu nguồn và gọi chung hàm xử lý, sau đó đối soát với CSV được pipeline xuất.',
        'README.md là điểm bắt đầu; docs/QUY-TRINH.md mô tả phương pháp; data/data_dictionary.md định nghĩa trường; docs/DOI-SOAT-BAN-CU.md lưu các số tính lại từ bản gốc; docs/PHAN-VIEC-NHOM.md ghi phần công việc cần nhóm cung cấp. Các nguồn phương pháp trên không chứng minh tính đại diện của dữ liệu.'
    ])
    from .academic_report import enrich
    return enrich(sections,m,v,stages,q,raw,families=families,null=null,nullstats=nullstats,boot=boot,
                  coverage=coverage,missing=missing,exp=exp)


def render_text(sections):
    """Markdown and HTML for the report, without the PDF.

    Split out so tests can assert on the report text in about a second instead of building a
    21-page PDF for every check.
    """
    tables,figures=_asset_numbers(sections)
    md=[];web=[]
    for s in sections:
        s['paras']=[_resolve(x,tables,figures) for x in s['paras']]
        md.append('# '+s['title']+'\n');web.append('<section><h1>'+html.escape(s['title'])+'</h1>')
        for p in s['paras']:
            md.append(p+'\n');web.append('<p>'+html.escape(p)+'</p>')
        # Captions carry their own text: never the section title, never the section number.
        caption=s.get('caption') or s['title'].split(' ',1)[-1]
        if s['chart']:
            label=f'Hình {figures[s["title"]]}. {caption}'
            md.append(f'![{label}](../charts/{s["chart"]})\n')
            web.append(f'<figure><img alt="{html.escape(label)}" src="../charts/{s["chart"]}"><figcaption>{html.escape(label)}</figcaption></figure>')
        if s['table']:
            label=f'Bảng {tables[s["title"]]}. {caption}'
            data=s['table']
            md.append(f'**{label}**\n\n| '+' | '.join(data[0])+' |\n| '+' | '.join(['---']*len(data[0]))+' |\n'+'\n'.join('| '+' | '.join(map(str,r))+' |' for r in data[1:])+'\n')
            web.append(f'<div class="scroll"><table><caption>{html.escape(label)}</caption>'+''.join('<tr>'+''.join(f'<td>{html.escape(str(x))}</td>' for x in row)+'</tr>' for row in data)+'</table></div>')
        web.append('</section>')
    return '\n'.join(md),''.join(web)


def build_report(root,d,t,m,v,stages,exp,recovery,raw=None,missing=None,families=None,null=None,nullstats=None,coverage=None,boot=None):
    sections=build_sections(root,d,t,m,v,stages,exp,recovery,raw=raw,missing=missing,
                            families=families,null=null,nullstats=nullstats,coverage=coverage)
    write_outputs(root,sections)


def write_outputs(root,sections):
    write_pdf(root,sections)
    write_text_outputs(root,sections)


def write_pdf(root,sections):
    import os
    tables,figures=_asset_numbers(sections)
    for s in sections:
        s['paras']=[_resolve(x,tables,figures) for x in s['paras']]
    fonts=Path(os.environ.get('WINDIR',''))/'Fonts'
    regular,bold='times.ttf','timesbd.ttf'
    if not (fonts/regular).exists():
        import matplotlib
        fonts=Path(matplotlib.get_data_path())/'fonts/ttf'
        regular,bold='DejaVuSerif.ttf','DejaVuSerif-Bold.ttf'
    for name,file in [('DV',regular),('DVB',bold)]:pdfmetrics.registerFont(TTFont(name,str(fonts/file)))
    pdfmetrics.registerFontFamily('DV',normal='DV',bold='DVB',italic='DV',boldItalic='DVB')
    styles={'title':ParagraphStyle('title',fontName='DVB',fontSize=19,leading=25,textColor=colors.HexColor('#173e56'),spaceAfter=18),'body':ParagraphStyle('body',fontName='DV',fontSize=10,leading=15,spaceAfter=10),'cell':ParagraphStyle('cell',fontName='DV',fontSize=8,leading=11),'head':ParagraphStyle('head',fontName='DVB',fontSize=8,leading=11,textColor=colors.white)}
    from reportlab.platypus.tableofcontents import TableOfContents
    class AcademicDocument(SimpleDocTemplate):
        def afterFlowable(self, flowable):
            if isinstance(flowable, Paragraph) and flowable.style.name == 'title':
                self.notify('TOCEntry', (0, flowable.getPlainText(), self.page))
    styles['title'].textColor = colors.black
    styles['title'].fontSize = 16
    styles['title'].leading = 22
    styles['body'].fontSize = 11
    styles['body'].leading = 16
    styles['body'].spaceAfter = 8
    styles['body'].alignment = 4
    styles['title'].keepWithNext = True
    styles['caption'] = ParagraphStyle('caption',parent=styles['body'],keepWithNext=True)
    cover = ParagraphStyle('cover',fontName='DVB',fontSize=21,leading=30,alignment=1,spaceAfter=25)
    story=[Spacer(1,95),Paragraph('BÁO CÁO HỌC PHẦN<br/>KHOA HỌC DỮ LIỆU',cover),Spacer(1,35),Paragraph('XÂY DỰNG BỘ DỮ LIỆU KINH DOANH SÁCH<br/>XỬ LÝ VÀ TRỰC QUAN HÓA DỮ LIỆU',cover),Spacer(1,25),Paragraph('Nghiên cứu mô phỏng và phân tích ý nghĩa kinh doanh',styles['body']),Spacer(1,100),Paragraph('Tháng 11 năm 2026',cover),PageBreak(),Paragraph('MỤC LỤC',cover)]
    toc=TableOfContents()
    toc.levelStyles=[ParagraphStyle('toc',fontName='DV',fontSize=10,leading=15,spaceAfter=5)]
    story.extend([toc,PageBreak()])
    for i,s in enumerate(sections):
        if i and (s['title'].startswith(('Chương','Tài liệu','Phụ lục','4.7'))):story.append(PageBreak())
        story.append(Paragraph(html.escape(s['title']),styles['title']))
        for p in s['paras']:
            story.append(Paragraph(html.escape(p),styles['body']))
        # Captions carry their own text: never the section title, never the section number.
        caption=s.get('caption') or s['title'].split(' ',1)[-1]
        if s['chart']:
            from PIL import Image as PILImage
            path=root/'charts'/s['chart'];w,h=PILImage.open(path).size
            label=f'Hình {figures[s["title"]]}. {caption}'
            story.append(KeepTogether([Image(str(path),width=min(440,300*w/h),height=min(300,440*h/w)),Spacer(1,6),Paragraph(label,styles['cell']),Spacer(1,14)]))
        if s['table']:
            label=f'Bảng {tables[s["title"]]}. {caption}'
            table_caption=Paragraph(label,styles['caption'])
            data=s['table'];widths=[480/len(data[0])]*len(data[0])
            cells=[[Paragraph(html.escape(str(x)),styles['head'] if ri==0 else styles['cell']) for x in row] for ri,row in enumerate(data)]
            table=Table(cells,colWidths=widths,repeatRows=1,hAlign='LEFT');table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#175C80')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.HexColor('#eff5f8'),colors.white]),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]));story.append(KeepTogether([table_caption,table]))
    def footer(canvas,doc):
        canvas.setFont('DV',8);canvas.setFillColor(colors.HexColor('#536879'));canvas.drawString(55,28,'KINH DOANH SÁCH • NGHIÊN CỨU MÔ PHỎNG');canvas.drawRightString(A4[0]-55,28,str(doc.page))
    AcademicDocument(str(root/'report/bao_cao.pdf'),pagesize=A4,rightMargin=55,leftMargin=55,topMargin=50,bottomMargin=48,title='Xây dựng bộ dữ liệu kinh doanh sách',author='',creator='kinh-doanh-sach',producer='kinh-doanh-sach',invariant=1).multiBuild(story,onFirstPage=footer,onLaterPages=footer)


def write_text_outputs(root,sections):
    """Write the Markdown and offline HTML.

    newline='\\n' keeps the committed files reproducible on Windows, where text mode would write
    CRLF and change the manifest hash for identical content.
    """
    md,web=render_text(sections)
    (root/'report/bao_cao.md').write_text(md,encoding='utf8',newline='\n')
    css='body{font:17px/1.7 Arial,sans-serif;background:#edf3f6;color:#203c4b;margin:0}main{max-width:1000px;margin:auto}section{background:white;margin:26px 0;padding:44px;border-radius:12px;border:1px solid #dce5ea}h1{font-size:28px;line-height:1.3;color:#175C80}img{width:100%;height:auto}table{border-collapse:collapse;width:100%;font-size:14px}td{padding:11px;border-bottom:1px solid #dce5ea}tr:first-child{background:#175C80;color:white}.scroll{overflow-x:auto}@media(max-width:650px){section{padding:20px}}@media print{section{break-before:page;border:0;margin:0;padding:0}body{background:white}}'
    css+='body{font-family:Georgia,"Times New Roman",serif;color:#111;background:#eee}h1{color:#000;font-size:24px}section{border:0;border-radius:0}td{border:1px solid #d9d9d9}tr:first-child{background:#eee;color:#000}@media print{section{break-before:auto}h1{break-after:avoid}}'
    (root/'report/bao_cao.html').write_text('<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Báo cáo nghiên cứu mô phỏng sách</title><style>'+css+'</style><main>'+web+'</main></html>',encoding='utf8',newline='\n')
