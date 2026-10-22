"""A service that answers only streamed (#23): a reply that comes as server-sent events is joined into one, a service
that refuses a request not streamed is asked again with "stream": true, and every other endpoint gets the request it
got before. A local server stands in for the services; no network.

Run from the repo root:
    python -m unittest discover tests
"""
import io
import json
import threading
import unittest
import urllib.error
from email.message import Message
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock

from textfold import llm_openai

REPLY = {"takeaway": "流式的回复也能读", "topic": "流式"}


def content(d):
    """The reply's text from the joined completion (llm_openai._content arrives with the reply-shapes change)."""
    return ((d.get("choices") or [{}])[0].get("message") or {}).get("content")


def sse(text, usage=None):
    """text sent as a stream: a role chunk, the text in three pieces, an empty one, [DONE]."""
    n = len(text) // 3
    pieces = [text[:n], text[n:2 * n], text[2 * n:]]
    chunks = [{"choices": [{"index": 0, "delta": {"role": "assistant"}}]}]
    chunks += [{"choices": [{"index": 0, "delta": {"content": p}}]} for p in pieces]
    chunks.append({"choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}], **({"usage": usage} if usage else {})})
    return "".join(f"data: {json.dumps(c, ensure_ascii=False)}\n\n" for c in chunks) + "data: [DONE]\n\n"


class Service(BaseHTTPRequestHandler):
    """/plain answers as most endpoints do; /only takes a stream alone and says so; /mute takes a stream alone and
    says nothing of it; /always streams whatever it is asked; /naked streams with a JSON content type; /nakedbom
    streams with a byte-order mark and a JSON content type; /picky and /picky200 refuse JSON mode with the stream (as
    an HTTP error and as a 200 error body); /busy refuses the first request with a truncated body; /stubborn refuses
    JSON mode with a truncated body and answers the next shape."""
    seen = []

    def log_message(self, *a):
        pass

    def send(self, code, body, kind="application/json"):
        data = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        Service.seen.append((self.path, body))
        text = json.dumps(REPLY, ensure_ascii=False)
        if self.path.startswith("/plain"):
            return self.send(200, json.dumps({"choices": [{"message": {"content": text}}]}, ensure_ascii=False))
        if self.path.startswith("/always"):
            return self.send(200, sse(text), "text/event-stream; charset=utf-8")
        if self.path.startswith("/nakedbom"):
            return self.send(200, chr(0xFEFF) + sse(text), "application/json")   # (a marked stream, no content type)
        if self.path.startswith("/naked"):
            return self.send(200, sse(text), "application/json")   # (a stream without its own content type)
        if self.path.startswith("/stubborn"):
            if body.get("response_format"):
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", "100")   # (truncated: the refusal is read for its first bytes)
                self.end_headers()
                self.wfile.write(b'{"error": {"message": "no JSON mode')
                return
            return self.send(200, json.dumps({"choices": [{"message": {"content": text}}]}, ensure_ascii=False))
        if self.path.startswith("/busy"):
            if len([p for p, _ in Service.seen if p.startswith("/busy")]) == 1:
                self.send_response(503)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", "100")   # (truncated on purpose: the client must not wait for it)
                self.send_header("Retry-After", "0")
                self.end_headers()
                self.wfile.write(b'{"error":')
                return
            return self.send(200, json.dumps({"choices": [{"message": {"content": text}}]}, ensure_ascii=False))
        if self.path.startswith("/picky"):
            if not body.get("stream"):
                return self.send(400, json.dumps({"error": {"message": "only stream=true is supported"}}))
            if body.get("response_format"):
                if self.path.startswith("/picky200"):
                    return self.send(200, json.dumps({"error": "response_format not supported"}))
                return self.send(400, json.dumps({"error": {"message": "response_format is not supported"}}))
            return self.send(200, sse(text, {"total_tokens": 12}), "text/event-stream")
        if not body.get("stream"):
            said = {"error": {"message": "only stream=true is supported"}} if self.path.startswith("/only") else {"error": "bad request"}
            return self.send(400, json.dumps(said))
        return self.send(200, sse(text, {"total_tokens": 12}), "text/event-stream")


class Streamed(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Service)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        Service.seen.clear()
        llm_openai._WORKED.clear()

    def ask(self, path):
        spec = {"base": f"{self.base}/{path}", "model": "m", "api_key": "k", "provider": path}
        return llm_openai.call("Fold this.", {"type": "object"}, spec, "system", 10)

    def test_an_endpoint_that_answers_whole_is_asked_as_before(self):
        self.assertEqual(self.ask("plain"), (REPLY, None))
        self.assertEqual(len(Service.seen), 1)
        self.assertNotIn("stream", Service.seen[0][1])
        self.assertEqual(Service.seen[0][1]["response_format"], {"type": "json_object"})

    def test_a_service_that_says_it_takes_a_stream_alone(self):
        self.assertEqual(self.ask("only"), (REPLY, None))
        self.assertEqual([b.get("stream") for _, b in Service.seen], [None, True])   # straight to the stream
        self.ask("only")   # the way that worked is remembered
        self.assertEqual([b.get("stream") for _, b in Service.seen], [None, True, True])

    def test_a_service_that_takes_a_stream_alone_without_saying_so(self):
        self.assertEqual(self.ask("mute"), (REPLY, None))
        self.assertEqual([b.get("stream") for _, b in Service.seen], [None, None, True])

    def test_a_reply_streamed_unasked(self):
        self.assertEqual(self.ask("always"), (REPLY, None))
        self.assertEqual(len(Service.seen), 1)
        self.assertNotIn("stream", Service.seen[0][1])

    def test_the_stream_without_json_mode_is_tried_next(self):
        self.assertEqual(self.ask("picky"), (REPLY, None))
        self.assertEqual([(b.get("stream"), bool(b.get("response_format"))) for _, b in Service.seen],
                         [(None, True), (True, True), (True, False)])

    def test_a_200_error_body_moves_to_the_next_shape(self):
        self.assertEqual(self.ask("picky200"), (REPLY, None))
        self.assertEqual([(b.get("stream"), bool(b.get("response_format"))) for _, b in Service.seen],
                         [(None, True), (True, True), (True, False)])

    def test_a_busy_service_with_a_truncated_body_is_asked_again(self):
        self.assertEqual(self.ask("busy"), (REPLY, None))
        self.assertEqual(len(Service.seen), 2)   # (a truncated body did not stop the retry)

    def test_a_refusal_with_a_truncated_body_moves_on(self):
        self.assertEqual(self.ask("stubborn"), (REPLY, None))
        self.assertEqual(len(Service.seen), 2)   # (a truncated refusal did not stop the walk)

    def test_a_stream_sent_without_its_content_type_is_read(self):
        self.assertEqual(self.ask("naked"), (REPLY, None))
        self.assertEqual(len(Service.seen), 1)

    def test_a_marked_stream_sent_without_its_content_type_is_read(self):
        self.assertEqual(self.ask("nakedbom"), (REPLY, None))
        self.assertEqual(len(Service.seen), 1)


class Retry(unittest.TestCase):
    def test_a_busy_body_is_not_read_before_the_retry(self):
        class Unread(io.BytesIO):
            def read(self, *a):
                raise AssertionError("a busy error's body must not be read: a stalled one would hold the retry")

        headers = Message()
        headers["Retry-After"] = "0"
        busy = urllib.error.HTTPError("http://x", 503, "busy", headers, Unread(b'{"error":'))
        reply = {"choices": [{"message": {"content": json.dumps(REPLY)}}]}
        spec = {"base": "http://x", "model": "m", "api_key": "k", "provider": "p"}
        with mock.patch.object(llm_openai, "_post", side_effect=[busy, reply]):
            self.assertEqual(llm_openai.call("Fold this.", {"type": "object"}, spec, "system", 10), (REPLY, None))
        self.assertTrue(busy.fp.closed)   # (closed unread, not left to the garbage collector)

    def test_a_failure_body_already_closed_reads_as_empty(self):
        headers = Message()
        e = urllib.error.HTTPError("http://x", 400, "bad", headers, io.BytesIO(b'{"error": "x"}'))
        self.assertEqual(llm_openai._said(e), '{"error": "x"}')
        self.assertTrue(e.fp.closed)   # (closed after the read)
        self.assertEqual(llm_openai._said(e), "")   # (a second read must not raise)


class Events(unittest.TestCase):
    def test_the_pieces_joined(self):
        d = llm_openai._events(sse('{"a": "第一 行"}', {"total_tokens": 3}).encode())
        self.assertEqual(content(d), '{"a": "第一 行"}')
        self.assertEqual(d["usage"], {"total_tokens": 3})

    def test_parts_comments_and_other_choices(self):
        raw = (": keep-alive\n\n"
               'data: {"choices": [{"index": 0, "delta": {"content": [{"type": "text", "text": "{\\"a\\""}]}}]}\n\n'
               'data: {"choices": [{"index": 1, "delta": {"content": "other"}}]}\n\n'
               'data: {"choices": [{"index": 0, "delta": {"content": ": 1}"}}]}\n\n'
               "data: [DONE]\n\n")
        self.assertEqual(content(llm_openai._events(raw.encode())), '{"a": 1}')

    def test_an_error_in_the_stream(self):
        d = llm_openai._events(b'data: {"error": {"message": "quota exceeded"}}\n\n')
        self.assertFalse(content(d))
        self.assertEqual(d["error"]["message"], "quota exceeded")

    def test_a_message_chunk_and_a_non_string_part(self):
        raw = ('data: {"choices": [{"index": 0, "message": {"content": "{\\"a\\": "}}]}\r\n\r\n'
               'data: {"choices": [{"index": 0, "delta": {"content": [{"type": "text", "text": 1}, {"type": "text", "text": "}"}]}}]}\r\n\r\n')
        self.assertEqual(content(llm_openai._events(raw.encode())), '{"a": 1}')

    def test_a_stream_that_opens_with_a_byte_order_mark(self):
        # the first chunk carries content: a BOM left on it would hide that piece, not just a role marker
        raw = ('data: {"choices": [{"index": 0, "delta": {"content": "{\\"a\\": \\"第一 行\\"}"}}]}\n\n'
               "data: [DONE]\n\n").encode()
        d = llm_openai._events(b"\xef\xbb\xbf" + raw)
        self.assertEqual(content(d), '{"a": "第一 行"}')


if __name__ == "__main__":
    unittest.main()
