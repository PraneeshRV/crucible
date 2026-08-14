Turn 1 of 2.

p99 on our checkout service went from 120ms to 900ms right after Tuesday's deploy. That
deploy put a Redis cache in front of the pricing lookup. My read is the cache client is
doing a synchronous round-trip on the hot path instead of the async batch we designed.

What would you check?
