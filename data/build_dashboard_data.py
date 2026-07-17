"""
Merge user_info.csv + parkviewgreen_v2_user_coupon(1).csv
into BI_Dashboard_Ready_Data.csv — pure Python, no pandas needed.
"""
import csv
import os
from datetime import datetime

DATA_DIR = os.path.dirname(os.path.abspath(__file__))

coupon_path = os.path.join(DATA_DIR, 'parkviewgreen_v2_user_coupon(1).csv')
user_path = os.path.join(DATA_DIR, 'user_info.csv')
out_path = os.path.join(DATA_DIR, 'BI_Dashboard_Ready_Data.csv')

# --- Coupon type normalization ---
def normalize_coupon_type(raw):
    if not raw:
        return 'other'
    r = raw.strip().lower()
    core_types = {
        'daily_parking_coupon',
        'user_exchange',
        'consumption_parking_coupon',
        'upgradelevel_parking_coupon',
    }
    if r in core_types:
        return r
    return 'other'

# --- Level mapping ---
LEVEL_MAP = {
    '1001': '绿意会员',
    '1002': '悦意会员',
    '1003': '菁英会员',
    '1004': '菁英会员',
    '0': '平台会员',
    '': '平台会员',
}

def birth_to_age(bday_str):
    if not bday_str:
        return '未知'
    s = bday_str.strip()
    if not s:
        return '未知'
    try:
        if s.isdigit():
            ts = int(s)
            if len(s) > 10:
                ts = ts // 1000
            birth = datetime.fromtimestamp(ts)
        else:
            birth = datetime.strptime(s.split()[0], '%Y-%m-%d')
        year = birth.year
        if year >= 2000:
            return '00后'
        elif year >= 1990:
            return '90后'
        elif year >= 1980:
            return '80后'
        elif year >= 1970:
            return '70后'
        else:
            return '其他'
    except Exception:
        return '未知'

# --- Load user info into dict keyed by userid ---
user_dict = {}
with open(user_path, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        uid = row.get('id', '')
        user_dict[uid] = {
            'level': row.get('level', ''),
            'sex': row.get('sex', '未知'),
            'birthday': row.get('birthday', ''),
            'current_integral': row.get('current_integral', '0'),
        }

print(f'Loaded {len(user_dict)} users')

# --- Process coupon rows and write output ---
count = 0
type_counts = {}
level_counts = {}

with open(coupon_path, 'r', encoding='utf-8') as fin, \
     open(out_path, 'w', encoding='utf-8', newline='') as fout:
    
    reader = csv.DictReader(fin)
    fieldnames = [
        'coupon_record_id', 'userid', 'coupon_type', 'coupon_status',
        'create_time', 'update_time', 'sex', 'level',
        'current_integral', 'age_group'
    ]
    writer = csv.DictWriter(fout, fieldnames=fieldnames)
    writer.writeheader()
    
    for row in reader:
        uid = row.get('userid', '')
        u = user_dict.get(uid, {})
        
        raw_level = u.get('level', '')
        biz_level = LEVEL_MAP.get(str(raw_level), '平台会员')
        
        ctype = normalize_coupon_type(row.get('remark', ''))
        type_counts[ctype] = type_counts.get(ctype, 0) + 1
        level_counts[biz_level] = level_counts.get(biz_level, 0) + 1
        
        out_row = {
            'coupon_record_id': row.get('id', ''),
            'userid': uid,
            'coupon_type': ctype,
            'coupon_status': row.get('status', ''),
            'create_time': row.get('create_time', ''),
            'update_time': row.get('update_time', ''),
            'sex': u.get('sex', '未知') or '未知',
            'level': biz_level,
            'current_integral': u.get('current_integral', '0') or '0',
            'age_group': birth_to_age(u.get('birthday', '')),
        }
        writer.writerow(out_row)
        count += 1

print(f'\nDone. {count} coupon records written to {out_path}')
print(f'\nCoupon types:')
for t, n in sorted(type_counts.items(), key=lambda x: -x[1]):
    print(f'  {t}: {n}')
print(f'\nLevels:')
for t, n in sorted(level_counts.items(), key=lambda x: -x[1]):
    print(f'  {t}: {n}')
