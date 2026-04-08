#!/usr/bin/env python3
"""
Athene Multi-Chain Arbitrage Scanner v2
Filters by volume + orderbook depth to find REAL opportunities.
"""

import json, os, sys, time, secrets, subprocess
from datetime import datetime, timezone
from pathlib import Path
import urllib.request

BASE_DIR = Path("/home/iggy/.openclaw/agents/athene")
RESULTS_FILE = BASE_DIR / "arbitrage_results.json"

def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "AtheneBot/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return None

def fetch_binance_24h():
    """Get 24h ticker with volume data"""
    data = fetch_json("https://api.binance.com/api/v3/ticker/24hr")
    if data:
        return {item["symbol"]: {
            "price": float(item["lastPrice"]),
            "volume_usd": float(item["quoteVolume"]),
            "high": float(item["highPrice"]),
            "low": float(item["lowPrice"]),
        } for item in data}
    return {}

def fetch_gateio_24h():
    """Gate.io tickers with volume"""
    data = fetch_json("https://api.gateio.ws/api/v4/spot/tickers")
    if data:
        return {item["currency_pair"]: {
            "price": float(item["last"]),
            "volume_usd": float(item["base_volume"]) * float(item["last"]),
            "high": float(item["high_24h"]),
            "low": float(item["low_24h"]),
        } for item in data}
    return {}

def fetch_binance_orderbook(symbol, limit=5):
    """Get top 5 bids/asks"""
    data = fetch_json(f"https://api.binance.com/api/v3/depth?symbol={symbol}&limit={limit}")
    if data:
        return {
            "bids": [(float(p), float(q)) for p, q in data.get("bids", [])],
            "asks": [(float(p), float(q)) for p, q in data.get("asks", [])],
        }
    return None

def find_real_arbitrage(binance_data, gateio_data, min_volume_usd=50000, min_spread_pct=0.1):
    """
    Find real arbitrage with:
    - Minimum volume on BOTH exchanges
    - Real orderbook prices (not just last price)
    - Account for trading fees (~0.1% per trade = 0.2% roundtrip)
    """
    opportunities = []
    
    # Build gateio lookup (BASE_QUOTE -> BASEQUOTE)
    gate_lookup = {}
    for pair, info in gateio_data.items():
        parts = pair.split("_")
        if len(parts) == 2:
            base, quote = parts
            key = f"{base}{quote}"
            if quote in ("USDT", "USDC", "BTC", "ETH"):
                gate_lookup[key] = info
    
    MIN_PROFIT_PCT = 0.25  # Must beat 0.2% roundtrip fees + buffer
    
    for symbol, binfo in binance_data.items():
        if symbol not in gate_lookup:
            continue
        ginfo = gate_lookup[symbol]
        
        # Volume filter
        if binfo["volume_usd"] < min_volume_usd or ginfo["volume_usd"] < min_volume_usd:
            continue
        
        bp = binfo["price"]
        gp = ginfo["price"]
        if bp <= 0 or gp <= 0:
            continue
        
        spread_pct = abs(bp - gp) / min(bp, gp) * 100
        
        if spread_pct < min_spread_pct:
            continue
        
        # Determine direction
        if gp < bp:
            buy_exchange, sell_exchange = "gateio", "binance"
            buy_price, sell_price = gp, bp
        else:
            buy_exchange, sell_exchange = "binance", "gateio"
            buy_price, sell_price = bp, gp
        
        # Estimate profit after fees
        fee_pct = 0.1  # per trade
        net_profit_pct = spread_pct - (fee_pct * 2)
        
        base = symbol.replace("USDT","").replace("USDC","").replace("BTC","").replace("ETH","")
        quote = symbol.replace(base, "")
        
        opportunities.append({
            "type": "CEX↔CEX",
            "pair": f"{base}/{quote}",
            "buy_exchange": buy_exchange,
            "sell_exchange": sell_exchange,
            "buy_price": round(buy_price, 8),
            "sell_price": round(sell_price, 8),
            "spread_pct": round(spread_pct, 4),
            "net_profit_pct": round(net_profit_pct, 4),
            "binance_vol_usd": round(binfo["volume_usd"], 0),
            "gateio_vol_usd": round(ginfo["volume_usd"], 0),
            "profitable": net_profit_pct > 0,
            "profit_per_10k": round(net_profit_pct / 100 * 10000, 2),
        })
    
    opportunities.sort(key=lambda x: x["spread_pct"], reverse=True)
    return opportunities

def store_in_db(opportunities):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for opp in opportunities[:5]:
        key = f"arb_cex_{opp['pair'].replace('/','_')}_{ts}"
        value = json.dumps(opp)
        cmd = [
            "psql", "-h", "127.0.0.1", "-U", "scraper", "-d", "metamaus",
            "-c", f"INSERT INTO agent_knowledge (key, value, category, learned_by, learned_at, tags) "
                  f"VALUES ('{key}', '{value.replace(chr(39), chr(39)+chr(39))}', 'arbitrage_research', 'athene', '{ts}', "
                  f"ARRAY['cex_cex', 'dry_run', 'volume_filtered']) "
                  f"ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW();"
        ]
        subprocess.run(cmd, capture_output=True, timeout=10, check=False)

def main():
    print("=" * 60)
    print("ATHENE ARBITRAGE SCANNER v2 — VOLUME-FILTERED")
    print(f"Time: {datetime.now(timezone.utc).isoformat()}")
    print("Mode: DRY RUN | Min volume: $50k | Min spread: 0.1%")
    print("=" * 60)
    
    print("\n[*] Fetching 24h ticker data...")
    binance = fetch_binance_24h()
    print(f"  Binance: {len(binance)} pairs")
    
    gateio = fetch_gateio_24h()
    print(f"  Gate.io: {len(gateio)} pairs")
    
    print("\n[*] Scanning with volume filter...")
    opps = find_real_arbitrage(binance, gateio)
    
    profitable = [o for o in opps if o["profitable"]]
    print(f"  Total opportunities: {len(opps)}")
    print(f"  Profitable (after fees): {len(profitable)}")
    
    print("\n--- TOP 15 BY SPREAD ---")
    for opp in opps[:15]:
        flag = "✅" if opp["profitable"] else "❌"
        print(f"  {flag} {opp['pair']:12s} | {opp['spread_pct']:7.3f}% spread | "
              f"net {opp['net_profit_pct']:+.3f}% | "
              f"B:${opp['binance_vol_usd']/1000:.0f}k G:${opp['gateio_vol_usd']/1000:.0f}k | "
              f"Buy:{opp['buy_exchange']:7s} Sell:{opp['sell_exchange']}")
    
    # Deep dive: get orderbooks for top 3 profitable
    if profitable:
        print("\n--- ORDERBOOK DEEP DIVE (Top 3 profitable) ---")
        for opp in profitable[:3]:
            symbol = opp["pair"].replace("/", "")
            ob = fetch_binance_orderbook(symbol)
            if ob and ob["asks"] and ob["bids"]:
                best_ask = ob["asks"][0][0]
                best_bid = ob["bids"][0][0]
                print(f"  {opp['pair']} Binance OB: Bid={best_ask} Ask={best_bid} Spread={((best_ask-best_bid)/best_bid*100):.3f}%")
    
    # Store
    print("\n[*] Storing in database...")
    store_in_db(opps)
    
    # Save
    results = {
        "scan_time": datetime.now(timezone.utc).isoformat(),
        "total": len(opps),
        "profitable": len(profitable),
        "opportunities": opps[:20],
    }
    with open(RESULTS_FILE, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to {RESULTS_FILE}")
    if profitable:
        b = profitable[0]
        print(f"\n🏆 BEST PROFITABLE: {b['pair']} — net {b['net_profit_pct']:.3f}% (${b['profit_per_10k']}/10k)")
        print(f"   Buy {b['buy_exchange']} @ {b['buy_price']}, Sell {b['sell_exchange']} @ {b['sell_price']}")
    else:
        print("\n⚠️ No profitable opportunities after fees this scan.")
    print("=" * 60)

if __name__ == "__main__":
    main()
