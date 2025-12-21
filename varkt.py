# model_separate_graphs.py
import matplotlib.pyplot as plt
from math import exp, sin, pi

# ============================================
# 1. ПАРАМЕТРЫ
# ============================================

m0 = 186417.95
burn_time = 70
fuel_used = 110166.31
mu = fuel_used / burn_time
F_thrust = 3840000

booster_mass = 24000  # Масса одного ускорителя
num_boosters = 4
total_booster_mass = booster_mass * num_boosters  # 96000 кг
booster_jettison_time = 62.7  # Время сброса

dry_mass = m0 - fuel_used - total_booster_mass

p0 = 1.2230948554874
H = 5600
Cx = 0.5
S = 19.04
g0 = 9.81
R = 600000

dt = 0.1
t_max = burn_time

# ============================================
# 2. МАТЕМАТИЧЕСКАЯ МОДЕЛЬ
# ============================================

def simulate_model():
    t = 0.0
    h = 11.15
    v = 0.74
    m = m0

    times = [t]
    heights = [h]
    velocities = [v]
    masses = [m]
    
    boosters_attached = True
    
    print(f"Старт: m={m:.0f} кг")

    while t < t_max:
        # 1. РАСХОД ТОПЛИВА
        if t < burn_time:
            m -= mu * dt
        
        # 2. ФИЗИКА с текущей массой (ЕЩЕ ДО сброса на этом шаге)
        g = g0 * (R / (R + h))**2
        F_g = m * g
        rho = p0 * exp(-h / H)
        F_d = 0.5 * rho * v**2 * Cx * S * (1 if v >= 0 else -1)
        a = (F_thrust - F_g - F_d) / m if m > 0 else 0
        
        # 3. ИНТЕГРИРОВАНИЕ
        v_new = v + a * dt
        h_new = h + v * dt
        
        # 4. ОБНОВЛЕНИЕ ВРЕМЕНИ
        t += dt
        
        # 5. СБРОС УСКОРИТЕЛЕЙ ПОСЛЕ расчета физики
        if t >= booster_jettison_time and boosters_attached:
            boosters_attached = False
            old_m = m
            m -= total_booster_mass
            print(f"\n[СБРОС] на {t:.1f} с")
            print(f"  Рассчитано с массой: {old_m:.0f} кг")
            print(f"  Новая масса: {m:.0f} кг")
            print(f"  Скорость: {v_new:.1f} м/с")
        
        # 6. ОБНОВЛЕНИЕ остальных переменных
        v = v_new
        h = h_new
        
        # 7. СОХРАНЕНИЕ
        times.append(t)
        heights.append(h)
        velocities.append(v)
        masses.append(m)
    
    return times, heights, velocities, masses


# ============================================
# 3. ЗАГРУЗКА ДАННЫХ KSP
# ============================================

def load_ksp_data():
    times, heights, velocities, masses = [], [], [], []
    
    try:
        with open('data/ksp_launch.log', 'r') as f:
            for line in f.readlines()[1:]:
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 5:
                        t = float(parts[0])
                        if t <= burn_time:
                            times.append(t)
                            heights.append(float(parts[2]))
                            velocities.append(float(parts[3]))
                            masses.append(float(parts[4]))
    except:
        print("Ошибка загрузки данных KSP")
    
    return times, heights, velocities, masses

# ============================================
# 4. ГРАФИК 1: ВЫСОТА 
# ============================================

def plot_height_comparison(model_data, ksp_data):
    model_t, model_h, _, _ = model_data
    ksp_t, ksp_h, _, _ = ksp_data
    
    plt.figure(figsize=(10, 6))
    

    plt.plot(ksp_t, ksp_h, 'bo', markersize=4, alpha=0.7, 
             label='KSP (реальные данные, точки)', markeredgewidth=0.5, markeredgecolor='b')

    plt.plot(ksp_t, ksp_h, 'b-', linewidth=0.8, alpha=0.4)
    
    # Модель: чёткая линия
    plt.plot(model_t, model_h, 'r-', linewidth=2.5, label='Математическая модель')
    
    plt.xlabel('Время, с', fontsize=12)
    plt.ylabel('Высота, м', fontsize=12)
    plt.title('СРАВНЕНИЕ: Высота ракеты\nKSP vs Математическая модель', fontsize=14, fontweight='bold')
    plt.legend(loc='upper left', fontsize=11)
    plt.grid(True, alpha=0.3)
    
    # Увеличиваем масштаб для деталей
    if ksp_h:
        # Берём диапазон KSP данных ±5%
        h_min = min(ksp_h) * 0.95
        h_max = max(ksp_h) * 1.05
        plt.ylim(h_min, h_max)
    
    plt.tight_layout()
    plt.savefig('graph_height_comparison.png', dpi=300, bbox_inches='tight')
    plt.savefig('graph_height_comparison.pdf', bbox_inches='tight')
    print("✓ График высоты сохранён в 'graph_height_comparison.png' и '.pdf'")
    plt.show()

# ============================================
# 5. ГРАФИК 2: СКОРОСТЬ 
# ============================================

def plot_velocity_comparison(model_data, ksp_data):
    model_t, _, model_v, _ = model_data
    ksp_t, _, ksp_v, _ = ksp_data
    
    plt.figure(figsize=(10, 6))
    
    # KSP: точки
    plt.plot(ksp_t, ksp_v, 'go', markersize=4, alpha=0.7, 
             label='KSP (реальные данные, точки)', markeredgewidth=0.5, markeredgecolor='g')
    plt.plot(ksp_t, ksp_v, 'g-', linewidth=0.8, alpha=0.4)
    
    # Модель
    plt.plot(model_t, model_v, 'r-', linewidth=2.5, label='Математическая модель')
    
    plt.xlabel('Время, с', fontsize=12)
    plt.ylabel('Скорость, м/с', fontsize=12)
    plt.title('СРАВНЕНИЕ: Скорость ракеты\nKSP vs Математическая модель', fontsize=14, fontweight='bold')
    plt.legend(loc='upper left', fontsize=11)
    plt.grid(True, alpha=0.3)
    
    # Увеличенный масштаб
    if ksp_v:
        v_min = min(ksp_v) * 0.95
        v_max = max(ksp_v) * 1.05
        plt.ylim(v_min, v_max)
    
    plt.tight_layout()
    plt.savefig('graph_velocity_comparison.png', dpi=300, bbox_inches='tight')
    plt.savefig('graph_velocity_comparison.pdf', bbox_inches='tight')
    print("✓ График скорости сохранён в 'graph_velocity_comparison.png' и '.pdf'")
    plt.show()

# ============================================
# 6. ГРАФИК 3: МАССА (ОТДЕЛЬНЫЙ ФАЙЛ)
# ============================================

def plot_mass_comparison(model_data, ksp_data):
    model_t, _, _, model_m = model_data
    ksp_t, _, _, ksp_m = ksp_data
    
    plt.figure(figsize=(10, 6))
    
    # KSP: точки
    plt.plot(ksp_t, ksp_m, 'mo', markersize=4, alpha=0.7, 
             label='KSP (реальные данные, точки)', markeredgewidth=0.5, markeredgecolor='m')
    plt.plot(ksp_t, ksp_m, 'm-', linewidth=0.8, alpha=0.4)
    
    # Модель
    plt.plot(model_t, model_m, 'r-', linewidth=2.5, label='Математическая модель')
    
    plt.xlabel('Время, с', fontsize=12)
    plt.ylabel('Масса, кг', fontsize=12)
    plt.title('СРАВНЕНИЕ: Масса ракеты\nKSP vs Математическая модель', fontsize=14, fontweight='bold')
    plt.legend(loc='upper right', fontsize=11)
    plt.grid(True, alpha=0.3)
    
    # Увеличенный масштаб для массы
    if ksp_m:
        m_min = min(ksp_m) * 0.999  
        m_max = max(ksp_m) * 1.001
        plt.ylim(m_min, m_max)
        
        print(f"\nДАННЫЕ МАССЫ KSP:")
        print(f"Начальная масса: {ksp_m[0]:.2f} кг")
        print(f"Конечная масса: {ksp_m[-1]:.2f} кг")
        print(f"Изменение: {ksp_m[0] - ksp_m[-1]:.2f} кг")
        print(f"Количество точек: {len(ksp_m)}")
        

    plt.tight_layout()
    plt.savefig('graph_mass_comparison.png', dpi=300, bbox_inches='tight')
    plt.savefig('graph_mass_comparison.pdf', bbox_inches='tight')
    print("✓ График массы сохранён в 'graph_mass_comparison.png' и '.pdf'")
    plt.show()

# ============================================
# 7. ОСНОВНАЯ ПРОГРАММА
# ============================================

def main():
    
    print("="*60)
    print("ТРИ ОТДЕЛЬНЫХ ГРАФИКА: KSP vs МАТЕМАТИЧЕСКАЯ МОДЕЛЬ")
    print("="*60)
    print("ПАРАМЕТРЫ МОДЕЛИ:")
    print(f"  Начальная масса ракеты: {m0/1000:.1f} т")
    print(f"  Масса топлива: {fuel_used/1000:.1f} т")
    print(f"  Время работы двигателя: {burn_time:.1f} с")
    print(f"  Расход топлива: {mu:.1f} кг/с")
    print(f"  Тяга двигателя: {F_thrust/1000000:.1f} МН")
    print("="*60)
    # 1. Запускаем модель
    print("\n1. Запуск математической модели...")
    model_data = simulate_model()
    
    # 2. Загружаем KSP данные
    print("2. Загрузка данных KSP...")
    ksp_data = load_ksp_data()
    
    print(f"   Загружено {len(ksp_data[0])} точек")

    # 3. Построение трёх отдельных графиков
    print("\n3. Построение графиков...")
    print("-"*40)
    
    # График 1: Высота
    plot_height_comparison(model_data, ksp_data)
    print()
    
    # График 2: Скорость
    plot_velocity_comparison(model_data, ksp_data)
    print()
    
    # График 3: Масса
    plot_mass_comparison(model_data, ksp_data)
    print()
    
    print("\n" + "="*60)
    print("ВСЕ ГРАФИКИ СОХРАНЕНЫ:")
    print("="*60)
    print("1. graph_height_comparison.png/.pdf - Высота")
    print("2. graph_velocity_comparison.png/.pdf - Скорость")
    print("3. graph_mass_comparison.png/.pdf - Масса")
    print("="*60)

# ============================================
# ЗАПУСК
# ============================================

if __name__ == "__main__":
    main()