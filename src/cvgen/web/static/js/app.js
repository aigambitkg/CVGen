/**
 * CVGen Main Application Controller
 * Manages tabs, theme, WebSocket, and global state
 */

class CVGenApp {
    constructor() {
        this.currentTab = 'dashboard';
        this.isDarkMode = true;
        this.language = 'en';
        this.ws = null;
        this.wsConnected = false;
        this.wsReconnectAttempts = 0;
        this.wsMaxReconnectAttempts = 5;
        this.wsReconnectDelay = 3000;
        this.firstRun = !localStorage.getItem('cvgen_first_run_done');
        this.eventListeners = {};

        this.init();
    }

    async init() {
        this.loadSettings();
        this.setupDOMListeners();
        this.setupTheme();

        // Initialize dashboard
        if (typeof Dashboard !== 'undefined') {
            this.dashboard = new Dashboard();
        }

        // Initialize chat
        if (typeof ChatInterface !== 'undefined') {
            this.chat = new ChatInterface();
        }

        // Initialize circuit builder
        if (typeof CircuitBuilder !== 'undefined') {
            this.circuitBuilder = new CircuitBuilder();
        }

        // Setup WebSocket
        this.connectWebSocket();

        // Show first-run wizard if needed
        if (this.firstRun) {
            this.showSetupWizard();
        }

        // Load initial data
        await this.loadBackends();
        await this.checkSystemStatus();
    }

    setupDOMListeners() {
        // Tab navigation
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.switchTab(e.target.dataset.tab));
        });

        // Theme toggle
        document.getElementById('theme-toggle').addEventListener('click', () => this.toggleTheme());

        // Settings button
        document.getElementById('settings-btn-header').addEventListener('click', () => {
            this.switchTab('settings');
        });

        // Settings
        document.getElementById('dark-mode-toggle').addEventListener('click', (e) => {
            this.isDarkMode = e.target.classList.toggle('active');
            this.setupTheme();
            this.saveSettings();
        });

        document.getElementById('language-select').addEventListener('change', (e) => {
            this.language = e.target.value;
            this.saveSettings();
            // Could trigger language change here
        });

        document.getElementById('test-connection-btn').addEventListener('click', () => this.testConnection());
        document.getElementById('reset-settings-btn').addEventListener('click', () => this.resetSettings());

        // Setup wizard
        document.getElementById('wizard-next').addEventListener('click', () => this.wizardNext());
        document.getElementById('wizard-back').addEventListener('click', () => this.wizardBack());
    }

    switchTab(tabName) {
        // Update DOM
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tabName);
        });

        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });

        document.getElementById(`tab-${tabName}`).classList.add('active');

        this.currentTab = tabName;
        this.saveSettings();

        // Trigger tab-specific initialization if needed
        if (tabName === 'dashboard' && this.dashboard) {
            this.dashboard.refresh();
        }
    }

    setupTheme() {
        const root = document.documentElement;
        const body = document.body;

        if (this.isDarkMode) {
            body.classList.remove('light-mode');
            document.getElementById('theme-toggle').textContent = '☀️';
        } else {
            body.classList.add('light-mode');
            document.getElementById('theme-toggle').textContent = '🌙';
        }

        document.getElementById('dark-mode-toggle').classList.toggle('active', this.isDarkMode);
    }

    toggleTheme() {
        this.isDarkMode = !this.isDarkMode;
        this.setupTheme();
        this.saveSettings();
    }

    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/events`;

        try {
            this.ws = new WebSocket(wsUrl);

            this.ws.onopen = () => {
                console.log('WebSocket connected');
                this.wsConnected = true;
                this.wsReconnectAttempts = 0;
                this.updateWSIndicator(true);
            };

            this.ws.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    this.handleWSMessage(message);
                } catch (e) {
                    console.error('Failed to parse WebSocket message:', e);
                }
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.wsConnected = false;
                this.updateWSIndicator(false);
            };

            this.ws.onclose = () => {
                console.log('WebSocket closed');
                this.wsConnected = false;
                this.updateWSIndicator(false);
                this.attemptReconnect();
            };
        } catch (e) {
            console.error('Failed to create WebSocket:', e);
            this.attemptReconnect();
        }
    }

    attemptReconnect() {
        if (this.wsReconnectAttempts < this.wsMaxReconnectAttempts) {
            this.wsReconnectAttempts++;
            console.log(`Attempting WebSocket reconnect (${this.wsReconnectAttempts}/${this.wsMaxReconnectAttempts})...`);
            setTimeout(() => this.connectWebSocket(), this.wsReconnectDelay);
        }
    }

    updateWSIndicator(connected) {
        const indicator = document.getElementById('ws-indicator');
        const dot = indicator.querySelector('.status-dot');

        if (connected) {
            indicator.classList.remove('disconnected');
            indicator.classList.add('connected');
            indicator.innerHTML = '<span class="status-dot connected"></span><span>Connected</span>';
        } else {
            indicator.classList.remove('connected');
            indicator.classList.add('disconnected');
            indicator.innerHTML = '<span class="status-dot"></span><span>Disconnected</span>';
        }
    }

    handleWSMessage(message) {
        const { type, data } = message;

        switch (type) {
            case 'job_status_change':
                this.emit('job_status_changed', data);
                if (this.dashboard) this.dashboard.updateJob(data);
                break;
            case 'backend_status_change':
                this.emit('backend_status_changed', data);
                if (this.dashboard) this.dashboard.updateBackendStatus(data);
                break;
            case 'agent_progress':
                this.emit('agent_progress', data);
                break;
            case 'system_metrics':
                this.emit('system_metrics', data);
                break;
        }
    }

    async loadBackends() {
        try {
            const response = await CVGenAPI.getBackends();
            this.backends = response.backends || [];
            this.emit('backends_loaded', this.backends);
        } catch (error) {
            console.error('Failed to load backends:', error);
        }
    }

    async checkSystemStatus() {
        try {
            const response = await CVGenAPI.health();
            this.emit('system_status', response);
        } catch (error) {
            console.error('Failed to check system status:', error);
        }
    }

    async testConnection() {
        const btn = document.getElementById('test-connection-btn');
        const originalText = btn.textContent;
        btn.disabled = true;
        btn.textContent = 'Testing...';

        try {
            const response = await CVGenAPI.health();
            alert(`✓ Connection successful!\nAPI Status: ${response.status}`);
        } catch (error) {
            alert(`✗ Connection failed:\n${error.message}`);
        } finally {
            btn.disabled = false;
            btn.textContent = originalText;
        }
    }

    resetSettings() {
        if (confirm('Reset all settings to defaults? This cannot be undone.')) {
            localStorage.clear();
            location.reload();
        }
    }

    saveSettings() {
        const settings = {
            isDarkMode: this.isDarkMode,
            language: this.language,
            currentTab: this.currentTab,
            lastVisit: new Date().toISOString(),
        };
        localStorage.setItem('cvgen_settings', JSON.stringify(settings));
    }

    loadSettings() {
        const stored = localStorage.getItem('cvgen_settings');
        if (stored) {
            const settings = JSON.parse(stored);
            this.isDarkMode = settings.isDarkMode !== false;
            this.language = settings.language || 'en';
            if (settings.currentTab) {
                this.currentTab = settings.currentTab;
            }
        }
    }

    showSetupWizard() {
        const wizard = document.getElementById('setup-wizard');
        wizard.classList.remove('hidden');
        this.wizardStep = 0;
        this.showWizardStep(0);
    }

    hideSetupWizard() {
        const wizard = document.getElementById('setup-wizard');
        wizard.classList.add('hidden');
        localStorage.setItem('cvgen_first_run_done', 'true');
    }

    wizardNext() {
        if (this.wizardStep === 4) {
            this.hideSetupWizard();
        } else {
            this.wizardStep++;
            this.showWizardStep(this.wizardStep);
        }
    }

    wizardBack() {
        if (this.wizardStep > 0) {
            this.wizardStep--;
            this.showWizardStep(this.wizardStep);
        }
    }

    showWizardStep(step) {
        const steps = [
            {
                title: 'Welcome to CVGen',
                subtitle: 'Quantum computing made accessible',
                content: `
                    <div class="form-group">
                        <p style="color: var(--color-text-secondary); line-height: 1.6;">
                            CVGen is a modern quantum computing platform. You can build quantum circuits, run quantum algorithms, and access real quantum hardware.
                        </p>
                        <p style="color: var(--color-text-secondary); line-height: 1.6; margin-top: 1rem;">
                            This wizard will help you configure CVGen for your needs.
                        </p>
                    </div>
                `
            },
            {
                title: 'Choose Language',
                subtitle: 'Select your preferred language',
                content: `
                    <div class="form-group">
                        <label class="form-label">Interface Language</label>
                        <select class="form-select" id="wizard-language">
                            <option value="en">English</option>
                            <option value="de">Deutsch</option>
                        </select>
                    </div>
                `
            },
            {
                title: 'Backend Configuration',
                subtitle: 'Configure your quantum backends',
                content: `
                    <div class="form-group">
                        <label class="form-label">API Server</label>
                        <input type="text" class="form-input" id="wizard-api-server" value="http://localhost:8000">
                    </div>
                    <div class="form-group">
                        <label class="form-label">WebSocket Server</label>
                        <input type="text" class="form-input" id="wizard-ws-server" value="ws://localhost:8000">
                    </div>
                `
            },
            {
                title: 'Detect Backends',
                subtitle: 'Scanning for available quantum services...',
                content: `
                    <div class="loading-state">
                        <div class="spinner"></div>
                        <p>Detecting available backends...</p>
                    </div>
                `
            },
            {
                title: 'Setup Complete!',
                subtitle: 'You\'re ready to start building quantum circuits',
                content: `
                    <div class="form-group">
                        <p style="color: var(--color-text-secondary); line-height: 1.6;">
                            ✓ CVGen is configured and ready to use.
                        </p>
                        <p style="color: var(--color-text-secondary); line-height: 1.6; margin-top: 1rem;">
                            Visit the Dashboard to monitor your quantum jobs, use the Chat interface to ask questions, or open the Circuit Builder to create quantum circuits.
                        </p>
                    </div>
                `
            }
        ];

        const stepData = steps[step];
        document.getElementById('wizard-title').textContent = stepData.title;
        document.getElementById('wizard-subtitle').textContent = stepData.subtitle;
        document.getElementById('wizard-form').innerHTML = stepData.content;

        // Update step indicators
        document.querySelectorAll('.step-indicator').forEach((el, i) => {
            el.classList.toggle('active', i <= step);
        });

        // Update back button
        document.getElementById('wizard-back').style.display = step > 0 ? 'block' : 'none';

        // Update next button text
        const nextBtn = document.getElementById('wizard-next');
        nextBtn.textContent = step === 4 ? 'Start Using CVGen' : 'Next';

        // If step 3, auto-detect backends
        if (step === 3) {
            setTimeout(() => this.wizardDetectBackends(), 500);
        }
    }

    async wizardDetectBackends() {
        try {
            const backends = await CVGenAPI.getBackends();
            const backendsList = (backends.backends || []).map(b => b.name).join(', ') || 'Simulator';

            document.getElementById('wizard-form').innerHTML = `
                <div class="form-group">
                    <p style="color: var(--color-text-secondary);">
                        <span style="color: var(--color-success);">✓</span> Detected backends: <strong>${backendsList}</strong>
                    </p>
                </div>
            `;
        } catch (error) {
            document.getElementById('wizard-form').innerHTML = `
                <div class="form-group">
                    <p style="color: var(--color-warning);">
                        ⚠ Could not detect backends. You can configure them later in Settings.
                    </p>
                </div>
            `;
        }
    }

    // Event system
    on(eventName, callback) {
        if (!this.eventListeners[eventName]) {
            this.eventListeners[eventName] = [];
        }
        this.eventListeners[eventName].push(callback);
    }

    emit(eventName, data) {
        if (this.eventListeners[eventName]) {
            this.eventListeners[eventName].forEach(callback => callback(data));
        }
    }
}

// Initialize app when DOM is ready
let app;
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        app = new CVGenApp();
    });
} else {
    app = new CVGenApp();
}
