'use client'

export function createAuthenticatedWebSocket(
  url: string,
  token: string
): WebSocket {
  const wsUrl = `${url}?token=${token}`
  const ws = new WebSocket(wsUrl)
  
  ws.onopen = () => {
    console.log('WebSocket connected')
  }
  
  ws.onerror = (error) => {
    console.error('WebSocket error:', error)
  }
  
  ws.onclose = (event) => {
    console.log('WebSocket disconnected:', event.code, event.reason)
  }
  
  return ws
}





