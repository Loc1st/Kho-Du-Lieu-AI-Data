# Data implementation notes

Implementation completed directly in the shared workspace on 2026-11-17. Existing `.env`, education databases, `data/error_manifest.json`, and `output/benchmark_result.csv` were not edited by this task.

## Entrypoints and preservation

- `.venv/Scripts/python.exe -m generator.generate_data`: deterministic seed 2026, 60,000 orders; skips an already populated phone source **before writing CSV**. `--orders` requires at least 50,000; `--seed` selects a deterministic fixture. `--csv-only` explicitly exports without database writes.
- `python -m etl.pipeline [--init-dw]`: both modes initialize only missing phone schema objects. `run_etl(init_dw=False)` returns a 32-character run ID. Schema initialization never drops databases/tables or truncates source.
- `etl.demo_scd2.change_store(ma_cua_hang,khu_vuc,ngay_hieu_luc)` returns changed flag, versions and fact update count. `python -m etl.demo_scd2` demonstrates CH00 effective 2026-01-01.
- `python -m unittest etl.test_scd2`: offline interval regression.
- `common.db` fixes database identifiers to `phone_source` and `phone_dw`; legacy SOURCE_DB/DW_DB values in `.env` cannot redirect destructive operations into education databases.

Generated CSV and exact 90-error manifest live only under `data/phone_sales/`; ETL JSON logs, rejects and DQ reports live under `output/phone_sales/`.

## Schema and arithmetic

Source has 13 constrained normalized business tables: `thuong_hieu`, `san_pham`, `phien_ban_san_pham`, `tinh_thanh`, `cua_hang`, `nhan_vien`, `khach_hang`, `kenh_ban`, `khuyen_mai`, `don_hang`, `chi_tiet_don_hang`, `tra_hang`, `chi_tiet_tra_hang`. Product variants and province catalog justify the additional normalized tables. Two operational extras are `lich_su_cua_hang` and `raw_import_error`. FK integrity is never disabled. Invalid raw envelopes never enter the constrained business tables.

`trang_thai` order values are COMPLETED, PARTIALLY_RETURNED, RETURNED, CANCELLED. Return document status is PARTIAL/FULL. Only CANCELLED orders are excluded. Promotions have inclusive validity dates and yearly seasonal identifiers, with NONE as the no-promotion member. Source employees belong to their assigned order store. No real personal data is used.

Warehouse follows the binding six-dimension/two-fact contract in PHONE_IMPLEMENTATION_PLAN.md. Money is DECIMAL(18,2); Python transformations use Decimal. Source `gia_von` and `giam_gia` are **line totals**. Return costs round HALF_UP and never exceed remaining line cost. Cumulative return units and refunds cannot exceed original sale units and revenue. `vw_sales_net` preaggregates returns before joining sales, preventing fanout.

ETL reads the database, stages sale/return/raw envelopes tagged by run ID, validates actual source dates/amounts/discounts/promotion validity/natural keys/history, loads dimensions then facts, validates cumulative returns, and records every rejected raw envelope plus cancelled sale lines. A malformed constrained source row aborts the transaction; business constraints prevent negative required amounts and broken FKs. There are actual EXTRACT, TRANSFORM and LOAD audit steps. Raw error labels are never accepted as validation evidence: rejection reasons come from payload validation.

`etl_log`: log_id,run_id,buoc,bang,so_dong_doc,so_dong_nap,so_dong_loai,ghi_chu,status,created_at. Loaded counts include accepted existing rows on rerun; read=loaded+rejected. `etl_data_quality`: dq_id,run_id,bang,loai_kiem_tra,so_dong_truoc,so_dong_sau,cach_xu_ly. `etl_reject`: reject_id,run_id,bang,source_id,reason,payload. `stg_import`: staging_id,run_id,source_table,source_id,payload. Audit histories accumulate across runs.

ETL/generator/SCD changes share MariaDB advisory lock `phone_dw_pipeline`; transaction commit precedes releasing it. Warehouse DML and source SCD history changes commit atomically. Failure rolls back data/staging/reject changes, then writes a FAILED pipeline audit. Fact upserts retain surrogate keys. Only obsolete return IDs are deleted; repeated ETL never clears return facts wholesale.

SCD2 uses exclusive interval ends `[ngay_hieu_luc,ngay_het_han)` and sentinel 9999-12-31. Effective-date insertion can split historical intervals; existing surrogate version keys are preserved and affected facts are rekeyed by their original sale date in the same transaction. An unchanged region is a no-op; a different region at an existing effective-date boundary raises ValueError to preserve historical records.

## Actual checks

Live MariaDB **10.4.32** connected successfully. Seed-2026 fixture generated and loaded: 60,000 orders; 83,638 source sale lines; 6,002 return lines; 90 raw errors (10 each duplicate, missing required, negative quantity, negative price, negative cost, unknown SKU, invalid date, invalid province, excessive return). Orders: 2,116 cancelled, 52,764 completed, 2,814 partially returned, 2,306 returned. Source has 100 SKUs, 18 stores, 12,000 customers, 90 employees, four channels and 16 temporal promotions.

Successful final implementation run: `b8e73286dc384368b402ee563641c879`: 80,646 warehouse sale lines, 6,002 return facts, 2,992 cancelled line rejects plus 90 controlled raw rejects. Complete ordered fact-row hashes including surrogate keys remained identical across repeated ETL. SCD insertion CH00 / Integration region / 2026-02-01 passed: changed=True on first call; identical second call changed=False; zero overlapping version pairs; zero facts outside their referenced store interval. Both offline SCD tests passed: exclusive intervals and same-date conflicting-region rejection before any mutation. Compileall passed. Default generation against populated source printed preservation skip and performed no overwrite.

Two initial repeat probes were deliberately interrupted after MariaDB chose a slow join/upsert plan with its small buffer pool. Transactions rolled back and FAILED audit rows were retained. The final implementation uses natural-key maps and parameterized batched upserts instead; final repeat verification passed. These failure audit records are expected historical evidence, not current ETL failure.

SQL04 provides net sales, five grouping views, all four brand/channel CUBE grouping sets, SKU-month weighted after-discount price and units, and brand/channel metrics. SQL05 answers product rankings, seasonal rollup/drilldown, brand/channel slice/dice/CUBE, price-demand observations plus Pearson correlation, and historical management region/store rollup. Price-demand correlation is descriptive and does not establish causal price elasticity.

Final extraction/transformation/load responsibilities are implemented in `etl.extract.extract_sales`, `etl.transform.transform_sales`, and `etl.load.load_sales`; the pipeline calls those functions directly. A final live read-only check transformed all 80,646 accepted source lines and confirmed the exact Decimal revenue total equals warehouse facts. Safe SQL04 recreation completed and the product units, SKU-month price/units, brand-channel and cube views all returned results with the expected columns.
