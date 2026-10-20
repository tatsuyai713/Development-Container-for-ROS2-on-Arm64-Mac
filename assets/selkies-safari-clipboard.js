// project-safari-clipboard-v1
// Based on the clipboard toolbar in tatsuyai713/kde-selkies-webtop-devcontainer
// (files/ubuntu-root/usr/local/bin/patch-selkies-safari-keyboard.py, GPL-3.0).
(() => {
  if (!/^((?!chrome|chromium|android|edg).)*safari/i.test(navigator.userAgent) ||
      globalThis.__projectSafariClipboard) return;
  globalThis.__projectSafariClipboard = true;
  let serverText = null;
  let assist = null;
  let previousFocus = null;
  const origin = location.origin;
  const input = () => window.webrtcInput;
  function releaseRemoteKeys() {
    const remote = input();
    remote?.resetKeyboard?.();
    // Also release keys sent by an older keyboard-assist/Guacamole handler.
    if (typeof remote?.send === 'function') remote.send('kr');
  }
  function remoteShortcut(key) {
    const remote = input();
    if (!remote || typeof remote._sendKeyEvent !== 'function') return;
    // A physical Command key may already have been forwarded as Alt.
    for (const [code, symbol] of Object.entries(remote._keyDownList || {})) {
      if (/^(Meta|Control)/.test(code)) remote._sendKeyEvent(symbol, code, false);
    }
    remote._sendKeyEvent(65507, 'ControlLeft', true);
    remote._sendKeyEvent(key.charCodeAt(0), 'Key' + key.toUpperCase(), true);
    remote._sendKeyEvent(key.charCodeAt(0), 'Key' + key.toUpperCase(), false);
    remote._sendKeyEvent(65507, 'ControlLeft', false);
  }
  // Called by the core only after sending clipboard data on its WebSocket.
  globalThis.__projectPasteRemote = () => remoteShortcut('v');
  function send(text) {
    if (typeof text !== 'string') return;
    window.postMessage({type: 'clipboardUpdateFromUI', text, paste: true}, origin);
  }
  let status;
  function showStatus(message) {
    if (status) status.textContent = message;
  }
  function clipboardError() {
    showStatus(window.isSecureContext === false
      ? 'Clipboard access requires HTTPS.'
      : 'Clipboard access denied. Allow clipboard access in Safari.');
  }
  // Cache server text directly, independently of Safari's automatic writes.
  globalThis.__projectReceiveClipboard = text => { serverText = String(text); };
  // Safari may reject an automatic clipboard write outside a user gesture.
  // Remember the remote text before that write, so the explicit Copy button
  // still works. Keep the original promise and its permission semantics.
  if (navigator.clipboard && navigator.clipboard.writeText) {
    const write = navigator.clipboard.writeText.bind(navigator.clipboard);
    try {
      navigator.clipboard.writeText = text => {
        serverText = String(text);
        return write(text);
      };
    } catch (_) { /* The core also publishes clipboardContentUpdate. */ }
  }
  window.addEventListener('message', event => {
    if (event.origin !== origin || event.source !== window) return;
    if (event.data?.type === 'clipboardContentUpdate' && typeof event.data.text === 'string') {
      serverText = event.data.text;
    }
  });
  function isRemoteTarget(target) {
    return target instanceof Element && !!target.closest(
      '#overlayInput, #keyboard-input-assist, #project-safari-paste, canvas');
  }
  // Intercept only native paste. Ordinary keys and IME belong to Selkies.
  // Register on window before the core's capture listener, so Cmd+V never
  // reaches the remote session before the clipboard contents do.
  window.addEventListener('keydown', event => {
    if (!isRemoteTarget(event.target) || event.isComposing || event.keyCode === 229) return;
    if (assist && (event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'v') {
      releaseRemoteKeys();
      previousFocus = document.activeElement;
      assist.focus({preventScroll: true});
      event.stopImmediatePropagation();
    }
  }, true);
  document.addEventListener('paste', event => {
    if (!assist || !isRemoteTarget(event.target) || !event.clipboardData) return;
    if (!Array.from(event.clipboardData.types).includes('text/plain')) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    send(event.clipboardData.getData('text/plain'));
    assist.value = '';
    if (previousFocus?.isConnected) previousFocus.focus({preventScroll: true});
  }, true);
  window.addEventListener('keyup', event => {
    if (event.target === assist && (event.key === 'Meta' || event.key === 'Control') &&
        previousFocus?.isConnected) previousFocus.focus({preventScroll: true});
  }, true);
  document.addEventListener('focusin', event => {
    if (!isRemoteTarget(event.target)) releaseRemoteKeys();
  }, true);
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) releaseRemoteKeys();
  });
  function focusRemoteKeyboard() {
    const remote = input();
    if (!remote || remote.isSharedMode) return;
    // Safari needs an editable input. The WebRTC overlay is readonly, and
    // pointerdown focus is undone by the browser's default mousedown focus.
    const field = document.getElementById('keyboard-input-assist') ||
      document.getElementById('overlayInput');
    field?.focus({preventScroll: true});
  }
  function focusAfterClick(event) {
    if (!isRemoteTarget(event.target)) return;
    focusRemoteKeyboard();
    // Run after the default focus action, without preventing the remote click.
    setTimeout(focusRemoteKeyboard, 0);
  }
  document.addEventListener('pointerdown', focusAfterClick, true);
  document.addEventListener('mousedown', focusAfterClick, true);
  window.addEventListener('focus', () => {
    const active = document.activeElement;
    if (isRemoteTarget(active) || active === document.body) focusRemoteKeyboard();
  });
  window.addEventListener('blur', releaseRemoteKeys);
  window.addEventListener('pagehide', releaseRemoteKeys);
  function bind() {
    if (document.getElementById('safari-clipboard-toolbar')) return;
    const bar = document.createElement('div');
    bar.id = 'safari-clipboard-toolbar';
    bar.addEventListener('mousedown', event => event.preventDefault());
    bar.setAttribute('aria-label', 'Session clipboard');
    bar.style.cssText = 'position:fixed;right:10px;bottom:48px;z-index:9999;display:flex;gap:8px;padding:6px;background:rgba(0,0,0,.65);border-radius:6px;font:12px sans-serif';
    const paste = document.createElement('button');
    paste.type = 'button';
    paste.setAttribute('class', 'allow-native-input');
    paste.textContent = 'Paste: Mac → Container';
    paste.addEventListener('click', () => {
      releaseRemoteKeys();
      if (navigator.clipboard?.readText) {
        navigator.clipboard.readText().then(text => { send(text); showStatus(''); }).catch(clipboardError);
      } else clipboardError();
    });
    const copy = document.createElement('button');
    copy.type = 'button';
    copy.setAttribute('class', 'allow-native-input');
    copy.textContent = 'Copy: Container → Mac';
    copy.addEventListener('click', () => {
      releaseRemoteKeys();
      if (serverText === null) {
        showStatus('Copy text in the remote application first.');
        return;
      }
      const text = serverText;
      const fallback = () => {
        const field = document.createElement('textarea');
        field.value = text;
        field.readOnly = true;
        document.body.appendChild(field);
        field.select();
        let copied = false;
        try { copied = document.execCommand('copy'); } catch (_) { /* Report failure without opening a dialog. */ }
        field.remove();
        if (!copied) clipboardError();
        else showStatus('');
      };
      if (navigator.clipboard?.writeText) navigator.clipboard.writeText(text).then(() => showStatus('')).catch(fallback);
      else fallback();
    });
    status = document.createElement('span');
    status.setAttribute('role', 'status');
    status.setAttribute('aria-live', 'polite');
    bar.append(paste, copy, status);
    document.body.appendChild(bar);

    // Let Safari deliver a real paste event instead of requiring permission
    // to read the clipboard on focus. Do not intercept sidebar/form fields.
    assist = document.createElement('textarea');
    assist.id = 'project-safari-paste';
    assist.setAttribute('class', 'allow-native-input');
    assist.setAttribute('aria-label', 'Remote paste input');
    assist.tabIndex = -1;
    assist.style.cssText = 'position:fixed;left:-1000px;top:0;width:1px;height:1px;opacity:0';
    document.body.appendChild(assist);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', bind, {once: true});
  else bind();
})();
