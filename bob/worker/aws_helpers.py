

def error_code_equals(client_error, error_code):
    if (client_error
       and hasattr(client_error, 'response')
       and 'Error' in client_error.response
       and 'Code' in client_error.response['Error']):
        return client_error.response['Error']['Code'] == error_code
