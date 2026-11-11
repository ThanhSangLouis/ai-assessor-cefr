"""Tests for the account management CLI.

The CLI is how every account on every machine gets created -- the setup guide
`docs/plan/CHAY_TREN_LOCALHOST.md` tells teammates to run it -- so its failure
messages are part of the product, not debug output. D103: an account is its email.
"""

from aicefr import accounts_cli


def _add(db: str, email: str, password: str = "matkhau123") -> int:
    return accounts_cli.main(
        ["--db", db, "them", "--email", email, "--vai-tro", "student", "--mat-khau", password]
    )


def test_tao_tai_khoan_va_liet_ke(tmp_path, capsys):
    db = str(tmp_path / "t.db")
    assert _add(db, "An.Nguyen@Truong.edu.vn") == 0
    assert accounts_cli.main(["--db", db, "liet-ke"]) == 0
    assert "an.nguyen@truong.edu.vn" in capsys.readouterr().out


def test_email_trung_bi_tu_choi(tmp_path):
    db = str(tmp_path / "t.db")
    assert _add(db, "sv1@truong.edu.vn") == 0
    assert _add(db, "SV1@truong.edu.vn") == 1


def test_mat_khau_qua_ngan_bi_tu_choi(tmp_path):
    db = str(tmp_path / "t.db")
    assert _add(db, "sv2@truong.edu.vn", "123") == 1


def test_email_sai_bi_tu_choi_bang_mot_dong_khong_phai_traceback(tmp_path, capsys):
    """Rejection must reach the operator as one readable line.

    It used to raise out of the repository: the user typed a password twice and
    then read a traceback. The check now runs before the prompt.
    """
    db = str(tmp_path / "t.db")
    assert _add(db, "23110301") == 1
    err = capsys.readouterr().err
    assert "Traceback" not in err
    assert "Email không hợp lệ" in err


def test_mo_khoa_theo_email(tmp_path, capsys):
    db = str(tmp_path / "t.db")
    assert _add(db, "sv3@truong.edu.vn") == 0
    assert accounts_cli.main(["--db", db, "mo-khoa", "--email", "SV3@truong.edu.vn"]) == 0
    assert accounts_cli.main(["--db", db, "mo-khoa", "--email", "khong@co.vn"]) == 1
