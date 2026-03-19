import streamlit as st


def page_header(room):

    st.title("🏠 Smart Resource Efficiency Dashboard")
    st.subheader(f"Room: {str(room).title()}")


def device_controls(devices, room):

    device_states = {}

    cols = st.columns(3)

    for i, device in enumerate(devices):

        display_device = str(device).title()

        col = cols[i % 3]

        with col:

            st.markdown(f"### {display_device}")

            toggle = st.toggle(
                f"{display_device} ON/OFF",
                key=f"{room}_{device}_toggle"
            )

            power = st.number_input(
                f"{display_device} Power",
                0.0,
                3.0,
                0.5,
                key=f"{room}_{device}_power"
            )

            device_states[device] = (toggle, power)

    return device_states