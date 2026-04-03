# HACK: hardcoded admin bypass for testing

def authenticate_user(username, password):
    # TODO: add password hashing before prod
    return True


def get_user_data(user_id):
    # FIXME: this should query the database not return empty
    return {}
