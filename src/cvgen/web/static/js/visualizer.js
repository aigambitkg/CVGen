/**
 * CVGen Visualizer — renders quantum measurement results.
 */
const Visualizer = {
    renderHistogram(container, counts, shots) {
        container.innerHTML = '';
        const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1]);
        const maxCount = Math.max(...sorted.map(e => e[1]));

        for (const [state, count] of sorted) {
            const pct = (count / shots * 100).toFixed(1);
            const barWidth = (count / maxCount * 100).toFixed(1);

            const row = document.createElement('div');
            row.className = 'hist-row';
            row.innerHTML = `
                <span class="hist-label">${state}</span>
                <div class="hist-bar-container">
                    <div class="hist-bar" style="width: ${barWidth}%"></div>
                </div>
                <span class="hist-value">${count} (${pct}%)</span>
            `;
            container.appendChild(row);
        }
    },

    renderProbabilities(container, probabilities) {
        container.innerHTML = '';
        const sorted = Object.entries(probabilities).sort((a, b) => b[1] - a[1]);

        for (const [state, prob] of sorted) {
            const row = document.createElement('div');
            row.className = 'prob-row';
            row.innerHTML = `<span>${state}</span><span>${(prob * 100).toFixed(2)}%</span>`;
            container.appendChild(row);
        }
    },

    renderGroverResult(container, result) {
        container.innerHTML = `
            <div class="${result.success ? 'success' : 'info'}">
                <strong>Solutions found:</strong> ${result.solutions.length > 0 ? result.solutions.join(', ') : 'None'}<br>
                <span class="info">Search space: ${result.search_space_size} states (${result.num_qubits} qubits)</span><br>
                <span class="info">Quantum steps: ${result.total_steps}</span>
            </div>
        `;
    },

    renderVQEResult(container, result) {
        let histHtml = '';
        if (result.cost_history && result.cost_history.length > 0) {
            const max = Math.max(...result.cost_history);
            const min = Math.min(...result.cost_history);
            const range = max - min || 1;
            const bars = result.cost_history.map(c => {
                const h = Math.max(2, ((c - min) / range) * 40);
                return `<div style="width:3px;height:${h}px;background:var(--accent);display:inline-block;vertical-align:bottom;margin:0 1px;"></div>`;
            }).join('');
            histHtml = `<div style="margin-top:8px;"><strong>Cost convergence:</strong><div style="height:48px;display:flex;align-items:flex-end;">${bars}</div></div>`;
        }

        container.innerHTML = `
            <div class="${result.success ? 'success' : 'info'}">
                <strong>Optimal cost:</strong> ${result.optimal_cost.toFixed(6)}<br>
                <span class="info">Converged: ${result.converged ? 'Yes' : 'No'}</span><br>
                <span class="info">Evaluations: ${result.num_evaluations}</span>
                ${histHtml}
            </div>
        `;
    },
};
