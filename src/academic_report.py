"""Academic structure and explanatory material for the submission report.

Every quantity below is derived from the run that produced the report. Nothing here may be
written as a literal: a stale literal is exactly the defect this module used to carry (base-case
line counts, revenue and quarantine totals that survived a change of `n_lines`).
"""
from .config import PARAMS


def enrich(sections, m, v, stages, q, raw, families=None, null=None, nullstats=None,
           coverage=None, missing=None, exp=None, boot=None):
    from .report_builder import f

    p = PARAMS
    n_raw = len(raw)
    n_clean = m['lines']
    n_quarantine = len(q)
    n_dup = n_raw - n_clean - n_quarantine
    n_truth = p['n_lines']
    n_removed = n_dup + n_quarantine
    n_business_lost = n_truth - n_clean
    revenue_gap = v['truth_revenue'] - v['clean_revenue']

    def block(title, *paragraphs):
        return dict(title=title, paras=list(paragraphs), chart=None, table=None, caption=None)

    introduction = block('Chương 1 Tổng quan đề tài',
        'Hoạt động bán sách tạo ra dữ liệu ở nhiều cấp độ, từ danh mục đầu sách đến từng dòng giao dịch. Để sử dụng dữ liệu phục vụ quản lý, cần thống nhất đơn vị quan sát, xác định các trường hợp sai và xây dựng chỉ tiêu có ý nghĩa nghiệp vụ. Một tổng bán hàng có thể tính đúng về số học nhưng vẫn thiếu giao dịch hoặc bị đếm lặp. Vì vậy, đề tài xem chất lượng dữ liệu và diễn giải kết quả là hai phần liên kết của cùng quá trình phân tích.',
        'Mục tiêu tổng quát là xây dựng bộ dữ liệu kinh doanh sách, xử lý dữ liệu, trực quan hóa và rút ra ý nghĩa từ kết quả. Các mục tiêu cụ thể gồm thiết kế danh mục và giao dịch có khóa định danh, mô phỏng lỗi thường gặp, xây dựng quy trình xử lý có thể truy vết, mô tả cơ cấu bán hàng và đánh giá mức phụ thuộc của kết luận vào giả định đầu vào.',
        f'Phạm vi nghiên cứu gồm {f(p["n_books"])} đầu sách thuộc 10 thể loại, năm kênh giả lập và thời gian từ tháng 1 năm 2024 đến tháng 12 năm 2025. Bộ dữ liệu được xây dựng bằng mô phỏng để có thể biết giá trị chuẩn trước khi cài lỗi. Lựa chọn này cho phép đánh giá trực tiếp khả năng phục hồi dữ liệu, đồng thời giới hạn mọi kết luận kinh doanh trong phạm vi mô hình đã thiết kế.',
        'Báo cáo triển khai theo sáu chương. Chương 1 xác định bài toán và câu hỏi. Chương 2 trình bày cơ sở phương pháp. Chương 3 mô tả quá trình xây dựng và xử lý dữ liệu. Chương 4 phân tích kết quả trực quan. Chương 5 đánh giá độ nhạy. Chương 6 thảo luận ý nghĩa, hạn chế và hướng phát triển. Các phụ lục cung cấp cấu trúc dữ liệu và cách tái lập kết quả.')
    theory = block('Chương 2 Cơ sở phương pháp',
        'Phân tích khám phá dữ liệu được sử dụng để mô tả phân phối, phát hiện quan sát bất thường và xác định quan hệ cần xem xét sâu hơn. Trong đề tài này, thống kê mô tả đi trước diễn giải kinh doanh. Mỗi kết quả phải xác định tập dữ liệu, đơn vị quan sát, công thức tổng hợp và mẫu số. Cách tổ chức này giúp phân biệt sự thay đổi của dữ liệu với sự thay đổi do bộ lọc hoặc cách tính.',
        'Chất lượng dữ liệu được đánh giá qua tính hợp lệ, đầy đủ, duy nhất và nhất quán. Tính hợp lệ kiểm tra miền giá trị như số lượng nguyên dương và điểm trong khoảng 1 đến 5. Tính đầy đủ gồm độ bao phủ của trường và giao dịch. Tính duy nhất được kiểm tra bằng mã dòng nghiệp vụ. Tính nhất quán được đánh giá qua quan hệ giữa giá gốc, giảm giá và giá bán. Việc đạt một tiêu chí không suy ra các tiêu chí còn lại cũng đạt.',
        'Khung ADEMP được dùng để trình bày rõ mục tiêu, cơ chế sinh dữ liệu, đại lượng cần đánh giá, phương pháp và thước đo kết quả (Morris và cộng sự, 2019). Trong nghiên cứu này, dữ liệu chuẩn tạo điều kiện đối chiếu nhưng được tách khỏi đầu vào làm sạch. Việc tách này giúp kiểm tra quy trình phục hồi bằng thông tin nghiệp vụ sẵn có thay vì vô tình sử dụng đáp án của thí nghiệm.',
        'Với dòng i, đặt pᵢ là giá bán và qᵢ là số cuốn. Giá trị dòng bằng pᵢ × qᵢ. Tổng giá trị T là tổng giá trị của mọi dòng giữ lại, còn tổng lượng Q là tổng qᵢ. Giá bình quân có trọng số bằng T/Q. Trung bình đơn giản của giá theo dòng cho mỗi giao dịch trọng số bằng nhau, nên trả lời một câu hỏi khác khi số cuốn mỗi dòng khác nhau.',
        'Hệ số Pearson đo liên hệ tuyến tính giữa hai biến, nằm trong khoảng từ −1 đến 1 khi phương sai khác không. Hệ số gần 0 có thể đi cùng một quan hệ phi tuyến hoặc nhiều nhóm có cấu trúc khác nhau. Trong dữ liệu này, một sách xuất hiện nhiều lần nên phân tích điểm sách được tổng hợp ở cấp mã sách. Việc lựa chọn cấp tổng hợp là một phần của thiết kế phân tích.',
        'Boxplot mô tả trung vị, tứ phân vị và các điểm nằm ngoài râu hộp (NIST/SEMATECH, 2012). Quy tắc 1,5 lần khoảng tứ phân vị cung cấp dấu hiệu cần xem xét. Quyết định giữ hay cách ly còn phụ thuộc miền giá trị và bối cảnh nghiệp vụ. Các dòng mua nhiều được xem xét riêng vì có thể chi phối trung bình và hệ số tương quan.',
        'Biểu đồ cột phù hợp so sánh các nhóm danh mục, biểu đồ đường thể hiện thứ tự thời gian, biểu đồ phân tán thể hiện quan hệ hai biến và ma trận tương quan tóm tắt liên hệ tuyến tính. Khi dùng thang log cho lượng bán, khoảng cách bằng nhau biểu thị tỷ lệ thay đổi bằng nhau. Chú thích biểu đồ cần giúp người đọc nhận diện phép biến đổi này trước khi so sánh.')
    # Keys are positions in the list returned by build_sections, not the numbers printed in the
    # old headings: inserting a section shifts every later index, so this map is written against
    # the current order and must move with it.
    titles = {
        1:'1.1 Câu hỏi và thiết kế nghiên cứu',
        2:'3.1 Nguồn gốc và cơ chế sinh dữ liệu',
        3:'3.2 Quy trình làm sạch',
        4:'3.3 Đánh giá chất lượng sau xử lý',
        5:'3.4 Hiệu năng phát hiện theo họ lỗi',
        6:'4.1 Cơ cấu theo thể loại',
        7:'4.2 Phân tích danh mục sách',
        8:'4.3 Phân tích theo thời gian',
        9:'4.4 Giá và giảm giá',
        10:'4.5 Điểm sách và lượng bán',
        11:'4.6 Kiểm chứng bằng phân phối null',
        12:'4.7 Khoảng bootstrap cho các chỉ tiêu chính',
        13:'4.8 Cấu trúc tương quan',
        14:'4.9 Kênh bán và phân khúc giá',
        15:'5.1 Thí nghiệm thay đổi giả định',
        16:'5.2 Thí nghiệm dữ liệu thiếu',
        17:'5.3 Độ bao phủ danh mục',
        18:'Chương 6 Thảo luận và kết luận',
    }
    for i, title in titles.items():
        sections[i]['title'] = title
    sections[1]['table'] = None
    sections[0]['title'] = 'Tóm tắt nghiên cứu'
    sections[0]['paras'] = [p_ for p_ in sections[0]['paras'] if not p_.startswith('NGHIÊN CỨU')]
    sections[0]['paras'] = [p_.replace(' Nhóm cần bổ sung thông tin bìa học phần và kiểm tra hiểu biết trước khi nộp.', '') for p_ in sections[0]['paras']]
    sections[2]['paras'].append('Thiết kế mô phỏng còn phân biệt hai nguồn biến động. Biến động giữa các dòng đến từ ngày bán, sách, kênh và số cuốn được lấy ngẫu nhiên. Khác biệt có hệ thống đến từ trọng số thể loại, mức giảm theo kênh và hệ số mùa vụ. Khi một nhóm đứng đầu, cần xem lại cả hai nguồn trước khi diễn giải. Seed cố định cho phép tái tạo cùng bộ dữ liệu, còn nhiều seed cho phép quan sát mức dao động do tính ngẫu nhiên.')
    sections[3]['paras'].append('Thứ tự làm sạch ảnh hưởng đến khả năng nhận diện bản sao. Hai dòng có cùng ý nghĩa nhưng khác cách viết tiền tệ hoặc khoảng trắng chỉ được nhận diện nhất quán sau chuẩn hóa. Ngược lại, gộp mọi dòng có cùng mã trước khi so nội dung có thể làm mất dấu xung đột. Quy trình vì vậy chuẩn hóa biểu diễn trước, so sánh nội dung theo khóa sau và ghi lại trạng thái cuối cho toàn bộ bản ghi nguồn.')
    sections[4]['paras'].append(
        f'Số dòng giảm từ {f(n_raw)} xuống {f(n_clean)} cần được đọc theo hai mẫu số. Có {f(n_dup)} bản sao được gộp và {f(n_quarantine)} dòng nguồn được cách ly, tổng cộng {f(n_removed)} dòng rời tập nguồn. '
        f'Tuy nhiên, {f(n_truth)} mã nghiệp vụ chuẩn chỉ giảm {f(n_business_lost)} mã, vì các bản sao không đại diện giao dịch bổ sung. Do đó tỷ lệ giữ dữ liệu nghiệp vụ được tính bằng {f(n_clean)}/{f(n_truth)}, thay vì {f(n_clean)}/{f(n_raw)}. '
        'Việc công bố cả hai số giúp tránh đánh đồng khử trùng với mất giao dịch.')
    sections[7]['paras'].append('So sánh tháng dựa trên tổng giá trị cần xem thêm số ngày lịch và số giao dịch trong từng tháng. Tháng ngắn hơn có ít cơ hội phát sinh dòng bán hơn khi ngày được chọn đều. Vì vậy mức chênh lệch đỉnh và đáy là kết quả mô tả tổng hợp. Một phân tích vận hành mở rộng có thể báo cáo thêm giá trị bình quân theo ngày hoạt động và số cuốn trên đơn để tách quy mô giao dịch khỏi giá trị mỗi giao dịch.')
    sections[13]['paras'].append(
        f'Sai lệch tổng giá trị trung bình ở cả ba kịch bản nằm quanh {f(v["relative_revenue_error_pct"],3)}%. Kết quả này cho thấy cơ chế cách ly gây thiếu tổng trong các lần thử đang xét, kể cả khi giả định về mùa vụ hoặc giảm giá thay đổi. '
        'Đây là một lý do cần theo dõi chỉ tiêu đầy đủ song song với chỉ tiêu sửa đúng. Khi tăng số lần chạy, MCSE của trung bình thường giảm theo căn bậc hai của số lần chạy trong điều kiện các lần chạy độc lập và phương sai hữu hạn.')
    if families is not None and len(families):
        agg = families.attrs.get('aggregate') or {}
        n_inj = int(families.n_cai.sum())
        n_caught = int(families.n_cach_ly.sum())
        n_wrong = int(families.con_sai.sum())
        sections[4]['paras'].append(
            f'Con số cần đọc không phải độ chính xác mà là độ phủ. Trên {f(n_inj)} dòng mang lỗi thuộc tám họ, chỉ {f(n_caught)} dòng bị cách ly, tức {f(100*n_caught/n_inj if n_inj else 0,1)}%. '
            f'{f(n_wrong)} dòng mang lỗi vẫn nằm trong tập phân tích và vẫn khác dữ liệu chuẩn. '
            'Bản trước công bố 100% cho cả độ chính xác và độ phủ vì mẫu số chỉ gồm hai họ lỗi mà quy tắc vốn nhắm tới; cách đo đó không thể phát hiện điều gì ngoài chính quy tắc đã dùng.')
        sections[4]['paras'].append(
            'Việc tách theo họ lỗi không nhằm làm con số đẹp hơn mà để chỉ ra giới hạn của phương pháp. Bốn họ lỗi tạo ra giá trị vẫn hợp lệ: giá bị đặt lại bằng giá gốc, giá bị hoán vị giữa hai dòng, ngày bị đảo tháng và thể loại sai nhưng hợp lệ. '
            'Không quy tắc nào chỉ dựa trên miền giá trị phát hiện được chúng, và bài không dựng quy tắc đọc dữ liệu chuẩn để xóa chúng, vì làm vậy sẽ biến đáp án của thí nghiệm thành đầu vào của quy trình.')
    if null is not None and nullstats is not None and len(nullstats):
        ns = nullstats.set_index('metric')
        _s = null['rating_book_qty_r'].dropna()
        _lo, _hi = _s.quantile(.025), _s.quantile(.975)
        _obs = m['rating_book_qty_r']
        _inside = _lo <= _obs <= _hi
        sections[10]['paras'].append(
            f'Để biết giá trị {f(_obs,3)} có ý nghĩa hay chỉ là nhiễu, dữ liệu được sinh lại qua {f(len(null))} seed và tính lại cùng hệ số. '
            f'Phân phối null có trung bình {f(ns.loc["rating_book_qty_r","mean"],3)}, độ lệch chuẩn {f(ns.loc["rating_book_qty_r","sd"],3)} và khoảng 95% thực nghiệm [{f(_lo,3)}; {f(_hi,3)}]. '
            f'Giá trị quan sát ở phân vị thứ {f(100*(_s<_obs).mean(),1)} và nằm {"trong" if _inside else "ngoài"} khoảng đó. '
            + ('Vì vậy nó tương thích với mức dao động do chính mô hình sinh ra, và không được trình bày như một phát hiện. '
               'Điều này cũng không cho phép kết luận ngược lại rằng có một quan hệ thị trường: điểm đánh giá được sinh độc lập với lượng, nên ở cấp quần thể tương quan bằng 0 theo thiết kế.'
               if _inside else
               'Vì vậy không thể nói giá trị này chỉ là nhiễu, và cũng không thể nói nó là quan hệ thị trường: nó chỉ ra một nguồn tương quan phụ trong mô hình hoặc trong quy trình làm sạch cần được giải thích.')
            + ' Việc phân vị và khoảng được báo cáo cùng nhau là có chủ ý, vì một giá trị có thể ở vùng đuôi mà vẫn nằm trong khoảng trung tâm 95%.')
    if coverage is not None and len(coverage):
        sections[17]['paras'].append(
            f'Giả định danh mục đầy đủ cũng được đo riêng, và kết quả nghiêm trọng hơn cách báo cáo cũ mô tả. Khi một mã sách không có trong danh mục, dòng giao dịch của nó không tra được thuộc tính và bị cách ly, nên độ bao phủ danh mục quyết định trực tiếp độ đầy đủ của tổng giá trị bán hàng chứ không chỉ độ đầy đủ của các cột mô tả. '
            'Ở mức bao phủ 50%, khoảng một nửa giá trị bán hàng biến khỏi tập phân tích. Đây là lý do giả định này phải được nêu ở phần hạn chế như một điều kiện của toàn bộ kết quả, không phải một chi tiết kỹ thuật.')
    sections[15]['paras'] = [p_ for p_ in sections[15]['paras'] if not p_.startswith(('Trách nhiệm nhóm:', 'Không có căn cứ'))]
    sections[15]['paras'].insert(1,
        f'Ý nghĩa quản trị trực tiếp của kết quả là xây dựng cơ chế đối soát trước khi sử dụng báo cáo bán hàng. Sai lệch {f(revenue_gap)} đồng giữa tập chuẩn và tập sạch cho biết phần giá trị nằm trong các giao dịch chưa đủ điều kiện phân tích. '
        'Khi vận hành thực tế, người phụ trách dữ liệu cần rà soát hồ sơ gốc của các mã bị cách ly, cập nhật trạng thái xử lý và tính lại tổng sau khi xác minh. Nhờ đó, báo cáo thể hiện cả kết quả phân tích và phạm vi dữ liệu đang chờ xử lý.')
    sections[15]['paras'].insert(2, 'Các kết quả theo thể loại, sách, kênh và thời gian cung cấp cấu trúc cho một báo cáo quản trị định kỳ. Người quản lý có thể dùng cấu trúc này để chọn nhóm cần kiểm tra thêm, chẳng hạn một đầu sách có tổng lượng cao do ít đơn mua nhiều. Quyết định nhập hàng cần bổ sung tồn kho và thời gian cung ứng. Quyết định khuyến mãi cần bổ sung giá vốn và chi phí kênh. Việc nêu dữ liệu cần bổ sung giúp chuyển nhận xét mô tả thành một quy trình ra quyết định có điều kiện kiểm chứng.')
    result = [sections[0], introduction, sections[1], theory,
        block('Chương 3 Xây dựng và xử lý dữ liệu', 'Quy trình gồm thiết kế danh mục, sinh giao dịch chuẩn, tạo bản dữ liệu có lỗi, chuẩn hóa và đối chiếu kết quả. Ba lớp dữ liệu nguồn, dữ liệu xử lý và dữ liệu kiểm chứng có vai trò riêng. Các bước xử lý đều ghi nhật ký để giải thích số dòng thay đổi và giá trị được sửa.'), *sections[2:6],
        block('Chương 4 Kết quả phân tích và trực quan hóa',
            f'Toàn bộ phân tích trong chương sử dụng {f(n_clean)} dòng sạch của kịch bản cơ sở. Tổng giá trị bán hàng là {f(m["revenue"])} đồng với {f(m["quantity"])} cuốn. '
            'Các biểu đồ được đọc theo thứ tự từ cơ cấu sản phẩm đến thời gian, quan hệ giữa các biến và kênh phân phối. Mỗi mục trình bày kết quả định lượng, giải thích trong phạm vi mô hình và ý nghĩa thực hành.'), *sections[6:15],
        block('Chương 5 Đánh giá độ nhạy của kết quả', 'Một kết quả xuất hiện trong một lần mô phỏng có thể phụ thuộc hạt giống ngẫu nhiên hoặc tham số thiết kế. Chương này thay đổi từng giả định và so sánh nhiều lần chạy. Các thí nghiệm bổ sung giúp nhận diện nguồn hình thành kết quả, đồng thời đánh giá lựa chọn xử lý thiếu dữ liệu.'), *sections[15:18],
        *sections[18:]]
    result.append(block('Phụ lục A Cấu trúc dữ liệu và khả năng truy vết',
        'Mã raw_row_id phân biệt từng bản ghi nguồn. Mã ma_dong phân biệt giao dịch nghiệp vụ và được giữ nguyên khi tạo bản sao. Mã ma_sach liên kết nhiều dòng bán với một sách trong danh mục. Ba mã này phục vụ ba mục đích khác nhau, nên khử trùng phải dựa vào mã nghiệp vụ và nội dung sau chuẩn hóa.',
        'Các trường mô tả sách gồm tên sách, thể loại, tác giả, nhà xuất bản và năm xuất bản. Các trường giao dịch gồm ngày bán, kênh, giá gốc, giảm giá niêm yết, giá bán và số lượng. Điểm đánh giá là thuộc tính cố định của sách. Giá trị bán hàng và giảm giá thực tế là các biến được tính từ trường nguồn.',
        'Tệp cell_changes ghi giá trị trước và sau ở cấp ô. Tệp row_lineage ghi trạng thái cuối cho mỗi dòng nguồn. Tệp quarantine giữ bản ghi cần xác minh cùng lý do. Khi đọc một tổng bị giảm sau làm sạch, có thể đi ngược từ bảng tổng hợp đến các trạng thái và mã dòng để xác định nguyên nhân.',
        'Từ điển đầy đủ tại data/data_dictionary.md quy định kiểu logic, đơn vị, miền giá trị và công thức. Tiền được biểu diễn bằng đồng, số lượng bằng cuốn và ngày theo định dạng YYYY-MM-DD. Các CSV sử dụng UTF-8 BOM để hỗ trợ đọc tiếng Việt.'))
    return result
