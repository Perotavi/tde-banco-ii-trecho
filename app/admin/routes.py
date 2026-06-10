from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/")
@login_required
def painel_admin():
    if not current_user.tem_perfil("admin"):
        flash("Acesso restrito a administradores.", "danger")
        return redirect(url_for("posts.feed"))

    return render_template("admin.html")