document.addEventListener('DOMContentLoaded', () => {
    const signalsGrid = document.getElementById('signals-grid');
    const messageContainer = document.getElementById('signals-message-container');
    const winRateValue = document.getElementById('win-rate-value');
    const pnlValue = document.getElementById('pnl-value');

    const API_BASE_URL = window.location.origin;

    function showMessage(type, text) {
        signalsGrid.innerHTML = '';
        let messageHTML = '';
        if (type === 'loading') {
            messageHTML = `<div class="loader"></div>`;
        } else {
            messageHTML = `<div class="message message-${type}">${text}</div>`;
        }
        messageContainer.innerHTML = messageHTML;
    }

    function renderSignals(signals) {
        signalsGrid.innerHTML = signals.map(signal => `
            <div class="signal-card">
                <div class="card-header">
                    <span class="symbol">${signal.symbol} (${signal.timeframe})</span>
                    <span class="signal-type ${signal.signal_type.toLowerCase()}">${signal.signal_type}</span>
                </div>
                <div class="card-body">
                    <p><strong>Entry:</strong> ${signal.entry_price.toFixed(5)}</p>
                    <p><strong>TP:</strong> ${signal.tp_price.toFixed(5)}</p>
                    <p><strong>SL:</strong> ${signal.sl_price.toFixed(5)}</p>
                </div>
                <div class="card-footer">
                    <span>Confidence: ${signal.confidence.toFixed(2)}%</span>
                </div>
            </div>
        `).join('');
    }

    async function fetchLiveSignals() {
        try {
            const response = await fetch(`${API_BASE_URL}/api/live-signals`);
            if (!response.ok) throw new Error('Network response was not ok.');
            const signals = await response.json();
            
            messageContainer.innerHTML = '';
            if (signals.length === 0) {
                showMessage('info', 'No active signals found. The AI is scanning the markets.');
            } else {
                renderSignals(signals);
            }
        } catch (error) {
            console.error("Error fetching live signals:", error);
            showMessage('error', 'Failed to load signals. Please try again in a few moments.');
        }
    }

    async function fetchSummaryData() {
        try {
            const response = await fetch(`${API_BASE_URL}/api/summary`);
            if (!response.ok) throw new Error('Failed to fetch summary data.');
            const summary = await response.json();
            winRateValue.textContent = `${summary.win_rate_24h.toFixed(2)}%`;
            pnlValue.textContent = `$${summary.today_pl.toFixed(2)}`;
        } catch (error) {
            console.error("Error fetching summary data:", error);
            winRateValue.textContent = 'Error';
            pnlValue.textContent = 'Error';
        }
    }

    // Initial Load
    showMessage('loading');
    fetchLiveSignals();
    fetchSummaryData();

    // Set intervals for refreshing data
    setInterval(fetchLiveSignals, 30000); // Refresh signals every 30 seconds
    setInterval(fetchSummaryData, 60000); // Refresh summary every 60 seconds
});
                          
