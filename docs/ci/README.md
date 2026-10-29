# CI — pipeline kiem tra

**Trang thai: DANG CHAY** tu 19/09/2026. Cau hinh: [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml).

Truoc do CI bi gat xuong ngay 13/09/2026 de tap trung vao phan chuc nang. Trong
sau ngay tat, **nam pull request duoc merge ma khong co mot check nao chay** —
do la khoang trong ma rubric TC2.6 va TC2.2 deu hoi toi.

## Pipeline co gi

Hai job chay song song:

| Job | Buoc | Doi hoi cua rubric |
|---|---|---|
| `kiem-tra` | lay ma nguon → cai Python (co cache) → cai phu thuoc → kiem dinh dang → lint → kiem thu + do phu → luu bao cao do phu | TC2.1 (phan tich tinh), TC2.5 (do phu >= 70%) |
| `quet-bi-mat` | lay ma nguon (day du lich su) → gitleaks | TC2.1 (bao cao quet secret) |

Tong **chin buoc**, vuot muc 5 cua TC2.6 (yeu cau >= 6 chang).

## Ba quyet dinh dang giai thich

**Chi cai `.[dev]`, khong cai extras `asr` va `vad`.** `asr` keo mlx-whisper (chi
chay tren macOS) hoac faster-whisper; `vad` keo torch khoang 2 GB. Ca hai deu
khong can de chay bo kiem thu — da kiem chung bang cach dung mot moi truong
sach tren Python 3.12 khong co torch va chay day du **442 test, xanh het, do phu
89%**. `default_vad()` tu roi ve `EnergyVad` khi thieu Silero nen khong test nao
hong. Cai torch tren CI chi de no ngoi khong la cach chac chan nhat de bien mot
pipeline hai phut thanh muoi phut va thinh thoang timeout — tuc la tu ban pha ty
le build xanh ma chinh rubric dang do.

**Nguong do phu de o 70%, khong phai 85%.** 70% la muc 5 cua TC2.5; hien tai
dang 89%, tuc con 19 diem du dia. Nguong o day de biet khi nao tut, khong phai
de chan duong ai.

**Quet bi mat tach thanh job rieng.** Mot truc trac cua gitleaks khong duoc che
mat ket qua kiem thu, va nguoc lai. Doc ket qua cung de hon: nhin mot cai la
biet hong o dau.

## Vi sao lan chay hoi thang 9 that bai

**Nguyen nhan da xac dinh: thieu goi phu thuoc kiem thu.** `tests/test_api.py`
dung `TestClient` cua FastAPI, lop nay goi `starlette.testclient`, ma module do
doi goi `httpx2`. Goi nay truoc day chi duoc cai tay tren may phat trien,
**khong khai bao trong `pyproject.toml`**. CI cai bang `pip install -e ".[dev]"`
nen khong co no, va pytest hong ngay o buoc **thu thap** test chu khong phai o
buoc chay:

```
RuntimeError: The starlette.testclient module requires the httpx2 package
```

Da sua: `httpx2>=0.1` nay nam trong `[project.optional-dependencies].dev`.

Bai hoc da ghi thanh nguyen tac trong `pyproject.toml`: **goi nao ma can thi
phai khai bao; chay duoc tren may minh khong phai bang chung.**

## Chay tai cho truoc khi push

`./kiemtra.sh` chay dung nhung buoc ma CI se chay, tru gitleaks.
