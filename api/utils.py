from rest_framework.response import Response
from rest_framework import status
from .constants import ResponseMessage, EntityNames

def create_response(status_code=status.HTTP_200_OK, message=None, data=None):
    """
    Create a standardized API response
    Args:
        status_code: HTTP status code
        message: Response message
        data: Response data
    Returns:
        Response object with standardized format
    """
    if not message:
        message = "Success" if status_code < 400 else "Error"
        
    return Response(
        {
            "code": status_code,
            "message": message,
            "data": data
        },
        status=status_code
    )

def create_validation_error_response(errors):
    """
    Create a response for validation errors
    Args:
        errors: Validation errors dictionary
    Returns:
        Response object with validation errors
    """
    return create_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        message=ResponseMessage.VALIDATION_ERROR,
        data=errors
    )

def create_not_found_response(entity_name):
    """
    Create a response for not found errors
    Args:
        entity_name: Name of the entity that was not found
    Returns:
        Response object with not found error
    """
    return create_response(
        status_code=status.HTTP_404_NOT_FOUND,
        message=ResponseMessage.NOT_FOUND.format(entity_name)
    )

def create_success_response(data=None, message=None):
    """
    Create a success response
    Args:
        data: Response data
        message: Success message
    Returns:
        Response object with success status
    """
    return create_response(
        status_code=status.HTTP_200_OK,
        message=message or "Success",
        data=data
    )

def create_created_response(data=None, entity_name=None):
    """
    Create a response for successful creation
    Args:
        data: Created object data
        entity_name: Name of the created entity
    Returns:
        Response object with created status
    """
    message = ResponseMessage.CREATE_SUCCESS.format(entity_name) if entity_name else "Created successfully"
    return create_response(
        status_code=status.HTTP_201_CREATED,
        message=message,
        data=data
    ) 