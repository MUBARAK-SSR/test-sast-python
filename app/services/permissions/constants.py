# Placeholder content for constants.py

class SourceTypeConstant:
    def role_source_type():
        return 'role_class'
    
    def policy_source_type():
        return 'policy_class'
    
    def permission_source_type():
        return 'permission_class'

expire_cache_time = 3600

PERMISSION_ALGORITHM = "HS512"
PERMISSION_ACCESS_TOKEN_EXPIRE_SECOND = 1800