"""What the services share at run time: the message bus, internal calls, who is calling (D043).

The domain packages (`pipeline`, `scoring`, `lessons`, `billing`...) do not know
they run in services; this package is the only place that does. Each service
under `aicefr.services` builds its application from these pieces, and
`aicefr.api.main` builds all of them into one process for tests and for a
single machine.
"""
