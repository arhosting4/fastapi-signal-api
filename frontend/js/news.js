document.addEventListener('DOMContentLoaded', function() {
    const newsGrid = document.getElementById('news-grid');

    async function fetchNews() {
        try {
            const response = await fetch('/api/news');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const result = await response.json();

            newsGrid.innerHTML = ''; // Clear previous content

            // --- CRITICAL FIX: Check if data exists and is an array ---
            if (result.data && Array.isArray(result.data)) {
                if (result.data.length === 0) {
                    newsGrid.innerHTML = '<p>No news found at the moment.</p>';
                    return;
                }

                result.data.forEach(article => {
                    const articleCard = document.createElement('div');
                    articleCard.className = 'bg-white dark:bg-gray-800 p-4 rounded-lg shadow';
                    
                    articleCard.innerHTML = `
                        <h3 class="font-bold text-lg mb-2">${article.title}</h3>
                        <p class="text-sm text-gray-600 dark:text-gray-400 mb-2">Source: ${article.source}</p>
                        <p class="text-sm mb-4">${article.snippet}</p>
                        <a href="${article.url}" target="_blank" rel="noopener noreferrer" class="text-yellow-500 hover:underline">Read Full Story &rarr;</a>
                    `;
                    newsGrid.appendChild(articleCard);
                });
            } else {
                // Handle cases where there's a message like "No news available"
                newsGrid.innerHTML = `<p>${result.message || 'Could not fetch news at this time.'}</p>`;
            }
        } catch (error) {
            console.error('Error fetching news:', error);
            newsGrid.innerHTML = '<p>Failed to load news. Please try again later.</p>';
        }
    }

    fetchNews();
    // Refresh news every 15 minutes
    setInterval(fetchNews, 15 * 60 * 1000); 
});
