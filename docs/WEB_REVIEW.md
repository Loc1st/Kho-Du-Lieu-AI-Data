# Web review (2026-11-17)

Read-only review of MVC, browser code and live model queries. No database writes were performed.

## Findings

1. **Blocker: SQL database isolation bypass** (`mvc/models/sql_model.py:25`). The FROM/JOIN regex skips parenthesized table references. Both `SELECT COUNT(*) n FROM (information_schema.tables)` and `SELECT COUNT(*) n FROM (phone_source.don_hang)` pass validation when selected database is `phone_dw`, and actually execute. Read-only proof returned 299 and 60,000 respectively. Validate the complete table grammar or reject parenthesized table factors and unapproved qualified references. Add both examples as rejection regression cases.

2. **High: ETL tab reads old/missing artifacts** (`mvc/models/etl_model.py:9,28`). `artifact()` reads directly from `output/`, while new reports are in `output/phone_sales/`. Tests filename is `dq_tests.json` instead of `test_cases_result.json`. Live model returned zero tests and three legacy education benchmark rows. Use the phone report directory and correct filename.

3. **Medium: default SCD example store does not exist** (`web/index.html:237`, `web/app.js` sample). Default search and history sample use `CH001`; generated stores are `CH00`, `CH01`, etc. Actual search for `CH001` returns no rows, leaving the initial SCD selection empty. Use a generated key or an empty initial search.

4. **Medium: visible Vietnamese characters lost** (`web/index.html`, `web/app.js`, MVC error strings). These files contain literal ASCII question marks in place of accented letters, e.g. labels for store history and error messages; this is present in file bytes, not just terminal rendering. The reviewed JS and HTML contain 190 and 254 question marks respectively (some JS question marks are legitimate operators). Repair the visible strings using UTF-8.

5. **Low: changing store history resets dashboard filters** (`web/app.js`, `filters()` / `changeStore()`). Refreshing filter options replaces every select without preserving selected values; currently selected filters silently disappear after an SCD mutation. Preserve still-valid selected values and refresh overview consistently.

## Working evidence

- Live `get_filter_options()`, unfiltered overview, filtered overview and empty-result overview complete successfully against the new schema.
- Model dashboard uses one shared parameterized filter for KPI, all six chart datasets and store table; sale-cohort return attribution is consistent.
- Live SQL rollup sample executes successfully.
- Overview request sequencing suppresses older overview responses; errors clear stale KPI/chart state.
- Chart and API field names agree for top models, monthly, brand/channel, scatter, brand trend and regions.
- Browser rendering remains for root integration; this review does not claim rendered-chart verification.

## Follow-up isolation review

After parenthesized table references were rejected, a second bypass was reproduced read-only:

```sql
SELECT COUNT(*) n FROM dim_san_pham p
JOIN dim_kenh_ban k
ON EXISTS (SELECT 1 FROM dim_thoi_gian WHERE nam=2024),
information_schema.tables i
```

The query passes `validate_select(...,'phone_dw')` and executes (count 120,400). The outer FROM-clause regex stops at the nested WHERE and misses the later comma table. Recommended restricted-grammar fix: reject nested SELECT/subqueries (not used by built-in samples), or replace regex checks with an actual SQL parser that validates all table references. Root notified immediately.

The artifact location/filename and first parenthesized-table issue were being corrected concurrently; initial findings above describe the initial review state.

Two further independent unsupported table syntaxes were also reproduced and reported:

```sql
SELECT COUNT(*) n FROM dim_san_pham p
STRAIGHT_JOIN information_schema.tables i ON 1=1
-- Executed metadata count: 30,100

SELECT COUNT(*) n FROM { OJ information_schema.tables }
-- Executed metadata count: 301
```

The validator must reject STRAIGHT_JOIN and ODBC brace escapes (or explicitly parse their table references); nested-SELECT rejection alone does not cover them. An anchored direct-table grammar for every FROM/JOIN token is preferable to skipping tokens that fail a loose search regex.

## Resolution verified by root

All reported unsupported SQL forms now fail validation; regression cases cover parenthesized tables, nested SELECT, STRAIGHT_JOIN and ODBC escapes. The playground deliberately supports direct approved table/view references only, with read-only transactions, function restrictions, a three-second statement limit and 500 returned rows. Unit tests passed on final code.

Artifact paths now resolve exclusively to `output/phone_sales/`, the initial store is CH00, Vietnamese literals are UTF-8, filter selections survive SCD option refresh and overview is updated. Real Chrome smoke evidence confirms six rendered charts, all tabs, current test/benchmark artifacts, mobile layout and API failure/recovery. The initial findings above remain as review history; final evidence is in `output/phone_sales/browser_smoke.json` and `api_smoke.json`.
