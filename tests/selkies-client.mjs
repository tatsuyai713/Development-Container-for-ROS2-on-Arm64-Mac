import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const decoderSource = fs.readFileSync(new URL('../assets/selkies-hardware-decoder.js', import.meta.url), 'utf8');
function decoderContext(supports, probe = async config => ({supported: supports(config), config})) {
  const attempts = [], frames = [], errors = [];
  class Native extends EventTarget {
    static isConfigSupported(config) { attempts.push(config); return probe(config); }
    constructor(options) { super(); this.options = options; this.state = 'unconfigured'; this.decodeQueueSize = 0; }
    reset() { this.state = 'unconfigured'; }
    configure(config) { this.config = config; this.state = 'configured'; }
    decode(chunk) { frames.push(chunk); }
    async flush() {}
    close() { this.state = 'closed'; }
  }
  const scope = vm.createContext({VideoDecoder: Native, EventTarget, Event, DOMException, Uint8Array, console: {info() {}}});
  vm.runInContext(decoderSource, scope);
  const decoder = new scope.ProjectVideoDecoder({output() {}, error: error => errors.push(error)});
  return {decoder, attempts, frames, errors};
}
const chunk = {
  byteLength: 12,
  copyTo(bytes) { bytes.set([0, 0, 0, 1, 0x67, 0x64, 0x0c, 0x29, 0, 0, 1, 0x65]); }
};
for (const hardware of [true, false]) {
  const {decoder, attempts, frames, errors} = decoderContext(c => hardware || c.hardwareAcceleration !== 'prefer-hardware');
  decoder.configure({codec: 'avc1.7A003E'});
  decoder.decode(chunk);
  decoder.decode(chunk);
  await decoder.flush();
  assert.equal(frames.length, 2);
  assert.equal(attempts.at(-1).codec, 'avc1.640c29');
  assert.equal(attempts.at(-1).hardwareAcceleration, hardware ? 'prefer-hardware' : 'no-preference');
  assert.equal(errors.length, 0);
  decoder.close();
}
{
  const {decoder, errors} = decoderContext(() => false);
  decoder.configure({codec: 'avc1.7A003E'}); decoder.decode(chunk); await decoder.flush();
  assert.equal(errors[0].name, 'NotSupportedError');
  assert.equal(decoder.state, 'closed');
}
{
  let finish;
  const {decoder, frames} = decoderContext(() => true, config => new Promise(resolve => { finish = () => resolve({supported: true, config}); }));
  decoder.configure({codec: 'avc1.7A003E'}); decoder.decode(chunk); decoder.reset(); finish();
  await Promise.resolve(); await Promise.resolve();
  assert.equal(frames.length, 0);
  assert.equal(decoder.state, 'unconfigured');
}

const safariSource = fs.readFileSync(new URL('../assets/selkies-safari-clipboard.js', import.meta.url), 'utf8');
function clipboardContext({safari = true, denyRead = false, denyWrite = false} = {}) {
  const nodes = new Map(), messages = [], written = [], shortcuts = [], prompts = [], keyEvents = [];
  class Target {
    constructor() { this.listeners = new Map(); }
    addEventListener(type, callback) { const handlers = this.listeners.get(type) || []; handlers.push(callback); this.listeners.set(type, handlers); }
    fire(type, event = {}) { for (const callback of this.listeners.get(type) || []) callback(event); }
  }
  const document = new Target();
  class Element extends Target {
    constructor(tag) { super(); this.tag = tag; this.style = {}; this.value = ''; this.children = []; this.isConnected = true; }
    setAttribute() {}
    append(...items) { for (const item of items) { this.children.push(item); if (item.id) nodes.set(item.id, item); } }
    appendChild(item) { this.append(item); }
    closest() { return ['overlayInput', 'keyboard-input-assist', 'project-safari-paste'].includes(this.id) ? this : null; }
    focus() { document.activeElement = this; }
    select() {}
    remove() { this.isConnected = false; }
  }
  document.readyState = 'complete'; document.body = new Element('body');
  document.createElement = tag => new Element(tag); document.getElementById = id => nodes.get(id);
  document.execCommand = () => false;
  const window = new Target();
  window.postMessage = (data, origin) => messages.push({data, origin});
  window.prompt = (...args) => { prompts.push(args); return args.length === 1 ? '手動 paste' : null; };
  window.alert = () => {};
  window.webrtcInput = {
    _keyDownList: {}, _sendKeyEvent: (...args) => shortcuts.push(args),
    _handleKeyDown(event) { keyEvents.push(['down', event.code]); this._keyDownList[event.code] = event.keyCode; },
    _handleKeyUp(event) { keyEvents.push(['up', event.code]); delete this._keyDownList[event.code]; },
    resetKeyboard() { keyEvents.push(['reset']); this._keyDownList = {}; },
    send(message) { keyEvents.push(['send', message]); }
  };
  const navigator = {userAgent: safari ? 'Version/26.0 Safari/605.1.15' : 'Chrome/155.0 Safari/537.36', clipboard: {
    readText: async () => { if (denyRead) throw new DOMException('Denied', 'NotAllowedError'); return 'Mac 日本語'; },
    writeText: async text => { if (denyWrite) throw new DOMException('Denied', 'NotAllowedError'); written.push(text); }
  }};
  const scope = vm.createContext({window, document, navigator, location: {origin: 'https://localhost:60501'}, Element, console, setTimeout: callback => callback()});
  vm.runInContext(safariSource, scope);
  return {scope, window, document, navigator, nodes, messages, written, shortcuts, prompts, keyEvents};
}
const settle = async () => { for (let i = 0; i < 5; i++) await Promise.resolve(); };
{
  const c = clipboardContext(); const bar = c.nodes.get('safari-clipboard-toolbar');
  assert.equal(bar.children.length, 3);
  assert.equal(bar.children[0].textContent, 'Paste: Mac → Container');
  assert.equal(bar.children[1].textContent, 'Copy: Container → Mac');
  bar.children[0].fire('click'); await settle();
  assert.equal(c.messages[0].data.text, 'Mac 日本語'); assert.equal(c.messages[0].data.paste, true);
  await c.navigator.clipboard.writeText('Linux 日本語');
  bar.children[1].fire('click'); await settle(); assert.equal(c.written.at(-1), 'Linux 日本語');
  c.window.fire('message', {source: c.window, origin: 'https://evil.test', data: {type: 'clipboardContentUpdate', text: 'bad'}});
  bar.children[1].fire('click'); await settle(); assert.equal(c.written.at(-1), 'Linux 日本語');
  c.scope.__projectPasteRemote(); assert.equal(c.shortcuts.length, 4);
  const remote = c.document.createElement('canvas'); remote.id = 'overlayInput';
  c.document.fire('paste', {target: remote, clipboardData: {types: ['text/plain'], getData: () => 'native paste'}, preventDefault() {}, stopImmediatePropagation() {}});
  assert.equal(c.messages.at(-1).data.text, 'native paste');
  const before = c.messages.length;
  c.document.fire('paste', {target: c.document.createElement('textarea'), clipboardData: {types: ['text/plain'], getData: () => 'local form'}});
  assert.equal(c.messages.length, before);
}
{
  const c = clipboardContext({denyRead: true, denyWrite: true}); const bar = c.nodes.get('safari-clipboard-toolbar');
  bar.children[0].fire('click'); await settle();
  assert.equal(c.messages.length, 0);
  assert.equal(c.prompts.length, 0);
  assert.match(bar.children[2].textContent, /Clipboard access denied/);
  await c.navigator.clipboard.writeText('remote despite permission error').catch(() => {});
  bar.children[1].fire('click'); await settle(); assert.equal(c.prompts.length, 0);
  assert.match(bar.children[2].textContent, /Clipboard access denied/);
  c.scope.__projectReceiveClipboard('received directly');
  bar.children[1].fire('click'); await settle();
  assert.equal(c.prompts.length, 0);
}
assert.equal(clipboardContext({safari: false}).nodes.has('safari-clipboard-toolbar'), false);
{
  const c = clipboardContext();
  const remote = c.document.createElement('textarea'); remote.id = 'overlayInput';
  const event = extra => ({target: remote, key: 'a', code: 'KeyA', keyCode: 65,
    preventDefault() { this.prevented = true; },
    stopImmediatePropagation() { this.stopped = true; }, ...extra});
  // Model the real capture order: window (core), then document (toolbar).
  // The toolbar must never call the core handler a second time or swallow IME.
  for (const extra of [{}, {key: 'Enter', code: 'Enter', keyCode: 13},
                       {isComposing: true, keyCode: 229}, {repeat: true}]) {
    const down = event(extra);
    c.window.fire('keydown', down); c.document.fire('keydown', down);
    assert.equal(down.stopped, undefined);
    assert.equal(down.prevented, undefined);
  }
  assert.equal(c.keyEvents.length, 0, 'Toolbar must not forward ordinary keys itself');
  c.document.activeElement = remote;
  const paste = event({key: 'v', code: 'KeyV', metaKey: true});
  c.window.fire('keydown', paste);
  assert.equal(paste.stopped, true);
  assert.equal(paste.prevented, undefined, 'Safari must deliver its native paste event');
  assert.equal(c.document.activeElement.id, 'project-safari-paste');
  c.window.fire('blur');
  assert.ok(c.keyEvents.some(e => e[0] === 'send' && e[1] === 'kr'));
}
console.log('Decoder, Safari clipboard, and keyboard/IME non-interference checks passed.');

{
  const c = clipboardContext();
  const overlay = c.document.createElement('input'); overlay.id = 'overlayInput'; overlay.readOnly = true;
  const assist = c.document.createElement('input'); assist.id = 'keyboard-input-assist'; assist.readOnly = false;
  c.document.body.append(overlay, assist);
  c.document.fire('mousedown', {target: overlay});
  assert.equal(c.document.activeElement, assist, 'Safari must focus the editable keyboard assist, not the readonly WebRTC overlay');
  const local = c.document.createElement('textarea'); c.document.activeElement = local;
  c.document.fire('mousedown', {target: local});
  assert.equal(c.document.activeElement, local, 'Local form fields must keep focus');
}
