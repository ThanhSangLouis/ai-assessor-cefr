# SCRUM-67 — Phân công Luna

Ngày 15/10/2026. Ba prompt A1 được lưu trước dispatch; root review/verification, Luna implement. Owner mỗi file ghi trong prompt. Historical target `3b2d2b7`, Sang `40907cc`; actual base `bab5f25`. Global SDD approval và reviewer acceptance còn PENDING.

- Billing: domain/money/repository/settlement.
- Gateway: sandbox/test adapter/signature/license/key protection.
- Data/API: W5 export/erase/retention/backup/restore và admin API/handoff.

## Review feedback đã phát hành (diễn giải lại)

1. Billing: sửa proration theo kỳ đã trả, quote snapshot/expiry và retry idempotent; kiểm quota/grace/renewal/downgrade, organization binding, repository race và dependency injection. Bổ sung test các nhánh từ chối và rollback trước final full suite.
2. Gateway/license: verify raw Stripe body, VNPay form/amount/GMT+7, MoMo pending/captured; callback signed header qua WSGI, key protection, finite expiry, issuance/install replay và optional test transport. Kiểm bằng fixture, không gọi merchant thật.
3. Data/API: giữ dữ liệu export hữu ích bằng allowlist; xác định đúng ownership và audit, bổ sung migration privacy v10 giữ checksum v5–v9. Kiểm preview stale khi job/intent đổi, lỗi wrong-type IDs/manifest, retention lock, cleanup retry, shared media và protected-key restore.
4. Final verification: Luna bổ sung regression/coverage và Chromium harness trên API thật; Codex chạy độc lập full non-smoke, clean wheel, browser và populated W5 roundtrip. Review read-only bổ sung không phát hiện BLOCKER/MAJOR trong vùng đã kiểm; không thay nghiệm thu Sang/Nguyên.

Đây là bản biên soạn dễ đọc của các follow-up thực tế, không phải transcript nguyên văn. Ba A1 ban đầu được giữ nguyên; fingerprint issuance `d5687f37e389236c7db41990e98705f9f10466af3dc984ef4140934cf5058ed3`. Workbook W05 sheet Thắng có bản diễn giải vừa phải; không ghi lời nhắc quản lý log của user.
