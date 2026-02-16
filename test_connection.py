"""
Prosty tester połączenia z LibreHardwareMonitor
Pokazuje dokładnie co zwraca API i które sensory są wykrywane
"""

import requests
import json

LIBRE_URL = "http://192.168.0.43:8085/data.json"

print("=" * 70)
print("FRUTIGER HARDWARE MONITOR - TESTER POŁĄCZENIA")
print("=" * 70)

print(f"\n🔍 Testowanie połączenia z: {LIBRE_URL}\n")

try:
    response = requests.get(LIBRE_URL, timeout=5)
    
    if not response.ok:
        print(f"❌ HTTP Error {response.status_code}")
        exit(1)
    
    data = response.json()
    print("✅ Połączenie OK!\n")
    
    # Pobierz właściwe dane
    if 'data' in data:
        data = data['data']
    
    # Funkcja do znajdywania sensora
    def find_sensor(node, sensor_id):
        if node.get('SensorId') == sensor_id:
            return node.get('Value', 'Brak wartości')
        
        if 'Children' in node:
            for child in node['Children']:
                result = find_sensor(child, sensor_id)
                if result:
                    return result
        return None
    
    # Testuj konkretne sensory
    print("📊 SPRAWDZANIE SENSORÓW:")
    print("-" * 70)
    
    sensors_to_check = [
        ("CPU (AMD Core Tctl/Tdie)", "/amdcpu/0/temperature/2"),
        ("CPU (Chipset)", "/lpc/nct6687d/0/temperature/0"),
        ("Dysk NVMe (Composite)", "/nvme/0/temperature/0"),
        ("Dysk NVMe (Temp #1)", "/nvme/0/temperature/1"),
        ("GPU Core", "/gpu-nvidia/0/temperature/0"),
    ]
    
    found_any = False
    for name, sensor_id in sensors_to_check:
        value = find_sensor(data, sensor_id)
        if value:
            print(f"✅ {name:30s} → {value}")
            found_any = True
        else:
            print(f"❌ {name:30s} → Nie znaleziono")
    
    if not found_any:
        print("\n⚠️  Nie znaleziono żadnych sensorów!")
        print("   Sprawdź czy LibreHardwareMonitor wyświetla temperatury")
    
    print("\n" + "=" * 70)
    print("PODSUMOWANIE:")
    print("=" * 70)
    
    cpu_temp = find_sensor(data, "/amdcpu/0/temperature/2")
    disk_temp = find_sensor(data, "/nvme/0/temperature/0")
    
    if cpu_temp and disk_temp:
        print("🎉 SUKCES! Wszystkie kluczowe sensory działają!")
        print(f"   CPU:  {cpu_temp}")
        print(f"   Dysk: {disk_temp}")
    elif cpu_temp:
        print("⚠️  CPU działa, ale dysk nie został wykryty")
        print(f"   CPU: {cpu_temp}")
    elif disk_temp:
        print("⚠️  Dysk działa, ale CPU nie został wykryty")
        print(f"   Dysk: {disk_temp}")
    else:
        print("❌ Żadne sensory nie zostały wykryte")
        print("   Sprawdź konfigurację LibreHardwareMonitor")
    
    print("\n💡 TIP: Jeśli wszystko działa tutaj, możesz uruchomić server.py")
    print("=" * 70)
    
except requests.exceptions.Timeout:
    print("❌ Timeout - LibreHardwareMonitor nie odpowiada")
    print(f"   Sprawdź czy działa na: {LIBRE_URL}")
except requests.exceptions.ConnectionError:
    print("❌ Connection Error - nie można połączyć")
    print(f"   Sprawdź czy LibreHardwareMonitor działa na: {LIBRE_URL}")
    print("   Upewnij się że:")
    print("   1. LibreHardwareMonitor jest uruchomiony")
    print("   2. Web server jest włączony (Options → Remote Web Server)")
    print("   3. Port 8085 jest otwarty")
except Exception as e:
    print(f"❌ Błąd: {e}")
