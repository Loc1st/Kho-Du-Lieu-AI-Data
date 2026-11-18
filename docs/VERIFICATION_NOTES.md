# Verification notes

Verification modules replace the education-domain tests and benchmark with phone sales checks. Reports are written only under `output/phone_sales`; the pre-existing `output/benchmark_result.csv` is preserved.

## Implemented checks

1. Source processing accounting against latest completed ETL audit, source completed/cancelled lines, invalid raw records, and fact/reject counts. Each audit read count must equal accepted plus rejected.
2. Sale and return business keys have no duplicates.
3. Positive quantity/price and valid discount/cost domains.
4. Every sales dimension FK and both return FKs resolve.
5. Gross/net revenue arithmetic holds per sale.
6. Net cost and gross profit arithmetic holds per sale.
7. Individual return domains and cumulative returned quantity/refund/cost never exceed original sale.
8. Store SCD2 intervals are nonoverlapping, exactly one current version exists, and each sale references its historical interval; demo history is required.
9. Actual ETL rerun: complete sorted row snapshots, row counts, and SHA256 hashes for all eight dimension/fact tables are compared before/after (including surrogate keys and values). Audit/staging tables intentionally grow.
10. Five OLAP source/DW comparisons at monthly, SKU, store, channel and promotion grains reconcile orders, units, refunds, revenue, costs, profit, AOV and return rate.

Benchmark uses the same valid source population (completed orders) and sale cohort dates as the warehouse. Returns are preaggregated by original line. Results are compared exactly using decimal arithmetic. One warmup precedes five measured full fetches per query; reports retain every timing, medians and the measured source/DW ratio. No speed advantage is assumed.

## Executed evidence

- `python -m py_compile tests/run_dq_tests.py analysis/benchmark.py run_all.py`: PASS on 2026-11-17.
- Full database integration deliberately deferred until the concurrently implemented data loader is ready. Root integration will append actual run evidence; compilation is not a claim that data checks passed.

Reset is limited to literal `phone_dw` and `phone_source` database names, requires `--reset --confirm-reset phone-sales`, and does not consume environment database names. Default mode initializes missing objects and generates data only if fewer than 50,000 orders exist. It never drops data by default.

- `python run_all.py --help`: PASS, all eight modes listed.
- `python run_all.py --reset`: PASS guard test: argparse rejects missing confirmation before any database operation.

## Live integration evidence (2026-11-17)

`python -m tests.run_dq_tests` completed with exit code 0: all 10 cases PASS after partial/full return statuses were enabled. Canonical valid sale population is every order whose status is not CANCELLED.

- 60,000 source orders; 83,638 source sale lines = 80,646 accepted facts + 2,992 cancelled rejects.
- 6,002 source returns = 6,002 return facts; 90 invalid raw records rejected; 3,082 total latest-run rejects.
- All fact FK/domain/revenue/profit/return bounds had zero violations.
- SCD2: seven historical versions; zero invalid intervals, overlap, current flags or historical-key mismatches.
- Actual rerun `e58867861cac4e6f959404abbb23d9e0` preserved complete row counts and SHA256 snapshots, including every surrogate key/value, for all eight dimension/fact tables.
- TC10 compares five benchmark grains and separately executes five required business questions; all ten source/DW result comparisons matched exactly.
- Business export row counts: product/brand rollup 31; year/quarter/month rollup 52; brand/channel rollup 26; SKU/month average price and quantity 3,600; region/store rollup 69.
- Required business CSV files use `olap_business_Q1_brand_model.csv` through `olap_business_Q5_region_store.csv`; benchmark query CSVs use the honest `benchmark_query_Q*.csv` prefix. `export_olap()` exports the required business questions.

Root subsequently completed default `run_all.py`: exit 0, 296.94 seconds (`output/phone_sales/run_all_result.json`, `run_all_final.log`). All ten tests passed, including the actual ETL snapshot comparison after the default SCD demo. Latest HTTP-triggered test run also passed all ten; its run ID is recorded in `database_inventory.json` and `test_cases_result.json`.

The final HTTP suite passed all 11 groups, including POST `/api/run_tests` (99,776.16 ms). The Chrome CDP smoke test passed all six rendered canvases, all four tabs, year filtering, ten test rows and five benchmark rows, mobile width 390 with no overflow, and simulated API 503 state clearing followed by recovery. Final static checks all passed. See `PHONE_SALES_IMPLEMENTATION_REPORT.md` for the exact benchmark medians and preservation evidence.
