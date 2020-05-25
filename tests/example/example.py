import os
from collections import defaultdict

from coworks import TechMicroService
from coworks.cws import TerraformWriter


class TechMS(TechMicroService):
    """Technical microservice for the CoWorks tutorial example."""
    version = "1.2"
    values = defaultdict(int)

    def get(self, usage="test"):
        """Entrypoint for testing named parameter."""
        return f"Simple microservice for {usage}.\n"

    def get_value(self, index):
        """Entrypoint for testing positional parameter."""
        return f"{self.values[index]}\n"

    def put_value(self, index, value=0):
        self.values[index] = value
        return value

    def get_env(self):
        return f"Simple microservice for {os.getenv('test')}.\n"


# usefull for test info (don't remove)
tech_app = TechMS()
TerraformWriter(tech_app)

app = TechMS()

if __name__ == '__main__':
    app.run()
