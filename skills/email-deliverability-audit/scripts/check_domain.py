#!/usr/bin/env python3
"""Check the email-authentication DNS records of a sending domain.

Looks up MX, SPF, DKIM, DMARC, MTA-STS, TLS-RPT and BIMI and reports problems
with a suggested fix for each. Standard library only: DNS queries go over
DNS-over-HTTPS (Cloudflare, with Google as a fallback), so the script works
without `dig` or extra packages.

Usage:
    python3 check_domain.py example.com
    python3 check_domain.py example.com --selector s1 --selector google
    python3 check_domain.py example.com --format text
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

DOH_ENDPOINTS = (
    "https://cloudflare-dns.com/dns-query",
    "https://dns.google/resolve",
)
RR_TYPES = {"A": 1, "CNAME": 5, "MX": 15, "TXT": 16, "AAAA": 28}
USER_AGENT = "email-deliverability-audit/1.0 (+https://github.com/mailbeast/cold-email-skills)"

# Selectors used by common mail providers and sending tools.
COMMON_DKIM_SELECTORS = (
    "google",        # Google Workspace
    "selector1",     # Microsoft 365
    "selector2",     # Microsoft 365
    "default",
    "dkim",
    "mail",
    "k1", "k2", "k3",  # Mailchimp / Mandrill, Klaviyo
    "s1", "s2",      # SendGrid and others
    "sig1",          # iCloud custom domains
    "zoho", "zmail",  # Zoho
    "mxvault",
    "protonmail", "protonmail2", "protonmail3",
    "smtp", "pm",    # Postmark
    "mandrill",
    "everlytickey1", "everlytickey2",
    "amazonses",
)

def costs_spf_lookup(term: str) -> bool:
    """Mechanisms and modifiers that cost a DNS lookup (RFC 7208, section 4.6.4)."""
    if term in ("a", "mx", "ptr"):
        return True
    return term.startswith(("include:", "exists:", "redirect=", "a:", "a/", "mx:", "mx/", "ptr:"))


class DnsError(RuntimeError):
    pass


def doh_query(name: str, rtype: str) -> dict[str, Any]:
    """Return {"status": int, "answers": [str]} for records of exactly `rtype`."""
    last_error: Exception | None = None
    for endpoint in DOH_ENDPOINTS:
        url = endpoint + "?" + urllib.parse.urlencode({"name": name, "type": rtype})
        request = urllib.request.Request(
            url, headers={"accept": "application/dns-json", "user-agent": USER_AGENT}
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                data = json.load(response)
        except (urllib.error.URLError, TimeoutError, ValueError) as error:
            last_error = error
            continue
        wanted = RR_TYPES[rtype]
        answers = [a["data"] for a in data.get("Answer", []) if a.get("type") == wanted]
        return {"status": data.get("Status", -1), "answers": answers}
    raise DnsError(f"DNS lookup failed for {name} {rtype}: {last_error}")


def txt_records(name: str) -> list[str]:
    """TXT strings of `name`, with multi-string records joined (RFC 7208, 3.3)."""
    records = []
    for raw in doh_query(name, "TXT")["answers"]:
        parts = re.findall(r'"((?:[^"\\]|\\.)*)"', raw)
        records.append("".join(parts) if parts else raw)
    return records


def finding(severity: str, area: str, message: str, fix: str | None = None) -> dict[str, str]:
    item = {"severity": severity, "area": area, "message": message}
    if fix:
        item["fix"] = fix
    return item


# --------------------------------------------------------------------------- MX


def check_mx(domain: str) -> tuple[dict[str, Any], list[dict[str, str]]]:
    result = doh_query(domain, "MX")
    records = []
    for raw in result["answers"]:
        priority, _, host = raw.partition(" ")
        records.append({"priority": int(priority) if priority.isdigit() else priority, "host": host.rstrip(".") or "."})
    records.sort(key=lambda r: r["priority"] if isinstance(r["priority"], int) else 0)
    findings = []
    null_mx = len(records) == 1 and records[0]["host"] == "."
    if result["status"] == 3:
        findings.append(finding("error", "MX", f"{domain} does not exist (NXDOMAIN).", "Check the spelling of the domain."))
    elif null_mx:
        findings.append(finding(
            "error", "MX",
            "Null MX (RFC 7505): the domain declares that it accepts no email. Replies to this domain will bounce.",
            "If you send from this domain and want replies, publish real MX records.",
        ))
    elif not records:
        findings.append(finding(
            "warning", "MX",
            "No MX records. Replies fall back to the A record, and many receivers treat a sender domain without MX as suspicious.",
            "Publish MX records for the mailbox provider that receives replies (for example Google Workspace or Microsoft 365).",
        ))
    return {"records": records, "null_mx": null_mx}, findings


# -------------------------------------------------------------------------- SPF


def spf_record(domain: str) -> tuple[list[str], list[str]]:
    txts = txt_records(domain)
    spf = [t for t in txts if t.lower().startswith("v=spf1")]
    return spf, txts


def count_spf_lookups(domain: str, seen: set[str] | None = None, depth: int = 0) -> tuple[int, int, list[str]]:
    """Return (lookups, void_lookups, notes) for the SPF tree under `domain`."""
    seen = seen if seen is not None else set()
    notes: list[str] = []
    if domain in seen:
        notes.append(f"loop: {domain} is included twice")
        return 0, 0, notes
    if depth > 10:
        notes.append("include chain deeper than 10 levels")
        return 0, 0, notes
    seen.add(domain)
    try:
        spf, _ = spf_record(domain)
    except DnsError as error:
        notes.append(str(error))
        return 0, 0, notes
    if not spf:
        return 0, 1, [f"{domain} has no SPF record (void lookup)"]
    lookups = 0
    voids = 0
    for term in spf[0].split()[1:]:
        bare = term.lstrip("+-~?").lower()
        if not costs_spf_lookup(bare):
            continue
        lookups += 1
        if bare.startswith("include:") or bare.startswith("redirect="):
            target = bare.split(":", 1)[1] if bare.startswith("include:") else bare.split("=", 1)[1]
            sub_lookups, sub_voids, sub_notes = count_spf_lookups(target, seen, depth + 1)
            lookups += sub_lookups
            voids += sub_voids
            notes.extend(sub_notes)
    return lookups, voids, notes


def check_spf(domain: str) -> tuple[dict[str, Any], list[dict[str, str]]]:
    spf, _ = spf_record(domain)
    findings = []
    info: dict[str, Any] = {"records": spf}
    if not spf:
        findings.append(finding(
            "error", "SPF",
            "No SPF record. Gmail, Yahoo and Microsoft expect SPF or DKIM on every message, and bulk senders need both.",
            f'Publish one TXT record on {domain}, for example "v=spf1 include:_spf.google.com ~all" for Google Workspace '
            'or "v=spf1 include:spf.protection.outlook.com ~all" for Microsoft 365, plus an include for each sending service.',
        ))
        return info, findings
    if len(spf) > 1:
        findings.append(finding(
            "error", "SPF",
            f"{len(spf)} SPF records. More than one is a permanent error (permerror) and SPF fails for every message.",
            "Merge them into a single v=spf1 record.",
        ))
    record = spf[0]
    terms = record.split()
    all_terms = [t for t in terms if t.lstrip("+-~?").lower() == "all"]
    if not all_terms:
        if not any(t.lower().startswith("redirect=") for t in terms):
            findings.append(finding("warning", "SPF", "The record has no 'all' mechanism, so unlisted senders get a neutral result.", "End the record with ~all (or -all once every sender is listed)."))
    else:
        qualifier = all_terms[-1][0] if all_terms[-1][0] in "+-~?" else "+"
        info["all"] = qualifier + "all"
        if qualifier == "+":
            findings.append(finding("error", "SPF", "+all lets any server on the internet send as this domain.", "Replace +all with ~all or -all."))
        elif qualifier == "?":
            findings.append(finding("warning", "SPF", "?all (neutral) gives receivers no signal.", "Use ~all or -all."))
    if any(t.lstrip("+-~?").lower().startswith("ptr") for t in terms):
        findings.append(finding("warning", "SPF", "The ptr mechanism is deprecated (RFC 7208) and slow; some receivers ignore it.", "Replace ptr with ip4:/ip6: or include: entries."))
    lookups, voids, notes = count_spf_lookups(domain)
    info["dns_lookups"] = lookups
    info["void_lookups"] = voids
    if notes:
        info["notes"] = notes
    if lookups > 10:
        findings.append(finding(
            "error", "SPF",
            f"The record needs {lookups} DNS lookups; the limit is 10 (RFC 7208). Receivers return permerror and SPF fails.",
            "Remove includes for services you no longer use, or replace some includes with ip4:/ip6: ranges.",
        ))
    elif lookups >= 8:
        findings.append(finding("warning", "SPF", f"The record needs {lookups} of the 10 allowed DNS lookups.", "Leave room before adding another sending service."))
    if voids > 2:
        findings.append(finding("warning", "SPF", f"{voids} lookups return nothing (void lookups); more than 2 can cause permerror.", "Remove includes that point to domains without SPF."))
    return info, findings


# ------------------------------------------------------------------------ DMARC


def parse_tags(record: str) -> dict[str, str]:
    tags = {}
    for part in record.split(";"):
        key, sep, value = part.strip().partition("=")
        if sep:
            tags[key.strip().lower()] = value.strip()
    return tags


def check_dmarc(domain: str) -> tuple[dict[str, Any], list[dict[str, str]]]:
    records = [t for t in txt_records(f"_dmarc.{domain}") if t.lower().startswith("v=dmarc1")]
    findings = []
    info: dict[str, Any] = {"records": records}
    if not records:
        labels = domain.split(".")
        parent = ".".join(labels[1:]) if len(labels) > 2 else None
        if parent:
            parent_records = [t for t in txt_records(f"_dmarc.{parent}") if t.lower().startswith("v=dmarc1")]
            if parent_records:
                info["inherited_from"] = parent
                info["records"] = parent_records
                records = parent_records
    if not records:
        findings.append(finding(
            "error", "DMARC",
            "No DMARC record. Gmail and Yahoo require one for bulk senders, and Microsoft for high-volume senders to Outlook.com.",
            f'Start with a TXT record on _dmarc.{domain}: "v=DMARC1; p=none; rua=mailto:dmarc@{domain}". '
            "Move to p=quarantine and then p=reject once the reports show all legitimate mail passing.",
        ))
        return info, findings
    if len(records) > 1:
        findings.append(finding("error", "DMARC", "More than one DMARC record; receivers ignore DMARC entirely.", "Keep a single v=DMARC1 record."))
    tags = parse_tags(records[0])
    info["tags"] = tags
    policy = tags.get("p", "").lower()
    if policy not in ("none", "quarantine", "reject"):
        findings.append(finding("error", "DMARC", f"Invalid or missing policy p={policy or '(empty)'}.", "Set p=none, p=quarantine or p=reject."))
    elif policy == "none":
        findings.append(finding("info", "DMARC", "p=none monitors only; spoofed mail is still delivered. It meets the Gmail/Yahoo minimum.", "After checking the aggregate reports, move to p=quarantine, then p=reject."))
    if "rua" not in tags:
        findings.append(finding("warning", "DMARC", "No rua address, so you receive no aggregate reports and cannot see who sends as your domain.", f"Add rua=mailto:dmarc@{domain} (or a DMARC reporting service)."))
    pct = tags.get("pct")
    if pct and pct.isdigit() and int(pct) < 100:
        findings.append(finding("info", "DMARC", f"pct={pct}: the policy applies to only {pct}% of failing mail.", "Raise pct to 100 when you are confident."))
    return info, findings


# ------------------------------------------------------------------------- DKIM


def dkim_key(domain: str, selector: str) -> str | None:
    """The public key (p=) of `selector`, "" when revoked, None when there is no record."""
    try:
        txts = txt_records(f"{selector}._domainkey.{domain}")
    except DnsError:
        return None
    keys = [t for t in txts if "p=" in t or t.lower().startswith("v=dkim1")]
    if not keys:
        return None
    return re.sub(r"\s+", "", parse_tags(keys[0]).get("p", ""))


def check_dkim(domain: str, selectors: list[str]) -> tuple[dict[str, Any], list[dict[str, str]]]:
    # A wildcard record (*._domainkey) answers for every selector; detect it with
    # a selector nobody uses so it is reported once, not once per selector.
    wildcard = dkim_key(domain, "zz-wildcard-probe-7f3a")
    found = []
    for selector in selectors:
        public_key = dkim_key(domain, selector)
        if public_key is None or (wildcard is not None and public_key == wildcard):
            continue
        entry: dict[str, Any] = {"selector": selector, "key_length_chars": len(public_key)}
        if not public_key:
            entry["revoked"] = True
        else:
            # A base64 RSA public key of ~216 chars is 1024-bit, ~392 chars is 2048-bit.
            entry["approx_rsa_bits"] = 2048 if len(public_key) >= 380 else 1024 if len(public_key) >= 200 else None
        found.append(entry)
    findings = []
    if wildcard is not None:
        findings.append(finding(
            "info", "DKIM",
            "A wildcard DKIM record (*._domainkey) answers for every selector"
            + (" with an empty key, which revokes any selector without its own record." if wildcard == "" else "."),
            None,
        ))
    if not found:
        findings.append(finding(
            "warning", "DKIM",
            f"No DKIM key found for the {len(selectors)} selectors checked. The domain may use a selector not in the list.",
            "Find the selector in the DKIM-Signature header (s=) of a message you sent and run the check again with --selector <name>; "
            "if there is no key, turn on DKIM signing in your mailbox provider and publish the record it gives you.",
        ))
    revoked = [e["selector"] for e in found if e.get("revoked")]
    if revoked:
        findings.append(finding("info", "DKIM", f"Revoked (empty) keys: {', '.join(revoked)}.", "Fine if those selectors are retired; otherwise publish the current key."))
    active = [e for e in found if not e.get("revoked")]
    if found and not active:
        findings.append(finding("warning", "DKIM", "Every DKIM key found is revoked, so no message can pass DKIM with these selectors.", "Turn on DKIM signing in your mailbox provider and publish its key."))
    for entry in active:
        if entry.get("approx_rsa_bits") == 1024:
            findings.append(finding("info", "DKIM", f"Selector {entry['selector']} looks like a 1024-bit key.", "Rotate to a 2048-bit key if your provider supports it."))
    return {"selectors_checked": selectors, "wildcard": wildcard is not None, "found": found}, findings


# ------------------------------------------------------------ MTA-STS, TLS-RPT, BIMI


def fetch_mta_sts_policy(domain: str) -> str | None:
    url = f"https://mta-sts.{domain}/.well-known/mta-sts.txt"
    request = urllib.request.Request(url, headers={"user-agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.read(4096).decode("utf-8", "replace")
    except Exception:  # noqa: BLE001 - any failure means "no usable policy"
        return None


def check_extras(domain: str) -> tuple[dict[str, Any], list[dict[str, str]]]:
    findings = []
    mta_sts = [t for t in txt_records(f"_mta-sts.{domain}") if t.lower().startswith("v=stsv1")]
    tls_rpt = [t for t in txt_records(f"_smtp._tls.{domain}") if t.lower().startswith("v=tlsrptv1")]
    bimi = [t for t in txt_records(f"default._bimi.{domain}") if t.lower().startswith("v=bimi1")]
    info: dict[str, Any] = {"mta_sts": mta_sts, "tls_rpt": tls_rpt, "bimi": bimi}
    if mta_sts:
        policy = fetch_mta_sts_policy(domain)
        mode = re.search(r"^mode:\s*(\w+)", policy or "", re.MULTILINE)
        info["mta_sts_mode"] = mode.group(1) if mode else None
        if not policy:
            findings.append(finding("warning", "MTA-STS", "The _mta-sts record exists but the policy file could not be fetched.", f"Serve https://mta-sts.{domain}/.well-known/mta-sts.txt over valid HTTPS."))
    else:
        findings.append(finding("info", "MTA-STS", "No MTA-STS policy (optional). It protects inbound mail to this domain from TLS downgrade.", None))
    if not tls_rpt:
        findings.append(finding("info", "TLS-RPT", "No TLS reporting record (optional).", f'Add a TXT record on _smtp._tls.{domain}: "v=TLSRPTv1; rua=mailto:tls-reports@{domain}".'))
    if not bimi:
        findings.append(finding("info", "BIMI", "No BIMI record (optional). BIMI shows your logo in supporting inboxes and needs DMARC at quarantine or reject.", None))
    return info, findings


# ------------------------------------------------------------------------ main


def audit(domain: str, selectors: list[str]) -> dict[str, Any]:
    domain = domain.strip().lower().rstrip(".")
    domain = re.sub(r"^https?://", "", domain).split("/")[0]
    if "@" in domain:
        domain = domain.split("@", 1)[1]
    report: dict[str, Any] = {"domain": domain}
    findings: list[dict[str, str]] = []
    for key, check in (
        ("mx", lambda: check_mx(domain)),
        ("spf", lambda: check_spf(domain)),
        ("dmarc", lambda: check_dmarc(domain)),
        ("dkim", lambda: check_dkim(domain, selectors)),
        ("extras", lambda: check_extras(domain)),
    ):
        try:
            info, items = check()
        except DnsError as error:
            info, items = {"error": str(error)}, [finding("warning", key.upper(), f"Lookup failed: {error}", "Run the check again.")]
        report[key] = info
        findings.extend(items)
    order = {"error": 0, "warning": 1, "info": 2}
    findings.sort(key=lambda f: order.get(f["severity"], 3))
    report["findings"] = findings
    report["summary"] = {s: sum(1 for f in findings if f["severity"] == s) for s in ("error", "warning", "info")}
    return report


def as_text(report: dict[str, Any]) -> str:
    lines = [f"Domain: {report['domain']}"]
    mx = report.get("mx", {})
    lines.append("MX: " + (", ".join(f"{r['priority']} {r['host']}" for r in mx.get("records", [])) or "none"))
    spf = report.get("spf", {})
    lines.append("SPF: " + (spf.get("records") or ["none"])[0] + (f"  [{spf.get('dns_lookups')} lookups]" if "dns_lookups" in spf else ""))
    dmarc = report.get("dmarc", {})
    lines.append("DMARC: " + (dmarc.get("records") or ["none"])[0] + (f"  (inherited from {dmarc['inherited_from']})" if dmarc.get("inherited_from") else ""))
    dkim = report.get("dkim", {})
    lines.append("DKIM: " + (", ".join(e["selector"] for e in dkim.get("found", [])) or "no key found for the selectors checked"))
    lines.append("")
    for item in report["findings"]:
        lines.append(f"[{item['severity'].upper()}] {item['area']}: {item['message']}")
        if item.get("fix"):
            lines.append(f"    fix: {item['fix']}")
    summary = report["summary"]
    lines.append("")
    lines.append(f"{summary['error']} errors, {summary['warning']} warnings, {summary['info']} notes")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check email authentication DNS records of a domain.")
    parser.add_argument("domain", help="Domain, email address or URL, e.g. example.com")
    parser.add_argument("--selector", action="append", default=[], help="DKIM selector to check (repeatable). Common selectors are always checked.")
    parser.add_argument("--format", choices=("json", "text"), default="json")
    args = parser.parse_args()
    selectors = list(dict.fromkeys([*args.selector, *COMMON_DKIM_SELECTORS]))
    report = audit(args.domain, selectors)
    print(as_text(report) if args.format == "text" else json.dumps(report, indent=2))
    return 1 if report["summary"]["error"] else 0


if __name__ == "__main__":
    sys.exit(main())
