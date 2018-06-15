class Job:
    def __init__(self, **kwargs):
        self.id = kwargs["id"]
        self.name = kwargs.get("name")
        self.status = kwargs.get("status")
        self.query_params = kwargs.get("query_params")

    def json_serialize(self):
        return self.__dict__
