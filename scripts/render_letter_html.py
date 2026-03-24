import argparse, json, os
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


def replace_once(html, old, new):
    if old not in html:
        raise ValueError('pattern not found')
    return html.replace(old, new, 1)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--analysis', required=True)
    ap.add_argument('--template', required=True)
    ap.add_argument('--out', required=True)
    args=ap.parse_args()

    with open(args.analysis,'r',encoding='utf-8') as f:
        d=json.load(f)

    cov=d['coverage']
    bills=d['bills_summary']
    by_inst=d.get('by_instrument_bills',[])

    start=dt_cn_iso(bills.get('start_utc'))
    end=dt_cn_iso(bills.get('end_utc'))
    insts=', '.join(cov.get('instIds') or [])

    net=bills.get('net_total',0)
    fee=bills.get('fee_total',0)

    # pick two symbols for metric tiles
    sym_rows=sorted(by_inst, key=lambda x: x.get('net',0), reverse=True)
    a=sym_rows[0] if len(sym_rows)>0 else {'instId':'','net':0}
    b=sym_rows[1] if len(sym_rows)>1 else {'instId':'','net':0}

    html=open(args.template,'r',encoding='utf-8').read()

    # Minimal, safe replacements (keep structure identical)
    html = replace_once(html, '写给那个还在和市场较劲，<br>但已经比以前更清醒一点的你', '写给那个还在和市场较劲，<br>但愿意开始收边界的你')
    html = replace_once(html, '这不是一份冷冰冰的报告，也不是整改通知。它更像一封被认真排版过的长信：把数据背后的情绪、结构、边界和成长，慢慢摊开给你看。',
                        '这不是报告，也不是宣判。更像一封写给朋友的长信：把你这段时间的节奏、边界、选择与消耗，慢慢摊开。')

    # core judgement stays

    # metric tiles
    html = replace_once(html, 'BTCUSDT 净收益', '合约净收益')
    html = replace_once(html, '+2811.79', fmt_money(net))
    html = replace_once(html, 'ETHUSDT 净结果', '手续费')
    html = replace_once(html, '-1906.67', fmt_money(fee))
    html = replace_once(html, 'ETH 亏损占比', f"{a.get('instId','品种A')} 净结果")
    html = replace_once(html, '83.69%', fmt_money(a.get('net',0)))
    html = replace_once(html, 'XAGUSDT 净结果', f"{b.get('instId','品种B')} 净结果")
    html = replace_once(html, '-2816.81', fmt_money(b.get('net',0)))

    # first paragraph anchor
    html = replace_once(html,
        '几木，这封信我还是不想写成报告，也不想写成什么“整改意见”。前面的那些报告，已经把数字、结构、问题和优点拆得很细了。现在更适合的方式，是坐下来像朋友一样聊一聊：关于交易，关于为什么有些时候你明明知道，却还是会做错；也关于为什么有些时候你其实已经比以前更强了，却还是觉得自己没有变好。',
        f'这封信不想写成报告，也不想写成整改意见。我们就当是坐下来聊一会儿：你这段时间到底在跟市场怎么相处，哪些地方在进步，哪些地方又在消耗。样本覆盖：{start} ～ {end}（北京时间），主要品种：{insts}。'
    )

    os.makedirs(args.out, exist_ok=True)
    out_path=os.path.join(args.out,'result-pages')
    os.makedirs(out_path, exist_ok=True)
    with open(os.path.join(out_path,'letter-version.html'),'w',encoding='utf-8') as f:
        f.write(html)

if __name__=='__main__':
    main()
