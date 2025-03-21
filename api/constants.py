class ResponseMessage:
    # Success messages
    CREATE_SUCCESS = "Create {} successfully"
    UPDATE_SUCCESS = "Update {} successfully"
    DELETE_SUCCESS = "Delete {} successfully"
    GET_SUCCESS = "Get {} successfully"
    LIST_SUCCESS = "Get list of {} successfully"
    FOLLOW_SUCCESS = "Follow user successfully"
    UNFOLLOW_SUCCESS = "Unfollow user successfully"
    LIKE_SUCCESS = "Like {} successfully"
    UNLIKE_SUCCESS = "Unlike {} successfully"

    # Error messages
    CREATE_ERROR = "Failed to create {}"
    UPDATE_ERROR = "Failed to update {}"
    DELETE_ERROR = "Failed to delete {}"
    NOT_FOUND = "{} not found"
    ALREADY_EXISTS = "{} already exists"
    INVALID_DATA = "Invalid data provided"
    UNAUTHORIZED = "You are not authorized to perform this action"
    FORBIDDEN = "You don't have permission to access this resource"
    VALIDATION_ERROR = "Validation error"
    MAX_DEPTH_REACHED = "Maximum comment depth reached"
    CANNOT_FOLLOW_SELF = "You cannot follow yourself"
    SERVER_ERROR = "Internal server error"

class EntityNames:
    USER = "user"
    POST = "post"
    COMMENT = "comment"
    CATEGORY = "category"
    SOCIAL_LINK = "social media link" 