export type SseHandler = (type: string, payload: string) => void

export interface SseConnection {
  close: () => void
}

/**
 * 连接 SSE 进度流，解析消息格式 "TYPE:payload" 或 "TYPE"
 */
export function connectSse(taskId: string, onMessage: SseHandler, onError?: () => void): SseConnection {
  const es = new EventSource(`/api/article/progress/${taskId}`, { withCredentials: true })

  es.onmessage = (event: MessageEvent) => {
    const raw: string = event.data
    const colonIdx = raw.indexOf(':')
    if (colonIdx === -1) {
      onMessage(raw, '')
    } else {
      const type = raw.slice(0, colonIdx)
      const payload = raw.slice(colonIdx + 1)
      onMessage(type, payload)
    }
  }

  es.onerror = () => {
    es.close()
    onError?.()
  }

  return { close: () => es.close() }
}
