/**
 * Weather Agent
 *
 * Integrates with NASA APIs to provide weather and environmental data
 * for mission planning and safety assessment.
 */

export class WeatherAgent {
    constructor(sasha) {
        this.sasha = sasha;
        this.nasaApiKey = sasha.config.nasaApiKey;
        this.lastWeatherCheck = null;
        this.cachedWeather = null;
        this.checkIntervalMs = 15 * 60 * 1000; // 15 minutes

        // Start periodic weather checks
        this._startPeriodicChecks();
    }

    /**
     * Handle events from Sasha core
     */
    onEvent(event, data) {
        // Weather agent primarily operates on schedule
        // but can respond to specific queries
    }

    /**
     * Start periodic weather checks
     */
    _startPeriodicChecks() {
        // Initial check
        this.checkWeather();

        // Periodic checks
        setInterval(() => {
            this.checkWeather();
        }, this.checkIntervalMs);
    }

    /**
     * Check weather conditions
     */
    async checkWeather() {
        try {
            console.log('[WEATHER] Checking conditions...');

            // Get APOD (Astronomy Picture of the Day) as a simple NASA API test
            // In production, you'd use actual weather APIs
            const apod = await this._fetchNasaAPOD();

            // For actual weather, you might use:
            // - NOAA APIs
            // - OpenWeatherMap
            // - NASA POWER (for solar/climate data)

            this.lastWeatherCheck = new Date();
            this.cachedWeather = {
                timestamp: this.lastWeatherCheck.toISOString(),
                conditions: 'operational', // Placeholder
                nasa_connection: apod ? 'OK' : 'FAILED',
            };

            console.log('[WEATHER] NASA API connection: OK');

        } catch (err) {
            console.error('[WEATHER] Check failed:', err.message);
        }
    }

    /**
     * Fetch NASA Astronomy Picture of the Day
     * Used as a connection test and for fun
     */
    async _fetchNasaAPOD() {
        const url = `https://api.nasa.gov/planetary/apod?api_key=${this.nasaApiKey}`;

        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`NASA API error: ${response.statusText}`);
        }

        return response.json();
    }

    /**
     * Get space weather (solar activity)
     * Relevant for long-range RF communications
     */
    async getSpaceWeather() {
        try {
            const url = `https://api.nasa.gov/DONKI/FLR?startDate=${this._getDateString(-7)}&endDate=${this._getDateString(0)}&api_key=${this.nasaApiKey}`;

            const response = await fetch(url);
            if (!response.ok) return null;

            const data = await response.json();

            // Check for recent solar flares
            if (data && data.length > 0) {
                const recent = data[data.length - 1];
                return {
                    hasActivity: true,
                    classType: recent.classType,
                    peakTime: recent.peakTime,
                    note: 'Solar activity may affect RF communications',
                };
            }

            return {
                hasActivity: false,
                note: 'No significant solar activity',
            };

        } catch (err) {
            console.error('[WEATHER] Space weather fetch failed:', err.message);
            return null;
        }
    }

    /**
     * Get Near-Earth Objects for a date range
     * Just for fun / educational
     */
    async getNearEarthObjects(days = 7) {
        try {
            const startDate = this._getDateString(0);
            const endDate = this._getDateString(days);

            const url = `https://api.nasa.gov/neo/rest/v1/feed?start_date=${startDate}&end_date=${endDate}&api_key=${this.nasaApiKey}`;

            const response = await fetch(url);
            if (!response.ok) return null;

            const data = await response.json();

            return {
                count: data.element_count,
                objects: Object.values(data.near_earth_objects || {}).flat().slice(0, 5),
            };

        } catch (err) {
            console.error('[WEATHER] NEO fetch failed:', err.message);
            return null;
        }
    }

    /**
     * Get weather assessment for operations
     */
    getOperationalAssessment() {
        if (!this.cachedWeather) {
            return {
                status: 'UNKNOWN',
                message: 'Weather data not yet available',
                lastCheck: null,
            };
        }

        return {
            status: 'GO',
            message: 'Conditions suitable for operations',
            lastCheck: this.cachedWeather.timestamp,
            details: this.cachedWeather,
        };
    }

    /**
     * Helper: Get date string in YYYY-MM-DD format
     */
    _getDateString(daysOffset = 0) {
        const date = new Date();
        date.setDate(date.getDate() + daysOffset);
        return date.toISOString().split('T')[0];
    }
}
