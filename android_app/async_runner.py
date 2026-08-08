import asyncio
import threading

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

    def run(self, coro, on_done=None):
        """Schedule a coroutine onto the worker loop from any thread.

        on_done(result, error) is invoked on the Kivy thread (UI-safe).
        - result: the coroutine's return value
        - error:  the exception if it raised, else None

        Why deliver (result, error) instead of re-raising: the failure happened
        on another thread; catching it there and hand-delivering via callback
        is the only safe way to report errors to widgets.
        """
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        if on_done is not None:
            def _finalize(fut):
                try:
                    result = fut.result()
                except Exception as exc:
                    result, error = None, exc
                else:
                    error = None
                # Clock.schedule_once is documented thread-safe: hop back to the
                # Kivy thread so the callback can safely touch widgets.
                Clock.schedule_once(lambda dt: on_done(result, error))
            future.add_done_callback(_finalize)  # runs inside the asyncio thread
        return future

    def to_thread(self, fn, *args, **kwargs):
        """Run blocking/sync code (e.g. _translate_text) off the worker loop."""
        return asyncio.run_coroutine_threadsafe(
            asyncio.to_thread(fn, *args, **kwargs), self._loop
        )


async_loop = AsyncLoop()  # singleton, imported by screens
