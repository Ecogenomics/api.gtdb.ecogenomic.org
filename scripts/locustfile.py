import time
from locust import HttpUser, task, between


class HelloWorldUser(HttpUser):
    wait_time = between(1, 5)

    @task
    def hello_world(self):
        self.client.get("/fastani/config")
        self.client.get("/taxonomy/count")
        self.client.get("/taxonomy/not-in-literature")
        self.client.get("/species/all")
        self.client.get("/genomes/all")

