import asyncio
import threading

from kivy.clock import Clock

class AsyncLoop:
    """Owns ONE asyncio event loop, run forever on a background daemon thread."""
    
    def __init__(self):
        self._loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run, name="async_loop", daemon=True)

    def _run(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def start(self):
        self._thread.start()

    def stop(self):
        if self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)

    def run(self, coro, on_done=None):
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        if on_done is not None:
            def _finalize(fut):
                try:
                    result = fut.result()          # raise-if-failed
                except Exception as exc:
                    result, error = None, exc
                else:
                    error = None
                Clock.schedule_once(lambda dt: on_done(result, error))
            future.add_done_callback(_finalize)    # runs in the asyncio thread
        return future

    def to_thread(self, fn, *args, **kwargs):
        return asyncio.run_coroutine_threadsafe(
            asyncio.to_thread(fn, *args, **kwargs), self._loop
        )


async_loop = AsyncLoop()
