const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

async function main() {
  const input = process.argv[2];
  const outDir = process.argv[3];
  if (!input || !outDir) throw new Error('Usage: node render_docx_preview.js input.docx output_dir');
  fs.mkdirSync(outDir, { recursive: true });
  const buf = fs.readFileSync(input);
  const b64 = buf.toString('base64');
  const zipScript = path.resolve(__dirname, 'node_modules/jszip/dist/jszip.min.js');
  const previewScript = path.resolve(__dirname, 'node_modules/docx-preview/dist/docx-preview.min.js');
  const browser = await chromium.launch({
    headless: true,
    executablePath: 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
  });
  try {
    const page = await browser.newPage({ viewport: { width: 1500, height: 2000 }, deviceScaleFactor: 1 });
    await page.setContent(`<!doctype html><html><head><meta charset="utf-8"><style>
      body { margin: 0; background: #d9dde1; }
      #container { padding: 28px 0; }
      .docx-wrapper { background: #d9dde1 !important; padding: 0 !important; }
      .docx-wrapper > section.docx { margin: 0 auto 28px auto !important; box-shadow: 0 2px 12px rgba(0,0,0,.18); }
    </style></head><body><div id="container"></div></body></html>`);
    await page.addScriptTag({ path: zipScript });
    await page.addScriptTag({ path: previewScript });
    await page.evaluate(async (base64) => {
      const bytes = Uint8Array.from(atob(base64), c => c.charCodeAt(0));
      await window.docx.renderAsync(bytes.buffer, document.getElementById('container'), null, {
        className: 'docx', inWrapper: true, ignoreWidth: false, ignoreHeight: false,
        ignoreFonts: false, breakPages: true, renderHeaders: true, renderFooters: true,
        renderFootnotes: true, renderEndnotes: true, useBase64URL: true
      });
    }, b64);
    await page.evaluate(() => document.fonts.ready);
    await page.waitForTimeout(1000);
    const pages = page.locator('.docx-wrapper > section.docx');
    const count = await pages.count();
    for (let i = 0; i < count; i++) {
      await pages.nth(i).screenshot({ path: path.join(outDir, `page-${String(i + 1).padStart(2, '0')}.png`) });
    }
    fs.writeFileSync(path.join(outDir, 'page-count.txt'), String(count));
    console.log(`Rendered ${count} pages`);
  } finally {
    await browser.close();
  }
}

main().catch(err => { console.error(err); process.exit(1); });
