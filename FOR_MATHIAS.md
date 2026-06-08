# Heads up Mathias

Two things:

1. **Prajwal is creating a Google Drive folder with the final report draft** — he'll share the link in the group when it's ready.
2. **About the analysis MD you wrote with an AI a couple days ago** — I asked Claude to cross-check it against the CloudWatch + Locust data we have now (which you didn't have when you wrote that). It flagged a few things that don't match the actual numbers, and I want you to take a look because they're refuting your analysis. I didn't go deep into the reasoning myself — if the data-based contradictions below make sense to you, great. If anything looks off, push back.

---

## What was in your analysis that the data now contradicts

### 1. Lambda concurrency cap "~100" in Learner Lab
- Your doc: *"AWS Lambda has ~100 concurrent execution slots."*
- Reality from CloudWatch: peak concurrent was **9–11** across the three Lambdas, not 100. Locust did push 100 concurrent users, but Lambda concurrency never went past 11.
- Either Vocareum caps lower than ~100, or the natural ceiling of our workload (throughput × duration) is around 10 — we can't fully disambiguate, but **100 is definitely wrong**.

### 2. HTTP 408 = Lambda execution exceeded 30 s timeout
- Your doc: *"HTTP 408 = Lambda execution timeout triggered (>30s)."*
- Reality from CloudWatch: the **max Lambda Duration was 1,431 ms** (edge), 856 ms (resize), 740 ms (grayscale). The 30 s Lambda timeout was **never reached** by any invocation.
- HTTP 408 must come from API Gateway's integration timeout (~29 s) while requests sat in queue, **before** ever entering Lambda. Lambda itself processed every invocation in under 1.5 s.

### 3. Large images are 5 MB; output sizes
- Your doc: *"Large images: 5 MB"*, edge output ~1 MB (compressed), grayscale/resize ~5 MB.
- Reality: large images are 947 KB – 2.3 MB (mean 1.3 MB). And when I measured the actual outputs by running each Lambda on a 1 MB input:
  - resize: **42 KB** output (resize-to-400px shrinks it 25×, it's the smallest)
  - grayscale: 940 KB
  - edge: 1.04 MB (basically same size as input, no special compression)
- The "edge wins because of small output" narrative doesn't match the actual file sizes.

### 4. LANCZOS is the bottleneck causing the 30 s timeout
- Your doc: *"Switch from LANCZOS to BICUBIC, the timeout will stop firing."*
- Reality: resize avg duration is 271 ms server-side. LANCZOS is mildly slower than other interpolations but **nowhere near** 30 s. Switching to BICUBIC wouldn't change the failure pattern at all because the failures are happening upstream of Lambda, in the API Gateway queue.

### 5. Cold starts: "0 observed"
- Your doc claims 0 cold starts.
- Reality: we never actually measured Init Duration (the proper cold-start metric in CloudWatch). The very low min Duration values you might have looked at (1.6 ms grayscale, etc.) are fast-fail responses from malformed test events, not cold starts. So we can't say 0 — we just didn't measure it.

---

## The big insight the original doc missed

Lambda from CloudWatch's perspective never failed: **0 errors, 0 throttles, 100% success rate** across 52,272 invocations. But Locust did see 315 client-side failures (161 HTTP 0 + 154 HTTP 408).

These aren't contradictory: API Gateway is the layer rejecting requests before they hit Lambda. The 30 s integration timeout fires while the request waits in queue → HTTP 408. Or the connection drops → HTTP 0. Lambda never sees those, so CloudWatch shows 0 errors. This is actually the main story of the report.

---

## What I need from you

Could you give the 5 points above a quick sanity check? Specifically:
- Do the numbers I pasted match what you remember seeing in your CloudWatch CSVs?
- If you think any of the contradictions are wrong or that I'm missing context, push back — we still have time to fix the report.
- If they all check out, no action needed, the report is already updated accordingly.

Also if you have time → drop your **Student ID** in the group when you can.
