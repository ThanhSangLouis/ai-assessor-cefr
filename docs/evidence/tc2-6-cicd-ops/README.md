# TC2.6 — CI/CD và vận hành

**Nguồn tiêu chí:** rubric PDF tại docs/rubric/.
**Trạng thái:** cập nhật 28/11/2026. Pipeline nằm trong repo, chạy xanh, tự triển khai lên production; môi trường mở công khai. Chờ GVHD xác nhận.

## Hồ sơ cần có

Cấu hình pipeline, lịch sử run/deploy, build artifact, hướng dẫn vận hành và link môi trường nếu có.

## Minh chứng hiện có

| Mã | Minh chứng | Nội dung |
| --- | --- | --- |
| OP-01 | [ci.yml](../../../.github/workflows/ci.yml) | 6 job: tài liệu và tệp cấm; định dạng, lint, test, độ phủ; MongoDB + Redis + S3 thật; dựng ảnh Docker + Trivy; ESLint; gitleaks |
| OP-02 | [deploy.yml](../../../.github/workflows/deploy.yml) | Merge vào `main` + CI xanh thì tự triển khai lên EC2 qua SSH; sao lưu trước khi cập nhật; chỉ triển khai commit mới nhất của `main` |
| OP-03 | [codeql.yml](../../../.github/workflows/codeql.yml) | Phân tích bảo mật mã |
| OP-04 | [uptime.yml](../../../.github/workflows/uptime.yml) + [`tools/uptime_report.py`](../../../tools/uptime_report.py) | Mỗi 30 phút gọi `/healthz` và trang chủ; lịch sử chạy là số liệu thời gian hoạt động (bật từ khi nhánh này được merge) |
| OP-05 | Lần chạy thành công gần nhất (26/11/2026, `2dfa4fc`) | [CI](https://github.com/ThanhSangLouis/ai-assessor-cefr/actions/runs/45749465088), [Deploy EC2](https://github.com/ThanhSangLouis/ai-assessor-cefr/actions/runs/45751203044). Lịch sử: [Actions](https://github.com/ThanhSangLouis/ai-assessor-cefr/actions) |
| OP-06 | Môi trường đang chạy | https://speakup.fit, ai cũng mở được. Ngày 28/11: trang chủ 200, tải trung bình ~0,95 giây (5 lần `curl`); `/healthz` 200 |
| OP-07 | Hướng dẫn vận hành | [TRIEN_KHAI_EC2.md](../../plan/TRIEN_KHAI_EC2.md), [TRIEN_KHAI_CHO_AI.md](../../plan/TRIEN_KHAI_CHO_AI.md), [CHAY_TREN_LOCALHOST.md](../../plan/CHAY_TREN_LOCALHOST.md) |

## Còn thiếu / giới hạn

- Số liệu uptime chỉ có từ khi `uptime.yml` lên `main`; trước đó chỉ có lịch sử deploy và kiểm `/healthz` thủ công.
- Production chạy một máy EC2 (2 vCPU, 8 GB), không có bản dự phòng.

## Lịch sử (W3, 10/2026)

| Artifact | Phạm vi | Trạng thái |
| --- | --- | --- |
| [Local run guide](../../local-run.md) | Setup/CLI, external data/model, loopback, restart/shutdown | W3 local demonstration |
| [W3 Evidence](../../sdd/features/w3-local-integration/evidence/evidence-manifest.md) | Actual local tests/build/browser/smoke gắn revision | Local verification |
