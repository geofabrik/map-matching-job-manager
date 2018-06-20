class Job:
    def __init__(self, **kwargs):
        self.id = kwargs["id"]
        self.name = kwargs.get("name")
        self.status = kwargs.get("status")
        self.query_params = kwargs.get("query_params")
        self.created_at = kwargs.get("created_at", None)
        self.started_at = kwargs.get("started_at", None)
        self.finished_at = kwargs.get("finished_at", None)
        self.download_path = kwargs.get("download_path", None)
