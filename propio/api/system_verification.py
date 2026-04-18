from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import frappe

WORKSPACE_ALIASES: dict[str, list[str]] = {
    "Portfolio": ["Property Hub"],
    "Leasing": ["Leasing Desk"],
    "Billing": ["Finance Hub"],
    "Collections": ["Collections Desk"],
    "Owners": ["Owner Hub"],
    "Operations": ["Maintenance Desk"],
}


def _fixture_root() -> Path:
    return Path(frappe.get_app_path("propio", "fixtures"))


def _read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _as_records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if isinstance(payload, dict):
        return [payload]
    return []


def _collect_from_fixture_file(path: Path, key: str = "name") -> list[str]:
    if not path.exists():
        return []
    data = _read_json(path)
    out: list[str] = []
    for row in _as_records(data):
        value = row.get(key)
        if value:
            out.append(str(value))
    return sorted(set(out))


def _collect_names_from_dir(path: Path, key: str = "name") -> list[str]:
    if not path.exists():
        return []
    out: list[str] = []
    for file in sorted(path.glob("*.json")):
        out.extend(_collect_from_fixture_file(file, key=key))
    return sorted(set(out))


def _check_exists(doctype: str, names: list[str]) -> dict[str, list[str]]:
    present: list[str] = []
    missing: list[str] = []
    mapped: list[str] = []
    for name in names:
        if frappe.db.exists(doctype, name):
            present.append(name)
            continue

        if doctype == "Workspace":
            aliases = WORKSPACE_ALIASES.get(name, [])
            resolved = next((alias for alias in aliases if frappe.db.exists("Workspace", alias)), None)
            if resolved:
                present.append(resolved)
                mapped.append(f"{name} -> {resolved}")
                continue

        missing.append(name)
    return {"present": present, "missing": missing, "mapped": mapped}


def _print_block(title: str, found: list[str], missing: list[str], mapped: list[str] | None = None) -> None:
    print(f"\n{title}")
    print("-" * len(title))
    print(f"found: {len(found)}")
    if mapped:
        print(f"mapped aliases: {len(mapped)}")
        for item in mapped:
            print(f"  * {item}")
    print(f"missing: {len(missing)}")
    if missing:
        for item in missing:
            print(f"  - {item}")


@frappe.whitelist()
def run_full_verification() -> dict[str, Any]:
    """Verify DB records against fixture files committed in this app."""
    root = _fixture_root()

    expected = {
        "Workspace": _collect_names_from_dir(root / "workspace"),
        "Number Card": _collect_from_fixture_file(root / "number_card.json"),
        "Dashboard Chart": _collect_from_fixture_file(root / "dashboard_chart.json"),
        "Workflow": _collect_from_fixture_file(root / "workflow.json"),
        "Report": _collect_from_fixture_file(root / "report.json"),
        "DocType": _collect_names_from_dir(root / "doctype"),
        "Role": _collect_from_fixture_file(root / "role.json"),
    }

    results: dict[str, Any] = {}
    total_missing = 0
    total_expected = 0

    print("\n" + "=" * 64)
    print("PROPIO FIXTURE ALIGNMENT VERIFICATION")
    print("=" * 64)

    for doctype, names in expected.items():
        check = _check_exists(doctype, names)
        results[doctype] = {
            "expected_count": len(names),
            "present_count": len(check["present"]),
            "missing_count": len(check["missing"]),
            "mapped_count": len(check.get("mapped", [])),
            "mapped": check.get("mapped", []),
            "missing": check["missing"],
        }
        total_expected += len(names)
        total_missing += len(check["missing"])
        _print_block(
            f"{doctype} Verification",
            check["present"],
            check["missing"],
            check.get("mapped", []),
        )

    # Critical sanity checks that caused recent issues.
    critical = {
        "Payment Intake": frappe.db.exists("DocType", "Payment Intake"),
        "Payment Intake Workflow": frappe.db.exists("Workflow", "Payment Intake Workflow"),
        "Lease Workflow": frappe.db.exists("Workflow", "Lease Workflow"),
    }
    results["critical"] = critical

    print("\nCritical Checks")
    print("---------------")
    for label, ok in critical.items():
        print(f"{'OK' if ok else 'FAIL'}: {label}")

    results["summary"] = {
        "expected_records": total_expected,
        "missing_records": total_missing,
        "status": "pass" if total_missing == 0 else "needs_attention",
    }

    print("\n" + "=" * 64)
    print(
        f"SUMMARY: expected={total_expected}, missing={total_missing}, "
        f"status={results['summary']['status']}"
    )
    print("=" * 64 + "\n")

    return results
