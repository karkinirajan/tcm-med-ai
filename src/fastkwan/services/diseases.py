class DiseaseStore:
    """Looks a disease up by (partial) name in MongoDB Atlas with an autocomplete search."""

    def __init__(self, collection, search_index):
        self.collection = collection
        self.search_index = search_index

    def find(self, name):
        pipeline = [
            {
                "$search": {
                    "index": self.search_index,
                    "autocomplete": {"query": name, "path": "病名"},
                }
            },
            {"$limit": 1},
            {"$project": {"_id": 0, "病名": 1, "预防与调摄": 1}},
        ]
        found = list(self.collection.aggregate(pipeline))
        return found[0] if found else None
