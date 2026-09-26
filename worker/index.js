var __defProp = Object.defineProperty;
var __name = (target, value) => __defProp(target, "name", { value, configurable: true });

// src/index.js
var __defProp2 = Object.defineProperty;
var __name2 = /* @__PURE__ */ __name((target, value) => __defProp2(target, "name", { value, configurable: true }), "__name");
var u8 = Uint8Array;
var u16 = Uint16Array;
var i32 = Int32Array;
var fleb = new u8([
  0,
  0,
  0,
  0,
  0,
  0,
  0,
  0,
  1,
  1,
  1,
  1,
  2,
  2,
  2,
  2,
  3,
  3,
  3,
  3,
  4,
  4,
  4,
  4,
  5,
  5,
  5,
  5,
  0,
  /* unused */
  0,
  0,
  /* impossible */
  0
]);
var fdeb = new u8([
  0,
  0,
  0,
  0,
  1,
  1,
  2,
  2,
  3,
  3,
  4,
  4,
  5,
  5,
  6,
  6,
  7,
  7,
  8,
  8,
  9,
  9,
  10,
  10,
  11,
  11,
  12,
  12,
  13,
  13,
  /* unused */
  0,
  0
]);
var clim = new u8([16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15]);
var freb = /* @__PURE__ */ __name2(function(eb, start) {
  var b = new u16(31);
  for (var i2 = 0; i2 < 31; ++i2) {
    b[i2] = start += 1 << eb[i2 - 1];
  }
  var r = new i32(b[30]);
  for (var i2 = 1; i2 < 30; ++i2) {
    for (var j = b[i2]; j < b[i2 + 1]; ++j) {
      r[j] = j - b[i2] << 5 | i2;
    }
  }
  return { b, r };
}, "freb");
var _a = freb(fleb, 2);
var fl = _a.b;
var revfl = _a.r;
fl[28] = 258, revfl[258] = 28;
var _b = freb(fdeb, 0);
var fd = _b.b;
var revfd = _b.r;
var rev = new u16(32768);
for (i = 0; i < 32768; ++i) {
  x = (i & 43690) >> 1 | (i & 21845) << 1;
  x = (x & 52428) >> 2 | (x & 13107) << 2;
  x = (x & 61680) >> 4 | (x & 3855) << 4;
  rev[i] = ((x & 65280) >> 8 | (x & 255) << 8) >> 1;
}
var x;
var i;
var hMap = /* @__PURE__ */ __name2((function(cd, mb, r) {
  var s = cd.length;
  var i2 = 0;
  var l = new u16(mb);
  for (; i2 < s; ++i2) {
    if (cd[i2])
      ++l[cd[i2] - 1];
  }
  var le = new u16(mb);
  for (i2 = 1; i2 < mb; ++i2) {
    le[i2] = le[i2 - 1] + l[i2 - 1] << 1;
  }
  var co;
  if (r) {
    co = new u16(1 << mb);
    var rvb = 15 - mb;
    for (i2 = 0; i2 < s; ++i2) {
      if (cd[i2]) {
        var sv = i2 << 4 | cd[i2];
        var r_1 = mb - cd[i2];
        var v = le[cd[i2] - 1]++ << r_1;
        for (var m = v | (1 << r_1) - 1; v <= m; ++v) {
          co[rev[v] >> rvb] = sv;
        }
      }
    }
  } else {
    co = new u16(s);
    for (i2 = 0; i2 < s; ++i2) {
      if (cd[i2]) {
        co[i2] = rev[le[cd[i2] - 1]++] >> 15 - cd[i2];
      }
    }
  }
  return co;
}), "hMap");
var flt = new u8(288);
for (i = 0; i < 144; ++i)
  flt[i] = 8;
var i;
for (i = 144; i < 256; ++i)
  flt[i] = 9;
var i;
for (i = 256; i < 280; ++i)
  flt[i] = 7;
var i;
for (i = 280; i < 288; ++i)
  flt[i] = 8;
var i;
var fdt = new u8(32);
for (i = 0; i < 32; ++i)
  fdt[i] = 5;
var i;
var flrm = /* @__PURE__ */ hMap(flt, 9, 1);
var fdrm = /* @__PURE__ */ hMap(fdt, 5, 1);
var max = /* @__PURE__ */ __name2(function(a) {
  var m = a[0];
  for (var i2 = 1; i2 < a.length; ++i2) {
    if (a[i2] > m)
      m = a[i2];
  }
  return m;
}, "max");
var bits = /* @__PURE__ */ __name2(function(d, p, m) {
  var o = p / 8 | 0;
  return (d[o] | d[o + 1] << 8) >> (p & 7) & m;
}, "bits");
var bits16 = /* @__PURE__ */ __name2(function(d, p) {
  var o = p / 8 | 0;
  return (d[o] | d[o + 1] << 8 | d[o + 2] << 16) >> (p & 7);
}, "bits16");
var shft = /* @__PURE__ */ __name2(function(p) {
  return (p + 7) / 8 | 0;
}, "shft");
var slc = /* @__PURE__ */ __name2(function(v, s, e) {
  if (s == null || s < 0)
    s = 0;
  if (e == null || e > v.length)
    e = v.length;
  return new u8(v.subarray(s, e));
}, "slc");
var ec = [
  "unexpected EOF",
  "invalid block type",
  "invalid length/literal",
  "invalid distance",
  "stream finished",
  "no stream handler",
  ,
  // determined by compression function
  "no callback",
  "invalid UTF-8 data",
  "extra field too long",
  "date not in range 1980-2099",
  "filename too long",
  "stream finishing",
  "invalid zip data"
  // determined by unknown compression method
];
var err = /* @__PURE__ */ __name2(function(ind, msg, nt) {
  var e = new Error(msg || ec[ind]);
  e.code = ind;
  if (Error.captureStackTrace)
    Error.captureStackTrace(e, err);
  if (!nt)
    throw e;
  return e;
}, "err");
var inflt = /* @__PURE__ */ __name2(function(dat, st, buf, dict) {
  var sl = dat.length, dl = dict ? dict.length : 0;
  if (!sl || st.f && !st.l)
    return buf || new u8(0);
  var noBuf = !buf;
  var resize = noBuf || st.i != 2;
  var noSt = st.i;
  if (noBuf)
    buf = new u8(sl * 3);
  var cbuf = /* @__PURE__ */ __name2(function(l2) {
    var bl = buf.length;
    if (l2 > bl) {
      var nbuf = new u8(Math.max(bl * 2, l2));
      nbuf.set(buf);
      buf = nbuf;
    }
  }, "cbuf");
  var final = st.f || 0, pos = st.p || 0, bt = st.b || 0, lm = st.l, dm = st.d, lbt = st.m, dbt = st.n;
  var tbts = sl * 8;
  do {
    if (!lm) {
      final = bits(dat, pos, 1);
      var type = bits(dat, pos + 1, 3);
      pos += 3;
      if (!type) {
        var s = shft(pos) + 4, l = dat[s - 4] | dat[s - 3] << 8, t = s + l;
        if (t > sl) {
          if (noSt)
            err(0);
          break;
        }
        if (resize)
          cbuf(bt + l);
        buf.set(dat.subarray(s, t), bt);
        st.b = bt += l, st.p = pos = t * 8, st.f = final;
        continue;
      } else if (type == 1)
        lm = flrm, dm = fdrm, lbt = 9, dbt = 5;
      else if (type == 2) {
        var hLit = bits(dat, pos, 31) + 257, hcLen = bits(dat, pos + 10, 15) + 4;
        var tl = hLit + bits(dat, pos + 5, 31) + 1;
        pos += 14;
        var ldt = new u8(tl);
        var clt = new u8(19);
        for (var i2 = 0; i2 < hcLen; ++i2) {
          clt[clim[i2]] = bits(dat, pos + i2 * 3, 7);
        }
        pos += hcLen * 3;
        var clb = max(clt), clbmsk = (1 << clb) - 1;
        var clm = hMap(clt, clb, 1);
        for (var i2 = 0; i2 < tl; ) {
          var r = clm[bits(dat, pos, clbmsk)];
          pos += r & 15;
          var s = r >> 4;
          if (s < 16) {
            ldt[i2++] = s;
          } else {
            var c = 0, n = 0;
            if (s == 16)
              n = 3 + bits(dat, pos, 3), pos += 2, c = ldt[i2 - 1];
            else if (s == 17)
              n = 3 + bits(dat, pos, 7), pos += 3;
            else if (s == 18)
              n = 11 + bits(dat, pos, 127), pos += 7;
            while (n--)
              ldt[i2++] = c;
          }
        }
        var lt = ldt.subarray(0, hLit), dt = ldt.subarray(hLit);
        lbt = max(lt);
        dbt = max(dt);
        lm = hMap(lt, lbt, 1);
        dm = hMap(dt, dbt, 1);
      } else
        err(1);
      if (pos > tbts) {
        if (noSt)
          err(0);
        break;
      }
    }
    if (resize)
      cbuf(bt + 131072);
    var lms = (1 << lbt) - 1, dms = (1 << dbt) - 1;
    var lpos = pos;
    for (; ; lpos = pos) {
      var c = lm[bits16(dat, pos) & lms], sym = c >> 4;
      pos += c & 15;
      if (pos > tbts) {
        if (noSt)
          err(0);
        break;
      }
      if (!c)
        err(2);
      if (sym < 256)
        buf[bt++] = sym;
      else if (sym == 256) {
        lpos = pos, lm = null;
        break;
      } else {
        var add = sym - 254;
        if (sym > 264) {
          var i2 = sym - 257, b = fleb[i2];
          add = bits(dat, pos, (1 << b) - 1) + fl[i2];
          pos += b;
        }
        var d = dm[bits16(dat, pos) & dms], dsym = d >> 4;
        if (!d)
          err(3);
        pos += d & 15;
        var dt = fd[dsym];
        if (dsym > 3) {
          var b = fdeb[dsym];
          dt += bits16(dat, pos) & (1 << b) - 1, pos += b;
        }
        if (pos > tbts) {
          if (noSt)
            err(0);
          break;
        }
        if (resize)
          cbuf(bt + 131072);
        var end = bt + add;
        if (bt < dt) {
          var shift = dl - dt, dend = Math.min(dt, end);
          if (shift + bt < 0)
            err(3);
          for (; bt < dend; ++bt)
            buf[bt] = dict[shift + bt];
        }
        for (; bt < end; ++bt)
          buf[bt] = buf[bt - dt];
      }
    }
    st.l = lm, st.p = lpos, st.b = bt, st.f = final;
    if (lm)
      final = 1, st.m = lbt, st.d = dm, st.n = dbt;
  } while (!final);
  return bt != buf.length && noBuf ? slc(buf, 0, bt) : buf.subarray(0, bt);
}, "inflt");
var et = /* @__PURE__ */ new u8(0);
var b2 = /* @__PURE__ */ __name2(function(d, b) {
  return d[b] | d[b + 1] << 8;
}, "b2");
var b4 = /* @__PURE__ */ __name2(function(d, b) {
  return (d[b] | d[b + 1] << 8 | d[b + 2] << 16 | d[b + 3] << 24) >>> 0;
}, "b4");
var b8 = /* @__PURE__ */ __name2(function(d, b) {
  return b4(d, b) + b4(d, b + 4) * 4294967296;
}, "b8");
function inflateSync(data, opts) {
  return inflt(data, { i: 2 }, opts && opts.out, opts && opts.dictionary);
}
__name(inflateSync, "inflateSync");
__name2(inflateSync, "inflateSync");
var td = typeof TextDecoder != "undefined" && /* @__PURE__ */ new TextDecoder();
var tds = 0;
try {
  td.decode(et, { stream: true });
  tds = 1;
} catch (e) {
}
var dutf8 = /* @__PURE__ */ __name2(function(d) {
  for (var r = "", i2 = 0; ; ) {
    var c = d[i2++];
    var eb = (c > 127) + (c > 223) + (c > 239);
    if (i2 + eb > d.length)
      return { s: r, r: slc(d, i2 - 1) };
    if (!eb)
      r += String.fromCharCode(c);
    else if (eb == 3) {
      c = ((c & 15) << 18 | (d[i2++] & 63) << 12 | (d[i2++] & 63) << 6 | d[i2++] & 63) - 65536, r += String.fromCharCode(55296 | c >> 10, 56320 | c & 1023);
    } else if (eb & 1)
      r += String.fromCharCode((c & 31) << 6 | d[i2++] & 63);
    else
      r += String.fromCharCode((c & 15) << 12 | (d[i2++] & 63) << 6 | d[i2++] & 63);
  }
}, "dutf8");
function strFromU8(dat, latin1) {
  if (latin1) {
    var r = "";
    for (var i2 = 0; i2 < dat.length; i2 += 16384)
      r += String.fromCharCode.apply(null, dat.subarray(i2, i2 + 16384));
    return r;
  } else if (td) {
    return td.decode(dat);
  } else {
    var _a2 = dutf8(dat), s = _a2.s, r = _a2.r;
    if (r.length)
      err(8);
    return s;
  }
}
__name(strFromU8, "strFromU8");
__name2(strFromU8, "strFromU8");
var slzh = /* @__PURE__ */ __name2(function(d, b) {
  return b + 30 + b2(d, b + 26) + b2(d, b + 28);
}, "slzh");
var zh = /* @__PURE__ */ __name2(function(d, b, z) {
  var fnl = b2(d, b + 28), efl = b2(d, b + 30), fn = strFromU8(d.subarray(b + 46, b + 46 + fnl), !(b2(d, b + 8) & 2048)), es = b + 46 + fnl;
  var _a2 = z64hs(d, es, efl, z, b4(d, b + 20), b4(d, b + 24), b4(d, b + 42)), sc = _a2[0], su = _a2[1], off = _a2[2];
  return [b2(d, b + 10), sc, su, fn, es + efl + b2(d, b + 32), off];
}, "zh");
var z64hs = /* @__PURE__ */ __name2(function(d, b, l, z, sc, su, off) {
  var nsc = sc == 4294967295, nsu = su == 4294967295, noff = off == 4294967295, e = b + l;
  var nf = nsc + nsu + noff;
  if (z && nf) {
    for (; b + 4 < e; b += 4 + b2(d, b + 2)) {
      if (b2(d, b) == 1) {
        return [
          nsc ? b8(d, b + 4 + 8 * nsu) : sc,
          nsu ? b8(d, b + 4) : su,
          noff ? b8(d, b + 4 + 8 * (nsu + nsc)) : off,
          1
        ];
      }
    }
    if (z < 2)
      err(13);
  }
  return [sc, su, off, 0];
}, "z64hs");
function unzipSync(data, opts) {
  var files = {};
  var e = data.length - 22;
  for (; b4(data, e) != 101010256; --e) {
    if (!e || data.length - e > 65558)
      err(13);
  }
  ;
  var c = b2(data, e + 8);
  if (!c)
    return {};
  var o = b4(data, e + 16);
  var z = b4(data, e - 20) == 117853008;
  if (z) {
    var ze = b4(data, e - 12);
    z = b4(data, ze) == 101075792;
    if (z) {
      c = b4(data, ze + 32);
      o = b4(data, ze + 48);
    }
  }
  var fltr = opts && opts.filter;
  for (var i2 = 0; i2 < c; ++i2) {
    var _a2 = zh(data, o, z), c_2 = _a2[0], sc = _a2[1], su = _a2[2], fn = _a2[3], no = _a2[4], off = _a2[5], b = slzh(data, off);
    o = no;
    if (!fltr || fltr({
      name: fn,
      size: sc,
      originalSize: su,
      compression: c_2
    })) {
      if (!c_2)
        files[fn] = slc(data, b, b + sc);
      else if (c_2 == 8)
        files[fn] = inflateSync(data.subarray(b, b + sc), { out: new u8(su) });
      else
        err(14, "unknown compression type " + c_2);
    }
  }
  return files;
}
__name(unzipSync, "unzipSync");
__name2(unzipSync, "unzipSync");
var API = "https://api.github.com";
var EVENT_TYPE = "gpt_task";
var RESULT_FILENAME = "execution_result.json";
var PROTOCOL_VERSION = "2025-06-18";
var ACCESS_TTL = 3600;
var REFRESH_TTL = 60 * 60 * 24 * 30;
var CODE_TTL = 300;
var SCOPE = "mcp";
var ASSET_READ_SCOPE = "asset.read";
var ASSET_TYPES = /* @__PURE__ */ new Set(["KNOWLEDGE", "SKILL", "REALITY", "DECISION"]);
var ASSET_ID_RE = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,199}$/;
var ASSET_SUBTYPE_SCHEMA = { "wechat-conversation-snapshot-v0.1": "wechat_conversation_snapshot" };
var CHATGPT_REDIRECT = "https://chatgpt.com/connector_platform_oauth_redirect";
var CHATGPT_REDIRECT_PREFIX = "https://chatgpt.com/connector/oauth/";
var ALLOWLIST = ["hello.py", "test_hello.py"];
var FORBIDDEN_PREFIXES = [".github/workflows/"];
var FORBIDDEN_SUBSTRINGS = ["secret", "token", "credential", ".env", ".pem", ".key"];
function corsHeaders() {
  return {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Authorization, Content-Type, Mcp-Session-Id, Accept",
    "Access-Control-Max-Age": "86400"
  };
}
__name(corsHeaders, "corsHeaders");
__name2(corsHeaders, "corsHeaders");
function json(body, status, extra = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...extra }
  });
}
__name(json, "json");
__name2(json, "json");
function originOf(request) {
  return new URL(request.url).origin;
}
__name(originOf, "originOf");
__name2(originOf, "originOf");
function bytesToB64url(bytes) {
  let bin = "";
  for (const b of bytes) bin += String.fromCharCode(b);
  return btoa(bin).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}
__name(bytesToB64url, "bytesToB64url");
__name2(bytesToB64url, "bytesToB64url");
function b64urlEncode(str) {
  return bytesToB64url(new TextEncoder().encode(str));
}
__name(b64urlEncode, "b64urlEncode");
__name2(b64urlEncode, "b64urlEncode");
function b64urlDecode(str) {
  const pad = str.length % 4 === 0 ? "" : "=".repeat(4 - str.length % 4);
  const b64 = str.replace(/-/g, "+").replace(/_/g, "/") + pad;
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i2 = 0; i2 < bin.length; i2++) bytes[i2] = bin.charCodeAt(i2);
  return new TextDecoder().decode(bytes);
}
__name(b64urlDecode, "b64urlDecode");
__name2(b64urlDecode, "b64urlDecode");
async function hmacKey(secret) {
  return crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign", "verify"]
  );
}
__name(hmacKey, "hmacKey");
__name2(hmacKey, "hmacKey");
async function signPayload(payload, secret) {
  const body = b64urlEncode(JSON.stringify(payload));
  const key = await hmacKey(secret);
  const sig = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(body));
  return `${body}.${bytesToB64url(new Uint8Array(sig))}`;
}
__name(signPayload, "signPayload");
__name2(signPayload, "signPayload");
async function verifyPayload(token, secret) {
  if (typeof token !== "string" || !token.includes(".")) return null;
  const [body, sig] = token.split(".");
  try {
    const key = await hmacKey(secret);
    const ok = await crypto.subtle.verify(
      "HMAC",
      key,
      Uint8Array.from(atob(sig.replace(/-/g, "+").replace(/_/g, "/")), (c) => c.charCodeAt(0)),
      new TextEncoder().encode(body)
    );
    if (!ok) return null;
    const payload = JSON.parse(b64urlDecode(body));
    if (payload.exp && payload.exp < Math.floor(Date.now() / 1e3)) return null;
    return payload;
  } catch {
    return null;
  }
}
__name(verifyPayload, "verifyPayload");
__name2(verifyPayload, "verifyPayload");
async function sha256B64url(text) {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return bytesToB64url(new Uint8Array(digest));
}
__name(sha256B64url, "sha256B64url");
__name2(sha256B64url, "sha256B64url");
function timingSafeEqual(a, b) {
  const ab = new TextEncoder().encode(a);
  const bb = new TextEncoder().encode(b);
  if (ab.length !== bb.length) return false;
  let diff = 0;
  for (let i2 = 0; i2 < ab.length; i2++) diff |= ab[i2] ^ bb[i2];
  return diff === 0;
}
__name(timingSafeEqual, "timingSafeEqual");
__name2(timingSafeEqual, "timingSafeEqual");
function nowSec() {
  return Math.floor(Date.now() / 1e3);
}
__name(nowSec, "nowSec");
__name2(nowSec, "nowSec");
function normalizeScopes(value) {
  const requested = String(value || "").split(/\s+/).filter(Boolean);
  const scopes = [...new Set(requested.filter((scope) => scope === SCOPE || scope === ASSET_READ_SCOPE))];
  return scopes.length ? scopes : [SCOPE];
}
__name(normalizeScopes, "normalizeScopes");
__name2(normalizeScopes, "normalizeScopes");
function scopeString(value) {
  return normalizeScopes(value).join(" ");
}
__name(scopeString, "scopeString");
__name2(scopeString, "scopeString");
function hasReadScope(auth) {
  return Boolean(auth && auth.scopes && (auth.scopes.includes(ASSET_READ_SCOPE) || auth.scopes.includes(SCOPE)));
}
__name(hasReadScope, "hasReadScope");
__name2(hasReadScope, "hasReadScope");
function hasWriteScope(auth) {
  return Boolean(auth && auth.scopes && auth.scopes.includes(SCOPE));
}
__name(hasWriteScope, "hasWriteScope");
__name2(hasWriteScope, "hasWriteScope");
function protectedResourceMetadata(origin) {
  return {
    resource: origin,
    authorization_servers: [origin],
    scopes_supported: [SCOPE, ASSET_READ_SCOPE],
    bearer_methods_supported: ["header"],
    resource_documentation: `${origin}/`
  };
}
__name(protectedResourceMetadata, "protectedResourceMetadata");
__name2(protectedResourceMetadata, "protectedResourceMetadata");
function authorizationServerMetadata(origin) {
  return {
    issuer: origin,
    authorization_endpoint: `${origin}/authorize`,
    token_endpoint: `${origin}/token`,
    registration_endpoint: `${origin}/register`,
    response_types_supported: ["code"],
    grant_types_supported: ["authorization_code", "refresh_token"],
    code_challenge_methods_supported: ["S256"],
    token_endpoint_auth_methods_supported: ["none"],
    scopes_supported: [SCOPE, ASSET_READ_SCOPE],
    authorization_response_iss_parameter_supported: false
  };
}
__name(authorizationServerMetadata, "authorizationServerMetadata");
__name2(authorizationServerMetadata, "authorizationServerMetadata");
async function registerClient(request, env, origin) {
  let body = {};
  try {
    body = await request.json();
  } catch {
    body = {};
  }
  const redirectUris = Array.isArray(body.redirect_uris) ? body.redirect_uris.map(String) : [];
  const clientId = await signPayload(
    { kind: "client", redirect_uris: redirectUris, exp: nowSec() + 60 * 60 * 24 * 365 },
    env.OAUTH_SIGNING_KEY
  );
  return json(
    {
      client_id: clientId,
      client_id_issued_at: nowSec(),
      redirect_uris: redirectUris,
      token_endpoint_auth_method: "none",
      grant_types: ["authorization_code", "refresh_token"],
      response_types: ["code"]
    },
    201
  );
}
__name(registerClient, "registerClient");
__name2(registerClient, "registerClient");
async function resolveRedirectUris(clientId, env) {
  if (!clientId) return [];
  if (clientId.startsWith("https://")) {
    try {
      const res = await fetch(clientId, { headers: { "User-Agent": "personal-ai-execution-mcp/0.1" } });
      if (!res.ok) return [];
      const doc = await res.json();
      return Array.isArray(doc.redirect_uris) ? doc.redirect_uris.map(String) : [];
    } catch {
      return [];
    }
  }
  const payload = await verifyPayload(clientId, env.OAUTH_SIGNING_KEY);
  return payload && Array.isArray(payload.redirect_uris) ? payload.redirect_uris : [];
}
__name(resolveRedirectUris, "resolveRedirectUris");
__name2(resolveRedirectUris, "resolveRedirectUris");
function redirectAllowed(registered, redirectUri) {
  if (!redirectUri) return false;
  if (redirectUri === CHATGPT_REDIRECT || redirectUri.startsWith(CHATGPT_REDIRECT_PREFIX)) return true;
  return registered.includes(redirectUri);
}
__name(redirectAllowed, "redirectAllowed");
__name2(redirectAllowed, "redirectAllowed");
function consentPage(params, error) {
  const hidden = Object.entries(params).map(([k, v]) => `<input type="hidden" name="${k}" value="${String(v).replace(/"/g, "&quot;")}">`).join("");
  const message = error ? `<p style="color:#b00">${error}</p>` : "";
  return `<!doctype html><html><head><meta charset="utf-8"><title>Authorize Personal AI Execution</title></head>
<body style="font-family:system-ui;max-width:520px;margin:48px auto">
<h2>Authorize <em>Personal AI Execution</em></h2>
<p>This grants the requesting MCP client access to <code>submit_task</code> and <code>get_task_result</code>.</p>
${message}
<form method="post" action="/authorize">
${hidden}
<label>Owner password<br><input type="password" name="password" autocomplete="current-password" style="width:100%"></label>
<p><button type="submit" style="padding:8px 16px">Authorize</button></p>
</form>
</body></html>`;
}
__name(consentPage, "consentPage");
__name2(consentPage, "consentPage");
async function authorizeGet(request, env) {
  const url = new URL(request.url);
  const p = Object.fromEntries(url.searchParams);
  if (p.response_type !== "code") return json({ error: "unsupported_response_type" }, 400);
  if (p.code_challenge_method && p.code_challenge_method !== "S256") {
    return json({ error: "invalid_request", error_description: "PKCE S256 required" }, 400);
  }
  if (!p.code_challenge) return json({ error: "invalid_request", error_description: "code_challenge required" }, 400);
  const registered = await resolveRedirectUris(p.client_id, env);
  if (!redirectAllowed(registered, p.redirect_uri)) {
    return json({ error: "invalid_request", error_description: "redirect_uri not allowed" }, 400);
  }
  return new Response(consentPage(p), { status: 200, headers: { "Content-Type": "text/html; charset=utf-8" } });
}
__name(authorizeGet, "authorizeGet");
__name2(authorizeGet, "authorizeGet");
async function authorizePost(request, env) {
  const form = await request.formData();
  const p = Object.fromEntries(form.entries());
  const registered = await resolveRedirectUris(p.client_id, env);
  if (!redirectAllowed(registered, p.redirect_uri)) {
    return json({ error: "invalid_request", error_description: "redirect_uri not allowed" }, 400);
  }
  if (!env.OWNER_PASSWORD || !timingSafeEqual(String(p.password || ""), env.OWNER_PASSWORD)) {
    return new Response(consentPage(p, "Incorrect owner password."), {
      status: 401,
      headers: { "Content-Type": "text/html; charset=utf-8" }
    });
  }
  const code = await signPayload(
    {
      kind: "code",
      client_id: p.client_id,
      redirect_uri: p.redirect_uri,
      code_challenge: p.code_challenge,
      scope: scopeString(p.scope || SCOPE),
      exp: nowSec() + CODE_TTL
    },
    env.OAUTH_SIGNING_KEY
  );
  const target = new URL(p.redirect_uri);
  target.searchParams.set("code", code);
  if (p.state) target.searchParams.set("state", p.state);
  return Response.redirect(target.toString(), 302);
}
__name(authorizePost, "authorizePost");
__name2(authorizePost, "authorizePost");
async function tokenEndpoint(request, env) {
  let form;
  try {
    form = await request.formData();
  } catch {
    return json({ error: "invalid_request" }, 400);
  }
  const grantType = String(form.get("grant_type") || "");
  if (grantType === "authorization_code") {
    const payload = await verifyPayload(String(form.get("code") || ""), env.OAUTH_SIGNING_KEY);
    if (!payload || payload.kind !== "code") return json({ error: "invalid_grant" }, 400);
    if (payload.redirect_uri !== String(form.get("redirect_uri") || "")) {
      return json({ error: "invalid_grant", error_description: "redirect_uri mismatch" }, 400);
    }
    const verifier = String(form.get("code_verifier") || "");
    if (!verifier) return json({ error: "invalid_grant", error_description: "code_verifier required" }, 400);
    const challenge = await sha256B64url(verifier);
    if (challenge !== payload.code_challenge) {
      return json({ error: "invalid_grant", error_description: "PKCE verification failed" }, 400);
    }
    return json(await issueTokens(env, payload.scope || SCOPE));
  }
  if (grantType === "refresh_token") {
    const payload = await verifyPayload(String(form.get("refresh_token") || ""), env.OAUTH_SIGNING_KEY);
    if (!payload || payload.kind !== "refresh") return json({ error: "invalid_grant" }, 400);
    return json(await issueTokens(env, payload.scope || SCOPE));
  }
  return json({ error: "unsupported_grant_type" }, 400);
}
__name(tokenEndpoint, "tokenEndpoint");
__name2(tokenEndpoint, "tokenEndpoint");
async function issueTokens(env, scope) {
  scope = scopeString(scope);
  const access = await signPayload(
    { kind: "access", sub: "owner", scope, aud: "mcp", exp: nowSec() + ACCESS_TTL },
    env.OAUTH_SIGNING_KEY
  );
  const refresh = await signPayload(
    { kind: "refresh", sub: "owner", scope, exp: nowSec() + REFRESH_TTL },
    env.OAUTH_SIGNING_KEY
  );
  return {
    access_token: access,
    token_type: "Bearer",
    expires_in: ACCESS_TTL,
    refresh_token: refresh,
    scope
  };
}
__name(issueTokens, "issueTokens");
__name2(issueTokens, "issueTokens");
async function mcpAuthorized(request, env) {
  const header = request.headers.get("Authorization") || "";
  if (!header.startsWith("Bearer ")) return false;
  const presented = header.slice("Bearer ".length).trim();
  if (env.MCP_AUTH_TOKEN && timingSafeEqual(presented, env.MCP_AUTH_TOKEN)) {
    return { scopes: [SCOPE, ASSET_READ_SCOPE], kind: "static" };
  }
  const payload = await verifyPayload(presented, env.OAUTH_SIGNING_KEY);
  return payload && payload.kind === "access" ? { scopes: normalizeScopes(payload.scope), kind: "oauth", payload } : false;
}
__name(mcpAuthorized, "mcpAuthorized");
__name2(mcpAuthorized, "mcpAuthorized");
function unauthorized(origin) {
  return json(
    { error: "UNAUTHORIZED" },
    401,
    {
      "WWW-Authenticate": `Bearer resource_metadata="${origin}/.well-known/oauth-protected-resource", scope="${SCOPE} ${ASSET_READ_SCOPE}"`
    }
  );
}
__name(unauthorized, "unauthorized");
__name2(unauthorized, "unauthorized");
function newTaskId() {
  return `cf-${crypto.randomUUID().replace(/-/g, "").slice(0, 12)}`;
}
__name(newTaskId, "newTaskId");
__name2(newTaskId, "newTaskId");
function buildContract(goal, instructions, acceptance) {
  return {
    task_id: newTaskId(),
    goal: String(goal ?? ""),
    instructions: Array.isArray(instructions) ? instructions.map(String) : [],
    risk_level: "LOW",
    expected_files: [...ALLOWLIST],
    acceptance: Array.isArray(acceptance) ? acceptance.map(String) : []
  };
}
__name(buildContract, "buildContract");
__name2(buildContract, "buildContract");
function validateContract(contract) {
  const errors = [];
  if (!contract.goal.trim()) errors.push("goal must be non-empty");
  if (!contract.instructions.length) errors.push("instructions must be a non-empty list");
  if (!contract.acceptance.length) errors.push("acceptance must be a non-empty list");
  for (const path of contract.expected_files) {
    const low = String(path).toLowerCase();
    if (FORBIDDEN_PREFIXES.some((p) => low.startsWith(p)) || FORBIDDEN_SUBSTRINGS.some((s) => low.includes(s))) {
      errors.push(`forbidden expected_file: ${path}`);
    } else if (!ALLOWLIST.includes(path)) {
      errors.push(`expected_file outside allowlist: ${path}`);
    }
  }
  return errors;
}
__name(validateContract, "validateContract");
__name2(validateContract, "validateContract");
function ghHeaders(env) {
  return {
    Authorization: `Bearer ${env.GITHUB_TOKEN}`,
    Accept: "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "personal-ai-execution-mcp-worker/0.1",
    "Content-Type": "application/json"
  };
}
__name(ghHeaders, "ghHeaders");
function safeGithubResponseBody(raw) {
  return String(raw || "")
    .slice(0, 512)
    .replace(/gh[pousr]_[A-Za-z0-9_\-]+/gi, "[REDACTED]")
    .replace(/github_pat_[A-Za-z0-9_]+/gi, "[REDACTED]")
    .replace(/("?(?:token|secret|password|authorization)"?\s*:\s*")([^"\\]*)"/gi, "$1[REDACTED]\"");
}
__name(safeGithubResponseBody, "safeGithubResponseBody");
async function dispatchTask(env, contract) {
  const res = await fetch(`${API}/repos/${env.GITHUB_REPO}/dispatches`, {
    method: "POST",
    headers: ghHeaders(env),
    body: JSON.stringify({ event_type: EVENT_TYPE, client_payload: { task: contract } })
  });
  const bodySafe = safeGithubResponseBody(await res.text());
  return {
    ok: res.ok,
    status: res.status,
    requestId: res.headers.get("x-github-request-id") || null,
    bodySafe
  };
}
__name(dispatchTask, "dispatchTask");
__name2(dispatchTask, "dispatchTask");
async function findArtifact(env, name) {
  const res = await fetch(
    `${API}/repos/${env.GITHUB_REPO}/actions/artifacts?name=${encodeURIComponent(name)}`,
    { headers: ghHeaders(env) }
  );
  if (!res.ok) throw new Error(`GitHub artifact lookup failed HTTP ${res.status}`);
  const payload = await res.json();
  const artifacts = payload.artifacts || [];
  if (!artifacts.length) return null;
  artifacts.sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)));
  return artifacts[0];
}
__name(findArtifact, "findArtifact");
__name2(findArtifact, "findArtifact");
async function downloadArtifactJson(env, artifactId) {
  const url = `${API}/repos/${env.GITHUB_REPO}/actions/artifacts/${artifactId}/zip`;
  let res = await fetch(url, { headers: ghHeaders(env), redirect: "manual" });
  if (res.status >= 300 && res.status < 400) {
    const location = res.headers.get("location");
    if (!location) throw new Error("artifact redirect without location");
    res = await fetch(location);
  }
  if (!res.ok) throw new Error(`artifact download failed HTTP ${res.status}`);
  const files = unzipSync(new Uint8Array(await res.arrayBuffer()));
  const name = Object.keys(files).find((n) => n.endsWith(RESULT_FILENAME));
  if (!name) throw new Error(`${RESULT_FILENAME} not found in artifact`);
  return JSON.parse(new TextDecoder().decode(files[name]));
}
__name(downloadArtifactJson, "downloadArtifactJson");
__name2(downloadArtifactJson, "downloadArtifactJson");
async function getArtifactWorkflowRun(env, artifact) {
  const runId = artifact?.workflow_run?.id;
  if (!runId) throw new Error("artifact missing workflow_run.id");
  const res = await fetch(`${API}/repos/${env.GITHUB_REPO}/actions/runs/${runId}`, {
    headers: ghHeaders(env)
  });
  if (!res.ok) throw new Error(`GitHub workflow lookup failed HTTP ${res.status}`);
  const run = await res.json();
  return {
    id: run.id,
    status: run.status,
    conclusion: run.conclusion,
    html_url: run.html_url,
    created_at: run.created_at ?? null,
    updated_at: run.updated_at ?? null,
    completed_at: run.completed_at ?? null
  };
}
__name(getArtifactWorkflowRun, "getArtifactWorkflowRun");
__name2(getArtifactWorkflowRun, "getArtifactWorkflowRun");
function verifiedResultStatus(rawStatus, run) {
  if (run.status !== "completed") return "pending";
  if (run.conclusion === "cancelled") return "cancelled";
  if (run.conclusion !== "success") return "failure";
  return rawStatus || "unknown";
}
__name(verifiedResultStatus, "verifiedResultStatus");
__name2(verifiedResultStatus, "verifiedResultStatus");
var REG_PREFIX = "task:";
var BLOCKED_AFTER_MS = 15 * 60 * 1e3;
function regKey(taskId) {
  return `${REG_PREFIX}${taskId}`;
}
__name(regKey, "regKey");
__name2(regKey, "regKey");
async function recordTask(env, contract) {
  if (!env.TASK_REGISTRY) return;
  const nowIso = (/* @__PURE__ */ new Date()).toISOString();
  const meta = {
    status: "submitted",
    title: String(contract.goal || "").slice(0, 120),
    created_at: nowIso,
    updated_at: nowIso,
    result_available: false,
    reviewed: false
  };
  await env.TASK_REGISTRY.put(regKey(contract.task_id), JSON.stringify({ task_id: contract.task_id, ...meta }), {
    metadata: meta
  });
}
__name(recordTask, "recordTask");
__name2(recordTask, "recordTask");
async function listTasks(env) {
  if (!env.TASK_REGISTRY) return [];
  const listed = await env.TASK_REGISTRY.list({ prefix: REG_PREFIX });
  return listed.keys.map((k) => ({ task_id: k.name.slice(REG_PREFIX.length), ...k.metadata || {} }));
}
__name(listTasks, "listTasks");
__name2(listTasks, "listTasks");
async function saveTask(env, entry) {
  if (!env.TASK_REGISTRY) return;
  const { task_id, ...meta } = entry;
  await env.TASK_REGISTRY.put(regKey(task_id), JSON.stringify(entry), { metadata: meta });
}
__name(saveTask, "saveTask");
__name2(saveTask, "saveTask");
async function readTask(env, taskId) {
  if (!env.TASK_REGISTRY) return null;
  return env.TASK_REGISTRY.get(regKey(taskId), "json");
}
__name(readTask, "readTask");
__name2(readTask, "readTask");
async function listPendingResults(env) {
  const tasks = await listTasks(env);
  const now = Date.now();
  const pending = [];
  const pending_review = [];
  const failed = [];
  const blocked = [];
  for (const task of tasks) {
    let status = task.status || "submitted";
    let resultAvailable = Boolean(task.result_available);
    let updatedAt = task.updated_at || task.created_at || "";
    let completedAt = task.completed_at || "";
    if (!resultAvailable || !task.workflow_verified) {
      try {
        const artifact = await findArtifact(env, `execution_result-${task.task_id}`);
        if (artifact) {
          const data = await downloadArtifactJson(env, artifact.id);
          const run = await getArtifactWorkflowRun(env, artifact);
          status = verifiedResultStatus(data.status, run);
          resultAvailable = run.status === "completed";
          updatedAt = run.updated_at || updatedAt;
          completedAt = run.completed_at || (resultAvailable ? updatedAt : "");
        } else if (task.result_available) {
          status = "unknown";
          resultAvailable = false;
        }
      } catch {
        status = task.result_available ? "unknown" : "submitted";
        resultAvailable = false;
      }
    }
    const entry = {
      task_id: task.task_id,
      status,
      title: task.title || "",
      updated_at: updatedAt,
      completed_at: completedAt,
      result_available: resultAvailable,
      reviewed: task.reviewed === true,
      requires_review: resultAvailable && task.reviewed !== true,
      recommended_action: resultAvailable ? "review" : "wait"
    };
    if (resultAvailable && task.reviewed !== true) {
      pending.push(entry);
      pending_review.push(entry);
      if (status === "failure") failed.push(entry);
    } else {
      if (!resultAvailable) {
        const created = Date.parse(task.created_at || "") || now;
        if (now - created > BLOCKED_AFTER_MS) {
          entry.recommended_action = "inspect";
          blocked.push(entry);
        }
      }
    }
  }
  return {
    pending,
    pending_review,
    failed,
    blocked,
    counts: {
      pending: pending.length,
      pending_review: pending_review.length,
      failed: failed.length,
      blocked: blocked.length,
      total: tasks.length
    }
  };
}
__name(listPendingResults, "listPendingResults");
__name2(listPendingResults, "listPendingResults");
var REVIEW_VERDICTS = ["PASS", "FAIL", "BLOCKED"];
async function toolMarkReviewed(env, args) {
  if (!env.TASK_REGISTRY) return { isError: true, text: "TASK_REGISTRY_UNAVAILABLE" };
  const taskId = String(args.task_id ?? "").trim();
  const verdict = String(args.verdict ?? "").trim().toUpperCase();
  const note = args.note == null ? null : String(args.note);
  if (!taskId) return { isError: true, text: "INVALID_INPUT: task_id required" };
  if (!REVIEW_VERDICTS.includes(verdict)) {
    return { isError: true, text: `INVALID_INPUT: verdict must be one of ${REVIEW_VERDICTS.join(", ")}` };
  }
  const task = await readTask(env, taskId);
  if (!task) return { isError: true, text: `UNKNOWN_TASK: ${taskId}` };
  if (task.reviewed === true) {
    if (task.verdict === verdict) {
      const result2 = {
        task_id: taskId,
        reviewed: true,
        verdict,
        review_event: task.review_event ?? null,
        idempotent: true
      };
      return { isError: false, text: JSON.stringify(result2), structuredContent: result2 };
    }
    return { isError: true, text: `REVIEW_ALREADY_RECORDED: ${task.verdict || "UNKNOWN"}` };
  }
  const timestamp = (/* @__PURE__ */ new Date()).toISOString();
  const reviewEvent = {
    task_id: taskId,
    action: "review",
    verdict,
    timestamp,
    note
  };
  const updated = {
    ...task,
    reviewed: true,
    verdict,
    reviewed_at: timestamp,
    review_note: note,
    review_event: reviewEvent,
    updated_at: timestamp
  };
  await saveTask(env, updated);
  const result = {
    task_id: taskId,
    reviewed: true,
    verdict,
    reviewed_at: timestamp,
    review_event: reviewEvent,
    idempotent: false
  };
  return { isError: false, text: JSON.stringify(result), structuredContent: result };
}
__name(toolMarkReviewed, "toolMarkReviewed");
__name2(toolMarkReviewed, "toolMarkReviewed");
async function toolSubmitTask(env, args) {
  const contract = buildContract(args.goal, args.instructions, args.acceptance);
  const errors = validateContract(contract);
  if (errors.length) return { isError: true, text: `INVALID_TASK: ${errors.join("; ")}` };
  let dispatch;
  try {
    dispatch = await dispatchTask(env, contract);
  } catch (err2) {
    return {
      isError: true,
      text: JSON.stringify({
        task_id: contract.task_id,
        status: "dispatch_failed",
        dispatch_status: "network_error",
        github_http_status: null,
        github_request_id: null,
        github_response_body_safe: null,
        error: safeGithubResponseBody(err2?.message || "request failed")
      })
    };
  }
  if (!dispatch.ok) {
    return {
      isError: true,
      text: JSON.stringify({
        task_id: contract.task_id,
        status: "dispatch_failed",
        dispatch_status: "github_rejected",
        github_http_status: dispatch.status,
        github_request_id: dispatch.requestId,
        github_response_body_safe: dispatch.bodySafe || null
      })
    };
  }
  try {
    await recordTask(env, contract);
  } catch {
  }
  return {
    isError: false,
    text: JSON.stringify({
      task_id: contract.task_id,
      status: "submitted",
      round: 1,
      dispatch_status: "accepted",
      github_http_status: dispatch.status,
      github_request_id: dispatch.requestId,
      github_response_body_safe: dispatch.bodySafe || null
    })
  };
}
__name(toolSubmitTask, "toolSubmitTask");
__name2(toolSubmitTask, "toolSubmitTask");
async function toolListPendingResults(env, _args) {
  try {
    return { isError: false, text: JSON.stringify(await listPendingResults(env)) };
  } catch (err2) {
    return { isError: true, text: `REGISTRY_READ_FAILED: ${err2.message}` };
  }
}
__name(toolListPendingResults, "toolListPendingResults");
__name2(toolListPendingResults, "toolListPendingResults");
function buildTaskResult(taskId, data, artifact, run) {
  const raw = data && typeof data === "object" && !Array.isArray(data) ? data : {};
  const result = {
    task_id: taskId,
    status: data ? verifiedResultStatus(raw.status, run) : "pending",
    round: raw.round ?? 1,
    execution_summary: raw.execution_summary ?? raw.summary ?? "",
    commit: raw.commit ?? "",
    tests: raw.tests ?? "",
    artifacts: raw.artifacts ?? raw.changed_files ?? [],
    execution_result_json: data ?? null,
    evidence: {
      ...raw.evidence ?? {
        artifact: {
          name: `execution_result-${taskId}`,
          id: artifact?.id ?? null,
          file: RESULT_FILENAME
        },
        validation: {
          artifact_found: Boolean(artifact),
          result_loaded: Boolean(data),
          task_id_matches: Boolean(data && raw.task_id === taskId)
        }
      },
      workflow_run: run ?? null
    }
  };
  if (raw.summary !== void 0) result.summary = raw.summary;
  return result;
}
__name(buildTaskResult, "buildTaskResult");
__name2(buildTaskResult, "buildTaskResult");
async function toolGetTaskResult(env, args) {
  const taskId = String(args.task_id ?? "");
  if (!taskId) return { isError: true, text: "INVALID_INPUT: task_id required" };
  let artifact;
  try {
    artifact = await findArtifact(env, `execution_result-${taskId}`);
  } catch (err2) {
    return { isError: true, text: `GITHUB_READ_FAILED: ${err2.message}` };
  }
  if (!artifact) {
    const result2 = buildTaskResult(taskId, null, null);
    return { isError: false, text: JSON.stringify(result2), structuredContent: result2 };
  }
  let data;
  try {
    data = await downloadArtifactJson(env, artifact.id);
  } catch (err2) {
    return { isError: true, text: `GITHUB_READ_FAILED: ${err2.message}` };
  }
  if (data.task_id !== taskId) return { isError: true, text: "TASK_ID_MISMATCH" };
  let run;
  try {
    run = await getArtifactWorkflowRun(env, artifact);
  } catch (err2) {
    return { isError: true, text: `GITHUB_READ_FAILED: ${err2.message}` };
  }
  const result = buildTaskResult(taskId, data, artifact, run);
  return { isError: false, text: JSON.stringify(result), structuredContent: result };
}
__name(toolGetTaskResult, "toolGetTaskResult");
__name2(toolGetTaskResult, "toolGetTaskResult");
function assetSubtype(row, content) {
  if (content && typeof content.subtype === "string" && content.subtype.trim()) return content.subtype.trim();
  return ASSET_SUBTYPE_SCHEMA[String(row.schema_version || "")] || null;
}
__name(assetSubtype, "assetSubtype");
__name2(assetSubtype, "assetSubtype");
var BLOCKED_READ_KEY = /(?:^|_)(?:path|source_db|decrypted_dir|media_root|key|token|secret|credential|password|authorization|database|db_path|raw_metadata)(?:$|_)/i;
function safeAssetRead(value, key = "", depth = 0) {
  if (depth > 12) return null;
  if (key && BLOCKED_READ_KEY.test(key)) return void 0;
  if (typeof value === "string") {
    if (/(?:^[A-Za-z]:[\\/]|^\\\\|^file:\/\/)/i.test(value)) return "[REDACTED]";
    return value;
  }
  if (Array.isArray(value)) return value.map((entry) => safeAssetRead(entry, "", depth + 1)).filter((entry) => entry !== void 0);
  if (value && typeof value === "object") {
    const out = {};
    for (const [childKey, childValue] of Object.entries(value)) {
      const cleaned = safeAssetRead(childValue, childKey, depth + 1);
      if (cleaned !== void 0) out[childKey] = cleaned;
    }
    return out;
  }
  return value;
}
__name(safeAssetRead, "safeAssetRead");
__name2(safeAssetRead, "safeAssetRead");
function parseAssetJson(value) {
  try {
    return JSON.parse(String(value));
  } catch {
    return String(value);
  }
}
__name(parseAssetJson, "parseAssetJson");
__name2(parseAssetJson, "parseAssetJson");
function readAssetMetadata(row) {
  const parsed = parseAssetJson(row.content);
  return {
    asset_id: row.asset_id,
    asset_type: row.asset_type,
    subtype: assetSubtype(row, parsed),
    title: row.title,
    current_version: row.current_version,
    content_hash: row.content_hash,
    updated_at: row.updated_at
  };
}
__name(readAssetMetadata, "readAssetMetadata");
__name2(readAssetMetadata, "readAssetMetadata");
async function toolSearchAssets(env, args) {
  if (!env.ASSET_DB) return { isError: true, text: "ASSET_READ_UNAVAILABLE" };
  const typeInput = String(args.asset_type ?? "").trim().toUpperCase();
  if (typeInput && !ASSET_TYPES.has(typeInput)) return { isError: true, text: "INVALID_ASSET_TYPE" };
  const subtype = String(args.subtype ?? "").trim().slice(0, 120);
  const query = String(args.query ?? "").trim().slice(0, 200);
  const limit = Math.min(Math.max(Number(args.limit) || 20, 1), 100);
  const like = query ? `%${query.replace(/[\\%_]/g, "\\$&")}%` : "%";
  const result = await env.ASSET_DB.prepare(
    "SELECT asset_id,asset_type,schema_version,title,status,current_version,content_hash,updated_at, (SELECT content FROM asset_versions av WHERE av.asset_id=assets.asset_id AND av.version=assets.current_version) AS content FROM assets WHERE (? = '' OR asset_type = ?) AND (? = '%' OR title LIKE ? ESCAPE '\\' OR asset_id LIKE ? ESCAPE '\\') ORDER BY updated_at DESC LIMIT ?"
  ).bind(typeInput, typeInput, query ? query : "%", like, like, limit).all();
  const assets = (result.results || []).map(readAssetMetadata).filter((asset) => !subtype || asset.subtype === subtype).slice(0, limit);
  return { isError: false, text: JSON.stringify({ assets }), structuredContent: { assets } };
}
__name(toolSearchAssets, "toolSearchAssets");
__name2(toolSearchAssets, "toolSearchAssets");
async function toolGetAsset(env, args) {
  if (!env.ASSET_DB) return { isError: true, text: "ASSET_READ_UNAVAILABLE" };
  const assetId = String(args.asset_id ?? "").trim();
  if (!ASSET_ID_RE.test(assetId)) return { isError: true, text: "INVALID_ASSET_ID" };
  const row = await env.ASSET_DB.prepare(
    "SELECT a.asset_id,a.asset_type,a.schema_version,a.title,a.status,a.current_version,a.content_hash,a.updated_at, v.content,v.provenance,v.verification FROM assets a JOIN asset_versions v ON v.asset_id=a.asset_id AND v.version=a.current_version WHERE a.asset_id=?"
  ).bind(assetId).first();
  if (!row) return { isError: true, text: "ASSET_NOT_FOUND" };
  const rawContent = parseAssetJson(row.content);
  const content = safeAssetRead(rawContent);
  const provenance = safeAssetRead(parseAssetJson(row.provenance));
  const result = {
    asset_id: row.asset_id,
    asset_type: row.asset_type,
    subtype: assetSubtype(row, rawContent),
    version: row.current_version,
    content_hash: row.content_hash,
    provenance,
    content
  };
  return { isError: false, text: JSON.stringify(result), structuredContent: result };
}
__name(toolGetAsset, "toolGetAsset");
__name2(toolGetAsset, "toolGetAsset");
var TOOLS = [
  {
    name: "submit_task",
    description: "Submit a structured task to the Cloud Agent via GitHub repository_dispatch.",
    inputSchema: {
      type: "object",
      properties: {
        goal: { type: "string" },
        instructions: { type: "array", items: { type: "string" } },
        acceptance: { type: "array", items: { type: "string" } }
      },
      required: ["goal", "instructions", "acceptance"]
    }
  },
  {
    name: "get_task_result",
    description: "Read the execution_result.json produced by the Cloud Agent for a task_id.",
    inputSchema: {
      type: "object",
      properties: { task_id: { type: "string" } },
      required: ["task_id"]
    },
    outputSchema: {
      type: "object",
      properties: {
        task_id: { type: "string" },
        status: { type: "string" },
        round: { type: "number" },
        execution_summary: { type: "string" },
        commit: { type: "string" },
        tests: { type: ["string", "object", "array", "null"] },
        artifacts: { type: ["array", "object"] },
        execution_result_json: { type: ["object", "array", "null"] },
        evidence: { type: ["object", "array", "null"] }
      },
      additionalProperties: true
    }
  },
  {
    name: "list_pending_results",
    description: "List tasks that have finished and await review, plus failed and blocked tasks. Returns buckets pending_review / failed / blocked.",
    inputSchema: { type: "object", properties: {}, required: [] }
  },
  {
    name: "mark_reviewed",
    description: "Record a review verdict for a completed task and close its pending review state.",
    inputSchema: {
      type: "object",
      properties: {
        task_id: { type: "string" },
        verdict: { type: "string", enum: REVIEW_VERDICTS },
        note: { type: ["string", "null"] }
      },
      required: ["task_id", "verdict"]
    },
    outputSchema: {
      type: "object",
      properties: {
        task_id: { type: "string" },
        reviewed: { type: "boolean" },
        verdict: { type: "string", enum: REVIEW_VERDICTS },
        reviewed_at: { type: "string" },
        review_event: { type: ["object", "null"] },
        idempotent: { type: "boolean" }
      },
      additionalProperties: true
    }
  },
  {
    name: "search_assets",
    description: "Search the Personal AI Cloud Asset canonical by type, subtype, and query. Read only; returns metadata without asset content.",
    inputSchema: {
      type: "object",
      properties: {
        asset_type: { type: "string", description: "Canonical asset type: reality, decision, knowledge, or skill." },
        subtype: { type: "string" },
        query: { type: "string" },
        limit: { type: "integer", minimum: 1, maximum: 100 }
      },
      required: []
    },
    outputSchema: {
      type: "object",
      properties: { assets: { type: "array" } },
      additionalProperties: false
    }
  },
  {
    name: "get_asset",
    description: "Read one canonical Personal AI Cloud Asset by asset_id. Read only; returns the current version, provenance, and canonical content.",
    inputSchema: {
      type: "object",
      properties: { asset_id: { type: "string" } },
      required: ["asset_id"]
    }
  }
];
async function handleMcp(request, env, cors, auth) {
  let message;
  try {
    message = await request.json();
  } catch {
    return json({ jsonrpc: "2.0", id: null, error: { code: -32700, message: "Parse error" } }, 400, cors);
  }
  const { id = null, method, params = {} } = message || {};
  if (method && method.startsWith("notifications/")) return new Response(null, { status: 202, headers: cors });
  const ok = /* @__PURE__ */ __name2((result) => json({ jsonrpc: "2.0", id, result }, 200, cors), "ok");
  const fail = /* @__PURE__ */ __name2((code, message2) => json({ jsonrpc: "2.0", id, error: { code, message: message2 } }, 200, cors), "fail");
  switch (method) {
    case "initialize":
      return ok({
        protocolVersion: params.protocolVersion || PROTOCOL_VERSION,
        capabilities: { tools: { listChanged: false } },
        serverInfo: { name: "personal-ai-execution", version: "0.1" }
      });
    case "ping":
      return ok({});
    case "tools/list":
      return ok({ tools: TOOLS });
    case "tools/call": {
      const name = params.name;
      const args = params.arguments || {};
      let outcome;
      if (name === "submit_task") {
        if (!hasWriteScope(auth)) return fail(-32002, "mcp scope required");
        outcome = await toolSubmitTask(env, args);
      } else if (name === "get_task_result") {
        if (!hasWriteScope(auth)) return fail(-32002, "mcp scope required");
        outcome = await toolGetTaskResult(env, args);
      } else if (name === "list_pending_results") {
        if (!hasWriteScope(auth)) return fail(-32002, "mcp scope required");
        outcome = await toolListPendingResults(env, args);
      } else if (name === "mark_reviewed") {
        if (!hasWriteScope(auth)) return fail(-32002, "mcp scope required");
        outcome = await toolMarkReviewed(env, args);
      } else if (name === "search_assets") {
        if (!hasReadScope(auth)) return fail(-32001, "asset.read scope required");
        outcome = await toolSearchAssets(env, args);
      } else if (name === "get_asset") {
        if (!hasReadScope(auth)) return fail(-32001, "asset.read scope required");
        outcome = await toolGetAsset(env, args);
      } else return fail(-32602, `unknown tool: ${name}`);
      const toolResult = { content: [{ type: "text", text: outcome.text }], isError: outcome.isError };
      if (outcome.structuredContent !== void 0) toolResult.structuredContent = outcome.structuredContent;
      return ok(toolResult);
    }
    default:
      return fail(-32601, `method not found: ${method}`);
  }
}
__name(handleMcp, "handleMcp");
__name2(handleMcp, "handleMcp");
var index_default = {
  async fetch(request, env) {
    const cors = corsHeaders();
    const url = new URL(request.url);
    const origin = originOf(request);
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });
    if (url.pathname === "/.well-known/oauth-protected-resource" || url.pathname === "/.well-known/oauth-protected-resource/mcp") {
      return json(protectedResourceMetadata(origin), 200, cors);
    }
    if (url.pathname === "/.well-known/oauth-authorization-server") {
      return json(authorizationServerMetadata(origin), 200, cors);
    }
    if (url.pathname === "/register" && request.method === "POST") return registerClient(request, env, origin);
    if (url.pathname === "/authorize" && request.method === "GET") return authorizeGet(request, env);
    if (url.pathname === "/authorize" && request.method === "POST") return authorizePost(request, env);
    if (url.pathname === "/token" && request.method === "POST") return tokenEndpoint(request, env);
    if (url.pathname === "/healthz") {
      return json({ status: "ok", name: "personal-ai-execution-mcp", version: "0.2" }, 200, cors);
    }
    if (url.pathname === "/mcp") {
      if (request.method !== "POST") {
        return new Response("Method Not Allowed", { status: 405, headers: { ...cors, Allow: "POST" } });
      }
      const auth = await mcpAuthorized(request, env);
      if (!auth) return unauthorized(origin);
      return handleMcp(request, env, cors, auth);
    }
    return json({ error: "NOT_FOUND" }, 404, cors);
  }
};
export {
  index_default as default
};
//# sourceMappingURL=index.js.map
