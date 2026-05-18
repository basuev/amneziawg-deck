import asyncio
import os
from unittest.mock import patch, AsyncMock

import wg_manager as wg


SAMPLE_DUMP = (
    "PRIVATE_KEY\tPUBLIC_IFACE\t51820\toff\n"
    "PEER_PUBKEY_1\tPSK_NULL\t198.51.100.10:51820\t0.0.0.0/0\t1700000000\t12345\t67890\t25\n"
)


def test_parse_awg_dump_single_peer():
    peers = wg.parse_awg_dump(SAMPLE_DUMP)
    assert len(peers) == 1
    p = peers[0]
    assert p.public_key == "PEER_PUBKEY_1"
    assert p.endpoint == "198.51.100.10:51820"
    assert p.last_handshake == 1700000000
    assert p.rx_bytes == 12345
    assert p.tx_bytes == 67890


def test_parse_awg_dump_empty():
    assert wg.parse_awg_dump("") == []
    assert wg.parse_awg_dump("only-interface-line\tfoo\t51820\toff") == []


def test_parse_awg_dump_skips_malformed():
    bad = "INTERFACE\tLINE\t51820\toff\nshort\tline\n"
    assert wg.parse_awg_dump(bad) == []


def test_parse_awg_dump_no_handshake_yet():
    payload = (
        "PRIVATE_KEY\tPUBLIC_IFACE\t51820\toff\n"
        "PEER_PUBKEY_1\tPSK_NULL\t198.51.100.10:51820\t0.0.0.0/0\t0\t0\t0\t0\n"
    )
    peers = wg.parse_awg_dump(payload)
    assert peers[0].last_handshake == 0


def test_redact_strips_private_key():
    text = "PrivateKey = qHQy7zHhJYRZsLqXmFkM7BxOAU6ojP9Wmn8sb6KtZGE= and PresharedKey=AAA"
    out = wg._redact(text)
    assert "qHQy" not in out
    assert "AAA" not in out
    assert "<redacted>" in out


def test_build_env_injects_path_and_userspace():
    env = wg._build_env()
    assert env["PATH"].startswith(wg.C.BIN_DIR + ":")
    assert env["WG_QUICK_USERSPACE_IMPLEMENTATION"] == wg.C.AWG_GO
    assert env["AMNEZIAWG_DECKY_LOG"].endswith("amneziawg-go.log")


def test_build_env_strips_decky_leaked_vars(monkeypatch):
    monkeypatch.setenv("LD_LIBRARY_PATH", "/decky/leaked/path")
    monkeypatch.setenv("LD_PRELOAD", "/decky/preload.so")
    monkeypatch.setenv("PYTHONHOME", "/decky/python")
    env = wg._build_env()
    assert "LD_LIBRARY_PATH" not in env
    assert "LD_PRELOAD" not in env
    assert "PYTHONHOME" not in env


def _make_proc(rc: int, stdout: bytes = b"", stderr: bytes = b""):
    proc = AsyncMock()
    proc.returncode = rc
    proc.communicate = AsyncMock(return_value=(stdout, stderr))
    proc.kill = lambda: None
    proc.wait = AsyncMock(return_value=None)
    return proc


def test_is_interface_up_true():
    proc = _make_proc(0)
    with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=proc)):
        result = asyncio.run(wg.is_interface_up("wg0"))
    assert result is True


def test_is_interface_up_false_nonzero():
    proc = _make_proc(1, stderr=b"Device not found")
    with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=proc)):
        result = asyncio.run(wg.is_interface_up("wg0"))
    assert result is False


def _write_fixture_conf(tmp_path):
    p = tmp_path / "wg0.conf"
    p.write_text(
        "[Interface]\nPrivateKey = AAA\nAddress = 10.0.0.1/32\n"
        "I2 =\nI3 =\n[Peer]\nPublicKey = BBB\nEndpoint = 1.2.3.4:5\nAllowedIPs = 0.0.0.0/0\n"
    )
    return str(p)


def test_up_raises_on_nonzero(tmp_path):
    proc = _make_proc(1, stderr=b"awg-quick: oops")
    conf = _write_fixture_conf(tmp_path)
    with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=proc)):
        try:
            asyncio.run(wg.up("wg0", conf))
        except wg.WgError as e:
            assert "oops" in str(e)
        else:
            raise AssertionError("expected WgError")


def test_up_success_sanitizes_config(tmp_path):
    proc = _make_proc(0, stdout=b"")
    conf = _write_fixture_conf(tmp_path)
    with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=proc)):
        asyncio.run(wg.up("wg0", conf))
    sanitized = os.path.join(wg.C.RUNTIME_DIR, "wg0.conf")
    assert os.path.isfile(sanitized)
    text = open(sanitized).read()
    assert "I2 =" not in text
    assert "I3 =" not in text


def test_dump_parses():
    proc = _make_proc(0, stdout=SAMPLE_DUMP.encode())
    with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=proc)):
        peers = asyncio.run(wg.dump("wg0"))
    assert len(peers) == 1
    assert peers[0].endpoint == "198.51.100.10:51820"


def test_read_logs_missing_file_returns_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(wg.C, "AWG_LOG_FILE", str(tmp_path / "nope.log"))
    out = asyncio.run(wg.read_logs(10))
    assert out == ""
