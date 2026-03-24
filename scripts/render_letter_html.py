import argparse, json, os
from datetime import datetime, timedelta, timezone

CN_TZ = timezone(timedelta(hours=8))

def iso_to_cn(iso):
    if not iso:
        return 'N/A'
    dt = datetime.fromisoformat(iso)
    return dt.astimezone(CN_TZ).strftime('%Y-%m-%d %H:%M')

def fmt_money(x):
    try:
        v=float(x)
        return f"{v:+.2f}"
    except Exception:
        return str(x)


def replace_once(html, old, new):
    if old not in html:
        raise ValueError(f"pattern not found: {old[:60]}")
    return html.replace(old, new, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--analysis', required=True)
    ap.add_argument('--template', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    d = json.load(open(args.analysis,'r',encoding='utf-8'))
    cov = d['coverage']
    bills = d['bills_summary']
    by_sym = d.get('by_instrument_bills', [])

    start_cn = iso_to_cn(bills.get('start_utc'))
    end_cn = iso_to_cn(bills.get('end_utc'))
    symbols = ', '.join(cov.get('instIds') or [])

    net = fmt_money(bills.get('net_total'))
    fee = fmt_money(bills.get('fee_total'))

    per = {row.get('instId'): row.get('net', 0) for row in by_sym}
    eth = fmt_money(per.get('ETH-USDT-SWAP', 0))
    okb = fmt_money(per.get('OKB-USDT-SWAP', 0))

    # Use the same template and only replace specific text blocks + metric panel.
    html = open(args.template,'r',encoding='utf-8').read()

    html = replace_once(html,
        '写给那个还在和市场较劲，<br>但已经比以前更清醒一点的你',
        '写给那个还在和市场较劲，<br>但愿意开始收边界的你'
    )

    html = replace_once(html,
        '这不是一份冷冰冰的报告，也不是整改通知。它更像一封被认真排版过的长信：把数据背后的情绪、结构、边界和成长，慢慢摊开给你看。',
        '这不是报告，也不是宣判。更像一封写给朋友的长信：把你这段时间的节奏、边界、选择与消耗，慢慢摊开。'
    )

    # metrics panel (4)
    html = replace_once(html, 'BTCUSDT 净收益', '合约净收益')
    html = replace_once(html, '+2811.79', net)
    html = replace_once(html, 'ETHUSDT 净结果', '手续费')
    html = replace_once(html, '-1906.67', fee)
    html = replace_once(html, 'ETH 亏损占比', 'ETH 净结果')
    html = replace_once(html, '83.69%', eth)
    html = replace_once(html, 'XAGUSDT 净结果', 'OKB 净结果')
    html = replace_once(html, '-2816.81', okb)

    # Replace a few key paragraphs in section 01 only (keep the whole layout unchanged)
    html = replace_once(html,
        '几木，这封信我还是不想写成报告，也不想写成什么“整改意见”。前面的那些报告，已经把数字、结构、问题和优点拆得很细了。现在更适合的方式，是坐下来像朋友一样聊一聊：关于交易，关于为什么有些时候你明明知道，却还是会做错；也关于为什么有些时候你其实已经比以前更强了，却还是觉得自己没有变好。',
        f'这封信我不想写成报告。更像是朋友之间坐下来聊一会儿：你这段时间到底在跟市场怎么相处，哪些地方已经更清醒了，哪些地方又在反复把你拖回老节奏。'
    )

    html = replace_once(html,
        '如果你真的是完全不会交易，数据不会长成现在这样。一个完全没有判断力的人，历史里通常看不到任何值得保留的盈利段，也看不到某些品种、某些阶段明显更像样的输出。你现在的问题，不是完全没有 edge，而是你的 edge 还太脆，很容易被频率、情绪、成本、注意力分散这些东西磨掉。',
        f'我并不觉得你是一个“不会交易的人”。你真正的问题更像是缺边界：把值得做的和不值得做的混在一起，久了就只剩消耗。'
    )

    html = replace_once(html,
        '比如 <span class="highlight">BTCUSDT 这 90 天依然留下了 +2811.79 的净收益</span>。这件事本身已经证明：你不是抓不到真正的机会，也不是完全没有能力。你是有刀的，只是很多时候，没有把刀留给最值得砍的地方。',
        f'样本覆盖：{start_cn} ～ {end_cn}（北京时间），主要品种：{symbols}。这些数字不重要到要背下来，但足够说明：频率和成本正在持续磨你。'
    )

    out_dir = os.path.join(args.out, 'result-pages')
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, 'letter-version.html')
    with open(out_path,'w',encoding='utf-8') as f:
        f.write(html)

if __name__=='__main__':
    main()
