from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENRES = ['Kỹ năng sống', 'Văn học', 'Kinh tế - Quản trị', 'Thiếu nhi', 'Tâm lý học', 'Khoa học công nghệ', 'Giáo dục - Ngoại ngữ', 'Lịch sử - Triết học', 'Truyện tranh', 'Nuôi dạy con']
CHANNELS = ['Sàn A', 'Sàn B', 'Sàn C', 'Cửa hàng', 'Website']
# Marketplace channels are the three sàn; Website is a digital channel but not a marketplace.
MARKETPLACE_CHANNELS = CHANNELS[:3]
DIGITAL_CHANNELS = CHANNELS[:3] + ['Website']
PARAMS = {
    'seed': 42, 'n_lines': 6500, 'n_books': 300,
    'start': '2024-01-01', 'end': '2025-12-31',
    'genre_weights': [.20,.18,.15,.13,.09,.06,.07,.04,.05,.03],
    'channel_weights': [.35,.22,.18,.15,.10],
    'discount_strength': 1.0, 'seasonality': True,
    'missing_rate': .02, 'catalog_coverage': 1.0,
    'max_qty_review': 1000, 'replications': 50,
    # Generator constants. They live here so the report can quote the design it actually ran
    # instead of repeating literals; changing one changes the simulation, not just the wording.
    'n_bulk': 8, 'bulk_qty_min': 155, 'bulk_qty_max': 200,
    'n_dup_exact': 130, 'n_dup_format': 25, 'n_conflicts': 5,
    'n_format_genre': 250, 'n_currency_format': 120, 'n_invalid_price': 15,
    'n_invalid_qty': 15, 'invalid_qty_high': 99999, 'invalid_qty_low': -10,
    'catalog_year_min': 2015, 'catalog_year_max': 2023,
    'price_median': 120000, 'price_log_sd': .48,
    'price_min': 45000, 'price_max': 350000,
    'rating_beta_a': 8, 'rating_beta_b': 2,
    'lam_base': 1.5, 'lam_price_scale': 200000,
    'season_peak': 1.7, 'season_shoulder': 1.3,
}
PRICE_LABELS = ['Dưới 80.000', '80.000–200.000', 'Trên 200.000']
RATING_LABELS = ['Dưới 3,0', '3,0–<4,0', '4,0–<4,5', 'Từ 4,5']
DISCOUNT_LABELS = ['0–5%', '>5–15%', '>15–25%', '>25–40%']
CAT_FIELDS = ['ten_sach','the_loai','tac_gia','nha_xuat_ban','nam_xuat_ban','gia_goc','diem_danh_gia']
