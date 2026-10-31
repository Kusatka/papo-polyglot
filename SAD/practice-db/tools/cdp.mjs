// Управление окном Brave/Chromium, запущенным с --remote-debugging-port, через Chrome DevTools Protocol.
// Без сторонних пакетов: Node 22+ (глобальные fetch и WebSocket).
//   node cdp.mjs nav <url>                 перейти и дождаться загрузки
//   node cdp.mjs wait <css> [мс]           дождаться видимого элемента
//   node cdp.mjs waittext <текст> [мс]     дождаться текста на странице
//   node cdp.mjs click <css>               щёлкнуть по элементу (настоящими событиями мыши)
//   node cdp.mjs clicktext <текст> [css]   щёлкнуть по самому вложенному видимому элементу с этим текстом
//   node cdp.mjs dblclicktext <текст> [css]
//   node cdp.mjs type <текст>              вставить текст в элемент с фокусом
//   node cdp.mjs key <Enter|Tab|Escape|a|...> [ctrl|shift|alt|ctrl+shift]
//   node cdp.mjs eval <js>                 выполнить JS и вывести результат
//   node cdp.mjs png <файл>                снимок области страницы (для самопроверки, не для отчёта)
//   node cdp.mjs only                      оставить одну вкладку
//   node cdp.mjs park [x y]                увести мышь страницы в сторону
const port = process.env.CDP_PORT || 9222;
const [cmd, ...args] = process.argv.slice(2);

const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
const page = targets.find(t => t.type === 'page' && /^(https?|about|chrome|brave|file):/.test(t.url) && !t.url.startsWith('chrome-extension'));
if (!page) { console.error('нет вкладки'); process.exit(2); }
const ws = new WebSocket(page.webSocketDebuggerUrl);
let seq = 0; const pending = new Map();
ws.onmessage = e => { const m = JSON.parse(e.data); if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
  // диалоги beforeunload/confirm блокируют страницу — сразу подтверждаем
  if (m.method === 'Page.javascriptDialogOpening') ws.send(JSON.stringify({ id: 999999, method: 'Page.handleJavaScriptDialog', params: { accept: true } })); };
await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
const send = (method, params = {}) => new Promise((res, rej) => {
  const i = ++seq; pending.set(i, m => m.error ? rej(new Error(method + ': ' + JSON.stringify(m.error))) : res(m.result));
  ws.send(JSON.stringify({ id: i, method, params }));
});
const evaluate = async expr => {
  const r = await send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true, userGesture: true });
  if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text);
  return r.result.value;
};
const sleep = ms => new Promise(r => setTimeout(r, ms));
async function poll(fn, timeout = 20000, what = '') {
  const t0 = Date.now();
  while (Date.now() - t0 < timeout) { try { if (await fn()) return true; } catch {} await sleep(300); }
  throw new Error('не дождался: ' + what);
}
const VIS = `(el => { if (!el) return false; const r = el.getBoundingClientRect(); const s = getComputedStyle(el);
  return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none'; })`;
const FIND_TEXT = (text, scope) => `(() => {
  const want = ${JSON.stringify(text)}; const vis = ${VIS};
  const all = [...document.querySelectorAll(${JSON.stringify(scope || '*')})].filter(el => vis(el));
  const norm = s => (s || '').replace(/\\s+/g, ' ').trim();
  let c = all.filter(el => norm(el.innerText) === want);
  if (!c.length) c = all.filter(el => norm(el.innerText).includes(want));
  c = c.filter(el => ![...el.children].some(ch => c.includes(ch)));
  return c[0] || null; })()`;

async function clickAt(exprEl, count = 1) {
  const box = await evaluate(`(() => { const el = ${exprEl}; if (!el) return null; el.scrollIntoView({block: 'center', inline: 'center'});
    const r = el.getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; })()`);
  if (!box) throw new Error('элемент не найден');
  await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: box.x, y: box.y });
  for (let i = 1; i <= count; i++) {
    await send('Input.dispatchMouseEvent', { type: 'mousePressed', x: box.x, y: box.y, button: 'left', clickCount: i });
    await send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: box.x, y: box.y, button: 'left', clickCount: i });
  }
  return box;
}

const KEYS = { Enter: [13, 'Enter', '\r'], Tab: [9, 'Tab', ''], Escape: [27, 'Escape', ''], Backspace: [8, 'Backspace', ''],
  ArrowDown: [40, 'ArrowDown', ''], ArrowUp: [38, 'ArrowUp', ''], ArrowRight: [39, 'ArrowRight', ''], End: [35, 'End', ''], Home: [36, 'Home', ''] };
async function key(name, mods = '') {
  const m = (mods.includes('alt') ? 1 : 0) | (mods.includes('ctrl') ? 2 : 0) | (mods.includes('shift') ? 8 : 0);
  let vk, code, text;
  if (KEYS[name]) [vk, code, text] = KEYS[name];
  else { vk = name.toUpperCase().charCodeAt(0); code = 'Key' + name.toUpperCase(); text = m & 2 ? '' : name; }
  await send('Input.dispatchKeyEvent', { type: m & 2 || !text ? 'rawKeyDown' : 'keyDown', key: name, code, windowsVirtualKeyCode: vk, modifiers: m, text: m & 2 ? undefined : text });
  await send('Input.dispatchKeyEvent', { type: 'keyUp', key: name, code, windowsVirtualKeyCode: vk, modifiers: m });
}

try {
  switch (cmd) {
    case 'nav':
      await send('Page.enable');
      await send('Page.navigate', { url: args[0] });
      await sleep(500);
      await poll(() => evaluate('document.readyState === "complete"'), 30000, 'загрузка');
      console.log('ok', await evaluate('location.href'));
      break;
    case 'wait':
      await poll(() => evaluate(`${VIS}(document.querySelector(${JSON.stringify(args[0])}))`), +args[1] || 20000, args[0]);
      console.log('ok'); break;
    case 'waittext':
      await poll(() => evaluate(`document.body.innerText.includes(${JSON.stringify(args[0])})`), +args[1] || 20000, args[0]);
      console.log('ok'); break;
    case 'click':
      console.log('ok', JSON.stringify(await clickAt(`document.querySelector(${JSON.stringify(args[0])})`))); break;
    case 'clicktext':
      console.log('ok', JSON.stringify(await clickAt(FIND_TEXT(args[0], args[1])))); break;
    case 'dblclicktext':
      console.log('ok', JSON.stringify(await clickAt(FIND_TEXT(args[0], args[1]), 2))); break;
    case 'type':
      await send('Input.insertText', { text: args[0] }); console.log('ok'); break;
    case 'key':
      await key(args[0], args[1] || ''); console.log('ok'); break;
    case 'eval':
      console.log(JSON.stringify(await evaluate(args[0]), null, 1)); break;
    case 'park': {   // увести мышь страницы в пустое место, чтобы не было подсветки и строки ссылки внизу
      const v = await evaluate('[innerWidth, innerHeight]');
      await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: +args[0] || v[0] - 8, y: +args[1] || Math.round(v[1] * 0.6) });
      console.log('ok'); break;
    }
    case 'shotel': {   // PNG элемента страницы в повышенном разрешении: shotel <css> <файл> [масштаб]
      const box = await evaluate(`(() => { const e = document.querySelector(${JSON.stringify(args[0])}); if (!e) return null;
        const r = e.getBoundingClientRect(); return { x: r.left + scrollX, y: r.top + scrollY, width: r.width, height: r.height }; })()`);
      if (!box) throw new Error('элемент не найден');
      const r = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true,
        clip: { x: box.x - 12, y: box.y - 12, width: box.width + 24, height: box.height + 24, scale: +args[2] || 2 } });
      (await import('node:fs')).writeFileSync(args[1], Buffer.from(r.data, 'base64'));
      console.log('ok', args[1], Math.round(box.width), 'x', Math.round(box.height)); break;
    }
    case 'svgpng': {   // SVG-элемент → PNG через canvas в нужном масштабе: svgpng <css> <файл> [масштаб]
      const url = await evaluate(`(async () => { const s = document.querySelector(${JSON.stringify(args[0])}); const k = ${+args[2] || 2};
        const img = new Image(); img.src = 'data:image/svg+xml;base64,' + btoa(unescape(encodeURIComponent(new XMLSerializer().serializeToString(s))));
        await img.decode(); const c = document.createElement('canvas'); c.width = s.width.baseVal.value * k; c.height = s.height.baseVal.value * k;
        const g = c.getContext('2d'); g.scale(k, k); g.drawImage(img, 0, 0); return c.toDataURL('image/png'); })()`);
      (await import('node:fs')).writeFileSync(args[1], Buffer.from(url.split(',')[1], 'base64'));
      console.log('ok', args[1]); break;
    }
    case 'clickxy': {   // щелчок по координатам области страницы
      const [x, y] = [+args[0], +args[1]];
      await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x, y });
      await send('Input.dispatchMouseEvent', { type: 'mousePressed', x, y, button: 'left', clickCount: 1 });
      await send('Input.dispatchMouseEvent', { type: 'mouseReleased', x, y, button: 'left', clickCount: 1 });
      console.log('ok'); break;
    }
    case 'only': {   // закрыть все вкладки, кроме текущей
      for (const t of targets.filter(t => t.type === 'page' && t.id !== page.id)) await fetch(`http://127.0.0.1:${port}/json/close/${t.id}`);
      console.log('ok'); break;
    }
    case 'png': {
      const r = await send('Page.captureScreenshot', { format: 'png' });
      (await import('node:fs')).writeFileSync(args[0], Buffer.from(r.data, 'base64')); console.log('ok', args[0]); break;
    }
    default: console.error('неизвестная команда', cmd); process.exitCode = 2;
  }
} catch (e) { console.error('ОШИБКА', e.message); process.exitCode = 1; }
ws.close();
