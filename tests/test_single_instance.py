"""Single-instance lock helpers."""

from __future__ import annotations

import unittest

import idle_lab.single_instance as si


class SingleInstanceTests(unittest.TestCase):
    def tearDown(self) -> None:
        try:
            si.release()
        except Exception:
            pass

    def test_acquire_then_other_handle_sees_existing(self) -> None:
        self.assertTrue(si.try_acquire())
        # Same as a second process: CreateMutex on an existing name.
        si.kernel32.SetLastError(0)
        handle = si.kernel32.CreateMutexW(None, False, si.MUTEX_NAME)
        self.assertTrue(handle)
        self.assertEqual(si.ctypes.get_last_error(), si.ERROR_ALREADY_EXISTS)
        si.kernel32.CloseHandle(handle)
        # Owner still holds the lock.
        self.assertTrue(si.try_acquire())


if __name__ == "__main__":
    unittest.main()
