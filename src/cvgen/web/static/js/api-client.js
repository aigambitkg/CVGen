/**
 * CVGen API Client — communicates with the FastAPI backend.
 */
const CVGenAPI = {
    baseURL: '/api/v1',

    async request(method, path, body = null) {
        const opts = {
            method,
            headers: { 'Content-Type': 'application/json' },
        };
        if (body) opts.body = JSON.stringify(body);

        const res = await fetch(this.baseURL + path, opts);
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: res.statusText }));
            throw new Error(err.detail || `HTTP ${res.status}`);
        }
        return res.json();
    },

    // Circuits
    async executeCircuit(circuitData) {
        return this.request('POST', '/circuits/execute', circuitData);
    },

    // Agents
    async runGrover(data) {
        return this.request('POST', '/agents/grover', data);
    },

    async runVQE(data) {
        return this.request('POST', '/agents/vqe', data);
    },

    // Backends
    async getBackends() {
        return this.request('GET', '/backends');
    },

    // Health
    async health() {
        return this.request('GET', '/health');
    },
};
