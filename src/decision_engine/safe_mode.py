def trigger_safe_mode():
    """
    Trigger a safe fallback action.
    In SITL: just log.
    In real drone: send RTL / HOLD command.
    """

    # print("🚨 SAFE MODE ACTIVATED")  # Disabled for performance testing

    # Examples (only one would be active in real system):
    # send_flight_mode("RTL")
    # send_flight_mode("HOLD")