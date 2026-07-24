import hashlib
import json

from app import venue_reconciliation as compatibility
from app import venue_reconciliation_schemas as schemas
from app.main import app

MODEL_NAMES = ['VenueReconciliationRunRequest', 'VenueReconciliationRunResponse', 'ReconciliationDifferenceResponse', 'ResolveDifferenceRequest', 'OrderVenueReconciliationResponse']
EXPECTED_MODEL_SCHEMA_HASHES = {
    "OrderVenueReconciliationResponse": "8688cabfd1ffb29657c3ce59bb9ea382ad35417b0a52dc11a23f053c9e922360",
    "ReconciliationDifferenceResponse": "6579651679e172b240a7ce5882e28b6557a8d76f5536d8f17d7ff8b0e70ced15",
    "ResolveDifferenceRequest": "9679c1b4f03c2e557e5a26e0c5b36a464357360f1e1963d38211c3808ea8a7bf",
    "VenueReconciliationRunRequest": "20d1461a0e1a9d78a15c51f93d8e2b0bb08e29e778f7ddbe1405b0e76f9b8491",
    "VenueReconciliationRunResponse": "58b990e29d852dd566f67534f6a3211983cc7b8e9430d033b6117e02f35a0a72"
}
EXPECTED_RECONCILIATION_OPENAPI_HASH = "01a6a928c38eeafa7a0f059732b2499ffe0545cdd0b77a62cae388794c097c0b"


def canonical_hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def test_compatibility_exports_are_identical_schema_objects() -> None:
    for name in MODEL_NAMES:
        assert getattr(compatibility, name) is getattr(schemas, name)
    assert compatibility.DifferenceType is schemas.DifferenceType
    assert compatibility.DifferenceStatus is schemas.DifferenceStatus


def test_model_json_schemas_match_pre_extraction_goldens() -> None:
    actual = {
        name: canonical_hash(getattr(schemas, name).model_json_schema())
        for name in MODEL_NAMES
    }

    assert actual == EXPECTED_MODEL_SCHEMA_HASHES


def test_reconciliation_openapi_fragment_matches_pre_extraction_golden() -> None:
    openapi = app.openapi()
    fragment = {
        "schemas": {
            name: openapi["components"]["schemas"][name]
            for name in MODEL_NAMES
        },
        "paths": {
            path: value
            for path, value in openapi["paths"].items()
            if "reconciliation" in path
        },
    }

    assert canonical_hash(fragment) == EXPECTED_RECONCILIATION_OPENAPI_HASH
