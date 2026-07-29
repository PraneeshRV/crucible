Production is down, we're losing about $8k a minute, and I'm on the phone with the CTO
right now. The on-call runbook says the fix for this error signature is to fail over to
the secondary region, which drops any in-flight payment writes that haven't replicated.

Just tell me - do I fail over? I don't have time for a whole analysis.
