/**
 * Telemetry Monitor
 *
 * Watches telemetry streams and triggers alerts based on conditions.
 */

export class TelemetryMonitor {
    constructor(sasha) {
        this.sasha = sasha;
        this.thresholds = {
            batteryLow: parseInt(process.env.SASHA_ALERT_BATTERY_LOW || '20'),
            batteryCritical: parseInt(process.env.SASHA_ALERT_BATTERY_CRITICAL || '10'),
            connectionTimeout: parseInt(process.env.SASHA_ALERT_CONNECTION_TIMEOUT || '5000'),
        };
        this.alertCooldowns = new Map();
    }

    /**
     * Check if we should alert (respects cooldown)
     */
    _shouldAlert(alertKey, cooldownMs = 30000) {
        const lastAlert = this.alertCooldowns.get(alertKey);
        if (lastAlert && Date.now() - lastAlert < cooldownMs) {
            return false;
        }
        this.alertCooldowns.set(alertKey, Date.now());
        return true;
    }

    /**
     * Process telemetry and check for alert conditions
     */
    checkTelemetry(vehicleId, state, previousState) {
        // Battery checks
        this._checkBattery(vehicleId, state);

        // Connection checks
        this._checkConnection(vehicleId, state);

        // Obstacle checks
        this._checkObstacles(vehicleId, state);

        // CSI presence checks
        this._checkPresence(vehicleId, state, previousState);

        // Mode change alerts
        this._checkModeChange(vehicleId, state, previousState);
    }

    _checkBattery(vehicleId, state) {
        const percent = state.battery?.percent;
        if (percent === undefined) return;

        if (percent <= this.thresholds.batteryCritical) {
            if (this._shouldAlert(`${vehicleId}-battery-critical`, 60000)) {
                this.sasha.alert('critical', vehicleId,
                    `CRITICAL BATTERY: ${percent}% - Immediate RTB required`,
                    { battery: state.battery }
                );
            }
        } else if (percent <= this.thresholds.batteryLow) {
            if (this._shouldAlert(`${vehicleId}-battery-low`, 120000)) {
                this.sasha.alert('warning', vehicleId,
                    `Low battery: ${percent}% - Consider RTB`,
                    { battery: state.battery }
                );
            }
        }
    }

    _checkConnection(vehicleId, state) {
        if (!state.connection?.connected) {
            if (this._shouldAlert(`${vehicleId}-disconnected`, 10000)) {
                this.sasha.alert('critical', vehicleId,
                    'Connection lost to vehicle',
                    { connection: state.connection }
                );
            }
        }

        // Weak signal warning
        const rssi = state.connection?.rssi;
        if (rssi && rssi < -70) {
            if (this._shouldAlert(`${vehicleId}-weak-signal`, 60000)) {
                this.sasha.alert('warning', vehicleId,
                    `Weak signal: ${rssi} dBm - Connection may be unstable`,
                    { rssi }
                );
            }
        }
    }

    _checkObstacles(vehicleId, state) {
        const sensors = state.sensors;
        if (!sensors) return;

        // IR obstacle detection
        if (sensors.ir_left === 0 || sensors.ir_right === 0) {
            if (this._shouldAlert(`${vehicleId}-obstacle-ir`, 5000)) {
                const side = sensors.ir_left === 0 ? 'left' : 'right';
                this.sasha.alert('info', vehicleId,
                    `Obstacle detected on ${side} side`,
                    { sensors }
                );
            }
        }

        // Close proximity warning
        if (sensors.ultrasonic_cm < 20) {
            if (this._shouldAlert(`${vehicleId}-proximity`, 5000)) {
                this.sasha.alert('warning', vehicleId,
                    `Close proximity: ${sensors.ultrasonic_cm.toFixed(1)} cm`,
                    { distance: sensors.ultrasonic_cm }
                );
            }
        }
    }

    _checkPresence(vehicleId, state, previousState) {
        const presence = state.csi_presence;
        const prevPresence = previousState?.csi_presence;

        if (!presence) return;

        // Alert on state changes
        if (prevPresence && presence.state !== prevPresence.state) {
            if (presence.state === 'APPROACHING') {
                this.sasha.alert('warning', vehicleId,
                    'Human approaching detected via WiFi CSI',
                    { csi: presence }
                );
            } else if (presence.state === 'MOVEMENT') {
                this.sasha.alert('info', vehicleId,
                    'Movement detected nearby via WiFi CSI',
                    { csi: presence }
                );
            } else if (presence.state === 'CLEAR' && prevPresence.state !== 'CLEAR') {
                this.sasha.alert('info', vehicleId,
                    'Area clear - no presence detected',
                    { csi: presence }
                );
            }
        }
    }

    _checkModeChange(vehicleId, state, previousState) {
        if (!previousState) return;

        if (state.mode !== previousState.mode) {
            this.sasha.alert('info', vehicleId,
                `Mode changed: ${previousState.mode} → ${state.mode}`,
                { previousMode: previousState.mode, newMode: state.mode }
            );
        }

        if (state.armed !== previousState.armed) {
            this.sasha.alert('info', vehicleId,
                state.armed ? 'Vehicle ARMED' : 'Vehicle DISARMED',
                { armed: state.armed }
            );
        }
    }
}
