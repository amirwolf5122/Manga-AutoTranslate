var MtZip = (function () {
  'use strict'
  var T = null

  function crc32(u8) {
    if (!T) {
      T = new Uint32Array(256)
      for (var n = 0; n < 256; n++) {
        var c = n
        for (var k = 0; k < 8; k++) c = (c & 1) ? (3988292384 ^ (c >>> 1)) : (c >>> 1)
        T[n] = c >>> 0
      }
    }
    var c = 4294967295
    for (var i = 0; i < u8.length; i++) c = T[(c ^ u8[i]) & 255] ^ (c >>> 8)
    return (c ^ 4294967295) >>> 0
  }

  function dosDateTime() {
    var d = new Date()
    return {
      time: ((d.getHours() & 31) << 11) | ((d.getMinutes() & 63) << 5) | ((d.getSeconds() >> 1) & 31),
      date: (((d.getFullYear() - 1980) & 127) << 9) | (((d.getMonth() + 1) & 15) << 5) | (d.getDate() & 31)
    }
  }

  function MtZip() {
    this.items = []
  }

  MtZip.prototype.add = function (name, u8) {
    this.items.push({ name: String(name), data: u8, crc: crc32(u8), dt: dosDateTime() })
  }

  MtZip.prototype.build = function () {
    var enc = new TextEncoder()
    var parts = []
    var central = []
    var offset = 0
    var cdSize = 0
    for (var i = 0; i < this.items.length; i++) {
      var it = this.items[i]
      var nb = enc.encode(it.name)
      var lh = new DataView(new ArrayBuffer(30))
      lh.setUint32(0, 67324752, true)
      lh.setUint16(4, 20, true)
      lh.setUint16(6, 2048, true)
      lh.setUint16(8, 0, true)
      lh.setUint16(10, it.dt.time, true)
      lh.setUint16(12, it.dt.date, true)
      lh.setUint32(14, it.crc, true)
      lh.setUint32(18, it.data.length, true)
      lh.setUint32(22, it.data.length, true)
      lh.setUint16(26, nb.length, true)
      lh.setUint16(28, 0, true)
      parts.push(new Uint8Array(lh.buffer))
      parts.push(nb)
      parts.push(it.data)
      var ch = new DataView(new ArrayBuffer(46))
      ch.setUint32(0, 33639248, true)
      ch.setUint16(4, 20, true)
      ch.setUint16(6, 20, true)
      ch.setUint16(8, 2048, true)
      ch.setUint16(10, 0, true)
      ch.setUint16(12, it.dt.time, true)
      ch.setUint16(14, it.dt.date, true)
      ch.setUint32(16, it.crc, true)
      ch.setUint32(20, it.data.length, true)
      ch.setUint32(24, it.data.length, true)
      ch.setUint16(28, nb.length, true)
      ch.setUint16(30, 0, true)
      ch.setUint16(32, 0, true)
      ch.setUint16(34, 0, true)
      ch.setUint16(36, 0, true)
      ch.setUint32(38, 0, true)
      ch.setUint32(42, offset, true)
      central.push(new Uint8Array(ch.buffer))
      central.push(nb)
      offset += 30 + nb.length + it.data.length
    }
    for (var j = 0; j < central.length; j++) cdSize += central[j].length
    var eo = new DataView(new ArrayBuffer(22))
    eo.setUint32(0, 101010256, true)
    eo.setUint16(4, 0, true)
    eo.setUint16(6, 0, true)
    eo.setUint16(8, this.items.length, true)
    eo.setUint16(10, this.items.length, true)
    eo.setUint32(12, cdSize, true)
    eo.setUint32(16, offset, true)
    eo.setUint16(20, 0, true)
    parts.push.apply(parts, central)
    parts.push(new Uint8Array(eo.buffer))
    return new Blob(parts, { type: 'application/zip' })
  }

  return MtZip
})()
