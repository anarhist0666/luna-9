import time
import krpc

conn = krpc.connect(name="LaunchLogger")
vessel = conn.space_center.active_vessel

# Создаём папку для данных
import os
os.makedirs("data", exist_ok=True)

# Открываем файл
file = open("data/ksp_launch.log", "w")
file.write("Time Pitch Altitude Speed Mass\n")

# Функция проверки запуска двигателей
def is_launched():
    for engine in vessel.parts.engines:
        if engine.active:
            return True
    return False

print("Ожидание запуска ракеты...")
while not is_launched():
    time.sleep(0.1)

print("Ракета запущена! Начинаю запись...")
mission_start_time = conn.space_center.ut
last_write_time = mission_start_time

try:
    while True:
        current_time = conn.space_center.ut
        elapsed = current_time - mission_start_time
        
        # Записываем каждые 0.1 секунды
        if current_time - last_write_time >= 0.1:
            altitude = vessel.flight().surface_altitude
            pitch = vessel.flight().pitch  # Угол тангажа
            speed = vessel.flight(vessel.orbit.body.reference_frame).speed
            mass = vessel.mass
            
            file.write(f"{elapsed:.2f} {pitch:.2f} {altitude:.2f} {speed:.2f} {mass:.2f}\n")
            last_write_time = current_time
            
            # Вывод в консоль каждую секунду
            if int(elapsed) != int(elapsed - 0.1):
                print(f"[{elapsed:.1f}с] H={altitude:.0f}м, V={speed:.0f}м/с, pitch={pitch:.1f}°")
        
        time.sleep(0.01)  # Не грузим процессор

except KeyboardInterrupt:
    print("\nЗапись остановлена пользователем")
finally:
    file.close()
    conn.close()
    print("Данные сохранены в data/ksp_launch.log")