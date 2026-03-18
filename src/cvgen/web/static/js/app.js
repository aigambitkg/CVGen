/**
 * CVGen App — main application logic.
 */
(function () {
    'use strict';

    // Elements
    const views = document.querySelectorAll('.view');
    const navBtns = document.querySelectorAll('.nav-btn');
    const backendSelect = document.getElementById('backend-select');
    const loadingOverlay = document.getElementById('loading-overlay');
    const loadingText = document.getElementById('loading-text');

    // Circuit Builder
    const builder = new CircuitBuilder(
        document.getElementById('circuit-canvas'),
        document.getElementById('circuit-json-code')
    );

    // Navigation
    navBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const view = btn.dataset.view;
            navBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            views.forEach(v => {
                v.classList.toggle('active', v.id === `view-${view}`);
            });
        });
    });

    // Qubit count
    document.getElementById('num-qubits').addEventListener('change', (e) => {
        builder.setQubits(parseInt(e.target.value) || 3);
    });

    // Clear / Undo
    document.getElementById('btn-clear').addEventListener('click', () => builder.clear());
    document.getElementById('btn-undo').addEventListener('click', () => builder.undo());

    // Gate palette click handlers
    const paramDialog = document.getElementById('param-dialog');
    const targetDialog = document.getElementById('target-dialog');
    let pendingGate = null;

    document.querySelectorAll('.gate-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const gate = btn.dataset.gate;
            const multiGates = { cx: 2, cz: 2, swap: 2, ccx: 3 };
            const paramGates = ['rx', 'ry', 'rz'];

            if (gate in multiGates) {
                pendingGate = { gate, numTargets: multiGates[gate], params: [] };
                if (paramGates.includes(gate)) {
                    // param + multi (unlikely, but handle)
                    showParamDialog(gate);
                } else {
                    showTargetDialog(gate, multiGates[gate]);
                }
            } else if (paramGates.includes(gate)) {
                pendingGate = { gate, numTargets: 1, params: [] };
                showParamDialog(gate);
            } else {
                // Simple single-qubit gate: add to qubit 0 or next available
                showTargetDialog(gate, 1);
            }
        });
    });

    function showParamDialog(gate) {
        document.getElementById('param-dialog-title').textContent = `${gate.toUpperCase()} Parameter`;
        document.getElementById('param-value').value = '1.5708';
        paramDialog.showModal();
    }

    document.getElementById('param-cancel').addEventListener('click', () => {
        paramDialog.close();
        pendingGate = null;
    });

    document.getElementById('param-ok').addEventListener('click', () => {
        const val = parseFloat(document.getElementById('param-value').value) || 0;
        paramDialog.close();
        if (pendingGate) {
            pendingGate.params = [val];
            if (pendingGate.numTargets > 1) {
                showTargetDialog(pendingGate.gate, pendingGate.numTargets);
            } else {
                showTargetDialog(pendingGate.gate, 1);
            }
        }
    });

    function showTargetDialog(gate, numTargets) {
        const container = document.getElementById('target-qubit-selectors');
        container.innerHTML = '';
        document.getElementById('target-dialog-title').textContent =
            `${gate.toUpperCase()} — Select ${numTargets} qubit${numTargets > 1 ? 's' : ''}`;

        const labels = numTargets === 1 ? ['Target'] :
            numTargets === 2 ? ['Control', 'Target'] :
                ['Control 1', 'Control 2', 'Target'];

        for (let i = 0; i < numTargets; i++) {
            const label = document.createElement('label');
            label.style.display = 'block';
            label.style.marginBottom = '8px';
            label.innerHTML = `${labels[i]}: <select class="target-select input-sm">
                ${Array.from({ length: builder.numQubits }, (_, q) =>
                `<option value="${q}" ${q === i ? 'selected' : ''}>q${q}</option>`
            ).join('')}
            </select>`;
            container.appendChild(label);
        }

        targetDialog.showModal();
    }

    document.getElementById('target-cancel').addEventListener('click', () => {
        targetDialog.close();
        pendingGate = null;
    });

    document.getElementById('target-ok').addEventListener('click', () => {
        const selects = document.querySelectorAll('.target-select');
        const targets = Array.from(selects).map(s => parseInt(s.value));
        targetDialog.close();

        const params = (pendingGate && pendingGate.params) || [];
        const gate = pendingGate ? pendingGate.gate : 'h';
        builder.addGate(gate, targets, params);
        pendingGate = null;
    });

    // Run Circuit
    document.getElementById('btn-run').addEventListener('click', async () => {
        const shots = parseInt(document.getElementById('num-shots').value) || 1024;
        const backend = backendSelect.value;
        const circuitData = {
            ...builder.toJSON(),
            shots,
            backend,
        };

        showLoading('Executing quantum circuit...');
        try {
            const result = await CVGenAPI.executeCircuit(circuitData);
            displayCircuitResult(result);
        } catch (err) {
            alert('Execution failed: ' + err.message);
        } finally {
            hideLoading();
        }
    });

    function displayCircuitResult(result) {
        document.getElementById('results-placeholder').classList.add('hidden');
        document.getElementById('results-content').classList.remove('hidden');

        Visualizer.renderHistogram(
            document.getElementById('histogram'),
            result.counts,
            result.shots
        );

        document.getElementById('most-likely').textContent = `|${result.most_likely}>`;

        Visualizer.renderProbabilities(
            document.getElementById('probabilities'),
            result.probabilities
        );

        document.getElementById('raw-counts').textContent =
            JSON.stringify(result.counts, null, 2);
    }

    // Grover
    document.getElementById('btn-grover').addEventListener('click', async () => {
        const data = {
            num_qubits: parseInt(document.getElementById('grover-qubits').value),
            target_states: document.getElementById('grover-targets').value
                .split(',').map(s => parseInt(s.trim())).filter(n => !isNaN(n)),
            shots: parseInt(document.getElementById('grover-shots').value),
            backend: backendSelect.value,
        };

        showLoading('Running Grover quantum search...');
        try {
            const result = await CVGenAPI.runGrover(data);
            Visualizer.renderGroverResult(document.getElementById('grover-results'), result);
        } catch (err) {
            document.getElementById('grover-results').innerHTML =
                `<div style="color:var(--error)">Error: ${err.message}</div>`;
        } finally {
            hideLoading();
        }
    });

    // VQE
    document.getElementById('btn-vqe').addEventListener('click', async () => {
        const nq = parseInt(document.getElementById('vqe-qubits').value);
        // Build a simple cost observable: minimize P(|1...1>)
        const observable = {};
        for (let i = 0; i < 2 ** nq; i++) {
            const bits = i.toString(2).padStart(nq, '0');
            observable[bits] = i / (2 ** nq - 1 || 1);
        }

        const data = {
            num_qubits: nq,
            cost_observable: observable,
            ansatz_depth: parseInt(document.getElementById('vqe-depth').value),
            max_iterations: parseInt(document.getElementById('vqe-iterations').value),
            shots: parseInt(document.getElementById('vqe-shots').value),
            backend: backendSelect.value,
        };

        showLoading('Running VQE optimization...');
        try {
            const result = await CVGenAPI.runVQE(data);
            Visualizer.renderVQEResult(document.getElementById('vqe-results'), result);
        } catch (err) {
            document.getElementById('vqe-results').innerHTML =
                `<div style="color:var(--error)">Error: ${err.message}</div>`;
        } finally {
            hideLoading();
        }
    });

    // Load backends
    async function loadBackends() {
        try {
            const data = await CVGenAPI.getBackends();
            backendSelect.innerHTML = '';
            data.backends.forEach(b => {
                const opt = document.createElement('option');
                opt.value = b.name;
                opt.textContent = `${b.name} (${b.max_qubits}q)`;
                backendSelect.appendChild(opt);
            });

            // Render backends view
            const grid = document.getElementById('backends-list');
            grid.innerHTML = '';
            data.backends.forEach(b => {
                const card = document.createElement('div');
                card.className = 'backend-card';
                card.innerHTML = `
                    <h4>${b.name} <span class="type-badge ${b.backend_type}">${b.backend_type}</span></h4>
                    <div class="meta">
                        <span>Max qubits: ${b.max_qubits}</span>
                        <span>Statevector: ${b.supports_statevector ? 'Yes' : 'No'}</span>
                        <span>Gates: ${b.supported_gates.length}</span>
                        <span>Status: ${b.status}</span>
                    </div>
                `;
                grid.appendChild(card);
            });
        } catch (err) {
            console.warn('Could not load backends:', err.message);
        }
    }

    function showLoading(text) {
        loadingText.textContent = text;
        loadingOverlay.classList.remove('hidden');
    }

    function hideLoading() {
        loadingOverlay.classList.add('hidden');
    }

    // Init
    loadBackends();
})();
