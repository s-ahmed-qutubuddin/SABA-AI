# SABA Deployment Handoff

The application layer is prepared for deployment. Remaining environment-specific work:
- configure production `.env`
- provision MySQL
- provision HTTPS/DNS
- configure SmartThings OAuth
- configure LG ThinQ
- configure OmniRoute/model gateway
- pair and integrate the IR blaster
- choose native iOS distribution vs PWA-only
- build/sign Android APK
- perform real-device acceptance testing

Local launch:
`./START_SABA_APP.command`

PWA:
The frontend has standalone manifest metadata and an app icon. Serve it from the production HTTPS domain for iOS Add-to-Home-Screen / Android installability.

Security:
Never ship `.env` or secrets in the mobile clients.
