// project-hardware-decoder-v1
// Select a decoder using the actual Annex B SPS, not a guessed profile/level.
(() => {
  if (globalThis.ProjectVideoDecoder || !globalThis.VideoDecoder) return;
  const NativeDecoder = globalThis.VideoDecoder;
  // A resized canvas loses its pixels, including stripes which are currently
  // static. Ask for a complete set of keyframes after layout has settled.
  if (typeof window !== 'undefined' && typeof document !== 'undefined') {
    let refreshTimer;
    const refresh = () => {
      clearTimeout(refreshTimer);
      refreshTimer = setTimeout(() => {
        if (document.hidden) return;
        const canvas = document.getElementById('videoCanvas');
        if (!canvas || !canvas.width || !canvas.height) return;
        try { window.webrtcInput?.send('REFRESH_VIDEO'); } catch (_) {}
      }, 600);
    };
    window.addEventListener('resize', refresh);
    window.visualViewport?.addEventListener('resize', refresh);
    document.addEventListener('fullscreenchange', refresh);
    document.addEventListener('visibilitychange', refresh);
    if (typeof MutationObserver !== 'undefined') {
      new MutationObserver(records => {
        if (records.some(record => record.target.id === 'videoCanvas' &&
            ['width', 'height'].includes(record.attributeName))) refresh();
      }).observe(document.documentElement, {subtree: true, attributes: true,
        attributeFilter: ['width', 'height']});
    }
  }
  function codecFromChunk(chunk, fallback) {
    const data = new Uint8Array(chunk.byteLength);
    chunk.copyTo(data);
    for (let i = 0; i + 6 < data.length; i++) {
      if (data[i] === 0 && data[i + 1] === 0 && data[i + 2] === 1 &&
          (data[i + 3] & 31) === 7) {
        return 'avc1.' + Array.from(data.slice(i + 4, i + 7),
          value => value.toString(16).padStart(2, '0')).join('');
      }
    }
    return fallback;
  }
  globalThis.ProjectVideoDecoder = class extends EventTarget {
    static async isConfigSupported(config) {
      // Selkies probes before receiving an SPS. Defer AVC capability probing
      // until the first key frame provides its real profile and level.
      if (/^avc[13]\./i.test(config.codec)) {
        return {supported: true, config: {...config}};
      }
      return NativeDecoder.isConfigSupported(config);
    }
    constructor(options) {
      super();
      this.options = options;
      this.status = 'unconfigured';
      this.epoch = 0;
      this.pending = [];
      this.ready = null;
      this.selected = false;
      this.decoder = new NativeDecoder({
        output: options.output,
        error: error => this.fail(error)
      });
      this.decoder.addEventListener('dequeue', () => {
        const event = new Event('dequeue');
        this.dispatchEvent(event);
        if (this.ondequeue) this.ondequeue(event);
      });
    }
    get state() { return this.status; }
    get decodeQueueSize() { return this.pending.length + this.decoder.decodeQueueSize; }
    configure(config) {
      if (this.status === 'closed') throw new DOMException('Decoder is closed', 'InvalidStateError');
      this.epoch++;
      this.decoder.reset();
      this.config = {...config};
      this.pending = [];
      this.ready = null;
      this.selected = false;
      this.status = 'configured';
    }
    decode(chunk) {
      if (this.status !== 'configured') throw new DOMException('Decoder is not configured', 'InvalidStateError');
      if (this.selected) { this.decoder.decode(chunk); return; }
      if (this.pending.length >= 120) {
        this.fail(new DOMException('Decoder startup queue is full', 'QuotaExceededError'));
        return;
      }
      this.pending.push(chunk);
      if (!this.ready) {
        const epoch = this.epoch;
        const config = {...this.config, codec: codecFromChunk(chunk, this.config.codec)};
        this.ready = this.prepare(config, epoch).catch(error => {
          if (this.epoch === epoch && this.status !== 'closed') this.fail(error);
        });
      }
    }
    async prepare(config, epoch) {
      for (const preference of ['prefer-hardware', 'no-preference', 'prefer-software']) {
        const candidate = {...config, hardwareAcceleration: preference};
        let support;
        try { support = await NativeDecoder.isConfigSupported(candidate); }
        catch (_) { continue; }
        if (this.epoch !== epoch || this.status === 'closed') return;
        if (!support.supported) continue;
        try { this.decoder.configure(candidate); } catch (_) { continue; }
        this.selected = true;
        console.info('[Selkies decoder]', config.codec, preference);
        const pending = this.pending;
        this.pending = [];
        for (const chunk of pending) this.decoder.decode(chunk);
        return;
      }
      throw new DOMException('No decoder supports ' + config.codec, 'NotSupportedError');
    }
    async flush() {
      if (this.status !== 'configured') throw new DOMException('Decoder is not configured', 'InvalidStateError');
      if (this.ready) await this.ready;
      if (this.selected) await this.decoder.flush();
    }
    reset() {
      if (this.status === 'closed') throw new DOMException('Decoder is closed', 'InvalidStateError');
      this.epoch++;
      this.pending = [];
      this.ready = null;
      this.selected = false;
      this.status = 'unconfigured';
      this.decoder.reset();
    }
    close() {
      this.epoch++;
      this.pending = [];
      this.status = 'closed';
      if (this.decoder.state !== 'closed') this.decoder.close();
    }
    fail(error) {
      this.close();
      this.options.error(error);
    }
  };
})();
