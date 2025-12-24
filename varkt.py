import math
import matplotlib.pyplot as plt

# ============================================
# 1. ПАРАМЕТРЫ 
# ============================================

# Начальная масса из лога 
m0 = 186447.0 

h_start = 1080.0   # Высота начала маневра (м)
h_end = 51800.0 

# Двигатели
# Перевод единиц KSP в кг/с
flow_booster_units = 41.407
flow_core_units = 44.407

mu_boosters_total = flow_booster_units * 7.5 * 4  # ~1242 кг/с
mu_core = flow_core_units * 5.0                   # ~222 кг/с
mu_start = mu_boosters_total + mu_core 

# Тяга 
F_booster_one = 670000  
F_core_one = 1500000      
F_thrust_start = (F_booster_one * 4) + F_core_one

# Ступени 

mass_drop_at_stage = 18531.0 

# Время сброса из лога 
booster_jettison_time = 64.2

turn_start_h = 1000.0    # Начинаем поворот на 1 км
turn_end_h = 50000.0 

# --- Атмосфера ---
p0 = 1.2230948554874
H = 5600
Cx = 0.5 # Средний коэффициент
S = 19.04
g0 = 9.81
R = 600000

dt = 0.1
t_max = 90.0 

# ============================================
# 2. МАТЕМАТИЧЕСКАЯ МОДЕЛЬ
# ============================================

def simulate_model():
    t = 0.0
    x = 0.0
    y = 11.24 # Начальная высота из лога
    vx = 0.0
    vy = 0.0
    m = m0
    
    current_mu = mu_start
    current_F = F_thrust_start
    boosters_attached = True

    times = [t]
    heights = [y]
    velocities = [0.74] # Начальная скорость из лога
    masses = [m]
    pitches = [90.0] 
    
    print(f"Запуск модели... m0={m:.0f} кг")

    while t < t_max:
        
        # 0 - 1000 м (Почти вертикальный взлет)
        if y < h_start:
            pitch_deg = 89.0

        elif 1000.0 < y <= 10000.0:
            fraction = (y - 1000.0) / 9000.0
            # Из лога: на 10000м угол ~45°, значит разворот на 44° за этот этап
            pitch_deg = 89.0 - (44.0 * fraction)

        elif 10000.0 < y <= 30000.0:
            fraction = (y - 10000.0) / 20000.0
            # Из лога: на 30000м угол ~20°, значит разворот на 25° за этот этап
            pitch_deg = 45.0 - (25.0 * fraction)
        elif 30000.0 < y <= 51800.0:
            fraction = (y - 30000.0) / 21800.0
            # Из лога: на ~51800м угол ~0°, разворот на 20° за этот этап
            pitch_deg = 20.0 - (20.0 * fraction)
        else:
            # После достижения целевой высоты поддерживаем ~0°
            pitch_deg = max(0.0, 20.0 * math.exp(-(y - 51800.0) / 10000.0))

        pitch_rad = math.radians(pitch_deg)

        # ФИЗИКА
        v_total = math.sqrt(vx**2 + vy**2)
        rho = p0 * math.exp(-y / H)
        g = g0 * (R / (R + y))**2
        
        # Силы
        F_gravity = m * g
        F_drag = 0.5 * rho * v_total**2 * Cx * S
        
        # Проекции сил 
        Fx_thrust = current_F * math.cos(pitch_rad)
        Fy_thrust = current_F * math.sin(pitch_rad)
        
        Fx_drag = F_drag * math.cos(pitch_rad)
        Fy_drag = F_drag * math.sin(pitch_rad)
        
        # Ускорения
        if m > 0:
            ax = (Fx_thrust - Fx_drag) / m
            ay = (Fy_thrust - Fy_drag - F_gravity) / m
        else:
            ax, ay = 0, 0
        
        # Интегрирование (Метод Эйлера)
        vx += ax * dt
        vy += ay * dt
        x += vx * dt
        y += vy * dt
        
        # Расход топлива
        if current_F > 0:
            m -= current_mu * dt
        t += dt
        
        # Сброс ускорителей
        if t >= booster_jettison_time and boosters_attached:
            boosters_attached = False
            
            # Вычитаем массу пустых ускорителей
            m -= mass_drop_at_stage 
            
            # Меняем параметры на центральный двигатель
            current_mu = mu_core      
            current_F = F_core_one
            print(f"[СБРОС] t={t:.1f}с | Масса упала до {m:.0f} кг | Угол {pitch_deg:.1f}°")
        
        # Сохранение данных
        times.append(t)
        heights.append(y)
        velocities.append(math.sqrt(vx**2 + vy**2))
        masses.append(m)
        pitches.append(pitch_deg)
    return times, heights, velocities, masses, pitches

# ============================================
# 3. ЗАГРУЗКА ДАННЫХ 
# ============================================

def load_ksp_data():
    times, heights, velocities, masses, pitches = [], [], [], [], []
    
    file_path = 'data/ksp_launch.log'
    
    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()
            
            start_index = 0
            if any(c.isalpha() for c in lines[0]):
                start_index = 1
                
            for line in lines[start_index:]:
                parts = line.split()
                # Time Pitch Altitude Speed Mass
                if len(parts) >= 5:
                    try:
                        t = float(parts[0])
                        p = float(parts[1]) # Pitch - 2-й столбец
                        h = float(parts[2]) # Altitude - 3-й столбец
                        v = float(parts[3]) # Speed - 4-й столбец
                        m = float(parts[4]) # Mass - 5-й столбец
                        
                        if t <= t_max:
                            times.append(t)
                            pitches.append(p)
                            heights.append(h)
                            velocities.append(v)
                            masses.append(m)
                    except ValueError:
                        continue # Пропускаем битые строки
                        
    except FileNotFoundError:
        print(f"ОШИБКА: Файл {file_path} не найден.")
        return [], [], [], [], []
        
    return times, heights, velocities, masses, pitches

# ============================================
# 4. ГРАФИКИ
# ============================================

def plot_comparison(model_data, ksp_data, title, y_label, m_idx, k_idx, filename):
    mt = model_data[0]
    m_val = model_data[m_idx] # Данные модели
    
    kt = ksp_data[0]
    k_val = ksp_data[k_idx]   # Данные KSP
    
    plt.figure(figsize=(10, 6))
    
    # Реальные данные (точки)
    if kt:
        plt.plot(kt, k_val, 'bo', markersize=2, alpha=0.6, label='KSP (Эксперимент)')
    
    # Модель (линия)
    plt.plot(mt, m_val, 'r-', linewidth=2.5, label='Мат. Модель (Теория)')
    
    plt.title(f'Сравнение: {title}', fontsize=14)
    plt.xlabel('Время (с)', fontsize=12)
    plt.ylabel(y_label, fontsize=12)
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig(filename, dpi=150)
    plt.show()

# ============================================
# MAIN
# ============================================

def main():
    
    # 1. Считаем теорию
    model_res = simulate_model() # times, heights, vels, masses, pitches
    
    # 2. Грузим практику
    ksp_res = load_ksp_data()    # times, heights, vels, masses, pitches
    
    if not ksp_res[0]:
        print("Данные KSP пусты! Проверь файл.")
        return

    # 3. Рисуем графики (индексы: 1=h, 2=v, 3=m, 4=p)
    plot_comparison(model_res, ksp_res, "ВЫСОТА ПОЛЕТА", "Высота (м)", 1, 1, "graph_height.png")
    plot_comparison(model_res, ksp_res, "СКОРОСТЬ", "Скорость (м/с)", 2, 2, "graph_speed.png")
    plot_comparison(model_res, ksp_res, "МАССА РАКЕТЫ", "Масса (кг)", 3, 3, "graph_mass.png")
    plot_comparison(model_res, ksp_res, "УГОЛ ТАНГАЖА", "Угол (град)", 4, 4, "graph_pitch.png")

    print("\nГотово! Графики сохранены.")

if __name__ == "__main__":
    main()