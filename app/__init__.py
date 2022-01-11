import string


valid_chars = string.ascii_lowercase + string.ascii_uppercase + string.digits + ' -_'


def validate_username(username):
    if len(username) > 12:
        return False
    if username.strip(valid_chars):
        return False
    return True


def get_level_marks(skill):
    if skill == 'total':
        return {i: str(i) for i in [1, 250, 500, 750, 1000, 1250, 1500, 1750, 2000, 2277]}
    else:
        return {i: str(i) for i in [1, 10, 20, 30, 40, 50, 60, 70, 80, 90, 99]}


def skill_pretty(skill):
    return skill[0].upper() + skill[1:].replace('_', ' ') + ' level'
