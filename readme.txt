# Flask-Security 기본 정보 정리

## 1. 기본 라우터
| URL         | 기능             |
| ----------- | ---------------- |
| `/login`    | <span style="color:blue">로그인</span> |
| `/register` | <span style="color:blue">회원가입</span> |
| `/logout`   | <span style="color:red">로그아웃</span> |
| `/reset`    | <span style="color:orange">비밀번호 재설정</span> |
| `/change`   | <span style="color:orange">비밀번호 변경</span> |

> <span style="color:green">Tip:</span> 로그인/회원가입 페이지를 커스터마이징 하고 싶다면, 동일한 경로로 템플릿을 만들어 덮어쓸 수 있습니다.

## 2. 설치 관련
```bash
pip install -r requirements.txt
```


## 3. 보안 관리

- 비밀번호 초기화, 세션 강제 종료 등 <span style="color:red">보안 관리용 기능</span>

- 고유값 보장이 필수 → <span style="color:blue">UUID 사용 추천</span> (충돌 가능성 거의 없음)

## 4. Admin 생성

- __init__.py에서 <span style="color:blue">Admin 생성</span>

- Admin 관련 설정을 변경하고 싶다면 <span style="color:red">33번 줄</span> 참고