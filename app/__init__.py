import string


username_chars = string.ascii_lowercase + string.ascii_uppercase + string.digits + ' -_'
def validate_username(username):
    if len(username) > 12:
        return False
    if username.strip(username_chars):
        return False
    return True


def default_n_neighbors(split):
    return {'all': 5, 'cb': 15, 'noncb': 5}[split]


def default_min_dist(split):
    return {'all': 0.25, 'cb': 0.25, 'noncb': 0.00}[split]


def skill_upper(skill):
    return skill[0].upper() + skill[1:]


def format_skill(skill):
    return f"{skill_upper(skill)} level"


def get_color_label(skill):
    return f"{skill_upper(skill)}\nlevel"


def get_color_range(skill):
    return [500, 2277] if skill == 'total' else [1, 99]


def get_point_size(ptsize_name):
    return {'small': 1, 'medium': 2, 'large': 3}[ptsize_name]


def get_level_tick_marks(skill):
    if skill == 'total':
        return {i: str(i) for i in [1, 250, 500, 750, 1000, 1250, 1500, 1750, 2000, 2277]}
    else:
        return {i: str(i) for i in [1, 10, 20, 30, 40, 50, 60, 70, 80, 90, 99]}
