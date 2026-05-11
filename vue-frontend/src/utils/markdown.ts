import { marked } from 'marked'

marked.setOptions({ async: false })

export function renderMarkdown(content: string): string {
  return marked(content) as string
}
