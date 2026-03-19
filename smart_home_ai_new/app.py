import streamlit as st
import pandas as pd
import random
import time
from firebase_admin import db
import plotly.express as px
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
from device_simulation import simulate_devices
from dashboard_ui import page_header, device_controls
from ai_model import predict_energy
from energy_service import save_energy, load_energy
from energy_forecast import forecast_energy
from anomaly_detection import detect_anomalies

st_autorefresh(interval=3000, key="device_refresh")
st.set_page_config(page_title="Smart Home AI", layout="wide")

# ---------------- UI STYLE ----------------

st.markdown("""
<style>

.stApp{
background:linear-gradient(135deg,#0f172a,#020617);
color:white;
}

section[data-testid="stSidebar"]{
background:rgba(15,23,42,0.9);
}

button{
color:white !important;
background:#3b82f6 !important;
}

.kpi-card{
padding:25px;
border-radius:20px;
background:linear-gradient(135deg,#6366f1,#3b82f6);
color:white;
text-align:center;
animation:fadeIn 0.6s ease;
transition:all .3s;
}

/* Glass chart cards */

.chart-card{
background: rgba(255,255,255,0.05);
border-radius:16px;
padding:20px;
border:1px solid rgba(255,255,255,0.12);
backdrop-filter: blur(12px);
box-shadow:0 10px 25px rgba(0,0,0,0.35);
margin-bottom:20px;
}
            
.chart-card:hover{
transform: translateY(-2px);
transition: 0.2s;
}            
                        
.kpi-card:hover{
transform:translateY(-6px) scale(1.03);
}

@keyframes fadeIn{
from{opacity:0; transform:translateY(10px);}
to{opacity:1; transform:translateY(0);}
}

.kpi-title{
font-size:16px;
opacity:0.9;
}

.kpi-value{
font-size:36px;
font-weight:700;
}

</style>
""", unsafe_allow_html=True)

# ---------------- NAVIGATION ----------------

st.sidebar.title("🏠 Smart Home AI")

page = st.sidebar.radio(
"Navigation",
["Master Dashboard","Dashboard","Room Analytics","AI Insights"]
)

# ---------------- ROOM MANAGEMENT ----------------

DEFAULT_DEVICES = ["Light", "Fan", "AC"]
DEVICE_POWER_PROFILE = {
    "light": 0.12,
    "fan": 0.22,
    "ac": 1.4,
    "tv": 0.18,
    "heater": 1.2,
}


def normalize_device_name(value):
    text = str(value).strip()
    upper = text.upper()
    if upper in {"AC", "TV"}:
        return upper
    return text.title()

def to_title_name(value):
    return normalize_device_name(value)


def normalize_rooms_devices(rooms, devices):
    normalized_rooms = []
    normalized_devices = {}

    for room in rooms:
        room_name = to_title_name(room)
        normalized_rooms.append(room_name)

    for room, room_devices in devices.items():
        room_name = to_title_name(room)
        normalized_devices[room_name] = [normalize_device_name(device) for device in room_devices]

    normalized_rooms = list(dict.fromkeys(normalized_rooms))
    return normalized_rooms, normalized_devices


def estimate_device_power(room_name, device_name, is_on):
    if not bool(is_on):
        return 0.0

    normalized_device = normalize_device_name(device_name)
    safe_room = room_name.replace(" ", "_")

    room_power_key = f"{room_name}_{normalized_device}_power"
    safe_power_key = f"{safe_room}_{normalized_device}_power"

    if room_power_key in st.session_state:
        return float(st.session_state.get(room_power_key, 0) or 0)

    if safe_power_key in st.session_state:
        return float(st.session_state.get(safe_power_key, 0) or 0)

    return float(DEVICE_POWER_PROFILE.get(str(device_name).strip().lower(), 0.2))


def build_realtime_room_energy_df():
    rooms_data = db.reference("rooms").get() or {}
    room_energy = {}

    for room_name, info in rooms_data.items():
        display_room = to_title_name(room_name)
        devices_state = (info or {}).get("devices", {}) or {}

        total = 0.0
        for device_name, is_on in devices_state.items():
            total += estimate_device_power(display_room, device_name, is_on)

        room_energy[display_room] = round(total, 3)

    for room_name in st.session_state.get("rooms", []):
        room_energy.setdefault(to_title_name(room_name), 0.0)

    if not room_energy:
        return pd.DataFrame(columns=["Room", "Energy"])

    return pd.DataFrame(
        {
            "Room": list(room_energy.keys()),
            "Energy": list(room_energy.values()),
        }
    )

# 🔥 LOAD ROOMS + DEVICES FROM FIREBASE
def load_rooms_and_devices():
    try:
        data = db.reference("rooms").get()

        if data:
            rooms = list(data.keys())

            devices = {}
            for room, info in data.items():
                device_dict = info.get("devices", {})
                normalized = {
                    str(device).strip().lower(): bool(state)
                    for device, state in device_dict.items()
                }

                missing_defaults = [
                    default.lower()
                    for default in DEFAULT_DEVICES
                    if default.lower() not in normalized
                ]

                if missing_defaults:
                    for missing in missing_defaults:
                        normalized[missing] = False
                    db.reference(f"rooms/{room}/devices").update(
                        {missing: False for missing in missing_defaults}
                    )

                devices[room] = [normalize_device_name(device) for device in normalized.keys()]

            return rooms, devices

        else:
            return ["Living Room","Bedroom","Kitchen"], {
                "Living Room": DEFAULT_DEVICES.copy(),
                "Bedroom": DEFAULT_DEVICES.copy(),
                "Kitchen": DEFAULT_DEVICES.copy()
            }

    except:
        return ["Living Room","Bedroom","Kitchen"], {
            "Living Room": DEFAULT_DEVICES.copy(),
            "Bedroom": DEFAULT_DEVICES.copy(),
            "Kitchen": DEFAULT_DEVICES.copy()
        }


# ✅ ALWAYS LOAD FROM FIREBASE
rooms, devices = load_rooms_and_devices()
rooms, devices = normalize_rooms_devices(rooms, devices)

# OPTIONAL: keep session_state for compatibility
st.session_state.rooms = rooms
st.session_state.devices = devices

st.sidebar.markdown("### Add Room")

new_room = st.sidebar.text_input("Room Name")

if st.sidebar.button("Add Room"):
    room_name = to_title_name(new_room)
    existing_rooms = {r.lower() for r in st.session_state.rooms}

    if room_name and room_name.lower() not in existing_rooms:

        st.session_state.rooms.append(room_name)

        # ✅ Add default devices
        st.session_state.devices[room_name] = DEFAULT_DEVICES.copy()

        db.reference(f"rooms/{room_name}").set({
            "devices": {
                "light": False,
                "fan": False,
                "ac": False
            }
        })

        # ✅ Initialize power values
        for device in DEFAULT_DEVICES:

            power_key = f"{room_name}_{device}_power"

            if device.lower() == "light":
                st.session_state[power_key] = random.uniform(0.05,0.12)

            elif device.lower() == "fan":
                st.session_state[power_key] = random.uniform(0.1,0.25)

            elif device.lower() == "ac":
                st.session_state[power_key] = random.uniform(1.0,1.6)

st.sidebar.markdown("### Remove Room")

remove_room = st.sidebar.selectbox(
"Select Room",
st.session_state.rooms,
format_func=to_title_name
)

if st.sidebar.button("Delete Room"):
    st.session_state.rooms.remove(remove_room)
    if remove_room in st.session_state.devices:
        del st.session_state.devices[remove_room]
    db.reference(f"rooms/{remove_room}").delete()
    st.rerun()

room = st.sidebar.selectbox(
"Active Room",
st.session_state.rooms,
format_func=to_title_name
)

# ---------------- DEVICE MANAGEMENT ----------------

st.sidebar.markdown("### Device Manager")

new_device = st.sidebar.selectbox(
    "Add Device",
    ["Light","Fan","AC","TV","Heater"]
)

if st.sidebar.button("Add Device"):

    if new_device:

        new_device = normalize_device_name(new_device)

        st.session_state.devices[room].append(new_device)
        db.reference(f"rooms/{room}/devices/{new_device.lower()}").set(False)

        # initialize power for new device
        power_key = f"{room}_{new_device}_power"

        if power_key not in st.session_state:

            if new_device.lower() == "light":
                st.session_state[power_key] = random.uniform(0.05,0.12)

            elif new_device.lower() == "fan":
                st.session_state[power_key] = random.uniform(0.1,0.25)

            elif new_device.lower() == "ac":
                st.session_state[power_key] = random.uniform(1.0,1.6)

            else:
                st.session_state[power_key] = random.uniform(0.05,0.3)

remove_device = st.sidebar.selectbox(
"Remove Device",
st.session_state.devices[room],
format_func=to_title_name
)

if st.sidebar.button("Remove Device"):
    st.session_state.devices[room].remove(remove_device)
    db.reference(f"rooms/{room}/devices/{remove_device.lower()}").delete()


st.sidebar.markdown("### ⚡ Energy Usage Limit")

energy_limit = st.sidebar.slider(
    "Set Energy Limit (kWh)",
    min_value=0.5,
    max_value=100.0,
    value=30.0,
    step=0.1
)

st.session_state.energy_limit = energy_limit

# ---------------- LOAD DATA ----------------

data = load_energy()

if data is not None and not data.empty:

    # remove duplicate columns
    data = data.loc[:, ~data.columns.duplicated()]

    # clean column names
    data.columns = data.columns.str.strip().str.capitalize()

    # ensure Energy column is single numeric column
    if "Energy" in data.columns:

        if isinstance(data["Energy"], pd.DataFrame):
            data["Energy"] = data["Energy"].iloc[:,0]

        data["Energy"] = pd.to_numeric(data["Energy"], errors="coerce")

# =================================================
# MASTER DASHBOARD
# =================================================

if page == "Master Dashboard":

    st_autorefresh(interval=5000, key="dashboard_refresh")

    st.title("🏠 Smart Home Energy Platform")

# ---------------- ROOM ENERGY CALCULATION ----------------
    room_df = build_realtime_room_energy_df()

    if room_df.empty:
        room_df = pd.DataFrame({
            "Room": st.session_state.rooms,
            "Energy": [0] * len(st.session_state.rooms)
        })

    total_energy = round(room_df["Energy"].sum(), 2)

    # -------- ENERGY LIMIT ALERT --------

    avg_energy = data["Energy"].mean() if data is not None and not data.empty else 1

    limit = st.session_state.get("energy_limit", avg_energy * 1.5)

    if "energy_alert_triggered" not in st.session_state:
        st.session_state.energy_alert_triggered = False


    if total_energy > limit:

        # dashboard warning
        st.error(
            f"⚠ Energy usage exceeded limit!\n\n"
            f"Current: {total_energy} kWh | Limit: {limit} kWh"
        )

        # popup alert
        if not st.session_state.energy_alert_triggered:

            st.toast(
                f"🚨 Energy limit exceeded! {total_energy} kWh",
                icon="⚡"
            )

            st.session_state.energy_alert_triggered = True


        # -------- AUTOMATIC DEVICE SHUTDOWN --------

        priority = ["ac","fan","light"]

        for device_type in priority:

            for r in st.session_state.rooms:

                devices = st.session_state.devices.get(r, [])

                for device in devices:

                    key = f"{r}_{device}_power"

                    if device.lower() == device_type and st.session_state.get(key,0) > 0:

                        st.session_state[key] = 0

                        st.warning(
                            f"⚡ {device} in {r} turned OFF automatically "
                            f"to reduce energy usage"
                        )

                        break

    else:

        st.session_state.energy_alert_triggered = False

    # ---------------- KPI CARDS ----------------

    col1,col2,col3,col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="kpi-card">
        <div class="kpi-title">⚡ Total Energy</div>
        <div class="kpi-value">{total_energy} kWh</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="kpi-card">
        <div class="kpi-title">🏠 Active Rooms</div>
        <div class="kpi-value">{len(room_df)}</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:

        if total_energy > 0:
            highest = room_df.sort_values(
                "Energy",
                ascending=False
            )["Room"].iloc[0]
        else:
            highest = "None"

        st.markdown(f"""
        <div class="kpi-card">
        <div class="kpi-title">🔥 Highest Usage</div>
        <div class="kpi-value">{highest}</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:

        avg = round(room_df["Energy"].mean(),2)

        st.markdown(f"""
        <div class="kpi-card">
        <div class="kpi-title">📊 Avg Energy</div>
        <div class="kpi-value">{avg}</div>
        </div>
        """, unsafe_allow_html=True)

    # =================================================
    # CHART GRID
    # =================================================

    col1, col2 = st.columns(2)

    # -------- Chart 1 : Energy by Room --------

    with col1:

        st.subheader("⚡ Energy by Room")

        fig = px.bar(
            room_df,
            x="Room",
            y="Energy",
            color="Energy",
            text="Energy",
            labels={
                "Room": "Room",
                "Energy": "Energy Consumption (kWh)"
            }
        )

        fig.update_layout(
            height=350,
            template="plotly_dark",
            margin=dict(l=20, r=20, t=40, b=20),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)"
        )

        fig.update_traces(textposition="outside")

        st.plotly_chart(
            fig,
            use_container_width=True,
            key="energy_by_room_chart"
        )

    # -------- Chart 2 : Energy Distribution --------

    with col2:

        st.subheader("🥧 Energy Distribution")

        fig = px.pie(
            room_df,
            names="Room",
            values="Energy",
            hole=0.45
        )

        fig.update_layout(
            height=350,
            template="plotly_dark",
            margin=dict(l=20, r=20, t=40, b=20),
            paper_bgcolor="rgba(0,0,0,0)"
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
            key="energy_distribution_pie"
        )


    col3, col4 = st.columns(2)

    # -------- Chart 3 : Energy Ranking --------

    with col3:

        st.subheader("🏆 Energy Ranking")

        sorted_df = room_df.sort_values(
            "Energy",
            ascending=False
        )

        fig = px.bar(
            sorted_df,
            x="Room",
            y="Energy",
            color="Energy",
            text="Energy",
            labels={
                "Room":"Room",
                "Energy":"Energy Consumption (kWh)"
            }
        )

        fig.update_layout(
            height=350,
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=20, r=20, t=40, b=20)
        )

        fig.update_traces(textposition="outside")

        st.plotly_chart(fig,use_container_width=True, key="energy_ranking_chart")


    # -------- Chart 4 : Dashboard Heatmap --------

    with col4:

        st.subheader("🔥 Energy Heatmap")

        heatmap_data = pd.DataFrame(
            [room_df["Energy"].values],
            columns=room_df["Room"]
        )

        fig = px.imshow(
            heatmap_data,
            labels=dict(
                x="Room",
                y="",
                color="Energy (kWh)"
            ),
            color_continuous_scale="reds"
        )

        fig.update_layout(
            height=350,
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)"
        )

        st.plotly_chart(fig,use_container_width=True, key="energy_heatmap_chart")

    # =================================================
    # ROW 3 : TREND + FORECAST
    # =================================================

    col5, col6 = st.columns(2)

    # -------- Chart 5 : Daily Energy Trend --------

    with col5:

        st.subheader("📈 Daily Energy Trend")

        if data is not None and not data.empty:

            trend_df = data.copy()

            # Use real timestamp if available
            if "Timestamp" in trend_df.columns:

                trend_df["Timestamp"] = pd.to_datetime(
                    trend_df["Timestamp"],
                    errors="coerce"
                )

            # fallback timeline
            else:
                trend_df["Timestamp"] = range(len(trend_df))

            fig = px.line(
                trend_df,
                x="Timestamp",
                y="Energy",
                markers=True,
                labels={
                    "Timestamp": "Time",
                    "Energy": "Energy (kWh)"
                }
            )

            fig.update_layout(
                height=350,
                template="plotly_dark",
                margin=dict(l=20,r=20,t=40,b=20),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)"
            )

            st.plotly_chart(fig, use_container_width=True)

        else:
            st.info("No historical energy data available.")



    # -------- Chart 6 : AI Energy Forecast --------

    with col6:

        st.subheader("🔮 AI Energy Forecast")

        if data is not None and not data.empty:

            try:

                clean_data = data.dropna(subset=["Energy"])

                forecast_df = forecast_energy(clean_data)

                if forecast_df is not None and not forecast_df.empty:

                    # Ensure required columns exist
                    if "Time" not in forecast_df.columns:

                        # create fallback timeline
                        forecast_df["Time"] = range(len(forecast_df))

                    fig = px.line(
                        forecast_df,
                        x="Time",
                        y="Energy",
                        markers=True,
                        labels={
                            "Time": "Future Time",
                            "Energy": "Predicted Energy (kWh)"
                        }
                    )

                    fig.update_layout(
                        height=350,
                        template="plotly_dark",
                        margin=dict(l=20,r=20,t=40,b=20),
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)"
                    )

                    st.plotly_chart(fig, use_container_width=True)

                else:
                    st.warning("Forecast data not available.")

            except Exception as e:
                st.error(f"Forecast error: {e}")

        else:
            st.info("Not enough historical data to generate forecast.")


# =================================================
# ROOM DASHBOARD
# =================================================

if page == "Dashboard":


    st_autorefresh(interval=2000, key="refresh_dashboard")

    page_header(room)

    devices = st.session_state.devices.get(room, [])

    # 🔥 GET REAL DEVICE STATES FROM FIREBASE
    firebase_data = db.reference("rooms").get() or {}

    # 🔥 REAL-TIME FIREBASE DEVICE CONTROL
    st.subheader("🎛 Device Control")

    current_room_states = firebase_data.get(room, {}).get("devices", {})
    ui_device_states = {}

    if devices:
        device_columns = st.columns(len(devices))
        for idx, device in enumerate(devices):
            firebase_key = device.lower()
            current_state = bool(current_room_states.get(firebase_key, False))

            with device_columns[idx]:
                new_state = st.toggle(
                    f"{device}",
                    value=current_state,
                    key=f"firebase_toggle_{room}_{device}"
                )

            ui_device_states[firebase_key] = bool(new_state)

            if new_state != current_state:
                db.reference(f"rooms/{room}/devices/{firebase_key}").set(bool(new_state))

    l = int(ui_device_states.get("light", False))
    f = int(ui_device_states.get("fan", False))
    a = int(ui_device_states.get("ac", False))

    energy = predict_energy(l, f, a)

    st.metric("Predicted Energy Usage",f"{energy} kWh")

    simulate_devices(room, devices)

    for device in devices:

        safe_room = room.replace(" ", "_")

        widget_key = f"{safe_room}_{device}_power"
        sim_key = f"{widget_key}_sim"

        if random.random() < 0.3:

            if device.lower() == "light":
                st.session_state[sim_key] = random.uniform(0.05, 0.15)

            elif device.lower() == "fan":
                st.session_state[sim_key] = random.uniform(0.08, 0.25)

            elif device.lower() == "ac":
                st.session_state[sim_key] = random.uniform(0.8, 1.5)

        else:
            st.session_state[sim_key] = 0

    # -------- AUTO SAVE ENERGY TO FIREBASE --------

    if "last_save_time" not in st.session_state:
        st.session_state.last_save_time = time.time()

    current_time = time.time()

    if current_time - st.session_state.last_save_time > 10:
        save_energy(room, energy)
        st.session_state.last_save_time = current_time

    if st.button("Save Energy Data"):
        save_energy(room,energy)
        st.success("Energy saved to Firebase")

    # -------- LIVE MONITORING --------

    st.subheader("⚡ Live Energy Monitoring")

    if "monitoring" not in st.session_state:
        st.session_state.monitoring = False

    if "live_energy" not in st.session_state:
        st.session_state.live_energy = []

    col1,col2 = st.columns(2)

    with col1:
        if st.button("▶ Start Monitoring"):
            st.session_state.monitoring = True

    with col2:
        if st.button("⏹ Stop Monitoring"):
            st.session_state.monitoring = False

    if st.session_state.monitoring:
        st_autorefresh(interval=1000, key="energyrefresh")

        simulate_devices(room, devices)

        simulated = energy + random.uniform(-0.15,0.15)

        st.session_state.live_energy.append(simulated)

    if st.session_state.live_energy:

        df = pd.DataFrame({
            "Time":range(len(st.session_state.live_energy)),
            "Energy":st.session_state.live_energy
        })

        with st.container(border=True):

            fig = px.line(
                df,
                x="Time",
                y="Energy",
                markers=True,
                labels={"Energy":"Energy (kWh)"}
            )

            fig.update_layout(height=350)

            st.plotly_chart(fig,use_container_width=True)

            st.metric(
            "⚡ Current Energy Usage",
            f"{st.session_state.live_energy[-1]:.2f} kWh"
            )

# =================================================
# ROOM ANALYTICS
# =================================================

if page == "Room Analytics":

    st.title("📊 Room Energy Analytics")

    # -------- Calculate Room Energy --------

    df = build_realtime_room_energy_df()

    if df.empty:
        st.warning("No energy data available yet.")

    col1, col2 = st.columns(2)

    # -------- Chart 1 --------
    with col1:


        st.subheader("⚡ Energy by Room")

        fig = px.bar(
            df,
            x="Room",
            y="Energy",
            color="Energy",
            text="Energy"
        )

        fig.update_layout(
            height=350,
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)"
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
            key="analytics_energy_bar"
        )


    # -------- Chart 2 --------
    with col2:

        st.subheader("🥧 Energy Distribution")

        fig = px.pie(
            df,
            names="Room",
            values="Energy",
            hole=0.45
        )

        fig.update_layout(
            height=350,
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)"
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
            key="analytics_energy_pie"
        )


    col3, col4 = st.columns(2)

    # -------- Chart 3 --------
    with col3:

        st.subheader("🏆 Energy Ranking")

        sorted_df = df.sort_values("Energy", ascending=False)

        fig = px.bar(
            sorted_df,
            x="Room",
            y="Energy",
            color="Energy",
            text="Energy"
        )

        fig.update_layout(
            height=350,
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)"
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
            key="analytics_energy_rank"
        )


    # -------- Chart 4 --------
    with col4:

        st.subheader("🔥 Energy Heatmap")

        heatmap_data = pd.DataFrame(
            [df["Energy"].values],
            columns=df["Room"]
        )

        fig = px.imshow(
            heatmap_data,
            color_continuous_scale="reds",
            labels=dict(x="Room", color="Energy (kWh)")
        )

        fig.update_layout(
            height=350,
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)"
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
            key="analytics_energy_heatmap"
        )

# =================================================
# AI INSIGHTS
# =================================================

if page == "AI Insights":

    st.title("🧠 AI Energy Insights")

    l = st.session_state.get(f"{room}_Light_power",0)
    f = st.session_state.get(f"{room}_Fan_power",0)
    a = st.session_state.get(f"{room}_AC_power",0)

    energy = predict_energy(int(l>0),int(f>0),int(a>0))

    # calculate historical average safely
    if data is not None and not data.empty and "Energy" in data.columns:

        avg_energy = float(pd.to_numeric(data["Energy"], errors="coerce").mean())

        if avg_energy == 0 or pd.isna(avg_energy):
            avg_energy = 1.0

    else:
        avg_energy = 1.0


    efficiency_score = max(
        0,
        min(
            100,
            round(100 - (energy / avg_energy) * 50)
        )
    )

    st.subheader("⚡ Energy Efficiency Score")

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=efficiency_score,
        title={"text": "Efficiency (%)"},
        gauge={
            "axis": {"range": [0,100]},
            "bar": {"color": "#22c55e"},
            "steps":[
                {"range":[0,40],"color":"#ef4444"},
                {"range":[40,70],"color":"#f59e0b"},
                {"range":[70,100],"color":"#22c55e"}
            ]
        }
    ))

    fig.update_layout(
        height=250,
        template="plotly_dark",
        margin=dict(l=20,r=20,t=40,b=20),
        paper_bgcolor="rgba(0,0,0,0)"
    )

    st.plotly_chart(fig,use_container_width=True)


    st.subheader("💡 AI Recommendations")

    suggestions=[]

    # -------- HISTORICAL ENERGY ANALYSIS --------

    if not data.empty:

        avg_energy = data["Energy"].mean()

        if energy > avg_energy * 1.3:
            suggestions.append("Energy usage higher than historical average")

        if energy < avg_energy * 0.5:
            suggestions.append("Energy usage unusually low")

    if a>0:
        suggestions.append("Reduce AC temperature or enable eco mode")

    if f>0:
        suggestions.append("Use fan instead of AC when possible")

    if l>0:
        suggestions.append("Turn off lights when room is empty")

    if energy>1.2:
        suggestions.append("High energy usage detected")

    if suggestions:
        for s in suggestions:
            st.write("•",s)
    else:
        st.success("Energy usage is optimal")


    st.subheader("🚨 Energy Anomaly Detection")

    anomaly_df = detect_anomalies(data) 

    if anomaly_df is not None and not anomaly_df.empty:

        # choose x axis safely
        x_axis = "Timestamp" if "Timestamp" in anomaly_df.columns else anomaly_df.index

        fig = px.scatter(
            anomaly_df,
            x=x_axis,
            y="Energy",
            color="anomaly",
            labels={
                "Energy": "Energy Usage (kWh)",
                "anomaly": "Status"
            }
        )

        fig.update_layout(
            height=350,
            template="plotly_dark",
            margin=dict(l=20,r=20,t=40,b=20),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)"
        )

        st.plotly_chart(fig,use_container_width=True)

    else:
        st.info("No anomaly data available.")
