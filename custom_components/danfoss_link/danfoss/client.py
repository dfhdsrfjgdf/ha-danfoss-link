"""
Aukšto lygio Danfoss Link MDG klientas.

Naudojimas:
    with DanfossMDG(cert_path, key_path, cc_peer_id) as cc:
        data = cc.get("/api/rooms")
        cc.post("/api/settings/temperature", {"temperature": 21.0, ...})
"""
import base64, json, re, socket, struct, os
from ecdsa import curves
from asn1crypto import keys as a_keys, x509 as a_x509

from .tlslib import TLS12
from .mdg import (ControlClient, MT_PLACE_CALL_REPLY, MT_SET_PEER_WHITELIST_REPLY,
                  parse, field_int, field_str)

HOSTS = ["77.66.11.90", "77.66.11.92", "5.179.92.180", "5.179.92.182"]
PORT = 443
CONTROL_SNI = b"mdg-danfoss.hosted.trifork.com"
ROUTING_MAGIC = 0xf09d8c95


def pem_to_der(pem):
    if "-----BEGIN" in pem:
        data = pem
    else:
        with open(pem) as f:
            data = f.read()
    b64 = "".join(re.findall(r"-----BEGIN [^-]+-----(.*?)-----END [^-]+-----", data, re.S))
    return base64.b64decode(b64)


def _varint(n):
    out = b""
    while True:
        b = n & 0x7F; n >>= 7
        out += bytes([b | 0x80]) if n else bytes([b])
        if not n: return out


def _pbf(field, v):
    return _varint((field << 3) | 5) + struct.pack("<I", v)


def _pbv(field, v):
    return _varint((field << 3) | 0) + _varint(v)


def _pbb(field, v):
    if isinstance(v, str): v = v.encode()
    return _varint((field << 3) | 2) + _varint(len(v)) + v


class DanfossMDG:
    def __init__(self, cert_path, key_path, cc_peer_id, host=None):
        self.cert_der = pem_to_der(cert_path)
        key_der = pem_to_der(key_path)
        self.key_d = a_keys.PrivateKeyInfo.load(key_der)["private_key"].parsed["private_key"].native
        self.curve = curves.BRAINPOOLP320r1
        self.cc_peer_id = cc_peer_id
        self.host = host
        self.control = None
        self.routing = None
        self.tls = None
        self._req_id = 1

    # ---------- lifecycle ----------
    def connect(self):
        hosts = [self.host] if self.host else HOSTS
        last = None
        for h in hosts:
            try:
                self._connect_control(h)
                return self
            except Exception as e:
                last = e
                self.close()
        raise last

    def _connect_control(self, host):
        c = ControlClient(host, PORT, self.cert_der, self.key_d, self.curve, sni=CONTROL_SNI)
        try:
            c.connect()
            c.set_whitelist([self.cc_peer_id], req_id=self._new_id())
            while True:
                tc, pl = c.recv_msg(timeout=15)
                if tc == MT_SET_PEER_WHITELIST_REPLY:
                    break
        except Exception:
            try:
                c.close()
            except Exception:
                pass
            raise
        self.control = c
        self.host = host

    def _new_id(self):
        self._req_id += 1
        return self._req_id

    def close(self):
        for s in (self.tls, self.routing, self.control):
            try:
                if s is not None:
                    s.close()
            except Exception:
                pass
        self.tls = self.routing = self.control = None

    def __enter__(self):
        return self.connect()

    def __exit__(self, *a):
        self.close()

    # ---------- routing + TLS ----------
    def _open_channel(self):
        # uždaryti seną
        if self.tls is not None:
            try: self.tls.close()
            except Exception: pass
            self.tls = None
        self.control.place_call(self.cc_peer_id, "cc_json", ticket="", req_id=self._new_id())
        host = port = token = None
        while True:
            tc, pl = self.control.recv_msg(timeout=30)
            if tc == MT_PLACE_CALL_REPLY:
                f = parse(pl)
                if field_int(f, 2) != 0:
                    raise RuntimeError("place_call nepavyko: %s" % field_str(f, 4))
                rf = parse(f[3][-1][1])
                ep = parse(rf[4][-1][1])
                host = ep[1][-1][1].decode()
                port = field_int(ep, 2)
                token = rf[5][-1][1]
                break
        rs = socket.create_connection((host, port), timeout=20)
        hs = _pbf(1, ROUTING_MAGIC) + _pbv(2, 1) + _pbv(3, 0)
        hs += _pbb(4, token) + _pbb(5, "tlsv1_2")
        rs.sendall(struct.pack(">H", len(hs) + 1) + b"\x00" + hs)

        def recv_frame():
            buf = b""
            while len(buf) < 2:
                d = rs.recv(2 - len(buf))
                if not d: raise EOFError()
                buf += d
            ln = struct.unpack(">H", buf)[0]
            body = b""
            while len(body) < ln:
                d = rs.recv(ln - len(body))
                if not d: raise EOFError()
                body += d
            return body

        while True:
            fr = recv_frame()
            if fr[0] == 2:
                break
            if fr[0] == 3:
                raise RuntimeError("ROUTINGERROR %s" % field_int(parse(fr[1:]), 1))
            # 1 = PLEASEHOLD -> toliau

        tls = TLS12(host, port, self.cert_der, self.key_d, self.curve, sni=b"")
        tls.app_profile = True
        tls.handshake(sock=rs)
        self.routing = rs
        self.tls = tls

    # ---------- cc_json ----------
    def request(self, uri, method="GET", content=None, port=8000, headers=None, retries=1):
        for attempt in range(retries + 1):
            if self.tls is None:
                self._open_channel()
            try:
                return self._request_once(uri, method, content, port, headers)
            except (EOFError, OSError, RuntimeError):
                self.tls = None
                if attempt == retries:
                    raise
        raise RuntimeError("unreachable")

    def _request_once(self, uri, method, content, port, headers):
        req = {"id": self._new_id(), "data": {"type": "JsonWebRequest",
                "data": {"uri": uri, "method": method,
                        "headers": headers or ["Accept: application/json; charset=utf-8"],
                        "port": port}}}
        if content is not None:
            req["data"]["data"]["content"] = content
        body = json.dumps(req).encode()
        self.tls.send_app(struct.pack(">H", len(body)) + body)
        data = b""
        while len(data) < 2:
            data += self.tls.recv_app()
        ln = struct.unpack(">H", data[:2])[0]
        while len(data) < 2 + ln:
            data += self.tls.recv_app()
        resp = json.loads(data[2:2 + ln])
        inner = resp["data"]["data"]
        return {"status": inner.get("status"), "content": inner.get("content"),
                "cc_time": resp.get("cc_time")}

    # ---------- patogios nuorodos ----------
    def get(self, uri, **kw):
        return self.request(uri, "GET", **kw)

    def post(self, uri, content, **kw):
        return self.request(uri, "POST", content=content, **kw)

    def put(self, uri, content, **kw):
        return self.request(uri, "PUT", content=content, **kw)

    def patch(self, uri, content, **kw):
        return self.request(uri, "PATCH", content=content, **kw)
