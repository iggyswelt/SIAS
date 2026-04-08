#!/usr/bin/env python3
"""
Athene Multi-Chain Arbitrage Scanner v4.0
Robust DexScreener + CoinGecko hybrid.
"""
import json, sys, subprocess, time
from urllib.request import urlopen, Request
from datetime import datetime, timezone

DB = "dbname=metamaus user=scraper host=127.0.0.1"

def get(url):
    try:
        with urlopen(Request(url, headers={"User-Agent": "Athene/4.0", "Accept": "application/json"}), timeout=20) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"  [ERR] {url[:80]}: {e}", file=sys.stderr)
        return None

def psql(sql):
    subprocess.run(["psql", "-h", "127.0.0.1", "-U", "scraper", "-d", "metamaus", "-c", sql],
                   capture_output=True, timeout=10)

# Token addresses for DexScreener search
TOKEN_ADDRS = {
    "ETH": {
        "ethereum": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        "bsc": "0x2170Ed0880ac9A755fd29B2688956BD959F933F8",
        "solana": "7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs",
    },
    "BTC": {
        "ethereum": "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",
        "bsc": "0x7130d2A12B9BCbFAe4f2634d864A1Ee1Ce3Ead9c",
        "solana": "3KiPiUqGUNt2XuZzRdgAECZNa1sRPYgh5oKuK6yK12Fw",
    },
    "SOL": {
        "ethereum": "0xD3CCE22B8eF51C27a06A647a8C43b972B1C2Dd61",
        "bsc": "0x2Ddcb2Dac77c3cE2E9Aa8708e8A7F9f1C19f8E7A",
        "solana": "So11111111111111111111111111111111111111112",
    },
}

def fetch_dexscreener_token(token, chain, addr):
    """Fetch price for a single token on a single chain."""
    data = get(f"https://api.dexscreener.com/latest/dex/tokens/{addr}")
    if not data or not data.get("pairs"):
        return None
    
    # Expected price ranges to filter noise
    expected = {"ETH": (500, 50000), "BTC": (20000, 200000), "SOL": (10, 500)}
    lo, hi = expected.get(token, (0.001, 999999))
    
    best_price = None
    best_liq = 0
    
    for pair in data["pairs"]:
        price_usd = pair.get("priceUsd")
        if not price_usd:
            continue
        try:
            price = float(price_usd)
        except:
            continue
        
        # Filter by expected range
        if price < lo or price > hi:
            continue
        
        # Must be on correct chain
        pair_chain = pair.get("chainId", "")
        chain_map = {"ethereum": "ethereum", "bsc": "bsc", "solana": "solana"}
        if pair_chain != chain_map.get(chain):
            continue
        
        liq = float(pair.get("liquidity", {}).get("usd", 0) or 0)
        quote_sym = pair.get("quoteToken", {}).get("symbol", "").upper()
        
        # Prefer stable-quoted pairs
        is_stable = any(s in quote_sym for s in ["USDC", "USDT"])
        
        if not best_price or (is_stable and liq > best_liq):
            best_price = price
            best_liq = liq
    
    return best_price

def fetch_all():
    """Fetch all token prices across all chains."""
    prices = {}
    for token, chains in TOKEN_ADDRS.items():
        prices[token] = {}
        for chain, addr in chains.items():
            print(f"  📡 {token} on {chain}...", end="", flush=True)
            p = fetch_dexscreener_token(token, chain, addr)
            prices[token][chain] = p
            print(f" ${p:,.2f}" if p else " N/A")
            time.sleep(0.3)
    
    # CoinGecko reference
    time.sleep(1)
    cg = get("https://api.coingecko.com/api/v3/simple/price?ids=ethereum,bitcoin,solana&vs_currencies=usd")
    if cg:
        for token, cg_id in [("ETH", "ethereum"), ("BTC", "bitcoin"), ("SOL", "solana")]:
            prices[token]["coingecko"] = cg.get(cg_id, {}).get("usd")
    
    return prices

def calc_spreads(prices):
    spreads = []
    chain_pairs = [("ethereum", "bsc"), ("ethereum", "solana"), ("bsc", "solana")]
    for token in ["ETH", "BTC", "SOL"]:
        chains = prices.get(token, {})
        for c1, c2 in chain_pairs:
            p1, p2 = chains.get(c1), chains.get(c2)
            if p1 and p2 and p1 > 0 and p2 > 0:
                spread = ((p2 - p1) / p1) * 100
                spreads.append({
                    "token": token, "chain_from": c1, "chain_to": c2,
                    "price_from": p1, "price_to": p2,
                    "spread_pct": round(spread, 4),
                })
    return spreads

def main():
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"\n[{ts}] 🏛 Athene Multi-Chain Scanner v4.0")
    print("═" * 55)
    
    prices = fetch_all()
    
    print(f"\n{'─'*55}")
    print(f"📊 PRICE MATRIX:")
    print(f"{'─'*55}")
    header = f"  {'Token':<6}"
    for c in ["Ethereum", "BSC", "Solana", "CoinGecko"]:
        header += f" {c:>12}"
    print(header)
    for token in ["ETH", "BTC", "SOL"]:
        c = prices.get(token, {})
        row = f"  {token:<6}"
        for chain in ["ethereum", "bsc", "solana", "coingecko"]:
            v = c.get(chain)
            row += f" {'N/A' if not v else f'${v:,.2f}':>12}"
        print(row)
    
    spreads = calc_spreads(prices)
    print(f"\n📈 SPREADS ({len(spreads)}):")
    for s in spreads:
        flag = "🚨" if abs(s["spread_pct"]) > 1.0 else ("🟡" if abs(s["spread_pct"]) > 0.3 else "⚪")
        print(f"  {flag} {s['token']} {s['chain_from']:10s} → {s['chain_to']:10s}: {s['spread_pct']:+.4f}%  (${s['price_from']:,.2f} → ${s['price_to']:,.2f})")
    
    # Log spreads
    for s in spreads:
        psql(f"""INSERT INTO athene_crosschain_spreads (token, chain_from, chain_to, price_from, price_to, spread_pct, price_from_source, price_to_source)
                 VALUES ('{s['token']}', '{s['chain_from']}', '{s['chain_to']}', {s['price_from']}, {s['price_to']}, {s['spread_pct']}, 'dexscreener', 'dexscreener')""")
    
    # Log seed prices
    for token, chains in prices.items():
        for chain, price in chains.items():
            if price and price > 0:
                psql(f"""INSERT INTO athene_trades (pair, type, amount, price)
                         VALUES ('{token}_{chain}', 'multichain_seed', 1, {price})""")
    
    n_sp = len(spreads)
    n_pr = sum(1 for t in prices.values() for p in t.values() if p and p > 0)
    print(f"\n{'─'*55}")
    print(f"✅ {n_pr} prices → athene_trades | {n_sp} spreads → athene_crosschain_spreads")
    
    if spreads:
        best = max(spreads, key=lambda x: abs(x["spread_pct"]))
        print(f"🎯 BEST: {best['token']} {best['chain_from']}→{best['chain_to']}: {best['spread_pct']:+.4f}%")

if __name__ == "__main__":
    main()
