import mimetypes
import os
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from config import DevConfig, LocalConfig
from cosmicjs import CosmicCmsClient
from coworks import TechMicroService, entry
from coworks.blueprint import Admin


class WebsiteMicroService(TechMicroService):

    def __init__(self, env=None, **kwargs):
        super().__init__(name="website-headless", **kwargs)
        self.jinja_env = env or Environment(
            loader=FileSystemLoader("templates"),
            autoescape=select_autoescape(['html', 'xml'], default_for_string=True)
        )
        self.cosmic_client = None

        @self.before_first_activation
        def init(*args):
            self.cosmic_client = CosmicCmsClient()

    @entry
    def get(self):
        template_filename = 'home.j2'
        template = self.jinja_env.get_template(template_filename)
        return self.render(template, **self.home)

    @entry
    def get_assets(self, folder, filename):
        file = Path.cwd() / 'assets' / folder / filename
        return self.get_file_content(file)

    @entry
    def get_form(self):
        template_filename = 'form.j2'
        template = self.jinja_env.get_template(template_filename)
        return self.render(template)

    @property
    def home(self):
        response = self.cosmic_client.object('home')
        home = {k: v for field in response['metafields'] for k, v in self.cosmic_client.to_dict(field).items()}
        return {
            'carousel': home.get('carousel'),
            'sections': home.get('sections'),
            'footer': home.get('footer'),
        }

    def render(self, template, **data):
        assets_url = os.getenv('ASSETS_URL')
        headers = {'Content-Type': 'text/html; charset=utf-8'}
        root = self.config.root
        return template.render(assets_url=assets_url, root=root, **data), 200, headers

    @staticmethod
    def get_file_content(file: Path):
        mt = mimetypes.guess_type(file)
        content = file.read_bytes()
        try:
            return content.decode('utf-8'), 200, {'Content-Type': mt[0]}
        except:
            return content, 200, {'Content-Type': mt[0]}


app = WebsiteMicroService(configs=[LocalConfig(), DevConfig()])
app.register_blueprint(Admin(), url_prefix='admin')

if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Command arg missing")
    elif sys.argv[1] == "run":
        app.execute("run", project_dir='.', module='website', workspace='local', service='app', auto_reload=True)
    elif sys.argv[1] == "deploy":
        app.execute("deploy", project_dir='.', module='website', workspace='prod', service='app')
