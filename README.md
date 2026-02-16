# Frutiger Hardware Monitor

Monitor sprzętowy w stylu Frutiger Aero z interfejsem webowym. Wyświetla w czasie rzeczywistym temperatury, obciążenie CPU/GPU/RAM/dysku i listę procesów.

## Funkcje

- Monitoring CPU, GPU, RAM, dysku (obciążenie + temperatury)
- Top 12 procesów według zużycia zasobów
- Odświeżanie co 1 sekundę
- Dostęp przez sieć lokalną
- Estetyczny interfejs z animacjami

## Wymagania

- Windows 10/11
- Python 3.8+
- [LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/releases) (do temperatur)

## Instalacja

```bash
pip install -r requirements.txt
```

## Uruchomienie

1. Uruchom **LibreHardwareMonitor jako administrator**
2. Włącz web server: **Options → Remote Web Server → Run**
3. Test połączenia:
```bash
python test_connection.py
```
4. Uruchom serwer:
```bash
python server.py
```
5. Otwórz w przeglądarce: `http://localhost:5000`

## Konfiguracja

### Zmiana adresu LibreHardwareMonitor
W `server.py` linia 11:
```python
LIBRE_HW_MONITOR_URL = "http://localhost:8085/data.json"
```

### Zmiana częstotliwości odświeżania
W `metrics.js` linia 4:
```javascript
const UPDATE_INTERVAL = 1000; // ms
```

## Troubleshooting

**Temperatury = 0°C**
- LibreHardwareMonitor nie działa lub nie ma włączonego web servera
- Sprawdź: `http://localhost:8085`

**Nie można połączyć**
- Firewall blokuje port 5000 lub 8085
- Uruchom jako administrator

**GPU = 0%**
- nvidia-smi wymagane dla kart NVIDIA
- Karty AMD obecnie nie wspierane
