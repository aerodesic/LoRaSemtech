# Implement simple queue (with thread safety)

import _thread

class RecurseLockException(Exception):
    pass

class recursive_lock():
    def __init__(self, locked=False):
        self._lock = _thread.allocate_lock()
        if locked:
            self._lock.acquire()
        self._release = _thread.allocate_lock()
        self._release.acquire()
        self._ident = None
        self._count = 0

    def acquire(self):
        self._lock.acquire()

        if self._ident == _thread.get_ident():
            # We are the owner, so increase the count
            self._count += 1

        else:
            # Wait for it to be released
            while self._ident != None:
                # Unlock the access
                self._lock.release()
                # Wait for a release
                self._release.acquire()
                # Relock and try test again
                self._lock.acquire()

            # Claim it as ours
            self._ident = _thread.get_ident()
            self._count = 1

        self._lock.release()

    def release(self):
        with self._lock:
            if self._ident == _thread.get_ident():
                self._count -= 1
                if self._release.locked():
                    self._release.release()
                if self._count == 0:
                    self._ident = None
            else:
                raise RecursiveLockException("Not held by caller")

    def locked(self):
        with self._lock:
            return self._ident == _thread.get_ident()

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, type, value, traceback):
        self.release()

class SemaphoreException(Exception):
    pass

class semaphore():
    def __init__(self, maxcount=1, available=None):
        self._lock = _thread.allocate_lock()
        self._changed = _thread.allocate_lock()
        self._changed.acquire()
        self._maxcount = maxcount
        self._available = maxcount if available == None else available

    # Acquire N counts. if wait, then wait for available items;if false,just test
    def acquire(self,  count=1, wait=1):
        ok = False
        with self._lock:
            if wait:
                while self._available < count:
                    self._lock.release()
                    self._changed.acquire()
                    self._lock.acquire()

            if self._available >= count:
                self._available = self._available - count
                ok = True

        return ok

    def release(self, count=1):
        with self._lock:
            new_available = self._available + count
            if new_available > self._maxcount:
                raise SemaphoreException("release")

            self._available = new_available

            if self._changed.locked():
                self._changed.release()
            

### Simple queue class

class QueueException(Exception):
    pass

class queue():
    def __init__(self, maxlen=0):
        self._maxlen = maxlen
        self._lock = _thread.allocate_lock()
        self._fill = _thread.allocate_lock()
        self._fill.acquire()
        self._queue = []

    def __len__(self):
        with self._lock:
            return len(self._queue)

    def append(self, item):
        with self._lock:
            if self._maxlen != 0 and len(self._queue) >= self._maxlen:
                raise QueueException("full")

            self._queue.append(item)
            if self._fill.locked():
                self._fill.release()

    def remove(self, wait=1):
        item = None
        found = False
        self._lock.acquire()

        if wait:
            while len(self._queue) == 0:
                # Wait for something
                self._lock.release()
                self._fill.acquire()
                self._lock.acquire()

        if len(self._queue) != 0:
            item  = self._queue[0]
            del self._queue[0]
            found = True

        self._lock.release()

        if wait and not found:
            raise QueueException("empty")

        return item


# Simple thread class

class thread():
    def __init__(self, name="sx127x", stack=0, ident=None, run=None):
        self._stack = stack
        self._name = name
        self._runninglock = _thread.allocate_lock()
        self._rc = None
        self.running = False
        self._ident = ident
        self._userrun = run

    # Return the name of the thread
    def name(self):
        return self._name

    def ident(self):
        return self._ident

    def __str__(self):
        return "%s:%s" % (self._name, self._ident)

    # Start the thread execution
    def start(self):
        if self._runninglock.acquire(0):
            self.running = True
            if self._stack != None:
                _thread.stack_size(self._stack)
            _thread.start_new_thread(self._run, ())

    # Calls user 'run' method and saves return code
    def _run(self):
        # Capture our ident
        self._ident = _thread.get_ident()
        # Run the user's code
        if self._userrun:
            self._rc = self._userrun(self)
        else:
            self._rc = self.run()
        # Allow 'wait' to finish
        self._runninglock.release()

    # Set flag to stop the thread
    def stop(self):
        self.running = False

    # Wait for thread to terminate if wait is 1 otherwise just test if terminated and return exit code
    def wait(self, wait=1):
        return self._rc if self._runninglock.acquire(wait) else None

