# Pattern: see .smoke-scratch/README.md
"""feature-17 / multi-file import / API batch contract."""
import pathlib
import tempfile

from app import create_app


SOURCE_A = "@feat_a\nFeature: A\n  @scenario_a\n  Scenario: Alpha\n    Given alpha\n"
SOURCE_B = (
    "# enum.priority: high\n@feat_b\nFeature: B\n"
    "  @scenario_b\n  Scenario: Beta\n    Given beta\n"
)


def make_client():
    root = tempfile.TemporaryDirectory()
    app = create_app(data_root=pathlib.Path(root.name))
    storage = app.extensions["storage"]
    storage.create_folder(["project"])
    storage.create_folder(["project", "module"])
    return root, app.test_client(), storage


# --- P1: preview flattens valid sources in source/scenario order ------------
root, client, _ = make_client()
try:
    response = client.post(
        "/api/files/import/preview",
        json={
            "sources": [
                {"name": "same.feature", "source": SOURCE_A},
                {"name": "same.feature", "source": SOURCE_B},
            ]
        },
    )
    assert response.status_code == 200, f"P1: {response.status_code}: {response.get_json()}"
    data = response.get_json()
    assert not data["errors"], f"P1: unexpected errors: {data!r}"
    assert [item["source_name"] for item in data["scenarios"]] == [
        "same.feature",
        "same.feature",
    ], f"P1: source order lost: {data!r}"
    assert [item["source_index"] for item in data["scenarios"]] == [0, 1], (
        f"P1: source-index association lost: {data!r}"
    )
    assert [item["scenario_name"] for item in data["scenarios"]] == ["Alpha", "Beta"], (
        f"P1: scenario order lost: {data!r}"
    )
    assert data["scenarios"][0]["feature_tags"] == ["feat_a"], f"P1: tags: {data!r}"
    assert data["enums_present"] is True, f"P1: enum flag: {data!r}"
    assert data["enum_sources"] == [
        {"source_index": 1, "source_name": "same.feature"}
    ], f"P1: enum source context: {data!r}"
    print("PASS  P1: batch preview preserves order with duplicate source labels")
finally:
    root.cleanup()


# --- P2: preview collects every source-specific blocking error --------------
root, client, storage = make_client()
try:
    response = client.post(
        "/api/files/import/preview",
        json={
            "sources": [
                {"name": "wrong.txt", "source": SOURCE_A},
                {
                    "name": "rule.feature",
                    "source": "Feature: f\n  Rule: r\n    Scenario: x\n      Given x\n",
                },
                {"name": "empty.feature", "source": "Feature: empty\n"},
            ]
        },
    )
    assert response.status_code == 200, f"P2: {response.status_code}: {response.get_json()}"
    errors = response.get_json()["errors"]
    assert [error["code"] for error in errors] == [
        "invalid_file_type",
        "parse_error",
        "no_scenarios",
    ], f"P2: errors not collected in source order: {errors!r}"
    assert not storage.list_folder(["project", "module"])["features"], (
        "P2: preview must not write cases"
    )
    print("PASS  P2: batch preview collects type, parse, and empty-source errors")
finally:
    root.cleanup()


# --- P3: server enforces both batch limits ----------------------------------
root, client, _ = make_client()
try:
    response = client.post(
        "/api/files/import/preview",
        json={
            "sources": [
                {"name": f"{index}.feature", "source": SOURCE_A}
                for index in range(21)
            ]
        },
    )
    assert response.status_code == 400, f"P3a: {response.status_code}"
    assert "20-file" in response.get_json()["error"]["message"], f"P3a: {response.get_json()}"

    response = client.post(
        "/api/files/import/preview",
        json={"sources": [{"name": "large.feature", "source": "#" * (3 * 1024 * 1024 + 1)}]},
    )
    assert response.status_code == 400, f"P3b: {response.status_code}"
    assert "MB total" in response.get_json()["error"]["message"], f"P3b: {response.get_json()}"
    print("PASS  P3: batch rejects more than 20 files or 3 MB total")
finally:
    root.cleanup()


# --- C1: one commit writes all source cases in flattened order --------------
root, client, storage = make_client()
try:
    response = client.post(
        "/api/files/import",
        json={
            "parent": "project/module",
            "sources": [
                {"name": "first.feature", "source": SOURCE_A},
                {"name": "second.feature", "source": SOURCE_B},
            ],
            "names": ["alpha", "beta"],
        },
    )
    assert response.status_code == 201, f"C1: {response.status_code}: {response.get_json()}"
    assert response.get_json()["created"] == [
        "project/module/alpha.feature",
        "project/module/beta.feature",
    ], f"C1: created order: {response.get_json()}"
    assert [item["scenario_name"] for item in storage.list_folder(["project", "module"])["features"]] == [
        "Alpha",
        "Beta",
    ], "C1: cases not persisted"
    print("PASS  C1: batch commit writes flattened cases in one destination")
finally:
    root.cleanup()


# --- C2: cross-source duplicate scenario aborts the whole batch -------------
root, client, storage = make_client()
try:
    response = client.post(
        "/api/files/import",
        json={
            "parent": "project/module",
            "sources": [
                {"name": "first.feature", "source": SOURCE_A},
                {
                    "name": "duplicate.feature",
                    "source": "Feature: duplicate\n  Scenario: alpha\n    Given duplicate\n",
                },
            ],
            "names": ["alpha", "duplicate"],
        },
    )
    assert response.status_code == 422, f"C2: {response.status_code}: {response.get_json()}"
    assert response.get_json()["error"]["code"] == "import_validation_error", f"C2: {response.get_json()}"
    assert not storage.list_folder(["project", "module"])["features"], (
        "C2: cross-source conflict must write zero cases"
    )
    print("PASS  C2: cross-source scenario conflict aborts with zero writes")
finally:
    root.cleanup()


# --- C3: commit revalidates source errors and keeps legacy body working ------
root, client, storage = make_client()
try:
    response = client.post(
        "/api/files/import",
        json={
            "parent": "project/module",
            "sources": [
                {"name": "valid.feature", "source": SOURCE_A},
                {
                    "name": "bad.feature",
                    "source": "Feature: f\n  Rule: r\n    Scenario: x\n      Given x\n",
                },
            ],
            "names": ["alpha"],
        },
    )
    assert response.status_code == 422, f"C3a: {response.status_code}: {response.get_json()}"
    assert not storage.list_folder(["project", "module"])["features"], (
        "C3a: invalid source must abort the whole batch"
    )

    response = client.post(
        "/api/files/import",
        json={"parent": "project/module", "source": SOURCE_A, "names": ["legacy"]},
    )
    assert response.status_code == 201, f"C3b: legacy body regressed: {response.get_json()}"
    print("PASS  C3: commit revalidates batch errors and preserves legacy source body")
finally:
    root.cleanup()
