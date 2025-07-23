document.addEventListener('DOMContentLoaded', function() {
    const signalsGrid = document.getElementById('signals-grid');
    const loadingMessage = document.getElementById('loading-signals');
    const winRateEl = document.getElementById('win-rate');
    const pnlEl = document.getElementById('pnl');

    async function fetchLiveSignals() {
        try {
            const response = await fetch('/api/live-signals');
            if (!response.ok) throw new Error('Network response was not ok');
            const signals = await response.json();

            if (signals && signals.length > 0) {
                if(loadingMessage) loadingMessage.style.display = 'none';
                signalsGrid.innerHTML = ''; // Clear grid
                signals.forEach(signal => {
                    const signalCard = document.createElement('div');
                    signalCard.className = 'bg-white dark:bg-gray-800 p-4 rounded-lg shadow';
                    const confidence = Math.round(signal.confidence);
                    const signalClass = signal.signal_type === 'BUY' ? 'text-green-500' : 'text-red-500';

                    signalCard.innerHTML = `
                        <div class="flex justify-between items-center mb-2">
                            <h3 class="font-bold text-lg">${signal.symbol}</h3>
                            <span class="text-xs text-gray-500">${signal.timeframe}</span>
                        </div>
                        <p class="mb-2"><span class="font-semibold ${signalClass}">${signal.signal_type}</span> @ ${signal.entry_price}</p>
                        <div class="text-xs">
                            <p>TP: ${signal.tp}</p>
                            <p>SL: ${signal.sl}</p>
                        </div>
                        <div class="mt-4">
                            <p class="text-xs text-center">Confidence: ${confidence}%</p>
                        </div>
                    `;
                    signalsGrid.appendChild(signalCard);
                });
            } else {
                 if(loadingMessage) {
                    loadingMessage.style.display = 'block';
                    loadingMessage.textContent = 'No active signals found. The AI is scanning the markets.';
                 }
            }
        } catch (error) {
            console.error('Error fetching live signals:', error);
            if(loadingMessage) {
                loadingMessage.style.display = 'block';
                loadingMessage.textContent = 'Failed to load signals.';
            }
        }
    }

    async function fetchSummary() {
        try {
            const response = await fetch('/api/summary');
            if (!response.ok) throw new Error('Network response was not ok');
            const summary = await response.json();
            
            // --- CRITICAL FIX: Check if summary data exists before using it ---
            if (summary && typeof summary.win_rate !== 'undefined' && typeof summary.pnl !== 'undefined') {
                winRateEl.textContent = `${summary.win_rate.toFixed(1)}%`;
                pnlEl.textContent = `$${summary.pnl.toFixed(2)}`;

                if(summary.pnl > 0) {
                    pnlEl.className = 'text-3xl font-bold text-green-500';
                } else if (summary.pnl < 0) {
                    pnlEl.className = 'text-3xl font-bold text-red-500';
                } else {
                    pnlEl.className = 'text-3xl font-bold text-gray-500';
                }
            } else {
                // This will run if the API returns empty data or a message
                winRateEl.textContent = '--%';
                pnlEl.textContent = '$--';
            }

        } catch (error) {
            console.error('Error fetching summary:', error);
            winRateEl.textContent = 'Error';
            pnlEl.textContent = 'Error';
        }
    }

    // Initial fetch
    fetchLiveSignals();
    fetchSummary();
    
    // Set intervals for periodic fetching
    setInterval(fetchLiveSignals, 30 * 1000); // Refresh every 30 seconds
    setInterval(fetchSummary, 5 * 60 * 1000); // Refresh every 5 minutes
});
