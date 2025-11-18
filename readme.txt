플라스크 시큐리티의 기본 라우터
| URL         | 기능       |
| ----------- | -------- |
| `/login`    | 로그인      |
| `/register` | 회원가입     |
| `/logout`   | 로그아웃     |
| `/reset`    | 비밀번호 재설정 |
| `/change`   | 비밀번호 변경  |

pip install 해야할것들

flask
flask_sqlalchemy
flask_security-too (플라스크 시큐리티 최신버전이자 안정적임)
email-validator
uuid (fs_uniquifier는 각 유저 세션을 고유하게 식별해야 함
비밀번호 초기화, 세션 강제 종료 등 보안 관리용으로 쓰임
고유값 보장이 필수 → UUID 사용하면 겹칠 가능성이 거의 없음)

로그인,회원가입 페이지를 변경하고싶으면 동일한 경로로 템플릿 만들면 덮어쓸수있음 

admin은 __init__.py에서 생성이 됩니다 여기서 변경하고싶으면 변경하세요 33번줄
