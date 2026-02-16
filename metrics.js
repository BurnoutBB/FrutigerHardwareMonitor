// Konfiguracja
// Automatycznie wykryj adres serwera na podstawie bieżącego hosta
const currentHost = window.location.hostname;
const API_URL = `http://${currentHost}:5000/api/metrics`;
const UPDATE_INTERVAL = 1000; // 1 sekunda

console.log('🌐 Wykryty host:', currentHost);
console.log('📡 API URL:', API_URL);

// Funkcja do pobierania danych z API
async function fetchMetrics() {
    try {
        console.log('📡 Próba połączenia:', API_URL);
        const response = await fetch(API_URL);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        console.log('✅ Dane otrzymane:', data);
        updateUI(data);
        
    } catch (error) {
        console.error('❌ Błąd połączenia:', error);
        
        // Pokaż błąd użytkownikowi
        const networkDiv = document.querySelector('#network h1');
        if (networkDiv) {
            if (error.message.includes('Failed to fetch')) {
                networkDiv.textContent = `Nie można połączyć z ${currentHost}:5000 - Sprawdź czy serwer działa`;
            } else {
                networkDiv.textContent = `Błąd: ${error.message}`;
            }
            networkDiv.style.color = '#ff6b6b';
        }
    }
}

// Funkcja do aktualizacji UI
function updateUI(data) {
    console.log('Otrzymane dane:', data);
    
    // Aktualizacja CPU
    const cpuProgress = document.querySelector('#usage div:nth-child(1) progress');
    const cpuTitle = document.querySelector('#usage div:nth-child(1) h1');
    if (cpuProgress && data.cpu) {
        cpuProgress.value = data.cpu.usage;
        cpuProgress.max = 100;
        cpuTitle.textContent = `CPU Usage ${data.cpu.usage}%`;
        console.log('CPU zaktualizowane:', data.cpu.usage + '%');
    }
    
    // Aktualizacja RAM
    const ramProgress = document.querySelector('#usage div:nth-child(2) progress');
    const ramTitle = document.querySelector('#usage div:nth-child(2) h1');
    if (ramProgress && data.ram) {
        ramProgress.value = data.ram.usage;
        ramProgress.max = 100;
        ramTitle.textContent = `RAM Usage ${data.ram.usage}%`;
    }
    
    // Aktualizacja GPU
    const gpuProgress = document.querySelector('#usage div:nth-child(3) progress');
    const gpuTitle = document.querySelector('#usage div:nth-child(3) h1');
    if (gpuProgress && data.gpu) {
        gpuProgress.value = data.gpu.usage;
        gpuProgress.max = 100;
        gpuTitle.textContent = `GPU Usage ${data.gpu.usage}%`;
    }
    
    // Aktualizacja dysku
    const diskProgress = document.querySelector('#drive_usage progress');
    const driveUsageDiv = document.querySelector('#drive_usage');
    if (diskProgress && driveUsageDiv && data.disk) {
        diskProgress.value = data.disk.usage;
        diskProgress.max = 100;
        // Aktualizacja tekstu przez atrybut data
        const diskText = `${data.disk.used_gb}GB / ${data.disk.total_gb}GB`;
        driveUsageDiv.setAttribute('data-usage', diskText);
        console.log('Dysk zaktualizowany:', diskText, 'Usage:', data.disk.usage + '%');
    }
    
    // Aktualizacja temperatur
    const tempTable = document.querySelector('#actual_temperature table');
    if (tempTable) {
        tempTable.innerHTML = `
            <tr>
                <th>CPU</th>
                <th>${data.cpu.temperature}°C</th>
            </tr>
            <tr>
                <th>GPU</th>
                <th>${data.gpu.temperature}°C</th>
            </tr>
            <tr>
                <th>SSD</th>
                <th>${data.disk.temperature}°C</th>
            </tr>
        `;
    }
    
    // Aktualizacja listy procesów
    const processTable = document.querySelector('#proces_monitor table');
    if (processTable && data.processes) {
        let processHTML = `
            <tr>
                <th>Proces name</th>
                <th>CPU</th>
                <th>RAM</th>
                <th>GPU</th>
            </tr>
        `;
        
        data.processes.forEach(process => {
            processHTML += `
                <tr>
                    <td>${process.name}</td>
                    <td>${process.cpu}%</td>
                    <td>${process.ram}%</td>
                    <td>${process.gpu}%</td>
                </tr>
            `;
        });
        
        processTable.innerHTML = processHTML;
    }
    
    // Aktualizacja informacji sieciowych
    const networkDiv = document.querySelector('#network h1');
    if (networkDiv && data.network) {
        networkDiv.textContent = `${data.network.hostname} ${data.network.ip}:5000`;
        networkDiv.style.color = 'rgb(138, 212, 255)';
    }
}

// Inicjalizacja - pierwsze pobranie danych
fetchMetrics();

// Ustawienie interwału dla regularnych aktualizacji
setInterval(fetchMetrics, UPDATE_INTERVAL);

// Obsługa błędów połączenia
window.addEventListener('online', () => {
    console.log('Połączenie przywrócone');
    fetchMetrics();
});

window.addEventListener('offline', () => {
    console.log('Brak połączenia z serwerem');
});