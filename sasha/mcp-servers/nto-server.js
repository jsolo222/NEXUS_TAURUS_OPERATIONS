#!/usr/bin/env node
/**
 * NEXUS TAURUS Operations MCP Server
 *
 * Model Context Protocol server that provides Sasha (and other AI assistants)
 * access to vehicle telemetry, commands, and mission data.
 *
 * Tools provided:
 * - get_vehicle_status: Get current state of a vehicle
 * - list_vehicles: List all known vehicles
 * - send_command: Send a command to a vehicle
 * - get_telemetry_history: Get historical telemetry
 * - get_alerts: Get recent alerts
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';

const NTO_API_URL = process.env.NTO_API_URL || 'http://localhost:8765';

// Create MCP server
const server = new Server(
    {
        name: 'nexus-taurus-operations',
        version: '0.1.0',
    },
    {
        capabilities: {
            tools: {},
        },
    }
);

// Helper function for API calls
async function ntoFetch(path, options = {}) {
    const response = await fetch(`${NTO_API_URL}${path}`, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...options.headers,
        },
    });

    if (!response.ok) {
        throw new Error(`NTO API error: ${response.status} ${response.statusText}`);
    }

    return response.json();
}

// Define tools
server.setRequestHandler('tools/list', async () => {
    return {
        tools: [
            {
                name: 'get_vehicle_status',
                description: 'Get current status and telemetry of a vehicle',
                inputSchema: {
                    type: 'object',
                    properties: {
                        vehicle_id: {
                            type: 'string',
                            description: 'Vehicle identifier (e.g., TAURUS-01)',
                        },
                    },
                    required: ['vehicle_id'],
                },
            },
            {
                name: 'list_vehicles',
                description: 'List all known vehicles and their connection status',
                inputSchema: {
                    type: 'object',
                    properties: {},
                },
            },
            {
                name: 'send_command',
                description: 'Send a command to a vehicle (requires confirmation for dangerous commands)',
                inputSchema: {
                    type: 'object',
                    properties: {
                        vehicle_id: {
                            type: 'string',
                            description: 'Vehicle identifier',
                        },
                        command: {
                            type: 'string',
                            enum: ['STOP', 'ARM', 'DISARM', 'SET_MODE', 'RTB'],
                            description: 'Command to send',
                        },
                        params: {
                            type: 'object',
                            description: 'Command parameters',
                        },
                    },
                    required: ['vehicle_id', 'command'],
                },
            },
            {
                name: 'get_telemetry_history',
                description: 'Get historical telemetry records for a vehicle',
                inputSchema: {
                    type: 'object',
                    properties: {
                        vehicle_id: {
                            type: 'string',
                            description: 'Vehicle identifier',
                        },
                        limit: {
                            type: 'number',
                            description: 'Maximum records to return (default 100)',
                        },
                    },
                    required: ['vehicle_id'],
                },
            },
            {
                name: 'emergency_stop',
                description: 'EMERGENCY: Immediately stop a vehicle. Use only in emergencies.',
                inputSchema: {
                    type: 'object',
                    properties: {
                        vehicle_id: {
                            type: 'string',
                            description: 'Vehicle identifier',
                        },
                    },
                    required: ['vehicle_id'],
                },
            },
        ],
    };
});

// Handle tool calls
server.setRequestHandler('tools/call', async (request) => {
    const { name, arguments: args } = request.params;

    try {
        switch (name) {
            case 'get_vehicle_status': {
                const data = await ntoFetch(`/api/vehicles/${args.vehicle_id}`);
                return {
                    content: [
                        {
                            type: 'text',
                            text: JSON.stringify(data, null, 2),
                        },
                    ],
                };
            }

            case 'list_vehicles': {
                const data = await ntoFetch('/api/vehicles');
                return {
                    content: [
                        {
                            type: 'text',
                            text: JSON.stringify(data, null, 2),
                        },
                    ],
                };
            }

            case 'send_command': {
                // Safety check for dangerous commands
                const dangerousCommands = ['ARM', 'MOVE'];
                if (dangerousCommands.includes(args.command)) {
                    return {
                        content: [
                            {
                                type: 'text',
                                text: `⚠️ SAFETY: Command "${args.command}" requires operator confirmation. Please confirm with the operator before executing.`,
                            },
                        ],
                        isError: false,
                    };
                }

                const data = await ntoFetch(`/api/vehicles/${args.vehicle_id}/command`, {
                    method: 'POST',
                    body: JSON.stringify({
                        command: args.command,
                        params: args.params || {},
                    }),
                });

                return {
                    content: [
                        {
                            type: 'text',
                            text: `Command sent: ${JSON.stringify(data)}`,
                        },
                    ],
                };
            }

            case 'get_telemetry_history': {
                const limit = args.limit || 100;
                const data = await ntoFetch(`/api/vehicles/${args.vehicle_id}/telemetry?limit=${limit}`);
                return {
                    content: [
                        {
                            type: 'text',
                            text: JSON.stringify(data, null, 2),
                        },
                    ],
                };
            }

            case 'emergency_stop': {
                const data = await ntoFetch(`/api/vehicles/${args.vehicle_id}/stop`, {
                    method: 'POST',
                });
                return {
                    content: [
                        {
                            type: 'text',
                            text: `🛑 EMERGENCY STOP executed for ${args.vehicle_id}: ${JSON.stringify(data)}`,
                        },
                    ],
                };
            }

            default:
                throw new Error(`Unknown tool: ${name}`);
        }
    } catch (error) {
        return {
            content: [
                {
                    type: 'text',
                    text: `Error: ${error.message}`,
                },
            ],
            isError: true,
        };
    }
});

// Start server
async function main() {
    const transport = new StdioServerTransport();
    await server.connect(transport);
    console.error('[NTO-MCP] Server started');
}

main().catch((error) => {
    console.error('[NTO-MCP] Fatal error:', error);
    process.exit(1);
});
