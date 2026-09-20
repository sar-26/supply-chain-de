"""AI validation bot. Reads RED/AMBER issue groups from dq_issues, asks Claude
for an explanation + recommendation per group, caches on content hash, and
writes results to issue_explanations. See db.py for the connection."""
import hashlib
import json
import os

import anthropic

from db import get_connection

MODEL = "claude-haiku-4-5-20251001"

CREATE_TABLE = """
CREATE TABLE issue_explanations (
    group_key      VARCHAR2(64) PRIMARY KEY,
    check_name     VARCHAR2(50),
    severity       VARCHAR2(10),
    issue_count    NUMBER,
    content_hash   VARCHAR2(64),
    explanation    CLOB,
    recommendation CLOB,
    generated_at   TIMESTAMP
)
"""


def ensure_table(cur):
    cur.execute("SELECT COUNT(*) FROM user_tables WHERE table_name = 'ISSUE_EXPLANATIONS'")
    if cur.fetchone()[0] == 0:
        cur.execute(CREATE_TABLE)
        print("Created issue_explanations table.")


def fetch_groups(cur):
    cur.execute("""
        SELECT check_name, severity, COUNT(*) AS cnt,
               MIN(metric_value) AS mn, MAX(metric_value) AS mx,
               MIN(threshold_value) AS thr
        FROM   dq_issues
        GROUP  BY check_name, severity
        ORDER  BY check_name, severity
    """)
    cols = [c[0].lower() for c in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def fetch_examples(cur, check_name, severity, n=3):
    cur.execute("""
        SELECT entity_ref, metric_value, detail
        FROM   dq_issues
        WHERE  check_name = :1 AND severity = :2
        FETCH FIRST :3 ROWS ONLY
    """, [check_name, severity, n])
    return [f"- {ref} (metric={val}): {det}" for ref, val, det in cur.fetchall()]


def ask_claude(client, group, examples):
    prompt = f"""A data-quality check flagged issues in an Indian quick-commerce supply-chain data platform.

Check: {group['check_name']}
Severity: {group['severity']}
Affected records: {int(group['cnt'])}
Rule threshold: {group['thr']}
Metric range across affected records: {group['mn']} to {group['mx']}
Example records:
{chr(10).join(examples)}

In 2-3 sentences, explain what this issue means for the business. Then give one
concrete recommended action. Respond ONLY with JSON, no markdown, using exactly
these keys: {{"explanation": "...", "recommendation": "..."}}"""

    resp = client.messages.create(
        model=MODEL,
        max_tokens=500,
        system="You are a supply-chain data-quality analyst. Be concise, concrete and business-focused.",
        messages=[{"role": "user", "content": prompt}],
    )
    text = resp.content[0].text.strip()
    if text.startswith("```"):
        text = text.strip("`").lstrip("json").strip()
    try:
        data = json.loads(text)
        return data.get("explanation", text), data.get("recommendation", "")
    except json.JSONDecodeError:
        return text, ""


def main():
    client = anthropic.Anthropic()
    conn = get_connection()
    cur = conn.cursor()
    ensure_table(cur)

    groups = fetch_groups(cur)
    if not groups:
        print("No issues found in dq_issues -- nothing to explain.")
        return

    written = skipped = 0
    for g in groups:
        group_key = hashlib.md5(f"{g['check_name']}|{g['severity']}".encode()).hexdigest()
        content_hash = hashlib.md5(
            f"{g['check_name']}|{g['severity']}|{int(g['cnt'])}|{g['mn']}|{g['mx']}".encode()
        ).hexdigest()

        cur.execute("SELECT content_hash FROM issue_explanations WHERE group_key = :1", [group_key])
        row = cur.fetchone()
        if row and row[0] == content_hash:
            print(f"  cached  {g['check_name']} / {g['severity']}")
            skipped += 1
            continue

        examples = fetch_examples(cur, g["check_name"], g["severity"])
        explanation, recommendation = ask_claude(client, g, examples)

        cur.execute("DELETE FROM issue_explanations WHERE group_key = :1", [group_key])
        cur.execute("""
            INSERT INTO issue_explanations
                (group_key, check_name, severity, issue_count, content_hash,
                 explanation, recommendation, generated_at)
            VALUES (:1, :2, :3, :4, :5, :6, :7, systimestamp)
        """, [group_key, g["check_name"], g["severity"], int(g["cnt"]),
              content_hash, explanation, recommendation])
        conn.commit()
        print(f"  wrote   {g['check_name']} / {g['severity']}  ({int(g['cnt'])} issues)")
        written += 1

    print(f"\nDone. {written} written, {skipped} cached.")
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
