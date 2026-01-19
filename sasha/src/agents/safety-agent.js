/**
 * Safety Agent
 *
 * Monitors vehicle safety conditions and provides recommendations.
 * Can request emergency actions when critical conditions are detected.
 */

export class SafetyAgent {
    constructor(sasha) {
        this.sasha = sasha;
        this.vehicleRiskLevels = new Map();
    }

    /**
     * Handle events from Sasha core
     */
    onEvent(event, data) {
        switch (event) {
            case 'vehicle_state':
                this._assessRisk(data.vehicleId, data.state, data.previousState);
                break;
            case 'alert':
                this._handleAlert(data);
                break;
        }
    }

    /**
     * Assess overall risk level for a vehicle
     */
    _assessRisk(vehicleId, state, previousState) {
        let riskScore = 0;
        const factors = [];

        // Battery risk
        if (state.battery.percent < 10) {
            riskScore += 50;
            factors.push('CRITICAL: Battery below 10%');
        } else if (state.battery.percent < 20) {
            riskScore += 20;
            factors.push('Battery low');
        }

        // Connection risk
        if (!state.connection.connected) {
            riskScore += 40;
            factors.push('Connection lost');
        } else if (state.connection.rssi < -75) {
            riskScore += 15;
            factors.push('Weak signal');
        }

        // Obstacle risk
        if (state.sensors.ultrasonic_cm < 15) {
            riskScore += 25;
            factors.push('Very close obstacle');
        } else if (state.sensors.ultrasonic_cm < 30) {
            riskScore += 10;
            factors.push('Nearby obstacle');
        }

        if (state.sensors.ir_left === 0 || state.sensors.ir_right === 0) {
            riskScore += 15;
            factors.push('Side obstacle detected');
        }

        // Presence risk (when armed)
        if (state.armed && state.csi_presence?.state === 'APPROACHING') {
            riskScore += 30;
            factors.push('Human approaching while armed');
        }

        // Temperature risk
        if (state.system.cpu_temp > 70) {
            riskScore += 20;
            factors.push('High CPU temperature');
        }

        // Update risk level
        const previousRisk = this.vehicleRiskLevels.get(vehicleId) || 0;
        this.vehicleRiskLevels.set(vehicleId, riskScore);

        // Trigger actions based on risk level
        if (riskScore >= 70 && previousRisk < 70) {
            this._recommendEmergencyAction(vehicleId, state, factors);
        } else if (riskScore >= 40 && previousRisk < 40) {
            this._recommendCaution(vehicleId, state, factors);
        }
    }

    /**
     * Recommend emergency action
     */
    _recommendEmergencyAction(vehicleId, state, factors) {
        console.log(`[SAFETY] HIGH RISK for ${vehicleId}`);
        console.log(`[SAFETY] Factors: ${factors.join(', ')}`);
        console.log(`[SAFETY] Recommendation: IMMEDIATE RTB or EMERGENCY STOP`);

        this.sasha.alert('critical', vehicleId,
            `High risk detected - Recommend immediate RTB`,
            { factors, recommendation: 'RTB' }
        );

        // If battery is critical, recommend emergency stop
        if (state.battery.percent < 10) {
            console.log(`[SAFETY] Auto-recommending DISARM due to critical battery`);
        }
    }

    /**
     * Recommend caution
     */
    _recommendCaution(vehicleId, state, factors) {
        console.log(`[SAFETY] ELEVATED RISK for ${vehicleId}`);
        console.log(`[SAFETY] Factors: ${factors.join(', ')}`);

        this.sasha.alert('warning', vehicleId,
            `Elevated risk - Exercise caution`,
            { factors }
        );
    }

    /**
     * Handle alerts from other agents
     */
    _handleAlert(alert) {
        // Safety agent can respond to alerts from other agents
        if (alert.level === 'critical' && alert.message.includes('approaching')) {
            console.log(`[SAFETY] Human approaching - monitoring situation`);
        }
    }

    /**
     * Get current risk assessment
     */
    getRiskAssessment(vehicleId) {
        const score = this.vehicleRiskLevels.get(vehicleId) || 0;
        let level = 'LOW';
        if (score >= 70) level = 'CRITICAL';
        else if (score >= 40) level = 'ELEVATED';
        else if (score >= 20) level = 'MODERATE';

        return { score, level };
    }
}
