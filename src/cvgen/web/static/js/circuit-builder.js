/**
 * CVGen Circuit Builder — visual drag-and-drop circuit editor.
 */
class CircuitBuilder {
    constructor(canvasEl, jsonEl) {
        this.canvas = canvasEl;
        this.jsonDisplay = jsonEl;
        this.numQubits = 3;
        this.gates = []; // [{gate, targets, params}]
        this.history = [];
        this.render();
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
            line.className = 'qubit-line';

            const label = document.createElement('div');
            label.className = 'qubit-label';
            label.textContent = `q${q}`;
            line.appendChild(label);

            const wire = document.createElement('div');
            wire.className = 'qubit-wire';

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
        el.className = 'gate-on-wire';
        el.title = `${gate.gate.toUpperCase()}${gate.params.length ? '(' + gate.params.map(p => p.toFixed(2)).join(',') + ')' : ''} on q${gate.targets.join(',')}`;

        const isControl = gate.targets.length > 1 && qubit === gate.targets[0] && gate.gate !== 'swap';

        if (isControl) {
            el.className += ' control-dot';
        } else if (gate.gate === 'measure') {
            el.className += ' measure-gate';
            el.textContent = 'M';
        } else if (['rx', 'ry', 'rz'].includes(gate.gate)) {
            el.className += ' param';
            el.textContent = gate.gate.toUpperCase();
        } else if (['cx', 'cz', 'swap', 'ccx'].includes(gate.gate)) {
            el.className += ' multi';
            el.textContent = gate.gate === 'swap' ? 'SW' : gate.gate.toUpperCase();
        } else {
            el.className += ' single';
            el.textContent = gate.gate.toUpperCase();
        }

        el.addEventListener('click', () => this.removeGate(index));
        return el;
    }
}
