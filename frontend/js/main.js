document.addEventListener('DOMContentLoaded', function() {
    // --- THEME TOGGLER (COMMON LOGIC) ---
    const themeToggle = document.getElementById('theme-toggle');
    const html = document.documentElement;

    // Apply the saved theme on load
    if (localStorage.getItem('theme') === 'dark') {
        html.classList.add('dark');
        if (themeToggle) themeToggle.innerHTML = '<i class="fas fa-sun"></i>';
    } else {
        html.classList.remove('dark');
        if (themeToggle) themeToggle.innerHTML = '<i class="fas fa-moon"></i>';
    }

    // Theme toggle button event listener
    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            html.classList.toggle('dark');
            if (html.classList.contains('dark')) {
                localStorage.setItem('theme', 'dark');
                themeToggle.innerHTML = '<i class="fas fa-sun"></i>';
            } else {
                localStorage.setItem('theme', 'light');
                themeToggle.innerHTML = '<i class="fas fa-moon"></i>';
            }
        });
    }

    // --- PAGE-SPECIFIC LOGIC ---
    // This function checks which page we are on and runs the relevant code.
    function route() {
        const path = window.location.pathname;

        if (path === '/' || path.endsWith('/index.html')) {
            runDashboardPage();
        } else if (path.endsWith('/history.html')) {
            runHistoryPage();
        } else if (path.endsWith('/news.html')) {
            runNewsPage();
        }
    }
    
    // --- DASHBOARD PAGE LOGIC ---
    function runDashboardPage() {
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
                    signalsGrid.innerHTML = '';
                    signals.forEach(signal => {
                        const signalCard = document.createElement('div');
                        signalCard.className = 'bg-white dark:bg-gray-800 p-4 rounded-lg shadow';
                        const confidence = Math.round(signal.confidence);
                        const signalClass = signal.signal_type === 'BUY' ? 'text-green-500' : 'text-red-500';
                        signalCard.innerHTML = `<div class="flex justify-between items-center mb-2"><h3 class="font-bold text-lg">${signal.symbol}</h3><span class="text-xs text-gray-500">${signal.timeframe}</span></div><p class="mb-2"><span class="font-semibold ${signalClass}">${signal.signal_type}</span> @ ${signal.entry_price}</p><div class="text-xs"><p>TP: ${signal.tp}</p><p>SL: ${signal.sl}</p></div><div class="mt-4"><p class="text-xs text-center">Confidence: ${confidence}%</p></div>`;
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
                
                if (summary && typeof summary.win_rate !== 'undefined' && typeof summary.pnl !== 'undefined') {
                    winRateEl.textContent = `${summary.win_rate.toFixed(1)}%`;
                    pnlEl.textContent = `$${summary.pnl.toFixed(2)}`;
                    if(summary.pnl > 0) pnlEl.className = 'text-3xl font-bold text-green-500';
                    else if (summary.pnl < 0) pnlEl.className = 'text-3xl font-bold text-red-500';
                    else pnlEl.className = 'text-3xl font-bold text-gray-500';
                } else {
                    winRateEl.textContent = '--%';
                    pnlEl.textContent = '$--';
                }
            } catch (error) {
                console.error('Error fetching summary:', error);
                winRateEl.textContent = 'Error';
                pnlEl.textContent = 'Error';
            }
        }

        fetchLiveSignals();
        fetchSummary();
        setInterval(fetchLiveSignals, 30 * 1000);
        setInterval(fetchSummary, 5 * 60 * 1000);
    }

    // --- HISTORY PAGE LOGIC ---
    function runHistoryPage() {
        const tableBody = document.getElementById('history-table-body');
        async function fetchHistory() {
            try {
                const response = await fetch('/api/history');
                if (!response.ok) throw new Error('Network response was not ok');
                const trades = await response.json();
                tableBody.innerHTML = '';
                if (trades && trades.length > 0) {
                    trades.forEach(trade => {
                        let resultClass = '';
                        if (trade.outcome === 'tp_hit') resultClass = 'text-green-500';
                        else if (trade.outcome === 'sl_hit') resultClass = 'text-red-500';
                        else resultClass = 'text-gray-500';
                        const row = `<tr><td class="p-4">${trade.symbol}</td><td class="p-4">${trade.entry_price}</td><td class="p-4 font-bold ${resultClass}">${trade.outcome.replace('_', ' ').toUpperCase()}</td><td class="p-4">${new Date(trade.closed_at).toLocaleString()}</td></tr>`;
                        tableBody.innerHTML += row;
                    });
                } else {
                    tableBody.innerHTML = '<tr><td colspan="4" class="p-4 text-center">No trade history found.</td></tr>';
                }
            } catch (error) {
                console.error('Error fetching history:', error);
                tableBody.innerHTML = '<tr><td colspan="4" class="p-4 text-center">Failed to load trade history.</td></tr>';
            }
        }
        fetchHistory();
        setInterval(fetchHistory, 60 * 1000);
    }

    // --- NEWS PAGE LOGIC ---
    function runNewsPage() {
        const newsGrid = document.getElementById('news-grid');
        async function fetchNews() {
            try {
                const response = await fetch('/api/news');
                if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
                const result = await response.json();
                newsGrid.innerHTML = '';
                if (result.data && Array.isArray(result.data) && result.data.length > 0) {
                    result.data.forEach(article => {
                        const articleCard = document.createElement('div');
                        articleCard.className = 'bg-white dark:bg-gray-800 p-4 rounded-lg shadow';
                        articleCard.innerHTML = `<h3 class="font-bold text-lg mb-2">${article.title}</h3><p class="text-sm text-gray-600 dark:text-gray-400 mb-2">Source: ${article.source}</p><p class="text-sm mb-4">${article.snippet}</p><a href="${article.url}" target="_blank" rel="noopener noreferrer" class="text-yellow-500 hover:underline">Read Full Story &rarr;</a>`;
                        newsGrid.appendChild(articleCard);
                    });
                } else {
                    newsGrid.innerHTML = `<p>${result.message || 'No news found at the moment.'}</p>`;
                }
            } catch (error) {
                console.error('Error fetching news:', error);
                newsGrid.innerHTML = '<p>Failed to load news. Please try again later.</p>';
            }
        }
        fetchNews();
        setInterval(fetchNews, 15 * 60 * 1000);
    }

    // Run the routing function to execute the correct code for the current page
    route();
});
                        
