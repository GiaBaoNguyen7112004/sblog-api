from rest_framework import renderers

class StandardJSONRenderer(renderers.JSONRenderer):
    media_type = 'application/json'
    format = 'json'
    
    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = renderer_context.get('response')
        
        # Nếu response đã theo format chuẩn, không cần xử lý thêm
        if isinstance(data, dict) and all(key in data for key in ['code', 'message', 'data']):
            return super().render(data, accepted_media_type, renderer_context)
        
        # Lấy status code từ response
        status_code = response.status_code

        # Kiểm tra xem message có được truyền vào không
        message = None
        if isinstance(data, dict):
            message = data.pop('message', None)  # Lấy message nếu có, và xóa nó khỏi data

        # Xây dựng response format chuẩn
        standard_response = {
            'code': status_code,
            'message': message if message else self._get_message(status_code),
            'data': data
        }

        # Trả về JSON theo format chuẩn
        return super().render(standard_response, accepted_media_type, renderer_context)
    
    def _get_message(self, status_code):
        """
        Trả về thông điệp mặc định nếu không có message được truyền vào
        """
        messages = {
            200: 'Success',
            201: 'Created successfully',
            204: 'No content',
            400: 'Bad request',
            401: 'Unauthorized',
            403: 'Forbidden',
            404: 'Not found',
            405: 'Method not allowed',
            422: 'Validation error',
            500: 'Internal server error'
        }
        
        return messages.get(status_code, 'Unknown status')
