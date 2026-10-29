"""Spike for `spry pace` (DESIGN.md §17): where did slices' time go? Not part of the tool.

Reads Claude Code session logs, writes a markdown report. Standard library only.

    python3 docs/spikes/pace.py <name> '~/.claude/projects/<project-dir>*' > report.md

Known limits, fixed in the design: a phase is the last skill run; background tasks show only as
the wait on them; no before/after comparison.
"""
import bisect, collections, datetime as dt, glob, json, os, re, statistics, sys

INTERVALS = []
YOU_GAPS = []   # (start, end, session, slice) — waits on you, moved later if you typed elsewhere
PROMPTS = []    # (time, session) of every human prompt
AWAY = 30 * 60  # a wait longer than this is "away", not "waiting on you"

def ts(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()

def slice_of(branch):
    if not branch:
        return None
    m = re.match(r"slice/([A-Z]+\d+)", branch) or re.match(r"sl-(\d+)", branch)
    if not m:
        return None
    return m.group(1) if branch.startswith("slice/") else f"SL-{m.group(1)}"

RUNNERS = {"pytest", "vitest", "jest", "playwright", "mocha", "ava"}

def segments(cmd):
    cmd = re.sub(r"<<-?\s*['\"]?(\w+)['\"]?.*?\n.*?\n\1\b", " ", cmd, flags=re.S)  # drop heredoc bodies
    for seg in re.split(r"&&|\|\||;|\||\n|\(|\)|\bdo\b|\bthen\b", cmd):
        w = seg.split()
        while w and (re.match(r"^[A-Z_][A-Z0-9_]*=", w[0]) or w[0] in ("export", "env", "time", "exec", "sudo", "{")):
            w = w[1:]
        if w:
            yield w

def seg_kind(w):
    h = w[0].split("/")[-1]
    rest = " ".join(w[1:6])
    if h in ("spry", "spry.py", "writ", "writ.py") or (h.startswith("python") and len(w) > 1 and re.search(r"(spry|writ)(\.py)?$", w[1])):
        sub = next((x for x in w[1:] if not x.startswith("-") and not re.search(r"(spry|writ)(\.py)?$|/", x)), "")
        return {"gate": "gate", "falsify": "falsify", "check": "spry check/index", "index": "spry check/index"}.get(sub, "spry other")
    if h in ("until", "while", "sleep") or (h == "for" and "sleep" in " ".join(w)):
        return "polling"
    if h in RUNNERS or (h in ("npx", "pnpm", "npm", "yarn", "bunx") and re.search(r"(^|\s)(vitest|jest|playwright|test|test:\S+|e2e|exec vitest|falsify)\b", rest)):
        return "falsify" if "falsify" in rest else "tests (outside gate)"
    if h == "go" and rest.startswith("test") or h == "cargo" and rest.startswith("test"):
        return "tests (outside gate)"
    if h in ("tsc", "eslint", "ruff", "mypy", "prettier", "biome") or (h in ("npx", "pnpm", "npm", "yarn") and re.search(r"\b(lint|typecheck|tsc|eslint|prettier|format|check-types)\b", rest)):
        return "fast checks (outside gate)"
    if h in ("docker", "docker-compose"):
        return "stack"
    if h == "gh":
        return "gh"
    if h == "git":
        return "git"
    if h in ("pnpm", "npm", "npx", "yarn"):
        return "pnpm/npm other"
    return None

ORDER = ["gate", "falsify", "tests (outside gate)", "fast checks (outside gate)", "polling", "spry check/index",
         "stack", "gh", "git", "pnpm/npm other", "spry other"]

def bash_kind(cmd):
    kinds = {seg_kind(w) for w in segments(cmd)} - {None}
    return next((k for k in ORDER if k in kinds), "shell other")

def tool_kind(b):
    n, i = b["name"], b.get("input", {})
    if n == "Bash":
        return bash_kind(i.get("command", ""))
    if n == "Agent":
        txt = (i.get("description", "") + " " + i.get("subagent_type", "") + " " + i.get("prompt", "")[:400]).lower()
        return "review agent" if "review" in txt else "other agent"
    if n in ("Edit", "Write", "Read", "Grep", "Glob", "NotebookEdit", "MultiEdit"):
        return "file tools"
    if n == "AskUserQuestion":
        return "you: answering a question"
    if n in ("Monitor", "TaskOutput", "BashOutput"):
        return "waiting on background"
    if n == "Skill":
        return "skill load"
    return "other tools"

def skill_phase(name):
    name = (name or "").split(":")[-1].lstrip("/")
    return {"slice-open": "open+build", "slice-close": "close", "merge": "merge", "review": "review",
            "slice": "slicing", "test-all": "test-all"}.get(name, "other")

class Slice:
    def __init__(self):
        self.cat = collections.Counter()      # seconds by category
        self.phase = collections.Counter()    # seconds by phase
        self.first = self.last = None
        self.sessions = set()
        self.prompts = self.asks = self.compacts = 0
        self.gates = []                       # (seconds, ran_tests, ok, steps{name: s}, retried)
        self.falsify = []                     # seconds
        self.reviews = 0
        self.outside_tests = []               # (seconds, command)
        self.agent_cat = collections.Counter()  # time inside subagents, by category
        self.agents = []                      # (seconds, is_review) per subagent

def parse_gate(out):
    steps = {m.group(2): float(m.group(3)) for m in re.finditer(r"^([✓✗]) (.+?) · ([\d.]+)s", out, re.M)}
    ran = any("test" in k for k in steps) or "tests-only" in out
    ok = "✗" not in out and "Exit code" not in out
    return steps, ran, ok, "quiet retry" in out

def walk(path, slices, top, sub=False):
    recs = []
    for line in open(path, errors="replace"):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get("timestamp") and d.get("type") in ("user", "assistant", "system"):
            recs.append(d)
    if not recs:
        return
    pending = {}   # tool_use id -> (start, kind, slice, label, block)
    state, prev, prev_slice, phase, ended, bg = "model", None, None, "other", True, 0
    for d in recs:
        t = ts(d["timestamp"])
        s_id = slice_of(d.get("gitBranch")) or prev_slice
        if prev is not None and t >= prev:
            gap = t - prev
            if pending:
                kind = min(pending.values(), key=lambda v: v[0])[1]
            elif d["type"] == "assistant":
                kind = "model (thinking + writing)"
            else:
                o = (d.get("origin") or {}).get("kind")
                if d.get("type") == "system" and d.get("subtype") == "scheduled_task_fire":
                    kind = "scheduled wake-up"
                elif o == "peer":
                    kind = "waiting on another session"
                elif o == "task-notification" or (ended and bg and gap <= AWAY):
                    kind = "waiting on background"
                elif gap > AWAY:
                    kind = "away"
                elif not ended:
                    kind = "model (thinking + writing)"
                else:
                    kind = "away" if gap > AWAY else "you: reading and replying"
            if not sub and kind == "you: reading and replying":
                YOU_GAPS.append((prev, t, d.get("sessionId"), prev_slice or "(no slice)"))
            if not sub and kind != "away":
                INTERVALS.append((prev, t, kind.startswith("you")))
            key = prev_slice or "(no slice)"
            S = slices[key]
            if sub:
                S.agent_cat[kind] += gap
            else:
                S.cat[kind] += gap
                if kind != "away":
                    S.phase[phase] += gap
        if s_id:
            prev_slice = s_id
        key = prev_slice or "(no slice)"
        S = slices[key]
        if not sub:
            S.sessions.add(d.get("sessionId"))
            S.first = t if S.first is None else min(S.first, t)
            S.last = t if S.last is None else max(S.last, t)
        typ = d["type"]
        if typ == "assistant":
            m = d["message"]
            for b in m.get("content", []):
                if b.get("type") == "tool_use":
                    bg_ = b.get("input", {}).get("run_in_background")
                    k = tool_kind(b)
                    if b["name"] == "Skill":
                        phase = skill_phase(b["input"].get("skill"))
                    if k == "review agent" and not sub:
                        S.reviews += 1
                    if k == "you: answering a question" and not sub:
                        S.asks += 1
                    pending[b["id"]] = (t, k if not bg_ else "starting background", key, b)
                    bg += 1 if bg_ else 0
            ended = m.get("stop_reason") == "end_turn" and not pending
            if pending:
                state = "tool"
            elif m.get("stop_reason") == "end_turn":
                state = "wait"
            else:
                state = "model"
        elif typ == "user":
            c = d["message"]["content"]
            if isinstance(c, list) and any(x.get("type") == "tool_result" for x in c):
                for x in c:
                    if x.get("type") != "tool_result" or x.get("tool_use_id") not in pending:
                        continue
                    start, k, key0, b = pending.pop(x["tool_use_id"])
                    secs = t - start
                    out = x.get("content")
                    out = out if isinstance(out, str) else " ".join(y.get("text", "") for y in (out or []) if isinstance(y, dict))
                    S0 = slices[key0]
                    cmd = b.get("input", {}).get("command", "") or b.get("input", {}).get("description", "")
                    if not sub:
                        top.append((secs, key0, k, cmd.strip().splitlines()[0][:110] if cmd.strip() else b["name"]))
                    if k == "gate":
                        steps, ran, ok, retried = parse_gate(out)
                        S0.gates.append((secs, ran, ok, steps, retried, sub, "--fast" in cmd))
                    elif k == "falsify" and re.search(r"falsify\s+run", cmd):
                        S0.falsify.append(secs)
                    elif k == "tests (outside gate)":
                        S0.outside_tests.append((secs, cmd.strip().splitlines()[0][:110], sub))
                state = "tool" if pending else "model"
            else:
                o = (d.get("origin") or {}).get("kind")
                text = c if isinstance(c, str) else " ".join(x.get("text", "") for x in c if isinstance(x, dict))
                m = re.search(r"<command-name>(.*?)</command-name>", text)
                if m:
                    phase = skill_phase(m.group(1))
                    if m.group(1) == "/compact" and not sub:
                        S.compacts += 1
                if o == "human" and not sub:
                    S.prompts += 1
                    PROMPTS.append((t, d.get("sessionId")))
                if o == "task-notification":
                    bg = max(0, bg - 1)
                if "[Request interrupted" in text:
                    ended = True
                elif not d.get("isMeta"):
                    state = "model"
        elif typ == "system":
            st = d.get("subtype")
            if st == "local_command":
                ended = True
            if st == "turn_duration":
                state = "wait" if not pending else state
                ended = ended or not pending
            elif st == "compact_boundary" and not sub:
                S.compacts += 1
        prev = t

def span(path, slices):
    first = last = br = None
    review = False
    for line in open(path, errors="replace"):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if not d.get("timestamp"):
            continue
        t = ts(d["timestamp"])
        if first is None:
            first = t
            c = d.get("message", {}).get("content", "")
            c = c if isinstance(c, str) else " ".join(x.get("text", "") for x in c if isinstance(x, dict))
            review = bool(re.search(r"\breview", c[:3000], re.I))
        last = t
        br = br or slice_of(d.get("gitBranch"))
    if first is not None:
        S = slices[br or "(no slice)"]
        S.agents.append((last - first, review))

def fmt(s):
    s = int(s)
    return f"{s // 3600}h{s % 3600 // 60:02d}" if s >= 3600 else f"{s // 60}m{s % 60:02d}"

def pct(a, b):
    return f"{100 * a / b:.0f}%" if b else "–"

WORK = lambda S: sum(v for k, v in S.cat.items() if k != "away")

def report(name, dirs):
    slices, top = collections.defaultdict(Slice), []
    for d in dirs:
        for f in sorted(glob.glob(os.path.join(d, "*.jsonl"))):
            walk(f, slices, top)
            for g in glob.glob(os.path.join(f[:-6], "subagents", "*.jsonl")):
                walk(g, slices, top, sub=True)
                span(g, slices)
    PROMPTS.sort()
    times = [p[0] for p in PROMPTS]
    for a, e, sid, key in YOU_GAPS:
        i, j = bisect.bisect_right(times, a), bisect.bisect_left(times, e)
        if any(PROMPTS[x][1] != sid for x in range(i, j)):
            slices[key].cat["you: reading and replying"] -= e - a
            slices[key].cat["you: busy in another session"] += e - a
    real = {k: v for k, v in slices.items() if k != "(no slice)"}
    out = [f"# {name}: where the time went", ""]
    allc = collections.Counter()
    for S in slices.values():
        allc.update(S.cat)
    total = sum(v for k, v in allc.items() if k != "away")
    sl_work = sum(WORK(S) for S in real.values())
    out += [f"- {len(real)} slices · {fmt(total)} of active time in sessions, {fmt(sl_work)} ({pct(sl_work, total)}) of it on slice branches",
            f"- \"away\" (gaps over {AWAY // 60} min) is left out of every total: {fmt(allc['away'])}", ""]
    iv = sorted(INTERVALS)
    wall = agent_wall = 0.0
    for want in (None, False):
        end, acc = 0.0, 0.0
        for a, b, you in iv:
            if want is not None and you != want:
                continue
            a = max(a, end)
            if b > a:
                acc += b - a
                end = b
        if want is None:
            wall = acc
        else:
            agent_wall = acc
    days = len({dt.date.fromtimestamp(a) for a, *_ in iv})
    timeouts = [x for x in top if 595 <= x[0] <= 615 and not x[2].startswith("you")]
    out += [f"- sessions ran side by side: {fmt(wall)} of real time had a session active, over {days} days; "
            f"some agent was busy for {fmt(agent_wall)} of it",
            f"- {len(timeouts)} tool calls ran into the 10-minute Bash limit ({fmt(sum(x[0] for x in timeouts))})", ""]
    out += ["## Where the active time went (all sessions, summed — parallel sessions overlap)", "", "| | time | share |", "|---|---:|---:|"]
    for k, v in allc.most_common():
        if k != "away":
            out.append(f"| {k} | {fmt(v)} | {pct(v, total)} |")
    agent = collections.Counter()
    for S in slices.values():
        agent.update(S.agent_cat)
    at = sum(v for k, v in agent.items() if k != "away")
    out += ["", f"## Inside subagents ({fmt(at)}, overlaps the main session's agent time above)", "", "| | time | share |", "|---|---:|---:|"]
    for k, v in agent.most_common(10):
        if k != "away":
            out.append(f"| {k} | {fmt(v)} | {pct(v, at)} |")

    # per slice
    works = sorted(WORK(S) for S in real.values())
    out += ["", "## Slices", "",
            f"- median active time per slice {fmt(statistics.median(works)) if works else '–'}, "
            f"slowest quarter starts at {fmt(works[3 * len(works) // 4]) if works else '–'}", "",
            "| slice | active | model | tools | gate | falsify | tests outside gate | review agents (n) | you | you elsewhere | sessions | prompts | full gates (failed) | fast gates | compactions |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|"]
    def row(k, S):
        w = WORK(S)
        tools = sum(v for c, v in S.cat.items() if c not in ("away", "model (thinking + writing)") and not c.startswith("you") and not c.startswith("waiting"))
        you = sum(v for c, v in S.cat.items() if c.startswith("you") and "another session" not in c)
        g = [x for x in S.gates if not x[5]]
        full, fast = [x for x in g if not x[6]], [x for x in g if x[6]]
        rv = [x[0] for x in S.agents if x[1]]
        return (f"| {k} | {fmt(w)} | {pct(S.cat['model (thinking + writing)'], w)} | {pct(tools, w)} | {fmt(S.cat['gate'])} | "
                f"{fmt(S.cat['falsify'])} | {fmt(S.cat['tests (outside gate)'])} | {fmt(sum(rv))} ({len(rv)}) | {fmt(you)} | {fmt(S.cat['you: busy in another session'])} | "
                f"{len(S.sessions)} | {S.prompts} | {len(full)} ({sum(1 for x in full if not x[2])}) | {len(fast)} | {S.compacts} |")
    for k, S in sorted(real.items(), key=lambda kv: -WORK(kv[1])):
        out.append(row(k, S))

    # phases
    ph = collections.Counter()
    for S in real.values():
        ph.update(S.phase)
    pt = sum(ph.values())
    out += ["", "## By phase (slice branches, last skill run)", "", "| phase | time | share |", "|---|---:|---:|"]
    for k, v in ph.most_common():
        out.append(f"| {k} | {fmt(v)} | {pct(v, pt)} |")

    # gate detail
    gates = [x for S in real.values() for x in S.gates]
    steps = collections.defaultdict(list)
    for x in gates:
        for n, s in x[3].items():
            steps[n].append(s)
    out += ["", "## Gate", "",
            f"- {len(gates)} gate runs on slices ({sum(1 for x in gates if x[5])} by subagents, {sum(1 for x in gates if x[6])} `--fast`): "
            f"{sum(1 for x in gates if x[1])} ran tests, {sum(1 for x in gates if not x[6] and not x[1])} full gates skipped tests on the stamp or docs-only, "
            f"{sum(1 for x in gates if not x[2])} failed, {sum(1 for x in gates if x[4])} needed a quiet retry",
            "", "| step | runs | total | median | max |", "|---|---:|---:|---:|---:|"]
    for n, v in sorted(steps.items(), key=lambda kv: -sum(kv[1]))[:12]:
        out.append(f"| {n} | {len(v)} | {fmt(sum(v))} | {statistics.median(v):.1f}s | {max(v):.1f}s |")

    # flags
    out += ["", "## Flags", ""]
    flags = []
    for k, S in real.items():
        g = [x for x in S.gates if x[1] and not x[5]]
        if len(g) > 2:
            flags.append((sum(x[0] for x in g), f"{k}: the gate ran tests {len(g)} times ({fmt(sum(x[0] for x in g))}) — §15 expects one full gate per slice"))
        if S.outside_tests:
            s = sum(x[0] for x in S.outside_tests)
            flags.append((s, f"{k}: tests run outside the gate {len(S.outside_tests)} times ({fmt(s)}), e.g. `{S.outside_tests[0][1]}`"))
        f = S.cat["falsify"]
        if WORK(S) and f / WORK(S) > 0.2:
            flags.append((f, f"{k}: falsify took {pct(f, WORK(S))} of the slice ({fmt(f)})"))
        rv = [x[0] for x in S.agents if x[1]]
        if len(rv) > 3:
            flags.append((sum(rv), f"{k}: {len(rv)} review agents ({fmt(sum(rv))})"))
        if S.compacts:
            flags.append((0, f"{k}: {S.compacts} compactions — the context filled up"))
    for _, txt in sorted(flags, reverse=True)[:30]:
        out.append(f"- {txt}")

    out += ["", "## The 25 longest single tool calls", "", "| time | slice | kind | command |", "|---:|---|---|---|"]
    for secs, k, kind, cmd in sorted(top, reverse=True)[:25]:
        out.append(f"| {fmt(secs)} | {k} | {kind} | `{cmd.replace('|', '¦')}` |")

    big = collections.defaultdict(lambda: [0, 0.0])
    for secs, k, kind, cmd in top:
        if kind.startswith("tests") or kind.startswith("fast"):
            key = re.sub(r"\s+", " ", cmd)[:90]
            big[key][0] += 1
            big[key][1] += secs
    out += ["", "## Test and check commands run outside the gate, by total time", "", "| runs | total | command |", "|---:|---:|---|"]
    for cmd, (n, s) in sorted(big.items(), key=lambda kv: -kv[1][1])[:15]:
        out.append(f"| {n} | {fmt(s)} | `{cmd.replace('|', '¦')}` |")
    return "\n".join(out) + "\n"

if __name__ == "__main__":
    print(report(sys.argv[1], [d for g in sys.argv[2:] for d in glob.glob(os.path.expanduser(g))]))
