# -*- coding: utf-8 -*-
# merge_normalize.py -- merge + clean 2GIS/Yandex parser CSV exports into one lead base.
# ASCII-only source (Windows consoles in cp1251 mangle Cyrillic string literals in .py).
# Column roles are detected BY CONTENT (phone/site/email regex), name = first column,
# so the script does not hardcode any Cyrillic header names and survives schema changes.
#
# Usage:
#   py merge_normalize.py OUT.csv IN1.csv [IN2.csv ...]
#   py merge_normalize.py OUT.csv "rawdir/*.csv"
#   py merge_normalize.py OUT.csv IN1.csv --only-with-phone
#
# Side effect: writes OUT.csv (utf-8-sig) + OUT.summary.md next to it.

import sys, csv, re, glob, os

PHONE_RE = re.compile(r'\+?\d[\d\s\-()]{6,}\d')
URL_RE   = re.compile(r'(https?://|www\.)', re.I)
EMAIL_RE = re.compile(r'[^@\s,;]+@[^@\s,;]+\.[^@\s,;]+')

def read_csv(path):
    with open(path, 'r', encoding='utf-8-sig', newline='') as f:
        rows = list(csv.reader(f))
    if not rows:
        return [], []
    return rows[0], [r for r in rows[1:] if any(c.strip() for c in r)]

def detect_col(header, body, test, min_frac=0.25):
    best, best_hits = -1, 0
    for c in range(len(header)):
        hits = total = 0
        for row in body:
            if c < len(row) and row[c].strip():
                total += 1
                if test(row[c]):
                    hits += 1
        if total and hits / total >= min_frac and hits > best_hits:
            best, best_hits = c, hits
    return best

def norm_phone(s):
    # take first phone-looking token, normalize Russian numbers to +7XXXXXXXXXX
    m = PHONE_RE.search(s or '')
    if not m:
        return ''
    digits = re.sub(r'\D', '', m.group(0))
    if len(digits) == 11 and digits[0] in '78':
        return '+7' + digits[1:]
    if len(digits) == 10:
        return '+7' + digits
    if digits:
        return '+' + digits
    return ''

def cell(row, idx):
    return row[idx].strip() if (idx >= 0 and idx < len(row)) else ''

def main():
    args = [a for a in sys.argv[1:]]
    only_phone = '--only-with-phone' in args
    args = [a for a in args if a != '--only-with-phone']
    if len(args) < 2:
        print('usage: py merge_normalize.py OUT.csv IN1.csv [IN2.csv ...] [--only-with-phone]')
        sys.exit(2)
    out_path, ins = args[0], args[1:]

    files = []
    for pat in ins:
        hit = glob.glob(pat)
        files.extend(hit if hit else [pat])
    files = [f for f in files if os.path.isfile(f)]
    if not files:
        print('no input files found')
        sys.exit(1)

    header = None
    all_body = []
    for f in files:
        h, body = read_csv(f)
        if header is None and h:
            header = h
        all_body.extend(body)

    if not header:
        print('empty / headerless input')
        sys.exit(1)

    phone_c = detect_col(header, all_body, lambda v: bool(PHONE_RE.search(v)))
    site_c  = detect_col(header, all_body, lambda v: bool(URL_RE.search(v)))
    email_c = detect_col(header, all_body, lambda v: bool(EMAIL_RE.search(v)))
    name_c  = 0

    seen = set()
    clean = []
    for row in all_body:
        name = cell(row, name_c)
        phone = norm_phone(cell(row, phone_c)) if phone_c >= 0 else ''
        if only_phone and not phone:
            continue
        key = (name.lower(), phone)
        if key in seen:
            continue
        seen.add(key)
        # write normalized phone back into its column if detected
        if phone_c >= 0:
            while len(row) <= phone_c:
                row.append('')
            if phone:
                row[phone_c] = phone
        clean.append(row)

    with open(out_path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(clean)

    n = len(clean)
    with_phone = sum(1 for r in clean if phone_c >= 0 and cell(r, phone_c))
    with_site  = sum(1 for r in clean if site_c  >= 0 and cell(r, site_c))
    with_email = sum(1 for r in clean if email_c >= 0 and cell(r, email_c))
    raw_total = len(all_body)

    def pct(x):
        return ('%.0f%%' % (100.0 * x / n)) if n else '0%'

    summ = [
        '# Lead base summary',
        '',
        '- source files: %d' % len(files),
        '- raw rows (pre-dedup): %d' % raw_total,
        '- clean rows: %d' % n,
        '- with phone: %d (%s)' % (with_phone, pct(with_phone)),
        '- with site: %d (%s)' % (with_site, pct(with_site)),
        '- with email: %d (%s)' % (with_email, pct(with_email)),
        '- detected cols -> name=%d phone=%d site=%d email=%d' % (name_c, phone_c, site_c, email_c),
        '- output: %s' % out_path,
    ]
    summ_path = os.path.splitext(out_path)[0] + '.summary.md'
    with open(summ_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(summ) + '\n')

    # console: ASCII only
    print('OK merged=%d clean=%d phone=%d site=%d email=%d' % (raw_total, n, with_phone, with_site, with_email))
    print('out: ' + out_path)
    print('summary: ' + summ_path)

if __name__ == '__main__':
    main()
