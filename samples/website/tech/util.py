from flask import render_template


def render_html_template(*args, **kwargs):
    return render_template(*args, **kwargs), 200, {'content-type': 'text/html; charset=utf-8'}
