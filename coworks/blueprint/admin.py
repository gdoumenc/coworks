from coworks import Blueprint


class Admin(Blueprint):

    def get_introspect(self):
        return self.current_request.to_dict()

# @admin.route('/introspect')
# def foo():
#     return admin.current_request.to_dict()
