from flask import Blueprint, redirect, url_for, render_template
from flask_security import current_user, login_required, roles_required

bp = Blueprint('auth', __name__, url_prefix='/auth')


# 🔐 로그인 후 이동할 기본 페이지
@bp.route('/user')
@login_required
def user_profile():
    return render_template("auth/user_profile.html", user=current_user)


# 🔐 관리자 전용 페이지
@bp.route('/admin')
@roles_required('admin')
def admin_dashboard():
    return render_template("auth/admin_dashboard.html",user=current_user)


#  로그인 후 권한에 따라 자동 분기
@bp.route('/redirect')
@login_required
def redirect_by_role():
    if current_user.has_role('admin'):
        return redirect(url_for('auth.admin_dashboard'))
    return redirect(url_for('auth.user_profile'))
