import os
import stat
import tempfile

import config as cfg

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def test_list_confs_sorted(tmp_path):
    (tmp_path / "b.conf").write_text("[Interface]\n")
    (tmp_path / "a.conf").write_text("[Interface]\n")
    (tmp_path / "ignored.txt").write_text("[Interface]\n")
    result = cfg.list_confs(str(tmp_path))
    assert [os.path.basename(p) for p in result] == ["a.conf", "b.conf"]


def test_list_confs_missing_dir():
    assert cfg.list_confs("/nonexistent/path/xyz") == []


def test_validate_valid_wg():
    path = os.path.join(FIXTURES, "valid_wg0.conf")
    os.chmod(path, 0o600)
    ok, reason = cfg.validate_conf(path)
    assert ok, reason


def test_validate_valid_amnezia():
    path = os.path.join(FIXTURES, "valid_amnezia.conf")
    os.chmod(path, 0o600)
    ok, reason = cfg.validate_conf(path)
    assert ok, reason


def test_validate_missing_peer():
    path = os.path.join(FIXTURES, "invalid_no_peer.conf")
    os.chmod(path, 0o600)
    ok, reason = cfg.validate_conf(path)
    assert not ok
    assert "[Peer]" in reason


def test_validate_missing_endpoint():
    path = os.path.join(FIXTURES, "invalid_no_endpoint.conf")
    os.chmod(path, 0o600)
    ok, reason = cfg.validate_conf(path)
    assert not ok
    assert "Endpoint" in reason


def test_validate_missing_file():
    ok, reason = cfg.validate_conf("/tmp/does_not_exist_xyz.conf")
    assert not ok
    assert "not found" in reason


def test_validate_chmods_loose_perms(tmp_path):
    src = open(os.path.join(FIXTURES, "valid_wg0.conf")).read()
    p = tmp_path / "loose.conf"
    p.write_text(src)
    os.chmod(p, 0o644)
    ok, _ = cfg.validate_conf(str(p))
    assert ok
    assert stat.S_IMODE(os.stat(p).st_mode) == 0o600


def test_has_amnezia_params():
    assert cfg.has_amnezia_params(os.path.join(FIXTURES, "valid_amnezia.conf"))
    assert not cfg.has_amnezia_params(os.path.join(FIXTURES, "valid_wg0.conf"))


def test_sanitize_drops_empty_i2_i5(tmp_path):
    src = tmp_path / "src.conf"
    src.write_text(
        "[Interface]\n"
        "PrivateKey = AAA\n"
        "Address = 10.0.0.1/32\n"
        "I1 = <b 0xabcdef>\n"
        "I2 = \n"
        "I3 =\n"
        "I4 =   \n"
        "I5 =\t\n"
        "\n"
        "[Peer]\n"
        "PublicKey = BBB\n"
        "Endpoint = 1.2.3.4:51820\n"
        "AllowedIPs = 0.0.0.0/0\n"
    )
    dst = tmp_path / "dst.conf"
    removed = cfg.sanitize_conf(str(src), str(dst))
    assert removed == 4
    content = dst.read_text()
    assert "I1 =" in content
    assert "I2 =" not in content
    assert "I3 =" not in content
    assert "I4 =" not in content
    assert "I5 =" not in content
    assert "[Peer]" in content
    assert stat.S_IMODE(os.stat(dst).st_mode) == 0o600


def test_sanitize_preserves_nonempty_i_values(tmp_path):
    src = tmp_path / "src.conf"
    src.write_text(
        "[Interface]\n"
        "PrivateKey = AAA\n"
        "Address = 10.0.0.1/32\n"
        "I2 = something\n"
        "I3 = <hex 1234>\n"
        "[Peer]\n"
        "PublicKey = BBB\n"
        "Endpoint = 1.2.3.4:51820\n"
        "AllowedIPs = 0.0.0.0/0\n"
    )
    dst = tmp_path / "dst.conf"
    removed = cfg.sanitize_conf(str(src), str(dst))
    assert removed == 0
    content = dst.read_text()
    assert "I2 = something" in content
    assert "I3 = <hex 1234>" in content


def test_sanitize_case_insensitive_key(tmp_path):
    src = tmp_path / "src.conf"
    src.write_text("[Interface]\nPrivateKey = AAA\ni2 =\ni3 = \n")
    dst = tmp_path / "dst.conf"
    removed = cfg.sanitize_conf(str(src), str(dst))
    assert removed == 2


def test_parse_skips_comments_and_blank(tmp_path):
    p = tmp_path / "x.conf"
    p.write_text(
        "# comment\n\n[Interface]\nPrivateKey = abc\nAddress = 10.0.0.1/32\n"
        "\n[Peer]\nPublicKey = def\nEndpoint = 1.2.3.4:5\nAllowedIPs = 0.0.0.0/0\n"
    )
    sections = cfg.parse_conf(str(p))
    assert sections["Interface"][0]["PrivateKey"] == "abc"
    assert sections["Peer"][0]["Endpoint"] == "1.2.3.4:5"
