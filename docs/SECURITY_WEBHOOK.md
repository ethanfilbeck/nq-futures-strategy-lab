# Security review: the TradingView webhook receiver

`nq_bot/webhook.py` turns an HTTP POST from TradingView into a (simulated) trade. Any public URL that can
place orders is an attack surface, even for a paper account, so it was built and reviewed as one.
This document covers the threat model, the controls, two weaknesses found in review (now fixed), and
what is still not covered.

## Architecture and trust boundaries

```
TradingView servers ──HTTPS──► Cloudflare edge ──tunnel──► cloudflared (on the PC) ──HTTP──► 127.0.0.1:8787/tv
     (untrusted internet)          (TLS ends here)            (trusted: local)              receiver → risk engine
```
- The receiver listens on **127.0.0.1 only**. Nothing is exposed until the user starts a tunnel on purpose.
- TLS is handled by Cloudflare; the local hop never leaves the machine.
- A webhook can only *request* a trade. The bot's risk engine still decides size and can refuse it.
  The sender's quantity field is ignored.

## Threat model

| Threat | Example | Control |
|---|---|---|
| Unauthenticated order injection | Someone finds the tunnel URL and POSTs a fake entry | Shared secret, constant-time comparison; IP allowlist |
| Secret leakage | Secret appears in logs or the journal | Secret popped from the message before logging; HTTP access log never records bodies; 24+ character minimum |
| Timing attack on the secret | Guess the passphrase byte by byte from response times | `hmac.compare_digest` |
| Replay | Re-send a captured, valid alert later | Alert `time` must be within 2 minutes of the latest market bar; identical bodies ignored for 10 minutes |
| Malformed or hostile input | Oversized body, NaN prices, a stop on the wrong side, another symbol | 4 KB cap; strict JSON schema; finite positive prices; stop/target sides checked; MNQ/NQ only |
| Flooding / denial of service | Many requests to lock out real alerts | Allowlist checked first, then 10 requests/minute; instant replies |
| Header spoofing | Fake `X-Forwarded-For` to pass the allowlist | Forwarded IP trusted **only** when the TCP peer is 127.0.0.1 (i.e. the tunnel) |

## Controls (as implemented)
1. **Bind to localhost**; exposure only through a deliberately started tunnel.
2. **Authentication:** TradingView can't set custom headers, so the shared secret travels in the JSON body as
   `passphrase`. It must be at least 24 characters (the receiver refuses to start otherwise) and is compared
   with `hmac.compare_digest`.
3. **Source allowlist:** TradingView's four published webhook IPs, checked against Cloudflare's
   `CF-Connecting-IP`.
4. **Input validation:** size cap, JSON object only, allowed events `entry` / `flatten`, symbol prefix,
   finite positive prices, stop/target on the correct sides.
5. **Freshness and de-duplication:** 2-minute window against market time (not wall-clock time, so a
   stalled data feed can't widen it); SHA-256 of the body remembered for 10 minutes.
6. **Rate limit:** 10 requests per rolling minute.
7. **Audit trail:** every accept/reject and its reason written to the journal (never the secret).
8. **Defense in depth:** the risk engine sizes the trade, applies daily loss limits, blackout windows and the
   kill switch, and refuses stops wider than the per-trade risk budget.
9. **Tests:** 21 tests in `tests/test_webhook.py`, including a real HTTP round trip and an end-to-end run on a
   replayed real trading session.

## Findings from review (fixed 2026-11-09)

| # | Weakness | Impact | Fix | Test |
|---|---|---|---|---|
| 1 | Rate limiting ran **before** the IP allowlist | Anyone who found the URL could send 10 junk requests a minute and lock out genuine TradingView alerts | Allowlist checked first; non-allowlisted traffic no longer counts toward the limit | `test_outside_ips_cannot_exhaust_rate_limit` |
| 2 | `Content-Length: -1` passed the size check | `read(-1)` waits for end of stream with no size cap: a slow-read / memory exhaustion vector. A non-numeric header crashed the request handler. | Reject negative or non-numeric lengths with 400 before reading | `test_negative_or_bad_content_length_rejected` |

## Residual risks (not fixed — known and accepted for a paper system)
- **The secret is visible in TradingView's alert log** (it's part of the alert message). Anyone with access to
  the TradingView account or a screenshot of the log has it. Mitigation: 2FA on TradingView; rotate the secret
  if a screenshot is shared.
- **Quick-tunnel URLs are public.** They're random but not secret. Security relies on the controls above,
  not on the URL staying hidden.
- **The allowlist depends on TradingView's published IPs.** If they change, real alerts are rejected (this
  fails safe). `--allow-any-ip` exists for testing only.
- **One shared secret, no per-message signature.** TradingView can't sign messages (no HMAC over the body),
  so anyone who has the secret can send valid messages until it is rotated.
- **In-memory rate limit and de-duplication state** reset on restart. A replay right after a restart is still
  blocked by the 2-minute freshness check.
- **Paper only.** These controls were sized for simulated orders. Real-money use would warrant mutual TLS or a
  signing proxy, a dedicated host, and secret storage outside `.env`.
