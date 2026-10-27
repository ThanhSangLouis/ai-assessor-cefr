"""Tests for the account management CLI.

The CLI is how every account on every machine gets created -- the setup guide
`docs/plan/CHAY_TREN_LOCALHOST.md` tells teammates to run it -- so its failure
messages are part of the product, not debug output.
"""

from aicefr import accounts_cli


def test_tao_tai_khoan_va_liet_ke(tmp_path, capsys):
    db = str(tmp_path / "t.db")
    rc = accounts_cli.main(
        [
            "--db",
            db,
            "them",
            "--but-danh",
            "SV-001",
            "--vai-tro",
            "student",
            "--mat-khau",
            "matkhau123",
        ]
    )
    assert rc == 0
    assert accounts_cli.main(["--db", db, "liet-ke"]) == 0
    assert "SV-001" in capsys.readouterr().out


def test_but_danh_trung_bi_tu_choi(tmp_path):
    db = str(tmp_path / "t.db")
    args = [
        "--db",
        db,
        "them",
        "--but-danh",
        "SV-001",
        "--vai-tro",
        "student",
        "--mat-khau",
        "matkhau123",
    ]
    assert accounts_cli.main(args) == 0
    assert accounts_cli.main(args) == 1


def test_mat_khau_qua_ngan_bi_tu_choi(tmp_path):
    db = str(tmp_path / "t.db")
    rc = accounts_cli.main(
        ["--db", db, "them", "--but-danh", "SV-002", "--vai-tro", "student", "--mat-khau", "123"]
    )
    assert rc == 1


def test_but_danh_giong_mssv_bi_tu_choi_bang_mot_dong_khong_phai_traceback(tmp_path, capsys):
    """Rejection must reach the operator as one readable line.

    It used to raise out of the repository: the user typed a password twice and
    then read a traceback. The check now runs before the prompt.
    """
    db = str(tmp_path / "t.db")
    rc = accounts_cli.main(
        [
            "--db",
            db,
            "them",
            "--but-danh",
            "23110301",
            "--vai-tro",
            "student",
            "--mat-khau",
            "matkhau123",
        ]
    )
    assert rc == 1
    err = capsys.readouterr().err
    assert "Traceback" not in err
    assert "mã số sinh viên" in err
