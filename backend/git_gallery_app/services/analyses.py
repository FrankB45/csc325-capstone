# ---- new file: backend/git_gallery_app/services/analyses.py ----
# MongoDB from compose.yaml (mongodb://localhost:27017/, db git_gallery).
# pymongo is imported lazily so Django checks and tests don't need it or Mongo.
_collection = None


def _get_collection():
    global _collection
    if _collection is None:
        from pymongo import MongoClient

        _collection = MongoClient("mongodb://localhost:27017/")["git_gallery"]["analyses"]
    return _collection


def save_analysis(snapshot: dict) -> dict:
    """Insert the immutable snapshot and return it with a string id."""
    doc = dict(snapshot)
    result = _get_collection().insert_one(doc)
    doc.pop("_id", None)
    doc["id"] = str(result.inserted_id)
    return doc