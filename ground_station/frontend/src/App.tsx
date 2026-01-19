import { useState, useEffect, useCallback, useRef } from 'react'

// Types
interface Position {
  x: number
  y: number
  heading: number
}

interface Velocity {
  linear: number
  angular: number
}

interface Battery {
  voltage: number
  current: number
  percent: number
}

interface Sensors {
  ir_left: number
  ir_right: number
  ultrasonic_cm: number
}

interface CSIPresence {
  state: 'CLEAR' | 'PRESENCE' | 'MOVEMENT' | 'APPROACHING' | 'RETREATING'
  confidence: number
  variance: number
  duration_ms: number
}

interface VehicleState {
  vehicle_id: string
  position: Position
  velocity: Velocity
  battery: Battery
  connection: {
    connected: boolean
    latency_ms: number
    rssi: number
  }
  mode: string
  armed: boolean
  motors: {
    left: number
    right: number
  }
  sensors: Sensors
  csi_presence?: CSIPresence
  system: {
    uptime_ms: number
    free_heap: number
    cpu_temp: number
  }
  telemetry: {
    sequence: number
    rate_hz: number
  }
  updated_at: string
}

interface EventLogEntry {
  timestamp: Date
  level: 'INFO' | 'WARNING' | 'ERROR'
  message: string
}

// WebSocket hook
function useWebSocket(url: string) {
  const [isConnected, setIsConnected] = useState(false)
  const [vehicleState, setVehicleState] = useState<VehicleState | null>(null)
  const [events, setEvents] = useState<EventLogEntry[]>([])
  const wsRef = useRef<WebSocket | null>(null)

  const addEvent = (level: EventLogEntry['level'], message: string) => {
    setEvents(prev => [...prev.slice(-99), { timestamp: new Date(), level, message }])
  }

  useEffect(() => {
    const connect = () => {
      const ws = new WebSocket(url)
      wsRef.current = ws

      ws.onopen = () => {
        console.log('[WS] Connected')
        setIsConnected(true)
        addEvent('INFO', 'Connected to ground station')
      }

      ws.onclose = () => {
        console.log('[WS] Disconnected')
        setIsConnected(false)
        addEvent('WARNING', 'Disconnected from ground station')
        setTimeout(connect, 3000)
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data.event === 'state_update') {
            setVehicleState(prev => {
              // Detect state changes for logging
              if (prev && data.state) {
                if (prev.armed !== data.state.armed) {
                  addEvent('INFO', data.state.armed ? 'Vehicle ARMED' : 'Vehicle DISARMED')
                }
                if (prev.mode !== data.state.mode) {
                  addEvent('INFO', `Mode changed to ${data.state.mode}`)
                }
                if (prev.csi_presence?.state !== data.state.csi_presence?.state) {
                  const csi = data.state.csi_presence
                  if (csi && csi.state !== 'CLEAR') {
                    addEvent(csi.state === 'APPROACHING' ? 'WARNING' : 'INFO',
                      `CSI: ${csi.state} (${(csi.confidence * 100).toFixed(0)}% confidence)`)
                  }
                }
                if (data.state.battery?.percent < 20 && prev.battery?.percent >= 20) {
                  addEvent('WARNING', 'Low battery warning')
                }
              }
              return data.state
            })
          } else if (data.event === 'initial_state') {
            const vehicles = data.vehicles
            const firstVehicle = Object.values(vehicles)[0] as VehicleState
            if (firstVehicle) {
              setVehicleState(firstVehicle)
              addEvent('INFO', `Vehicle ${firstVehicle.vehicle_id} state received`)
            }
          } else if (data.event === 'error') {
            addEvent('ERROR', data.message || 'Unknown error')
          }
        } catch (e) {
          console.error('[WS] Parse error:', e)
        }
      }

      ws.onerror = () => {
        addEvent('ERROR', 'WebSocket error')
      }
    }

    connect()
    addEvent('INFO', 'System initialized')

    return () => {
      wsRef.current?.close()
    }
  }, [url])

  return { isConnected, vehicleState, events }
}

// Send command helper
async function sendCommand(vehicleId: string, command: string, params: Record<string, unknown> = {}) {
  try {
    const response = await fetch(`/api/vehicles/${vehicleId}/command`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ command, params }),
    })
    return response.ok
  } catch (e) {
    console.error('Command failed:', e)
    return false
  }
}

// Components
function StatusIndicator({ connected }: { connected: boolean }) {
  return (
    <div className={`status-indicator ${connected ? 'connected' : 'disconnected'}`} />
  )
}

function DataDisplay({ label, value, unit }: { label: string; value: string | number; unit?: string }) {
  return (
    <div>
      <div className="data-label">{label}</div>
      <div className="flex items-baseline">
        <span className="data-value">{value}</span>
        {unit && <span className="data-unit">{unit}</span>}
      </div>
    </div>
  )
}

function BatteryGauge({ percent, voltage }: { percent: number; voltage: number }) {
  const color = percent > 50 ? 'bg-status-green' : percent > 20 ? 'bg-status-yellow' : 'bg-status-red'

  return (
    <div className="space-y-2">
      <div className="flex justify-between text-sm">
        <span>Battery</span>
        <span>{voltage.toFixed(1)}V</span>
      </div>
      <div className="h-4 bg-panel-border rounded overflow-hidden">
        <div
          className={`h-full ${color} transition-all duration-300`}
          style={{ width: `${percent}%` }}
        />
      </div>
      <div className="text-center text-2xl font-bold">{percent}%</div>
    </div>
  )
}

function ControlPanel({ vehicleId, armed, mode }: { vehicleId: string; armed: boolean; mode: string }) {
  const handleArm = () => sendCommand(vehicleId, armed ? 'DISARM' : 'ARM')
  const handleStop = () => sendCommand(vehicleId, 'STOP')
  const handleEmergency = () => sendCommand(vehicleId, 'SET_MODE', { mode: 'E_STOP' })

  const handleMove = useCallback((linear: number, angular: number) => {
    sendCommand(vehicleId, 'MOVE', { linear, angular })
  }, [vehicleId])

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        <button
          className={`btn flex-1 ${armed ? 'btn-danger' : 'btn-primary'}`}
          onClick={handleArm}
        >
          {armed ? 'DISARM' : 'ARM'}
        </button>
        <button className="btn btn-secondary flex-1" onClick={handleStop}>
          STOP
        </button>
      </div>

      <button
        className="btn btn-danger w-full py-4 text-lg font-bold"
        onClick={handleEmergency}
      >
        EMERGENCY STOP
      </button>

      {armed && mode === 'MANUAL' && (
        <div className="grid grid-cols-3 gap-2">
          <div />
          <button
            className="btn btn-secondary py-4"
            onMouseDown={() => handleMove(0.5, 0)}
            onMouseUp={() => handleMove(0, 0)}
            onMouseLeave={() => handleMove(0, 0)}
          >
            FWD
          </button>
          <div />
          <button
            className="btn btn-secondary py-4"
            onMouseDown={() => handleMove(0, -0.5)}
            onMouseUp={() => handleMove(0, 0)}
            onMouseLeave={() => handleMove(0, 0)}
          >
            LEFT
          </button>
          <button
            className="btn btn-secondary py-4"
            onMouseDown={() => handleMove(-0.5, 0)}
            onMouseUp={() => handleMove(0, 0)}
            onMouseLeave={() => handleMove(0, 0)}
          >
            REV
          </button>
          <button
            className="btn btn-secondary py-4"
            onMouseDown={() => handleMove(0, 0.5)}
            onMouseUp={() => handleMove(0, 0)}
            onMouseLeave={() => handleMove(0, 0)}
          >
            RIGHT
          </button>
        </div>
      )}
    </div>
  )
}

function ModeSelector({ vehicleId, currentMode }: { vehicleId: string; currentMode: string }) {
  const modes = ['STANDBY', 'MANUAL', 'AUTONOMOUS']

  return (
    <div className="flex gap-2">
      {modes.map((mode) => (
        <button
          key={mode}
          className={`btn flex-1 ${currentMode === mode ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => sendCommand(vehicleId, 'SET_MODE', { mode })}
        >
          {mode}
        </button>
      ))}
    </div>
  )
}

function SensorDisplay({ sensors }: { sensors: Sensors }) {
  return (
    <div className="grid grid-cols-3 gap-4 text-center">
      <div>
        <div className={`w-8 h-8 mx-auto rounded-full ${sensors.ir_left ? 'bg-status-green' : 'bg-status-red'}`} />
        <div className="text-xs mt-1">IR Left</div>
      </div>
      <div>
        <div className="text-2xl font-bold">{sensors.ultrasonic_cm.toFixed(0)}</div>
        <div className="text-xs">Distance (cm)</div>
      </div>
      <div>
        <div className={`w-8 h-8 mx-auto rounded-full ${sensors.ir_right ? 'bg-status-green' : 'bg-status-red'}`} />
        <div className="text-xs mt-1">IR Right</div>
      </div>
    </div>
  )
}

function CSIPresenceDisplay({ presence }: { presence?: CSIPresence }) {
  if (!presence) return null

  const stateColors: Record<string, string> = {
    CLEAR: 'bg-status-green',
    PRESENCE: 'bg-status-yellow',
    MOVEMENT: 'bg-status-yellow',
    APPROACHING: 'bg-status-red',
    RETREATING: 'bg-nasa-blue',
  }

  const stateIcons: Record<string, string> = {
    CLEAR: '✓',
    PRESENCE: '👤',
    MOVEMENT: '🚶',
    APPROACHING: '⚠️',
    RETREATING: '←',
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-2xl">{stateIcons[presence.state] || '?'}</span>
          <span className={`px-2 py-1 rounded text-sm font-medium ${stateColors[presence.state]} bg-opacity-20`}>
            {presence.state}
          </span>
        </div>
        <span className="text-lg font-bold">{(presence.confidence * 100).toFixed(0)}%</span>
      </div>
      <div className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <div className="text-text-secondary">Variance</div>
          <div className="font-mono">{presence.variance.toFixed(2)}</div>
        </div>
        <div>
          <div className="text-text-secondary">Duration</div>
          <div className="font-mono">{(presence.duration_ms / 1000).toFixed(1)}s</div>
        </div>
      </div>
    </div>
  )
}

function EventLog({ events }: { events: EventLogEntry[] }) {
  const logRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight
    }
  }, [events])

  const levelColors: Record<string, string> = {
    INFO: 'text-status-green',
    WARNING: 'text-status-yellow',
    ERROR: 'text-status-red',
  }

  return (
    <div ref={logRef} className="h-48 overflow-y-auto text-xs font-mono space-y-1">
      {events.map((event, i) => (
        <div key={i} className={levelColors[event.level]}>
          [{event.timestamp.toLocaleTimeString()}] {event.message}
        </div>
      ))}
      {events.length === 0 && (
        <div className="text-text-secondary">Waiting for events...</div>
      )}
    </div>
  )
}

function formatUptime(ms: number): string {
  const seconds = Math.floor(ms / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)

  if (hours > 0) {
    return `${hours}h ${minutes % 60}m`
  }
  return `${minutes}m ${seconds % 60}s`
}

// Main App
export default function App() {
  const wsUrl = `ws://${window.location.host}/ws/dashboard`
  const { isConnected, vehicleState, events } = useWebSocket(wsUrl)

  return (
    <div className="min-h-screen bg-space-black p-4">
      {/* Header */}
      <header className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <h1 className="text-xl font-bold tracking-wider">
            NEXUS TAURUS OPERATIONS
          </h1>
          <div className="flex items-center gap-2 text-sm text-text-secondary">
            <StatusIndicator connected={isConnected} />
            <span>{isConnected ? 'Connected' : 'Disconnected'}</span>
          </div>
        </div>
        <div className="text-sm text-text-secondary">
          Command Center v0.1.0
        </div>
      </header>

      {!vehicleState ? (
        <div className="flex items-center justify-center h-96">
          <div className="text-center">
            <div className="text-2xl mb-4">No Vehicle Connected</div>
            <div className="text-text-secondary">Waiting for TAURUS-01...</div>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Left Column - Status */}
          <div className="space-y-4">
            {/* Vehicle Info */}
            <div className="panel">
              <div className="panel-header">Vehicle Status</div>
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <StatusIndicator connected={vehicleState.connection.connected} />
                  <span className="text-lg font-semibold">{vehicleState.vehicle_id}</span>
                </div>
                <div className={`px-3 py-1 rounded text-sm font-medium ${
                  vehicleState.armed
                    ? 'bg-status-green/20 text-status-green'
                    : 'bg-panel-border text-text-secondary'
                }`}>
                  {vehicleState.armed ? 'ARMED' : 'DISARMED'}
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <DataDisplay label="Mode" value={vehicleState.mode} />
                <DataDisplay label="Uptime" value={formatUptime(vehicleState.system.uptime_ms)} />
                <DataDisplay label="RSSI" value={vehicleState.connection.rssi} unit="dBm" />
                <DataDisplay label="Telemetry" value={vehicleState.telemetry.rate_hz.toFixed(1)} unit="Hz" />
              </div>
            </div>

            {/* Battery */}
            <div className="panel">
              <div className="panel-header">Power</div>
              <BatteryGauge
                percent={vehicleState.battery.percent}
                voltage={vehicleState.battery.voltage}
              />
            </div>

            {/* System */}
            <div className="panel">
              <div className="panel-header">System</div>
              <div className="grid grid-cols-2 gap-4">
                <DataDisplay label="CPU Temp" value={vehicleState.system.cpu_temp.toFixed(1)} unit="°C" />
                <DataDisplay
                  label="Free Heap"
                  value={(vehicleState.system.free_heap / 1024).toFixed(0)}
                  unit="KB"
                />
              </div>
            </div>
          </div>

          {/* Center Column - Digital Twin / Map (placeholder) */}
          <div className="space-y-4">
            <div className="panel h-80">
              <div className="panel-header">Digital Twin</div>
              <div className="h-full flex items-center justify-center text-text-secondary">
                <div className="text-center">
                  <div className="text-6xl mb-4">🤖</div>
                  <div>Position: ({vehicleState.position.x.toFixed(2)}, {vehicleState.position.y.toFixed(2)})</div>
                  <div>Heading: {vehicleState.position.heading.toFixed(1)}°</div>
                  <div className="mt-4 text-sm">
                    GPS integration coming soon
                  </div>
                </div>
              </div>
            </div>

            {/* Sensors */}
            <div className="panel">
              <div className="panel-header">Sensors</div>
              <SensorDisplay sensors={vehicleState.sensors} />
            </div>

            {/* CSI Presence Detection */}
            <div className="panel">
              <div className="panel-header">WiFi Presence (CSI)</div>
              <CSIPresenceDisplay presence={vehicleState.csi_presence} />
            </div>

            {/* Motors */}
            <div className="panel">
              <div className="panel-header">Motor Output</div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-xs text-text-secondary mb-1">Left Motor</div>
                  <div className="h-4 bg-panel-border rounded overflow-hidden">
                    <div
                      className="h-full bg-nasa-blue transition-all duration-100"
                      style={{
                        width: `${Math.abs(vehicleState.motors.left) / 255 * 100}%`,
                        marginLeft: vehicleState.motors.left < 0 ? 'auto' : 0,
                      }}
                    />
                  </div>
                  <div className="text-center text-sm mt-1">{vehicleState.motors.left}</div>
                </div>
                <div>
                  <div className="text-xs text-text-secondary mb-1">Right Motor</div>
                  <div className="h-4 bg-panel-border rounded overflow-hidden">
                    <div
                      className="h-full bg-nasa-blue transition-all duration-100"
                      style={{
                        width: `${Math.abs(vehicleState.motors.right) / 255 * 100}%`,
                        marginLeft: vehicleState.motors.right < 0 ? 'auto' : 0,
                      }}
                    />
                  </div>
                  <div className="text-center text-sm mt-1">{vehicleState.motors.right}</div>
                </div>
              </div>
            </div>
          </div>

          {/* Right Column - Controls */}
          <div className="space-y-4">
            {/* Mode Selection */}
            <div className="panel">
              <div className="panel-header">Mode</div>
              <ModeSelector vehicleId={vehicleState.vehicle_id} currentMode={vehicleState.mode} />
            </div>

            {/* Control Panel */}
            <div className="panel">
              <div className="panel-header">Controls</div>
              <ControlPanel
                vehicleId={vehicleState.vehicle_id}
                armed={vehicleState.armed}
                mode={vehicleState.mode}
              />
            </div>

            {/* Event Log */}
            <div className="panel flex-1">
              <div className="panel-header">Event Log</div>
              <EventLog events={events} />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
