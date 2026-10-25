"""Read the public vegetable wholesale report; keep the previous data on failure."""
import datetime, html, json, re, subprocess
from pathlib import Path
SOURCE = 'https://www.taladsrimuang.com/site/product/report_all.php?id=1'
def parse_report(raw):
    date = re.search(r'Date\s*(?:&nbsp;|\s)*(\d{4}-\d{2}-\d{2})', raw)
    if not date:
        raise ValueError('Source report date missing')
    table = re.search(r'<table\b[^>]*class="product_re_table"[^>]*>(.*?)</table>', raw, re.S)
    if not table:
        raise ValueError('Source price table missing')
    items = []
    for row in re.findall(r'<td\b[^>]*padding:[^>]*>(.*?)(?=</tr>)', table.group(1), re.S):
        cells = re.findall(r'<span\b[^>]*class="blank_th"[^>]*>(.*?)</span>', row, re.S)
        if len(cells) != 3:
            continue
        name, price, unit = [' '.join(html.unescape(re.sub('<[^>]+>', '', c)).split()) for c in cells]
        match = re.fullmatch(r'([\d,]+(?:\.\d+)?)(?:\s*-\s*([\d,]+(?:\.\d+)?))?', price)
        if not match:
            continue
        low = float(match[1].replace(',', ''))
        high = float((match[2] or match[1]).replace(',', ''))
        if high > 0 and low <= high:
            items.append(dict(name=name, low=low, high=high, unit=unit))
    if len(items) < 10:
        raise ValueError('Too few valid prices; retaining previous data')
    items.sort(key=lambda a: (-a['high'], a['name']))
    return dict(source=SOURCE, date=date[1], category='อาคารผัก', total=len(items), items=items[:10])
if __name__ == '__main__':
    raw = subprocess.run(['curl','--fail','--location','--silent','--show-error','--max-time','30',SOURCE], check=True, capture_output=True).stdout.decode('utf-8')
    result = parse_report(raw)
    result['checked_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    target = Path(__file__).resolve().parents[1] / 'data/market-prices.json'
    target.parent.mkdir(exist_ok=True)
    tmp = target.with_suffix('.tmp')
    tmp.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    tmp.replace(target)
    print(f"Updated {len(result['items'])} of {result['total']} products, report date {result['date']}")
