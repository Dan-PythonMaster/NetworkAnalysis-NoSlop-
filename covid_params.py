"""The COVID-like parameter set, and where each value comes from.

These are the values of bt_sweep.BASE that covid_strategies.py and covid_animation.py
override; everything not named here keeps its baseline value. SOURCES is the justification
for each one, kept next to the numbers so the two cannot drift apart.

Nothing else about the model changes: there is still no latent period, no symptoms and no
variation in infectiousness between people. This is the same simulator with COVID-like
numbers, not a COVID model.
"""
DAY = 86400

COVID = {
    "rssi": -75,
    "room_rssi": -90,
    "room_dose": 0.8,
    "imm_lo": 150,
    "imm_hi": 1800,
    "period": 5 * DAY,
    "home_risk": 1.0,
    "home_dose": 500,
    "ring_delay": 3 * DAY,
    "ring_per_case": 10,
}

# What each value above rests on. Where a number was tuned rather than taken from a paper,
# the entry says so and names what it was tuned against.
SOURCES = {
    "close contact = within about 1.5 m":
        "Sekara & Lehmann, PLoS ONE 2014 (RSSI -75 dBm); CDC close-contact distance",
    "same room = detected at all, weaker signal":
        "RSSI -90 dBm, the bulk of Bluetooth detections",
    "infectious for about 5 days":
        "about 2 days before symptoms plus about 3 days after; "
        "Cevik et al., Lancet Microbe 2021",
    "resistance 2.5 to 30 hours of exposure":
        "tuned so that two nights of household exposure infect about half, in the range of "
        "the 42.7% household attack rate in Madewell et al., JAMA Netw Open 2022, and so "
        "that outbreaks neither always fizzle nor always reach everyone",
    "room exposure a sixth of close contact":
        "sharing a room counts 0.8 of the 5 minutes a close contact counts",
    "tracing delay 3 days":
        "Kretzschmar et al., Lancet Public Health 2020",
}
