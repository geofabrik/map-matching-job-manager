from datetime import datetime
from job_manager.job import Job

class JobList:
    def __init__(self):
        self.jobs = []

    def size(self):
        return len(self.jobs)

    def __iter__(self):
        return self.jobs.__iter__()

    def __len__(self):
        return len(self.jobs)

    def create_from_dict_list(input_list):
        """
        Return an instance of JobList created from a list of dicts.
        """
        job_list = JobList()
        for entry in input_list:
            job_list.add(Job(**entry))
        return job_list

    def add(self, job):
        self.jobs.append(job)

    def json_serialize(d):
        if isinstance(d, datetime):
            return d.strftime("%Y-%m-%dT%H:%M:%SZ")
        if isinstance(d, (Job, JobList)):
            return d.__dict__
        raise TypeError("Type %s not serializable".format(type(obj)))
