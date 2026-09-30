// SVG → PNG 批量转换（.cjs 强制 CommonJS；sharp 自带 librsvg，无需系统 cairo）
// 用法：需已在 %TEMP%\svgconv 执行 npm install sharp，然后 node svg_to_png.cjs
// （sharp 按脚本位置解析模块，故用 createRequire 显式指向安装目录）
// 按需修改 NAMES 列表；中文版源 docs/images，英文版源 docs/images/en。
const { createRequire } = require('module');
const fs = require('fs');
const path = require('path');
const os = require('os');

const SHARP_ROOT = path.join(os.tmpdir(), 'svgconv');
const localRequire = createRequire(path.join(SHARP_ROOT, 'node_modules', 'sharp'));
const sharp = localRequire('sharp');

const REPO = 'D:/API/Evolution-Ai.Design';
const NAMES = [
  'whitepaper-arch', 'paper-nurbs-pipeline', 'arch-dataflow',
  'product-journey', 'method-pipeline', 'integration-flow',
  'validation-metrics', 'api-lifecycle', 'meta-10dims',
];
const DENSITY = 200;

(async () => {
  for (const lang of ['cn', 'en']) {
    const srcDir = lang === 'en'
      ? path.join(REPO, 'docs/images/en')
      : path.join(REPO, 'docs/images');
    const outDir = path.join(os.tmpdir(), 'svgconv', lang);
    fs.mkdirSync(outDir, { recursive: true });
    for (const name of NAMES) {
      const src = path.join(srcDir, name + '.svg');
      const dst = path.join(outDir, name + '.png');
      await sharp(src, { density: DENSITY }).png().toFile(dst);
      console.log(lang, name, '->', dst);
    }
  }
})();
