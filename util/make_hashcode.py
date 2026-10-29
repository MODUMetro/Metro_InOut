import hashlib

# 원하는 비밀번호를 입력받는 변수
new_password = "1a2a3a4a5a"

hash_value = hashlib.sha256(new_password.encode()).hexdigest()

# 출력 결과: new_password를 hash code로 변화
print(f"해시값: {hash_value}")