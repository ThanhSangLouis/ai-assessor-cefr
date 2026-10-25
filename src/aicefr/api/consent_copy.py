"""Shared copy for the web and printable consent-v2 form."""

from aicefr.contracts import CURRENT_CONSENT_VERSION

CONSENT_VERSION = CURRENT_CONSENT_VERSION

AUDIO_STORAGE_CHOICE = (
    "Cho phép hệ thống lưu bản ghi âm để xử lý và chấm bài nói. "
    "Nếu không bật lựa chọn này, bạn sẽ không thể nộp audio speaking."
)
RESEARCH_USE_CHOICE = (
    "Cho phép dùng audio và dữ liệu đánh giá đã gắn mã giả danh cho nghiên cứu của nhóm "
    "(tùy chọn, tách biệt với việc lưu audio)."
)

CONSENT_PURPOSE = (
    "Bản ghi âm được dùng để xử lý và chấm bài nói trong hệ thống. "
    "Nếu bạn chọn riêng mục nghiên cứu, nhóm có thể dùng audio và dữ liệu đánh giá "
    "đã gắn mã giả danh cho nghiên cứu. Kết quả AI chỉ hỗ trợ tham khảo, "
    "không phải chứng chỉ CEFR hay quyết định điểm môn học."
)
CONSENT_RETENTION = (
    "Thời hạn lưu/xóa chưa được chốt trong chính sách dữ liệu hiện hành; mốc tối đa "
    "12 tháng mới là đề xuất. Ứng dụng hiện chưa tự động xóa audio theo lịch. "
    "Trước khi thu dữ liệu thật, GVHD cần chốt thời hạn và cách xóa; nhóm sẽ thực hiện "
    "xóa theo chính sách đã chốt."
)
CONSENT_WITHDRAWAL = (
    "Bạn có thể thay đổi riêng từng lựa chọn. Tắt lựa chọn nghiên cứu không ảnh hưởng "
    "quyền nộp bài nếu bạn vẫn bật lưu audio. Tắt lưu audio hoặc rút đồng ý sẽ chặn "
    "các lần nộp mới. "
    "Việc rút đồng ý không tự xóa audio đã lưu. Muốn yêu cầu xóa dữ liệu đã lưu, "
    "hãy liên hệ GVHD hoặc người phụ trách dự án. Việc từ chối nghiên cứu không ảnh hưởng "
    "đến quyền lợi học tập."
)
