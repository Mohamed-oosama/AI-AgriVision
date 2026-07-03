document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('soilForm');
    const submitBtn = document.getElementById('submitBtn');
    const resultSection = document.getElementById('resultSection');
    const emptyState = document.getElementById('emptyState');
    const loadingState = document.getElementById('loadingState');
    const resultContent = document.getElementById('resultContent');
    const recommendationText = document.getElementById('recommendationText');
    const resCropName = document.getElementById('resCropName');

    // Configure Marked.js to parse markdown text securely
    if (typeof marked !== 'undefined') {
        marked.setOptions({
            breaks: true,
            gfm: true
        });
    }

    // Fetch crops from API
    async function loadCrops() {
        const cropSelect = document.getElementById('crop');
        try {
            const response = await fetch('/api/crops');
            if (!response.ok) throw new Error('Failed to fetch crops');
            const crops = await response.json();
            
            cropSelect.innerHTML = '<option value="" disabled selected>Select crop...</option>';
            crops.forEach(crop => {
                const option = document.createElement('option');
                option.value = crop.id;
                option.textContent = crop.name;
                // If it's tomato, pre-select it like the screenshot
                if (crop.id.toLowerCase() === 'tomato') {
                    option.selected = true;
                }
                cropSelect.appendChild(option);
            });
        } catch (error) {
            console.error('Error loading crops:', error);
            cropSelect.innerHTML = '<option value="" disabled selected>Error loading crops</option>';
            // Add a mock tomato option just in case the API is down
            cropSelect.innerHTML += '<option value="tomato">Tomato</option>';
        }
    }

    loadCrops();

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const cropEl = document.getElementById('crop');
        const cropName = cropEl.options[cropEl.selectedIndex].text;
        resCropName.textContent = cropName;

        // Get values
        const data = {
            crop: document.getElementById('crop').value,
            season: document.getElementById('season').value,
            n_val: parseFloat(document.getElementById('n_val').value),
            p_val: parseFloat(document.getElementById('p_val').value),
            k_val: parseFloat(document.getElementById('k_val').value),
            ph_val: parseFloat(document.getElementById('ph_val').value),
            soil_type: document.getElementById('soil_type').value,
            // Optional fields
            temperature: document.getElementById('temperature').value ? parseFloat(document.getElementById('temperature').value) : null,
            humidity: document.getElementById('humidity').value ? parseFloat(document.getElementById('humidity').value) : null,
            rainfall: document.getElementById('rainfall').value ? parseFloat(document.getElementById('rainfall').value) : null
        };

        // UI Updates for loading
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<div class="spinner" style="width: 20px; height: 20px; margin: 0; display: inline-block; vertical-align: middle;"></div> Analyzing...';
        
        emptyState.classList.add('hidden');
        resultContent.classList.add('hidden');
        loadingState.classList.remove('hidden');

        // Scroll to result section on mobile
        if (window.innerWidth <= 992) {
            resultSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }

        try {
            const response = await fetch('http://localhost:8000/predict', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || 'Failed to generate recommendation. Please try again.');
            }

            const result = await response.json();
            
            // Show result
            loadingState.classList.add('hidden');
            resultContent.classList.remove('hidden');
            
            // Parse Markdown to HTML
            if (typeof marked !== 'undefined') {
                recommendationText.innerHTML = marked.parse(result.recommendation);
            } else {
                recommendationText.innerText = result.recommendation;
            }
            
            // Update chart card text
            const chartContainer = document.getElementById('chartContainer');
            if(chartContainer) {
                chartContainer.innerHTML = `<p class="chart-empty">Analysis complete. Visualization is currently disabled.</p>`;
            }
            
        } catch (error) {
            console.error('Error:', error);
            loadingState.classList.add('hidden');
            emptyState.classList.remove('hidden');
            
            // Replace empty state with error message
            emptyState.innerHTML = `
                <div style="color: #ef4444;">
                    <i class="fa-solid fa-triangle-exclamation" style="font-size: 2rem; margin-bottom: 1rem;"></i>
                    <h3>Error Occurred</h3>
                    <p>${error.message}</p>
                </div>
            `;
        } finally {
            // Reset button
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> Generate Recommendation';
        }
    });
});
