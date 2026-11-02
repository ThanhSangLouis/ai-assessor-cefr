"""Payment for run packs through payment gateways (D035, D053, D075).

One centre runs the deployment; a learner or a teacher buys runs for the
metered channel (D049) and pays through a gateway. The service plans,
licences and licence keys of D033 and D034 were removed in D075.

Stripe lives in `stripe_gateway`, the sandbox in `gateways` (VNPay and MoMo
were removed in D075); the one
place that reads the database and decides is `service.BillingService`.
"""
