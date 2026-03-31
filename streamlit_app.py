import streamlit as st
import math

st.set_page_config(
    page_title="Konfigurator Opryskiwacza Autonomicznego",
    page_icon="🌿",
    layout="wide"
)

st.markdown("""
<style>
.ok   { color: #1a7f1a; font-weight: 600; font-size: 0.95rem; }
.err  { color: #cc2200; font-weight: 600; font-size: 0.95rem; }
.warn { color: #b85c00; font-weight: 600; font-size: 0.95rem; }
.card {
    border-radius: 10px;
    padding: 14px 18px;
    margin: 6px 0;
    border-left: 5px solid #ccc;
    background: #fafafa;
    font-size: 0.9rem;
    line-height: 1.6;
}
.card.ok   { border-left-color: #1a7f1a; background: #f0faf0; }
.card.err  { border-left-color: #cc2200; background: #fff5f3; }
.card.warn { border-left-color: #b85c00; background: #fff8f0; }
.card.info { border-left-color: #1a66cc; background: #f0f5ff; }
.section { font-size: 1.05rem; font-weight: 700; margin: 1.2rem 0 0.5rem; color: #222; }
</style>
""", unsafe_allow_html=True)

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
        "max_current_a": 2.0, "voltage_max": 46,
        "channels": 2, "interface": "PWM"
    },
    "BTS7960 43A (IBT-2) — 1 kanał": {
        "max_current_a": 43.0, "voltage_max": 27,
        "channels": 1, "interface": "PWM"
    },
    "Cytron SmartDriveDuo MDDS30 — 2×30A": {
        "max_current_a": 30.0, "voltage_max": 35,
        "channels": 2, "interface": "UART/PWM/RC"
    },
    "Cytron SmartDriveDuo MDDS50 — 2×50A": {
        "max_current_a": 50.0, "voltage_max": 50,
        "channels": 2, "interface": "UART/PWM/RC"
    },
    "Sabertooth 2×32A": {
        "max_current_a": 32.0, "voltage_max": 30,
        "channels": 2, "interface": "UART/RC/analog"
    },
    "RoboClaw 2×60A": {
        "max_current_a": 60.0, "voltage_max": 34,
        "channels": 2, "interface": "UART/RC/analog"
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
    "RPLiDAR A1 (zasięg 12m)":       {"power_w": 3.0},
    "RPLiDAR A3 (zasięg 25m)":       {"power_w": 4.5},
    "Intel RealSense D435i":          {"power_w": 4.5},
    "Luxonis OAK-D":                  {"power_w": 4.0},
    "GPS RTK Ardusimple SimpleRTK2B": {"power_w": 1.0},
}

SPRAY_PUMPS = {
    "Brak pompy":                        {"power_w": 0,   "voltage": 0},
    "Shurflo 8007 12V 8 L/min":         {"power_w": 60,  "voltage": 12},
    "Shurflo 8007 24V 8 L/min":         {"power_w": 80,  "voltage": 24},
    "Pompa membranowa 24V 15 L/min":    {"power_w": 120, "voltage": 24},
}

TERRAIN = {
    "Asfalt / twarda nawierzchnia":     0.02,
    "Trawa / miękka darń":              0.10,
    "Miękka ziemia / torf (borówka)":  0.15,
}

# ═══════════════════════════════════════════════════════════════
# NAGŁÓWEK
# ═══════════════════════════════════════════════════════════════

st.title("🌿 Konfigurator Autonomicznego Opryskiwacza Polowego")
st.caption("Walidacja fizyczna i elektryczna doboru komponentów — wzory inżynierskie")
st.markdown("---")

col_left, col_mid, col_right = st.columns([1.0, 1.3, 1.7])

# ═══════════════════════════════════════════════════════════════
# LEWY PANEL
# ═══════════════════════════════════════════════════════════════
with col_left:
    st.markdown("### ⚙️ Parametry fizyczne")

    total_mass_kg = st.slider(
        "Masa całkowita pojazdu (kg)",
        min_value=20, max_value=350, value=145, step=5,
        help="Rama + akumulator + elektronika + zbiornik z cieczą"
    )
    wheel_diameter_mm = st.slider(
        "Średnica koła (mm)",
        min_value=150, max_value=600, value=254, step=5,
        help="Koło 10 cali = 254 mm | Koło 12 cali = 305 mm"
    )
    terrain_choice = st.selectbox("Typ terenu", list(TERRAIN.keys()), index=2)
    Cr = TERRAIN[terrain_choice]
    st.info(f"Cr = {Cr}  |  r = {wheel_diameter_mm/2:.0f} mm")

    st.markdown("---")
    st.markdown("### 💧 Parametry pola")
    tank_vol    = st.slider("Pojemność zbiornika (L)", 0, 200, 100, 10)
    row_len_m   = st.slider("Długość rzędu (m)", 10, 400, 180, 10)
    num_rows    = st.number_input("Liczba rzędów", 1, 100, 21, 1)
    st.caption(f"Masa cieczy: ~{tank_vol} kg  |  Łączna trasa: {int(num_rows * row_len_m)} m")

# ═══════════════════════════════════════════════════════════════
# ŚRODKOWY PANEL
# ═══════════════════════════════════════════════════════════════
with col_mid:
    st.markdown("### 🔩 Napęd")
    motor_choice = st.selectbox("Silnik (×4 sztuki)", list(MOTORS.keys()))
    motor = MOTORS[motor_choice]
    ctrl_choice  = st.selectbox("Sterownik silników", list(CONTROLLERS.keys()))
    ctrl  = CONTROLLERS[ctrl_choice]

    st.markdown("### 🔋 Zasilanie")
    batt_choice = st.selectbox("Akumulator", list(BATTERIES.keys()))
    batt = BATTERIES[batt_choice]

    st.markdown("### 🖥️ Elektronika")
    comp_choice   = st.selectbox("Komputer główny", list(COMPUTERS.keys()))
    comp = COMPUTERS[comp_choice]
    sensor_choice = st.selectbox("Sensor / LiDAR", list(SENSORS.keys()))
    sensor = SENSORS[sensor_choice]
    gps_on    = st.checkbox("GPS RTK Ardusimple (+1 W)",   value=True)
    imu_on    = st.checkbox("IMU BNO085 (+0.3 W)",         value=True)
    router_on = st.checkbox("Router WiFi 5 GHz (+8 W)",    value=True)

    st.markdown("### 🚿 Moduł oprysku")
    pump_choice  = st.selectbox("Pompa opryskiwacza", list(SPRAY_PUMPS.keys()))
    pump = SPRAY_PUMPS[pump_choice]
    nozzle_count = st.number_input("Liczba dysz", 1, 20, 10, 1)

# ═══════════════════════════════════════════════════════════════
# OBLICZENIA
# ═══════════════════════════════════════════════════════════════

g   = 9.81
S   = 2.0
qty = motor["qty"]   # 4 silniki
r_m = (wheel_diameter_mm / 2) / 1000.0

# 1. Moment obrotowy  T = (m * g * f * r) * S
T_req_total    = total_mass_kg * g * Cr * r_m * S
T_req_motor    = T_req_total / qty
T_avail_total  = motor["stall_torque_nm"] * qty
torque_ok      = T_avail_total >= T_req_total

# 2. Wytrzymałość wału
shaft_risk = (total_mass_kg > 80 and motor["shaft_mm"] < 12)

# 3. Napięcie silnik vs akumulator
voltage_ok = (batt["voltage"] == motor["voltage"])

# 4. Sterownik — prąd szczytowy silnika vs max sterownika
ctrl_current_ok  = (ctrl["max_current_a"] >= motor["peak_current_a"])
ctrl_voltage_ok  = (ctrl["voltage_max"]   >= batt["voltage"])
controller_ok    = ctrl_current_ok and ctrl_voltage_ok

# 5. Bilans energetyczny
extra_w = (
    comp["power_w"] + sensor["power_w"]
    + (1.0 if gps_on    else 0)
    + (0.3 if imu_on    else 0)
    + (8.0 if router_on else 0)
    + pump["power_w"]
)
motor_cont_a  = motor["cont_current_a"] * qty
extra_a       = extra_w / batt["voltage"] if batt["voltage"] > 0 else 0
total_a       = motor_cont_a + extra_a
total_w       = motor_cont_a * batt["voltage"] + extra_w
runtime_h     = batt["capacity_ah"] / total_a if total_a > 0 else 0

v_ms          = (motor["no_load_rpm"] * 2 * math.pi * r_m) / 60.0
v_kmh         = v_ms * 3.6
total_route_m = num_rows * row_len_m
route_time_h  = (total_route_m / v_ms) / 3600.0 if v_ms > 0 else 0
runtime_ok    = runtime_h >= route_time_h

# 6. Pompa
pump_ok = (pump["voltage"] == 0 or pump["voltage"] <= batt["voltage"])

# ═══════════════════════════════════════════════════════════════
# PRAWY PANEL — RAPORT
# ═══════════════════════════════════════════════════════════════
with col_right:
    st.markdown("### 📋 Dynamiczny Raport Kompatybilności")

    # ── 1. Moment obrotowy ─────────────────────────────────────
    st.markdown('<div class="section">1. Moment obrotowy  T = (m · g · f · r) · S</div>', unsafe_allow_html=True)
    formula = (f"T = ({total_mass_kg} · {g} · {Cr} · {r_m:.3f}) · {S} "
               f"= <b>{T_req_total:.2f} Nm</b> wymagane łącznie")
    avail   = (f"Dostępne: {motor['stall_torque_nm']:.2f} Nm/sil × {qty} "
               f"= <b>{T_avail_total:.2f} Nm</b>")
    if torque_ok:
        reserve = ((T_avail_total / T_req_total) - 1) * 100
        st.markdown(
            f'<div class="card ok">✅ <b>MOMENT OK</b><br>{formula}<br>{avail}<br>'
            f'Na silnik wymagane: {T_req_motor:.2f} Nm  |  Rezerwa: {reserve:.0f}%</div>',
            unsafe_allow_html=True)
    else:
        deficit = T_req_total - T_avail_total
        st.markdown(
            f'<div class="card err">❌ <b>NIEWYSTARCZAJĄCY MOMENT</b><br>{formula}<br>{avail}<br>'
            f'Brakuje: <b>{deficit:.2f} Nm</b> — wybierz silniki o wyższym Stall Torque.</div>',
            unsafe_allow_html=True)

    # ── 2. Wytrzymałość wału ───────────────────────────────────
    st.markdown('<div class="section">2. Wytrzymałość wału silnika</div>', unsafe_allow_html=True)
    if shaft_risk:
        st.markdown(
            f'<div class="card err">⚠️ <b>RYZYKO MECHANICZNEGO ŚCIĘCIA WAŁU</b><br>'
            f'Masa {total_mass_kg} kg &gt; 80 kg  AND  wał {motor["shaft_mm"]} mm &lt; 12 mm.<br>'
            f'Przy montażu bezpośrednim sił bocznych grozi ścięciem.<br>'
            f'Rozwiązanie: silnik z wałem ≥ 12 mm lub napęd łańcuchowy/pasowy.</div>',
            unsafe_allow_html=True)
    elif total_mass_kg > 80:
        st.markdown(
            f'<div class="card ok">✅ <b>WAŁ OK</b> — Masa {total_mass_kg} kg &gt; 80 kg, '
            f'ale wał {motor["shaft_mm"]} mm ≥ 12 mm. Montaż bezpośredni dopuszczalny.</div>',
            unsafe_allow_html=True)
    else:
        st.markdown(
            f'<div class="card ok">✅ <b>WAŁ OK</b> — Masa {total_mass_kg} kg ≤ 80 kg. '
            f'Wał {motor["shaft_mm"]} mm wystarczający.</div>',
            unsafe_allow_html=True)

    # ── 3. Kompatybilność napięciowa ───────────────────────────
    st.markdown('<div class="section">3. Kompatybilność napięciowa (akumulator = silnik)</div>', unsafe_allow_html=True)
    if voltage_ok:
        st.markdown(
            f'<div class="card ok">✅ <b>NAPIĘCIE OK</b> — '
            f'Akumulator {batt["voltage"]}V = Silnik {motor["voltage"]}V</div>',
            unsafe_allow_html=True)
    else:
        st.markdown(
            f'<div class="card err">❌ <b>NIEZGODNOŚĆ NAPIĘCIA</b> — '
            f'Akumulator {batt["voltage"]}V ≠ Silnik {motor["voltage"]}V.<br>'
            f'Konieczna przetwornica DC-DC lub zmiana komponentu.</div>',
            unsafe_allow_html=True)

    # ── 4. Sterownik ───────────────────────────────────────────
    st.markdown('<div class="section">4. Sterownik silników</div>', unsafe_allow_html=True)
    if not ctrl_voltage_ok:
        st.markdown(
            f'<div class="card err">❌ <b>NAPIĘCIE STEROWNIKA ZA NISKIE</b> — '
            f'Max {ctrl["voltage_max"]}V &lt; Akumulator {batt["voltage"]}V. '
            f'Ryzyko uszkodzenia!</div>',
            unsafe_allow_html=True)
    elif ctrl_current_ok:
        st.markdown(
            f'<div class="card ok">✅ <b>STEROWNIK OK</b> — '
            f'Peak silnika {motor["peak_current_a"]}A &lt; Max sterownika {ctrl["max_current_a"]}A.<br>'
            f'Interfejs: {ctrl["interface"]}  |  Max napięcie: {ctrl["voltage_max"]}V</div>',
            unsafe_allow_html=True)
    else:
        excess = motor["peak_current_a"] - ctrl["max_current_a"]
        st.markdown(
            f'<div class="card err">❌ <b>STEROWNIK ZA SŁABY</b> — '
            f'Peak silnika {motor["peak_current_a"]}A &gt; Max sterownika {ctrl["max_current_a"]}A.<br>'
            f'Przekroczenie o {excess:.0f}A — ryzyko przegrzania i spalenia.</div>',
            unsafe_allow_html=True)

    # ── 5. Bilans energetyczny ─────────────────────────────────
    st.markdown('<div class="section">5. Bilans energetyczny  t = C_ah / I_total</div>', unsafe_allow_html=True)
    ecls = "ok" if runtime_ok else "err"
    eicon = "✅" if runtime_ok else "❌"
    elabel = "WYSTARCZAJĄCY" if runtime_ok else "NIEWYSTARCZAJĄCY — BATERIA SIĘ WYCZERPIE"
    st.markdown(
        f'<div class="card {ecls}">{eicon} <b>CZAS PRACY — {elabel}</b><br>'
        f'Prąd silników (ciągły): {motor_cont_a:.1f} A  '
        f'({motor["cont_current_a"]} A × {qty})<br>'
        f'Prąd elektroniki + pompa: {extra_a:.1f} A  ({extra_w:.0f} W / {batt["voltage"]} V)<br>'
        f'Łączny pobór: <b>{total_a:.1f} A</b>  ({total_w:.0f} W)<br>'
        f'Czas pracy na baterii: <b>{runtime_h:.1f} h</b>  '
        f'({batt["capacity_ah"]} Ah / {total_a:.1f} A)<br>'
        f'Czas przejazdu całego pola: <b>{route_time_h:.2f} h</b>  '
        f'({total_route_m} m przy {v_kmh:.1f} km/h)</div>',
        unsafe_allow_html=True)

    # ── 6. Prędkość robota ─────────────────────────────────────
    st.markdown('<div class="section">6. Prędkość robota  V = (RPM · 2π · r) / 60</div>', unsafe_allow_html=True)
    scls = "ok" if 0.5 <= v_kmh <= 4.0 else "warn"
    sicon = "✅" if 0.5 <= v_kmh <= 4.0 else "⚠️"
    snote = ""
    if v_kmh > 4.0:
        snote = "<br>Za szybko jak na oprysk! Optymalne 1–3 km/h."
    elif v_kmh < 0.5:
        snote = "<br>Za wolno — sprawdź parametry silnika."
    st.markdown(
        f'<div class="card {scls}">{sicon} <b>Prędkość robocza: {v_kmh:.2f} km/h</b>{snote}<br>'
        f'RPM silnika: {motor["no_load_rpm"]}  |  Promień koła: {r_m*100:.1f} cm</div>',
        unsafe_allow_html=True)

    # ── 7. Pompa ───────────────────────────────────────────────
    if pump["voltage"] > 0:
        st.markdown('<div class="section">7. Moduł oprysku</div>', unsafe_allow_html=True)
        if pump_ok:
            extra_note = ""
            if pump["voltage"] < batt["voltage"]:
                extra_note = f" (przez przetwornicę {batt['voltage']}V → {pump['voltage']}V)"
            st.markdown(
                f'<div class="card ok">✅ <b>POMPA OK</b> — {pump_choice}<br>'
                f'Napięcie pompy: {pump["voltage"]}V{extra_note}<br>'
                f'Pobór: {pump["power_w"]}W  |  Dysze: {nozzle_count}</div>',
                unsafe_allow_html=True)
        else:
            st.markdown(
                f'<div class="card err">❌ <b>NIEZGODNOŚĆ NAPIĘCIA POMPY</b> — '
                f'Pompa {pump["voltage"]}V &gt; Akumulator {batt["voltage"]}V.</div>',
                unsafe_allow_html=True)

    # ── Podsumowanie ───────────────────────────────────────────
    st.markdown("---")
    checks = [torque_ok, not shaft_risk, voltage_ok,
              ctrl_current_ok, ctrl_voltage_ok, runtime_ok, pump_ok]
    passed = sum(checks)
    total  = len(checks)
    pct    = int(passed / total * 100)

    labels = [
        ("Moment obrotowy",         torque_ok),
        ("Wytrzymałość wału",        not shaft_risk),
        ("Napięcie silnik/bateria",  voltage_ok),
        ("Sterownik — prąd",        ctrl_current_ok),
        ("Sterownik — napięcie",    ctrl_voltage_ok),
        ("Bilans energetyczny",     runtime_ok),
        ("Napięcie pompy",          pump_ok),
    ]

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        for name, ok in labels[:4]:
            icon = "✅" if ok else "❌"
            st.markdown(f"{icon} {name}")
    with col_s2:
        for name, ok in labels[4:]:
            icon = "✅" if ok else "❌"
            st.markdown(f"{icon} {name}")

    st.markdown("")
    if pct == 100:
        st.success(f"✅ Wszystkie {total} sprawdzenia zaliczone ({pct}%). Konfiguracja gotowa!")
    elif pct >= 70:
        st.warning(f"⚠️ {passed}/{total} sprawdzeń OK ({pct}%). Popraw zaznaczone błędy.")
    else:
        st.error(f"❌ {passed}/{total} sprawdzeń OK ({pct}%). Konfiguracja wymaga korekty.")

    st.caption("Wzory: T=(m·g·f·r)·S  |  t=C/I  |  V=(RPM·2π·r)/60  |  S=2.0")
