# Phone Sales Data Warehouse — implementation contract

Approved scope: user specification dated 2026-11-17. Work directly in current workspace; no clone, commits or push. Backup: backups/20261117_214730/workspace_before.zip. Preserve .env and modified data/error_manifest.json and output/benchmark_result.csv.

## Architecture and decisions
Reuse Python HTTP Server, MVC, SQLAlchemy/PyMySQL, responsive tabs and Chart.js. Database names are fixed phone_source and phone_dw, independent of legacy SOURCE_DB values in .env. Money uses DECIMAL(18,2). Data dates 2024-01-01 through 2026-12-31; returns may extend into 2027. KPI date filters are SALE COHORT dates: returns attributed to original sale, while return date remains independently queryable. Net revenue = sale after discount minus refunds; net cost = original cost minus returned cost; gross profit = net revenue minus net cost; return rate = returned units / sold units; AOV = net revenue / valid distinct orders. Invalid raw imports are kept separate from constrained 3NF tables, then extracted and rejected audibly by ETL. Never disable source FK integrity to inject errors.

## Shared database contract
Source tables use Vietnamese names as requested. Warehouse columns below are binding for all tasks:
- dim_thoi_gian(thoi_gian_key INT YYYYMMDD, ngay DATE, nam, quy, thang)
- dim_san_pham(san_pham_key, ma_sku, ten_san_pham, thuong_hieu, ram_gb, bo_nho_gb, mau_sac)
- dim_cua_hang(cua_hang_key, ma_cua_hang, ten_cua_hang, tinh_thanh, khu_vuc_quan_ly, ngay_hieu_luc DATE, ngay_het_han DATE exclusive, is_current)
- dim_khach_hang(khach_hang_key, ma_khach_hang, ho_ten, tinh_thanh)
- dim_kenh_ban(kenh_ban_key, ma_kenh, ten_kenh)
- dim_khuyen_mai(khuyen_mai_key, ma_khuyen_mai, ten_khuyen_mai)
- fact_ban_hang(ban_hang_key, ma_chi_tiet UNIQUE, ma_don_hang, thoi_gian_key, san_pham_key, cua_hang_key, khach_hang_key, kenh_ban_key, khuyen_mai_key, so_luong, don_gia, giam_gia, doanh_thu, gia_von) [gia_von is total line cost]
- fact_tra_hang(tra_hang_key, ma_chi_tiet_tra UNIQUE, ban_hang_key FK, thoi_gian_key [return date], so_luong_tra, tien_hoan, gia_von_hoan)
- vw_sales_net: one row per sale after LEFT JOIN PREAGGREGATED returns. Contains every fact_ban_hang column plus so_luong_tra, tien_hoan, gia_von_hoan, doanh_thu_thuan, gia_von_thuan, loi_nhuan. Zero coalescing required.
- etl_log, etl_data_quality, etl_reject: run_id on every row; exact additional columns owned by data implementer and consumers inspect schema.

## Tasks / ownership
- [x] Phase 1 audit all text files and backup before edits; preserve dirty files.
- [ ] Data implementation: common/, sql/, generator/, etl/, .env.example, requirements.txt. Includes SCD2 tests and source-safe load. Public functions generator.generate_data.main(), etl.pipeline.run_etl(init_dw=False)->run_id; etl.demo_scd2.change_store(ma_cua_hang, khu_vuc, ngay_hieu_luc)->dict and main(). Must serialize SCD changes and ETL; intervals [start,end). Fixed output under output/phone_sales and data/phone_sales.
- [ ] Web implementation: mvc/, web/, web_app.py; filters, overview, store/search_store, scd2_change, etl, run_tests, sql. Local Chart.js, six charts, errors visible, stale-request protection, SELECT playground restricted to approved table identifiers and functions, read-only transaction/time cap.
- [ ] Verification/orchestration: tests/run_dq_tests.py provides run_tests()->list[dict] and main()->exit code; actual ten checks including ETL rerun. analysis/benchmark.py real repeated equivalent queries and result equality; run_all.py safe default all, explicit reset guard. Tests no hardcoded PASS.
- [ ] Documentation: README, mapping, dictionary, ERD, demo and Windows/IDE guides; retire inactive education scripts after backup.
- [ ] Integration: local MariaDB availability, generate >=50k orders, ETL repeat, SCD2, real queries, APIs and browser six charts; final report with precise PASS/FAIL/SKIP.

## Review focus
No destructive defaults; exact monetary math; cumulative returns never exceed sold quantities/refunds; cancelled sales excluded; SCD2 historical lookup; concurrency and idempotency; no secrets; all filters apply to all panels; prevent cross-database SQL access. All work remains uncommitted. User has explicitly opted out of approval/plan-only gates.
