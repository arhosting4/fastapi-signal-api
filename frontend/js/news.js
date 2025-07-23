document.addEventListener('DOMContentLoaded', () => {
    const newsGrid = document.getElementById('news-grid');
    const messageContainer = document.getElementById('news-message-container');
    const API_BASE_URL = window.location.origin;

    function showMessage(type, text) {
        newsGrid.innerHTML = '';
        messageContainer.innerHTML = `<div class="message message-${type}">${text}</div>`;
    }

    function renderNews(newsData) {
        if (!newsData || !newsData.data) {
            showMessage('info', newsData.message || 'No news available.');
            return;
        }
        newsGrid.innerHTML = newsData.data.map(item => `
            <div class="news-card">
                <img src="${item.image_url}" alt="News Image" class="news-image">
                <div class="news-content">
                    <h3>${item.title}</h3>
                    <p class="snippet">${item.snippet}</p>
                    <a href="${item.url}" target="_blank" rel="noopener noreferrer" class="read-more">Read Full Story</a>
                    <span class="source">Source: ${item.source}</span>
                </div>
            </div>
        `).join('');
    }

    async function fetchNews() {
        showMessage('loading', '<div class="loader"></div>');
        try {
            const response = await fetch(`${API_BASE_URL}/api/news`);
            if (!response.ok) throw new Error('Failed to fetch news.');
            const news = await response.json();
            
            messageContainer.innerHTML = '';
            renderNews(news);
        } catch (error) {
            console.error("Error fetching news:", error);
            showMessage('error', 'Failed to load news.');
        }
    }

    fetchNews();
});
