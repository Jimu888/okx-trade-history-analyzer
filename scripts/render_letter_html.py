import argparse
import html
import json
import os
import re
from datetime import datetime, timedelta, timezone

CN_TZ = timezone(timedelta(hours=8))


def fmt_money(x):
    try:
        return f"{float(x):+.2f}"
    except Exception:
        return str(x)


def dt_cn_iso(iso):
    if not iso:
        return ''
    dt = datetime.fromisoformat(iso)
    return dt.astimezone(CN_TZ).strftime('%Y-%m-%d %H:%M')


def replace_once(html_text, old, new):
    if old not in html_text:
        raise ValueError('pattern not found')
    return html_text.replace(old, new, 1)


def replace_main_content(template_html, new_main):
    pattern = re.compile(r'<main class="wrap">.*?</main>', re.S)
    if not pattern.search(template_html):
        raise ValueError('main.wrap not found in template')
    return pattern.sub(new_main, template_html, count=1)


def read_letter_markdown(path):
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read().strip()

    title = '写给你的一封信'
    subtitle = ''
    blocks = []
    current = []

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if line.startswith('# '):
            title = line[2:].strip() or title
            continue
        if line.startswith('> '):
            subtitle = line[2:].strip()
            continue
        if not line.strip():
            if current:
                blocks.append('\n'.join(current).strip())
                current = []
            continue
        current.append(line)

    if current:
        blocks.append('\n'.join(current).strip())

    return title, subtitle, blocks


def make_metrics(analysis):
    bills = analysis.get('bills_summary', {})
    orders = analysis.get('orders_summary', {})
    fills = analysis.get('fills_summary', {})
    by_inst = analysis.get('by_instrument_bills', [])
    top_inst = by_inst[0].get('instId', '主力品种') if by_inst else '主力品种'

    return [
        ('合约净收益', fmt_money(bills.get('net_total', 0))),
        ('手续费', fmt_money(bills.get('fee_total', 0))),
        ('活跃交易日', str(fills.get('active_days', 0))),
        (f'{top_inst} 净结果', fmt_money(by_inst[0].get('net', 0) if by_inst else 0)),
        ('订单胜率', f'{float(orders.get("quality_order", {}).get("win_rate", 0)) * 100:.1f}%'),
        ('最大回撤', fmt_money(orders.get('equity_order', {}).get('max_drawdown', 0))),
    ]


def block_to_html(block):
    if block.startswith('——'):
        return f'<p class="signature">{html.escape(block)}</p>'
    if len(block) <= 48:
        return f'<div class="quote">{html.escape(block)}</div>'
    lines = [html.escape(line.strip()) for line in block.splitlines() if line.strip()]
    return f'<p>{"<br>".join(lines)}</p>'


def render_agent_letter_page(template_html, analysis, letter_md_path):
    title, subtitle, blocks = read_letter_markdown(letter_md_path)
    cov = analysis.get('coverage', {})
    insts = ', '.join(cov.get('instIds') or []) or '样本中无明确品种'
    metrics = make_metrics(analysis)

    intro_block = blocks[0] if blocks else '这封信基于本次交易数据分析生成。'
    body_blocks = blocks[1:] if len(blocks) > 1 else []

    metric_html = '\n'.join(
        f'''<div class="metric">
                <div class="label">{html.escape(label)}</div>
                <div class="value">{html.escape(value)}</div>
              </div>'''
        for label, value in metrics[:4]
    )

    content_html = '\n'.join(block_to_html(block) for block in body_blocks if block.strip())
    if not content_html:
        content_html = '<p>本次信件没有生成可展示的正文。</p>'

    start = dt_cn_iso(cov.get('time_range_cn', {}).get('start'))
    end = dt_cn_iso(cov.get('time_range_cn', {}).get('end'))
    range_text = f'{start} ～ {end}（北京时间）' if start and end else '时间范围待确认'

    new_main = f'''
  <main class="wrap">
    <section class="hero">
      <div class="hero-card">
        <div class="eyebrow">Letter · Agent Written · Data Grounded</div>
        <h1>{html.escape(title)}</h1>
        <p class="subtitle">
          {html.escape(subtitle or "这封信的正文由 agent 基于交易分析报告生成，页面仅复用模板视觉风格。")}
        </p>

        <div class="hero-grid">
          <div class="panel">
            <h3>开场观察</h3>
            <p class="keyline">{html.escape(intro_block)}</p>
          </div>
          <div class="panel">
            <h3>文中关键数字</h3>
            <div class="metrics">
              {metric_html}
            </div>
          </div>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="section-grid">
        <aside class="sticky-card">
          <div class="index">01</div>
          <h2>来自数据的这封信</h2>
          <p>数据时段：{html.escape(range_text)}。主要品种：{html.escape(insts)}。这个页面沿用模板的视觉风格，但正文内容来自 agent 对报告的阅读与归纳。</p>
        </aside>
        <article class="content-card">
          {content_html}
        </article>
      </div>
    </section>

    <footer>
      <div class="ending">
        <p>{html.escape(intro_block)}</p>
        <div class="signature">{html.escape(title)}</div>
      </div>
    </footer>
  </main>'''

    page = replace_main_content(template_html, new_main)
    page = re.sub(r'<title>.*?</title>', f'<title>{html.escape(title)}</title>', page, count=1)
    return page


def render_template_fallback(template_html, analysis):
    cov = analysis['coverage']
    bills = analysis['bills_summary']
    by_inst = analysis.get('by_instrument_bills', [])

    start = dt_cn_iso(bills.get('start_utc'))
    end = dt_cn_iso(bills.get('end_utc'))
    insts = ', '.join(cov.get('instIds') or [])

    net = bills.get('net_total', 0)
    fee = bills.get('fee_total', 0)

    sym_rows = sorted(by_inst, key=lambda x: x.get('net', 0), reverse=True)
    a = sym_rows[0] if len(sym_rows) > 0 else {'instId': '', 'net': 0}
    b = sym_rows[1] if len(sym_rows) > 1 else {'instId': '', 'net': 0}

    html_text = template_html
    html_text = replace_once(html_text, '写给那个还在和市场较劲，<br>但已经比以前更清醒一点的你', '写给那个还在和市场较劲，<br>但愿意开始收边界的你')
    html_text = replace_once(html_text, '这不是一份冷冰冰的报告，也不是整改通知。它更像一封被认真排版过的长信：把数据背后的情绪、结构、边界和成长，慢慢摊开给你看。',
                             '这不是报告，也不是宣判。更像一封写给朋友的长信：把你这段时间的节奏、边界、选择与消耗，慢慢摊开。')
    html_text = replace_once(html_text, 'BTCUSDT 净收益', '合约净收益')
    html_text = replace_once(html_text, '+2811.79', fmt_money(net))
    html_text = replace_once(html_text, 'ETHUSDT 净结果', '手续费')
    html_text = replace_once(html_text, '-1906.67', fmt_money(fee))
    html_text = replace_once(html_text, 'ETH 亏损占比', f"{a.get('instId','品种A')} 净结果")
    html_text = replace_once(html_text, '83.69%', fmt_money(a.get('net', 0)))
    html_text = replace_once(html_text, 'XAGUSDT 净结果', f"{b.get('instId','品种B')} 净结果")
    html_text = replace_once(html_text, '-2816.81', fmt_money(b.get('net', 0)))
    html_text = replace_once(
        html_text,
        '几木，这封信我还是不想写成报告，也不想写成什么“整改意见”。前面的那些报告，已经把数字、结构、问题和优点拆得很细了。现在更适合的方式，是坐下来像朋友一样聊一聊：关于交易，关于为什么有些时候你明明知道，却还是会做错；也关于为什么有些时候你其实已经比以前更强了，却还是觉得自己没有变好。',
        f'这封信不想写成报告，也不想写成整改意见。我们就当是坐下来聊一会儿：你这段时间到底在跟市场怎么相处，哪些地方在进步，哪些地方又在消耗。样本覆盖：{start} ～ {end}（北京时间），主要品种：{insts}。'
    )
    return html_text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--analysis', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--template', required=True)
    ap.add_argument('--letter-md')
    args = ap.parse_args()

    with open(args.analysis, 'r', encoding='utf-8') as f:
        analysis = json.load(f)
    with open(args.template, 'r', encoding='utf-8') as f:
        template_html = f.read()

    if args.letter_md and os.path.exists(args.letter_md):
        html_text = render_agent_letter_page(template_html, analysis, args.letter_md)
    else:
        html_text = render_template_fallback(template_html, analysis)

    os.makedirs(args.out, exist_ok=True)
    out_path = os.path.join(args.out, 'result-pages')
    os.makedirs(out_path, exist_ok=True)
    with open(os.path.join(out_path, 'letter-version.html'), 'w', encoding='utf-8') as f:
        f.write(html_text)


if __name__ == '__main__':
    main()
