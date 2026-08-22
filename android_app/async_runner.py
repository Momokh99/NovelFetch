import asyncio
import threading
from concurrent.futures import CancelledError

from kivy.clock import Clock


class AsyncLoop:
    """Owns ONE asyncio event loop, run forever on a background daemon thread.

    Why a dedicated forever-loop instead of asyncio.run() per call:
    RoyalRoadSource/WuxiaSpotSource create httpx.AsyncClient instances once at
    import time. An AsyncClient binds to whichever event loop first uses it, and
    a per-call loop would let different threads/loops touch the same client.
    One stable loop keeps every await on the same thread, forever.
    """

    def __init__(self):
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._run, name="async-loop", daemon=True
        )

    def _run(self):
        asyncio.set_event_loop(self._loop)   # claim this thread as the loop's thread
        self._loop.run_forever()             # pump pending coroutines forever

    def start(self):
        self._thread.start()

    def stop(self):
        if self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)

    def run(self, coro, on_done=None, timeout=None):
        """Schedule a coroutine onto the worker loop from any thread.

        on_done(result, error) is invoked on the Kivy thread (UI-safe).
        - result: the coroutine's return value
        - error:  the exception if it raised, else None
        - timeout: seconds before the coroutine is cancelled; None (default)
          means unbounded. Pass a short timeout for network one-shots so a
          hung connection can't leave the UI busy forever — but leave long,
          user-initiated jobs (novel downloads) without one.

        Why deliver (result, error) instead of re-raising: the failure happened
        on another thread; catching it there and hand-delivering via callback
        is the only safe way to report errors to widgets.
        """
        if timeout is not None:
            coro = asyncio.wait_for(coro, timeout=timeout)
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        if on_done is not None:
            def _finalize(fut):
                try:
                    result = fut.result()
                except CancelledError:
                    # Cancelled by the caller (.cancel()), which owns the UI
                    # state for that path — e.g. download_dialog._cancel().
                    # CancelledError subclasses BaseException (not Exception),
                    # so it must be handled before the generic except.
                    return
                except Exception as exc:
                    result, error = None, exc
                else:
                    error = None
                # Clock.schedule_once is documented thread-safe: hop back to the
                # Kivy thread so the callback can safely touch widgets. Guarded:
                # an exception inside on_done must not kill this callback chain.
                def _deliver(_dt):
                    try:
                        on_done(result, error)
                    except Exception:
                        pass
                Clock.schedule_once(_deliver)
            future.add_done_callback(_finalize)  # runs inside the asyncio thread
        return future

    def to_thread(self, fn, *args, **kwargs):
        """Run blocking/sync code (e.g. _translate_text) off the worker loop."""
        return asyncio.run_coroutine_threadsafe(
            asyncio.to_thread(fn, *args, **kwargs), self._loop
        )


async_loop = AsyncLoop()  # singleton, imported by screens
