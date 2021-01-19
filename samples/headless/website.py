import mimetypes
import os
from pathlib import Path

from coworks import TechMicroService
from coworks.cws.runner import CwsRunner
from jinja2 import Environment, FileSystemLoader, select_autoescape

from config import DevConfig, LocalConfig
from cosmicjs import CosmicCmsClient


class WebsiteMicroService(TechMicroService):

    def __init__(self, env=None, **kwargs):
        super().__init__(name="website-handless", **kwargs)
        self.jinja_env = env or Environment(
            loader=FileSystemLoader("templates"),
            autoescape=select_autoescape(['html', 'xml'], default_for_string=True)
        )
        self.cosmic_client = self.workspace = None

        @self.before_first_activation
        def init(*args):
            self.workspace = os.getenv('WORKSPACE')
            self.cosmic_client = CosmicCmsClient()

    def get(self):
        assets_url = os.getenv('ASSETS_URL')
        home = self.cosmic_client.get_home()
        template_filename = 'home.j2'
        template = self.jinja_env.get_template(template_filename)
        headers = {'Content-Type': 'text/html; charset=utf-8'}
        return template.render(assets_url=assets_url, **home), 200, headers

    def get_(self, slug):
        assets_url = os.getenv('ASSETS_URL')
        home = self.cosmic_client.get_home()
        data = self.cosmic_client.get_slug(slug)
        template_filename = 'product.j2'
        template = self.jinja_env.get_template(template_filename)
        headers = {'Content-Type': 'text/html; charset=utf-8'}
        return template.render(assets_url=assets_url, **home, **data), 200, headers

    def get_form(self):
        assets_url = os.getenv('ASSETS_URL')
        home = self.cosmic_client.get_home()
        template_filename = 'form.j2'
        template = self.jinja_env.get_template(template_filename)
        headers = {'Content-Type': 'text/html; charset=utf-8'}
        return template.render(assets_url=assets_url, **home), 200, headers

    def get_assets_css(self, filename):
        return self.return_file(f'assets/css/{filename}')

    def get_assets_css_images(self, filename):
        return self.return_file(f'assets/css/images/{filename}')

    def get_assets_js(self, filename):
        return self.return_file(f'assets/js/{filename}')

    def get_assets_webfonts(self, filename):
        return self.return_file(f'assets/webfonts/{filename}')

    def get_images(self, filename):
        return self.return_file(f'images/{filename}')

    @staticmethod
    def return_file(file):
        file = Path.cwd() / file
        mt = mimetypes.guess_type(file)
        content = file.read_bytes()
        try:
            return content.decode('utf-8'), 200, {'Content-Type': mt[0]}
        except:
            return content, 200, {'Content-Type': mt[0]}


app = WebsiteMicroService(configs=[LocalConfig(), DevConfig()])
CwsRunner(app)

if __name__ == '__main__':
    app.execute("run", project_dir='.', module='website', workspace='local')
