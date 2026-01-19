/**
 * SASHA - AI Mission Control Assistant
 *
 * Situational Awareness System for Hazard Assessment
 * Core entry point and orchestration
 */

import 'dotenv/config';
import { TelemetryMonitor } from './telemetry-monitor.js';
import { WeatherAgent } from './agents/weather-agent.js';
import { SafetyAgent } from './agents/safety-agent.js';
import { SashaCore } from './sasha-core.js';

console.log(`
╔═══════════════════════════════════════════════════════════════════════════╗
║                                                                           ║
║   ███████╗ █████╗ ███████╗██╗  ██╗ █████╗                                 ║
║   ██╔════╝██╔══██╗██╔════╝██║  ██║██╔══██╗                                ║
║   ███████╗███████║███████╗███████║███████║                                ║
║   ╚════██║██╔══██║╚════██║██╔══██║██╔══██║                                ║
║   ███████║██║  ██║███████║██║  ██║██║  ██║                                ║
║   ╚══════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝                                ║
║                                                                           ║
║   Situational Awareness System for Hazard Assessment                      ║
║   NEXUS TAURUS OPERATIONS - AI Mission Control                            ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝
`);

async function main() {
    console.log('[SASHA] Initializing...');

    // Initialize core
    const sasha = new SashaCore({
        ntoApiUrl: process.env.NTO_API_URL || 'http://localhost:8765',
        ntoWsUrl: process.env.NTO_WS_URL || 'ws://localhost:8765/ws/dashboard',
        nasaApiKey: process.env.NASA_API_KEY || 'DEMO_KEY',
        ollamaHost: process.env.OLLAMA_HOST,
        ollamaModel: process.env.OLLAMA_MODEL || 'llama3.2',
    });

    // Initialize telemetry monitor
    const telemetryMonitor = new TelemetryMonitor(sasha);

    // Initialize agents
    const safetyAgent = new SafetyAgent(sasha);
    const weatherAgent = new WeatherAgent(sasha);

    // Register agents
    sasha.registerAgent('safety', safetyAgent);
    sasha.registerAgent('weather', weatherAgent);

    // Start monitoring
    await sasha.connect();

    console.log('[SASHA] All systems operational');
    console.log('[SASHA] Monitoring NEXUS TAURUS fleet...');
    console.log('');

    // Keep alive
    process.on('SIGINT', async () => {
        console.log('\n[SASHA] Shutting down...');
        await sasha.disconnect();
        process.exit(0);
    });
}

main().catch(err => {
    console.error('[SASHA] Fatal error:', err);
    process.exit(1);
});
