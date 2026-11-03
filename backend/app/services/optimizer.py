"""CP-SAT local, políticas tipadas e verificação independente da solução numérica."""
from collections import Counter, defaultdict
from datetime import UTC, date, datetime, time, timedelta
from time import monotonic
from zoneinfo import ZoneInfo
from app.services.capacity import civil, merge
from app.services.labor_rules import clipped_total, minutes, overlap, segments


class ModelLimit(ValueError):
    pass


def dt(value):
    return datetime.fromisoformat(value)


def midnight(day, tz):
    return datetime.combine(day, time.min, tz).astimezone(UTC)


def rule_span(rule, facts, tz):
    left, right = dt(rule["valid_from"]), dt(rule["valid_until"])
    successors = [r for r in facts["labor_rules"] if r["supersedes_id"] == rule["id"]]
    if successors:
        right = min(right, min(dt(r["valid_from"]) for r in successors))
    if rule["contract_id"]:
        contract = next((c for c in facts["contracts"] if c["id"] == rule["contract_id"]), None)
        if contract is None:
            return left, left
        left = max(left, midnight(date.fromisoformat(contract["valid_from"]), tz))
        if contract["valid_until"]:
            right = min(right, midnight(date.fromisoformat(contract["valid_until"]), tz))
    return left, right


def rules_for(snapshot, person, start, end, kind=None, unit_id=None):
    facts = snapshot["facts"]
    tz = ZoneInfo(snapshot["timezone"])
    own_contracts = {c["id"] for c in facts["contracts"] if c["employee_id"] == person["id"]}
    result = []
    for rule in facts["labor_rules"]:
        a, b = rule_span(rule, facts, tz)
        if a >= b or not overlap(a, b, start, end) or kind and rule["kind"] != kind:
            continue
        if rule["unit_id"] and rule["unit_id"] != (unit_id or snapshot["scenario"]["unit_id"]):
            continue
        if rule["job_role_id"] and rule["job_role_id"] != person["job_role_id"]:
            continue
        if rule["contract_id"] and rule["contract_id"] not in own_contracts:
            continue
        result.append(rule)
    return result


def contract_at(facts, person, day):
    values = [c for c in facts["contracts"] if c["employee_id"] == person["id"] and date.fromisoformat(c["valid_from"]) <= day and
              (not c["valid_until"] or day < date.fromisoformat(c["valid_until"]))]
    return values[0] if len(values) == 1 else None


def required_rest(snapshot, person, start, end, unit_id=None):
    return max([snapshot["options"]["limits"]["min_rest_minutes"], *[r["minutes"] for r in rules_for(snapshot, person, start, end, "min_rest", unit_id)]])


def cap_limit(snapshot, person, start, end, kind):
    fallback = snapshot["options"]["limits"]["max_daily_minutes" if kind == "max_daily" else "max_weekly_minutes"]
    values = [fallback, *[r["minutes"] for r in rules_for(snapshot, person, start, end, kind)]]
    if kind == "max_weekly":
        tz = ZoneInfo(snapshot["timezone"])
        day = start.astimezone(tz).date()
        while midnight(day, tz) < end:
            contract = contract_at(snapshot["facts"], person, day)
            if contract:
                values.append(contract["weekly_minutes"])
            day += timedelta(days=1)
        target = snapshot["scenario"]["inputs"].get("target_weekly_minutes")
        if target:
            values.append(target)
    return min(values)


def weekly_rest(snapshot, person, start, end):
    return max([snapshot["options"]["limits"]["min_weekly_rest_minutes"], *[r["minutes"] for r in rules_for(snapshot, person, start, end, "min_weekly_rest")]])


def qualify(snapshot, person, candidate):
    facts, options = snapshot["facts"], snapshot["options"]
    if person["status"] != "active" or person["unit_id"] != snapshot["scenario"]["unit_id"]:
        return "inactive_or_outside_unit"
    demand = snapshot["scenario"]["inputs"]["demands"][candidate["activity"]]
    role_ids = options["activity_job_role_ids"].get(str(candidate["activity"]), [])
    if role_ids and person["job_role_id"] not in role_ids:
        return "role_not_authorized"
    if not options["allow_cross_department"] and person["department_id"] != demand["department_id"]:
        return "department_not_authorized"
    if options["allow_cross_department"] and not role_ids:
        return "substitution_roles_unspecified"
    skills = {s["skill_id"] for s in facts["employee_skills"] if s["employee_id"] == person["id"]}
    required_skills = set(demand["skill_ids"]) | {s["skill_id"] for s in facts["role_skills"] if s["job_role_id"] == person["job_role_id"]}
    if required_skills - skills:
        return "skill_missing"
    required_quals = set(demand["qualification_ids"]) | {q["qualification_id"] for q in facts["role_qualifications"] if q["job_role_id"] == person["job_role_id"]}
    tz = ZoneInfo(snapshot["timezone"])
    first, last = candidate["start"].astimezone(tz).date(), (candidate["end"] - timedelta(microseconds=1)).astimezone(tz).date()
    for ident in required_quals:
        values = [q for q in facts["employee_qualifications"] if q["employee_id"] == person["id"] and q["qualification_id"] == ident and
                  date.fromisoformat(q["valid_from"]) <= first and date.fromisoformat(q["valid_until"]) > last]
        if not any(options["eligibility"] == "hypothesis" or q["verification_status"] == "validated" for q in values):
            return "qualification_missing_expired_or_unverified"
    day, shift_contracts = first, set()
    while day <= last:
        contract = contract_at(facts, person, day)
        if contract is None:
            return "contract_missing_or_ambiguous"
        shift_contracts.add(contract["id"])
        if len(shift_contracts) > 1:
            return "contract_transition_within_shift"
        pattern = next(p for p in facts["work_patterns"] if p["id"] == contract["work_pattern_id"])
        config = pattern["configuration"]
        anchor = options["cycle_anchors"].get(pattern["id"])
        if not anchor and snapshot["scenario"]["inputs"].get("work_pattern_id") == pattern["id"]:
            anchor = snapshot["scenario"]["inputs"].get("cycle_anchor")
        if config.get("cycle") and anchor and day == first:
            if config["cycle"][(first - date.fromisoformat(anchor)).days % len(config["cycle"])] != "work" or minutes(candidate["start"], candidate["end"]) != config["shift_minutes"]:
                return "cycle_restriction"
        day += timedelta(days=1)
    for absence in facts["availability_rules"]:
        if absence["employee_id"] == person["id"] and absence["type"] == "unavailable" and overlap(candidate["start"], candidate["end"], dt(absence["start_at"]), dt(absence["end_at"])):
            return "unavailable"
    work_minutes = sum(minutes(a, b) for a, b in candidate["work"])
    pause = max([minutes(dt(p["start_at"]), dt(p["end_at"])) for p in candidate["breaks"]] or [0])
    criteria = [(options["limits"]["break_threshold_minutes"], options["limits"]["min_break_minutes"])]
    criteria += [(r["threshold_minutes"], r["minutes"]) for r in rules_for(snapshot, person, candidate["start"], candidate["end"], "min_break")]
    if any(work_minutes > threshold and pause < minimum for threshold, minimum in criteria):
        return "insufficient_break"
    for fixed in snapshot["fixed"].get(person["id"], []):
        if incompatible(snapshot, person, candidate, fixed):
            return "historical_commitment_or_rest"
    return None


def incompatible(snapshot, person, a, b):
    if overlap(a["start"], a["end"], b["start"], b["end"]):
        return True
    earlier, later = (a, b) if a["end"] <= b["start"] else (b, a)
    rest = max(required_rest(snapshot, person, earlier["start"], later["end"], unit) for unit in {earlier["unit_id"], later["unit_id"]})
    if earlier["unit_id"] != later["unit_id"]:
        rest += snapshot["options"]["cross_unit_travel_minutes"]
    return minutes(earlier["end"], later["start"]) < rest


def prepare(snapshot):
    facts, options = snapshot["facts"], snapshot["options"]
    unit = next(u for u in facts["units"] if u["id"] == snapshot["scenario"]["unit_id"])
    snapshot["timezone"] = unit["timezone"]
    tz = ZoneInfo(unit["timezone"])
    begin, end = midnight(date.fromisoformat(options["start_date"]), tz), midnight(date.fromisoformat(options["end_date"]), tz)
    fixed = defaultdict(list)
    for row in facts["calendar_shifts"]:
        if row["state"] == "draft":
            fixed[row["employee_id"]].append({"start": dt(row["start_at"]), "end": dt(row["end_at"]), "work": segments(dt(row["start_at"]), dt(row["end_at"]), row["breaks"]), "unit_id": row["unit_id"]})
    for schedule in facts["approved_schedules"]:
        if schedule["id"] == options["parent_schedule_id"]:
            continue
        for row in schedule["assignments"]:
            fixed[row["employee_id"]].append({"start": dt(row["start_at"]), "end": dt(row["end_at"]), "work": segments(dt(row["start_at"]), dt(row["end_at"]), row["breaks"]), "unit_id": schedule["unit_id"]})
    snapshot["fixed"] = dict(fixed)
    candidates, reasons, examined = [], Counter(), 0
    demands = snapshot["scenario"]["inputs"]["demands"]
    if not demands:
        raise ModelLimit("NO_DEMAND")
    day = options_first = date.fromisoformat(options["start_date"]) - timedelta(days=1)
    while midnight(day, tz) < end:
        for template_index, template in enumerate(options["templates"]):
            if day.weekday() not in template["weekdays"]:
                continue
            start = civil(day, template["start_time"], tz)
            finish = start + timedelta(minutes=template["duration_minutes"])
            if not overlap(start, finish, begin, end):
                continue
            pauses = []
            if template["break_minutes"]:
                a = start + timedelta(minutes=template["break_after_minutes"])
                pauses = [{"start_at": a.isoformat(), "end_at": (a + timedelta(minutes=template["break_minutes"])).isoformat(), "paid": template["break_paid"]}]
            work = segments(start, finish, pauses)
            for activity, demand in enumerate(demands):
                for person in facts["employees"]:
                    examined += 1
                    if examined > 500000:
                        raise ModelLimit("CANDIDATE_SEARCH_LIMIT")
                    candidate = {"employee_id": person["id"], "activity": activity, "department_id": demand["department_id"], "unit_id": unit["id"],
                        "template": template_index, "start": start, "end": finish, "breaks": pauses, "work": work, "cost_cents": template["cost_cents"]}
                    reason = qualify(snapshot, person, candidate)
                    if reason:
                        reasons[reason] += 1
                    else:
                        preference = person["preferences"]
                        shift_name = "day" if 6 <= start.astimezone(tz).hour < 18 else "night"
                        candidate["penalty"] = int(preference.get("preferred_shift", shift_name) != shift_name) + int(day.weekday() in preference.get("preferred_days_off", []))
                        candidate["id"] = len(candidates)
                        candidates.append(candidate)
                        if len(candidates) > 25000:
                            raise ModelLimit("VARIABLE_LIMIT")
        day += timedelta(days=1)
    cells = []
    for activity, demand in enumerate(demands):
        windows, day = [], options_first
        while midnight(day, tz) < end:
            if day.weekday() in demand["weekdays"]:
                a = civil(day, demand["start_time"], tz)
                b = a + timedelta(minutes=demand["duration_minutes"])
                if overlap(a, b, begin, end):
                    windows.append((max(a, begin), min(b, end), demand["required_staff"], 1))
            day += timedelta(days=1)
        for window in options["coverage_windows"]:
            if window["activity_index"] == activity and overlap(dt(window["start_at"]), dt(window["end_at"]), begin, end):
                windows.append((max(dt(window["start_at"]), begin), min(dt(window["end_at"]), end), window["required_staff"], window["priority"]))
        points = {begin, end, *[p for a, b, _, _ in windows for p in [a, b]]}
        for candidate in candidates:
            if candidate["activity"] == activity:
                points.update(p for a, b in candidate["work"] for p in [a, b] if begin < p < end)
        day = date.fromisoformat(options["start_date"])
        while midnight(day, tz) < end:
            points.add(midnight(day, tz)); day += timedelta(days=1)
        points = sorted(points)
        for a, b in zip(points, points[1:]):
            relevant = [(count, priority) for s, e, count, priority in windows if s <= a and b <= e]
            count = max([n for n, _ in relevant] or [0])
            if count:
                eligible = [c["id"] for c in candidates if c["activity"] == activity and any(s <= a and b <= e for s, e in c["work"])]
                cells.append({"activity": activity, "start": a, "end": b, "required": count, "priority": max(p for _, p in relevant), "candidates": eligible})
    if not cells or len(cells) > 20000:
        raise ModelLimit("COVERAGE_GRID_LIMIT_OR_EMPTY_DEMAND")
    # Candidato que não atende nenhum intervalo de demanda não é uma opção útil.
    useful = {i for cell in cells for i in cell["candidates"]}
    return {"snapshot": snapshot, "candidates": [c for c in candidates if c["id"] in useful], "cells": cells,
            "rejections": dict(reasons), "begin": begin, "end": end, "tz": tz}


def windows(data):
    candidates = data["candidates"]
    if not candidates:
        return []
    tz = data["tz"]
    first = min(c["start"] for c in candidates).astimezone(tz).date()
    last = max(c["end"] for c in candidates).astimezone(tz).date()
    result, day = [], first
    while day <= last:
        result.append(("max_daily", midnight(day, tz), midnight(day + timedelta(days=1), tz)))
        day += timedelta(days=1)
    monday = first - timedelta(days=first.weekday())
    while monday <= last:
        result.append(("max_weekly", midnight(monday, tz), midnight(monday + timedelta(days=7), tz)))
        monday += timedelta(days=7)
    return result


def day_blocks(data, person):
    options, tz = data["snapshot"]["options"], data["tz"]
    span = options["limits"]["max_consecutive_days"]
    first = data["begin"].astimezone(tz).date() - timedelta(days=span)
    last = data["end"].astimezone(tz).date() + timedelta(days=span)
    day = first
    while day + timedelta(days=span) <= last:
        yield [midnight(day + timedelta(days=i), tz) for i in range(span + 2)]
        day += timedelta(days=1)


def check_solution(data, selected):
    """Não usa CP-SAT: reconta intervalos, minutos, pessoas, descanso e cobertura."""
    snapshot = data["snapshot"]
    by_id = {c["id"]: c for c in data["candidates"]}
    errors = []
    if len(set(selected)) != len(selected) or any(i not in by_id for i in selected):
        return {"valid": False, "errors": ["INVALID_ASSIGNMENT_IDS"]}
    chosen = [by_id[i] for i in selected]
    for person in snapshot["facts"]["employees"]:
        own = [c for c in chosen if c["employee_id"] == person["id"]]
        if not own:
            continue
        for candidate in own:
            if qualify(snapshot, person, candidate):
                errors.append("INELIGIBLE_ASSIGNMENT")
        for i, a in enumerate(own):
            for b in own[i + 1:]:
                if incompatible(snapshot, person, a, b):
                    errors.append("OVERLAP_OR_REST")
        fixed = snapshot["fixed"].get(person["id"], [])
        work = [s for c in own for s in c["work"]] + merge([s for c in fixed for s in c["work"]])
        busy = merge([(c["start"], c["end"]) for c in own + fixed])
        for kind, a, b in windows(data):
            if not any(clipped_total(c["work"], a, b) for c in own):
                continue
            if clipped_total(work, a, b) > cap_limit(snapshot, person, a, b, kind):
                errors.append("TIME_LIMIT")
            if kind == "max_weekly":
                cursor, longest = a, 0
                for s, e in busy:
                    if overlap(s, e, a, b):
                        longest = max(longest, minutes(cursor, max(cursor, s)))
                        cursor = max(cursor, min(e, b))
                longest = max(longest, minutes(cursor, b))
                if longest < weekly_rest(snapshot, person, a, b):
                    errors.append("WEEKLY_REST")
        maximum = snapshot["options"]["limits"]["max_consecutive_days"]
        for boundaries in day_blocks(data, person):
            if not any(overlap(c["start"], c["end"], boundaries[0], boundaries[-1]) for c in own):
                continue
            days = sum(any(overlap(s, e, a, b) for s, e in busy) for a, b in zip(boundaries, boundaries[1:]))
            if days > maximum:
                errors.append("CONSECUTIVE_DAYS")
    gaps, required_total, covered_total = [], 0, 0
    continuity = defaultdict(set)
    for cell in data["cells"]:
        people = {c["employee_id"] for c in chosen if c["activity"] == cell["activity"] and any(s <= cell["start"] and cell["end"] <= e for s, e in c["work"])}
        gap = max(0, cell["required"] - len(people))
        duration = minutes(cell["start"], cell["end"])
        required_total += cell["required"] * duration
        covered_total += min(cell["required"], len(people)) * duration
        continuity[(cell["activity"], cell["start"].astimezone(data["tz"]).date())].update(people)
        if gap:
            gaps.append({"activity_index": cell["activity"], "start_at": cell["start"].isoformat(), "end_at": cell["end"].isoformat(), "missing_staff": gap, "staff_minutes": gap * duration, "priority": cell["priority"]})
    if snapshot["options"]["mode"] == "strict" and gaps:
        errors.append("MANDATORY_COVERAGE")
    maximum = snapshot["options"]["continuity_max_people_per_activity_day"]
    if maximum and any(len(people) > maximum for people in continuity.values()):
        errors.append("CONTINUITY")
    return {"valid": not errors, "errors": sorted(set(errors)), "required_staff_minutes": required_total,
            "covered_staff_minutes": covered_total, "uncovered_staff_minutes": required_total - covered_total, "gaps": gaps}


def approval_blockers(data, selected):
    snapshot, facts = data["snapshot"], data["snapshot"]["facts"]
    options, blockers = snapshot["options"], set()
    if options["eligibility"] != "verified":
        blockers.add("HYPOTHESIS_ELIGIBILITY")
    if options["limits"]["validation_status"] != "validated":
        blockers.add("OPERATIONAL_LIMITS_PENDING")
    if len(options["history_review_evidence"]) < 20:
        blockers.add("HISTORY_REVIEW_REQUIRED")
    scenario = snapshot["scenario"]
    reviewed = scenario["inputs"]["validation_status"] == "validated" and all(d["validation_status"] == "validated" for d in scenario["inputs"]["demands"])
    reviewed |= any(r["entity_digest"] == scenario["digest"] for r in facts["scenario_reviews"])
    if not reviewed:
        blockers.add("SCENARIO_ASSUMPTIONS_PENDING")
    if any(w["validation_status"] != "validated" for w in options["coverage_windows"]):
        blockers.add("HANDOVER_ASSUMPTIONS_PENDING")
    chosen = [c for c in data["candidates"] if c["id"] in selected]
    for candidate in chosen:
        person = next(p for p in facts["employees"] if p["id"] == candidate["employee_id"])
        if not options["activity_job_role_ids"].get(str(candidate["activity"])):
            blockers.add("ACTIVITY_ROLES_UNSPECIFIED")
        first = candidate["start"].astimezone(data["tz"]).date()
        last = (candidate["end"] - timedelta(microseconds=1)).astimezone(data["tz"]).date()
        day = first
        while day <= last:
            contract = contract_at(facts, person, day)
            if contract is None or contract["validation_status"] != "validated":
                blockers.add("CONTRACT_PENDING")
            elif contract:
                pattern = next(p for p in facts["work_patterns"] if p["id"] == contract["work_pattern_id"])
                if pattern["legal_status"] != "validated":
                    blockers.add("PATTERN_PENDING")
                anchor = options["cycle_anchors"].get(pattern["id"]) or (scenario["inputs"].get("cycle_anchor") if scenario["inputs"].get("work_pattern_id") == pattern["id"] else None)
                if not pattern["configuration"].get("cycle") or not anchor:
                    blockers.add("CYCLE_CONFIGURATION_REQUIRED")
            day += timedelta(days=1)
        rules = rules_for(snapshot, person, candidate["start"], candidate["end"])
        points = sorted({candidate["start"], candidate["end"], *[p for r in rules for p in rule_span(r, facts, data["tz"]) if candidate["start"] < p < candidate["end"]]})
        for a, b in zip(points, points[1:]):
            for kind in ["max_daily", "max_weekly", "min_break", "min_rest", "min_weekly_rest"]:
                active = [r for r in rules if r["kind"] == kind and rule_span(r, facts, data["tz"])[0] <= a and rule_span(r, facts, data["tz"])[1] >= b]
                if not active:
                    blockers.add("RULE_FAMILY_MISSING")
                if any(r["status"] != "validated" for r in active):
                    blockers.add("RULE_PENDING")
                if len({(r["minutes"], r["threshold_minutes"]) for r in active}) > 1:
                    blockers.add("RULE_CONFLICT")
        for rule in rules:
            if rule["kind"] not in {"max_daily", "max_weekly", "min_break", "min_rest", "min_weekly_rest"}:
                blockers.add("UNSUPPORTED_RULE")
        for kind, a, b in windows(data):
            if kind not in {"max_daily", "max_weekly"} or not clipped_total(candidate["work"], a, b):
                continue
            window_rules = rules_for(snapshot, person, a, b, kind)
            if kind == "max_weekly":
                window_rules += rules_for(snapshot, person, a, b, "min_weekly_rest")
            for rule in window_rules:
                left, right = rule_span(rule, facts, data["tz"])
                if left > a or right < b:
                    blockers.add("RULE_WINDOW_TRANSITION")
    return sorted(blockers)


def solve(snapshot):
    import ortools
    from ortools.sat.python import cp_model
    started = monotonic()
    data = prepare(snapshot)
    candidates, cells = data["candidates"], data["cells"]
    model = cp_model.CpModel()
    variables = {c["id"]: model.new_bool_var(f'x{c["id"]}') for c in candidates}
    gaps_by_priority = defaultdict(list)
    for index, cell in enumerate(cells):
        active = [variables[i] for i in cell["candidates"] if i in variables]
        if snapshot["options"]["mode"] == "strict":
            model.add(sum(active) >= cell["required"])
        else:
            gap = model.new_int_var(0, cell["required"], f"gap{index}")
            model.add(sum(active) + gap >= cell["required"])
            gaps_by_priority[cell["priority"]].append(gap * minutes(cell["start"], cell["end"]))
    workloads = []
    for person in snapshot["facts"]["employees"]:
        own = [c for c in candidates if c["employee_id"] == person["id"]]
        if not own:
            continue
        for i, a in enumerate(own):
            for b in own[i + 1:]:
                if incompatible(snapshot, person, a, b):
                    model.add(variables[a["id"]] + variables[b["id"]] <= 1)
        fixed = snapshot["fixed"].get(person["id"], [])
        fixed_work = merge([s for c in fixed for s in c["work"]])
        for kind, a, b in windows(data):
            coefficients = [(c, clipped_total(c["work"], a, b)) for c in own if clipped_total(c["work"], a, b)]
            if not coefficients:
                continue
            used = model.new_bool_var(f"used_{person['id']}_{kind}_{a.isoformat()}")
            model.add_max_equality(used, [variables[c["id"]] for c, _ in coefficients])
            model.add(sum(variables[c["id"]] * m for c, m in coefficients) + clipped_total(fixed_work, a, b) <= cap_limit(snapshot, person, a, b, kind)).only_enforce_if(used)
            if kind == "max_weekly":
                rest = weekly_rest(snapshot, person, a, b)
                if rest:
                    starts = {a, *[c["end"] for c in own + fixed if a < c["end"] < b]}
                    choices = []
                    for start in sorted(starts):
                        finish = start + timedelta(minutes=rest)
                        if finish > b or any(overlap(start, finish, c["start"], c["end"]) for c in fixed):
                            continue
                        choice = model.new_bool_var(f"rest_{person['id']}_{start.isoformat()}")
                        for c in own:
                            if overlap(start, finish, c["start"], c["end"]):
                                model.add(variables[c["id"]] == 0).only_enforce_if(choice)
                        choices.append(choice)
                    model.add(sum(choices) >= 1).only_enforce_if(used)
        for boundaries in day_blocks(data, person):
            relevant = [c for c in own if overlap(c["start"], c["end"], boundaries[0], boundaries[-1])]
            if not relevant:
                continue
            used = model.new_bool_var("consecutive_used")
            model.add_max_equality(used, [variables[c["id"]] for c in relevant])
            days = []
            for a, b in zip(boundaries, boundaries[1:]):
                if any(overlap(c["start"], c["end"], a, b) for c in fixed):
                    days.append(1)
                else:
                    day = model.new_bool_var("working_day")
                    active = [variables[c["id"]] for c in own if overlap(c["start"], c["end"], a, b)]
                    model.add_max_equality(day, active or [0])
                    days.append(day)
            model.add(sum(days) <= snapshot["options"]["limits"]["max_consecutive_days"]).only_enforce_if(used)
        workload = model.new_int_var(0, 1000000, "workload")
        model.add(workload == sum(variables[c["id"]] * sum(minutes(a, b) for a, b in c["work"]) for c in own))
        workloads.append(workload)
    continuity = snapshot["options"]["continuity_max_people_per_activity_day"]
    if continuity:
        groups = defaultdict(set)
        for cell in cells:
            groups[(cell["activity"], cell["start"].astimezone(data["tz"]).date())].update(cell["candidates"])
        for group in groups.values():
            people = defaultdict(list)
            for c in candidates:
                if c["id"] in group:
                    people[c["employee_id"]].append(variables[c["id"]])
            assigned_people = []
            for values in people.values():
                assigned = model.new_bool_var("continuity_person")
                model.add_max_equality(assigned, values)
                assigned_people.append(assigned)
            model.add(sum(assigned_people) <= continuity)
    maximum, minimum = model.new_int_var(0, 1000000, "max_work"), model.new_int_var(0, 1000000, "min_work")
    model.add_max_equality(maximum, workloads or [0]); model.add_min_equality(minimum, workloads or [0])
    options = snapshot["options"]
    work = sum(variables[c["id"]] * sum(minutes(a, b) for a, b in c["work"]) for c in candidates)
    cost = sum(variables[c["id"]] * c["cost_cents"] for c in candidates)
    preferences = sum(variables[c["id"]] * c["penalty"] for c in candidates)
    stages = [(f"gap_priority_{priority}", sum(values)) for priority, values in sorted(gaps_by_priority.items(), reverse=True)]
    stages += [("minimum_work_minutes", work), ("cost_balance_preferences", cost * options["cost_weight"] +
               (maximum - minimum) * options["balance_weight"] + preferences * options["preference_weight"])]
    traces, selected, final_status = [], None, "UNKNOWN"
    for name, expression in stages:
        remaining = options["seconds"] - (monotonic() - started)
        if remaining <= 0:
            final_status = "FEASIBLE" if selected is not None else "UNKNOWN"
            break
        model.minimize(expression)
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = remaining
        solver.parameters.num_search_workers = options["workers"]
        solver.parameters.random_seed = options["seed"]
        solver.parameters.max_memory_in_mb = 512
        status = solver.solve(model)
        status_name = solver.status_name(status)
        trace = {"stage": name, "status": status_name, "wall_seconds": solver.wall_time}
        if status in {cp_model.OPTIMAL, cp_model.FEASIBLE}:
            selected = [i for i, variable in variables.items() if solver.value(variable)]
            trace.update({"objective": solver.objective_value, "best_bound": solver.best_objective_bound})
            final_status = status_name
            traces.append(trace)
            if status != cp_model.OPTIMAL:
                break
            model.add(expression == round(solver.objective_value))
        else:
            traces.append(trace)
            final_status = "FEASIBLE" if selected is not None and status == cp_model.UNKNOWN else status_name
            break
    report = {"solver_status": final_status, "stages": traces, "ortools_version": ortools.__version__, "algorithm_version": "chronos-cpsat-1.0",
        "seconds": round(monotonic() - started, 6), "seed": options["seed"], "workers": options["workers"], "variables": len(variables),
        "coverage_cells": len(cells), "candidate_rejections": data["rejections"], "assignments": [], "verification": {"valid": False},
        "approval_blockers": [], "scope": "Conformidade com regras configuradas; não é certificação jurídica ou publicação."}
    if selected is not None:
        report["verification"] = check_solution(data, selected)
        report["approval_blockers"] = approval_blockers(data, selected)
        if report["verification"].get("uncovered_staff_minutes"):
            report["approval_blockers"].append("UNCOVERED_DEMAND")
        report["estimated_cost_cents"] = sum(c["cost_cents"] for c in candidates if c["id"] in selected)
        for candidate in candidates:
            if candidate["id"] in selected:
                report["assignments"].append({"candidate_id": candidate["id"], "employee_id": candidate["employee_id"], "activity_index": candidate["activity"],
                    "department_id": candidate["department_id"], "start_at": candidate["start"].isoformat(), "end_at": candidate["end"].isoformat(),
                    "breaks": candidate["breaks"], "label": options["templates"][candidate["template"]]["name"]})
        if not report["verification"]["valid"]:
            report["solver_status"] = "VERIFICATION_FAILED"
    report["empty_coverage_cells"] = sum(not c["candidates"] for c in cells)
    return report
