"""Service plans, licences and payment for an institution's deployment (D033).

The customer is the institution -- a faculty, a language centre -- never the
student: accounts are handed out by an administrator (BR-03), the system knows
pseudonyms only (BR-02), and a learner must never find a lesson, a report or
their own data behind a paywall (BR-29). What a plan limits is the
institution's capacity: how many student accounts it runs, which quality
assurance tools its staff can start, how many assessments it expects a month.

Pure rules live in `plans` and `keys`; the gateways in `gateways`; the one
place that reads the database and decides is `service.BillingService`.
"""
