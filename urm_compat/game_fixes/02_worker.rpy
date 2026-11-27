init 999 python:

    # -----------------------------------------------------------------------
    # The worker: our slow work, never on a frame (the speed plan, DECISIONS
    # 2026-11-25: no piece of our work holds the game longer than 16 ms).
    #
    # A job is a generator function; each `yield` is a point where it may
    # pause (a float yielded, 0 to 1, is its progress), and it ends by
    # yielding _URMWorkDone(result) (a generator cannot return a value on
    # Python 2). A plain function is a job done in one go. Two kinds:
    #   _urm_work_slices(name, fn)  runs on the game's own thread, between
    #       frames: the engine's periodic callbacks (20 a second, in every
    #       interaction, 7.3.5 - 8.5) give it at most _URM_WORK_SLICE
    #       seconds each. For work that touches the store or the engine.
    #   _urm_work_thread(name, fn)  runs on a thread of its own, pausing
    #       every _URM_WORK_SLICE so the game's thread gets the interpreter
    #       (one runs at a time). For isolated work such as reading script
    #       data or talking to the update server. It must never touch the
    #       store or engine state or make or change rollback objects. Store
    #       code makes by default (a list, dict or set literal, range,
    #       sorted, list(), dict(), a class on `object`: FINDINGS, Engines;
    #       its job object is python_object). With no threads
    #       (web builds) it runs as slices. Blocking I/O requires a thread
    #       and never holds up settling the startup script reads.
    # then(result), when given, runs on the game's thread once the job is
    # done (failed: result is None). A job's state: _urm_work_state(name).
    # Kept in our memory, never saved.
    # -----------------------------------------------------------------------

    _URM_WORK_SLICE = 0.008

    # A job's state is written from its thread: python_object, the
    # interpreter's own object (in store code `object` is the rollback's
    # kind, noted in the rollback log at every change; minstore.py).

    class _URMWorkDone(python_object):
        """What a job yields last: its result."""
        def __init__(self, result=None):
            self.result = result

    class _URMWorkWait(python_object):
        """What a job yields while it only waits (a pause in typing): the
        rest of this frame's share goes to the other jobs."""

    _URM_WORK_WAIT = _URMWorkWait()

    class _URMWorkJob(python_object):
        def __init__(self, name, fn, then, threaded, blocking_io):
            self.name = name
            self.fn = fn
            self.then = then
            self.threaded = threaded
            self.blocking_io = blocking_io
            self.state = "waiting"      # waiting, running, ready, failed, cancelled
            self.progress = 0.0
            self.result = None
            self.gen = None
            self.reported = False

    class _URMWork(python_object):
        def __init__(self):
            self.jobs = python_dict()   # name -> _URMWorkJob; only the game's thread touches these two
            self.order = python_list()  # slice jobs, in the order asked

    def _urm_work():
        return _urm_kept("work", _URMWork)

    def _urm_work_step(job):
        """One pass of a job's generator; True when it has finished."""
        if job.gen is None:
            job.state = "running"
            job.gen = job.fn()
            if not hasattr(job.gen, "next") and not hasattr(job.gen, "__next__"):
                job.result = job.gen    # a plain function: done in one go
                job.state = "ready"
                return True
        try:
            said = next(job.gen)
        except StopIteration:
            job.state = "ready"
            return True
        if isinstance(said, _URMWorkDone):
            job.result = said.result
            job.state = "ready"
            return True
        if isinstance(said, float):
            job.progress = said
        return said is _URM_WORK_WAIT

    def _urm_work_run(job, budget):
        """Run a job until it finishes or `budget` seconds pass."""
        import sys
        import time
        end = time.time() + budget
        try:
            while job.state in ("waiting", "running"):
                if _urm_work_step(job) or job.state not in ("waiting", "running"):
                    break
                if time.time() >= end:
                    break
        except Exception as error:
            job.state = "failed"
            job.result = None
            # Ren'Py's store print can set a gameplay checkpoint on 7.3.5.
            if sys.stdout is not None:
                sys.stdout.write("MRM: %s failed (%s)\n" % (job.name, error))

    def _urm_work_thread_body(job):
        import time
        while job.state in ("waiting", "running"):
            _urm_work_run(job, _URM_WORK_SLICE)
            time.sleep(0.001)           # the game's thread takes the interpreter

    def _urm_work_add(name, fn, then, threaded, first=False, blocking_io=False):
        work = _urm_work()
        old = work.jobs.get(name)
        if old is not None and old.state in ("waiting", "running"):
            old.state = "cancelled"
        job = _URMWorkJob(name, fn, then, threaded, blocking_io)
        work.jobs[name] = job
        if threaded:
            try:
                import threading
                worker = threading.Thread(target=_urm_work_thread_body, args=(job,), name="URM+ " + name)
                worker.daemon = True
                worker.start()
                return job
            except Exception:
                job.threaded = False
                if blocking_io:
                    job.state = "failed"
                    return job
        if first:
            work.order.insert(0, job)   # what the player asked for, ahead of reading behind the game
        else:
            work.order.append(job)
        return job

    def _urm_work_slices(name, fn, then=None, first=False):
        """Run fn's generator on the game's thread, between frames. first:
        the player is waiting on it (a search typed): it takes the frames'
        share before the reading done behind the game."""
        return _urm_work_add(name, fn, then, False, first)

    def _urm_work_thread(name, fn, then=None, blocking_io=False):
        """Run fn's work on a thread. Blocking I/O has no in-frame fallback."""
        return _urm_work_add(name, fn, then, True, blocking_io=blocking_io)

    def _urm_work_state(name):
        job = _urm_work().jobs.get(name)
        return job.state if job is not None else None

    def _urm_work_result(name):
        job = _urm_work().jobs.get(name)
        return job.result if job is not None and job.state == "ready" else None

    def _urm_work_progress(name):
        job = _urm_work().jobs.get(name)
        if job is None:
            return None
        return 1.0 if job.state == "ready" else job.progress

    def _urm_work_cancel(name):
        job = _urm_work().jobs.get(name)
        if job is not None and job.state in ("waiting", "running"):
            job.state = "cancelled"

    def _urm_work_finish(name):
        """Run a slice job to its end now: for an answer asked for before
        its job got there (a screen opened early pays the rest once)."""
        job = _urm_work().jobs.get(name)
        if job is not None and not job.threaded and job.state in ("waiting", "running")                 and job.gen is not None and getattr(job.gen, "gi_running", False):
            return None         # asked from inside its own steps: never step it again
        if job is not None and not job.threaded and job.state in ("waiting", "running"):
            _urm_work_run(job, 1e9)
            if job.state in ("ready", "failed") and not job.reported:
                job.reported = True     # only this job's then(), never another job's steps
                if job.then is not None:
                    try:
                        job.then(job.result)
                    except Exception as error:
                        print("MRM: %s, then failed (%s)" % (job.name, error))
        return _urm_work_result(name)

    def _urm_work_busy(settling=False):
        """Is any job still to finish (the speed check asks)."""
        for job in python_list(_urm_work().jobs.values()):
            if settling and job.blocking_io:
                continue
            if job.state in ("waiting", "running") or (job.state in ("ready", "failed") and not job.reported):
                return True
        return False

    def _urm_work_tick():
        """config.periodic_callbacks: slices for the waiting jobs, and the
        then() of every job that finished."""
        import time
        work = _urm_work()
        end = time.time() + _URM_WORK_SLICE
        for job in python_list(work.order):
            if job.state not in ("waiting", "running"):
                work.order.remove(job)
                continue
            left = end - time.time()
            if left <= 0:
                break
            _urm_work_run(job, left)
        for job in python_list(work.jobs.values()):
            if job.state in ("ready", "failed") and not job.reported:
                job.reported = True
                if job.then is not None:
                    try:
                        job.then(job.result)
                    except Exception as error:
                        print("MRM: %s, then failed (%s)" % (job.name, error))
        # Once every job asked for at start-up is done, what they read is
        # moved out of the collector's way (_urm_work_settle).
        if (not getattr(_URMMemory, "settled", False)
                and any(not job.blocking_io for job in work.jobs.values()) and not _urm_work_busy(settling=True)):
            _urm_work_settle()

    def _urm_work_settle():
        """Once the start-up reads are done: on Python 3, the objects alive
        now (the game's script, our reads) move out of the garbage
        collector's way (gc.freeze), so the full collections Ren'Py runs
        now and then walk only what is made after: 0.45 s on Finding Cloud
        9, 1.5 s on Being a DIK with everything kept (FINDINGS, Engines).
        Python 2.7 has no freeze. Once per run."""

        import gc
        if getattr(_URMMemory, "settled", False):
            return
        _URMMemory.settled = True
        if hasattr(gc, "freeze"):
            gc.freeze()

    # A game reloaded in place (Shift+R, an update that reloads the script)
    # starts here again: what the last run froze is let go first, or it
    # would never be freed.
    try:
        import gc as _urm_gc
        if hasattr(_urm_gc, "unfreeze"):
            _urm_gc.unfreeze()
    except Exception:
        pass

    if _urm_work_tick not in config.periodic_callbacks:
        config.periodic_callbacks.append(_urm_work_tick)

    # -----------------------------------------------------------------------
    # Ren'Py's round, on the Python 2 engines that take Python 3's (7.5 -
    # 7.8: renpy.compat gives every module future's `round`, which works
    # each number out through Decimal). Text calls it for every size it
    # scales: on Thief of Hearts 2 (7.8.2) half of drawing a Settings page
    # (72 of 143 ms) was in it (FINDINGS). The same answer, worked out on
    # the float: round half to even, as Python 3 rounds; anything else
    # (digits asked for, an int, inf or nan) goes to the engine's own.
    # Every engine module holding it gets ours.
    # -----------------------------------------------------------------------

    import math as _urm_math

    def _urm_round_fast(slow):
        def round(number, ndigits=None):
            if ndigits is None and type(number) is float and number - number == 0.0:
                whole = _urm_math.floor(number)
                part = number - whole           # exact for every float
                if part > 0.5 or (part == 0.5 and whole % 2 == 1.0):
                    whole += 1.0
                return int(whole)
            if ndigits is None:
                return slow(number)
            return slow(number, ndigits)
        round._urm_slow = slow
        return round

    def _urm_round_engine():
        import sys
        slow = getattr(getattr(renpy, "compat", None), "round", None)
        module = getattr(slow, "__module__", "") or ""
        if slow is None or not module.startswith("future"):
            return 0
        fast = _urm_round_fast(slow)
        n = 0
        for name, mod in python_list(sys.modules.items()):
            if mod is None or not (name == "renpy" or name.startswith("renpy.")):
                continue
            if getattr(mod, "round", None) is slow:
                try:
                    mod.round = fast
                    n += 1
                except Exception:
                    pass
        return n

    try:
        _urm_round_engine()
    except Exception as error:
        print("MRM: the engine's round is left as it is (%s)" % (error,))
