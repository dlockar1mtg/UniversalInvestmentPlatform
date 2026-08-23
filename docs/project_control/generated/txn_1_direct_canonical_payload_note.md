# TXN-1 Direct Canonical Payload Note

This corrective change removes the transaction form's dependency on temporarily rewriting the visible Asset textbox during submit.

The governed picker retains the user-facing asset label and stores the certified canonical asset ID in `txn-asset.dataset.assetId`.

`dashboard.js` now reads that canonical field directly when constructing `asset_id` for `/v1/transactions`.

The server-side active certified asset catalog validator remains unchanged.

This note records the corrective intent; final acceptance still requires CI, Render deployment, and a successful live correction transaction.
