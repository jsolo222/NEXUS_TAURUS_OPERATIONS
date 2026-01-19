/**
 * SASHA Core
 *
 * Central orchestration for the AI mission control assistant.
 * Manages agents, telemetry streams, and decision making.
 */

import WebSocket from 'ws';

export class SashaCore {
    constructor(config) {
        this.config = config;
        this.agents = new Map();
        this.vehicleStates = new Map();
        this.ws = null;
        this.connected = false;
        this.eventHandlers = new Map();
        this.alertHistory = [];
    }

    /**
     * Register a specialized agent
     */
    registerAgent(name, agent) {
        this.agents.set(name, agent);
        console.log(`[SASHA] Registered agent: ${name}`);
    }

    /**
     * Connect to NEXUS TAURUS ground station
     */
    async connect() {
        return new Promise((resolve, reject) => {
            console.log(`[SASHA] Connecting to ${this.config.ntoWsUrl}...`);

            this.ws = new WebSocket(this.config.ntoWsUrl);

            this.ws.on('open', () => {
                this.connected = true;
                console.log('[SASHA] Connected to ground station');
                resolve();
            });

            this.ws.on('message', (data) => {
                this._handleMessage(JSON.parse(data.toString()));
            });

            this.ws.on('close', () => {
                this.connected = false;
                console.log('[SASHA] Disconnected from ground station');
                // Attempt reconnect after delay
                setTimeout(() => this.connect(), 5000);
            });

            this.ws.on('error', (err) => {
                console.error('[SASHA] WebSocket error:', err.message);
                if (!this.connected) reject(err);
            });

            // Timeout
            setTimeout(() => {
                if (!this.connected) {
                    reject(new Error('Connection timeout'));
                }
            }, 10000);
        });
    }

    /**
     * Disconnect from ground station
     */
    async disconnect() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
        this.connected = false;
    }

    /**
     * Handle incoming WebSocket message
     */
    _handleMessage(message) {
        if (message.event === 'initial_state') {
            // Initial state from all vehicles
            for (const [vehicleId, state] of Object.entries(message.vehicles)) {
                this.vehicleStates.set(vehicleId, state);
                this._notifyAgents('vehicle_state', { vehicleId, state, initial: true });
            }
            console.log(`[SASHA] Received initial state for ${Object.keys(message.vehicles).length} vehicles`);

        } else if (message.event === 'state_update') {
            // Real-time state update
            const { vehicle_id: vehicleId, state } = message;
            const previousState = this.vehicleStates.get(vehicleId);
            this.vehicleStates.set(vehicleId, state);

            this._notifyAgents('vehicle_state', { vehicleId, state, previousState });
        }
    }

    /**
     * Notify all agents of an event
     */
    _notifyAgents(event, data) {
        for (const [name, agent] of this.agents) {
            try {
                if (typeof agent.onEvent === 'function') {
                    agent.onEvent(event, data);
                }
            } catch (err) {
                console.error(`[SASHA] Agent ${name} error:`, err.message);
            }
        }
    }

    /**
     * Get current state of a vehicle
     */
    getVehicleState(vehicleId) {
        return this.vehicleStates.get(vehicleId);
    }

    /**
     * Get all vehicle states
     */
    getAllVehicleStates() {
        return Object.fromEntries(this.vehicleStates);
    }

    /**
     * Send command to vehicle via ground station
     */
    async sendCommand(vehicleId, command, params = {}) {
        const response = await fetch(
            `${this.config.ntoApiUrl}/api/vehicles/${vehicleId}/command`,
            {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ command, params }),
            }
        );

        if (!response.ok) {
            throw new Error(`Command failed: ${response.statusText}`);
        }

        return response.json();
    }

    /**
     * Issue an alert
     */
    alert(level, vehicleId, message, details = {}) {
        const alert = {
            timestamp: new Date().toISOString(),
            level,
            vehicleId,
            message,
            details,
        };

        this.alertHistory.push(alert);
        console.log(`[ALERT][${level.toUpperCase()}] ${vehicleId}: ${message}`);

        // Notify agents
        this._notifyAgents('alert', alert);

        return alert;
    }

    /**
     * Generate status report for a vehicle
     */
    async generateStatusReport(vehicleId) {
        const state = this.vehicleStates.get(vehicleId);
        if (!state) {
            return `Vehicle ${vehicleId} not found`;
        }

        const lines = [
            `═══════════════════════════════════════`,
            `  ${vehicleId} STATUS REPORT`,
            `═══════════════════════════════════════`,
            ``,
            `Mode:        ${state.mode}`,
            `Armed:       ${state.armed ? 'YES' : 'NO'}`,
            ``,
            `Battery:     ${state.battery.percent}% (${state.battery.voltage.toFixed(1)}V)`,
            `Connection:  ${state.connection.connected ? 'ONLINE' : 'OFFLINE'} (${state.connection.rssi} dBm)`,
            ``,
            `Position:    (${state.position.x.toFixed(2)}, ${state.position.y.toFixed(2)})`,
            `Heading:     ${state.position.heading.toFixed(1)}°`,
            ``,
            `Sensors:`,
            `  IR Left:   ${state.sensors.ir_left ? 'Clear' : 'BLOCKED'}`,
            `  IR Right:  ${state.sensors.ir_right ? 'Clear' : 'BLOCKED'}`,
            `  Distance:  ${state.sensors.ultrasonic_cm.toFixed(1)} cm`,
        ];

        // Add CSI presence if available
        if (state.csi_presence) {
            lines.push(``);
            lines.push(`Presence:    ${state.csi_presence.state}`);
            if (state.csi_presence.state !== 'CLEAR') {
                lines.push(`  Confidence: ${(state.csi_presence.confidence * 100).toFixed(0)}%`);
            }
        }

        lines.push(``);
        lines.push(`System:`);
        lines.push(`  Uptime:    ${this._formatUptime(state.system.uptime_ms)}`);
        lines.push(`  CPU Temp:  ${state.system.cpu_temp.toFixed(1)}°C`);
        lines.push(`  Free Heap: ${(state.system.free_heap / 1024).toFixed(0)} KB`);
        lines.push(`═══════════════════════════════════════`);

        return lines.join('\n');
    }

    _formatUptime(ms) {
        const seconds = Math.floor(ms / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);

        if (hours > 0) {
            return `${hours}h ${minutes % 60}m`;
        }
        return `${minutes}m ${seconds % 60}s`;
    }

    /**
     * Query Ollama for local AI inference
     */
    async queryOllama(prompt) {
        if (!this.config.ollamaHost) {
            throw new Error('Ollama not configured');
        }

        const response = await fetch(`${this.config.ollamaHost}/api/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                model: this.config.ollamaModel,
                prompt,
                stream: false,
            }),
        });

        if (!response.ok) {
            throw new Error(`Ollama query failed: ${response.statusText}`);
        }

        const data = await response.json();
        return data.response;
    }
}
