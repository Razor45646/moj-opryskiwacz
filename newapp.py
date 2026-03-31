import streamlit as st
import math
import json

st.set_page_config(
    page_title="Konfigurator Opryskiwacza Autonomicznego v2",
    page_icon="🌿",
    layout="wide"
)

st.markdown("""
<style>
.card {
    border-radius: 10px; padding: 14px 18px; margin: 6px 0;
    border-left: 5px solid #ccc; background: #fafafa;
    font-size: 0.9rem; line-height: 1.6;
}
.card.ok   { border-left-color: #1a7f1a; background: #f0faf0; }
.card.err  { border-left-color: #cc2200; background: #fff5f3; }
.card.warn { border-left-color: #b85c00; background: #fff8f0; }
.card.info { border-left-color: #1a66cc; background: #f0f5ff; }
.section { font-size: 1.05rem; font-weight: 700; margin: 1.2rem 0 0.5rem; color: #222; }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# STAŁE INŻYNIERSKIE
# ═══════════════════════════════════════════════════════════════
G = 9.81
SAFETY_FACTOR = 2.0
MIN_SHAFT_MM_FOR_HEAVY = 12
# POPRAWKA #3: straty uwzględniane przez mnożnik prądu, nie dzielenie czasu
ENERGY_LOSS_FACTOR = 1.12   # rzeczywisty pobór = obliczony * 1.12
# POPRAWKA #2: typowy spadek RPM pod obciążeniem nominalnym = 15%
LOAD_RPM_DROP = 0.85
# Nacisk na grunt — limit agrotechniczny dla borówki
GROUND_PRESSURE_LIMIT_KPA = 50.0
# Szacowana powierzchnia kontaktu opony 10 cali z gruntem (m²)
TIRE_CONTACT_AREA_M2 = 0.010   # ~100 cm² na oponę

# ═══════════════════════════════════════════════════════════════
# BAZA DANYCH
# ═══════════════════════════════════════════════════════════════
MOTORS = {
    "Pololu 37D 24V 30:1 (4681) — 9 kg·cm": {
        "voltage": 24, "power_w": 20,
        "stall_torque_nm": 0.88, "rated_torque_nm": 0.22,
        "no_load_rpm": 350, "peak_current_a": 5.0, "cont_current_a": 1.5,
        "shaft_mm": 6, "qty": 4, "type": "szczotkowy"
    },
    "Pololu 37D 24V 50:1 (4683) — 23 kg·cm": {
        "voltage": 24, "power_w": 20,
        "stall_torque_nm": 2.26, "rated_torque_nm": 0.57,
        "no_load_rpm": 200, "peak_current_a": 5.0, "cont_current_a": 1.5,
        "shaft_mm": 6, "qty": 4, "type": "szczotkowy"
    },
    "Pololu 37D 24V 70:1 (4684) — 35 kg·cm": {
        "voltage": 24, "power_w": 20,
        "stall_torque_nm": 3.43, "rated_torque_nm": 0.86,
        "no_load_rpm": 140, "peak_current_a": 5.0, "cont_current_a": 1.5,
        "shaft_mm": 6, "qty": 4, "type": "szczotkowy"
    },
    "DC 250W szczotkowy 24V 120 RPM (1016WZ) — wózek inw.": {
        "voltage": 24, "power_w": 250,
        "stall_torque_nm": 20.0, "rated_torque_nm": 8.0,
        "no_load_rpm": 140, "peak_current_a": 35.0, "cont_current_a": 10.5,
        "shaft_mm": 17, "qty": 4, "type": "szczotkowy"
    },
    "Silnik planetarny 250W 24V 80 RPM": {
        "voltage": 24, "power_w": 250,
        "stall_torque_nm": 25.0, "rated_torque_nm": 9.5,
        "no_load_rpm": 100, "peak_current_a": 30.0, "cont_current_a": 11.0,
        "shaft_mm": 14, "qty": 4, "type": "planetarny"
    },
    "Silnik planetarny 400W 24V 100 RPM": {
        "voltage": 24, "power_w": 400,
        "stall_torque_nm": 35.0, "rated_torque_nm": 14.0,
        "no_load_rpm": 120, "peak_current_a": 45.0, "cont_current_a": 17.0,
        "shaft_mm": 16, "qty": 4, "type": "planetarny"
    },
    "Hub Motor 350W 24V (silnik w piaście)": {
        "voltage": 24, "power_w": 350,
        "stall_torque_nm": 40.0, "rated_torque_nm": 15.0,
        "no_load_rpm": 60, "peak_current_a": 40.0, "cont_current_a": 15.0,
        "shaft_mm": 20, "qty": 4, "type": "BLDC"
    },
}

CONTROLLERS = {
    "L298N — tani mostek (2A ciągłe)": {
        "max_current_a": 2.0, "voltage_max": 46, "channels": 2, "interface": "PWM"
    },
    "BTS7960 43A (IBT-2) — 1 kanał": {
        "max_current_a": 43.0, "voltage_max": 27, "channels": 1, "interface": "PWM"
    },
    "Cytron SmartDriveDuo MDDS30 — 2×30A": {
        "max_current_a": 30.0, "voltage_max": 35, "channels": 2, "interface": "UART/PWM/RC"
    },
    "Cytron SmartDriveDuo MDDS50 — 2×50A": {
        "max_current_a": 50.0, "voltage_max": 50, "channels": 2, "interface": "UART/PWM/RC"
    },
    "Sabertooth 2×32A": {
        "max_current_a": 32.0, "voltage_max": 30, "channels": 2, "interface": "UART/RC/analog"
    },
    "RoboClaw 2×60A": {
        "max_current_a": 60.0, "voltage_max": 34, "channels": 2, "interface": "UART/RC/analog"
    },
}

BATTERIES = {
    "LiFePO4 24V 20Ah (480 Wh)": {"voltage": 24, "capacity_ah": 20, "chemistry": "LiFePO4"},
    "LiFePO4 24V 40Ah (960 Wh)": {"voltage": 24, "capacity_ah": 40, "chemistry": "LiFePO4"},
    "LiFePO4 24V 60Ah (1440 Wh)": {"voltage": 24, "capacity_ah": 60, "chemistry": "LiFePO4"},
    "LiFePO4 48V 30Ah (1440 Wh)": {"voltage": 48, "capacity_ah": 30, "chemistry": "LiFePO4"},
    "LiFePO4 48V 40Ah (1920 Wh)": {"voltage": 48, "capacity_ah": 40, "chemistry": "LiFePO4"},
    "AGM 2×12V 100Ah szeregowo (24V)": {"voltage": 24, "capacity_ah": 100, "chemistry": "AGM"},
}

COMPUTERS = {
    "Raspberry Pi 5 8GB":           {"power_w": 12, "ai_capable": False},
    "NVIDIA Jetson Orin Nano 8GB":  {"power_w": 15, "ai_capable": True},
    "NVIDIA Jetson Orin NX 16GB":   {"power_w": 25, "ai_capable": True},
}

SENSORS = {
    "RPLiDAR A1 (zasięg 12m)":        {"power_w": 3.0},
    "RPLiDAR A3 (zasięg 25m)":        {"power_w": 4.5},
    "Intel RealSense D435i":           {"power_w": 4.5},
    "Luxonis OAK-D":                   {"power_w": 4.0},
    "GPS RTK Ardusimple SimpleRTK2B":  {"power_w": 1.0},
}

SPRAY_PUMPS = {
    "Brak pompy":                     {"power_w": 0,   "voltage": 0,  "flow_lpm": 0},
    "Shurflo 8007 12V 8 L/min":      {"power_w": 60,  "voltage": 12, "flow_lpm": 8},
    "Shurflo 8007 24V 8 L/min":      {"power_w": 80,  "voltage": 24, "flow_lpm": 8},
    "Pompa membranowa 24V 15 L/min": {"power_w": 120, "voltage": 24, "flow_lpm": 15},
}

TERRAIN = {
    "Asfalt / twarda nawierzchnia":    0.02,
    "Trawa / miękka darń":             0.10,
    "Miękka ziemia / torf (borówka)": 0.15,
}

# ═══════════════════════════════════════════════════════════════
# FUNKCJE OBLICZENIOWE — POPRAWIONA FIZYKA
# ═══════════════════════════════════════════════════════════════

def calc_torque(mass_kg, Cr, r_m, slope_deg, safety, qty):
    """
    Moment startowy z uwzględnieniem oporu toczenia I pochylenia terenu.
    T = (m*g*Cr*r + m*g*sin(α)*r) * S  — pełny wzór
    """
    alpha = math.radians(slope_deg)
    T_roll  = mass_kg * G * Cr * r_m           # opór toczenia [Nm]
    T_slope = mass_kg * G * math.sin(alpha) * r_m  # składnik grawitacyjny [Nm]
    T_total = (T_roll + T_slope) * safety
    T_per_motor = T_total / qty
    return T_total, T_per_motor, T_roll * safety, T_slope * safety


def calc_shaft_stress(mass_kg, shaft_mm, r_m):
    """
    Przybliżone naprężenie gnące wału [MPa] przy montażu bezpośrednim.
    σ = M_b / W_x gdzie M_b = F_radial * L_overhang, W_x = π*d³/32
    Zakładamy L_overhang = 30 mm, F_radial ≈ 0.3 * (masa/4 * g)
    Stal S235: granica plastyczności Re = 235 MPa
    """
    F_radial = (mass_kg / 4) * G * 0.3   # siła poprzeczna na wał [N]
    L_oh = 0.030                           # wysięg wału [m]
    M_b = F_radial * L_oh                  # moment gnący [Nm]
    d = shaft_mm / 1000.0
    W_x = math.pi * d**3 / 32             # wskaźnik wytrzymałości [m³]
    sigma_mpa = (M_b / W_x) / 1e6        # naprężenie [MPa]
    re_s235 = 235.0
    safety_margin = re_s235 / sigma_mpa if sigma_mpa > 0 else 999
    return sigma_mpa, safety_margin


def calc_ground_pressure(mass_kg, num_wheels, contact_area_m2):
    """
    Nacisk na grunt [kPa] = F / A
    """
    F_total = mass_kg * G
    A_total = num_wheels * contact_area_m2
    p_kpa = (F_total / A_total) / 1000.0
    return p_kpa


def calc_speed(no_load_rpm, r_m, load_factor=LOAD_RPM_DROP):
    """
    Prędkość liniowa przy obciążeniu nominalnym.
    POPRAWKA: używamy spadku RPM ~15% (nie 25%).
    V = (RPM_real * 2π * r) / 60
    """
    rpm_loaded = no_load_rpm * load_factor
    v_ms = (rpm_loaded * 2 * math.pi * r_m) / 60.0
    return v_ms, rpm_loaded


def calc_spray_dose(flow_lpm, nozzles, v_ms, row_spacing_m):
    """
    Dawka oprysku [L/ha] = (Q_total [L/min] / (v [m/min] * szerokość_robocza [m])) * 10000
    Szerokość robocza ≈ rozstaw rzędów (robot jedzie jednym międzyrzędziem)
    """
    if v_ms <= 0 or flow_lpm <= 0:
        return 0.0
    Q_total_lpm = flow_lpm   # jedna pompa dla wszystkich dysz
    v_mpm = v_ms * 60.0      # prędkość w m/min
    working_width_m = row_spacing_m
    dose_l_ha = (Q_total_lpm / (v_mpm * working_width_m)) * 10000.0
    return dose_l_ha


def calc_energy_balance(motor, qty, extra_w, batt):
    """
    POPRAWKA #3: straty uwzględniane przez mnożnik prądu
    I_real = I_nominal * ENERGY_LOSS_FACTOR
    t = C_ah / I_real
    """
    motor_cont_a = motor["cont_current_a"] * qty
    extra_a = extra_w / batt["voltage"] if batt["voltage"] > 0 else 0
    total_a_nominal = motor_cont_a + extra_a
    total_a_real = total_a_nominal * ENERGY_LOSS_FACTOR  # uwzględnia straty
    runtime_h = batt["capacity_ah"] / total_a_real if total_a_real > 0 else 0
    total_w_real = total_a_real * batt["voltage"]
    return total_a_nominal, total_a_real, total_w_real, runtime_h


# ═══════════════════════════════════════════════════════════════
# INTERFEJS
# ═══════════════════════════════════════════════════════════════

st.title("🌿 Konfigurator Autonomicznego Opryskiwacza Polowego")
st.caption("Walidacja fizyczna i elektryczna • wzory inżynierskie v2 • poprawiona fizyka")
st.markdown("---")

col_left, col_mid, col_right = st.columns([1.0, 1.3, 1.7])

with col_left:
    st.markdown("### ⚙️ Parametry fizyczne")
    total_mass_kg = st.slider("Masa całkowita pojazdu (kg)", 20, 350, 145, 5,
                              help="Rama + akumulator + elektronika + zbiornik z cieczą")
    wheel_diameter_mm = st.slider("Średnica koła (mm)", 150, 600, 254, 5,
                                  help="Koło 10 cali = 254 mm | Koło 12 cali = 305 mm")
    terrain_choice = st.selectbox("Typ terenu", list(TERRAIN.keys()), index=2)
    Cr = TERRAIN[terrain_choice]
    r_m = (wheel_diameter_mm / 2) / 1000.0

    # NOWE: kąt pochylenia terenu
    slope_deg = st.slider("Pochylenie terenu (°)", 0, 20, 3, 1,
                          help="Typowe pole borówki: 2–5°")

    st.info(f"Cr = {Cr}  |  r = {r_m*1000:.0f} mm  |  α = {slope_deg}°")

    st.markdown("---")
    st.markdown("### 💧 Parametry pola")
    tank_vol = st.slider("Pojemność zbiornika (L)", 0, 200, 100, 10)
    row_len_m = st.slider("Długość rzędu (m)", 10, 400, 180, 10)
    num_rows = st.number_input("Liczba rzędów", 1, 100, 21, 1)
    row_spacing_m = st.slider("Rozstaw rzędów (m)", 1.0, 4.0, 3.0, 0.1,
                              help="Odległość między środkami rzędów borówki")
    total_route_m = int(num_rows) * row_len_m

    # WALIDACJA: masa cieczy vs masa pojazdu
    if tank_vol > total_mass_kg * 0.9:
        st.warning(f"⚠️ Zbiornik {tank_vol}L ({tank_vol} kg) to >{int(tank_vol/total_mass_kg*100)}% "
                   f"zadeklarowanej masy pojazdu {total_mass_kg} kg. "
                   f"Upewnij się że masa całkowita już uwzględnia ciecz.")

    st.caption(f"Ciecz: ~{tank_vol} kg  |  Trasa łącznie: {total_route_m} m")

with col_mid:
    st.markdown("### 🔩 Napęd")
    motor_choice = st.selectbox("Silnik (×4 sztuki)", list(MOTORS.keys()))
    motor = MOTORS[motor_choice]
    ctrl_choice = st.selectbox("Sterownik silników", list(CONTROLLERS.keys()))
    ctrl = CONTROLLERS[ctrl_choice]

    st.markdown("### 🔋 Zasilanie")
    batt_choice = st.selectbox("Akumulator", list(BATTERIES.keys()))
    batt = BATTERIES[batt_choice]

    st.markdown("### 🖥️ Elektronika")
    comp_choice = st.selectbox("Komputer główny", list(COMPUTERS.keys()))
    comp = COMPUTERS[comp_choice]
    sensor_choice = st.selectbox("Sensor / LiDAR", list(SENSORS.keys()))
    sensor = SENSORS[sensor_choice]
    gps_on    = st.checkbox("GPS RTK Ardusimple (+1 W)",   value=True)
    imu_on    = st.checkbox("IMU BNO085 (+0.3 W)",          value=True)
    router_on = st.checkbox("Router WiFi 5 GHz (+8 W)",     value=True)

    st.markdown("### 🚿 Moduł oprysku")
    pump_choice  = st.selectbox("Pompa opryskiwacza", list(SPRAY_PUMPS.keys()))
    pump = SPRAY_PUMPS[pump_choice]
    nozzle_count = st.number_input("Liczba dysz", 1, 20, 10, 1)

# ═══════════════════════════════════════════════════════════════
# OBLICZENIA — WSZYSTKIE MODUŁY
# ═══════════════════════════════════════════════════════════════

qty = motor["qty"]

# 1. Moment obrotowy (pełny wzór z pochyleniem)
T_req_total, T_req_motor, T_roll_part, T_slope_part = calc_torque(
    total_mass_kg, Cr, r_m, slope_deg, SAFETY_FACTOR, qty
)
T_avail_total = motor["stall_torque_nm"] * qty
torque_ok = T_avail_total >= T_req_total
reserve_pct = ((T_avail_total / T_req_total) - 1) * 100 if T_req_total > 0 else 0

# 2. Wytrzymałość wału — naprężenia
shaft_risk = (total_mass_kg > 80 and motor["shaft_mm"] < MIN_SHAFT_MM_FOR_HEAVY)
sigma_mpa, shaft_safety_margin = calc_shaft_stress(total_mass_kg, motor["shaft_mm"], r_m)

# 3. Napięcie
voltage_ok = (batt["voltage"] == motor["voltage"])

# 4. Sterownik
channels_per_ctrl = ctrl["channels"]
num_ctrls_needed = math.ceil(qty / channels_per_ctrl)
ctrl_current_ok = ctrl["max_current_a"] >= motor["peak_current_a"]
ctrl_voltage_ok = ctrl["voltage_max"] >= batt["voltage"]

# 5. Prędkość (POPRAWKA: 85% no-load RPM)
v_ms, rpm_loaded = calc_speed(motor["no_load_rpm"], r_m)
v_kmh = v_ms * 3.6
route_time_h = (total_route_m / v_ms) / 3600.0 if v_ms > 0 else 0

# 6. Bilans energetyczny (POPRAWKA: straty mnożnikiem prądu)
extra_w = (
    comp["power_w"] + sensor["power_w"]
    + (1.0 if gps_on else 0)
    + (0.3 if imu_on else 0)
    + (8.0 if router_on else 0)
    + pump["power_w"]
)
total_a_nom, total_a_real, total_w_real, runtime_h = calc_energy_balance(
    motor, qty, extra_w, batt
)
runtime_ok = runtime_h >= route_time_h

# 7. Nacisk na grunt (NOWE)
ground_kpa = calc_ground_pressure(total_mass_kg, qty, TIRE_CONTACT_AREA_M2)
ground_ok = ground_kpa <= GROUND_PRESSURE_LIMIT_KPA

# 8. Dawka oprysku L/ha (NOWE)
dose_l_ha = calc_spray_dose(pump["flow_lpm"], nozzle_count, v_ms, row_spacing_m)
area_ha = (total_route_m * row_spacing_m) / 10000.0
total_liquid_needed = dose_l_ha * area_ha
refills_needed = math.ceil(total_liquid_needed / tank_vol) if tank_vol > 0 else 0

# 9. Pompa
pump_ok = (pump["voltage"] == 0 or pump["voltage"] <= batt["voltage"])

# ═══════════════════════════════════════════════════════════════
# PRAWY PANEL — RAPORT
# ═══════════════════════════════════════════════════════════════

with col_right:
    st.markdown("### 📋 Dynamiczny Raport Kompatybilności")

    # ── 1. Moment obrotowy ─────────────────────────────────────
    st.markdown('<div class="section">1. Moment obrotowy  T = (m·g·Cr·r + m·g·sin α·r) · S</div>',
                unsafe_allow_html=True)
    f_str = (f"T_toczenie = {T_roll_part:.2f} Nm  |  "
             f"T_pochylenie ({slope_deg}°) = {T_slope_part:.2f} Nm<br>"
             f"T_wymagane łącznie = <b>{T_req_total:.2f} Nm</b>  "
             f"({T_req_motor:.2f} Nm/silnik)<br>"
             f"T_dostępne = {motor['stall_torque_nm']:.2f} × {qty} = "
             f"<b>{T_avail_total:.2f} Nm</b>")
    if torque_ok:
        st.markdown(
            f'<div class="card ok">✅ <b>MOMENT OK</b> — rezerwa {reserve_pct:.0f}%<br>{f_str}</div>',
            unsafe_allow_html=True)
    else:
        deficit = T_req_total - T_avail_total
        st.markdown(
            f'<div class="card err">❌ <b>NIEWYSTARCZAJĄCY MOMENT</b><br>{f_str}<br>'
            f'Brakuje: <b>{deficit:.2f} Nm</b> — wybierz silnik o wyższym Stall Torque.</div>',
            unsafe_allow_html=True)

    # ── 2. Wytrzymałość wału ───────────────────────────────────
    st.markdown('<div class="section">2. Wytrzymałość wału  σ = M_b / W_x</div>',
                unsafe_allow_html=True)
    shaft_cls = "err" if (shaft_risk or shaft_safety_margin < 1.5) else \
                "warn" if shaft_safety_margin < 3.0 else "ok"
    shaft_icon = "❌" if shaft_cls == "err" else ("⚠️" if shaft_cls == "warn" else "✅")

    shaft_detail = (f"Naprężenie obliczone: <b>{sigma_mpa:.1f} MPa</b>  "
                    f"(stal S235: Re = 235 MPa)<br>"
                    f"Zapas bezpieczeństwa: <b>{shaft_safety_margin:.1f}×</b>  "
                    f"(min. zalecany: 2.0×)<br>"
                    f"Wał: {motor['shaft_mm']} mm  |  Masa: {total_mass_kg} kg")

    if shaft_risk:
        st.markdown(
            f'<div class="card err">{shaft_icon} <b>RYZYKO MECHANICZNEGO ŚCIĘCIA WAŁU</b><br>'
            f'{shaft_detail}<br>'
            f'Rozwiązanie: silnik z wałem ≥ 12 mm lub napęd łańcuchowy/pasowy.</div>',
            unsafe_allow_html=True)
    else:
        st.markdown(
            f'<div class="card {shaft_cls}">{shaft_icon} <b>WAŁ OK</b><br>{shaft_detail}</div>',
            unsafe_allow_html=True)

    # ── 3. Nacisk na grunt (NOWE) ──────────────────────────────
    st.markdown('<div class="section">3. Nacisk na grunt  p = F / A  [kPa]</div>',
                unsafe_allow_html=True)
    gnd_cls = "ok" if ground_ok else "err"
    gnd_icon = "✅" if ground_ok else "❌"
    st.markdown(
        f'<div class="card {gnd_cls}">{gnd_icon} <b>Nacisk: {ground_kpa:.1f} kPa</b> '
        f'(limit dla borówki: {GROUND_PRESSURE_LIMIT_KPA} kPa)<br>'
        f'F = {total_mass_kg}×{G} = {total_mass_kg*G:.0f} N  |  '
        f'A = {qty}×{TIRE_CONTACT_AREA_M2*10000:.0f} cm² = {qty*TIRE_CONTACT_AREA_M2*10000:.0f} cm²<br>'
        f'{"OK — korzenie borówki bezpieczne." if ground_ok else "UWAGA: zbyt wysoki nacisk może uszkodzić płytkie korzenie borówki!"}</div>',
        unsafe_allow_html=True)

    # ── 4. Kompatybilność napięciowa ───────────────────────────
    st.markdown('<div class="section">4. Kompatybilność napięciowa</div>',
                unsafe_allow_html=True)
    if voltage_ok:
        st.markdown(
            f'<div class="card ok">✅ <b>NAPIĘCIE OK</b> — '
            f'Akumulator {batt["voltage"]}V = Silnik {motor["voltage"]}V</div>',
            unsafe_allow_html=True)
    else:
        st.markdown(
            f'<div class="card err">❌ <b>NIEZGODNOŚĆ NAPIĘCIA</b> — '
            f'Akumulator {batt["voltage"]}V ≠ Silnik {motor["voltage"]}V.<br>'
            f'Wymagana przetwornica DC-DC lub zmiana komponentu.</div>',
            unsafe_allow_html=True)

    # ── 5. Sterownik ───────────────────────────────────────────
    st.markdown('<div class="section">5. Sterownik silników</div>',
                unsafe_allow_html=True)
    if not ctrl_voltage_ok:
        st.markdown(
            f'<div class="card err">❌ <b>NAPIĘCIE STEROWNIKA ZA NISKIE</b> — '
            f'Max {ctrl["voltage_max"]}V &lt; Akumulator {batt["voltage"]}V.<br>'
            f'Zamień na sterownik obsługujący ≥{batt["voltage"]}V.</div>',
            unsafe_allow_html=True)
    elif ctrl_current_ok:
        st.markdown(
            f'<div class="card ok">✅ <b>STEROWNIK OK</b><br>'
            f'Peak silnika {motor["peak_current_a"]}A ≤ Max sterownika {ctrl["max_current_a"]}A<br>'
            f'Potrzebna liczba sterowników: <b>{num_ctrls_needed} szt.</b>  '
            f'(po {channels_per_ctrl} kanały/szt.)<br>'
            f'Interfejs: {ctrl["interface"]}  |  Max napięcie: {ctrl["voltage_max"]}V</div>',
            unsafe_allow_html=True)
    else:
        excess = motor["peak_current_a"] - ctrl["max_current_a"]
        st.markdown(
            f'<div class="card err">❌ <b>STEROWNIK ZA SŁABY</b><br>'
            f'Peak silnika {motor["peak_current_a"]}A &gt; Max sterownika {ctrl["max_current_a"]}A<br>'
            f'Przekroczenie o {excess:.0f}A — ryzyko przegrzania i spalenia.<br>'
            f'Użyj sterownika z prądem max ≥{motor["peak_current_a"]}A.</div>',
            unsafe_allow_html=True)

    # ── 6. Prędkość (poprawiony wzór) ──────────────────────────
    st.markdown('<div class="section">6. Prędkość robota  V = (RPM_real · 2π · r) / 60</div>',
                unsafe_allow_html=True)
    speed_ok = 0.5 <= v_kmh <= 4.0
    scls = "ok" if speed_ok else "warn"
    snote = ""
    if v_kmh > 4.0:
        snote = "<br>⚠️ Za szybko jak na oprysk! Optymalne 1–3 km/h."
    elif v_kmh < 0.5:
        snote = "<br>⚠️ Za wolno — sprawdź parametry silnika."
    st.markdown(
        f'<div class="card {scls}">{"✅" if speed_ok else "⚠️"} '
        f'<b>Prędkość robocza: {v_kmh:.2f} km/h</b>{snote}<br>'
        f'RPM no-load: {motor["no_load_rpm"]}  →  RPM pod obciążeniem: {rpm_loaded:.0f} '
        f'({LOAD_RPM_DROP*100:.0f}% no-load)<br>'
        f'Promień koła: {r_m*100:.1f} cm  |  V = ({rpm_loaded:.0f}·2π·{r_m:.3f})/60</div>',
        unsafe_allow_html=True)

    # ── 7. Bilans energetyczny (poprawiony) ────────────────────
    st.markdown('<div class="section">7. Bilans energetyczny  t = C_ah / (I_nom · 1.12)</div>',
                unsafe_allow_html=True)
    ecls = "ok" if runtime_ok else "err"
    eicon = "✅" if runtime_ok else "❌"
    elabel = "WYSTARCZAJĄCY" if runtime_ok else "NIEWYSTARCZAJĄCY"
    st.markdown(
        f'<div class="card {ecls}">{eicon} <b>CZAS PRACY — {elabel}</b><br>'
        f'Prąd silników (ciągły): {motor["cont_current_a"]*qty:.1f} A  '
        f'({motor["cont_current_a"]} A × {qty})<br>'
        f'Elektronika + pompa: {extra_w:.0f} W → {extra_w/batt["voltage"]:.1f} A<br>'
        f'Prąd nominalny: {total_a_nom:.1f} A  →  z stratami (+12%): '
        f'<b>{total_a_real:.1f} A</b>  ({total_w_real:.0f} W)<br>'
        f'Czas pracy: <b>{runtime_h:.1f} h</b>  |  '
        f'Czas przejazdu pola: <b>{route_time_h:.2f} h</b></div>',
        unsafe_allow_html=True)

    # ── 8. Dawka oprysku (NOWE) ────────────────────────────────
    if pump["flow_lpm"] > 0:
        st.markdown('<div class="section">8. Agrotechnika oprysku  Dawka [L/ha]</div>',
                    unsafe_allow_html=True)
        dose_ok = 100 <= dose_l_ha <= 500
        dcls = "ok" if dose_ok else "warn"
        dicon = "✅" if dose_ok else "⚠️"
        dose_note = ""
        if dose_l_ha > 500:
            dose_note = "<br>Za wysoka dawka! Typowo dla borówki: 150–300 L/ha."
        elif dose_l_ha < 100:
            dose_note = "<br>Za niska dawka — ryzyko niedostatecznego pokrycia."
        st.markdown(
            f'<div class="card {dcls}">{dicon} <b>Dawka: {dose_l_ha:.0f} L/ha</b>{dose_note}<br>'
            f'Wzór: Dawka = (Q [L/min] / (v [m/min] × sz.rob. [m])) × 10000<br>'
            f'= ({pump["flow_lpm"]} / ({v_ms*60:.1f} × {row_spacing_m})) × 10000<br>'
            f'Pole całkowite: <b>{area_ha:.2f} ha</b>  |  '
            f'Cieczy potrzeba: <b>{total_liquid_needed:.0f} L</b><br>'
            f'Napełnień zbiornika ({tank_vol}L): <b>{refills_needed} razy</b></div>',
            unsafe_allow_html=True)

    # ── 9. Pompa ───────────────────────────────────────────────
    if pump["voltage"] > 0:
        st.markdown('<div class="section">9. Moduł oprysku</div>',
                    unsafe_allow_html=True)
        if pump_ok:
            extra_note = ""
            if pump["voltage"] < batt["voltage"]:
                extra_note = (f" (przez przetwornicę "
                              f"{batt['voltage']}V → {pump['voltage']}V)")
            st.markdown(
                f'<div class="card ok">✅ <b>POMPA OK</b> — {pump_choice}<br>'
                f'Napięcie: {pump["voltage"]}V{extra_note}  |  '
                f'Pobór: {pump["power_w"]}W  |  Dysze: {nozzle_count}</div>',
                unsafe_allow_html=True)
        else:
            st.markdown(
                f'<div class="card err">❌ <b>NIEZGODNOŚĆ NAPIĘCIA POMPY</b> — '
                f'Pompa {pump["voltage"]}V &gt; Akumulator {batt["voltage"]}V.</div>',
                unsafe_allow_html=True)

    # ── PODSUMOWANIE ────────────────────────────────────────────
    st.markdown("---")
    checks = [torque_ok, not shaft_risk, ground_ok, voltage_ok,
              ctrl_current_ok, ctrl_voltage_ok, runtime_ok, pump_ok]
    labels_chk = [
        ("Moment obrotowy",         torque_ok),
        ("Wytrzymałość wału",        not shaft_risk),
        ("Nacisk na grunt",          ground_ok),
        ("Napięcie silnik/bateria",  voltage_ok),
        ("Sterownik — prąd",        ctrl_current_ok),
        ("Sterownik — napięcie",    ctrl_voltage_ok),
        ("Bilans energetyczny",     runtime_ok),
        ("Napięcie pompy",          pump_ok),
    ]
    passed = sum(checks)
    total  = len(checks)
    pct    = int(passed / total * 100)

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        for name, ok in labels_chk[:4]:
            st.markdown(f"{'✅' if ok else '❌'} {name}")
    with col_s2:
        for name, ok in labels_chk[4:]:
            st.markdown(f"{'✅' if ok else '❌'} {name}")

    st.markdown("")
    if pct == 100:
        st.success(f"✅ Wszystkie {total} sprawdzenia zaliczone ({pct}%). Konfiguracja gotowa!")
    elif pct >= 75:
        st.warning(f"⚠️ {passed}/{total} sprawdzeń OK ({pct}%). Popraw zaznaczone błędy.")
    else:
        st.error(f"❌ {passed}/{total} sprawdzeń OK ({pct}%). Konfiguracja wymaga korekty.")

    # Eksport JSON
    config_export = {
        "motor": motor_choice, "controller": ctrl_choice,
        "controllers_needed": num_ctrls_needed,
        "battery": batt_choice, "terrain": terrain_choice,
        "slope_deg": slope_deg, "mass_kg": total_mass_kg,
        "wheel_diameter_mm": wheel_diameter_mm,
        "torque_required_nm": round(T_req_total, 2),
        "torque_available_nm": round(T_avail_total, 2),
        "torque_reserve_pct": round(reserve_pct, 1),
        "shaft_stress_mpa": round(sigma_mpa, 1),
        "shaft_safety_margin": round(shaft_safety_margin, 2),
        "ground_pressure_kpa": round(ground_kpa, 1),
        "speed_kmh": round(v_kmh, 2),
        "runtime_h": round(runtime_h, 2),
        "route_time_h": round(route_time_h, 2),
        "spray_dose_l_ha": round(dose_l_ha, 0) if pump["flow_lpm"] > 0 else None,
        "refills_needed": refills_needed if pump["flow_lpm"] > 0 else None,
        "status_pct": pct,
        "status": "OK" if pct == 100 else "Needs fixes"
    }

    st.download_button(
        label="📤 Pobierz konfigurację jako JSON",
        data=json.dumps(config_export, indent=2, ensure_ascii=False),
        file_name="opryskiwacz_config.json",
        mime="application/json",
        use_container_width=True
    )

    st.caption(
        "Wzory: T=(m·g·Cr·r + m·g·sin α·r)·S | σ=M_b/W_x | "
        "p=F/A | t=C/(I·1.12) | V=(RPM·0.85·2π·r)/60 | "
        "Dawka=Q/(v·szer)·10000"
    )
