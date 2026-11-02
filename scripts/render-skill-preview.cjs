const fs = require('fs');
const MarkdownIt = require('markdown-it');
const md = new MarkdownIt({ html: true, linkify: true });
const src = fs.readFileSync('.trae/skills/troubleshoot-i18n-deploy/SKILL.md', 'utf8')
  .replace(/^---[\s\S]*?---/, '');
const body = md.render(src);
const css = 'body{max-width:860px;margin:40px auto;padding:0 24px;font-family:"Segoe UI","Microsoft YaHei",sans-serif;color:#1a1a1a;line-height:1.75}'
  + 'h1{border-bottom:2px solid #4F6BED;padding-bottom:8px}'
  + 'h2{border-bottom:1px solid #ddd;padding-bottom:4px;margin-top:36px}'
  + 'table{border-collapse:collapse;width:100%;margin:12px 0}'
  + 'th,td{border:1px solid #ccc;padding:8px 10px;text-align:left;font-size:14px}'
  + 'th{background:#f2f4f8}'
  + 'code{background:#f4f4f4;padding:2px 6px;border-radius:4px;font-family:Consolas,monospace;font-size:13px}'
  + 'pre{background:#2d2d2d;color:#f8f8f2;padding:16px;border-radius:8px;overflow-x:auto}'
  + 'pre code{background:none;color:inherit;padding:0}'
  + 'blockquote{border-left:4px solid #4F6BED;margin:0;padding:4px 16px;background:#f7f9ff;color:#444}';
const html = '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">'
  + '<title>troubleshoot-i18n-deploy · SKILL 预览</title>'
  + '<style>' + css + '</style></head><body>' + body + '</body></html>';
fs.writeFileSync('docs/skill-troubleshoot-i18n-deploy-preview.html', html);
console.log('written');
