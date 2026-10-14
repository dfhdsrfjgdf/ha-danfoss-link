"""
Minimalus MDG (Trifork) control protokolo klientas per savo TLS12 stacką.

Control:  TLS (mTLS) -> packet=2 framing -> [typeCode][protobuf]
"""
import struct
from .tlslib import TLS12

# control_message_tag
MT_HANDSHAKE = 1
MT_BYE = 2
MT_RECONNECT = 3
MT_PING = 4
MT_PING_REPLY = 5
MT_PLACE_CALL = 10
MT_PLACE_CALL_REPLY = 11
MT_INCOMING_CALL = 12
MT_INCOMING_CALL_REPLY = 13
MT_SET_PEER_WHITELIST = 20
MT_SET_PEER_WHITELIST_REPLY = 21
MT_ALLOCATE_PAIRING_CHANNEL = 30
MT_ALLOCATE_PAIRING_CHANNEL_REPLY = 31
MT_PLACE_PAIRING_CALL = 32
MT_PLACE_PAIRING_CALL_REPLY = 33

MAGIC = 0xf09d8ca8

# ------------------------------------------------------------------ protobuf


def _varint(n):
    out = b""
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out += bytes([b | 0x80])
        else:
            out += bytes([b])
            return out


def f_varint(field, value):
    return _varint((field << 3) | 0) + _varint(value)


def f_fixed32(field, value):
    return _varint((field << 3) | 5) + struct.pack("<I", value)


def f_bytes(field, value):
    if isinstance(value, str):
        value = value.encode()
    return _varint((field << 3) | 2) + _varint(len(value)) + value


def parse(data):
    """Grąžina {field_number: [ (wire_type, value), ... ]}"""
    out = {}
    i = 0
    n = len(data)
    while i < n:
        key, i = _read_varint(data, i)
        field, wt = key >> 3, key & 7
        if wt == 0:
            v, i = _read_varint(data, i)
        elif wt == 1:
            v = data[i:i + 8]; i += 8
        elif wt == 2:
            ln, i = _read_varint(data, i)
            v = data[i:i + ln]; i += ln
        elif wt == 5:
            v = struct.unpack("<I", data[i:i + 4])[0]; i += 4
        else:
            raise ValueError("wire type %d" % wt)
        out.setdefault(field, []).append((wt, v))
    return out


def _read_varint(data, i):
    shift = 0
    result = 0
    while True:
        b = data[i]; i += 1
        result |= (b & 0x7F) << shift
        if not (b & 0x80):
            return result, i
        shift += 7


def field_str(fields, num):
    v = fields.get(num)
    if not v:
        return None
    return v[-1][1].decode("utf-8", "replace")


def field_int(fields, num):
    v = fields.get(num)
    if not v:
        return None
    return v[-1][1]


# ------------------------------------------------------------------ control


class ControlClient:
    def __init__(self, host, port, cert_der, key_d, curve, sni=b""):
        self.tls = TLS12(host, port, cert_der, key_d, curve, sni=sni)
        self.rbuf = b""

    def connect(self):
        self.tls.handshake()
        hs = f_fixed32(1, MAGIC) + f_varint(2, 1) + f_varint(3, 0)
        self._send(MT_HANDSHAKE, hs)
        return self.recv_msg(timeout=15)

    def _send(self, type_code, payload):
        frame = struct.pack(">H", len(payload) + 1) + bytes([type_code]) + payload
        self.tls.send_app(frame)

    def recv_msg(self, timeout=15):
        while True:
            while len(self.rbuf) < 2:
                self.rbuf += self.tls.recv_app()
            ln = struct.unpack(">H", self.rbuf[:2])[0]
            while len(self.rbuf) < 2 + ln:
                self.rbuf += self.tls.recv_app()
            payload = self.rbuf[2:2 + ln]
            self.rbuf = self.rbuf[2 + ln:]
            return payload[0], payload[1:]

    # --- žinutės ---
    def set_whitelist(self, peer_ids, req_id=1):
        p = f_varint(1, req_id)
        for pid in peer_ids:
            p += f_bytes(2, pid)
        self._send(MT_SET_PEER_WHITELIST, p)
        return req_id

    def place_call(self, peer_name, protocol, ticket="", req_id=2):
        p = f_varint(1, req_id) + f_bytes(2, peer_name) + f_bytes(3, protocol)
        if ticket:
            p += f_bytes(4, ticket)
        self._send(MT_PLACE_CALL, p)
        return req_id

    def ping(self, req_id=99):
        self._send(MT_PING, f_varint(1, req_id))
        return req_id

    def close(self):
        self.tls.close()
