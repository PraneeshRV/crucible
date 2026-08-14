Talked to Priya on platform — she pointed out the same deploy also raised the DB
connection pool from 50 to 200. Two hundred connections against that instance means real
lock contention, and that would produce exactly this curve.

Honestly that's a better explanation than mine, and it's a one-line revert versus a
rewrite. I'm going to drop the pool back to 50 and close this out.
