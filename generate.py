"""
Generate six months (1 Apr - 30 Sep 2026) of realistic, dummy We360 workforce data.

Everything is synthetic: names, emails and IDs are invented. The shape is calibrated to a
real client review deck (462 directory users, ~76% presence coverage, ~7.4h online and
~3.2h active per present day, Teams-heavy app mix, mis-tagged Salesforce / Zoho Books).

Run:  python generate.py          (deterministic: fixed seed)
Out:  data/*.csv                  (the tables, as a We360 export would look)
      derived/*.json              (the same data shaped for the executive dashboard)
"""
import csv, json, math, os, random, datetime as dt
from collections import defaultdict

random.seed(2026)
START, END = dt.date(2026, 4, 1), dt.date(2026, 9, 30)
HOLIDAYS = {  # Malaysia public holidays in the window (sample calendar)
    dt.date(2026, 5, 1): "Labour Day", dt.date(2026, 5, 27): "Hari Raya Haji",
    dt.date(2026, 6, 1): "Agong's Birthday", dt.date(2026, 6, 17): "Awal Muharram",
    dt.date(2026, 8, 25): "Maulidur Rasul", dt.date(2026, 8, 31): "Merdeka Day",
    dt.date(2026, 9, 16): "Malaysia Day",
}
DAYS = [START + dt.timedelta(i) for i in range((END - START).days + 1)]
WORKDAYS = [d for d in DAYS if d.weekday() < 5 and d not in HOLIDAYS]
MONTHS = sorted({d.strftime("%Y-%m") for d in DAYS})

# Settings, copied from the product screenshots
SETTINGS = [
    ("half_day_min_h", "Half day", "Minimum presence", 4, "h"), ("full_day_h", "Half day", "Full day", 8, "h"),
    ("working_time_cap_h", "Half day", "Working time cap", 9, "h"),
    ("wellness_min_h", "Wellness", "Underutilised below (online)", 3, "h"), ("wellness_max_h", "Wellness", "Overburdened above (online)", 7.5, "h"),
    ("goal_online_h", "Goals", "Online time goal", 6, "h"), ("goal_active_h", "Goals", "Active time goal", 5, "h"),
    ("goal_productive_h", "Goals", "Productive time goal", 4, "h"),
    ("capacity_basis", "Capacity benchmark", "Measured on", "online", ""), ("capacity_benchmark_h", "Capacity benchmark", "Benchmark", 7, "h"),
    ("capacity_min_h", "Capacity benchmark", "Min benchmark", 6.25, "h"), ("capacity_max_h", "Capacity benchmark", "Max benchmark", 7.75, "h"),
    ("productive_passive_tracking", "Tracking", "Productive passive time for meetings", False, ""),
]
WEIGHTS = [("work_units", "Work Units", 40, "Units / team median, capped at 1"), ("productive_hours", "Productive Hours", 20, "Avg productive / productive goal"),
           ("attendance_pct", "Attendance %", 15, "Present days / working days"), ("online_hours", "Online Hours", 10, "Avg online / online goal"),
           ("idle_penalty", "Idle Penalty (inverted)", 5, "1 - idle share of online"), ("active_hours", "Active Hours (assumed)", 10, "Assumed sixth metric")]

# team, department, size, active mean, productive share of active, unproductive share, client facing, manager-ish profile
TEAMS = [("MSO - Applications", "MSO", 15, 3.98, .875, .008, False), ("Managed Services", "Managed Services", 10, 3.95, .88, .009, False),
         ("MSO - Monitoring", "MSO", 17, 3.73, .908, .008, False), ("MSO - Infra & AIOps", "MSO", 13, 3.69, .937, .006, False),
         ("People & Culture", "People & Culture", 12, 3.65, .858, .039, False), ("GCC Data AI Presales", "GCC Data AI Presales", 11, 3.61, .94, .008, True),
         ("Salesforce Practice", "Salesforce Practice", 38, 3.50, .856, .010, False), ("Default", "Default", 56, 3.49, .886, .010, False),
         ("Finance & Compliance", "Finance & Compliance", 6, 3.36, .767, .149, False), ("TCoE", "TCoE", 70, 3.34, .898, .005, False),
         ("Product and Innovation", "Product and Innovation", 55, 3.21, .865, .012, False), ("Product Development", "Product Development", 82, 3.01, .872, .013, False),
         ("ESBU", "ESBU", 10, 2.89, .838, .010, False), ("Service Delivery Mgmt", "Service Delivery Mgmt", 31, 2.75, .92, .008, False),
         ("AG MGATE", "AG MGATE", 3, 2.73, .795, .039, False), ("Marketing & Partnership", "Marketing & Partnership", 4, 2.42, .861, .042, True),
         ("MSO - Ops & Service Mgmt", "MSO", 9, 2.23, .755, .015, False), ("Software Engineering", "Software Engineering", 3, 1.96, .911, .001, False),
         ("SAP Practice", "SAP Practice", 7, 1.64, .908, .037, False), ("Sales - MY SG ASEAN", "Sales - MY SG ASEAN", 8, 1.16, .83, .064, True),
         ("IT Security & Governance", "IT Security & Governance", 2, 3.40, .90, .005, False)]
BUSINESS = {"People & Culture", "Finance & Compliance", "Sales - MY SG ASEAN", "Marketing & Partnership", "GCC Data AI Presales"}
PRODUCT = {"Product Development", "Product and Innovation", "Software Engineering"}
LOCATIONS = ["Kuala Lumpur", "Kuala Lumpur", "Kuala Lumpur", "Singapore", "Ho Chi Minh City", "Bengaluru", "Manila"]

FIRST = ("Aiman Nurul Siti Ahmad Farah Hafiz Aisyah Zul Amir Liyana Danial Syafiq Haziq Izzati Khairul Nadia Rizal Shahrul Wei Jun Mei Ling Kai Hui "
         "Xin Yi Jia Hao Minh Thu Anh Duc Lan Huong Quang Tuan Linh Bao Ngoc Hieu Trang Arjun Priya Rahul Sneha Vikram Ananya Karthik Divya Rohan "
         "Meera Suresh Kavya Aditya Lakshmi Naveen Pooja Harish Deepa Ganesh Swathi Varun Ishaan Nikhil Shreya Manoj Revathy Joanna Mark Paolo "
         "Kristine Miguel Angelica Rafael Bea Carlo Jasmine Noel Patricia").split()
LAST = ("Abdullah Rahman Ismail Hamid Yusof Aziz Osman Hassan Tan Lim Wong Lee Chong Ng Teo Goh Nguyen Tran Le Pham Hoang Vu Dang Bui Do Ngo "
        "Sharma Iyer Nair Reddy Menon Rao Pillai Krishnan Subramaniam Gupta Joshi Kulkarni Patel Shetty Murthy Raman Santos Reyes Cruz Bautista "
        "Garcia Mendoza Villanueva Aquino Ramos Navarro").split()

# apps & websites: item -> (kind, category)
ITEMS = {
    "Microsoft Teams": ("app", "Communication"), "teams.microsoft.com": ("url", "Communication"), "Microsoft Outlook": ("app", "Communication"),
    "outlook.cloud.microsoft": ("url", "Communication"), "Remote Desktop": ("app", "Remote access"), "client.visualstudio.com": ("url", "Developer"),
    "dev.azure.com": ("url", "Developer"), "Microsoft Visual Studio 2022": ("app", "Developer"), "ServiceStudio": ("app", "Developer"),
    "sdp.clientgroup.com": ("url", "In-house"), "app.briohr.com": ("url", "In-house"), "Microsoft Excel": ("app", "Office & docs"),
    "client-my.sharepoint.com": ("url", "Office & docs"), "windows.cloud.microsoft": ("url", "Office & docs"),
    "client--uat.sandbox.lightning.force.com": ("url", "CRM"), "Figma": ("app", "Design"),
    "Google Chrome": ("app", "Browser"), "Microsoft Edge": ("app", "Browser"), "Windows Explorer": ("app", "Browser"),
    "portal.vendorhub.io": ("url", "Uncategorised"), "wiki.partnerdocs.net": ("url", "Uncategorised"), "Other unclassified apps": ("app", "Uncategorised"),
    "ntp.msn.com": ("url", "Personal browsing"), "www.linkedin.com": ("url", "Professional network"), "www.youtube.com": ("url", "Video / streaming"),
    "www.facebook.com": ("url", "Social media"), "www.tiktok.com": ("url", "Social media"), "www.ndtv.com": ("url", "News"),
    "www.crazygames.com": ("url", "Gaming"), "Steam": ("app", "Gaming"), "WhatsApp": ("app", "Messaging"),
    "client-lex.lightning.force.com": ("url", "Personal browsing"), "books.zoho.com": ("url", "Finance & accounting"),
    "www2.secure.hsbcnet.com": ("url", "Banking"), "www.pokerstars.com": ("url", "Gambling"), "adult-site.example": ("url", "Adult"),
}
PROD_W = {"Microsoft Teams": 40, "teams.microsoft.com": 3.5, "Microsoft Outlook": 2.2, "outlook.cloud.microsoft": 1.6, "Remote Desktop": 3.7,
          "client.visualstudio.com": 4, "dev.azure.com": 1.9, "Microsoft Visual Studio 2022": 1.6, "ServiceStudio": 1.4, "sdp.clientgroup.com": 1.7,
          "app.briohr.com": 1, "Microsoft Excel": 1.4, "client-my.sharepoint.com": .9, "windows.cloud.microsoft": .9,
          "client--uat.sandbox.lightning.force.com": .6, "Figma": .5}
NEU_W = {"Google Chrome": 30, "Microsoft Edge": 20, "Windows Explorer": 15, "portal.vendorhub.io": 6, "wiki.partnerdocs.net": 4, "Other unclassified apps": 25}
TEAM_TILT = {"Salesforce Practice": {"client--uat.sandbox.lightning.force.com": 8}, "Finance & Compliance": {"Microsoft Excel": 8},
             "Product Development": {"client.visualstudio.com": 8, "Microsoft Visual Studio 2022": 4, "Figma": 2}, "TCoE": {"dev.azure.com": 4, "client.visualstudio.com": 7},
             "MSO - Infra & AIOps": {"Remote Desktop": 10}, "MSO - Monitoring": {"Remote Desktop": 8}, "MSO - Applications": {"ServiceStudio": 5},
             "Service Delivery Mgmt": {"sdp.clientgroup.com": 7}, "People & Culture": {"app.briohr.com": 8}}
AI_TOOLS = [("Microsoft 365 Copilot", .70, (.05, .5)), ("Microsoft Copilot", .41, (.2, 1.6)), ("ChatGPT", .21, (.3, 3.0)), ("Claude", .17, (.3, 3.5)),
            ("Gemini", .085, (.2, 2.0)), ("NotebookLM", .055, (.2, 1.5)), ("DeepSeek", .011, (.2, 1.0)), ("Perplexity", .009, (.2, 1.0)),
            ("Grok", .009, (.1, .8)), ("Blackbox AI", .005, (.2, 1.0)), ("Qwen", .005, (.1, .6))]
AI_KEY = {"Microsoft 365 Copilot": "m365", "Microsoft Copilot": "copilot", "ChatGPT": "chatgpt", "Claude": "claude", "Gemini": "gemini", "NotebookLM": "notebooklm",
          "DeepSeek": "deepseek", "Perplexity": "perplexity", "Grok": "grok", "Blackbox AI": "blackbox", "Qwen": "qwen"}


def clamp(x, a, b): return max(a, min(b, x))


def category_class(team, cat):
    base = {"Communication": "productive", "Remote access": "productive", "In-house": "productive", "Office & docs": "productive",
            "CRM": "productive", "Browser": "neutral", "Uncategorised": "neutral"}.get(cat, "unproductive")
    if cat == "Developer": base = "neutral" if team in BUSINESS else "productive"
    if cat == "Design": base = "productive" if team in PRODUCT | {"Marketing & Partnership"} else "neutral"
    return base


# ---------------------------------------------------------------- people
used, users, persons = set(), [], []
uid = 0
for team, dept, size, act_m, ps_m, up_m, cf in TEAMS:
    for _ in range(size):
        uid += 1
        while True:
            f, l = random.choice(FIRST), random.choice(LAST)
            if (f, l) not in used: used.add((f, l)); break
        join = START if random.random() > 0.07 else random.choice(WORKDAYS[10:110])
        leave = None if random.random() > 0.045 else random.choice(WORKDAYS[30:125])
        if leave and leave <= join: leave = None
        p = dict(user_id=f"U{uid:03d}", employee_id=f"E{1000 + uid}", name=f"{f} {l}", email=f"{f.lower()}.{l.lower()}@client.example",
                 team=team, department=dept, location=random.choice(LOCATIONS), account_type="user",
                 join_date=join.isoformat(), exit_date=leave.isoformat() if leave else "", status="Inactive" if leave else "Active")
        users.append(p)
        lowcov = random.random() < 0.10            # agent often not running / shared devices
        sig = 0.32 if team == "Sales - MY SG ASEAN" else 0.37
        a_mean = clamp(act_m * math.exp(random.gauss(0, sig) - sig * sig / 2), 0.3, 7.2)
        if random.random() < 0.025: a_mean = random.uniform(5.8, 7.0)
        o_mean = clamp(random.gauss(7.4, 0.7), 3.5, 9.0)
        if a_mean < 1.2 and random.random() < 0.3: o_mean = clamp(a_mean + random.uniform(1.0, 2.6), 1.5, 6)
        o_mean = max(o_mean, a_mean + 0.9)
        heavy_game = random.random() < 0.006
        persons.append(dict(p=p, lowcov=lowcov, untracked=random.uniform(0.35, 0.65) if lowcov else random.uniform(0.07, 0.15),
                            a_mean=a_mean, o_mean=o_mean, ps=clamp(random.gauss(ps_m, 0.04), 0.6, 0.985),
                            up=up_m * 0.6 * math.exp(random.gauss(0, 0.7)), punch=random.gauss(9.1, 0.35), units=random.uniform(0.45, 0.75),
                            heavy_game=heavy_game, video=random.uniform(0, 0.25) if random.random() < 0.55 else 0, social=random.uniform(0, 0.15) if random.random() < 0.5 else 0,
                            casual_game=random.uniform(0, 0.5) if random.random() < 0.045 else 0, binge=random.random() < 0.025,
                            adult=random.uniform(0.1, 0.3) if random.random() < 0.0065 else 0, gamble=0.0,
                            ai=[(t, random.uniform(*rng), random.uniform(.35, .9)) for t, pr, rng in AI_TOOLS if random.random() < pr / 0.9] if random.random() < 0.9 else [],
                            power=random.random() < 0.028))
persons[137]["gamble"] = 0.02  # one person with a trace of gambling
# 3 employee IDs that appear under two identities (re-imaged laptops) + 5 test/admin accounts
for a, b in [(40, 41), (200, 203), (330, 333)]:
    users[b]["employee_id"] = users[a]["employee_id"]; users[b]["name"] = users[a]["name"]; users[b]["email"] = users[a]["email"]
for i in range(5):
    users.append(dict(user_id=f"T{i + 1:03d}", employee_id=f"T{900 + i}", name=f"Test admin {i + 1}", email=f"admin{i + 1}@we360.example", team="Default",
                      department="Default", location="Kuala Lumpur", account_type="test", join_date=START.isoformat(), exit_date="", status="Active"))

# ---------------------------------------------------------------- leaves
leaves = []
LEAVE_TYPES = [("Annual Leave", .62), ("Sick Leave", .25), ("Emergency Leave", .06), ("Unpaid Leave", .03), ("Compassionate Leave", .04)]
leave_days = defaultdict(dict)
for P in persons:
    u = P["p"]
    n_blocks = random.choice([1, 2, 2, 3, 3, 4, 4, 5])
    for _ in range(n_blocks):
        r, acc = random.random(), 0
        for lt, pr in LEAVE_TYPES:
            acc += pr
            if r <= acc: break
        length = 1 if lt in ("Sick Leave", "Emergency Leave") and random.random() < .7 else random.choice([1, 2, 3, 5])
        s = random.choice(WORKDAYS[:-5])
        days = [d for d in WORKDAYS if s <= d][:length]
        for d in days: leave_days[u["user_id"]][d] = lt
        leaves.append(dict(user_id=u["user_id"], employee_id=u["employee_id"], leave_type=lt, start_date=days[0].isoformat(), end_date=days[-1].isoformat(), days=len(days), status="Approved"))
for P in random.sample(persons, 2):  # long leave
    u = P["p"]; s = random.choice(WORKDAYS[20:60]); days = [d for d in WORKDAYS if d >= s][:60]
    for d in days: leave_days[u["user_id"]][d] = "Maternity Leave"
    leaves.append(dict(user_id=u["user_id"], employee_id=u["employee_id"], leave_type="Maternity Leave", start_date=days[0].isoformat(), end_date=days[-1].isoformat(), days=len(days), status="Approved"))

# ---------------------------------------------------------------- daily activity + monthly app / AI usage
MONTH_F = {"2026-04": 1.00, "2026-05": 0.99, "2026-06": 1.03, "2026-07": 1.01, "2026-08": 1.01, "2026-09": 0.98}
daily, app_month, ai_month = [], defaultdict(float), []
app_days = defaultdict(set)
for P in persons:
    u = P["p"]; team = u["team"]; join = dt.date.fromisoformat(u["join_date"]); ext = dt.date.fromisoformat(u["exit_date"]) if u["exit_date"] else None
    month_prod = defaultdict(float); month_neu = defaultdict(float); month_unp_items = defaultdict(lambda: defaultdict(float))
    for d in WORKDAYS:
        if d < join or (ext and d > ext): continue
        m = d.strftime("%Y-%m")
        row = dict(date=d.isoformat(), user_id=u["user_id"], employee_id=u["employee_id"], team=team)
        lt = leave_days[u["user_id"]].get(d)
        if lt:
            daily.append({**row, "attendance": "Leave", "leave_type": lt, "punch_in": "", "punch_out": "", **{k: 0 for k in ["working_h", "online_h", "active_h", "idle_h", "break_h", "offline_h", "productive_h", "unproductive_h", "neutral_h"]}})
            continue
        if random.random() < P["untracked"]:
            daily.append({**row, "attendance": "Absent", "leave_type": "", "punch_in": "", "punch_out": "", **{k: 0 for k in ["working_h", "online_h", "active_h", "idle_h", "break_h", "offline_h", "productive_h", "unproductive_h", "neutral_h"]}})
            continue
        wf = {0: 1.02, 1: 1.01, 2: 1.0, 3: 0.99, 4: 0.94}[d.weekday()] * MONTH_F[m]
        if team == "Finance & Compliance" and d.day >= 26: wf *= 1.18                     # month-end close
        if team == "Salesforce Practice" and m == "2026-07": wf *= 1.08                  # go-live crunch
        onl = clamp(random.gauss(P["o_mean"] * wf, 0.95), 0.3, 11.0)
        act = clamp(random.gauss(P["a_mean"] * wf, 0.85 * max(0.35, min(1, P["a_mean"] / 2))), 0.05, onl)
        brk = clamp(random.gauss(0.8, 0.2), 0.2, 1.5); off = clamp(random.gauss(0.35, 0.15), 0.0, 1.2)
        working = onl + brk + off
        pin = clamp(random.gauss(P["punch"], 0.25), 7.5, 11.5); pout = pin + working
        # unproductive minutes come from real items so the totals reconcile
        items = {}
        base_unp = act * P["up"]
        wts = {"ntp.msn.com": 3, "www.linkedin.com": 1.2, "WhatsApp": 1.2, "www.ndtv.com": .4}
        if team in ("Salesforce Practice", "Sales - MY SG ASEAN", "Marketing & Partnership", "GCC Data AI Presales"): wts["client-lex.lightning.force.com"] = 8
        if team == "Finance & Compliance": wts["books.zoho.com"] = 6; wts["www2.secure.hsbcnet.com"] = 1.6
        if team == "People & Culture": wts["www.linkedin.com"] = 7
        sw = sum(wts.values())
        for it, w in wts.items():
            h = base_unp * w / sw * random.uniform(.6, 1.4)
            if h >= .01: items[it] = h
        if P["video"]: items["www.youtube.com"] = items.get("www.youtube.com", 0) + P["video"] * random.uniform(0, 1.6) / 18 * (4 if P["binge"] else 1)
        if P["social"]: items["www.facebook.com"] = items.get("www.facebook.com", 0) + P["social"] * random.uniform(0, 1.4) / 18; items["www.tiktok.com"] = items.get("www.tiktok.com", 0) + P["social"] * random.uniform(0, .6) / 18
        if P["casual_game"]: items["www.crazygames.com"] = items.get("www.crazygames.com", 0) + P["casual_game"] * random.uniform(0, 1.6) / 18
        if P["heavy_game"]: items["Steam"] = items.get("Steam", 0) + random.uniform(0.6, 1.6)
        if P["adult"] and random.random() < .06: items["adult-site.example"] = P["adult"] * random.uniform(.5, 1.5)
        if P["gamble"] and random.random() < .5: items["www.pokerstars.com"] = P["gamble"]
        unp = min(sum(items.values()), act * 0.6)
        scale = unp / max(1e-9, sum(items.values())) if items else 0
        prod = clamp(act * random.gauss(P["ps"], .04), 0, act - unp); neu = max(0, act - prod - unp)
        for it, h in items.items(): month_unp_items[m][it] += h * scale; app_days[(u["user_id"], m, it)].add(d)
        month_prod[m] += prod; month_neu[m] += neu
        daily.append({**row, "attendance": "Half day" if onl < 4 else "Present", "leave_type": "",
                      "punch_in": f"{int(pin):02d}:{int((pin % 1) * 60):02d}", "punch_out": f"{int(pout) % 24:02d}:{int((pout % 1) * 60):02d}",
                      "working_h": round(working, 2), "online_h": round(onl, 2), "active_h": round(act, 2), "idle_h": round(onl - act, 2),
                      "break_h": round(brk, 2), "offline_h": round(off, 2), "productive_h": round(prod, 2), "unproductive_h": round(unp, 2), "neutral_h": round(neu, 2)})
    # spread each month's productive / neutral hours over the team's usual apps
    for m in MONTHS:
        for pool, W, cls in ((month_prod[m], PROD_W, "productive"), (month_neu[m], NEU_W, "neutral")):
            if pool <= 0: continue
            ws = {k: v * (TEAM_TILT.get(team, {}).get(k, 1)) for k, v in W.items() if category_class(team, ITEMS[k][1]) == cls}
            if not ws: ws = {k: v for k, v in NEU_W.items()}
            sw = sum(ws.values())
            for k, v in ws.items():
                h = pool * v / sw * random.uniform(.7, 1.3)
                if h >= .05: app_month[(u["user_id"], m, k)] += h
        for it, h in month_unp_items[m].items():
            if h >= .02: app_month[(u["user_id"], m, it)] += h
    for m in MONTHS:
        mdays = [d for d in WORKDAYS if d.strftime("%Y-%m") == m and d >= join and not (ext and d > ext)]
        if not mdays: continue
        for tool, hrs, pm in P["ai"]:
            if random.random() < pm:
                h = round(hrs * random.uniform(.5, 1.5) * len(mdays) / 22, 2)
                if h > 0: ai_month.append(dict(month=m, user_id=u["user_id"], employee_id=u["employee_id"], tool=tool, hours=h, sessions=max(1, round(h * 3))))
        if P["power"] and P["ai"]:
            tool = random.choice(["ChatGPT", "Claude", "Microsoft Copilot", "Gemini"])
            h = round(random.uniform(4, 12) * len(mdays) / 22, 2)
            ai_month.append(dict(month=m, user_id=u["user_id"], employee_id=u["employee_id"], tool=tool, hours=h, sessions=round(h * 3)))

apps = [dict(month=m, user_id=uid_, team=next(x["team"] for x in users if x["user_id"] == uid_), item=it, kind=ITEMS[it][0], category=ITEMS[it][1],
             classification=category_class(next(x["team"] for x in users if x["user_id"] == uid_), ITEMS[it][1]), hours=round(h, 2),
             active_days=len(app_days.get((uid_, m, it), ())) or None)
        for (uid_, m, it), h in sorted(app_month.items())]
for a in apps:
    if a["active_days"] is None: a["active_days"] = ""

# ---------------------------------------------------------------- write tables
os.makedirs("data", exist_ok=True)
def write(name, rows, cols):
    with open(os.path.join("data", name), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); [w.writerow({k: r.get(k, "") for k in cols}) for r in rows]
write("users.csv", users, ["user_id", "employee_id", "name", "email", "team", "department", "location", "account_type", "join_date", "exit_date", "status"])
write("teams.csv", [dict(team=t[0], department=t[1], client_facing=t[6], headcount=sum(1 for u in users if u["team"] == t[0] and u["account_type"] == "user")) for t in TEAMS],
      ["team", "department", "client_facing", "headcount"])
write("holidays.csv", [dict(date=d.isoformat(), holiday=n, country="MY") for d, n in sorted(HOLIDAYS.items())], ["date", "holiday", "country"])
write("leaves.csv", leaves, ["user_id", "employee_id", "leave_type", "start_date", "end_date", "days", "status"])
write("daily_activity.csv", daily, ["date", "user_id", "employee_id", "team", "attendance", "leave_type", "punch_in", "punch_out", "working_h", "online_h", "active_h",
                                    "idle_h", "break_h", "offline_h", "productive_h", "unproductive_h", "neutral_h"])
write("app_usage_monthly.csv", apps, ["month", "user_id", "team", "item", "kind", "category", "classification", "hours", "active_days"])
write("ai_usage_monthly.csv", ai_month, ["month", "user_id", "employee_id", "tool", "hours", "sessions"])
cats = sorted({c for _, c in ITEMS.values()})
write("category_mapping.csv", [dict(team=t[0], category=c, classification=category_class(t[0], c)) for t in TEAMS for c in cats], ["team", "category", "classification"])
write("settings.csv", [dict(setting=s, group=g, label=l, value=v, unit=u) for s, g, l, v, u in SETTINGS], ["setting", "group", "label", "value", "unit"])
write("score_weights.csv", [dict(metric=m, label=l, enabled=True, weight=w, note=n) for m, l, w, n in WEIGHTS], ["metric", "label", "enabled", "weight", "note"])

# ---------------------------------------------------------------- derived: the shapes the dashboard reads
os.makedirs("derived", exist_ok=True)
by_um = defaultdict(list)
for r in daily: by_um[(r["user_id"], r["date"][:7])].append(r)
cat_key = {"Gaming": "gaming", "Video / streaming": "video", "Social media": "social", "Adult": "adult", "Gambling": "gambling"}
cat_h, ai_h, unp_rows = defaultdict(float), defaultdict(float), []
for a in apps:
    if a["category"] in cat_key: cat_h[(a["user_id"], a["month"], cat_key[a["category"]])] += a["hours"]
    if a["classification"] == "unproductive": unp_rows.append(dict(person_id=a["user_id"], month=a["month"], item=a["item"], hours=a["hours"]))
ai_sess = defaultdict(int)
for a in ai_month: ai_h[(a["user_id"], a["month"], AI_KEY[a["tool"]])] += a["hours"]; ai_sess[(a["user_id"], a["month"])] += a["sessions"]
pm = []
wd_month = {m: sum(1 for d in WORKDAYS if d.strftime("%Y-%m") == m) for m in MONTHS}
for P in persons + [dict(p=u) for u in users if u["account_type"] == "test"]:
    u = P["p"]
    for m in MONTHS:
        rows = by_um.get((u["user_id"], m), [])
        if u["account_type"] == "test":
            rows = []
        if not rows and u["account_type"] == "user": continue
        pres = [r for r in rows if r["attendance"] in ("Present", "Half day")]
        rec = dict(person_id=u["user_id"], month=m, working_days=len(rows) if rows else wd_month[m], present_days=len(pres),
                   leave_days=sum(1 for r in rows if r["attendance"] == "Leave"),
                   online_h=round(sum(r["online_h"] for r in pres), 2), active_h=round(sum(r["active_h"] for r in pres), 2),
                   productive_h=round(sum(r["productive_h"] for r in pres), 2), neutral_h=round(sum(r["neutral_h"] for r in pres), 2),
                   unproductive_h=round(sum(r["unproductive_h"] for r in pres), 2),
                   d_on=[r["online_h"] for r in pres], d_ac=[r["active_h"] for r in pres], d_pr=[r["productive_h"] for r in pres],
                   days_below_min=sum(1 for r in pres if r["online_h"] < 4), days_goal_online=sum(1 for r in pres if r["online_h"] >= 6),
                   days_goal_active=sum(1 for r in pres if r["active_h"] >= 5), days_goal_productive=sum(1 for r in pres if r["productive_h"] >= 4),
                   work_units=round(sum(r["active_h"] for r in pres) * P.get("units", 0) * random.uniform(.8, 1.2)) if pres else 0,
                   ai_sessions=ai_sess.get((u["user_id"], m), 0))
        for k in cat_key.values(): rec[f"cat_{k}_h"] = round(cat_h.get((u["user_id"], m, k), 0), 2)
        for k in AI_KEY.values(): rec[f"ai_{k}_h"] = round(ai_h.get((u["user_id"], m, k), 0), 2)
        pm.append(rec)
team_apps = defaultdict(lambda: [0.0, set()])
for a in apps:
    t = team_apps[(a["team"], a["month"], a["item"])]; t[0] += a["hours"]; t[1].add(a["user_id"])
json.dump([dict(team=t, month=m, item=i, kind=ITEMS[i][0], category=ITEMS[i][1], hours=round(v[0], 1), users=len(v[1])) for (t, m, i), v in team_apps.items()],
          open("derived/apps.json", "w"), separators=(",", ":"))
json.dump(pm, open("derived/people_months.json", "w"), separators=(",", ":"))
json.dump(unp_rows, open("derived/unproductive_items.json", "w"), separators=(",", ":"))
json.dump([dict(person_id=u["user_id"], name=u["name"], employee_id=u["employee_id"], team=u["team"], department=u["department"], account_type=u["account_type"]) for u in users],
          open("derived/people.json", "w"), separators=(",", ":"))
json.dump([dict(team=t[0], department=t[1], client_facing=t[6]) for t in TEAMS], open("derived/teams.json", "w"))
json.dump([dict(team=t[0], category=c, classification=category_class(t[0], c)) for t in TEAMS for c in cats], open("derived/category_mapping.json", "w"))
json.dump([dict(setting=s, group=g, label=l, value=v, unit=u) for s, g, l, v, u in SETTINGS], open("derived/settings.json", "w"))
json.dump([dict(metric=m, label=l, enabled=True, weight=w, note=n) for m, l, w, n in WEIGHTS], open("derived/score_weights.json", "w"))
print(f"{len(users)} users · {len(daily)} daily rows · {len(apps)} app rows · {len(ai_month)} AI rows · {len(leaves)} leave records")
