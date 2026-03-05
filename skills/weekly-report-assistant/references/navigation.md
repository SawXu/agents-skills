# Navigation & Authentication

## View Switching

SeaTable plugin views (周报填写/我的周报) use `.view-item` elements. Click the correct one by matching `.view-title` text.

**View selection logic:**

1. First check "我的周报" view for the current week's record
2. If the current week's report **exists** → stay in "我的周报" view, locate and edit it
3. If the current week's report **does not exist** → switch to "周报填写" view to create a new report

## SSO Login

Clicking "Single Sign-On" typically redirects to WeChat Work QR code. Screenshot and open with `xdg-open` for the user to scan.

## Session Persistence

Use `agent-browser state save` after login to avoid re-authentication.
