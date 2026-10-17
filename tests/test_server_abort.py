"""A browser that aborts a request (a reload, a tab closed) is the reader having left, not a server error: Handler.send
swallows every ConnectionError — Windows raises ConnectionAbortedError (WinError 10053) while the headers are being
written, as this machine's log showed — so one aborted page load does not print two tracebacks.

Run from the repo root:
    python -m unittest discover tests
"""
import unittest

from textfold import server


class WFile:
    def __init__(self, fail):
        self.fail = fail

    def write(self, data):
        if self.fail == "write":
            raise ConnectionAbortedError(10053, "你的主机中的软件中止了一个已建立的连接。")


class Stub:
    """What Handler.send touches: a handler whose socket the client closed at one point or another."""

    def __init__(self, fail):
        self.fail, self.wfile = fail, WFile(fail)

    def send_response(self, code):
        pass

    def send_header(self, k, v):
        pass

    def end_headers(self):
        if self.fail == "headers":
            raise ConnectionAbortedError(10053, "你的主机中的软件中止了一个已建立的连接。")


class Aborted(unittest.TestCase):
    def send(self, fail):
        server.make_handler(None).send(Stub(fail), 200, "hi")   # (jobs is not touched by send)

    def test_a_body_the_browser_aborted_is_not_a_traceback(self):
        self.send("write")

    def test_headers_the_browser_aborted_are_not_a_traceback(self):
        self.send("headers")


if __name__ == "__main__":
    unittest.main()
