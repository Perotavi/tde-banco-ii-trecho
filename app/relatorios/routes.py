from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user

relatorios_bp = Blueprint("relatorios", __name__, url_prefix="/relatorios")


@relatorios_bp.route("/")
@login_required
def painel_relatorios():
    if not current_user.tem_perfil("analista", "admin"):
        flash("Acesso restrito a analistas e administradores.", "danger")
        return redirect(url_for("posts.feed"))

    return render_template("relatorios.html")