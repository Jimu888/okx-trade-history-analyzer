import argparse, json, os
from datetime import datetime, timedelta, timezone

CN_TZ = timezone(timedelta(hours=8))

def iso_to_cn(iso):
    if not iso:
        return 'N/A'
    dt = datetime.fromisoformat(iso)
    return dt.astimezone(CN_TZ).strftime('%Y-%m-%d %H:%M')

def money(x):
    try:
        return f"{float(x):,.2f}"
    except Exception:
        return str(x)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--analysis', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    d = json.load(open(args.analysis,'r',encoding='utf-8'))
    bills = d['bills_summary']
    cov = d['coverage']

    start_cn = iso_to_cn(bills.get('start_utc'))
    end_cn = iso_to_cn(bills.get('end_utc'))
    insts = ', '.join(cov.get('instIds') or [])

    net = money(bills.get('net_total'))
    pnl = money(bills.get('pnl_total'))
    fee = money(bills.get('fee_total'))

    letter = []
    letter.append('# 写给你的一封信（朋友版）\n')
    letter.append('我先说一句真话：我并不觉得你“不会交易”。\n')
    letter.append('我更像是看到：你有反应、有手感、也敢出手。但你现在把自己放在一个很消耗的节奏里：一旦开了交易开关，就很难关掉。\n')
    letter.append(f'这段样本覆盖：{start_cn} ～ {end_cn}（北京时间），主要品种：{insts}。')
    letter.append(f'账单口径净收益 {net} USDT（已实现盈亏 {pnl}，手续费 {fee}）。\n')
    letter.append('我不想把它说成“你冲动”。我更愿意说：你太想在场了。市场永远有理由让你继续出手，而真正磨掉你的，往往是这种停不下来的纠缠。\n')
    letter.append('你现在最需要的，不是更多复杂的技术，而是更硬的边界：更少的出手次数、更少的品种、更少的“为了在场而交易”。\n')
    letter.append('三个很具体的提醒（不浪漫，但管用）：')
    letter.append('1) 给自己一个当天最大交易次数，到点就停。')
    letter.append('2) 主战品种只留 1~2 个，其他进入观察名单。')
    letter.append('3) 每天只复盘一件事：今天哪几笔是“值钱的”（我愿意在未来重复）。\n')
    letter.append('最后一句朋友话：你不缺勇气，你缺刹车。刹车装上，你会的那部分才会留下来。\n')
    letter.append('—— 小棠')

    out_path = os.path.join(args.out, 'LETTER.md')
    with open(out_path,'w',encoding='utf-8') as f:
        f.write('\n'.join(letter))

if __name__ == '__main__':
    main()
