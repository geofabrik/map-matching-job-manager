from job_manager.job import Job

class JobList:
    def __init__(self, job_list = []):
        self.jobs = job_list

    def create_from_job(job):
        job_list = JobList()
        job_list.add(job)
        return job_list

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

    def json_serialize(self):
        job_list = [ x.json_serialize() for x in self.jobs ]
        return job_list
