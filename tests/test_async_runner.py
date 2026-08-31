"""Tests for gui/async_runner.py — real threads, no Kivy Clock."""

import asyncio

import pytest

from gui.async_runner import AsyncLoop


@pytest.fixture()
def loop():
    al = AsyncLoop()
    al.start()
    yield al
    al.stop()


async def _coro(v):
    return v


async def _bad():
    raise ValueError("boom")


async def _slow():
    await asyncio.sleep(10)


async def _multiply(a, b):
    return a * b


def test_run_returns_future(loop):
    fut = loop.run(_coro(42))
    assert fut.result(5) == 42


def test_run_exception_propagates(loop):
    fut = loop.run(_bad())
    with pytest.raises(ValueError, match="boom"):
        fut.result(5)


def test_run_timeout_cancels(loop):
    fut = loop.run(_slow(), timeout=0.05)
    with pytest.raises((TimeoutError, asyncio.TimeoutError)):
        fut.result(5)


def test_run_with_none_on_done(loop):
    fut = loop.run(_coro("x"), on_done=None)
    assert fut.result(5) == "x"


def test_to_thread(loop):
    fut = loop.to_thread(lambda a, b: a * b, 6, 7)
    assert fut.result(5) == 42


def test_stop_is_idempotent():
    al = AsyncLoop()
    al.start()
    al.stop()
    al.stop()


def test_singleton_exists():
    from gui.async_runner import async_loop
    assert isinstance(async_loop, AsyncLoop)
