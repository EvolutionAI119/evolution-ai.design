import os, time

def count_pdf_pages(fpath):
    """Count PDF pages by reading raw bytes"""
    with open(fpath, 'rb') as f:
        data = f.read()
    # Count /Type /Page entries (not /Pages)
    count = 0
    idx = 0
    while True:
        idx = data.find(b'/Type /Page', idx)
        if idx == -1:
            break
        # Make sure it's /Page not /Pages
        if idx + 11 < len(data) and data[idx+11:idx+12] != b's':
            count += 1
        idx += 11
    return max(count, 1)

docs_dir = r'D:\API\AI_3D_Model_Build\EVOLUTION_AI\frontend\public\docs'
files = [
    ('patent_request.pdf', 'Request Form'),
    ('patent_specification.pdf', 'Specification'),
    ('patent_claims.pdf', 'Claims'),
    ('patent_abstract.pdf', 'Abstract'),
    ('patent_figures.pdf', 'Figures'),
]

print('=' * 78)
print('  Patent Application Document Inventory Report')
print('  Generated: ' + time.strftime('%Y-%m-%d %H:%M:%S'))
print('=' * 78)
header = '  {:<12} {:<26} {:>6} {:>10} {:>20}'.format('Doc', 'Filename', 'Pages', 'Size(KB)', 'Modified')
print(header)
print('-' * 78)

total_pages = 0
total_size = 0

for fname, label in files:
    fpath = os.path.join(docs_dir, fname)
    if os.path.exists(fpath):
        size_kb = os.path.getsize(fpath) / 1024
        mtime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(os.path.getmtime(fpath)))
        try:
            pages = count_pdf_pages(fpath)
        except Exception:
            pages = 0
        total_pages += pages
        total_size += size_kb
        row = '  {:<12} {:<26} {:>6} {:>10.1f} {:>20}'.format(label, fname, pages, size_kb, mtime)
        print(row)
    else:
        print('  {:<12} {:<26}   NOT FOUND'.format(label, fname))

print('-' * 78)
row = '  {:<12} {:<26} {:>6} {:>10.1f}'.format('TOTAL', '', total_pages, total_size)
print(row)
print('=' * 78)
