import psutil
import socket
import platform
from flask import Flask, jsonify
from flask_cors import CORS
import json
import threading
import time
import requests

app = Flask(__name__)
CORS(app)

# Konfiguracja LibreHardwareMonitor - ZMIEŃ NA SWÓJ ADRES!
LIBRE_HW_MONITOR_URL = "http://192.168.0.43:8085/data.json"

# Cache dla danych z LibreHardwareMonitor
libre_hw_cache = {
    'data': None,
    'last_update': 0,
    'update_interval': 2  # Aktualizuj co 2 sekundy
}

def fetch_libre_hardware_data():
    """Pobiera dane z LibreHardwareMonitor API"""
    try:
        current_time = time.time()
        
        # Użyj cache jeśli dane są świeże
        if (libre_hw_cache['data'] is not None and 
            current_time - libre_hw_cache['last_update'] < libre_hw_cache['update_interval']):
            return libre_hw_cache['data']
        
        # Pobierz nowe dane
        response = requests.get(LIBRE_HW_MONITOR_URL, timeout=2)
        if response.ok:
            json_data = response.json()
            # Wyciągnij właściwe dane (są w kluczu 'data')
            data = json_data.get('data', json_data)
            libre_hw_cache['data'] = data
            libre_hw_cache['last_update'] = current_time
            return data
        else:
            print(f"[DEBUG] LibreHardwareMonitor HTTP {response.status_code}")
            return None
            
    except requests.exceptions.Timeout:
        print("[DEBUG] LibreHardwareMonitor timeout")
        return None
    except requests.exceptions.ConnectionError:
        print("[DEBUG] LibreHardwareMonitor connection error - sprawdź czy działa na http://192.168.0.43:8085")
        return None
    except Exception as e:
        print(f"[DEBUG] LibreHardwareMonitor error: {e}")
        return None

def find_sensor_by_path(data, sensor_id):
    """
    Znajduje sensor po jego SensorId (ścieżce)
    Przykład: "/amdcpu/0/temperature/2" -> temperatura CPU Core (Tctl/Tdie)
    """
    if not data:
        return None
    
    def search_recursive(node):
        # Sprawdź czy to właściwy sensor
        if node.get('SensorId') == sensor_id:
            value = node.get('Value', '')
            if value:
                # Usuń jednostki (°C, %, GB, etc.)
                value_clean = value.replace('°C', '').replace('%', '').replace('GB', '').replace(',', '.').strip()
                try:
                    return float(value_clean)
                except ValueError:
                    pass
        
        # Kontynuuj przeszukiwanie dzieci
        if 'Children' in node:
            for child in node['Children']:
                result = search_recursive(child)
                if result is not None:
                    return result
        
        return None
    
    return search_recursive(data)

def get_cpu_temp_from_libre():
    """
    Pobiera temperaturę CPU z LibreHardwareMonitor
    Na podstawie rzeczywistych danych: Core (Tctl/Tdie) = /amdcpu/0/temperature/2
    """
    data = fetch_libre_hardware_data()
    if not data:
        return 0
    
    # DOKŁADNA ŚCIEŻKA z Twojego systemu
    cpu_temp = find_sensor_by_path(data, "/amdcpu/0/temperature/2")
    
    # Fallback: spróbuj też z chipset CPU (z płyty głównej)
    if not cpu_temp or cpu_temp == 0:
        cpu_temp = find_sensor_by_path(data, "/lpc/nct6687d/0/temperature/0")
    
    if cpu_temp and cpu_temp > 0:
        print(f"[DEBUG] CPU temp from LibreHW: {cpu_temp}°C")
        return cpu_temp
    
    return 0

def get_disk_temp_from_libre():
    """
    Pobiera temperaturę dysku z LibreHardwareMonitor
    Na podstawie rzeczywistych danych: Composite Temperature = /nvme/0/temperature/0
    """
    data = fetch_libre_hardware_data()
    if not data:
        return 0
    
    # DOKŁADNA ŚCIEŻKA z Twojego systemu - Lexar SSD NM620 1TB
    disk_temp = find_sensor_by_path(data, "/nvme/0/temperature/0")
    
    if disk_temp and disk_temp > 0:
        print(f"[DEBUG] Disk temp from LibreHW: {disk_temp}°C")
        return disk_temp
    
    return 0

# Background thread do ciągłego update'u CPU
def cpu_monitor_background():
    """Wątek w tle który ciągle aktualizuje CPU stats"""
    while True:
        psutil.cpu_percent(interval=1, percpu=False)
        for proc in psutil.process_iter(['cpu_percent']):
            try:
                proc.cpu_percent(interval=None)
            except:
                pass
        time.sleep(1)

def get_network_info():
    """Pobiera nazwę połączenia i adres IP"""
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        
        # Próba uzyskania bardziej dokładnego IP (nie localhost)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('8.8.8.8', 80))
            local_ip = s.getsockname()[0]
        except:
            pass
        finally:
            s.close()
            
        return {
            'hostname': hostname,
            'ip': local_ip
        }
    except:
        return {
            'hostname': 'Unknown',
            'ip': '0.0.0.0'
        }

def get_cpu_info():
    """Pobiera informacje o CPU"""
    try:
        cpu_percent = psutil.cpu_percent(interval=None)
        
        if cpu_percent == 0.0:
            cpu_percent = psutil.cpu_percent(interval=0.1)
        
        # Najpierw spróbuj LibreHardwareMonitor
        cpu_temp = get_cpu_temp_from_libre()
        
        # Jeśli nie działa, fallback na psutil
        if cpu_temp == 0:
            try:
                temps = psutil.sensors_temperatures()
                if 'coretemp' in temps:
                    cpu_temp = temps['coretemp'][0].current
                elif 'cpu_thermal' in temps:
                    cpu_temp = temps['cpu_thermal'][0].current
                elif 'k10temp' in temps:
                    cpu_temp = temps['k10temp'][0].current
                elif temps:
                    cpu_temp = list(temps.values())[0][0].current
            except Exception as e:
                print(f"Nie można odczytać temperatury CPU przez psutil: {e}")
                cpu_temp = 0
            
        return {
            'usage': round(cpu_percent, 1),
            'temperature': round(cpu_temp, 1)
        }
    except Exception as e:
        print(f"Błąd CPU: {e}")
        return {
            'usage': 0,
            'temperature': 0
        }

def get_gpu_info():
    """Pobiera informacje o GPU (wymaga nvidia-smi dla NVIDIA lub ROCm dla AMD)"""
    try:
        import subprocess
        # Próba dla NVIDIA
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=utilization.gpu,temperature.gpu', '--format=csv,noheader,nounits'],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            usage, temp = result.stdout.strip().split(',')
            return {
                'usage': float(usage.strip()),
                'temperature': float(temp.strip())
            }
    except:
        pass
    
    return {
        'usage': 0,
        'temperature': 0
    }

def get_ram_info():
    """Pobiera informacje o RAM"""
    memory = psutil.virtual_memory()
    return {
        'usage': round(memory.percent, 1),
        'used_gb': round(memory.used / (1024**3), 1),
        'total_gb': round(memory.total / (1024**3), 1)
    }

def get_disk_info():
    """Pobiera informacje o dysku"""
    try:
        if platform.system() == 'Windows':
            disk_path = 'C:\\'
        else:
            disk_path = '/'
            
        disk = psutil.disk_usage(disk_path)
        
        # Najpierw spróbuj LibreHardwareMonitor
        disk_temp = get_disk_temp_from_libre()
        
        # Jeśli nie działa, fallback na psutil
        if disk_temp == 0:
            try:
                temps = psutil.sensors_temperatures()
                if 'nvme' in temps:
                    disk_temp = temps['nvme'][0].current
                elif 'drivetemp' in temps:
                    disk_temp = temps['drivetemp'][0].current
            except Exception as e:
                print(f"Nie można odczytać temperatury dysku przez psutil: {e}")
            
        return {
            'usage': round(disk.percent, 1),
            'used_gb': round(disk.used / (1024**3), 1),
            'total_gb': round(disk.total / (1024**3), 1),
            'temperature': round(disk_temp, 1)
        }
    except Exception as e:
        print(f"Błąd dysku: {e}")
        return {
            'usage': 0,
            'used_gb': 0,
            'total_gb': 0,
            'temperature': 0
        }

def get_top_processes():
    """Pobiera 12 najbardziej zasobożernych procesów"""
    processes = []
    
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try:
            pinfo = proc.info
            cpu = proc.cpu_percent(interval=None)
            ram = pinfo['memory_percent'] or 0
            
            if pinfo['name'].lower() in ['system idle process', 'idle']:
                continue
            
            if cpu > 100.0:
                cpu = cpu / psutil.cpu_count()
            
            cpu = min(cpu, 100.0)
            ram = min(ram, 100.0)
            
            if cpu > 0.1 or ram > 0.5:
                processes.append({
                    'name': pinfo['name'][:30],
                    'cpu': round(cpu, 1),
                    'ram': round(ram, 1),
                    'gpu': 0
                })
                
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    
    processes.sort(key=lambda x: x['cpu'], reverse=True)
    top_processes = processes[:12]
    
    if len(top_processes) < 12:
        remaining = [p for p in processes if p not in top_processes]
        remaining.sort(key=lambda x: x['ram'], reverse=True)
        top_processes.extend(remaining[:12-len(top_processes)])
    
    return top_processes if top_processes else [{
        'name': 'No processes',
        'cpu': 0,
        'ram': 0,
        'gpu': 0
    }]

@app.route('/api/metrics', methods=['GET'])
def get_metrics():
    """Endpoint zwracający wszystkie metryki systemowe"""
    metrics = {
        'cpu': get_cpu_info(),
        'gpu': get_gpu_info(),
        'ram': get_ram_info(),
        'disk': get_disk_info(),
        'network': get_network_info(),
        'processes': get_top_processes()
    }
    
    return jsonify(metrics)

@app.route('/api/port', methods=['GET'])
def get_port():
    """Endpoint zwracający port na jakim działa serwer"""
    return jsonify({'port': 5000})

@app.route('/api/libre-debug', methods=['GET'])
def debug_libre():
    """Endpoint debugowy do sprawdzania danych z LibreHardwareMonitor"""
    data = fetch_libre_hardware_data()
    if data:
        # Znajdź temperatury do debugowania
        cpu_temp = get_cpu_temp_from_libre()
        disk_temp = get_disk_temp_from_libre()
        
        return jsonify({
            'status': 'ok',
            'cpu_temp': cpu_temp,
            'disk_temp': disk_temp,
            'libre_hw_connected': True
        })
    else:
        return jsonify({
            'status': 'error',
            'message': 'Cannot connect to LibreHardwareMonitor',
            'url': LIBRE_HW_MONITOR_URL,
            'libre_hw_connected': False
        }), 503

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 FRUTIGER HARDWARE MONITOR - SERVER")
    print("=" * 60)
    print(f"📡 Serwer: http://localhost:5000")
    print(f"📊 API:    http://localhost:5000/api/metrics")
    print(f"🔧 LibreHW: {LIBRE_HW_MONITOR_URL}")
    print(f"🐛 Debug:  http://localhost:5000/api/libre-debug")
    print("=" * 60)
    
    # Uruchom background thread dla CPU monitoring
    cpu_thread = threading.Thread(target=cpu_monitor_background, daemon=True)
    cpu_thread.start()
    print("✓ Background CPU monitor uruchomiony")
    
    # Pierwsze wywołanie żeby zainicjalizować cache
    psutil.cpu_percent(interval=None)
    
    # Test połączenia z LibreHardwareMonitor
    print("\n🔍 Testowanie połączenia z LibreHardwareMonitor...")
    test_data = fetch_libre_hardware_data()
    if test_data:
        print("✓ LibreHardwareMonitor POŁĄCZONY!")
        
        # Testuj temperatury
        cpu_temp = get_cpu_temp_from_libre()
        disk_temp = get_disk_temp_from_libre()
        
        print(f"  • CPU Temperature:  {cpu_temp}°C")
        print(f"  • Disk Temperature: {disk_temp}°C")
        
        if cpu_temp > 0 and disk_temp > 0:
            print("\n🎉 WSZYSTKO DZIAŁA! Temperatury są odczytywane poprawnie!")
        elif cpu_temp > 0:
            print("\n⚠️  CPU działa, ale dysk zwraca 0°C")
        elif disk_temp > 0:
            print("\n⚠️  Dysk działa, ale CPU zwraca 0°C")
        else:
            print("\n❌ Temperatury zwracają 0°C - sprawdź sensory w LibreHardwareMonitor")
    else:
        print("❌ Nie można połączyć z LibreHardwareMonitor!")
        print(f"   Sprawdź czy LibreHardwareMonitor działa na: {LIBRE_HW_MONITOR_URL}")
        print("   Temperatury będą pokazywać 0°C")
    
    print("\n" + "=" * 60)
    print("🌊 Serwer gotowy! Otwórz index.html w przeglądarce")
    print("=" * 60 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=False)