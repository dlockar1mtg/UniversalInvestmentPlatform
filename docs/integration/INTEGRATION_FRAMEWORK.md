\# Integration Framework



\## Purpose



The Universal Integration Framework loads validated platform exports into a

central DuckDB database.



It does not replace platform-specific databases or internal analytical logic.



\## Database



Local database path:



`data/integration/uiip\_integration.duckdb`



The database is generated locally and excluded from Git.



\## Schemas



\### meta



Stores:



\- Database versions

\- Import audit records

\- Import errors



\### registry



Stores:



\- Machine registry

\- Platform registry



\### contracts



Stores records conforming to Universal Data Contracts:



\- Platform status

\- Asset master

\- Recommendations

\- Forecasts

\- Risk metrics

\- Portfolio positions

\- Macro signals

\- Export manifests



\### analytics



Provides current-state and combined analytical views.



\## Standard Workflow



1\. Validate a platform export.

2\. Calculate the source-file checksum.

3\. Check whether the same file and contract were already imported.

4\. Convert values to database-compatible types.

5\. Insert the records inside a transaction.

6\. Record the successful import in `meta.import\_runs`.

7\. Expose the data through analytical views.



\## Duplicate Protection



Successful imports are uniquely identified by:



\- Source-file SHA-256 checksum

\- Contract name



Reimporting the same unchanged file for the same contract is skipped.



\## Commands



\### Initialize database



```text

python scripts\\initialize\_integration\_db.py

