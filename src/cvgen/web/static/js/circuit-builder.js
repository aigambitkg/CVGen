/**
 * CVGen Circuit Builder — visual drag-and-drop circuit editor.
 */
class CircuitBuilder {
    constructor() {
        this.canvas = document.getElementById('circuit-canvas');
        this.jsonDisplay = document.getElementById('circuit-json-code');
        this.numQubits = 3;
        this.gates = []; // [{gate, targets, params}]
        this.history = [];

        this.setupEventListeners();
        this.render();
    }

    setupEventListeners() {
        // Qubit count change
        document.getElementById('num-qubits').addEventListener('change', (e) => {
            this.setQubits(parseInt(e.target.value) || 3);
        });

        // Clear button
        document.getElementById('btn-clear').addEventListener('click', () => this.clear());

        // Undo button
        document.getElementById('btn-undo').addEventListener('click', () => this.undo());

        // Run button
        document.getElementById('btn-run').addEventListener('click', () => this.executeCircuit());

        // Gate palette
        document.querySelectorAll('.gate-btn').forEach(btn => {
            btn.addEventListener('click', () => this.onGateClick(btn));
        });
    }

    onGateClick(btn) {
        const gate = btn.dataset.gate;
        const multiGates = { cx: 2, cz: 2, swap: 2, ccx: 3 };
        const paramGates = ['rx', 'ry', 'rz'];

        // Handle parameter gates
        if (paramGates.includes(gate)) {
            this.promptParameter(gate);
        }
        // Handle multi-qubit gates
        else if (multiGates[gate]) {
            this.promptTargets(gate, multiGates[gate]);
        }
        // Handle single-qubit gates
        else {
            this.promptTarget(gate);
        }
    }

    promptTarget(gate) {
        const qubits = Array.from({ length: this.numQubits }, (_, i) => i);
        const selection = prompt(`Select qubit for ${gate.toUpperCase()} (0-${this.numQubits - 1}):`, '0');

        if (selection !== null) {
            const qubit = parseInt(selection);
            if (!isNaN(qubit) && qubit >= 0 && qubit < this.numQubits) {
                this.addGate(gate, [qubit]);
            }
        }
    }

    promptParameter(gate) {
        const angle = prompt(`Enter angle (in radians) for ${gate.toUpperCase()}:`, '1.5708');

        if (angle !== null) {
            const param = parseFloat(angle);
            if (!isNaN(param)) {
                const qubit = prompt(`Select qubit for ${gate.toUpperCase()} (0-${this.numQubits - 1}):`, '0');
                if (qubit !== null) {
                    const q = parseInt(qubit);
                    if (!isNaN(q) && q >= 0 && q < this.numQubits) {
                        this.addGate(gate, [q], [param]);
                    }
                }
            }
        }
    }

    promptTargets(gate, count) {
        let targets = [];
        for (let i = 0; i < count; i++) {
            const q = prompt(`Select qubit ${i + 1} for ${gate.toUpperCase()} (0-${this.numQubits - 1}):`, String(i));
            if (q === null) return;

            const qubit = parseInt(q);
            if (isNaN(qubit) || qubit < 0 || qubit >= this.numQubits || targets.includes(qubit)) {
                alert('Invalid qubit selection');
                return;
            }
            targets.push(qubit);
        }

        this.addGate(gate, targets);
    }

    setQubits(n) {
        this.numQubits = Math.max(1, Math.min(20, n));
        // Remove gates that reference invalid qubits
        this.gates = this.gates.filter(g =>
            g.targets.every(t => t < this.numQubits)
        );
        this.render();
    }

    addGate(gate, targets, params = []) {
        this.history.push(JSON.stringify(this.gates));
        this.gates.push({ gate, targets, params });
        this.render();
    }

    undo() {
        if (this.history.length > 0) {
            this.gates = JSON.parse(this.history.pop());
            this.render();
        }
    }

    clear() {
        if (this.gates.length === 0) return;
        this.history.push(JSON.stringify(this.gates));
        this.gates = [];
        this.render();
    }

    removeGate(index) {
        this.history.push(JSON.stringify(this.gates));
        this.gates.splice(index, 1);
        this.render();
    }

    toJSON() {
        return {
            num_qubits: this.numQubits,
            gates: this.gates.map(g => ({
                gate: g.gate,
                targets: g.targets,
                params: g.params || [],
            })),
        };
    }

    async executeCircuit() {
        const circuitData = this.toJSON();
        const shots = parseInt(document.getElementById('num-shots').value) || 1024;

        try {
            const btn = document.getElementById('btn-run');
            btn.disabled = true;
            btn.textContent = 'Running...';

            const response = await CVGenAPI.executeCircuit({
                ...circuitData,
                shots: shots,
                backend: 'simulator',
            });

            this.displayResults(response);
        } catch (error) {
            alert(`Error executing circuit: ${error.message}`);
        } finally {
            const btn = document.getElementById('btn-run');
            btn.disabled = false;
            btn.textContent = 'Run Circuit';
        }
    }

    displayResults(response) {
        const resultsContent = document.getElementById('results-content');
        const resultsPlaceholder = document.getElementById('results-placeholder');

        resultsPlaceholder.classList.add('hidden');
        resultsContent.classList.remove('hidden');

        // Display histogram
        const histogram = document.getElementById('histogram');
        histogram.innerHTML = '';

        const counts = response.counts || {};
        const max = Math.max(...Object.values(counts));

        Object.entries(counts).forEach(([state, count]) => {
            const bar = document.createElement('div');
            bar.className = 'histogram-bar';
            bar.style.height = `${(count / max) * 100}%`;
            bar.title = `${state}: ${count}`;

            const label = document.createElement('div');
            label.className = 'histogram-bar-label';
            label.textContent = state;
            bar.appendChild(label);

            const value = document.createElement('div');
            value.className = 'histogram-bar-value';
            value.textContent = count;
            bar.appendChild(value);

            histogram.appendChild(bar);
        });

        // Most likely
        const mostLikelyEl = document.getElementById('most-likely');
        const mostLikely = Object.entries(counts).sort((a, b) => b[1] - a[1])[0];
        if (mostLikely) {
            mostLikelyEl.innerHTML = `<strong>${mostLikely[0]}</strong> (${mostLikely[1]} times, ${(mostLikely[1] * 100 / Object.values(counts).reduce((a, b) => a + b)).toFixed(1)}%)`;
        }

        // Probabilities
        const probEl = document.getElementById('probabilities');
        const total = Object.values(counts).reduce((a, b) => a + b);
        probEl.innerHTML = Object.entries(counts)
            .sort((a, b) => b[1] - a[1])
            .map(([state, count]) => {
                const prob = (count / total * 100).toFixed(2);
                return `<div style="margin-bottom: 0.5rem;"><span style="font-weight: 600;">${state}</span>: ${prob}% (${count} counts)</div>`;
            })
            .join('');
    }

    render() {
        this.canvas.innerHTML = '';

        // Build per-qubit gate timeline
        const timelines = Array.from({ length: this.numQubits }, () => []);
        const gateColumns = []; // For vertical connections

        this.gates.forEach((g, idx) => {
            const col = this._findNextColumn(timelines, g.targets);
            gateColumns.push({ gate: g, col, idx });
            g.targets.forEach(t => {
                while (timelines[t].length <= col) timelines[t].push(null);
                timelines[t][col] = { gate: g, idx };
            });
        });

        const maxCols = Math.max(1, ...timelines.map(t => t.length));

        for (let q = 0; q < this.numQubits; q++) {
            const line = document.createElement('div');
            line.style.display = 'flex';
            line.style.alignItems = 'center';
            line.style.marginBottom = '1rem';
            line.style.gap = '0.5rem';

            const label = document.createElement('div');
            label.style.fontWeight = '600';
            label.style.width = '40px';
            label.style.textAlign = 'center';
            label.style.color = 'var(--color-accent-primary)';
            label.textContent = `q${q}`;
            line.appendChild(label);

            const wire = document.createElement('div');
            wire.style.display = 'flex';
            wire.style.flex = '1';
            wire.style.alignItems = 'center';
            wire.style.gap = '4px';
            wire.style.padding = '0.5rem';
            wire.style.borderBottom = '2px solid var(--color-border)';

            for (let c = 0; c < maxCols; c++) {
                const entry = timelines[q][c];
                if (entry) {
                    const gateEl = this._createGateElement(entry.gate, q, entry.idx);
                    wire.appendChild(gateEl);
                } else {
                    const spacer = document.createElement('div');
                    spacer.style.width = '36px';
                    spacer.style.height = '36px';
                    spacer.style.flexShrink = '0';
                    wire.appendChild(spacer);
                }
            }

            line.appendChild(wire);
            this.canvas.appendChild(line);
        }

        // Update JSON display
        if (this.jsonDisplay) {
            this.jsonDisplay.textContent = JSON.stringify(this.toJSON(), null, 2);
        }
    }

    _findNextColumn(timelines, targets) {
        let col = 0;
        for (const t of targets) {
            col = Math.max(col, timelines[t].length);
        }
        return col;
    }

    _createGateElement(gate, qubit, index) {
        const el = document.createElement('div');
        el.style.width = '36px';
        el.style.height = '36px';
        el.style.display = 'flex';
        el.style.alignItems = 'center';
        el.style.justifyContent = 'center';
        el.style.borderRadius = 'var(--radius-md)';
        el.style.cursor = 'pointer';
        el.style.fontSize = '0.75rem';
        el.style.fontWeight = '600';
        el.style.border = '1px solid var(--color-border)';
        el.style.flexShrink = '0';
        el.title = `${gate.gate.toUpperCase()}${gate.params.length ? '(' + gate.params.map(p => p.toFixed(2)).join(',') + ')' : ''} on q${gate.targets.join(',')}`;

        const isControl = gate.targets.length > 1 && qubit === gate.targets[0] && gate.gate !== 'swap';

        if (isControl) {
            el.style.background = 'var(--color-border)';
            el.style.borderRadius = '50%';
            el.style.width = '20px';
            el.style.height = '20px';
            el.style.border = '2px solid var(--color-accent-primary)';
        } else if (gate.gate === 'measure') {
            el.style.background = 'var(--color-accent-primary)';
            el.style.color = 'var(--color-bg-primary)';
            el.textContent = 'M';
        } else if (['rx', 'ry', 'rz'].includes(gate.gate)) {
            el.style.background = 'var(--color-accent-secondary)';
            el.style.color = 'white';
            el.textContent = gate.gate.toUpperCase();
        } else if (['cx', 'cz', 'swap', 'ccx'].includes(gate.gate)) {
            el.style.background = 'var(--color-accent-tertiary)';
            el.style.color = 'white';
            el.textContent = gate.gate === 'swap' ? 'SW' : gate.gate.toUpperCase();
        } else {
            el.style.background = 'var(--color-accent-primary)';
            el.style.color = 'var(--color-bg-primary)';
            el.textContent = gate.gate.toUpperCase();
        }

        el.addEventListener('click', () => this.removeGate(index));
        el.addEventListener('hover', () => {
            el.style.filter = 'brightness(1.2)';
        });

        return el;
    }
}
