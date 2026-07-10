# Northwind Cloud — Service Guide

Northwind Cloud is a fictional managed hosting platform. This document is
sample content for the Document Q&A service: upload it, then ask questions
like "How long is the free trial?" or "What happens when I cancel?"

## Plans and pricing

Northwind Cloud offers three plans. The Starter plan costs 12 dollars per
month and includes one project, 10 GB of storage, and community support.
The Team plan costs 49 dollars per month and includes ten projects, 250 GB
of storage, and email support with a 24-hour response target. The Enterprise
plan uses custom pricing and adds a dedicated account manager, single
sign-on, and a 99.95 percent uptime commitment.

Every new account starts with a 14-day free trial of the Team plan. No
credit card is required during the trial. When the trial ends, accounts
that have not added a payment method are automatically moved to a
read-only state for 30 days, after which project data is scheduled for
deletion.

## Billing and refunds

Invoices are issued on the first day of each billing cycle and are payable
within 15 days. Customers on annual billing receive a discount of two
months compared to paying monthly for the same plan.

Refunds are available within 30 days of any charge for monthly plans, and
within 60 days for annual plans. To request a refund, customers must open
a billing ticket and include the invoice number. Refunds are returned to
the original payment method within 5 to 10 business days. Charges for
usage-based add-ons, such as extra bandwidth, are not refundable.

## Cancellation policy

Subscriptions can be cancelled at any time from the account settings page.
Cancellation takes effect at the end of the current billing cycle; access
continues until that date. After cancellation, project data is retained
for 90 days and can be restored by reactivating the account. Once the
90-day retention window passes, data is permanently deleted and cannot be
recovered by support.

Enterprise customers must provide written notice of cancellation at least
60 days before their renewal date, as specified in their master service
agreement.

## Support and maintenance

Community support is available through the public forum for all plans.
Email support, included with Team and Enterprise plans, operates Monday
through Friday. Enterprise customers also receive a phone escalation line
staffed around the clock.

Planned maintenance windows are announced at least 7 days in advance and
are scheduled on Sundays between 02:00 and 06:00 UTC. During maintenance,
the platform remains available in degraded mode: deployments are paused,
but running services continue to serve traffic.

## Data and security

Customer data is encrypted at rest using AES-256 and in transit using TLS
1.3. Backups run every 6 hours and are retained for 35 days. Customers on
the Enterprise plan may request a specific data residency region from the
list of supported locations: United States, European Union, and Singapore.
