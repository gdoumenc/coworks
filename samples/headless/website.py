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
        super().__init__(name="website-handless", **kwargs)
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
        return self.render(template)

    @entry
    def get_produit(self, slug):
        template_filename = 'product.j2'
        template = self.jinja_env.get_template(template_filename)
        data = self.cosmic_client.object_metafields(slug)
        return self.render(template, **data)

    @entry
    def get_assets(self, folder, filename):
        file = Path.cwd() / 'assets' / folder / filename
        return self.get_file_content(file)

    @entry
    def get_assets_(self, folder, subfolder, filename):
        file = Path.cwd() / 'assets' / folder / subfolder / filename
        return self.get_file_content(file)

    @entry
    def get_form(self):
        template_filename = 'form.j2'
        template = self.jinja_env.get_template(template_filename)
        return self.render(template)

    @property
    def home(self):
        response = self.cosmic_client.object('home')
        home = {k: v for d in response['metafields'] for k, v in self.cosmic_client.to_dict(d).items()}
        product_objects = self.cosmic_client.objects('products')
        products = [self.cosmic_client.to_dict(d) for d in product_objects]
        reference_objects = self.cosmic_client.objects('references')
        references = [self.cosmic_client.to_dict(d) for d in reference_objects]
        banner_objects = self.cosmic_client.objects('banners')
        banners = [self.cosmic_client.to_dict(d) for d in banner_objects]
        post_objects = self.cosmic_client.objects('posts')
        posts = [self.cosmic_client.to_dict(d) for d in post_objects]
        return {
            'home': home,
            'products': products,
            'product_ids': [obj['slug'] for obj in products],
            'references': references,
            'reference_ids': [obj['slug'] for obj in references],
            'banners': banners,
            'banner_ids': [obj['slug'] for obj in banners],
            'posts': posts,
            'post_ids': [obj['slug'] for obj in posts],
        }

    def render(self, template, **data):
        assets_url = os.getenv('ASSETS_URL')
        headers = {'Content-Type': 'text/html; charset=utf-8'}
        root = self.config.root
        return template.render(assets_url=assets_url, root=root, **self.home, **data), 200, headers

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
    app.execute("run", project_dir='.', module='website', workspace='local')
