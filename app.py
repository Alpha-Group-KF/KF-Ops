def load_flavor_cost_prices():
    """
    Attempts to read the unit cost prices from Assumptions sheet Column E (index 4).
    Falls back to FLAVORS config if unavailable.
    """
    try:
        ws = get_ws("Assumptions")
        values = ws.get_all_values()
        cost_map = {}
        for r in values:
            # Column A (index 0) = Flavor Name, Column E (index 4) = Cost Price / unit
            if len(r) >= 5 and r[0].strip() and any(c.isdigit() for c in r[4]):
                name = r[0].strip().lower()
                cost_map[name] = _num(r[4])
        costs = []
        for f in FLAVORS:
            name_lower = f[1].lower()
            if name_lower in cost_map and cost_map[name_lower] > 0:
                costs.append(cost_map[name_lower])
            else:
                costs.append(f[3])
        return costs
    except Exception:
        return [f[3] for f in FLAVORS]