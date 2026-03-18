/**
 * CVGen Chat Interface Tab
 * Natural language interface for quantum circuit creation and execution
 */

class ChatInterface {
    constructor() {
        this.messages = [];
        this.isWaiting = false;
        this.templates = {
            bell: {
                name: 'Bell State erstellen',
                prompt: 'Create a Bell state (entangled qubits) with 2 qubits'
            },
            grover: {
                name: 'Grover Search mit 4 Qubits',
                prompt: 'Run Grover\'s quantum search algorithm with 4 qubits searching for states 3 and 5'
            },
            vqe: {
                name: 'VQE Optimierung',
                prompt: 'Run a VQE optimization with 2 qubits and depth 2'
            },
            qft: {
                name: 'Quantum Fourier Transform',
                prompt: 'Create and execute a Quantum Fourier Transform circuit with 3 qubits'
            }
        };

        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadChatHistory();
        this.renderTemplates();
    }

    setupEventListeners() {
        const chatInput = document.getElementById('chat-input');
        const sendBtn = document.getElementById('chat-send-btn');

        // Send button click
        sendBtn.addEventListener('click', () => this.sendMessage());

        // Enter key to send (Shift+Enter for newline)
        chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Template buttons
        document.querySelectorAll('.template-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const templateKey = btn.dataset.template;
                const template = this.templates[templateKey];
                if (template) {
                    chatInput.value = template.prompt;
                    chatInput.focus();
                }
            });
        });
    }

    renderTemplates() {
        const container = document.getElementById('chat-templates');
        container.innerHTML = Object.entries(this.templates).map(([key, template]) => `
            <button class="template-btn" data-template="${key}">
                <div class="template-btn-title">${template.name}</div>
                <div class="template-btn-desc">${template.prompt.substring(0, 40)}...</div>
            </button>
        `).join('');

        // Re-attach listeners
        document.querySelectorAll('.template-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const templateKey = btn.dataset.template;
                const template = this.templates[templateKey];
                if (template) {
                    document.getElementById('chat-input').value = template.prompt;
                    document.getElementById('chat-input').focus();
                }
            });
        });
    }

    async sendMessage() {
        const input = document.getElementById('chat-input');
        const message = input.value.trim();

        if (!message || this.isWaiting) return;

        // Add user message to chat
        this.addMessage('user', message);
        input.value = '';
        input.style.height = 'auto';

        this.isWaiting = true;
        const sendBtn = document.getElementById('chat-send-btn');
        sendBtn.disabled = true;

        try {
            // Call the quantum-ask endpoint
            const response = await CVGenAPI.quantumAsk({
                query: message,
                include_code: true,
                include_execution: true,
            });

            // Add response
            this.addMessage('assistant', response.answer);

            // Add code if present
            if (response.code) {
                this.addCodeBlock(response.code);
            }

            // Add result visualization if present
            if (response.result) {
                this.addResultVisualization(response.result);
            }

            // Save to history
            this.saveChatHistory();
        } catch (error) {
            this.addMessage('assistant', `Error: ${error.message}`);
        } finally {
            this.isWaiting = false;
            sendBtn.disabled = false;
            document.getElementById('chat-input').focus();
        }
    }

    addMessage(role, content) {
        const history = document.getElementById('chat-history');
        const message = document.createElement('div');
        message.className = `chat-message ${role}`;

        const bubble = document.createElement('div');
        bubble.className = 'chat-bubble';
        bubble.textContent = content;

        message.appendChild(bubble);
        history.appendChild(message);
        history.scrollTop = history.scrollHeight;

        this.messages.push({ role, content, timestamp: new Date().toISOString() });
    }

    addCodeBlock(code) {
        const history = document.getElementById('chat-history');
        const codeBlock = document.createElement('div');
        codeBlock.className = 'chat-code';
        codeBlock.style.marginTop = '0.75rem';
        codeBlock.style.marginBottom = '0.75rem';

        // Simple syntax highlighting
        const highlighted = this.highlightCode(code);
        codeBlock.innerHTML = highlighted;

        history.appendChild(codeBlock);
        history.scrollTop = history.scrollHeight;
    }

    addResultVisualization(result) {
        const history = document.getElementById('chat-history');
        const resultContainer = document.createElement('div');
        resultContainer.style.marginTop = '0.75rem';
        resultContainer.style.marginBottom = '0.75rem';
        resultContainer.style.padding = '1rem';
        resultContainer.style.background = 'var(--color-bg-tertiary)';
        resultContainer.style.borderRadius = 'var(--radius-md)';
        resultContainer.style.border = '1px solid var(--color-border)';

        if (result.histogram) {
            const histogram = this.createHistogram(result.histogram);
            resultContainer.appendChild(histogram);
        }

        if (result.summary) {
            const summary = document.createElement('div');
            summary.style.marginTop = '1rem';
            summary.style.fontSize = '0.9rem';
            summary.style.color = 'var(--color-text-secondary)';
            summary.textContent = result.summary;
            resultContainer.appendChild(summary);
        }

        history.appendChild(resultContainer);
        history.scrollTop = history.scrollHeight;
    }

    createHistogram(data) {
        const container = document.createElement('div');
        container.className = 'histogram-container';
        container.style.height = '150px';

        const max = Math.max(...Object.values(data));

        Object.entries(data).forEach(([state, count]) => {
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

            container.appendChild(bar);
        });

        return container;
    }

    highlightCode(code) {
        // Simple syntax highlighting without external library
        return code
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;')
            .replace(/\b(def|class|import|from|if|else|return|for|while)\b/g, '<span style="color: var(--color-accent-secondary);">$1</span>')
            .replace(/#.*/g, '<span style="color: var(--color-text-tertiary);">$&</span>')
            .replace(/(['"]).*?\1/g, '<span style="color: var(--color-success);">$&</span>');
    }

    saveChatHistory() {
        localStorage.setItem('cvgen_chat_history', JSON.stringify(this.messages.slice(-20)));
    }

    loadChatHistory() {
        const stored = localStorage.getItem('cvgen_chat_history');
        if (stored) {
            this.messages = JSON.parse(stored);
            // Render previous messages
            this.messages.forEach(msg => {
                this.addMessage(msg.role, msg.content);
            });
        }
    }
}
