#!/usr/bin/env python3
"""Earlybird collector: free public signals about new startups, merged per company and scored.

Standard library only, so it runs anywhere Python 3.9+ runs (an AI assistant's code sandbox, a coding
agent, a laptop, GitHub Actions). Every source is optional; a source that fails is reported and
skipped, so the assistant can fall back to web search for it.

Usage:
  python collect.py collect --profile radar-profile.json --days 7 --out signals.json
  python collect.py collect --profile radar-profile.json --sources hn,yc,github
  python collect.py jobs --company acme            # Greenhouse / Lever / Ashby open roles
  python collect.py site --url https://acme.com    # homepage check: demo CTA, pricing, B2B words
"""
from __future__ import annotations

import argparse
import html
import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

UA = "earlybird-skill/1.0"
SOURCES = ["hn", "hn_intent", "hn_hiring", "yc", "github", "sec_formd", "companies_house"]
_last_call: dict[str, float] = {}


# ----------------------------------------------------------------------------- http
def get(url: str, params: dict | None = None, headers: dict | None = None, timeout: int = 30,
        min_interval: float = 0.0, as_json: bool = True):
    if params:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    host = urllib.parse.urlparse(url).netloc
    wait = _last_call.get(host, 0) + min_interval - time.time()
    if wait > 0:
        time.sleep(wait)
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                _last_call[host] = time.time()
                body = r.read().decode("utf-8", "replace")
                return json.loads(body) if as_json else body
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and attempt < 2:
                time.sleep(2 * (attempt + 1))
                continue
            raise


def utc(v) -> datetime:
    if isinstance(v, (int, float)):
        return datetime.fromtimestamp(v, tz=timezone.utc)
    d = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


SKIP_DOMAINS = {"github.com", "news.ycombinator.com", "ycombinator.com", "twitter.com", "x.com", "linkedin.com",
                "medium.com", "youtube.com", "reddit.com", "producthunt.com", "substack.com", "notion.site",
                "google.com", "apple.com", "gitlab.com", "huggingface.co", "vercel.app", "netlify.app",
                # job boards, forms and link hosts: shared by many companies, so never a company's own domain
                "ashbyhq.com", "lever.co", "greenhouse.io", "workable.com", "wellfound.com", "angel.co",
                "breezy.hr", "recruitee.com", "teamtailor.com", "rippling.com", "gusto.com", "bamboohr.com",
                "jobvite.com", "smartrecruiters.com", "workatastartup.com", "forms.gle", "typeform.com",
                "tally.so", "notion.so", "calendly.com", "airtable.com", "bit.ly", "linktr.ee", "hackernews.com"}


def domain(url: str | None) -> str | None:
    if not url:
        return None
    if "://" not in url:
        url = "https://" + url
    host = (urllib.parse.urlparse(url).netloc or "").lower().split(":")[0]
    host = host[4:] if host.startswith("www.") else host
    if not host or "." not in host:
        return None
    if any(host == d or host.endswith("." + d) for d in SKIP_DOMAINS):
        return None
    return host


TAG = re.compile(r"<[^>]+>")


def clean(text_html: str | None) -> str:
    return html.unescape(TAG.sub("", re.sub(r"<p>", "\n", text_html or ""))).strip()


def signal(source, kind, title, url, observed_at, strength, website=None, description="", people=None, **extra):
    return {"source": source, "kind": kind, "title": title, "url": url, "observed_at": observed_at.isoformat(),
            "website": website, "domain": domain(website), "description": description[:400],
            "people": people or [], "strength": round(strength, 2), "extra": extra}


# ----------------------------------------------------------------------------- sources
HN = "https://hn.algolia.com/api/v1/search_by_date"
_PREFIX = re.compile(r"^(show|launch)\s+hn\s*[:\-–—]\s*", re.I)
_SPLIT = re.compile(r"\s+[\-–—|:]\s+|\s*[:–—]\s+|,\s+")


def hn_name(title: str) -> str:
    t = re.sub(r"\s*\((yc|ycombinator)[^)]*\)", "", _PREFIX.sub("", title).strip(), flags=re.I)
    name = _SPLIT.split(t, maxsplit=1)[0].strip()
    return name[:60] if len(name.split()) <= 5 else name.split(" ")[0][:60]


def parse_hn(hits: list[dict], min_points: int = 5) -> list[dict]:
    out = []
    for h in hits:
        title = h.get("title") or ""
        if not _PREFIX.match(title):
            continue
        launch = title.lower().startswith("launch hn")
        pts = h.get("points") or 0
        if pts < min_points and not launch:
            continue
        own_site = domain(h.get("url")) is not None
        author = h.get("author")
        out.append(signal(
            "hn", "accelerator" if launch else "launch", hn_name(title),
            f"https://news.ycombinator.com/item?id={h['objectID']}", utc(h["created_at_i"]),
            2.0 if launch else min(3.0, 0.6 + pts / 50) * (1.0 if own_site else 0.4),
            website=h.get("url"), description=title,
            people=[{"name": author, "role": "poster", "url": f"https://news.ycombinator.com/user?id={author}"}] if author else [],
            points=pts))
    return out


def src_hn(since, profile):
    out = []
    for tags, query in (("show_hn", ""), ("story", "Launch HN")):
        for page in range(10):
            d = get(HN, {"tags": tags, "query": query, "hitsPerPage": 100, "page": page,
                         "numericFilters": f"created_at_i>{int(since.timestamp())}"})
            out += parse_hn(d.get("hits", []))
            if page + 1 >= d.get("nbPages", 0):
                break
    return out


SELF_PROMO = re.compile(r"\b(i|we)\s+(built|made|launched|founded|run|created)\b|\bour (tool|product|platform|startup)\b|\bshow hn\b", re.I)
BUYING = re.compile(r"\b(looking for|alternatives? (to|for)|switch(ed|ing)? (from|away)|recommend(ation)?s?|"
                    r"anyone (using|tried|use)|what do you (use|recommend)|replace|need help|any advice|suggestions?)\b", re.I)
JOB_THREAD = re.compile(r"\b(who is hiring|who wants to be hired|seeking freelancer)\b", re.I)
SEEKING_WORK = re.compile(r"\b(seeking work|available for (hire|work)|open to (work|roles)|my (resume|cv)|hire me)\b", re.I)


def topic_patterns(profile: dict) -> dict[str, re.Pattern]:
    """Intent topics come from the user's profile: competitor names and pain phrases per offer."""
    pats = {}
    for o in profile.get("offers", []):
        if comps := o.get("competitors", []):
            pats[f"competitor:{o['key']}"] = re.compile(r"\b(" + "|".join(re.escape(c.lower()) for c in comps) + r")\b", re.I)
        phrases = o.get("pain_phrases", [])
        if phrases:
            pats[f"pain:{o['key']}"] = re.compile(r"\b(" + "|".join(re.escape(p.lower()) for p in phrases) + r")\b", re.I)
    return pats


def parse_intent(hit: dict, pats: dict[str, re.Pattern]) -> dict | None:
    is_comment = hit.get("comment_text") is not None
    body = clean(hit.get("comment_text") if is_comment else hit.get("story_text"))
    title = hit.get("title") or hit.get("story_title") or ""
    text = body if is_comment else f"{title}\n{body}"
    topics = [t for t, rx in pats.items() if rx.search(text)]
    author = hit.get("author")
    if not topics or not author or JOB_THREAD.search(title) or SEEKING_WORK.search(text):
        return None
    if not is_comment and _PREFIX.match(title):
        return None  # a Show HN / Launch HN post is a vendor presenting its own product, not a buyer
    promo = bool(SELF_PROMO.search(text)) and not any(t.startswith("competitor") for t in topics)
    ask = title.lower().startswith("ask hn")
    m = next(rx.search(text) for t, rx in pats.items() if t in topics)
    a = max(0, m.start() - 120)
    snippet = ("…" if a else "") + text[a:m.end() + 140].replace("\n", " ")
    buying = bool(BUYING.search(text))
    pain_only = all(t.startswith("pain:") for t in topics)
    if pain_only and not ask and not buying and "?" not in snippet:
        return None  # a phrase used in passing ("the first customers of this ISP"), not someone asking for help
    if promo and pain_only:
        return None  # someone pitching their own solution to the problem
    return signal("hn_intent", "intent", author, f"https://news.ycombinator.com/item?id={hit['objectID']}",
                  utc(hit["created_at_i"]),
                  (2.2 if ask and not is_comment else 1.5) * (1.4 if buying else 1.0) * (0.6 if promo else 1.0),
                  description=f"{'Ask HN' if ask else 'HN comment' if is_comment else 'HN post'} ({title[:80]}): {snippet}",
                  people=[{"name": author, "role": "author", "url": f"https://news.ycombinator.com/user?id={author}"}],
                  intent_topics=topics, buying_language=buying, person_only=True)


def src_hn_intent(since, profile):
    pats = topic_patterns(profile)
    if not pats:
        return []
    queries = [c for o in profile.get("offers", []) for c in o.get("competitors", [])[:10]]
    queries += [p for o in profile.get("offers", []) for p in o.get("pain_phrases", [])[:6]]
    seen, out = set(), []
    for q in queries[:30]:
        d = get(HN, {"query": q, "tags": "(story,comment)", "hitsPerPage": 100,
                     "numericFilters": f"created_at_i>{int(since.timestamp())}"})
        for h in d.get("hits", []):
            if h["objectID"] not in seen and (s := parse_intent(h, pats)):
                seen.add(h["objectID"])
                out.append(s)
    for s in out[:80]:  # the author's HN profile often links their company site
        try:
            about = clean(get(f"https://hn.algolia.com/api/v1/users/{s['title']}", min_interval=0.3).get("about"))
            site = next((u.rstrip(".,") for u in re.findall(r"https?://[^\s<>\"')]+", about) if domain(u)), None)
            s["website"], s["domain"] = site, domain(site)
            s["extra"]["person_only"] = site is None
        except Exception:
            pass
    return out


FIRST_SALES = re.compile(
    r"\b(founding|first)\s+(sales|account executive|ae|gtm|go[- ]to[- ]market|sdr|bdr|business development|growth|revenue)\b|"
    r"\bhead of (sales|gtm|growth|revenue|business development)\b|\bvp,?\s+(of\s+)?sales\b|\bfirst sales hire\b", re.I)
SALES_ROLE = re.compile(
    r"\b(account executives?|sdrs?|bdrs?|sales development|business development (rep|representative|manager)s?|"
    r"sales (reps?|representatives?|managers?|engineers?|directors?|executives?)|inside sales|enterprise sales)\b", re.I)
TEAM_N = re.compile(r"\b(?:team of|we are|we're)\s+(\d{1,3})\b", re.I)
ROLE_WORDS = re.compile(r"\b(head of|vp|engineer|developer|manager|lead|director|executive|founding|sales|gtm|"
                        r"remote|full[- ]time|part[- ]time|contract|hiring|intern)\b", re.I)


def parse_hiring(hit: dict, story_id: str) -> dict | None:
    if str(hit.get("parent_id")) != str(story_id):
        return None
    raw = hit.get("comment_text") or ""
    text = clean(raw)
    header = text.split("\n", 1)[0]
    parts = [p.strip() for p in re.split(r"\s*\|\s*", header) if p.strip()]
    if len(parts) < 2:
        return None
    company = re.sub(r"\s*\((yc|ycombinator)\s*[a-z]?\d{2}\)", "", parts[0], flags=re.I).strip(" -–—:")
    company = re.sub(r"\s*\(?https?://\S+\)?", "", company).strip()
    if not company or len(company) > 60 or (ROLE_WORDS.search(company) and len(company.split()) >= 2):
        return None
    links = [html.unescape(u) for u in re.findall(r'href="([^"]+)"', raw)]
    tokens = [p for p in parts if re.fullmatch(r"(https?://)?[\w.-]+\.[a-z]{2,}(/\S*)?", p, re.I)]
    website = next((u for u in tokens + links if domain(u)), None)
    first = FIRST_SALES.search(text)
    sales = SALES_ROLE.search(text)
    m = TEAM_N.search(text)
    team = int(m.group(1)) if m else None
    return signal("hn_hiring", "sales_hiring" if (first or sales) else "hiring", company,
                  f"https://news.ycombinator.com/item?id={hit['objectID']}", utc(hit["created_at_i"]),
                  min(3.0, (2.0 if first else 1.2 if sales else 0.7) * (1.3 if team and team <= 20 else 1.0)),
                  website=website, description=header[:220], first_sales=bool(first),
                  sales_role=(first or sales).group(0) if (first or sales) else "", team_size=team,
                  intent_topics=["first_sales_hire"] if first else [])


def src_hn_hiring(since, profile):
    """The whole current monthly thread: a job post stays open all month, so the run window does not apply."""
    d = get(HN, {"tags": "story,author_whoishiring", "hitsPerPage": 12})
    threads = sorted([h for h in d.get("hits", []) if (h.get("title") or "").lower().startswith("ask hn: who is hiring")],
                     key=lambda h: h["created_at_i"], reverse=True)[:1]
    out = []
    for t in threads:
        for page in range(5):
            d = get(HN, {"tags": f"comment,story_{t['objectID']}", "hitsPerPage": 1000, "page": page})
            out += [s for h in d.get("hits", []) if (s := parse_hiring(h, t["objectID"]))]
            if page + 1 >= d.get("nbPages", 0):
                break
    return out


def parse_yc(rows: list[dict], since: datetime) -> list[dict]:
    out = []
    for c in rows:
        if not c.get("launched_at") or utc(c["launched_at"]) < since or c.get("status") not in (None, "Active"):
            continue
        out.append(signal("yc", "accelerator", c.get("name") or c.get("slug"),
                          c.get("url") or f"https://www.ycombinator.com/companies/{c.get('slug')}",
                          utc(c["launched_at"]), 2.0, website=c.get("website"),
                          description=f"YC {c.get('batch')}: {c.get('one_liner') or ''}",
                          batch=c.get("batch"), industry=c.get("industry"), team_size=c.get("team_size"),
                          location=c.get("all_locations")))
    return out


def src_yc(since, profile):
    return parse_yc(get("https://yc-oss.github.io/api/companies/all.json", timeout=90), since)


NOISE = re.compile(r"awesome|tutorial|course|interview|roadmap|cheatsheet|leetcode|dotfiles|homework|\bnotes\b|"
                   r"prompts?|jailbreak|leak|crack|free-|-free|wallpaper|resume|portfolio", re.I)


def parse_github(items: list[dict], min_stars: int = 50) -> list[dict]:
    out = []
    for it in items:
        stars = it.get("stargazers_count", 0)
        if stars < min_stars or it.get("fork") or it.get("archived") or NOISE.search(it["full_name"] + " " + (it.get("description") or "")):
            continue
        owner = it.get("owner") or {}
        org = owner.get("type") == "Organization"
        if not (org or domain(it.get("homepage"))):
            continue
        out.append(signal("github", "repo_traction", owner.get("login") if org else it["name"], it["html_url"],
                          utc(it["created_at"]), min(3.0, math.log10(max(stars, 10)) - 0.5 + (0.5 if org else 0)),
                          website=it.get("homepage"), description=f"{it['full_name']}: {it.get('description') or ''} (★{stars})",
                          people=[] if org else [{"name": owner.get("login"), "role": "author", "url": owner.get("html_url")}],
                          stars=stars))
    return out


def src_github(since, profile):
    h = {"Accept": "application/vnd.github+json"}
    if tok := os.getenv("GITHUB_TOKEN"):
        h["Authorization"] = f"Bearer {tok}"
    out = []
    for page in range(1, 4):
        d = get("https://api.github.com/search/repositories",
                {"q": f"created:>={since.date().isoformat()} stars:>=50", "sort": "stars", "order": "desc",
                 "per_page": 100, "page": page}, headers=h, min_interval=2.1)
        out += parse_github(d.get("items", []))
        if len(d.get("items", [])) < 100:
            break
    return out


SEC_LINE = re.compile(r"^(?P<form>\S+(?: \S+)*?)\s{2,}(?P<name>.+?)\s{2,}(?P<cik>\d+)\s{2,}"
                      r"(?P<date>\d{8}|\d{4}-\d{2}-\d{2})\s{2,}(?P<file>\S+)\s*$")
FUND_NAME = re.compile(r"\b(fund|funds|capital|holdings?|aggregator|investors?|partners|ventures|co-?invest\w*|spv|"
                       r"series \w+|portfolio|propert(y|ies)|realty|real estate|income|opportunit\w*|management|"
                       r"assets?|trust|l\.?p\.?|l\.?l\.?c\.?)\b", re.I)
SEC_INDUSTRIES = {"Computers", "Other Technology", "Telecommunications", "Business Services", "Biotechnology",
                  "Other Health Care", "Other Banking and Financial Services", "Insurance", "Other"}


def parse_form_index(text: str) -> list[dict]:
    rows = []
    for line in text.splitlines():
        m = SEC_LINE.match(line)
        if m and m["form"] == "D":
            rows.append({"name": m["name"].strip(), "cik": m["cik"],
                         "accession": m["file"].rsplit("/", 1)[-1].removesuffix(".txt")})
    return rows


def parse_form_d(xml_text: str) -> dict:
    root = ET.fromstring(xml_text)
    for el in root.iter():
        if "}" in el.tag:
            el.tag = el.tag.split("}", 1)[1]

    def t(node, path):
        el = node.find(path) if node is not None else None
        return el.text.strip() if el is not None and el.text else None

    iss, od = root.find("primaryIssuer"), root.find("offeringData")
    people = []
    for p in root.findall("relatedPersonsList/relatedPersonInfo"):
        name = f"{t(p, 'relatedPersonName/firstName') or ''} {t(p, 'relatedPersonName/lastName') or ''}".strip()
        if name:
            rels = ", ".join(r.text for r in p.findall("relatedPersonRelationshipList/relationship") if r.text)
            people.append({"name": name.title() if name.isupper() else name, "role": rels})

    def money(n):
        v = t(od, f"offeringSalesAmounts/{n}") or t(od, f"offeringAmounts/{n}")
        try:
            return float(v) if v else None
        except ValueError:
            return None

    return {"entity_name": t(iss, "entityName"), "entity_type": t(iss, "entityType"),
            "city": t(iss, "issuerAddress/city"), "state": t(iss, "issuerAddress/stateOrCountryDescription"),
            "year_of_inc": t(iss, "yearOfInc/value"), "yet_to_be_formed": t(iss, "yearOfInc/yetToBeFormed") == "true",
            "industry": t(od, "industryGroup/industryGroupType"), "total_sold": money("totalAmountSold"),
            "total_offering": money("totalOfferingAmount"), "people": people}


def form_d_signal(row: dict, doc: dict, filed: datetime) -> dict | None:
    name = doc["entity_name"] or row["name"]
    if FUND_NAME.search(name) or doc["entity_type"] not in ("Corporation", None) or doc["industry"] not in SEC_INDUSTRIES:
        return None
    if not doc["yet_to_be_formed"]:
        try:
            if filed.year - int(doc["year_of_inc"] or 0) > 3:
                return None
        except ValueError:
            return None
    sold = doc["total_sold"] or 0
    if sold > 50_000_000:
        return None
    loc = ", ".join(x for x in (doc["city"], doc["state"]) if x)
    return signal("sec_formd", "funding", name,
                  f"https://www.sec.gov/Archives/edgar/data/{row['cik']}/{row['accession'].replace('-', '')}/",
                  filed, 1.0 + min(2.0, sold / 2_000_000),
                  description=f"Form D: {doc['industry']}, raised ${sold:,.0f}" + (f", inc. {doc['year_of_inc']}" if doc["year_of_inc"] else ""),
                  people=doc["people"], total_sold=sold, location=loc or None)


def src_sec_formd(since, profile):
    email = profile.get("contact_email") or os.getenv("EARLYBIRD_CONTACT_EMAIL")
    if not email:
        raise RuntimeError("needs contact_email in the profile (SEC requires a contact in the User-Agent)")
    h = {"User-Agent": f"earlybird-skill {email}"}
    out, fetched, day = [], 0, since.date()
    while day <= datetime.now(timezone.utc).date() and fetched < 400:
        if day.weekday() < 5:
            url = f"https://www.sec.gov/Archives/edgar/daily-index/{day.year}/QTR{(day.month - 1) // 3 + 1}/form.{day:%Y%m%d}.idx"
            try:
                rows = parse_form_index(get(url, headers=h, min_interval=0.15, as_json=False))
            except Exception:
                rows = []
            filed = datetime(day.year, day.month, day.day, 21, tzinfo=timezone.utc)
            for row in rows[: 400 - fetched]:
                fetched += 1
                try:
                    xml_text = get(f"https://www.sec.gov/Archives/edgar/data/{row['cik']}/{row['accession'].replace('-', '')}/primary_doc.xml",
                                   headers=h, min_interval=0.15, as_json=False)
                    if s := form_d_signal(row, parse_form_d(xml_text), filed):
                        out.append(s)
                except Exception:
                    continue
        day += timedelta(days=1)
    return out


SOFTWARE_SIC = ["62011", "62012", "62020", "62090", "63110", "63120", "58290"]


def src_companies_house(since, profile):
    key = os.getenv("COMPANIES_HOUSE_API_KEY")
    if not key:
        raise RuntimeError("needs COMPANIES_HOUSE_API_KEY (free at developer.company-information.service.gov.uk)")
    import base64
    h = {"Authorization": "Basic " + base64.b64encode(f"{key}:".encode()).decode()}
    d = get("https://api.company-information.service.gov.uk/advanced-search/companies",
            {"incorporated_from": since.date().isoformat(), "sic_codes": ",".join(SOFTWARE_SIC),
             "company_status": "active", "size": 200}, headers=h, min_interval=0.6)
    out = []
    for c in d.get("items", []):
        out.append(signal("companies_house", "incorporation", c.get("company_name", "").title(),
                          f"https://find-and-update.company-information.service.gov.uk/company/{c.get('company_number')}",
                          utc(c.get("date_of_creation")), 0.8,
                          description=f"UK company incorporated {c.get('date_of_creation')}, SIC {', '.join(c.get('sic_codes', []))}"))
    return out


COLLECTORS = {"hn": src_hn, "hn_intent": src_hn_intent, "hn_hiring": src_hn_hiring, "yc": src_yc,
              "github": src_github, "sec_formd": src_sec_formd, "companies_house": src_companies_house}


# ----------------------------------------------------------------------------- merge + score
DEFAULT_WEIGHTS = {"competitor": 4.0, "pain": 3.0, "first_sales_hire": 2.0, "sales_hiring": 1.5, "funding": 2.0,
                   "accelerator": 2.0, "launch": 1.5, "incorporation": 0.6, "repo_traction": 0.5, "hiring": 0.3}
DIRECT = {"competitor", "pain", "first_sales_hire", "sales_hiring"}
STARTUP_KINDS = {"funding", "accelerator", "launch", "incorporation", "repo_traction"}


def norm_name(n: str) -> str:
    n = re.sub(r"\b(inc|llc|ltd|limited|corp|co|gmbh|labs?|ai|hq|app)\b\.?", "", (n or "").lower())
    return re.sub(r"[^a-z0-9]", "", n)


def merge(signals: list[dict]) -> list[dict]:
    groups: dict[str, dict] = {}
    by_name: dict[str, str] = {}
    for s in signals:
        if s["extra"].get("person_only"):
            key = f"person:{s['source']}:{s['title'].lower()}"
        elif s["domain"]:
            key = s["domain"]
        else:
            key = by_name.get(norm_name(s["title"])) or f"name:{norm_name(s['title'])}"
        g = groups.setdefault(key, {"key": key, "name": s["title"], "website": s["website"], "signals": []})
        if s["domain"] and not g["website"]:
            g["website"] = s["website"]
        g["signals"].append(s)
        if not s["extra"].get("person_only"):
            by_name.setdefault(norm_name(s["title"]), key)
    return list(groups.values())


def tags_of(s: dict, offer_key: str) -> set[str]:
    t = {s["kind"]}
    for topic in s["extra"].get("intent_topics", []):
        if topic == "first_sales_hire":
            t.add(topic)
        elif topic == f"competitor:{offer_key}":
            t.add("competitor")
        elif topic == f"pain:{offer_key}":
            t.add("pain")
    return t


def score_offer(c: dict, offer: dict, now: datetime) -> dict:
    w = {**DEFAULT_WEIGHTS, **offer.get("weights", {})}
    best: dict[str, tuple[float, dict, str]] = {}
    for s in c["signals"]:
        tg = max(tags_of(s, offer["key"]), key=lambda x: w.get(x, 0))
        if w.get(tg, 0) <= 0:
            continue
        age = max(0.0, (now - utc(s["observed_at"])).total_seconds() / 86400)
        half_life = 7 if s["kind"] == "intent" else 45 if s["kind"] in ("sales_hiring", "hiring") else 14  # job posts stay open for weeks
        v = w[tg] * s["strength"] * 0.5 ** (age / half_life) * (2.5 if tg in DIRECT else 1)
        if v > best.get(s["source"], (0,))[0]:
            best[s["source"]] = (v, s, tg)
    if not best:
        return {"rule_score": 0.0, "why_now": []}
    mult = min(2.0, 1 + 0.35 * (len(best) - 1))
    team = max([s["extra"].get("team_size") for s in c["signals"] if isinstance(s["extra"].get("team_size"), int)], default=None)
    flags = []
    if offer.get("max_team") and team and team > offer["max_team"]:
        mult *= 0.35
        flags.append(f"team ~{team}, above {offer['max_team']}")
    raised = max((s["extra"].get("total_sold") or 0 for s in c["signals"]), default=0)
    if offer.get("max_raise") and raised > offer["max_raise"]:
        mult *= 0.5
        flags.append(f"large round (${raised / 1e6:.0f}M)")
    kinds = {s["kind"] for s in c["signals"]}
    if not kinds & STARTUP_KINDS and not kinds & {"intent", "sales_hiring"}:
        mult *= 0.6
        flags.append("only job posts, may not be a startup")
    ranked = sorted(best.values(), key=lambda x: x[0], reverse=True)
    return {"rule_score": round(sum(v for v, _, _ in ranked) * mult, 2),
            "why_now": [f"{tg}: {s['description'][:160]} ({s['source']}, {s['observed_at'][:10]}) {s['url']}" for _, s, tg in ranked[:4]],
            "flags": flags, "sources": len(best)}


def cmd_collect(a):
    profile = json.load(open(a.profile)) if a.profile else {"offers": []}
    for i, o in enumerate(profile.get("offers", [])):
        o.setdefault("key", f"offer{i + 1}")
    since = datetime.now(timezone.utc) - timedelta(days=a.days)
    wanted = a.sources.split(",") if a.sources else profile.get("sources", SOURCES)
    signals, status = [], {}
    for name in wanted:
        try:
            got = COLLECTORS[name](since, profile)
            signals += got
            status[name] = f"ok ({len(got)})"
        except Exception as e:
            status[name] = f"failed: {type(e).__name__}: {str(e)[:120]}"
        print(f"{name}: {status[name]}", file=sys.stderr)
    seen = set(profile.get("seen", []))
    now = datetime.now(timezone.utc)
    companies = merge(signals)
    for c in companies:
        c["new"] = c["key"] not in seen
        c["offers"] = {o["key"]: score_offer(c, o, now) for o in profile.get("offers", [])} or \
                      {"default": score_offer(c, {"key": "default"}, now)}
        c["best_score"] = max(v["rule_score"] for v in c["offers"].values())
    companies = [c for c in companies if c["best_score"] >= a.min_score]
    companies.sort(key=lambda c: c["best_score"], reverse=True)
    out = {"generated_at": now.isoformat(), "days": a.days, "source_status": status,
           "companies": companies[: a.limit] if a.limit > 0 else companies}
    with open(a.out, "w") as f:
        json.dump(out, f, indent=1, default=str)
    written = min(a.limit, len(companies)) if a.limit > 0 else len(companies)
    print(f"{len(companies)} companies scored, {written} written to {a.out}", file=sys.stderr)


# ----------------------------------------------------------------------------- enrichment
def cmd_jobs(a):
    slug = re.sub(r"[^a-z0-9-]", "", a.company.lower().split(".")[0])
    boards = {"greenhouse": f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
              "lever": f"https://api.lever.co/v0/postings/{slug}?mode=json",
              "ashby": f"https://api.ashbyhq.com/posting-api/job-board/{slug}"}
    result = {"company": a.company, "boards": {}}
    for name, url in boards.items():
        try:
            d = get(url, timeout=15)
            jobs = d.get("jobs", []) if isinstance(d, dict) else d
            titles = [j.get("title") or j.get("text") for j in jobs]
            result["boards"][name] = {"open_roles": len(titles), "titles": titles[:40],
                                      "sales_roles": [t for t in titles if t and (SALES_ROLE.search(t) or FIRST_SALES.search(t))]}
        except Exception:
            continue
    print(json.dumps(result, indent=1))


def cmd_site(a):
    try:
        page = get(a.url, as_json=False, timeout=20)
    except Exception as e:
        print(json.dumps({"url": a.url, "error": str(e)[:200]}))
        return
    low = page.lower()
    title = re.search(r"<title[^>]*>(.*?)</title>", page, re.I | re.S)
    desc = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)', page, re.I)
    print(json.dumps({
        "url": a.url, "title": html.unescape(title.group(1).strip())[:200] if title else None,
        "description": html.unescape(desc.group(1))[:300] if desc else None,
        "demo_cta": bool(re.search(r"book a demo|request a demo|schedule a demo|talk to sales|contact sales", low)),
        "pricing_page": "/pricing" in low, "self_serve": bool(re.search(r"sign up free|start free|free trial|get started free", low)),
        "b2b_words": len(re.findall(r"\b(teams?|businesses|enterprise|b2b|workflow|saas|companies)\b", low)),
        "b2c_words": len(re.findall(r"\b(download on the app store|for kids|your family|dating|recipes)\b", low)),
        "linkedin": next(iter(re.findall(r"https?://(?:www\.)?linkedin\.com/company/[\w-]+", page)), None),
    }, indent=1))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("collect")
    c.add_argument("--profile")
    c.add_argument("--days", type=int, default=7)
    c.add_argument("--sources", help="comma list: " + ",".join(SOURCES))
    c.add_argument("--min-score", type=float, default=1.0)
    c.add_argument("--limit", type=int, default=0, help="max companies to write; 0 = all (default)")
    c.add_argument("--out", default="signals.json")
    j = sub.add_parser("jobs")
    j.add_argument("--company", required=True, help="company slug or domain")
    s = sub.add_parser("site")
    s.add_argument("--url", required=True)
    a = p.parse_args()
    {"collect": cmd_collect, "jobs": cmd_jobs, "site": cmd_site}[a.cmd](a)


if __name__ == "__main__":
    main()
