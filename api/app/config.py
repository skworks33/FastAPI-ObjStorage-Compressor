import os


# 共通設定
class BaseConfig:
    CONN_LIMIT = 100  # 並列接続上限数


# 開発環境用設定
class DevelopmentConfig(BaseConfig):
    OS_AUTH_URL = ""  # OpenStack認証URL
    OS_SWIFT_INT_URL = ""  # 内部向けSwiftエンドポイントURL
    OS_SWIFT_EXT_URL = ""  # 外部向けSwiftエンドポイントURL
    OS_SWIFT_COMP_MGR_PROJECT_ID = ""  # 圧縮管理プロジェクトID
    OS_SWIFT_COMP_MGR_USER_CREDENTIAL_ID = ""  # 圧縮管理プロジェクトのユーザー認証ID
    OS_SWIFT_COMP_MGR_USER_CREDENTIAL_SECRET = ""  # 圧縮管理プロジェクトのユーザー認証シークレット
    ACCOUNT_META_TEMP_URL_KEY = ""  # アカウントメタデータのtemp_url_key


# 本番環境用設定
class ProductionConfig(BaseConfig):
    OS_AUTH_URL = ""
    OS_SWIFT_INT_URL = ""
    OS_SWIFT_EXT_URL = ""
    OS_SWIFT_COMP_MGR_PROJECT_ID = ""
    OS_SWIFT_COMP_MGR_USER_CREDENTIAL_ID = ""
    OS_SWIFT_COMP_MGR_USER_CREDENTIAL_SECRET = ""
    ACCOUNT_META_TEMP_URL_KEY = ""


# 環境変数に基づいて適切な設定をロード
env = os.getenv("APP_ENV", "dev")
if env == "prod":
    config = ProductionConfig()
else:
    config = DevelopmentConfig()
