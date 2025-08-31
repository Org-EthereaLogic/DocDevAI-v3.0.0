# Vulture whitelist - add false positives here
# This file is used by vulture to ignore certain unused code patterns

# SQLAlchemy model attributes
_.id
_.created_at
_.updated_at
_.deleted_at
_.metadata
_.query
_.session
_.__tablename__
_.__table_args__
_.soft_delete
_.restore

# Pydantic model attributes  
_.model_config
_.model_fields
_.model_validate
_.model_dump
_.model_json_schema

# Common test fixtures
_.fixture
_.pytest_fixture
_.setup_method
_.teardown_method
_.setup_class
_.teardown_class

# FastAPI/Flask routes (if used)
_.get
_.post  
_.put
_.delete
_.patch

# Common metaclass attributes
_.__init__
_.__new__
_.__call__
_.__str__
_.__repr__

# Django/Flask (if applicable)
_.DoesNotExist
_.MultipleObjectsReturned
_.as_view

# Async patterns
_.aenter
_.aexit
_.aiter
_.anext

# Property decorators
_.setter
_.deleter

# DevDocAI specific patterns
_.generate_documentation
_.analyze_quality
_.review_code
_.template_registry
_.security_validator
_.miair_score