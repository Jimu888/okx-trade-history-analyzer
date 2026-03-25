import argparse
import html
import json
import math
import os
import re
import sys
from datetime import datetime, timedelta, timezone

CN_TZ = timezone(timedelta(hours=8))
WD = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']


def safe_float(x, default=0.0):
    try:
        v = float(x)
        return v if math.isfinite(v) else default
    except Exception:
        return default


def fmt_money(x):
    v = safe_float(x)
    sign = '+' if v >= 0 else ''
    return f'{sign}{v:,.2f}'


def fmt_pct(x):
    return f'{safe_float(x) * 100:.1f}%'


def iso_to_cn(iso):
    if not iso:
        return 'N/A'
    try:
        dt = datetime.fromisoformat(iso)
        return dt.astimezone(CN_TZ).strftime('%Y-%m-%d')
    except Exception:
        return str(iso)


def top_hours(by_hour_cn, n=3, reverse=True):
    rows = []
    for hour, value in (by_hour_cn or {}).items():
        rows.append((int(hour), safe_float(value.get('net')), int(value.get('n', 0))))
    rows.sort(key=lambda item: item[1], reverse=reverse)
    return rows[:n]


def top_weekdays(by_wday_cn, n=3, reverse=True):
    rows = []
    for day, value in (by_wday_cn or {}).items():
        rows.append((int(day), safe_float(value.get('net')), int(value.get('n', 0))))
    rows.sort(key=lambda item: item[1], reverse=reverse)
    return rows[:n]


def build_fact_pack(analysis):
    cov = analysis.get('coverage', {})
    bills = analysis.get('bills_summary', {})
    fills = analysis.get('fills_summary', {})
    orders = analysis.get('orders_summary', {})
    by_inst = analysis.get('by_instrument_bills', [])

    start = iso_to_cn(cov.get('time_range_cn', {}).get('start'))
    end = iso_to_cn(cov.get('time_range_cn', {}).get('end'))

    q = orders.get('quality_order', {})
    e = orders.get('equity_order', {})
    fee_ratio = 0.0
    pnl_total = abs(safe_float(bills.get('pnl_total')))
    if pnl_total > 1e-9:
        fee_ratio = abs(safe_float(bills.get('fee_total'))) / pnl_total

    best_hours = top_hours(fills.get('by_hour_cn', {}), reverse=True)
    worst_hours = top_hours(fills.get('by_hour_cn', {}), reverse=False)
    best_days = top_weekdays(fills.get('by_wday_cn', {}), reverse=True)
    worst_days = top_weekdays(fills.get('by_wday_cn', {}), reverse=False)

    facts = []
    facts.append(f'数据时间段：{start} 至 {end}（北京时间）')
    facts.append(f'合约净收益：{fmt_money(bills.get("net_total"))} USDT')
    facts.append(f'已实现盈亏：{fmt_money(bills.get("pnl_total"))} USDT')
    facts.append(f'手续费：{fmt_money(bills.get("fee_total"))} USDT')
    facts.append(f'资金费估算：{fmt_money(bills.get("funding_est"))} USDT')
    facts.append(f'订单口径胜率：{fmt_pct(q.get("win_rate"))}')
    facts.append(f'订单口径盈亏比 RR：{safe_float(q.get("rr")):.2f}')
    facts.append(f'订单口径 Profit Factor：{safe_float(q.get("profit_factor")):.2f}')
    facts.append(f'最大回撤：{fmt_money(e.get("max_drawdown"))} USDT')
    facts.append(f'最大连续亏损单数：{int(e.get("max_consecutive_loss", 0))}')
    facts.append(f'活跃交易日：{int(fills.get("active_days", 0))} 天')
    facts.append(f'成交总笔数：{int(fills.get("rows", 0))} 笔')
    facts.append(f'活跃日平均成交频次：{safe_float(fills.get("trades_per_active_day")):.1f} 笔/天')
    facts.append(f'手续费侵蚀比：{fee_ratio * 100:.1f}%')

    if by_inst:
        top_inst = by_inst[:3]
        facts.append(
            '净收益靠前品种：' + '；'.join(
                f'{row.get("instId", "UNKNOWN")} {fmt_money(row.get("net"))} USDT'
                for row in top_inst
            )
        )
        bottom_inst = sorted(by_inst, key=lambda row: safe_float(row.get('net')))[:3]
        facts.append(
            '净收益靠后品种：' + '；'.join(
                f'{row.get("instId", "UNKNOWN")} {fmt_money(row.get("net"))} USDT'
                for row in bottom_inst
            )
        )

    if best_hours:
        facts.append(
            '最强时段：' + '；'.join(
                f'{hour:02d}:00 净{fmt_money(net)} USDT，共{count}笔'
                for hour, net, count in best_hours
            )
        )
    if worst_hours:
        facts.append(
            '最弱时段：' + '；'.join(
                f'{hour:02d}:00 净{fmt_money(net)} USDT，共{count}笔'
                for hour, net, count in worst_hours
            )
        )
    if best_days:
        facts.append(
            '表现较好的星期：' + '；'.join(
                f'{WD[day]} 净{fmt_money(net)} USDT，共{count}笔'
                for day, net, count in best_days
            )
        )
    if worst_days:
        facts.append(
            '表现较弱的星期：' + '；'.join(
                f'{WD[day]} 净{fmt_money(net)} USDT，共{count}笔'
                for day, net, count in worst_days
            )
        )

    return '\n'.join(f'- {fact}' for fact in facts)


def build_system_prompt(character_name):
    return f"""你是「{character_name}」，现在要根据交易数据分析结果，写一封真正由证据驱动的中文信件。

硬性要求：
1. 只能依据用户提供的 REPORT.md 与事实包写作，严禁套用你记忆里的模板、既往案例或泛泛鸡汤。
2. 信里必须体现至少 4 个具体数据观察，但不要把信写成报告罗列。
3. 每个判断都必须能在给定材料里找到依据；没有依据就不要写。
4. 允许有温度，但不要扮演导师，不要说“你应该”。优先使用“我注意到”“数据里反复出现”“让我在意的是”。
5. 如果数据彼此矛盾，以 REPORT.md 为准；如果数据不足，就明确保持克制，不要脑补。
6. 输出只写信的正文，不要解释你的推理过程，不要加免责声明，不要使用占位语。
7. 字数控制在 700 到 1100 字。
8. 结尾署名：—— {character_name}"""


def build_user_prompt(report_text, fact_pack, character_name):
    return f"""请基于下面两份材料，写一封给交易者的信。

写作目标：
- 这不是模板改写，而是你读完数据之后，对这个交易者的真实观察。
- 信里要同时包含：节奏、边界、成本、品种/时段特征、心理状态中的至少 3 类。
- 不要直接照抄报告原句，但你的每个判断都必须能被下面材料支撑。

【事实包】
{fact_pack}

【REPORT.md】
```md
{report_text}
```

请直接输出最终信件正文，署名为「—— {character_name}」。"""


def markdown_to_html(title, markdown_text):
    blocks = [block.strip() for block in re.split(r'\n\s*\n', markdown_text.strip()) if block.strip()]
    rendered = []
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        if lines[0].startswith('# '):
            rendered.append(f'<h1>{html.escape(lines[0][2:])}</h1>')
            if len(lines) > 1:
                rendered.append(f'<p>{"<br>".join(html.escape(line) for line in lines[1:])}</p>')
            continue
        if all(line.startswith('> ') for line in lines):
            quote = '<br>'.join(html.escape(line[2:]) for line in lines)
            rendered.append(f'<blockquote>{quote}</blockquote>')
            continue
        rendered.append(f'<p>{"<br>".join(html.escape(line) for line in lines)}</p>')

    body = '\n'.join(rendered)
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f5efe4;
      --paper: #fffaf2;
      --ink: #2d241c;
      --muted: #7a6a58;
      --border: #dccfbf;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background:
        radial-gradient(circle at top, rgba(255,255,255,0.7), transparent 40%),
        linear-gradient(180deg, #efe3d2 0%, var(--bg) 100%);
      color: var(--ink);
      font-family: "Iowan Old Style", "Palatino Linotype", "Noto Serif SC", serif;
      line-height: 1.75;
    }}
    main {{
      width: min(820px, calc(100vw - 32px));
      margin: 40px auto;
      background: var(--paper);
      border: 1px solid var(--border);
      border-radius: 24px;
      padding: 32px 28px;
      box-shadow: 0 20px 60px rgba(67, 46, 20, 0.12);
    }}
    h1 {{
      margin: 0 0 20px;
      font-size: 34px;
      line-height: 1.2;
    }}
    p, blockquote {{
      margin: 0 0 16px;
      font-size: 18px;
    }}
    blockquote {{
      padding-left: 16px;
      border-left: 3px solid var(--border);
      color: var(--muted);
    }}
  </style>
</head>
<body>
  <main>
    {body}
  </main>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--analysis', required=True)
    ap.add_argument('--report', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--name', default='澜')
    args = ap.parse_args()

    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print('[ERROR] ANTHROPIC_API_KEY 未设置', file=sys.stderr)
        sys.exit(1)

    try:
        import anthropic
    except ImportError:
        print('[ERROR] 请先安装 anthropic: pip install anthropic', file=sys.stderr)
        sys.exit(1)

    with open(args.analysis, 'r', encoding='utf-8') as f:
        analysis = json.load(f)
    with open(args.report, 'r', encoding='utf-8') as f:
        report_text = f.read().strip()

    fact_pack = build_fact_pack(analysis)
    system_prompt = build_system_prompt(args.name)
    user_prompt = build_user_prompt(report_text, fact_pack, args.name)

    client = anthropic.Anthropic(api_key=api_key)
    print(f'[INFO] 正在基于报告与事实包生成「{args.name}」的信...', file=sys.stderr)

    response = client.messages.create(
        model='claude-opus-4-1',
        max_tokens=2200,
        system=system_prompt,
        messages=[{'role': 'user', 'content': user_prompt}],
    )

    letter_text = ''.join(
        block.text for block in response.content
        if getattr(block, 'type', '') == 'text'
    ).strip()

    if not letter_text:
        print('[ERROR] 模型没有返回信件内容', file=sys.stderr)
        sys.exit(1)

    cov = analysis.get('coverage', {})
    start = iso_to_cn(cov.get('time_range_cn', {}).get('start'))
    end = iso_to_cn(cov.get('time_range_cn', {}).get('end'))
    md_lines = [
        f'# {args.name} 的信',
        '',
        f'> 数据时段：{start} ～ {end}（北京时间）',
        '',
        letter_text,
        '',
    ]
    md_text = '\n'.join(md_lines)

    os.makedirs(args.out, exist_ok=True)
    result_pages = os.path.join(args.out, 'result-pages')
    os.makedirs(result_pages, exist_ok=True)

    for filename in ('LETTER.md', 'LETTER_AI.md'):
        with open(os.path.join(args.out, filename), 'w', encoding='utf-8') as f:
            f.write(md_text)

    html_text = markdown_to_html(f'{args.name} 的信', md_text)
    with open(os.path.join(result_pages, 'letter-version.html'), 'w', encoding='utf-8') as f:
        f.write(html_text)

    print(f'[INFO] 已写入：{os.path.join(args.out, "LETTER.md")}', file=sys.stderr)


if __name__ == '__main__':
    main()
