import { useState, useEffect, useRef } from 'react'
import './Demo.css'

function Demo() {
  const [connected, setConnected] = useState(false)
  const [rssi, setRssi] = useState(null)
  const [stats, setStats] = useState({ received: 0, expected: 0 })
  const [lastPacketTime, setLastPacketTime] = useState(null)
  const [packetsDelayed, setPacketsDelayed] = useState(false)
  const wsRef = useRef(null)

  // Set demo-specific body styles
  useEffect(() => {
    document.body.classList.add('demo-body')
    return () => document.body.classList.remove('demo-body')
  }, [])

  // Check for delayed packets every second
  useEffect(() => {
    const interval = setInterval(() => {
      if (lastPacketTime && Date.now() - lastPacketTime > 15000) {
        setPacketsDelayed(true)
      } else {
        setPacketsDelayed(false)
      }
    }, 1000)
    return () => clearInterval(interval)
  }, [lastPacketTime])

  useEffect(() => {
    const connect = () => {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsUrl = `${protocol}//${window.location.host}/ws`

      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => setConnected(true)
      ws.onclose = () => {
        setConnected(false)
        setTimeout(connect, 2000)
      }
      ws.onerror = () => ws.close()
      ws.onmessage = (event) => {
        const msg = JSON.parse(event.data)
        handleMessage(msg)
      }
    }

    connect()
    return () => wsRef.current?.close()
  }, [])

  const handleMessage = (msg) => {
    if (msg.type === 'init') {
      if (msg.stats) setStats(msg.stats)
      if (msg.latest?.rssi !== undefined) setRssi(msg.latest.rssi)
      setLastPacketTime(Date.now())
    } else if (msg.type === 'keepalive' || msg.type === 'button' || msg.type === 'ack') {
      if (msg.stats) setStats(msg.stats)
      if (msg.rssi !== undefined) setRssi(msg.rssi)
      setLastPacketTime(Date.now())
    }
  }

  const packetLoss = stats.expected - stats.received
  const rssiGood = rssi !== null && rssi >= -70
  const lossGood = packetLoss <= 2

  return (
    <div className="demo-frame">
      <h1 className="demo-title">
        RISE Connectivity Demo<br/>
        on <span className="subgig">SubGHz</span> Network
      </h1>

      <div className="demo-dash">
        <div className="demo-header">
          <div className="demo-connection-status">
            <span className={`demo-status-dot ${connected ? 'connected' : ''}`}></span>
            <span>{connected ? 'Connected' : 'Disconnected'}</span>
          </div>
        </div>
        <div className="demo-cards">

          <section className="demo-card">
            <h2>RSSI Measurements</h2>
            <div className="demo-blackbox-large">
              <div className="demo-value">{rssi ?? '--'}</div>
              <div className="demo-unit">dBm</div>
            </div>
            <div className={`demo-pill ${rssiGood ? 'green' : 'red'}`}>
              {rssi === null ? 'Waiting...' : rssiGood ? 'Good Signal' : 'Weak Signal'}
            </div>
          </section>

          <section className="demo-card">
            <h2>Packet Loss</h2>
            <div className="demo-blackbox-large">
              <div className="demo-value">{stats.expected > 0 ? packetLoss : '--'}</div>
              <div className="demo-unit">Packets Lost</div>
            </div>
            <div className={`demo-pill ${packetsDelayed ? 'red warning' : lossGood ? 'green' : 'red'}`}>
              {packetsDelayed ? 'Packets delayed - probable loss' : stats.expected === 0 ? 'Waiting...' : lossGood ? 'Good' : 'Requires Attention'}
            </div>
          </section>

        </div>
      </div>
    </div>
  )
}

export default Demo
