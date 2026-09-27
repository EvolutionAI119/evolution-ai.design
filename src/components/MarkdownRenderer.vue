<template>
  <div class="markdown-renderer" v-html="renderedMarkdown"></div>
</template>

<script setup>
import { computed } from 'vue'
import MarkdownIt from 'markdown-it'
import * as markdownItEmoji from 'markdown-it-emoji'

const props = defineProps({
  content: {
    type: String,
    default: ''
  }
})

const md = new MarkdownIt({
  html: true,
  breaks: true,
  linkify: true
}).use(markdownItEmoji.full)

const stripFrontmatter = (text) => {
  const frontmatterRegex = /^---\s*\n([\s\S]*?)\n---\s*\n/
  return text.replace(frontmatterRegex, '')
}

const renderedMarkdown = computed(() => {
  let content = props.content || '# No Content\n\nNo markdown content available.'
  content = stripFrontmatter(content)
  return md.render(content)
})
</script>

<style scoped>
.markdown-renderer {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  line-height: 1.8;
  color: var(--text-primary);
  padding: 24px;
}

.markdown-renderer h1 {
  font-size: 24px;
  font-weight: 700;
  margin: 24px 0 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border-color);
}

.markdown-renderer h2 {
  font-size: 20px;
  font-weight: 600;
  margin: 20px 0 12px;
}

.markdown-renderer h3 {
  font-size: 16px;
  font-weight: 600;
  margin: 16px 0 8px;
}

.markdown-renderer h4,
.markdown-renderer h5,
.markdown-renderer h6 {
  font-size: 14px;
  font-weight: 600;
  margin: 12px 0 8px;
}

.markdown-renderer p {
  margin: 8px 0;
}

.markdown-renderer strong {
  font-weight: 600;
  color: var(--accent);
}

.markdown-renderer em {
  font-style: italic;
}

.markdown-renderer code {
  background: var(--accent-bg);
  color: var(--accent);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Fira Code', 'Consolas', monospace;
  font-size: 0.9em;
}

.markdown-renderer pre {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 16px;
  overflow-x: auto;
  margin: 12px 0;
}

.markdown-renderer pre code {
  background: transparent;
  padding: 0;
  color: var(--text-primary);
  font-size: 13px;
  line-height: 1.5;
}

.markdown-renderer ul,
.markdown-renderer ol {
  padding-left: 24px;
  margin: 8px 0;
}

.markdown-renderer li {
  margin: 4px 0;
}

.markdown-renderer li > ul,
.markdown-renderer li > ol {
  padding-left: 16px;
  margin: 4px 0;
}

.markdown-renderer a {
  color: var(--accent);
  text-decoration: none;
}

.markdown-renderer a:hover {
  text-decoration: underline;
}

.markdown-renderer hr {
  border: none;
  border-top: 1px solid var(--border-color);
  margin: 24px 0;
}

.markdown-renderer blockquote {
  border-left: 4px solid var(--accent);
  padding: 8px 16px;
  margin: 12px 0;
  background: var(--accent-bg);
  border-radius: 0 8px 8px 0;
  color: var(--text-secondary);
}

.markdown-renderer blockquote p {
  margin: 4px 0;
}

.markdown-renderer table {
  width: 100%;
  border-collapse: collapse;
  margin: 16px 0;
  font-size: 14px;
}

.markdown-renderer th,
.markdown-renderer td {
  border: 1px solid var(--border-color);
  padding: 10px 14px;
  text-align: left;
}

.markdown-renderer th {
  background: var(--bg-secondary);
  font-weight: 600;
  color: var(--text-primary);
}

.markdown-renderer tr:nth-child(even) {
  background: rgba(255, 255, 255, 0.02);
}

.markdown-renderer tr:hover {
  background: var(--accent-bg);
}

.markdown-renderer img {
  max-width: 100%;
  border-radius: 8px;
}

.markdown-renderer .emoji {
  font-size: 1.2em;
  line-height: 1;
}
</style>