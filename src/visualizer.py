import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import textwrap
from .config import PRICE_LABELS, DISCOUNT_LABELS

plt.rcParams.update({'font.family':'DejaVu Sans','font.size':12,'axes.titlesize':13,'axes.labelsize':12,'axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':240})
BLUE='#175C80'; TEAL='#128579'; ORANGE='#CF762D'

# Figure numbers are NOT printed on the images. The report numbers figures by document order,
# so a baked-in "Hình 5" would contradict the caption as soon as a section moves.
SCENARIO_LABELS={'Cơ sở':'Cơ sở','Không hệ số giảm giá':'Bỏ hệ số\ngiảm giá','Không mùa vụ':'Bỏ mùa vụ'}


def generate_all_charts(d,tables,experiments,out):
    out.mkdir(parents=True,exist_ok=True)
    def save(fig,name,note=''):
        fig.text(.02,.015,textwrap.fill('Nguồn: dữ liệu mô phỏng, seed 42 | 2024–2025. '+note,105),fontsize=9,color='#53606C')
        fig.tight_layout(rect=[0,.10,1,1]); fig.savefig(out/name,bbox_inches='tight'); plt.close(fig)
    g=tables['genre'].iloc[::-1]
    fig,ax=plt.subplots(1,2,figsize=(10,5.5),sharey=True)
    ax[0].barh(g.the_loai,g.doanh_thu/1e6,color=BLUE); ax[0].set_xlabel('Giá trị bán hàng (triệu đồng)')
    ax[1].barh(g.the_loai,g.so_luong,color=TEAL); ax[1].set_xlabel('Số cuốn')
    fig.suptitle('Cơ cấu thể loại trong kịch bản cơ sở')
    save(fig,'01_genre.png','Hai thước đo được tách trục; không phải thị phần thị trường.')
    b=tables['books'].head(10).iloc[::-1]
    fig,ax=plt.subplots(figsize=(10,5)); ax.barh(b.ma_sach,b.doanh_thu/1e6,color=BLUE);ax.set_xlabel('Giá trị bán hàng (triệu đồng)');ax.set_title('Mười mã sách giả lập có giá trị bán hàng cao nhất')
    save(fig,'02_books.png','Xếp theo mã sách; không xếp hạng sách/tác giả thực.')
    m=tables['month'].sort_values('thang_nam')
    fig,ax=plt.subplots(2,1,figsize=(11,6),sharex=True)
    ax[0].plot(m.thang_nam,m.doanh_thu/1e6,'o-',color=BLUE); ax[0].set_ylabel('Triệu đồng')
    ax[1].plot(m.thang_nam,m.so_luong,'s-',color=TEAL); ax[1].set_ylabel('Cuốn');ax[1].tick_params(axis='x',rotation=60)
    fig.suptitle('Tổng hợp theo tháng; hệ số mùa vụ là giả định đầu vào')
    save(fig,'03_month.png')
    fig,ax=plt.subplots(1,2,figsize=(10,5))
    groups=DISCOUNT_LABELS
    v=[d.loc[d.nhom_giam_gia.eq(g),'so_luong'] for g in groups]
    ax[0].boxplot(v,tick_labels=[f'{g}\nn={len(x):,}' for g,x in zip(groups,v)],showfliers=True)
    ax[0].set_ylabel('Cuốn / dòng (thang log)');ax[0].set_yscale('log');ax[0].set_title('Phân phối gồm cả dòng mua số lượng lớn')
    hb=ax[1].hexbin(d.gia_ban/1000,d.so_luong,gridsize=35,mincnt=1,cmap='Blues',bins='log');ax[1].set_xlabel('Giá bán (nghìn đồng)');ax[1].set_ylabel('Cuốn / dòng');ax[1].set_title('Mật độ giá bán và lượng bán');fig.colorbar(hb,ax=ax[1],label='Số dòng (thang log)')
    fig.suptitle('Quan hệ giá và lượng trong cơ chế sinh đã chỉ định')
    save(fig,'04_discount.png','Không ước lượng tác động nhân quả hoặc mức giảm giá tối ưu.')
    b=tables['books']; corr=b.diem_danh_gia.corr(b.so_luong)
    fig,ax=plt.subplots(figsize=(10,5));ax.scatter(b.diem_danh_gia,b.so_luong,alpha=.55,s=22,color=TEAL);ax.set_xlabel('Điểm giả lập cố định của sách');ax.set_ylabel('Tổng số cuốn / mã sách');ax.set_title(f'Điểm và lượng bán ở cấp sách (n={len(b)}, Pearson r={corr:.3f})')
    save(fig,'05_rating.png','Điểm được sinh độc lập; không đo hài lòng khách hàng thực.')
    c=tables['correlation']; labels=['Giá gốc','Giá bán','Giảm giá thực tế','Số lượng','Giá trị bán hàng','Điểm giả lập']
    fig,ax=plt.subplots(figsize=(8,6));im=ax.imshow(c,vmin=-1,vmax=1,cmap='RdBu_r');fig.colorbar(im,ax=ax,label='Pearson r')
    ax.set_xticks(range(len(c)),labels,rotation=45,ha='right');ax.set_yticks(range(len(c)),labels)
    for i in range(len(c)):
        for j in range(len(c)):ax.text(j,i,f'{c.iloc[i,j]:.2f}',ha='center',va='center',color='white' if abs(c.iloc[i,j])>.65 else 'black')
    ax.set_title('Tương quan mô tả ở cấp dòng bán hàng')
    save(fig,'06_correlation.png','Giá trị bán hàng = giá × lượng; có quan hệ định nghĩa.')
    fig,ax=plt.subplots(1,2,figsize=(12,5));ch=tables['channel'].iloc[::-1];sg=tables['segment'].set_index('phan_khuc_gia').reindex(PRICE_LABELS)
    ax[0].barh(ch.kenh_ban,ch.ty_trong,color=BLUE);ax[0].set_xlabel('% giá trị bán hàng');ax[0].set_title('Kênh giả lập')
    ax[1].barh(sg.index,sg.ty_trong,color=TEAL);ax[1].set_xlabel('% giá trị bán hàng');ax[1].set_title('Phân khúc giá bán (đồng)')
    save(fig,'07_composition.png','Mẫu số: toàn bộ giá trị bán hàng của tập sạch.')
    fig,ax=plt.subplots(1,2,figsize=(12,5))
    names=list(experiments.scenario.unique())
    for a,col,title in zip(ax,['discount_qty_r_without_bulk','q4_share'],['Tương quan giảm giá–lượng, loại dòng >150 cuốn','Tỷ trọng quý IV (%)']):
        vals=[experiments.loc[experiments.scenario.eq(s),col] for s in names]
        a.boxplot(vals,tick_labels=[SCENARIO_LABELS.get(s,s) for s in names]);a.set_title(title,fontsize=10)
    fig.suptitle(f'Độ nhạy qua {experiments.seed.nunique()} seed / kịch bản')
    save(fig,'08_sensitivity.png','Phân bố giữa các lần mô phỏng; không phải khoảng tin cậy thị trường.')
