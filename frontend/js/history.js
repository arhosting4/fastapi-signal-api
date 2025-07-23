document.addEventListener('DOMContentLoaded', () => {
    const tableBody = document.getElementById('history-table-body');
    const messageContainer = document.getElementById('history-message-container');
    const API_BASE_URL = window.location.origin;

    function showMessage(type, text) {
        tableBody.innerHTML = '';
        messageContainer.innerHTML = `<div class="message message-${type}">${text}</div>`;
    }

    function renderHistory(trades) {
        tableBody.innerHTML = trades.map(trade => `
            <tr>
                <td>${trade.symbol} (${trade.timeframe})</td>
                <td class="${trade.signal_type.toLowerCase()}">${trade.signal_type}</td>
                <td>${trade.entry_price.toFixed(5)}</td>
                <td><span class="status-tag ${trade.outcome}">${trade.outcome.replace('_', ' ')}</span></td>
                <td>${new Date(trade.closed_at).toLocaleString()}</td>
            </tr>
        `).join('');
    }

    async function fetchTradeHistory() {
        showMessage('loading', '<div class="loader"></div>');
        try {
            const response = await fetch(`${API_BASE_URL}/api/history`);
            if (!response.ok) throw new Error('Failed to fetch trade history.');
            const trades = await response.json();

            messageContainer.innerHTML = '';
            if (trades.length === 0) {
                showMessage('info', 'No completed trades found yet.');
            } else {
                renderHistory(trades);
            }
        } catch (error) {
            console.error("Error fetching trade history:", error);
            showMessage('error', 'Failed to load trade history.');
        }
    }

    fetchTradeHistory();
});```

#### **فائل 15: `frontend/news.html`**
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Market News - ScalpMaster AI</title>
    <link rel="stylesheet" href="/css/main.css">
</head>
<body>
    <div class="container">
        <header>
            <!-- Header content -->
        </header>
        <main>
            <section class="market-news">
                <h2>Market News</h2>
                <div id="news-message-container"></div>
                <div class="news-grid" id="news-grid">
                    <!-- News cards will be injected here -->
                </div>
            </section>
        </main>
        <nav class="mobile-nav">
            <!-- Mobile navigation -->
        </nav>
    </div>
    <script src="/js/main.js"></script>
    <script src="/js/news.js"></script>
</body>
</html>
