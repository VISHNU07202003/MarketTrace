# Coinbase Exchange Level2 Adapter Seam Specification

## Protocol Overview

Per the [Coinbase Exchange WebSocket Documentation](https://help.coinbase.com/en/developer-platform/websocket-feeds/exchange), the `level2` channel provides real-time order-book data for crypto pairs (e.g. `BTC-USD`).

### Protocol Flow
1. **Subscription:** Client connects to `wss://ws-feed.exchange.coinbase.com` and issues a `subscribe` message with channel `level2` and product `BTC-USD`.
2. **Snapshot:** The first message delivered is a `snapshot` containing arrays of `[price, size]` for bids and asks:
   ```json
   {
     "type": "snapshot",
     "product_id": "BTC-USD",
     "bids": [["60000.00", "1.50000000"], ...],
     "asks": [["60005.00", "2.10000000"], ...]
   }
   ```
3. **Incremental Updates:** Subsequent messages are of type `l2update` with a list of `changes`:
   ```json
   {
     "type": "l2update",
     "product_id": "BTC-USD",
     "time": "2026-11-06T18:00:00.123456Z",
     "changes": [
       ["buy", "60000.50", "0.75000000"],
       ["sell", "60005.00", "0.00000000"]
     ]
   }
   ```

---

## Critical Behavioral Finding: Sequence Number Semantics

> [!IMPORTANT]
> The public `level2` channel on Coinbase Exchange **does not provide contiguous per-message sequence numbers**. Contiguous order-level sequence numbers are only available on the private `full` channel.

### Consequence for Market-Data Reliability
1. **Observable vs Unobservable Gaps:** On a feed without transport-level sequence numbers, an omitted update cannot be flagged immediately by a sequence mismatch detector.
2. **Anomaly-Based Detection:** In live mode, detection must rely on semantic anomalies:
   - Crossed book state (`best_bid >= best_ask`)
   - Abrupt price jumps exceeding liquidity bounds
   - Heartbeat timeout / stale feed timers
3. **Deterministic Fixture Isolation:** For this reason, synthetic fixture testing with known sequence numbers remains the only mathematically rigorous method to evaluate exact missing-update fault recovery.

---

## Adapter Mapping to Canonical EventEnvelope

When ingesting live or captured Coinbase L2 data, the adapter maps messages as follows:

| Coinbase Field | MarketTrace Envelope Field | Transformation / Scaling |
|---|---|---|
| Auto-generated UUID | `delivery_id` | Unique identifier per local socket arrival |
| `"coinbase_exchange"` | `source` | Identifies feed origin |
| `time` (ISO 8601) | `provider_time_ns` | Converted to epoch nanoseconds |
| System arrival time | `receive_time_ns` | High-resolution local clock (`std::chrono::high_resolution_clock`) |
| `product_id` | `instrument` | Matches `"BTC-USD"` |
| `type == "snapshot"` | `message_kind = SNAPSHOT` | Clears book and applies initial depth |
| `type == "l2update"` | `message_kind = UPDATE` | Applies incremental price level change |
| `change[0] == "buy"` | `side = Side::Bid` | Mapped to enum |
| `change[0] == "sell"` | `side = Side::Ask` | Mapped to enum |
| `change[1]` (string price) | `price_ticks` | Exact integer arithmetic: `round(float(price) * 100)` ($0.01 ticks) |
| `change[2]` (string size) | `size_units` | Exact integer arithmetic: `round(float(size) * 1e8)` (satoshis) |

---

## Reconnection & Resynchronization Policy

1. If the WebSocket connection disconnects or an anomalous crossed book occurs, mark book state `QualityState::INCOMPLETE`.
2. Drop in-flight updates until a fresh `snapshot` message is received.
3. Apply the fresh snapshot to restore `QualityState::VALID` for the *current* book.
4. Historical calculation windows spanning the disconnected interval remain `QualityState::INCOMPLETE`.
