"""
Minimal TLS 1.2 ECDHE-ECDSA client with brainpoolP320r1 certificate signatures.

Standartiniai TLS stack'ai (OpenSSL) nepalaiko brainpoolP320r1, todėl serverio
(Trifork MDG) sertifikato parašo patikrinti negali. ECDHE grupė = secp256r1
(standartinė), o brainpoolP320r1 naudojamas TIK sertifikatų parašams -- tai
padengiama grynos Python `ecdsa` biblioteka.
"""
import os, struct, socket, hmac, hashlib
from ecdsa import curves, SigningKey, VerifyingKey, ellipticcurve, util
from ecdsa.util import sigencode_der, sigdecode_der
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

CT_CHANGE_CIPHER_SPEC = 20
CT_ALERT = 21
CT_HANDSHAKE = 22
CT_APPLICATION_DATA = 23

HS_CLIENT_HELLO = 1
HS_SERVER_HELLO = 2
HS_CERTIFICATE = 11
HS_SERVER_KEY_EXCHANGE = 12
HS_CERTIFICATE_REQUEST = 13
HS_SERVER_HELLO_DONE = 14
HS_CERTIFICATE_VERIFY = 15
HS_CLIENT_KEY_EXCHANGE = 16
HS_FINISHED = 20

CIPHER_AES128_GCM_SHA256 = 0xC02B
CIPHER_AES256_GCM_SHA384 = 0xC02C


def u8(v): return bytes([v])
def u16(v): return struct.pack(">H", v)
def u24(v): return struct.pack(">I", v)[1:]
def p8(b): return u8(len(b)) + b
def p16(b): return u16(len(b)) + b
def p24(b): return u24(len(b)) + b


def prf(secret, label, seed, length, hash_name):
    """TLS 1.2 PRF (P_hash)."""
    hf = getattr(hashlib, hash_name)
    label_seed = label + seed

    def p_hash(secret, seed, length):
        out = b""
        a = seed
        while len(out) < length:
            a = hmac.new(secret, a, hf).digest()
            out += hmac.new(secret, a + seed, hf).digest()
        return out[:length]

    return p_hash(secret, label_seed, length)


class TLS12:
    def __init__(self, host, port, client_cert_der, client_key_d, client_curve,
                 sni=b"", verify_server_sig=True):
        self.host = host
        self.port = port
        self.client_cert_der = client_cert_der
        self.sk = SigningKey.from_secret_exponent(client_key_d, curve=client_curve)
        self.client_curve = client_curve
        self.sni = sni
        self.verify_server_sig = verify_server_sig
        self.sock = None
        self.rbuf = b""
        self.transcript = b""
        self.cipher = None
        self.hash_name = None
        self.master_secret = None
        self.client_key = self.server_key = None
        self.client_iv = self.server_iv = None
        self.client_seq = self.server_seq = 0
        self.server_certs = []

    # ---------------- I/O ----------------
    def _recv(self, n):
        while len(self.rbuf) < n:
            d = self.sock.recv(16384)
            if not d:
                raise EOFError("ryšys uždarytas")
            self.rbuf += d
        out, self.rbuf = self.rbuf[:n], self.rbuf[n:]
        return out

    def _read_record(self):
        hdr = self._recv(5)
        ct = hdr[0]
        ver = hdr[1:3]
        ln = struct.unpack(">H", hdr[3:5])[0]
        frag = self._recv(ln)
        return ct, ver, frag

    def _read_plain_record(self):
        ct, ver, frag = self._read_record()
        return ct, frag

    def _send_record(self, ct, frag, ver=0x0303):
        self.sock.sendall(u8(ct) + u16(ver) + p16(frag))

    def _read_handshake(self):
        """Perskaito vieną handshake pranešimą (gali kirsti kelis įrašus).

        Likę kito pranešimo baitai laikomi atskirame hs_buf, kad nesugadintų
        record-lyer'io buferio (LibreSSL deda kelis pranešimus į vieną įrašą).
        """
        buf = getattr(self, "hs_buf", b"")
        self.hs_buf = b""
        while len(buf) < 4:
            ct, frag = self._read_plain_record()
            if ct == CT_ALERT:
                raise RuntimeError("TLS ALERT (handshake): %s" % frag.hex())
            assert ct == CT_HANDSHAKE, "laukta handshake, gauta %d" % ct
            buf += frag
        t = buf[0]
        ln = int.from_bytes(buf[1:4], "big")
        while len(buf) < 4 + ln:
            ct, frag = self._read_plain_record()
            assert ct == CT_HANDSHAKE
            buf += frag
        body = buf[4:4 + ln]
        self.transcript += buf[:4 + ln]
        self.hs_buf = buf[4 + ln:]
        return t, body

    # ---------------- handshake ----------------
    def _build_client_hello(self, client_random):
        if getattr(self, "app_profile", False):
            return self._build_client_hello_app(client_random)
        ciphers = [CIPHER_AES256_GCM_SHA384, CIPHER_AES128_GCM_SHA256]
        groups = [0x0017]  # secp256r1
        sigalgs = [0x0403, 0x0503, 0x0603, 0x0401, 0x0501, 0x0601]
        exts = b""
        exts += u16(0x000d) + p16(p16(b"".join(u16(s) for s in sigalgs)))  # signature_algorithms
        exts += u16(0x000a) + p16(p16(b"".join(u16(g) for g in groups)))   # supported_groups
        exts += u16(0x000b) + p16(p8(b"\x00"))                              # ec_point_formats
        exts += u16(0xff01) + p16(b"\x00")                                  # renegotiation_info (empty)
        exts += u16(0x0017) + p16(b"")                                      # extended_master_secret
        if self.sni:
            sn = u8(0) + p16(self.sni)
            exts += u16(0x0000) + p16(p16(sn))
        exts += u16(0x0032) + p16(p16(b"".join(u16(s) for s in sigalgs)))   # signature_algorithms_cert
        body = (u16(0x0303) + client_random + p8(b"") +
                p16(b"".join(u16(c) for c in ciphers)) + p8(b"\x00") + p16(exts))
        return raw_hs(HS_CLIENT_HELLO, body), client_random

    def _build_client_hello_app(self, client_random):
        """Atkartoja Danfoss app/LibreSSL ClientHello (routing TLS)."""
        ciphers = [0xC030, 0xC02C, 0xC028, 0xC024, 0xC014, 0xC00A, 0x00A5, 0x00A3,
                   0x00A1, 0x009F, 0x006B, 0x006A, 0x0069, 0x0068, 0x0039, 0x0038,
                   0x0037, 0x0036, 0xC032, 0xC02E, 0xC02A, 0xC026, 0xC00F, 0xC005,
                   0x009D, 0x003D, 0x0035, 0xC02F, 0xC02B, 0xC027, 0xC023, 0xC013,
                   0xC009, 0x00A4, 0x00A2, 0x00A0, 0x009E, 0x0067, 0x0040, 0x003F,
                   0x003E, 0x0033, 0x0032, 0x0031, 0x0030, 0xC031, 0xC02D, 0xC029,
                   0xC025, 0xC00E, 0xC004, 0x009C, 0x003C, 0x002F, 0x0007, 0xC012,
                   0xC008, 0x0016, 0x0013, 0x0010, 0x000D, 0xC00D, 0xC003, 0x000A, 0x00FF]
        groups = [0x0017, 0x001D, 0x0019, 0x001C, 0x001B, 0x0018, 0x001A,
                  0x0016, 0x000E, 0x000D, 0x000B, 0x000C, 0x0009, 0x000A]
        sigalgs = [0x0601, 0x0602, 0x0603, 0x0501, 0x0502, 0x0503, 0x0401, 0x0402,
                   0x0403, 0x0301, 0x0302, 0x0303, 0x0201, 0x0202, 0x0203]
        exts = b""
        exts += u16(0x000b) + p16(p8(b"\x03\x00\x01\x02"))                  # ec_point_formats
        exts += u16(0x000a) + p16(p16(b"".join(u16(g) for g in groups)))    # supported_groups
        exts += u16(0x000d) + p16(p16(b"".join(u16(s) for s in sigalgs)))   # signature_algorithms
        exts += u16(0x000f) + p16(b"\x01")                                  # heartbeat
        exts += u16(0x0015) + p16(b"\x00" * 250)                            # padding
        body = (u16(0x0303) + client_random + p8(b"") +
                p16(b"".join(u16(c) for c in ciphers)) + p8(b"\x00") + p16(exts))
        return raw_hs(HS_CLIENT_HELLO, body), client_random

    def handshake(self, sock=None):
        if sock is not None:
            self.sock = sock
        elif self.sock is None:
            self.sock = socket.create_connection((self.host, self.port), timeout=20)
        client_random = os.urandom(32)
        ch, _ = self._build_client_hello(client_random)
        if os.environ.get("TLS_DEBUG"):
            print("[debug] ClientHello (%d B): %s" % (len(ch), ch.hex()))
        self.transcript += ch
        self._send_record(CT_HANDSHAKE, ch,
                          0x0301 if getattr(self, "app_profile", False) else 0x0303)

        server_random = None
        ske = None
        cert_req = None
        while True:
            t, body = self._read_handshake()
            if t == HS_SERVER_HELLO:
                server_random = body[2:34]
                sidlen = body[34]
                j = 35 + sidlen
                self.cipher = struct.unpack(">H", body[j:j + 2])[0]
                if self.cipher == CIPHER_AES256_GCM_SHA384:
                    self.hash_name = "sha384"
                elif self.cipher == CIPHER_AES128_GCM_SHA256:
                    self.hash_name = "sha256"
                else:
                    raise RuntimeError("nepalaikomas cipher 0x%04X" % self.cipher)
                k = j + 3  # po cipher + compression
                self.ems = False
                if k + 2 <= len(body):
                    elen = struct.unpack(">H", body[k:k + 2])[0]
                    p = k + 2
                    end = k + 2 + elen
                    while p + 4 <= end:
                        et = struct.unpack(">H", body[p:p + 2])[0]
                        ln = struct.unpack(">H", body[p + 2:p + 4])[0]
                        if os.environ.get("TLS_DEBUG"):
                            print("[debug] SH ext 0x%04X len=%d" % (et, ln))
                        if et == 0x0017:
                            self.ems = True
                        p += 4 + ln
            elif t == HS_CERTIFICATE:
                clen = int.from_bytes(body[0:3], "big")
                j = 3
                while j < 3 + clen:
                    l = int.from_bytes(body[j:j + 3], "big")
                    j += 3
                    self.server_certs.append(body[j:j + l])
                    j += l
            elif t == HS_CERTIFICATE_REQUEST:
                cert_req = body
            elif t == HS_SERVER_KEY_EXCHANGE:
                ske = body
            elif t == HS_SERVER_HELLO_DONE:
                break
            else:
                pass

        assert self.cipher and server_random and ske, "nepilnas serverio atsakymas"

        # 1) patikrinti serverio SKE parašą (brainpoolP320r1)
        self._verify_ske(client_random, server_random, ske)

        # 2) ECDHE
        ct_type = ske[0]
        assert ct_type == 3, "SKE: tik named_curve"
        named = struct.unpack(">H", ske[1:3])[0]
        assert named == 0x0017
        publen = ske[3]
        server_point_bytes = ske[4:4 + publen]
        from ecdsa import NIST256p
        x = int.from_bytes(server_point_bytes[1:33], "big")
        y = int.from_bytes(server_point_bytes[33:65], "big")
        server_point = ellipticcurve.Point(NIST256p.curve, x, y, NIST256p.order)

        eph = SigningKey.generate(curve=NIST256p)
        our_point = eph.verifying_key.pubkey.point
        shared = server_point * eph.privkey.secret_multiplier
        pms = int(shared.x()).to_bytes(32, "big")

        # 4) kliento flight 1: Certificate + ClientKeyExchange
        flight = b""
        if cert_req is not None:
            cert_msg = p24(p24(self.client_cert_der))
            flight += raw_hs(HS_CERTIFICATE, cert_msg)
        our_point_bytes = b"\x04" + int(our_point.x()).to_bytes(32, "big") + int(our_point.y()).to_bytes(32, "big")
        cke = p8(our_point_bytes)
        flight += raw_hs(HS_CLIENT_KEY_EXCHANGE, cke)

        # 3) raktai (EMS jei serveris palaiko)
        if getattr(self, "ems", False):
            sess_hash = getattr(hashlib, self.hash_name)(self.transcript + flight).digest()
            self.master_secret = prf(pms, b"extended master secret", sess_hash, 48, self.hash_name)
        else:
            self.master_secret = prf(pms, b"master secret",
                                     client_random + server_random, 48, self.hash_name)
        n = 32 if self.cipher == CIPHER_AES256_GCM_SHA384 else 16
        kb = prf(self.master_secret, b"key expansion",
                 server_random + client_random, 2 * (n + 4), self.hash_name)
        self.client_key = kb[0:n]
        self.server_key = kb[n:2 * n]
        self.client_iv = kb[2 * n:2 * n + 4]
        self.server_iv = kb[2 * n + 4:2 * n + 8]

        # CertificateVerify (tik jei serveris prašė kliento sertifikato)
        if cert_req is not None:
            transcript_so_far = self.transcript + flight
            digest = hashlib.sha256(transcript_so_far).digest()
            sig = self.sk.sign_digest(digest, sigencode=sigencode_der)
            cv = u16(0x0403) + p16(sig)
            flight += raw_hs(HS_CERTIFICATE_VERIFY, cv)

        self.transcript += flight
        self._send_record(CT_HANDSHAKE, flight)

        # 5) ChangeCipherSpec + Finished (šifruotas)
        self._send_record(CT_CHANGE_CIPHER_SPEC, b"\x01")
        self.client_seq = 0
        verify_data = prf(self.master_secret, b"client finished",
                          getattr(hashlib, self.hash_name)(self.transcript).digest(), 12, self.hash_name)
        fin = raw_hs(HS_FINISHED, verify_data)
        self._send_encrypted(CT_HANDSHAKE, fin)
        self.transcript += fin

        # 6) serverio CCS + Finished
        while True:
            ct, frag = self._read_plain_record()
            if ct == CT_CHANGE_CIPHER_SPEC:
                self.server_seq = 0
                break
            if ct == CT_ALERT:
                raise RuntimeError("ALERT prieš CCS: %s" % frag.hex())
        if os.environ.get("TLS_DEBUG"):
            print("[debug] cipher=0x%04X ems=%s" % (self.cipher, getattr(self, "ems", None)))
            print("[debug] server_key=", self.server_key.hex())
            print("[debug] server_iv =", self.server_iv.hex())
        sct, sfin = self._read_encrypted()
        if os.environ.get("TLS_DEBUG"):
            print("[debug] server enc record ct=%d len=%d" % (sct, len(sfin)))
        assert sct == CT_HANDSHAKE and sfin[0] == HS_FINISHED
        expect = prf(self.master_secret, b"server finished",
                     getattr(hashlib, self.hash_name)(self.transcript).digest(), 12, self.hash_name)
        got = sfin[4:4 + 12]
        assert hmac.compare_digest(expect, got), "server Finished NESUTAMPA"
        return True

    def _verify_ske(self, client_random, server_random, ske):
        if not self.verify_server_sig:
            return
        from asn1crypto import x509
        from ecdsa import NIST256p, NIST384p, NIST521p
        cert = x509.Certificate.load(self.server_certs[0])
        pb = cert.public_key["public_key"].native
        coord = (len(pb) - 1) // 2
        x = int.from_bytes(pb[1:1 + coord], "big")
        y = int.from_bytes(pb[1 + coord:1 + 2 * coord], "big")
        if coord == 40:
            C = curves.BRAINPOOLP320r1
        elif coord == 32:
            C = NIST256p
        elif coord == 48:
            C = NIST384p
        else:
            C = NIST521p
        pt = ellipticcurve.Point(C.curve, x, y, C.order)
        vk = VerifyingKey.from_public_point(pt, curve=C)
        publen = ske[3]
        params = ske[0:4 + publen]
        sig_alg = struct.unpack(">H", ske[4 + publen:6 + publen])[0]
        siglen = struct.unpack(">H", ske[6 + publen:8 + publen])[0]
        sig = ske[8 + publen:8 + publen + siglen]
        hash_name = {2: "sha1", 3: "sha224", 4: "sha256",
                     5: "sha384", 6: "sha512"}.get(sig_alg >> 8, "sha256")
        digest = getattr(hashlib, hash_name)(client_random + server_random + params).digest()
        vk.verify_digest(sig, digest, sigdecode=sigdecode_der, allow_truncate=True)

    # ---------------- record layer ----------------
    def _nonce(self, iv, seq):
        return iv + seq.to_bytes(8, "big")

    def _send_encrypted(self, ct, plaintext):
        explicit = self.client_seq.to_bytes(8, "big")
        aad = explicit + u8(ct) + u16(0x0303) + u16(len(plaintext))
        ctbytes = AESGCM(self.client_key).encrypt(self._nonce(self.client_iv, self.client_seq),
                                                  plaintext, aad)
        frag = explicit + ctbytes
        self.client_seq += 1
        self._send_record(ct, frag)

    def _read_encrypted(self):
        ct, ver, frag = self._read_record()
        if ct == CT_ALERT:
            raise RuntimeError("TLS ALERT: %s" % frag.hex())
        explicit = frag[0:8]
        body = frag[8:]
        if os.environ.get("TLS_DEBUG"):
            print("[debug] enc frag(%d)=%s" % (len(frag), frag.hex()))
            print("[debug] ct=%d seq=%d explicit=%s" % (ct, self.server_seq, explicit.hex()))
        aad = self.server_seq.to_bytes(8, "big") + u8(ct) + u16(0x0303) + u16(len(body) - 16)
        # nonce = fixed_iv || explicit_nonce (iš įrašo), AAD naudoja seq
        pt = AESGCM(self.server_key).decrypt(self.server_iv + explicit, body, aad)
        self.server_seq += 1
        return ct, pt

    def send_app(self, data):
        self._send_encrypted(CT_APPLICATION_DATA, data)

    def recv_app(self):
        """Surenka pilną aplikacijos duomenų įrašą."""
        while True:
            ct, pt = self._read_encrypted()
            if ct == CT_APPLICATION_DATA:
                return pt
            if ct == CT_ALERT:
                raise RuntimeError("ALERT: %s" % pt.hex())

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass


def raw_hs(t, body):
    return u8(t) + u24(len(body)) + body
