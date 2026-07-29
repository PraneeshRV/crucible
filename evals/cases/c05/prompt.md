Turn 1 of 2.

We're seeing 3 corrupted rows per million in the analytics warehouse. It could be the
ingestion job's batch boundary handling, or a known driver bug in the Parquet writer,
or upstream bad data we're faithfully recording.

Reproducing it means replaying six weeks of raw events through a staging warehouse -
roughly $400 in compute and two days. The corrupted rows are dropped by every
downstream consumer already.

Where does that leave us?
