import { useState, useEffect, useRef } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

function App() {
  const [connected, setConnected] = useState(false)
  const [sensorData, setSensorData] = useState({
    temp_c: null,
    humidity_pct: null,
    light_lux: null,
    battery_mv: null,
    rssi: null,
    seq: null,
  })
  const [stats, setStats] = useState({
    received: 0,
    expected: 0,
    prr: 100.0,
    button_count: 0,
  })
  const [rssiHistory, setRssiHistory] = useState([])
  const [devices, setDevices] = useState([])
  const [logs, setLogs] = useState([])
  const [command, setCommand] = useState('')
  const [commandHistory, setCommandHistory] = useState([])
  const [historyIndex, setHistoryIndex] = useState(-1)
  const wsRef = useRef(null)
  const logContainerRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    const connect = () => {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsUrl = `${protocol}//${window.location.host}/ws`

      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        setConnected(true)
        addLog('system', 'Connected to backend')
      }

      ws.onclose = () => {
        setConnected(false)
        addLog('system', 'Disconnected - reconnecting...')
        setTimeout(connect, 2000)
      }

      ws.onerror = () => {
        ws.close()
      }

      ws.onmessage = (event) => {
        const msg = JSON.parse(event.data)
        handleMessage(msg)
      }
    }

    connect()

    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [])

  const addLog = (type, message) => {
    const timestamp = new Date().toLocaleTimeString()
    setLogs(prev => [...prev.slice(-100), { type, message, timestamp }])
  }

  const handleMessage = (msg) => {
    switch (msg.type) {
      case 'init':
        // Restore state from backend on connect/reconnect
        if (msg.latest) {
          setSensorData(prev => ({
            ...prev,
            temp_c: msg.latest.temp_c ?? prev.temp_c,
            humidity_pct: msg.latest.humidity_pct ?? prev.humidity_pct,
            light_lux: msg.latest.light_lux ?? prev.light_lux,
            battery_mv: msg.latest.battery_mv ?? prev.battery_mv,
            rssi: msg.latest.rssi ?? prev.rssi,
            seq: msg.latest.seq ?? prev.seq,
          }))
        }
        if (msg.stats) {
          setStats(msg.stats)
        }
        if (msg.rssi_history) {
          setRssiHistory(msg.rssi_history)
        }
        if (msg.devices) {
          setDevices(msg.devices)
        }
        addLog('system', 'State restored from backend')
        break

      case 'keepalive':
        setSensorData(prev => ({
          ...prev,
          temp_c: msg.temp_c ?? prev.temp_c,
          humidity_pct: msg.humidity_pct ?? prev.humidity_pct,
          light_lux: msg.light_lux ?? prev.light_lux,
          battery_mv: msg.battery_mv ?? prev.battery_mv,
          rssi: msg.rssi ?? prev.rssi,
          seq: msg.seq ?? prev.seq,
        }))
        if (msg.stats) {
          setStats(msg.stats)
        }
        if (msg.rssi !== null && msg.rssi !== undefined) {
          setRssiHistory(prev => [...prev.slice(-59), { seq: msg.seq, rssi: msg.rssi }])
        }
        addLog('keepalive', `Keepalive seq=${msg.seq} rssi=${msg.rssi}dBm PRR=${msg.stats?.prr ?? '--'}%`)
        break

      case 'button':
        if (msg.stats) {
          setStats(msg.stats)
        }
        addLog('button', `Button ${msg.button_id} pressed (seq=${msg.seq})`)
        break

      case 'ack':
        if (msg.stats) {
          setStats(msg.stats)
        }
        addLog('ack', `ACK seq=${msg.seq} rssi=${msg.rssi}dBm`)
        break

      case 'route':
        if (msg.devices) {
          setDevices(msg.devices)
        }
        addLog('route', `Device: ${msg.route?.address}${msg.route?.is_root ? ' (root)' : ''}`)
        break

      case 'log':
        addLog('log', msg.message)
        break

      case 'error':
        addLog('error', msg.message)
        break

      default:
        addLog('log', JSON.stringify(msg))
    }
  }

  // Auto-scroll logs
  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight
    }
  }, [logs])

  // Auto-refresh routes every 30s
  useEffect(() => {
    if (!connected) return
    const interval = setInterval(() => {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ cmd: 'routes' }))
      }
    }, 30000)
    return () => clearInterval(interval)
  }, [connected])

  const sendCommand = (cmd) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN && cmd.trim()) {
      wsRef.current.send(JSON.stringify({ cmd: 'send', text: cmd.trim() }))
      addLog('cmd', `> ${cmd.trim()}`)
      setCommandHistory(prev => [...prev, cmd.trim()])
      setHistoryIndex(-1)
      setCommand('')
    }
  }

  const requestRoutes = () => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ cmd: 'routes' }))
      addLog('cmd', '> routes')
    }
  }

  const shortenAddr = (addr) => {
    if (!addr) return '--'
    const parts = addr.split(':')
    return parts.slice(-2).join(':')
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      sendCommand(command)
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      if (commandHistory.length > 0) {
        const newIndex = historyIndex < commandHistory.length - 1 ? historyIndex + 1 : historyIndex
        setHistoryIndex(newIndex)
        setCommand(commandHistory[commandHistory.length - 1 - newIndex] || '')
      }
    } else if (e.key === 'ArrowDown') {
      e.preventDefault()
      if (historyIndex > 0) {
        const newIndex = historyIndex - 1
        setHistoryIndex(newIndex)
        setCommand(commandHistory[commandHistory.length - 1 - newIndex] || '')
      } else {
        setHistoryIndex(-1)
        setCommand('')
      }
    }
  }

  const formatValue = (value, decimals = 1) => {
    if (value === null || value === undefined) return '--'
    return Number(value).toFixed(decimals)
  }

  return (
    <div className="app">
      <header>
        <h1>DroneCom</h1>
        <div className="status">
          <span className={`status-dot ${connected ? 'connected' : ''}`}></span>
          <span>{connected ? 'Connected' : 'Disconnected'}</span>
        </div>
      </header>

      <div className="dashboard">
        <div className="card temp">
          <h2>Temperature</h2>
          <span className="value">{formatValue(sensorData.temp_c)}</span>
          <span className="unit">°C</span>
        </div>

        <div className="card humidity">
          <h2>Humidity</h2>
          <span className="value">{formatValue(sensorData.humidity_pct)}</span>
          <span className="unit">%</span>
        </div>

        <div className="card light">
          <h2>Light</h2>
          <span className="value">{formatValue(sensorData.light_lux, 0)}</span>
          <span className="unit">lux</span>
        </div>

        <div className="card battery">
          <h2>Battery</h2>
          <span className="value">{formatValue(sensorData.battery_mv ? sensorData.battery_mv / 1000 : null, 2)}</span>
          <span className="unit">V</span>
        </div>

        <div className="card rssi">
          <h2>RSSI</h2>
          <span className="value">{formatValue(sensorData.rssi, 0)}</span>
          <span className="unit">dBm</span>
        </div>

        <div className="card prr">
          <h2>Packet Reception</h2>
          <span className="value">{formatValue(stats.prr, 1)}</span>
          <span className="unit">%</span>
          <div className="stats-detail">
            {stats.received}/{stats.expected} packets
          </div>
        </div>

        <div className="card buttons">
          <h2>Button Presses</h2>
          <span className="value">{stats.button_count}</span>
        </div>
      </div>

      <div className="devices-section">
        <div className="section-header">
          <h2>Devices ({devices.length})</h2>
          <button onClick={requestRoutes} disabled={!connected}>Refresh</button>
        </div>
        {devices.length > 0 ? (
          <table className="devices-table">
            <thead>
              <tr>
                <th>Address</th>
                <th>Parent</th>
                <th>Lifetime</th>
                <th>Role</th>
              </tr>
            </thead>
            <tbody>
              {devices.map((device, i) => (
                <tr key={i} className={device.is_root ? 'root' : ''}>
                  <td title={device.address}>{shortenAddr(device.address)}</td>
                  <td title={device.parent}>{shortenAddr(device.parent)}</td>
                  <td>{device.lifetime === -1 ? '∞' : `${device.lifetime}s`}</td>
                  <td>{device.is_root ? 'Root (connected)' : 'Node'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="no-devices">No devices. Click Refresh to query routes.</p>
        )}
      </div>

      <div className="chart-section">
        <h2>RSSI Over Time</h2>
        <div className="chart-container">
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={rssiHistory} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#333" />
              <XAxis
                dataKey="seq"
                stroke="#888"
                tick={{ fill: '#888', fontSize: 12 }}
              />
              <YAxis
                domain={[-100, -20]}
                stroke="#888"
                tick={{ fill: '#888', fontSize: 12 }}
                tickFormatter={(v) => `${v}`}
              />
              <Tooltip
                contentStyle={{ background: '#16213e', border: '1px solid #333', borderRadius: '8px' }}
                labelStyle={{ color: '#888' }}
                formatter={(value) => [`${value} dBm`, 'RSSI']}
              />
              <Line
                type="monotone"
                dataKey="rssi"
                stroke="#ab47bc"
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="log-section">
        <h2>Event Log</h2>
        <div className="log-container" ref={logContainerRef}>
          {logs.map((log, i) => (
            <div key={i} className={`log-entry ${log.type}`}>
              <span className="timestamp">{log.timestamp}</span>
              {log.message}
            </div>
          ))}
        </div>
        <div className="terminal-input">
          <span className="prompt">&gt;</span>
          <input
            ref={inputRef}
            type="text"
            value={command}
            onChange={(e) => setCommand(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type command (help, interval, log, routes, etc.)"
            disabled={!connected}
          />
          <button onClick={() => sendCommand(command)} disabled={!connected}>
            Send
          </button>
        </div>
      </div>
    </div>
  )
}

export default App
