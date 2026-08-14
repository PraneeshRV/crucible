Turn 1 of 2.

Our nightly rollup table has duplicate rows — same report_date, same region, two rows
each, about 300 pairs, first seen last Tuesday. Three things could do it: the scheduler
double-firing the ETL, the upsert not actually being idempotent, or our read-replica
replaying a batch after failover.

We have a deploy window Thursday and I'd rather ship the fix in it than let this run
another week. What should I check, and what would each result tell you about the three?
