from coworks.blueprint.admin_blueprint import Admin
from coworks.tech.directory import DirectoryMicroService

app = DirectoryMicroService()
app.register_blueprint(Admin(), url_prefix='/admin')
