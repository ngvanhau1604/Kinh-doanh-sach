import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import textwrap
from .config import PRICE_LABELS, DISCOUNT_LABELS

plt.rcParams.update({'font.family':'DejaVu Sans','font.size':12,'axes.titlesize':13,'axes.labelsize':12,'axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':240})
BLUE='#175C80'; TEAL='#128579'; ORANGE='#CF762D'; GREY='#7A8B99'

# Figure numbers are NOT printed on the images. The report numbers figures by document order,
# so a baked-in "Hình 5" would contradict the caption as soon as a section moves.
SCENARIO_LABELS={'Cơ sở':'Cơ sở','Không hệ số giảm giá':'Bỏ hệ số\ngiảm giá','Không mùa vụ':'Bỏ mùa vụ'}

# Every caption states the sample, the unit of observation and the source, because a figure
# without them invites a reader to treat a simulated sample as a market measurement.
SOURCE='Nguồn: dữ liệu mô phỏng, seed 42 | 2024–2025. '


def generate_all_charts(d,tables,experiments,out,null=None,families=None,missing=None,coverage=None,metrics=None,boot=None):
    out.mkdir(parents=True,exist_ok=True)
    def save(fig,name,note=''):
        fig.text(.02,.015,textwrap.fill(SOURCE+note,105),fontsize=9,color='#53606C')
        fig.tight_layout(rect=[0,.10,1,1]); fig.savefig(out/name,bbox_inches='tight'); plt.close(fig)
    g=tables['genre'].iloc[::-1]
    fig,ax=plt.subplots(1,2,figsize=(10,5.5),sharey=True)
    ax[0].barh(g.the_loai,g.doanh_thu/1e6,color=BLUE); ax[0].set_xlabel('Giá trị bán hàng (triệu đồng)')
    ax[1].barh(g.the_loai,g.so_luong,color=TEAL); ax[1].set_xlabel('Số cuốn')
    fig.suptitle('Cơ cấu thể loại trong kịch bản cơ sở')
    save(fig,'01_genre.png',f'Đơn vị: dòng bán hàng; n={len(d):,} dòng sạch. Hai thước đo được tách trục; không phải thị phần thị trường.')
    b=tables['books'].head(10).iloc[::-1]
    fig,ax=plt.subplots(figsize=(10,5)); ax.barh(b.ma_sach,b.doanh_thu/1e6,color=BLUE);ax.set_xlabel('Giá trị bán hàng (triệu đồng)');ax.set_title('Mười mã sách giả lập có giá trị bán hàng cao nhất')
    save(fig,'02_books.png',f'Đơn vị: mã sách; n={len(tables["books"]):,} mã. Xếp theo mã sách; không xếp hạng sách/tác giả thực.')
    m=tables['month'].sort_values('thang_nam')
    fig,ax=plt.subplots(2,1,figsize=(11,6),sharex=True)
    ax[0].plot(m.thang_nam,m.doanh_thu/1e6,'o-',color=BLUE); ax[0].set_ylabel('Triệu đồng')
    ax[1].plot(m.thang_nam,m.so_luong,'s-',color=TEAL); ax[1].set_ylabel('Cuốn');ax[1].tick_params(axis='x',rotation=60)
    fig.suptitle('Tổng hợp theo tháng; hệ số mùa vụ là giả định đầu vào')
    save(fig,'03_month.png',f'Đơn vị: tháng; n={len(m)} tháng. Số ngày mỗi tháng không bằng nhau.')
    fig,ax=plt.subplots(1,2,figsize=(10,5))
    groups=DISCOUNT_LABELS
    v=[d.loc[d.nhom_giam_gia.eq(g),'so_luong'] for g in groups]
    ax[0].boxplot(v,tick_labels=[f'{g}\nn={len(x):,}' for g,x in zip(groups,v)],showfliers=True)
    ax[0].set_ylabel('Cuốn / dòng (thang log)');ax[0].set_yscale('log');ax[0].set_title('Phân phối gồm cả dòng mua số lượng lớn')
    hb=ax[1].hexbin(d.gia_ban/1000,d.so_luong,gridsize=35,mincnt=1,cmap='Blues',bins='log');ax[1].set_xlabel('Giá bán (nghìn đồng)');ax[1].set_ylabel('Cuốn / dòng');ax[1].set_title('Mật độ giá bán và lượng bán');fig.colorbar(hb,ax=ax[1],label='Số dòng (thang log)')
    fig.suptitle('Quan hệ giá và lượng trong cơ chế sinh đã chỉ định')
    save(fig,'04_discount.png','Đơn vị: dòng bán hàng. Không ước lượng tác động nhân quả hoặc mức giảm giá tối ưu.')
    b=tables['books']; corr=b.diem_danh_gia.corr(b.so_luong)
    fig,ax=plt.subplots(figsize=(10,5));ax.scatter(b.diem_danh_gia,b.so_luong,alpha=.55,s=22,color=TEAL);ax.set_xlabel('Điểm giả lập cố định của sách');ax.set_ylabel('Tổng số cuốn / mã sách');ax.set_title(f'Điểm và lượng bán ở cấp sách (n={len(b)}, Pearson r={corr:.3f})')
    save(fig,'05_rating.png',f'Đơn vị: mã sách; n={len(b):,}. Điểm được sinh độc lập với lượng; không đo hài lòng khách hàng thực.')
    c=tables['correlation']; labels=['Giá gốc','Giá bán','Giảm giá thực tế','Số lượng','Giá trị bán hàng','Điểm giả lập']
    fig,ax=plt.subplots(figsize=(8,6));im=ax.imshow(c,vmin=-1,vmax=1,cmap='RdBu_r');fig.colorbar(im,ax=ax,label='Pearson r')
    ax.set_xticks(range(len(c)),labels,rotation=45,ha='right');ax.set_yticks(range(len(c)),labels)
    for i in range(len(c)):
        for j in range(len(c)):ax.text(j,i,f'{c.iloc[i,j]:.2f}',ha='center',va='center',color='white' if abs(c.iloc[i,j])>.65 else 'black')
    ax.set_title('Tương quan mô tả ở cấp dòng bán hàng')
    save(fig,'06_correlation.png',f'Đơn vị: dòng bán hàng; n={len(d):,}. Giá trị bán hàng = giá × lượng; có quan hệ định nghĩa.')
    fig,ax=plt.subplots(1,2,figsize=(12,5));ch=tables['channel'].iloc[::-1];sg=tables['segment'].set_index('phan_khuc_gia').reindex(PRICE_LABELS)
    ax[0].barh(ch.kenh_ban,ch.ty_trong,color=BLUE);ax[0].set_xlabel('% giá trị bán hàng');ax[0].set_title('Kênh giả lập')
    ax[1].barh(sg.index,sg.ty_trong,color=TEAL);ax[1].set_xlabel('% giá trị bán hàng');ax[1].set_title('Phân khúc giá bán (đồng)')
    save(fig,'07_composition.png','Mẫu số: toàn bộ giá trị bán hàng của tập sạch; đơn vị: dòng bán hàng.')
    fig,ax=plt.subplots(1,2,figsize=(12,5))
    names=list(experiments.scenario.unique())
    for a,col,title in zip(ax,['discount_qty_r_without_bulk','q4_share'],['Tương quan giảm giá–lượng, loại dòng >150 cuốn','Tỷ trọng quý IV (%)']):
        vals=[experiments.loc[experiments.scenario.eq(s),col] for s in names]
        a.boxplot(vals,tick_labels=[SCENARIO_LABELS.get(s,s) for s in names]);a.set_title(title,fontsize=10)
    fig.suptitle(f'Độ nhạy qua {experiments.seed.nunique()} seed / kịch bản')
    save(fig,'08_sensitivity.png','Phân bố giữa các lần mô phỏng; không phải khoảng tin cậy thị trường.')

    # --- PR2 figures: what the cleaning pipeline can and cannot detect ----------------------
    if families is not None and len(families):
        order=families.sort_values('recall')
        fig,ax=plt.subplots(figsize=(11,5.5))
        y=np.arange(len(order))
        ax.barh(y,order.recall*100,color=[TEAL if d=='yes' else (ORANGE if d=='partly' else '#B23A48') for d in order.phat_hien_duoc])
        ax.set_yticks(y,order.ho_loi);ax.set_xlim(0,105);ax.set_xlabel('Tỷ lệ phát hiện (%)')
        for yi,(r,n,c) in enumerate(zip(order.recall,order.n_cai,order.con_sai)):
            ax.text(r*100+1.5,yi,f'{r*100:.0f}%  (n={n}, còn sai {c})',va='center',fontsize=10)
        ax.set_title('Tỷ lệ phát hiện theo họ lỗi được cài')
        handles=[plt.Rectangle((0,0),1,1,color=TEAL),plt.Rectangle((0,0),1,1,color=ORANGE),plt.Rectangle((0,0),1,1,color='#B23A48')]
        ax.legend(handles,['Miền giá trị phát hiện được','Phát hiện một phần','Không thể phát hiện'],loc='lower right',fontsize=10,frameon=False)
        save(fig,'09_error_family.png','Đơn vị: dòng mang lỗi được cài. Tỷ lệ phát hiện = số dòng được phát hiện (cách ly hoặc gắn cờ) / số dòng mang lỗi.')

    if null is not None and metrics is not None:
        fig,ax=plt.subplots(1,2,figsize=(12,5))
        for a,col,label,observed in [(ax[0],'rating_book_qty_r','Tương quan điểm–lượng ở cấp sách',metrics.get('rating_book_qty_r')),
                                     (ax[1],'discount_qty_r','Tương quan giảm giá–lượng ở cấp dòng',metrics.get('discount_qty_r'))]:
            s=null[col].dropna()
            a.hist(s,bins=24,color=GREY,alpha=.85)
            lo,hi=s.quantile(.025),s.quantile(.975)
            a.axvspan(lo,hi,color=TEAL,alpha=.18,label=f'Khoảng 95% null: [{lo:.3f}; {hi:.3f}]')
            if observed is not None:
                a.axvline(observed,color='#B23A48',lw=2,label=f'Seed 42: {observed:.3f}')
            a.set_title(label,fontsize=11);a.set_xlabel('Pearson r');a.set_ylabel('Số seed');a.legend(fontsize=9,frameon=False)
        fig.suptitle(f'Phân phối null của tương quan qua {len(null)} seed')
        save(fig,'10_null_band.png','Mỗi seed là một lần sinh dữ liệu đầy đủ. Khoảng 95% là phân vị thực nghiệm của phân phối null, không phải khoảng tin cậy thị trường.')

    if missing is not None and len(missing):
        fig,ax=plt.subplots(1,3,figsize=(15,4.8),sharey=True)
        for a,mech in zip(ax,['MCAR','MAR','MNAR']):
            sub=missing[missing.mechanism.eq(mech)]
            for method,color in [('Trung bình toàn cục',GREY),('Trung bình thể loại',BLUE),('Trung vị thể loại',ORANGE)]:
                s=sub[sub.method.eq(method)].sort_values('missing_rate')
                if len(s): a.plot(s.missing_rate*100,s.mae_mean,'o-',color=color,label=method)
            a.set_title(mech);a.set_xlabel('Tỷ lệ ô bị che (%)')
        ax[0].set_ylabel('MAE trên ô bị che');ax[0].legend(fontsize=9,frameon=False)
        fig.suptitle('Sai số điền khuyết theo cơ chế thiếu và tỷ lệ che')
        save(fig,'11_missing_mechanism.png','Đơn vị: ô điểm đánh giá bị che; MAE trung bình qua các seed. Phương án giữ thiếu không có MAE vì không tạo dự đoán.')

    if coverage is not None and len(coverage):
        fig,ax=plt.subplots(1,2,figsize=(12,4.8))
        ax[0].plot(coverage.catalog_coverage*100,coverage.retained_pct,'o-',color=BLUE,label='Dòng giữ lại (%)')
        ax[0].plot(coverage.catalog_coverage*100,coverage.quarantined_pct,'s-',color='#B23A48',label='Dòng bị cách ly (%)')
        ax[0].set_xlabel('Độ bao phủ danh mục (%)');ax[0].set_ylabel('% dòng thô');ax[0].legend(fontsize=9,frameon=False)
        ax[0].set_title('Dữ liệu mất khi danh mục khuyết')
        ax[1].plot(coverage.catalog_coverage*100,coverage.relative_revenue_error_pct,'o-',color=ORANGE)
        ax[1].axhline(0,color=GREY,lw=1,ls='--')
        ax[1].set_xlabel('Độ bao phủ danh mục (%)');ax[1].set_ylabel('Sai lệch giá trị bán hàng (%)')
        ax[1].set_title('Giá trị bán hàng bị thiếu theo mức khuyết')
        save(fig,'12_catalog_coverage.png','Đơn vị: dòng bán hàng. Danh mục bị che theo nguyên dòng sách, và dòng giao dịch của sách đó mất thuộc tính như một phép nối thất bại.')

    # --- PR3 figure: the three intervals, side by side, because they are easy to conflate ----
    if boot is not None and len(boot):
        rows=[('rating_book_qty_r','Tương quan điểm–lượng (cấp sách)'),
              ('discount_qty_r','Tương quan giảm giá–lượng (cấp dòng)'),
              ('q4_share','Tỷ trọng quý IV (%)')]
        fig,ax=plt.subplots(figsize=(11,4.8))
        y=np.arange(len(rows))
        for i,(metric,label) in enumerate(rows):
            r=boot[boot.metric.eq(metric)].iloc[0]
            ax.plot([r.ci_low,r.ci_high],[i,i],color=BLUE,lw=7,solid_capstyle='butt')
            ax.plot(r.point,i,'o',color='#B23A48',ms=8,zorder=3)
            ax.text(r.ci_high+r.ci_width*.06,i,f'[{r.ci_low:.3f}; {r.ci_high:.3f}]',
                    va='center',fontsize=9)
        ax.set_yticks(y,[l for _,l in rows]);ax.set_ylim(-.7,len(rows)-.3)
        ax.set_xlabel('Giá trị ước lượng');ax.grid(axis='x',alpha=.25)
        ax.set_title(f'Khoảng bootstrap {int(boot.n_boot.max()):,} lần rút lại, độ tin cậy 95%')
        ax.text(.99,.02,'Thanh: khoảng bootstrap. Chấm: giá trị trên mẫu đã làm sạch.',
                transform=ax.transAxes,ha='right',fontsize=9,color='#53606C')
        save(fig,'13_bootstrap_ci.png',
             'Đơn vị rút lại: dòng bán hàng, riêng tương quan cấp sách rút lại theo đầu sách. '
             'Đây là biến thiên lấy mẫu trong mẫu mô phỏng, KHÔNG phải khoảng tin cậy thị trường '
             'và không phải khoảng null ở Hình trước.')
