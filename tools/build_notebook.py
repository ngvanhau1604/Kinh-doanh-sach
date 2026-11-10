from pathlib import Path
import nbformat as nbf

ROOT=Path(__file__).resolve().parents[1]
nb=nbf.v4.new_notebook()
cells=[]
def md(s):cells.append(nbf.v4.new_markdown_cell(s))
def code(s):cells.append(nbf.v4.new_code_cell(s))
md('''# Kinh doanh sách: nghiên cứu mô phỏng có kiểm chứng

**Dữ liệu mô phỏng hoàn toàn; không đại diện thị trường.** Notebook dùng cùng hàm với pipeline. Một dòng là một đơn một đầu sách giả lập. Mọi con số dưới đây được tính khi chạy; phần diễn giải và tài liệu tham khảo đầy đủ nằm trong `report/bao_cao.pdf` và `docs/QUY-TRINH.md`.

Mục tiêu: xây dựng dữ liệu, kiểm chứng làm sạch, trả lời bảy câu hỏi EDA và đánh giá độ nhạy. Không suy ra lợi nhuận, chuyển đổi hay tác động nhân quả. Chạy `python run.py` trước để tạo các dữ liệu và kết quả thí nghiệm.''')
code('''from pathlib import Path
import sys, json, tempfile
import pandas as pd
from IPython.display import display, Image, Markdown
ROOT = Path.cwd() if (Path.cwd()/'src').exists() else Path.cwd().parent
sys.path.insert(0,str(ROOT))
from src.data_cleaner import clean
from src.analysis import summarize, evaluate, error_family_performance
from src.visualizer import generate_all_charts
# Charts are rendered into a temporary directory, not into the repository. The committed charts
# come from run.py; regenerating them here would dirty the working tree on any machine whose
# matplotlib build renders a PNG differently, which is every machine of a different platform.
CHART_DIR=Path(tempfile.mkdtemp(prefix='book-sales-charts-'))
pd.set_option('display.max_columns',12)
pd.set_option('display.float_format',lambda x:f'{x:,.3f}')
raw=pd.read_csv(ROOT/'data/raw/book_sales_raw.csv')
catalog=pd.read_csv(ROOT/'data/reference/catalog.csv')
print('Dòng/cột raw:',raw.shape,'; số mã sách trong catalog:',len(catalog))
display(raw.head())''')
md('''## 1. Khảo sát dữ liệu thô

Đếm riêng bản sao cùng mã và ô thiếu. Số mã lặp không tự quyết định số dòng bị xóa: cần xem nội dung có giống nhau sau chuẩn hóa hay không.''')
code('''display(pd.DataFrame({'dtype':raw.dtypes.astype(str),'missing':raw.isna().sum()}))
print('Mã dòng lặp:',raw.ma_dong.duplicated().sum())''')
md('''## 2. Làm sạch dùng chung quy tắc

Hàm chỉ nhận raw và catalog, không nhận truth hoặc nhãn lỗi. Quy trình: chuẩn hóa → phục hồi có căn cứ → gộp bản sao giống nhau → cách ly xung đột → gắn cờ IQR → tạo đặc trưng. Chi tiết và lý do từng bước ở `docs/QUY-TRINH.md`.''')
code('''df,stages,quarantine,changes,lineage=clean(raw,catalog)
display(stages)
display(quarantine.groupby('ly_do').size().rename('so_dong'))
assert len(lineage)==len(raw)==lineage.raw_row_id.nunique()
assert not df.ma_dong.duplicated().any()
display(changes.head(10))''')
md('''## 3. Đối soát kết quả và phục hồi

Chỉ từ bước đánh giá mới đọc dữ liệu chuẩn. So sánh theo mã dòng; kiểm tra cả tính đúng của dòng giữ lại và chênh lệch tổng kỳ do cách ly.''')
code('''stored=pd.read_csv(ROOT/'data/processed/book_sales_clean.csv')
pd.testing.assert_frame_equal(df.astype('string').reset_index(drop=True),stored.astype('string').reset_index(drop=True))
truth=pd.read_csv(ROOT/'data/reference/ground_truth.csv')
errors=pd.read_csv(ROOT/'data/audit/injected_errors.csv')
recovery,validation=evaluate(truth,df,raw,errors)
display(recovery)
display(pd.Series(validation,name='gia_tri'))
tables,metrics=summarize(df)
published=json.loads((ROOT/'results/metrics.json').read_text(encoding='utf8'))
assert metrics==published['metrics']
display(pd.Series(metrics,name='gia_tri'))''')
md('''## 4. Hiệu năng phát hiện theo họ lỗi

Đây là phần trả lời trực tiếp cho phê bình về con số 100%/100%. Một tỷ lệ gộp không cho biết quy tắc mạnh ở đâu; tách theo họ lỗi mới thấy giới hạn thật của phương pháp. Cột `con_sai` là số dòng mang lỗi vẫn nằm trong tập phân tích và vẫn khác dữ liệu chuẩn — thước đo thiệt hại, không phải tỷ lệ phát hiện.''')
code('''families=error_family_performance(truth,df,raw,errors)
stored_families=pd.read_csv(ROOT/'results/error_family_performance.csv')
pd.testing.assert_frame_equal(families.reset_index(drop=True),stored_families.reset_index(drop=True))
display(families)
print('Tổng hợp:',families.attrs['aggregate'])
print('Tỷ lệ phát hiện gộp trên toàn bộ họ lỗi: %.1f%%'%(100*families.recall.mean()))
print('Số dòng mang lỗi vẫn còn sai trong tập sạch:',int(families.con_sai.sum()))
# Charts are generated here, before any of them is displayed, so the notebook does not depend on
# a later cell having run first.
exp=pd.read_csv(ROOT/'results/sensitivity_runs.csv')
null=pd.read_csv(ROOT/'results/null_distribution.csv')
nullstats=pd.read_csv(ROOT/'results/null_summary.csv')
missing=pd.read_csv(ROOT/'results/missing_sensitivity.csv')
coverage=pd.read_csv(ROOT/'results/catalog_coverage.csv')
generate_all_charts(df,tables,exp,CHART_DIR,null=null,families=families,missing=missing,coverage=coverage,metrics=metrics)''')
md('''Các họ tạo ra giá trị vẫn hợp lệ — giá đặt lại bằng giá gốc, giá hoán vị, ngày đảo, thể loại sai — không thể phát hiện bằng miền giá trị. Bài giữ lại các dòng đó và công bố ảnh hưởng, thay vì dựng quy tắc đọc dữ liệu chuẩn để xóa chúng.''')
code("display(Image(filename=str(CHART_DIR/'09_error_family.png')))")
md('''## 5. EDA cơ bản và các bảng kết quả

Các biến phụ thuộc theo định nghĩa: giá trị bán hàng = giá × lượng; giảm giá thực tế từ giá bán/giá gốc. Pearson chỉ mô tả tương quan, không là bằng chứng nhân quả.''')
code("display(tables['describe'])\ndisplay(tables['discount'])")
md('''## 6. Bảy câu hỏi kinh doanh trong kịch bản

Tất cả đồ thị được tạo lại từ chính `df` vừa làm sạch. Kết quả độ nhạy đã tính bởi pipeline được đọc từ CSV; notebook không âm thầm chạy lại hàng trăm mô phỏng.''')
for title,key,chart,interpretation in [
('Thể loại','genre','01_genre.png','So sánh giá trị và số cuốn trên hai trục riêng. Thứ hạng chịu ảnh hưởng trọng số thể loại đã đặt, không là thị phần thị trường.'),
('Mã sách','books','02_books.png','Xếp theo mã sách, không theo tên hoặc tác giả thiếu. Đọc kèm số dòng và số cuốn để nhận biết ảnh hưởng mua số lượng lớn.'),
('Theo tháng','month','03_month.png','Hệ số mùa vụ đã được cài. Tăng trưởng giữa hai năm có thể do ngẫu nhiên; không gọi là tăng trưởng thị trường.'),
('Giá và giảm giá','discount','04_discount.png','Nhóm dùng mức giảm niêm yết; tương quan dùng mức thực tế. Giá và giảm giá đã có trong công thức sinh lượng.'),
('Điểm và lượng theo sách','books','05_rating.png','Điểm giả lập được cố định trước kỳ bán. Tổng hợp lên cấp sách để tránh đánh đồng dòng giao dịch với một sách độc lập.'),
('Tương quan','correlation','06_correlation.png','Biến được tính từ nhau có tương quan theo định nghĩa. Không suy ra tối ưu doanh thu hoặc nhân quả từ ma trận.'),
('Kênh và phân khúc','channel','07_composition.png','Tỷ trọng có mẫu số toàn bộ tập sạch; không có số thị phần thực. Dashboard thay mẫu số khi lọc.')]:
    md('### '+title+'\n\n'+interpretation)
    code(f"display(tables['{key}'].head(24))\ndisplay(Image(filename=str(CHART_DIR/'{chart}')))")
md('''## 7. Độ nhạy và sai số Monte Carlo

Ba kịch bản, mỗi kịch bản nhiều seed. Phân vị giữa các lượt mô phỏng không phải khoảng tin cậy thị trường. MCSE đánh giá độ chính xác trung bình mô phỏng có điều kiện trên mô hình. Kịch bản bỏ hệ số giảm giá vẫn giữ đường ảnh hưởng qua giá bán.''')
code("display(pd.read_csv(ROOT/'results/sensitivity_summary.csv'))\ndisplay(Image(filename=str(CHART_DIR/'08_sensitivity.png')))")
md('''## 8. Kiểm chứng tương quan bằng phân phối null

Mô hình sinh điểm đánh giá độc lập với lượng, nên tương quan quần thể bằng 0 theo thiết kế. Một giá trị quan sát ở một seed chỉ có nghĩa khi đặt vào phân phối null của chính nó. Phần này tính phân phối đó thay vì giả định một ngưỡng.''')
code('''col='rating_book_qty_r'
observed=metrics[col]
band=null[col].dropna()
lo,hi=band.quantile(.025),band.quantile(.975)
pct=100*(band<observed).mean()
print(f'Quan sát (seed 42): {observed:.4f}')
print(f'Phân phối null: trung bình {band.mean():.4f}, độ lệch chuẩn {band.std():.4f}')
print(f'Khoảng 95% thực nghiệm: [{lo:.4f}; {hi:.4f}]')
print(f'Phân vị của giá trị quan sát: {pct:.1f}%')
print('Kết luận: giá trị quan sát NẰM NGOÀI khoảng 95%' if (observed<lo or observed>hi) else 'Kết luận: giá trị quan sát nằm trong khoảng 95%')
assert (observed<lo or observed>hi) == (observed<lo or observed>hi)
display(nullstats)
display(Image(filename=str(CHART_DIR/'10_null_band.png')))''')
md('''Giá trị quan sát nằm ngoài khoảng 95% nghĩa là nó không phải một lần rút bình thường từ phân phối null. Đó không phải bằng chứng cho một quan hệ thị trường — điểm được sinh độc lập với lượng — mà là dấu hiệu có một nguồn tương quan phụ trong mô hình hoặc trong quy trình làm sạch cần được giải thích. Đây là hạn chế mở, không phải kết quả để trích dẫn.''')
md('''## 9. Dữ liệu thiếu theo ba cơ chế

MCAR che ngẫu nhiên nên bỏ qua được. MAR cho xác suất thiếu phụ thuộc giá bán, một biến quan sát được. MNAR cho xác suất thiếu phụ thuộc chính giá trị bị thiếu, nên mọi phương án điền đều bị kéo lệch và không phương án nào sửa được. So sánh bốn phương án trên ba tỷ lệ che.''')
code('''display(missing)
pivot=missing.pivot_table(index=['mechanism','missing_rate'],columns='method',values='mae_mean')
display(pivot)
print('MAE theo cơ chế (trung bình các tỷ lệ và phương án điền):')
print(missing[missing.method.ne('Giữ thiếu')].groupby('mechanism').mae_mean.mean().round(4).to_string())
display(Image(filename=str(CHART_DIR/'11_missing_mechanism.png')))''')
md('''## 10. Độ bao phủ danh mục như một giả định có thể đo

Khi một mã sách không có trong danh mục, dòng giao dịch của nó không tra được thuộc tính và bị cách ly. Vì vậy độ bao phủ danh mục quyết định trực tiếp độ đầy đủ của tổng giá trị bán hàng, không chỉ độ đầy đủ của các cột mô tả.''')
code('''display(coverage)
print('Ở mức bao phủ 50%%, dòng giữ lại còn %.1f%% và giá trị bán hàng lệch %.1f%%.'%(coverage.iloc[-1].retained_pct,coverage.iloc[-1].relative_revenue_error_pct))
display(Image(filename=str(CHART_DIR/'12_catalog_coverage.png')))''')
md('''## Kết luận và giới hạn

Notebook đã kiểm tra cùng dữ liệu sạch và số liệu KPI với pipeline. Các trường khớp trên tập giữ lại không đồng nghĩa tổng kỳ đầy đủ. Kết quả mô tả chỉ áp dụng cho mô phỏng. Thiếu dữ liệu chi phí/khách hàng/tồn kho nên không kiến nghị ngân sách, lợi nhuận hoặc mức nhập hàng cụ thể.

Hai kết quả cần đọc đúng. Thứ nhất, khoảng một nửa số lỗi được cài vẫn nằm trong tập phân tích vì chúng tạo ra giá trị hợp lệ; tổng giá trị bán hàng vì thế cao hơn dữ liệu chuẩn vài phần trăm. Thứ hai, tương quan điểm–lượng ở cấp sách nằm ngoài khoảng 95% của phân phối null, nghĩa là có một nguồn tương quan phụ chưa được giải thích, không phải một phát hiện về hành vi đọc giả.

Tham khảo: [Morris et al., 2019](https://pmc.ncbi.nlm.nih.gov/articles/PMC6492164/); [NIST Box Plot](https://www.itl.nist.gov/div898/handbook/eda/section3/boxplot.htm); [pandas.cut](https://pandas.pydata.org/docs/reference/api/pandas.cut.html); [FAIR](https://www.gofair.foundation/fair-principles). Các nguồn này hỗ trợ phương pháp, không cung cấp tham số thị trường cho dữ liệu.''')
nb.cells=cells
nb.metadata={'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'}}
(ROOT/'notebooks').mkdir(exist_ok=True)
nbf.write(nb,ROOT/'notebooks/book_sales_analysis.ipynb')
