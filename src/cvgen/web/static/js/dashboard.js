/**
 * CVGen Dashboard Tab
 * Displays system status, active jobs, and recent results
 */

class Dashboard {
    constructor() {
        this.activeJobs = [];
        this.recentResults = [];
        this.systemStatus = {};
        this.refreshInterval = null;

        this.init();
    }

    init() {
        // Listen to app events
        if (window.app) {
            window.app.on('system_status', (data) => this.updateSystemStatus(data));
            window.app.on('job_status_changed', (data) => this.updateJob(data));
            window.app.on('backends_loaded', (data) => this.updateBackendsGrid(data));
        }

        this.setupEventListeners();
        this.refresh();

        // Refresh every 5 seconds
        this.refreshInterval = setInterval(() => this.refresh(), 5000);
    }

    setupEventListeners() {
        // Listen to tab visibility changes
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                clearInterval(this.refreshInterval);
            } else {
                this.refresh();
                this.refreshInterval = setInterval(() => this.refresh(), 5000);
            }
        });
    }

    async refresh() {
        try {
            await Promise.all([
                this.loadSystemStatus(),
                this.loadActiveJobs(),
                this.loadRecentResults(),
                this.loadBackends(),
            ]);
        } catch (error) {
            console.error('Dashboard refresh failed:', error);
        }
    }

    async loadSystemStatus() {
        try {
            const response = await CVGenAPI.health();
            this.updateSystemStatus(response);
        } catch (error) {
            console.error('Failed to load system status:', error);
            this.updateSystemStatusError();
        }
    }

    updateSystemStatus(status) {
        this.systemStatus = status;

        // Update status cards
        const statusElements = {
            'api-status': status.status === 'ok' ? '●' : '○',
            'db-status': status.qdrant_available ? '●' : '○',
            'llm-status': status.ollama_available ? '●' : '○',
            'quantum-status': status.origin_pilot_available ? '●' : '○',
        };

        Object.entries(statusElements).forEach(([id, symbol]) => {
            const el = document.getElementById(id);
            if (el) {
                el.textContent = symbol;
                el.style.color = symbol === '●' ? 'var(--color-success)' : 'var(--color-error)';
            }
        });
    }

    updateSystemStatusError() {
        const statusElements = ['api-status', 'db-status', 'llm-status', 'quantum-status'];
        statusElements.forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                el.textContent = '?';
                el.style.color = 'var(--color-warning)';
            }
        });
    }

    async loadActiveJobs() {
        try {
            // This would call an endpoint that returns active jobs
            // For now, we'll show a placeholder
            this.renderActiveJobs([]);
        } catch (error) {
            console.error('Failed to load active jobs:', error);
        }
    }

    renderActiveJobs(jobs) {
        const container = document.getElementById('active-jobs');

        if (!jobs || jobs.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">⏱️</div>
                    <p>No active jobs</p>
                </div>
            `;
            return;
        }

        container.innerHTML = jobs.map(job => `
            <div class="job-item">
                <div class="job-info">
                    <div class="job-name">${job.name}</div>
                    <div class="job-meta">Started ${this.formatTime(job.created_at)} • Circuit: ${job.circuit_id}</div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${job.progress || 0}%"></div>
                    </div>
                </div>
                <div style="text-align: right; min-width: 80px;">
                    <div style="font-weight: 600; color: var(--color-accent-primary);">${job.progress || 0}%</div>
                </div>
            </div>
        `).join('');
    }

    updateJob(jobData) {
        // Find and update the job in the list
        const jobIndex = this.activeJobs.findIndex(j => j.id === jobData.id);
        if (jobIndex >= 0) {
            this.activeJobs[jobIndex] = jobData;
            this.renderActiveJobs(this.activeJobs);
        }
    }

    async loadRecentResults() {
        try {
            // This would call an endpoint that returns recent results
            // For now, we'll show a placeholder
            this.renderRecentResults([]);
        } catch (error) {
            console.error('Failed to load recent results:', error);
        }
    }

    renderRecentResults(results) {
        const container = document.getElementById('recent-results');

        if (!results || results.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">📊</div>
                    <p>No results yet</p>
                </div>
            `;
            return;
        }

        container.innerHTML = results.map(result => `
            <div class="result-item">
                <div class="job-info">
                    <div class="job-name">${result.name}</div>
                    <div class="job-meta">Completed ${this.formatTime(result.completed_at)} • ${result.backend}</div>
                </div>
                <div style="text-align: right; min-width: 80px;">
                    <div style="font-weight: 600; color: var(--color-success);">✓</div>
                </div>
            </div>
        `).join('');
    }

    async loadBackends() {
        try {
            const response = await CVGenAPI.getBackends();
            this.updateBackendsGrid(response.backends || []);
        } catch (error) {
            console.error('Failed to load backends:', error);
        }
    }

    updateBackendsGrid(backends) {
        // This is handled in the backends tab, but we could also show a quick view here
        // For now, we'll update statistics
        const totalBackends = Array.isArray(backends) ? backends.length : 0;
        // Could update quick stats here
    }

    updateBackendStatus(backendData) {
        // Handle backend status changes from WebSocket
        console.log('Backend status updated:', backendData);
    }

    formatTime(dateString) {
        if (!dateString) return 'unknown';
        const date = new Date(dateString);
        const now = new Date();
        const diffSeconds = Math.floor((now - date) / 1000);

        if (diffSeconds < 60) return `${diffSeconds}s ago`;
        if (diffSeconds < 3600) return `${Math.floor(diffSeconds / 60)}m ago`;
        if (diffSeconds < 86400) return `${Math.floor(diffSeconds / 3600)}h ago`;
        return `${Math.floor(diffSeconds / 86400)}d ago`;
    }

    destroy() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
    }
}
