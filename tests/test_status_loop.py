import asyncio
from unittest.mock import patch, AsyncMock

import wg_manager as wg
from status_loop import StatusLoop


def _peer(last_handshake: int = 1_700_000_000, rx: int = 100, tx: int = 200):
    return wg.Peer(
        public_key="PUB",
        endpoint="1.2.3.4:51820",
        last_handshake=last_handshake,
        rx_bytes=rx,
        tx_bytes=tx,
    )


def test_tick_disconnected_when_iface_down():
    loop = StatusLoop()
    with patch("status_loop.wg.is_interface_up", AsyncMock(return_value=False)):
        snap = asyncio.run(loop._tick())
    assert snap["connected"] is False
    assert snap["public_endpoint"] == ""


def test_tick_connected_populates_fields():
    loop = StatusLoop()
    with patch("status_loop.wg.is_interface_up", AsyncMock(return_value=True)), \
         patch("status_loop.wg.dump", AsyncMock(return_value=[_peer()])):
        snap = asyncio.run(loop._tick())
    assert snap["connected"] is True
    assert snap["public_endpoint"] == "1.2.3.4:51820"
    assert snap["rx_bytes"] == 100


def test_watchdog_reup_after_two_stale_ticks():
    loop = StatusLoop(stale_handshake_s=180, reup_throttle_s=0)
    loop.set_active_conf("/tmp/x.conf")
    stale_ts = 1

    async def scenario():
        with patch("status_loop.wg.is_interface_up", AsyncMock(return_value=True)), \
             patch("status_loop.wg.dump", AsyncMock(return_value=[_peer(last_handshake=stale_ts)])), \
             patch("status_loop.wg.down", AsyncMock()) as mock_down, \
             patch("status_loop.wg.up", AsyncMock()) as mock_up:
            await loop._tick()
            assert mock_up.await_count == 0
            await loop._tick()
            assert mock_down.await_count == 1
            assert mock_up.await_count == 1

    asyncio.run(scenario())


def test_no_reup_without_active_conf():
    loop = StatusLoop(stale_handshake_s=180, reup_throttle_s=0)
    stale_ts = 1

    async def scenario():
        with patch("status_loop.wg.is_interface_up", AsyncMock(return_value=True)), \
             patch("status_loop.wg.dump", AsyncMock(return_value=[_peer(last_handshake=stale_ts)])), \
             patch("status_loop.wg.down", AsyncMock()) as mock_down, \
             patch("status_loop.wg.up", AsyncMock()) as mock_up:
            for _ in range(3):
                await loop._tick()
            assert mock_down.await_count == 0
            assert mock_up.await_count == 0

    asyncio.run(scenario())


def test_kick_emits_connected_snapshot_when_iface_up():
    loop = StatusLoop()

    async def scenario():
        with patch("status_loop.wg.is_interface_up", AsyncMock(return_value=True)), \
             patch("status_loop.wg.dump", AsyncMock(return_value=[_peer()])), \
             patch("status_loop._emit", AsyncMock()) as mock_emit:
            await loop.kick()
            assert loop._snapshot["connected"] is True
            await asyncio.sleep(0)
            assert mock_emit.await_count == 1
            event_name, payload = mock_emit.await_args.args
            assert event_name == "status_update"
            assert payload["connected"] is True
            assert payload["public_endpoint"] == "1.2.3.4:51820"

    asyncio.run(scenario())


def test_kick_emits_disconnected_snapshot_when_iface_down():
    loop = StatusLoop()
    loop._snapshot["connected"] = True

    async def scenario():
        with patch("status_loop.wg.is_interface_up", AsyncMock(return_value=False)), \
             patch("status_loop._emit", AsyncMock()) as mock_emit:
            await loop.kick()
            assert loop._snapshot["connected"] is False
            await asyncio.sleep(0)
            assert mock_emit.await_count == 1
            _, payload = mock_emit.await_args.args
            assert payload["connected"] is False

    asyncio.run(scenario())


def test_kick_does_not_block_on_hanging_emit():
    loop = StatusLoop()

    async def scenario():
        async def hanging_emit(*_a, **_kw):
            await asyncio.sleep(60)

        with patch("status_loop.wg.is_interface_up", AsyncMock(return_value=True)), \
             patch("status_loop.wg.dump", AsyncMock(return_value=[_peer()])), \
             patch("status_loop._emit", side_effect=hanging_emit):
            await asyncio.wait_for(loop.kick(), timeout=1.0)
            assert loop._snapshot["connected"] is True

    asyncio.run(scenario())


def test_no_reup_when_handshake_zero_means_pending():
    loop = StatusLoop(stale_handshake_s=180, reup_throttle_s=0)
    loop.set_active_conf("/tmp/x.conf")

    async def scenario():
        with patch("status_loop.wg.is_interface_up", AsyncMock(return_value=True)), \
             patch("status_loop.wg.dump", AsyncMock(return_value=[_peer(last_handshake=0)])), \
             patch("status_loop.wg.down", AsyncMock()) as mock_down, \
             patch("status_loop.wg.up", AsyncMock()) as mock_up:
            for _ in range(5):
                await loop._tick()
            assert mock_down.await_count == 0
            assert mock_up.await_count == 0

    asyncio.run(scenario())
