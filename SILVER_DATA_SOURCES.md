# Silver (XAG) Data Sources for TA-DSS

**Research Date:** March 6, 2026  
**Tested From:** Google Cloud VM (us-central1)  
**Purpose:** Find free crypto exchanges that provide silver (XAG) price data

---

## Executive Summary

| Exchange | Symbol | Type | Status | VM Access | API Key | Cost |
|----------|--------|------|--------|-----------|---------|------|
| **Gate.io** | XAG/USDT:USDT | Swap | ✅ **RECOMMENDED** | ✅ Works | ❌ No | Free |
| **Bitfinex** | XAGF0/USTF0 | Futures | ✅ Works | ✅ Works | ❌ No | Free |
| **Twelve Data** | XAG/USD | Spot | ⚠️ Paid Only | ✅ Works | ✅ Yes | $45/mo |
| **OKX** | XAUT/USDT | Tokenized Gold | ❌ No XAG | ⚠️ CCXT bug | ❌ No | Free |
| **Kraken** | - | - | ❌ No metals | ✅ Works | ❌ No | N/A |
| **Binance** | - | - | ❌ No metals | ❌ Blocked | ❌ No | N/A |

---

## Detailed Results

### 1. Gate.io ⭐ **BEST FOR SILVER**

**Symbol:** `XAG/USDT:USDT` (Silver Swap)

**Test Results:**
```
Status: ✅ WORKS from VM
Latest Data: 2026-03-06 Close=83.76
API Key: NOT required for public OHLCV data
Free Tier: Unlimited
```

**CCXT Usage:**
```python
import ccxt

gate = ccxt.gateio({'enableRateLimit': True})
gate.load_markets()

# Fetch silver data
ohlcv = gate.fetch_ohlcv('XAG/USDT:USDT', '1d', limit=100)
print(ohlcv)
```

**Pros:**
- ✅ Current/recent data (2026)
- ✅ Works from Google Cloud VM
- ✅ No API key required
- ✅ Free unlimited access
- ✅ Native CCXT support

**Cons:**
- ⚠️ Swap contract (not spot price)
- ⚠️ May have contract rollover dates

---

### 2. Bitfinex

**Symbol:** `XAGF0/USTF0` (Silver Futures)

**Test Results:**
```
Status: ✅ WORKS from VM
Latest Data: 2020-10-30 Close=23.67 (OLD DATA)
API Key: NOT required for public OHLCV data
Free Tier: Unlimited
```

**CCXT Usage:**
```python
import ccxt

bf = ccxt.bitfinex({'enableRateLimit': True})
bf.load_markets()

# Fetch silver futures data
ohlcv = bf.fetch_ohlcv('XAGF0/USTF0', '1d', limit=100)
print(ohlcv)
```

**Pros:**
- ✅ Works from Google Cloud VM
- ✅ No API key required
- ✅ Free unlimited access

**Cons:**
- ❌ **Historical data only** (last update 2020)
- ❌ Futures contract (not spot)
- ❌ May not be suitable for current price monitoring

---

### 3. Twelve Data

**Symbol:** `XAG/USD` (Silver Spot)

**Test Results:**
```
Status: ⚠️ Paid Plan Required
API Error: "This symbol is available starting with Grow (Grow plan)"
API Key: Required
Cost: $45/month (Grow plan)
```

**API Usage:**
```python
from twelvedata import TDClient

td = TDClient(api_key='YOUR_KEY')
data = td.time_series(symbol='XAG/USD', interval='1day', outputsize=100)
df = data.as_pandas()
```

**Pros:**
- ✅ Spot price (not futures/swap)
- ✅ Reliable data
- ✅ Works from VM

**Cons:**
- ❌ **Requires paid plan** ($45/month)
- ❌ Not available on free tier

---

### 4. OKX

**Symbol:** `XAUT/USDT` (Paxos Gold Token - NOT Silver)

**Test Results:**
```
Status: ❌ CCXT Bug
Error: "unsupported operand type(s) for +: 'NoneType' and 'str'"
```

**Notes:**
- OKX only has XAUT (tokenized gold), no XAG (silver)
- CCXT has a bug with OKX market parsing
- Not recommended for silver data

---

### 5. Exchanges WITHOUT Silver

| Exchange | Reason |
|----------|--------|
| **Kraken** | No metals/forex support |
| **Binance** | No spot metals + geo-blocked |
| **Bybit** | Geo-restricted (HTTP 403) |
| **Kucoin** | Only has XAUT (tokenized gold) |
| **Huobi** | XAG/USDT exists but not accessible from VM |

---

## Recommendation

### For Silver (XAG) Monitoring:

**Option 1: Gate.io (FREE) ⭐**
```python
# Add to src/data_fetcher.py
def _fetch_gateio_silver(self, timeframe, limit):
    gate = ccxt.gateio({'enableRateLimit': True})
    gate.load_markets()
    return gate.fetch_ohlcv('XAG/USDT:USDT', timeframe, limit=limit)
```

**Pros:** Free, works on VM, current data  
**Cons:** Swap contract (minor)

**Option 2: Twelve Data ($45/mo)**
- Only if you need spot price specifically
- Already integrated for XAUUSD
- One API for all metals

---

## Implementation: Gate.io for XAGUSD

### Step 1: Update Smart Routing

```python
# src/data_fetcher.py

def _detect_data_source(pair: str) -> Literal["yfinance", "ccxt", "twelvedata", "gateio"]:
    pair_upper = pair.upper().replace("-", "").replace("_", "")
    
    # Metals (Gold, Silver)
    if pair_upper.startswith('XAU'):
        return "twelvedata"  # XAU works on free tier
    if pair_upper.startswith('XAG'):
        return "gateio"  # XAG requires paid on Twelve Data
    
    # ... rest of routing
```

### Step 2: Add Gate.io Fetch Method

```python
def _fetch_gateio(self, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
    """Fetch OHLCV from Gate.io (for silver swap)."""
    gate = ccxt.gateio({'enableRateLimit': True})
    gate.load_markets()
    
    # Gate.io silver symbol
    gate_symbol = 'XAG/USDT:USDT'
    
    # Map timeframe
    tf_map = {'d1': '1d', 'h4': '4h', 'h1': '1h'}
    gate_tf = tf_map.get(timeframe, '1d')
    
    ohlcv = gate.fetch_ohlcv(gate_symbol, gate_tf, limit=limit)
    
    # Convert to DataFrame
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    
    return df
```

### Step 3: Update get_ohlcv()

```python
# In get_ohlcv method, add gateio case:
if detected_source == "gateio":
    df = self._fetch_gateio(symbol, validated_tf, limit)
```

---

## Cost Comparison

| Solution | Monthly Cost | Notes |
|----------|--------------|-------|
| **Gate.io** | $0 | Free, swap contract |
| **Bitfinex** | $0 | But old data (2020) |
| **Twelve Data** | $45 | Spot price, all metals |
| **Custom API** | $0-50 | Depends on provider |

---

## Conclusion

**For XAGUSD (Silver) monitoring, use Gate.io:**
- ✅ Free
- ✅ Works on your VM
- ✅ Current data (2026)
- ✅ No API key required
- ⚠️ Swap contract (acceptable for price monitoring)

**Implementation Time:** 1-2 hours

---

## Test Commands

```bash
# Test Gate.io silver data
docker exec tadss python3 -c "
import ccxt
gate = ccxt.gateio({'enableRateLimit': True})
gate.load_markets()
ohlcv = gate.fetch_ohlcv('XAG/USDT:USDT', '1d', limit=5)
print('Gate.io XAG/USDT:USDT:')
for candle in ohlcv:
    print(f'  {candle[0]}: O={candle[1]:.2f} H={candle[2]:.2f} L={candle[3]:.2f} C={candle[4]:.2f}')
"
```

---

**References:**
- Gate.io API: https://www.gate.io/docs/developers/apiv4/
- CCXT Gate.io: https://docs.ccxt.com/#/README?id=gateio
- Twelve Data Pricing: https://twelvedata.com/pricing
