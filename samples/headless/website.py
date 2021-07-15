import mimetypes
import os
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from cosmicjs import CosmicCmsClient
from coworks import TechMicroService, entry
from coworks.blueprint import Admin


class WebsiteMicroService(TechMicroService):

    def __init__(self, env=None, **kwargs):
        super().__init__(name="sample-headless-microservice", **kwargs)
        self.jinja_env = env or Environment(
            loader=FileSystemLoader("templates"),
            autoescape=select_autoescape(['j2', 'html', 'xml'], default_for_string=True)
        )
        self.cosmic_client = None

        @self.before_first_activation
        def init(*args):
            self.cosmic_client = CosmicCmsClient()

    def auth(self, auth_request):
        return True

    @entry
    def get(self):
        """Entry for the home page."""
        template_filename = 'home.j2'
        template = self.jinja_env.get_template(template_filename)

        response = self.cosmic_client.object('home')
        home = self.cosmic_client.fields(response)

        return self.render(template, **home)

    @entry
    def get_biere(self, name=None):
        """Entry for the beer (all or one specific)."""
        template_filename = 'one-beer.j2' if name else 'all-beer.j2'
        template = self.jinja_env.get_template(template_filename)

        if name is None:
            return self.render(template)

        beer = self.get_beers(name)
        return self.render(template, beer=beer)

    @entry
    def get_assets(self, folder, filename):
        """Access for all assets."""
        file = Path.cwd() / 'assets' / folder / filename
        mt = mimetypes.guess_type(file)
        content = file.read_bytes()
        try:
            return content.decode('utf-8'), 200, {'Content-Type': mt[0]}
        except UnicodeDecodeError:
            return content, 200, {'Content-Type': mt[0]}

    @entry
    def get_form(self):
        template_filename = 'form.j2'
        template = self.jinja_env.get_template(template_filename)
        return self.render(template)

    def get_beers(self, name=None):
        response = self.cosmic_client.objects('bieres')
        if name is None:
            return {resp['slug']: self.cosmic_client.fields(resp) for resp in response}
        for resp in response:
            if resp['slug'] == name:
                return self.cosmic_client.fields(resp)

    def render(self, template, **data):
        response = self.cosmic_client.objects('bieres')
        beers = self.get_beers()
        data['footer'] = ""
        assets_url = os.getenv('ASSETS_URL')
        headers = {'Content-Type': 'text/html; charset=utf-8'}
        return template.render(assets_url=assets_url, root='.', beers=beers, **data), 200, headers


app = WebsiteMicroService()
app.register_blueprint(Admin(), url_prefix='admin')

if __name__ == '__main__':
    app.execute("run", project_dir='.', module='website', workspace='local', auto_reload=True,
                authorization_value='test')
