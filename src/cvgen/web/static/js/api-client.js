/**
 * CVGen API Client — communicates with the FastAPI backend.
 * Enhanced with new endpoints and WebSocket support
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

    async requestStream(method, path, body = null) {
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
        return res;
    },

    // ============ CIRCUITS ============
    async executeCircuit(circuitData) {
        return this.request('POST', '/circuits/execute', circuitData);
    },

    // ============ AGENTS ============
    async runGrover(data) {
        return this.request('POST', '/agents/grover', data);
    },

    async runVQE(data) {
        return this.request('POST', '/agents/vqe', data);
    },

    async quantumAsk(query) {
        return this.request('POST', '/agents/quantum-ask', query);
    },

    // ============ BACKENDS ============
    async getBackends() {
        return this.request('GET', '/backends');
    },

    async getBackend(name) {
        return this.request('GET', `/backends/${name}`);
    },

    async testBackend(name) {
        return this.request('POST', `/backends/${name}/test`, {});
    },

    // ============ JOBS ============
    async getJobs(limit = 10) {
        return this.request('GET', `/jobs?limit=${limit}`);
    },

    async getJob(jobId) {
        return this.request('GET', `/jobs/${jobId}`);
    },

    async cancelJob(jobId) {
        return this.request('POST', `/jobs/${jobId}/cancel`, {});
    },

    // ============ RAG ============
    async ragStatus() {
        return this.request('GET', '/rag/status');
    },

    async ragIndex(documents) {
        return this.request('POST', '/rag/index', { documents });
    },

    // ============ HEALTH ============
    async health() {
        return this.request('GET', '/health');
    },
};
