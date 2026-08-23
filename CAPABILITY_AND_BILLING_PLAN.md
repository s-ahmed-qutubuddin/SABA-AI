# SABA Capability + Billing

## SmartThings controls
SABA now discovers SmartThings device profiles and production capability definitions and returns a normalized `controls` list from `/home/capabilities`. Commands marked unavailable by the device are filtered from executable controls. The generic `/home/control` route already accepts capability, command, arguments, and component, so new supported SmartThings commands do not require a new backend endpoint.

## Energy / billing
SmartThings `powerConsumptionReport` telemetry is exposed through `/home/energy`. This is device energy telemetry, not an official utility meter reading. The existing cost calculation is a flat `kWh × tariff` estimate. An exact utility bill requires the actual tariff schedule, fixed charges, duties/taxes, and billing period for the user's electricity provider; those must be configured from real tariff data rather than guessed.
