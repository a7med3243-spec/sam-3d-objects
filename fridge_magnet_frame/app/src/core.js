// ===== Nameplate geometry core =====
// Builds a watertight plate mesh: the verified plate body (embedded) with the
// text merged into its flat top face. No CSG: the top face is re-triangulated
// around the text outline, text walls and caps are added.
// Units: mm. Plate coords: back face z=0, front face z=ztop (4.4), text on top.
var NP = (function () {
  'use strict';

  function b64ToBytes(b64) {
    var s = atob(b64), out = new Uint8Array(s.length);
    for (var i = 0; i < s.length; i++) out[i] = s.charCodeAt(i);
    return out;
  }
  function decodeBase(g) {
    var pos = new Float32Array(b64ToBytes(g.pos).buffer);
    var idx = new Uint16Array(b64ToBytes(g.idx).buffer);
    var loopIdx = new Uint16Array(b64ToBytes(g.loop).buffer);
    var loop = [];
    for (var i = 0; i < loopIdx.length; i++) loop.push([pos[loopIdx[i] * 3], pos[loopIdx[i] * 3 + 1]]);
    return { pos: pos, idx: idx, loop: loop, ztop: pos[loopIdx[0] * 3 + 2] };
  }

  function area(r) {
    var a = 0;
    for (var i = 0; i < r.length; i++) { var p = r[i], q = r[(i + 1) % r.length]; a += p[0] * q[1] - q[0] * p[1]; }
    return a / 2;
  }
  function inside(pt, r) {             // even-odd point in polygon
    var c = false;
    for (var i = 0, j = r.length - 1; i < r.length; j = i++) {
      var a = r[i], b = r[j];
      if (((a[1] > pt[1]) !== (b[1] > pt[1])) && (pt[0] < (b[0] - a[0]) * (pt[1] - a[1]) / (b[1] - a[1]) + a[0])) c = !c;
    }
    return c;
  }
  // drop repeated and collinear points (the triangulator would drop them too,
  // leaving T-junctions against the walls)
  function clean(r) {
    var out = r.slice(), changed = true;
    while (changed && out.length > 3) {
      changed = false;
      for (var i = 0; i < out.length && out.length > 3; i++) {
        var p = out[(i + out.length - 1) % out.length], q = out[i], n = out[(i + 1) % out.length];
        var dup = Math.abs(q[0] - p[0]) < 1e-7 && Math.abs(q[1] - p[1]) < 1e-7;
        var cr = (q[0] - p[0]) * (n[1] - q[1]) - (q[1] - p[1]) * (n[0] - q[0]);
        if (dup || Math.abs(cr) < 1e-10) { out.splice(i, 1); i--; changed = true; }
      }
    }
    return out;
  }
  // tiny deterministic jitter (0.00002 mm): text from fonts often has many points on
  // one exact line (a baseline); the triangulator merges those across letters
  var seed = 1;
  function jit() { seed = (seed * 16807) % 2147483647; return (seed / 2147483647 - 0.5) * 4e-5; }
  function jitter(r) { return r.map(function (p) { return [p[0] + jit(), p[1] + jit()]; }); }
  // exterior rings CCW, holes CW (solid on the left of every ring)
  function orient(polys) {
    seed = 1;
    return polys.map(function (p) {
      return p.map(function (r) { return clean(jitter(r)); }).filter(function (r) { return r.length >= 3 && Math.abs(area(r)) > 1e-4; });
    }).filter(function (p) { return p.length && p[0].length >= 3; }).map(function (p) {
      return p.map(function (r, k) {
        var ccw = area(r) > 0;
        return ((k === 0) === ccw) ? r : r.slice().reverse();
      });
    });
  }

  function Tri() { this.a = []; }
  Tri.prototype.push = function (p, q, r) { this.a.push(p[0], p[1], p[2], q[0], q[1], q[2], r[0], r[1], r[2]); };

  // triangulate a polygon (outer + holes) at height z, facing +z (up) or -z
  function cap(T, outer, holes, z, up) {
    var V2 = THREE.Vector2;
    var c = outer.map(function (p) { return new V2(p[0], p[1]); });
    var hs = holes.map(function (h) { return h.map(function (p) { return new V2(p[0], p[1]); }); });
    var faces = THREE.ShapeUtils.triangulateShape(c, hs);
    var all = outer.concat.apply(outer, holes);
    for (var i = 0; i < faces.length; i++) {
      var A = all[faces[i][0]], B = all[faces[i][1]], C = all[faces[i][2]];
      var s = (B[0] - A[0]) * (C[1] - A[1]) - (B[1] - A[1]) * (C[0] - A[0]);
      if (Math.abs(s) < 1e-12) continue;
      var flip = (s > 0) !== up;
      var a = [A[0], A[1], z], b = [B[0], B[1], z], cc = [C[0], C[1], z];
      if (flip) T.push(a, cc, b); else T.push(a, b, cc);
    }
  }
  // vertical walls of one ring between z0 and z1; outward = solid on the left of the ring
  function walls(T, ring, z0, z1, solidInside) {
    for (var i = 0; i < ring.length; i++) {
      var p = ring[i], q = ring[(i + 1) % ring.length];
      var b0 = [p[0], p[1], z0], b1 = [q[0], q[1], z0], t0 = [p[0], p[1], z1], t1 = [q[0], q[1], z1];
      if (solidInside) { T.push(b0, b1, t1); T.push(b0, t1, t0); }
      else { T.push(b0, t1, b1); T.push(b0, t0, t1); }
    }
  }
  // regions of the plate's top face that stay at ztop: the loop minus the text
  // outlines, plus the counters (holes of letters) minus anything nested in them
  function topFace(T, loop, polys, z) {
    var exts = polys.map(function (p) { return p[0]; });
    var topLevel = exts.filter(function (e, i) {
      return !polys.some(function (p, j) { return j !== i && p.slice(1).some(function (h) { return inside(e[0], h); }); });
    });
    cap(T, loop, topLevel, z, true);
    polys.forEach(function (p) {
      p.slice(1).forEach(function (h) {
        var nested = exts.filter(function (e) { return e !== p[0] && inside(e[0], h); });
        // keep only the outermost nested outlines
        nested = nested.filter(function (e) { return !nested.some(function (o) { return o !== e && inside(e[0], o); }); });
        cap(T, h, nested, z, true);
      });
    });
  }

  // mode: 'raised' | 'engraved' | 'none'; h: raised height or engraving depth
  function buildPlate(base, polys, mode, h, info) {
    var T = new Tri(), P = base.pos, I = base.idx, z = base.ztop;
    for (var i = 0; i < I.length; i += 3) {
      var a = I[i] * 3, b = I[i + 1] * 3, c = I[i + 2] * 3;
      T.push([P[a], P[a + 1], P[a + 2]], [P[b], P[b + 1], P[b + 2]], [P[c], P[c + 1], P[c + 2]]);
    }
    if (info) info.nBase = T.a.length / 9;
    polys = (mode === 'none') ? [] : orient(polys);
    topFace(T, base.loop, polys, z);
    if (info) info.nTop = T.a.length / 9 - info.nBase;
    polys.forEach(function (p) {
      if (mode === 'raised') {
        p.forEach(function (r) { walls(T, r, z, z + h, true); });
        cap(T, p[0], p.slice(1), z + h, true);
      } else if (mode === 'engraved') {
        p.forEach(function (r) { walls(T, r, z - h, z, false); });
        cap(T, p[0], p.slice(1), z - h, true);
      }
    });
    return new Float32Array(T.a);
  }
  // the raised text alone (for two-colour printing): closed solid from ztop to ztop+h
  function buildText(base, polys, h) {
    var T = new Tri(), z = base.ztop;
    orient(polys).forEach(function (p) {
      p.forEach(function (r) { walls(T, r, z, z + h, true); });
      cap(T, p[0], p.slice(1), z + h, true);
      cap(T, p[0], p.slice(1), z, false);
    });
    return new Float32Array(T.a);
  }

  // binary STL
  function stl(tris, name) {
    var n = tris.length / 9, buf = new ArrayBuffer(84 + n * 50), dv = new DataView(buf);
    var head = ('nameplate ' + (name || '')).slice(0, 79);
    for (var i = 0; i < head.length; i++) dv.setUint8(i, head.charCodeAt(i) & 127);
    dv.setUint32(80, n, true);
    for (var t = 0; t < n; t++) {
      var o = 84 + t * 50, k = t * 9;
      var ux = tris[k + 3] - tris[k], uy = tris[k + 4] - tris[k + 1], uz = tris[k + 5] - tris[k + 2];
      var vx = tris[k + 6] - tris[k], vy = tris[k + 7] - tris[k + 1], vz = tris[k + 8] - tris[k + 2];
      var nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx, l = Math.hypot(nx, ny, nz) || 1;
      dv.setFloat32(o, nx / l, true); dv.setFloat32(o + 4, ny / l, true); dv.setFloat32(o + 8, nz / l, true);
      for (var j = 0; j < 9; j++) dv.setFloat32(o + 12 + j * 4, tris[k + j], true);
    }
    return new Uint8Array(buf);
  }

  // minimal ZIP (stored, no compression)
  var CRC = (function () {
    var t = new Uint32Array(256);
    for (var n = 0; n < 256; n++) { var c = n; for (var k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1; t[n] = c >>> 0; }
    return t;
  })();
  function crc32(d) { var c = 0xFFFFFFFF; for (var i = 0; i < d.length; i++) c = CRC[(c ^ d[i]) & 255] ^ (c >>> 8); return (c ^ 0xFFFFFFFF) >>> 0; }
  function utf8(s) { return new TextEncoder().encode(s); }
  function zip(files) {            // files: [{name, data: Uint8Array}]
    var parts = [], central = [], offset = 0;
    files.forEach(function (f) {
      var name = utf8(f.name), crc = crc32(f.data), size = f.data.length;
      var lh = new DataView(new ArrayBuffer(30));
      lh.setUint32(0, 0x04034b50, true); lh.setUint16(4, 20, true); lh.setUint16(6, 0x0800, true);
      lh.setUint16(8, 0, true); lh.setUint16(10, 0, true); lh.setUint16(12, 0x21, true);
      lh.setUint32(14, crc, true); lh.setUint32(18, size, true); lh.setUint32(22, size, true);
      lh.setUint16(26, name.length, true); lh.setUint16(28, 0, true);
      parts.push(new Uint8Array(lh.buffer), name, f.data);
      var ch = new DataView(new ArrayBuffer(46));
      ch.setUint32(0, 0x02014b50, true); ch.setUint16(4, 20, true); ch.setUint16(6, 20, true); ch.setUint16(8, 0x0800, true);
      ch.setUint16(10, 0, true); ch.setUint16(12, 0, true); ch.setUint16(14, 0x21, true);
      ch.setUint32(16, crc, true); ch.setUint32(20, size, true); ch.setUint32(24, size, true);
      ch.setUint16(28, name.length, true); ch.setUint32(42, offset, true);
      central.push(new Uint8Array(ch.buffer), name);
      offset += 30 + name.length + size;
    });
    var cdSize = central.reduce(function (s, p) { return s + p.length; }, 0);
    var end = new DataView(new ArrayBuffer(22));
    end.setUint32(0, 0x06054b50, true); end.setUint16(8, files.length, true); end.setUint16(10, files.length, true);
    end.setUint32(12, cdSize, true); end.setUint32(16, offset, true);
    var all = parts.concat(central, [new Uint8Array(end.buffer)]);
    var total = all.reduce(function (s, p) { return s + p.length; }, 0), out = new Uint8Array(total), o = 0;
    all.forEach(function (p) { out.set(p, o); o += p.length; });
    return out;
  }

  return { decodeBase: decodeBase, buildPlate: buildPlate, buildText: buildText, stl: stl, zip: zip, area: area, orient: orient };
})();
if (typeof module !== 'undefined') module.exports = NP;
