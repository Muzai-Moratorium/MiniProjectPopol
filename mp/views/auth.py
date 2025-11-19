from flask import Blueprint, redirect, url_for, render_template, request,flash
from flask_security import current_user, login_required, roles_required, hash_password
from datetime import date
from ..models import db,User
bp = Blueprint('auth', __name__, url_prefix='/auth')

# 회원가입

@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # 폼 데이터 가져오기
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        password_confirm = request.form.get("password_confirm")
        birth_str = request.form.get("birth")  # YYYY-MM-DD 형식
        mobile1 = request.form.get("mobile1")
        mobile2 = request.form.get("mobile2")
        mobile3 = request.form.get("mobile3")
        mobile = f"{mobile1}{mobile2}{mobile3}"

        # birth를 datetime.date 객체로 변환
        birth = date.fromisoformat(birth_str)

        # 1 비밀번호 확인
        if password != password_confirm:
            flash("비밀번호가 일치하지 않습니다.")
            return render_template("auth/register.html")

        # 2 이메일 중복 체크
        if User.query.filter_by(email=email).first():
            flash("이미 존재하는 이메일입니다.")
            return render_template("auth/register.html")

        # 3 모바일 중복 체크
        if User.query.filter_by(mobile=mobile).first():
            flash("이미 등록된 휴대폰 번호입니다.")
            return render_template("auth/register.html")

        # User 생성
        new_user = User(
            name=name,
            email=email,
            password=hash_password(password),
            birth=birth,
            mobile=mobile,
            active=True
        )

        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for("index.index"))  # 가입 후 로그인 페이지로 이동

    # GET 요청일 경우 템플릿 렌더링
    return render_template("auth/register.html")

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
