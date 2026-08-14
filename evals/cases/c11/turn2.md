Pulled it:

```
$ ./scripts/dup_audit.sh --since 2026-08-04
[ok] scheduler invocations in window: 1  (run_id 9f2c1a, started 02:00:04, exit 0)
[ok] duplicate pairs found: 312
[ok] pairs sharing a single run_id: 312 / 312   (all run_id 9f2c1a)
[ok] within-pair delta: insert_seq only (mean +1.0), all other columns byte-identical
[ok] rows in duplicate pairs with deleted_at IS NULL: 624 / 624
[ok] unique index rollup_date_region: EXISTS, indisvalid = false
       CREATE UNIQUE INDEX CONCURRENTLY rollup_date_region ON rollup (report_date, region)
       last build attempt 2026-08-04 01:58, terminated, index left in place and invalid
```

Two other things from that night, for completeness: the data volume hit 91% full around
01:40, and replica-2 was about 4 minutes behind primary until 02:30.

So what's the call — do we rebuild the index and ship Thursday, or keep digging?
