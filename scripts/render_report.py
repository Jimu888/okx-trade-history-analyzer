import argparse, json, math
from datetime import datetime, timedelta, timezone

CN_TZ = timezone(timedelta(hours=8))
WD = ['周一','周二','周三','周四','周五','周六','周日']

def fmt_money(x):
    try:
        return f"{float(x):,.2f}"
    except Exception:
        return str(x)

def fmt_pct(x):
    try:
        return f"{float(x)*100:.2f}%"
    except Exception:
        return str(x)

def iso_to_cn(iso):
    if not iso:
        return 'N/A'
    dt = datetime.fromisoformat(iso)
    return dt.astimezone(CN_TZ).strftime('%Y-%m-%d %H:%M')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--analysis', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    d = json.load(open(args.analysis,'r',encoding='utf-8'))

    cov = d['coverage']
    bills = d['bills_summary']
    fills = d['fills_summary']
    orders = d['orders_summary']
    by_sym = d['by_instrument_bills']

    start_cn = iso_to_cn(bills.get('start_utc'))
    end_cn = iso_to_cn(bills.get('end_utc'))
    insts = ', '.join(cov.get('instIds') or [])

    # fee ratio
    pnl = float(bills.get('pnl_total') or 0)
    fee = float(bills.get('fee_total') or 0)
    denom = abs(pnl) if abs(pnl) > 1e-9 else 1.0
    fee_ratio = abs(fee) / denom

    lines=[]
    lines.append('# OKX CEX 合约交易分析报告（全面版）\n')

    lines.append('## 0）数据覆盖与口径说明')
    lines.append(f'- 覆盖时间：{start_cn} ～ {end_cn}（北京时间）')
    lines.append('- 覆盖市场：永续合约（SWAP）')
    lines.append(f'- 覆盖品种：{insts if insts else "无"}')
    lines.append(f"- 记录规模：bills {cov.get('bills_rows',0)} 条；fills {cov.get('fills_rows',0)} 条；orders {cov.get('orders_rows',0)} 条\n")

    lines.append('口径说明：')
    lines.append('- **盈亏/手续费/资金费**：以 bills（账单流水）为准（最接近真实资金变动）。')
    lines.append('- **订单口径**：orders 的 pnl+fee 用于估算“交易质量”；订单类型/方向/成交状态用于刻画习惯。')
    lines.append('- **逐笔口径（行为证据）**：fills 的逐笔净变动更适合看频率、时段分布、连亏结构，但比订单口径更噪。\n')

    lines.append('## 1）硬数据层（客观指标）')
    lines.append(f"- 净收益（bills）：{fmt_money(bills.get('net_total'))} USDT")
    lines.append(f"- 已实现盈亏（bills）：{fmt_money(bills.get('pnl_total'))} USDT")
    lines.append(f"- 手续费（bills）：{fmt_money(bills.get('fee_total'))} USDT")
    lines.append(f"- 资金费（估算，bills type=8）：{fmt_money(bills.get('funding_est'))} USDT\n")

    lines.append(f"- 活跃交易日（fills）：{fills.get('active_days',0)} 天")
    lines.append(f"- 成交笔数（fills）：{fills.get('rows',0)} 笔")
    lines.append(f"- 活跃日内日均交易频次：{fills.get('trades_per_active_day',0):.1f} 笔/天\n")

    q_ord = orders.get('quality_order',{})
    e_ord = orders.get('equity_order',{})
    q_fill = fills.get('quality_fill',{})
    e_fill = fills.get('equity_fill',{})

    lines.append('### 1.1 交易质量（两种口径）')
    lines.append(f"- 胜率（订单口径）：{fmt_pct(q_ord.get('win_rate',0))}")
    lines.append(f"- 盈亏比RR（订单口径）：{(q_ord.get('rr',0) if math.isfinite(float(q_ord.get('rr',0) or 0)) else 0):.2f}")
    lines.append(f"- Profit Factor（订单口径）：{(q_ord.get('profit_factor',0) if math.isfinite(float(q_ord.get('profit_factor',0) or 0)) else 0):.2f}")
    lines.append(f"- 最大连续亏损单数（订单口径估算）：{e_ord.get('max_consecutive_loss',0)}")
    lines.append(f"- 最大回撤估算（订单净值曲线）：{fmt_money(e_ord.get('max_drawdown',0))} USDT\n")

    lines.append(f"- 胜率（逐笔口径）：{fmt_pct(q_fill.get('win_rate',0))}")
    lines.append(f"- 盈亏比RR（逐笔口径）：{(q_fill.get('rr',0) if math.isfinite(float(q_fill.get('rr',0) or 0)) else 0):.2f}")
    lines.append(f"- Profit Factor（逐笔口径）：{(q_fill.get('profit_factor',0) if math.isfinite(float(q_fill.get('profit_factor',0) or 0)) else 0):.2f}")
    lines.append(f"- 最大连续亏损笔数（逐笔口径估算）：{e_fill.get('max_consecutive_loss',0)}")
    lines.append(f"- 最大回撤估算（逐笔净值曲线）：{fmt_money(e_fill.get('max_drawdown',0))} USDT\n")

    lines.append('## 2）品种维度（按 bills 资金口径）')
    for row in by_sym:
        lines.append(f"- {row.get('instId')}: 净 {fmt_money(row.get('net'))} / 盈亏 {fmt_money(row.get('pnl'))} / 手续费 {fmt_money(row.get('fee'))} / 记录 {row.get('n')} 条")
    lines.append('')

    lines.append('## 3）时间维度（行为证据：按逐笔成交净变动）')
    by_hour = fills.get('by_hour_cn',{})
    by_wday = fills.get('by_wday_cn',{})

    lines.append('### 3.1 时段（北京时间小时）')
    for h in sorted(by_hour.keys(), key=lambda x:int(x)):
        v=by_hour[h]
        lines.append(f"- {int(h):02d}:00：净 {fmt_money(v.get('net',0))} USDT（{v.get('n',0)} 笔）")
    lines.append('')

    lines.append('### 3.2 星期维度（北京时间）')
    for k in sorted(by_wday.keys(), key=lambda x:int(x)):
        v=by_wday[k]
        lines.append(f"- {WD[int(k)]}：净 {fmt_money(v.get('net',0))} USDT（{v.get('n',0)} 笔）")
    lines.append('')

    lines.append('## 4）订单维度（交易习惯）')
    lines.append(f"- 订单总数：{orders.get('rows',0)}")
    def fmt_counter(dct):
        if not dct: return ''
        return '；'.join([f"{k}:{v}" for k,v in dct.items()])
    lines.append('- 订单状态分布：' + fmt_counter(orders.get('state',{})))
    lines.append('- 订单类型分布：' + fmt_counter(orders.get('ordType',{})))
    lines.append('- 买卖方向分布：' + fmt_counter(orders.get('side',{})))
    lines.append('- 持仓方向分布：' + fmt_counter(orders.get('posSide',{})))
    lines.append('')

    lines.append('## 5）行为模式信号（只基于数据，不做人格定性）')
    tpd = float(fills.get('trades_per_active_day',0) or 0)
    if fills.get('active_days',0) and tpd >= 50:
        lines.append('- 高频/冲动交易信号：明显（活跃天数少，但单日成交密度很高）')
    elif fills.get('active_days',0) and tpd >= 20:
        lines.append('- 高频交易信号：偏高')
    else:
        lines.append('- 高频交易信号：一般')
    lines.append(f"- 成本侵蚀：手续费/已实现盈亏 ≈ {fee_ratio*100:.1f}%")

    out_path = os.path.join(args.out, 'REPORT.md')
    with open(out_path,'w',encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')

if __name__=='__main__':
    main()
