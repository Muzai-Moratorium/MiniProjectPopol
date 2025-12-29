from flask import Blueprint, redirect, url_for, render_template

bp = Blueprint("massage",__name__)

@bp.route("/massage")
def massage():
    return render_template("massage.html")
