import krpc
import time
import math

conn = krpc.connect(name='Луна-9')
vessel = conn.space_center.active_vessel
ap = vessel.auto_pilot
control = vessel.control

ut = conn.add_stream(getattr, conn.space_center, 'ut')
altitude_terrain = conn.add_stream(
    getattr, vessel.flight(), 'surface_altitude'
)
apoapsis = conn.add_stream(getattr, vessel.orbit, 'apoapsis_altitude')
periapsis = conn.add_stream(getattr, vessel.orbit, 'periapsis_altitude')


# Функция обновления активного корабля
def update_active_vessel():
    new_vessel = conn.space_center.active_vessel
    if new_vessel.name != vessel.name:
        return new_vessel
    return vessel


# Мониторинг топлива первой ступени
start = vessel.resources_in_decouple_stage(stage=12, cumulative=False)
start_fuel = conn.add_stream(start.amount, 'SolidFuel')

# Старт
control.throttle = 1
control.sas = True
time.sleep(3)
control.activate_next_stage()
time.sleep(3)

# Работа твердотопливных ускорителей
start_time = time.time()
last_correction_time = start_time
while start_fuel() > 0:
    if time.time() - last_correction_time >= 5:
        last_correction_time = time.time()
    time.sleep(0.5)

# Переход на следующую ступень
control.activate_next_stage()
vessel = update_active_vessel()
control = vessel.control
control.throttle = 0
time.sleep(2)

# Маневр наклона и выведения
def immediate_pitch_to_horizontal():
    total_start_time = time.time()
    TOTAL_DURATION = 80.0
    APO_TARGET_LOW = 210.0
    APO_TARGET_HIGH = 215.0
    TARGET_HEADING = 90.0

    current_vessel = vessel
    control = current_vessel.control
    flight = current_vessel.flight()

    ap = current_vessel.auto_pilot
    ap.reference_frame = current_vessel.surface_reference_frame
    ap.engage()
    ap.target_roll = 0.0

    # Начальная коррекция курса
    ap.target_pitch_and_heading(90.0, TARGET_HEADING)
    time.sleep(1)

    current_heading = flight.heading
    if abs(current_heading - TARGET_HEADING) > 2.0:
        ap.target_pitch_and_heading(90.0, TARGET_HEADING)
        ap.wait()
        time.sleep(1)

    control.throttle = 1
    current_pitch = 90.0
    min_pitch = -30.0
    max_pitch = 10.0

    state = 0
    last_state_change = time.time()
    last_display = time.time()
    oscillation_count = 0
    MAX_OSCILLATIONS = 3

    # Главный цикл осциллирующего режима
    while (time.time() - total_start_time < TOTAL_DURATION
           and oscillation_count < MAX_OSCILLATIONS):
        current_time = time.time()
        current_apo = apoapsis() / 1000
        current_heading = flight.heading

        if state == 0:
            if current_apo > APO_TARGET_LOW:
                apo_difference = current_apo - APO_TARGET_LOW

                if apo_difference > 100:
                    pitch_decrement = 3.0
                elif apo_difference > 50:
                    pitch_decrement = 2.0
                elif apo_difference > 20:
                    pitch_decrement = 1.5
                elif apo_difference > 10:
                    pitch_decrement = 1.0
                elif apo_difference > 5:
                    pitch_decrement = 0.7
                else:
                    pitch_decrement = 0.3

                new_pitch = current_pitch - pitch_decrement
                current_pitch = max(min_pitch, new_pitch)

                ap.target_pitch_and_heading(current_pitch, TARGET_HEADING)

                if abs(current_heading - TARGET_HEADING) > 1.0:
                    ap.target_pitch_and_heading(current_pitch, TARGET_HEADING)
            else:
                state = 1
                last_state_change = current_time
                oscillation_count += 1
                current_pitch = min_pitch + 5.0

        elif state == 1:
            if current_apo < APO_TARGET_HIGH:
                apo_difference = APO_TARGET_HIGH - current_apo

                if apo_difference > 100:
                    pitch_increment = 3.0
                elif apo_difference > 50:
                    pitch_increment = 2.0
                elif apo_difference > 20:
                    pitch_increment = 1.5
                elif apo_difference > 10:
                    pitch_increment = 1.0
                elif apo_difference > 5:
                    pitch_increment = 0.7
                else:
                    pitch_increment = 0.3

                new_pitch = current_pitch + pitch_increment
                current_pitch = min(max_pitch, new_pitch)

                ap.target_pitch_and_heading(current_pitch, TARGET_HEADING)

                if abs(current_heading - TARGET_HEADING) > 1.0:
                    ap.target_pitch_and_heading(current_pitch, TARGET_HEADING)
            else:
                state = 0
                last_state_change = current_time
                current_pitch = max_pitch - 5.0

        time.sleep(0.05)

    # Финальная стабилизация
    APO_TARGET_MID = (APO_TARGET_LOW + APO_TARGET_HIGH) / 2
    current_apo = apoapsis() / 1000
    apo_difference = current_apo - APO_TARGET_MID

    if abs(apo_difference) > 5.0:
        if apo_difference > 0:
            final_pitch = max(min_pitch, current_pitch - 2.0)
        else:
            final_pitch = min(max_pitch, current_pitch + 2.0)

        ap.target_pitch_and_heading(final_pitch, TARGET_HEADING)
        current_pitch = final_pitch
        time.sleep(2)

    # Полет с фиксированным наклоном
    remaining_time = max(0, TOTAL_DURATION - (time.time() - total_start_time))

    if remaining_time > 0:
        phase_start = time.time()

        while time.time() - phase_start < remaining_time:
            current_heading = flight.heading

            if abs(current_heading - TARGET_HEADING) > 0.5:
                ap.target_pitch_and_heading(current_pitch, TARGET_HEADING)

            time.sleep(0.05)

    ap.disengage()
    return apoapsis()


final_apo = immediate_pitch_to_horizontal()

control.throttle = 0
control.activate_next_stage()
time.sleep(2)
vessel = update_active_vessel()
control = vessel.control

# Ожидание апоцентра
current_apo = apoapsis()
while current_apo < 200000:
    time.sleep(1)
    current_apo = apoapsis()


# Функция циркуляции орбиты
def perform_orbit_circularization(target_apo, target_peri):
    kerbin_radius = vessel.orbit.body.equatorial_radius
    current_apo_val = apoapsis() 
    current_peri_val = periapsis()

    # Переводим высоты относительно поверхности в абсолютные расстояния от центра планеты
    current_apo_abs = current_apo_val + kerbin_radius
    current_peri_abs = current_peri_val + kerbin_radius
    target_apo_abs = target_apo + kerbin_radius
    target_peri_abs = target_peri + kerbin_radius

    # Гравитационный параметр планеты (mu = G*M) и большие полуоси
    mu = vessel.orbit.body.gravitational_parameter
    current_sma = vessel.orbit.semi_major_axis          # Текущая большая полуось
    target_sma = (target_apo_abs + target_peri_abs) / 2  # Целевая большая полуось

    # Расчет требуемого изменения скорости
    v_current = math.sqrt(mu * (2 / current_apo_abs - 1 / current_sma))  # Текущая скорость в апоцентре
    v_target = math.sqrt(mu * (2 / current_apo_abs - 1 / target_sma))    # Целевая скорость в апоцентре
    delta_v = v_target - v_current  # Необходимое приращение скорости (ΔV)

    main_node = control.add_node(
        ut() + vessel.orbit.time_to_apoapsis,
        prograde=delta_v
    )

    vessel.auto_pilot.reference_frame = main_node.reference_frame
    vessel.auto_pilot.target_direction = (0, 1, 0)
    vessel.auto_pilot.engage()
    vessel.auto_pilot.wait()

    # Расчет времени работы двигателя
    F = vessel.available_thrust
    Isp = vessel.specific_impulse * 9.82

    m0 = vessel.mass
    m1 = m0 / math.exp(delta_v / Isp)
    flow_rate = F / Isp
    burn_time = (m0 - m1) / flow_rate if flow_rate > 0 else 0
    burn_time = max(0, min(burn_time, 300))

    # Выполнение маневра
    if burn_time > 0:

        while vessel.orbit.time_to_apoapsis > burn_time / 2:
            time.sleep(0.5)

        control.throttle = 1.0
        start_burn_time = time.time()
        remaining_dv = delta_v

        while (time.time() - start_burn_time < burn_time
               and remaining_dv > 5):
            elapsed = time.time() - start_burn_time

            remaining_dv = max(0, delta_v * (1 - elapsed / burn_time))
            time.sleep(0.1)

        control.throttle = 0.0
        vessel.auto_pilot.disengage()

    main_node.remove()
    time.sleep(3)
    return apoapsis(), periapsis()


# Отделение ступеней
for i in range(2):
    control.activate_next_stage()
    time.sleep(2)
    vessel = update_active_vessel()
    control = vessel.control
vessel.control.toggle_action_group(1)

# Циркуляция орбиты
target_apo = 210000
target_peri = 210000
perform_orbit_circularization(target_apo, target_peri)
time.sleep(3)

# Отделение ступеней
for i in range(2):
    control.activate_next_stage()
    time.sleep(2)
    vessel = update_active_vessel()
    control = vessel.control