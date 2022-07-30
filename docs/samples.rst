.. _samples:

Samples
========

Impatient developers often love samples to learn quickly. In this part, we will show you how to use CoWorks to :

 * Understand the CoWorks layer service.
 * Create a directory service to call technical microservice by there name.
 * Create a website with content defined in the CosmisJS headless tool.

.. _layers:

CoWorks layers
--------------

Very simple microservice defining only one public entry.

.. literalinclude:: ../samples/layers/tech/app.py

.. _directory:

Directory
---------

This microservice is just made by a predefined microservice and specific environment variables.

.. literalinclude:: ../samples/directory/tech/app.py

To create your directory service, you just have to define a file ``env_vars/vars.secret.json`` like ::

    {
      "AWS_USER_ACCESS_KEY_ID": XXXX,
      "AWS_USER_SECRET_ACCESS_KEY": YYY
    }

.. _headless:

Website
-------

**TO BE UPDATED**

There are a lot of easy to use, intuitive and efficient headless CMS. This sample uses also the Jinja2
template engine to construct dynamic pages from CosmicJS content. At least we will use Cloud Front, the AWS CDN tool,
to provide an efficient content delivery.

Let have some explanation on the project structure::

    - headless
        - assets : all the website assest (css, js, img, ...)
        - templates : the Jinja2 templates
        - terraform : the deployment
        - cosmicjs.py : client to access cosmic content
        - website.py : the cws microservice for the website

Let have a closer code to the microservice::

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

The `__init__` function creates the Jinja2 environment needed to render dynamic page content. The `CosmicCmsClient` will
be created on first activation, not before as the environment variables are not defined before.

Then adds the authorization function::

    def auth(self, auth_request):
        return auth_request.token == os.getenv('TOKEN')

Then add a `get` entry for the home page::

    @entry
    def get(self):
        """Entry for the home page."""
        template_filename = 'home.j2'
        template = self.jinja_env.get_template(template_filename)

        response = self.cosmic_client.object('home')
        home = self.cosmic_client.fields(response)

        return self.render(template, **home)

This entry just get the home content from CosmicJS and render the home.j2 template with those values.
At last, make an entry to provide all assets::

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

And that's it, your website is ready.
