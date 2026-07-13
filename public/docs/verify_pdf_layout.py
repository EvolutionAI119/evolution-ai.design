"""Verify patent_figures.pdf layout and formatting"""
import os
import sys

def verify_pdf():
    pdf_path = r'D:\API\AI_3D_Model_Build\EVOLUTION_AI\frontend\public\docs\patent_figures.pdf'

    if not os.path.exists(pdf_path):
        print(f"ERROR: {pdf_path} not found")
        return False

    size_kb = os.path.getsize(pdf_path) / 1024
    mtime = os.path.getmtime(pdf_path)

    # Read raw PDF to check page count and dimensions
    with open(pdf_path, 'rb') as f:
        data = f.read()

    # Count pages
    page_count = 0
    idx = 0
    while True:
        idx = data.find(b'/Type /Page', idx)
        if idx == -1:
            break
        if idx + 11 < len(data) and data[idx+11:idx+12] != b's':
            page_count += 1
        idx += 11

    # Check for MediaBox (page dimensions)
    mediaboxes = []
    idx = 0
    while True:
        idx = data.find(b'/MediaBox', idx)
        if idx == -1:
            break
        end = data.find(b']', idx)
        if end != -1:
            box_str = data[idx:end+1].decode('latin-1', errors='replace')
            mediaboxes.append(box_str)
        idx = end if end != -1 else idx + 1

    # Check for font embedding (fonttype 42)
    has_truetype = b'/FontDescriptor' in data

    # Check for common issues
    issues = []

    if page_count != 12:
        issues.append(f"Page count is {page_count}, expected 12")

    if size_kb < 100:
        issues.append(f"File size {size_kb:.1f}KB seems too small")

    if size_kb > 2000:
        issues.append(f"File size {size_kb:.1f}KB seems too large")

    # Check MediaBox consistency
    unique_boxes = set(mediaboxes)
    if len(unique_boxes) > 1:
        issues.append(f"Inconsistent page sizes: {len(unique_boxes)} different MediaBox values")
        for box in unique_boxes:
            issues.append(f"  {box}")

    # Check for overlapping text markers (Fig. titles)
    fig_titles_found = []
    for i in range(1, 13):
        marker = f'Fig. {i}'.encode('latin-1')
        if marker in data:
            fig_titles_found.append(i)

    missing_figs = [i for i in range(1, 13) if i not in fig_titles_found]
    if missing_figs:
        issues.append(f"Missing figure titles: {missing_figs}")

    # Print report
    print("=" * 60)
    print("  patent_figures.pdf Verification Report")
    print("=" * 60)
    print(f"  File size:      {size_kb:.1f} KB")
    print(f"  Page count:     {page_count}")
    print(f"  TrueType fonts: {'Yes' if has_truetype else 'No'}")
    print(f"  Fig titles:     {len(fig_titles_found)}/12 found")
    if fig_titles_found:
        print(f"  Found:          {fig_titles_found}")
    print(f"  MediaBox count: {len(mediaboxes)}")
    if unique_boxes:
        print(f"  Unique sizes:   {len(unique_boxes)}")
        for box in list(unique_boxes)[:3]:
            print(f"    {box[:80]}")

    if issues:
        print(f"\n  ISSUES ({len(issues)}):")
        for issue in issues:
            print(f"    - {issue}")
    else:
        print(f"\n  All checks PASSED")

    print("=" * 60)
    return len(issues) == 0

if __name__ == '__main__':
    ok = verify_pdf()
    sys.exit(0 if ok else 1)
