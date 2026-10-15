# Dependency runtime S02

Historical target `3b2d2b78ba5bb35bd162b8f3e5de21ade946d237`; reference `40907cc35b3d04408f9a8713f16d9be99f4cd6c7`; actual base51eff1f.

M10 yêu cầu simplemma cho lemma tiếng Anh. Pin dùng trong task: `simplemma==1.1.2`, wheel cache ngoài Git tại runtime/wheelhouse/scrum-70; đã cài offline vào venv kiểm thử. API `simplemma.lemmatize(token, lang='en')` được đối chiếu [tài liệu repository chính thức](https://github.com/adbar/simplemma), đọc ngày15/10/2026. Không cần tải model lúc runtime; irregular fallback là quy tắc ứng dụng có version, không thay thế dependency đã khai báo.

Lemmatizer không có morphosyntactic context đầy đủ; lemma tương đương chỉ giúp nhận trạng thái chưa chắc, không chứng minh phát âm/ngữ pháp đúng. Không dùng lemma hoặc số từ làm điểm CEFR. Coverage, wheel install và failure behavior được xác minh ở evidence cuối task, không suy từ bước cài dependency.
