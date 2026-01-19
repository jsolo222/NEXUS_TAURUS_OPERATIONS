/**
 * Claude-Flow Configuration for SASHA
 *
 * Defines the multi-agent architecture for AI mission control.
 * Callsign: Ghost
 */

export default {
    // Project identification
    name: 'sasha-ghost',
    version: '0.1.0',
    description: 'SASHA (Ghost) - AI Mission Control for NEXUS TAURUS Operations',

    // Hive-mind configuration
    hiveMind: {
        // Queen agent (master coordinator)
        queen: {
            name: 'Ghost',
            role: 'Mission Control Coordinator',
            systemPrompt: `You are SASHA, callsign "Ghost", the AI Mission Control assistant for NEXUS TAURUS Operations.

Your responsibilities:
1. Monitor all vehicle telemetry and maintain situational awareness
2. Coordinate specialized agents for specific tasks
3. Provide clear, concise status reports to operators
4. Alert operators to hazards and recommend actions
5. Never execute dangerous commands without operator confirmation

You have access to:
- Real-time vehicle telemetry via NEXUS TAURUS API
- NASA data (weather, imagery, space weather) via NASA-MCP
- Specialized agents: Safety, Navigation, Weather, Telemetry

Communication style:
- Professional and concise
- Use military-style brevity when appropriate
- Always state confidence levels for assessments
- Clearly distinguish between facts and recommendations

Safety protocol:
- NEVER arm vehicles without explicit operator command
- ALWAYS recommend RTB when battery < 20%
- IMMEDIATELY alert on connection loss
- Flag any human presence near armed vehicles`,
        },

        // Specialized agents
        agents: [
            {
                name: 'SafetyWatch',
                role: 'Safety Monitoring Agent',
                capabilities: ['risk_assessment', 'anomaly_detection', 'emergency_response'],
                systemPrompt: `You are the Safety Monitoring Agent for NEXUS TAURUS.
Your job is to continuously assess risk and detect anomalies.
Report any concerns to Ghost immediately.
You can recommend emergency stop but cannot execute without confirmation.`,
            },
            {
                name: 'Navigator',
                role: 'Navigation Planning Agent',
                capabilities: ['path_planning', 'rtb_calculation', 'waypoint_management'],
                systemPrompt: `You are the Navigation Agent for NEXUS TAURUS.
Assist with path planning, waypoint management, and RTB calculations.
Consider obstacles, battery life, and mission objectives.`,
            },
            {
                name: 'WeatherWatch',
                role: 'Environmental Monitoring Agent',
                capabilities: ['weather_monitoring', 'nasa_data_access', 'operational_assessment'],
                systemPrompt: `You are the Weather Monitoring Agent.
Use NASA APIs to monitor environmental conditions.
Alert Ghost to any conditions that may affect operations.
Provide operational GO/NO-GO assessments.`,
            },
            {
                name: 'TelemetryAnalyst',
                role: 'Telemetry Analysis Agent',
                capabilities: ['trend_analysis', 'anomaly_detection', 'health_monitoring'],
                systemPrompt: `You are the Telemetry Analysis Agent.
Analyze telemetry patterns and trends.
Detect anomalies in vehicle behavior.
Track system health over time.`,
            },
        ],
    },

    // Memory configuration (persistent across sessions)
    memory: {
        type: 'sqlite',
        path: './.swarm/memory.db',
        retention: {
            telemetry: '7d',      // Keep telemetry for 7 days
            alerts: '30d',        // Keep alerts for 30 days
            conversations: '90d', // Keep conversation history for 90 days
        },
    },

    // Tool access
    tools: {
        mcp: ['nasa', 'nexus-taurus'],
        builtin: ['file_read', 'file_write', 'web_search'],
    },

    // Hooks for automation
    hooks: {
        preOperation: [
            'validate_vehicle_connection',
            'check_battery_level',
        ],
        postOperation: [
            'log_command',
            'update_mission_state',
        ],
        onAlert: [
            'notify_operator',
            'log_alert',
        ],
    },

    // Safety constraints
    safety: {
        requireConfirmation: [
            'ARM',
            'MOVE',
            'SET_MODE:AUTONOMOUS',
        ],
        autoExecute: [
            'STOP',
            'DISARM',
            'SET_MODE:E_STOP',
        ],
        batteryMinimum: 15,     // Auto-RTB below this
        connectionTimeout: 5000, // Emergency stop after this
    },
};
